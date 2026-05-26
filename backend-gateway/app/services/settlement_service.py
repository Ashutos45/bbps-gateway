from sqlalchemy.ext.asyncio import AsyncSession
from app.database.repositories.transaction_repository import TransactionRepository
from app.core.idempotency import IdempotencyEngine
from app.core.constants import TransactionState
from app.database.models import ReconciliationLog
from app.services.telemetry_service import TelemetryService
from loguru import logger
from datetime import datetime
import uuid

class SettlementService:
    """
    Orchestrates the safe, atomic, and idempotent resolution of transactions into terminal states.
    Employs row locking (SELECT FOR UPDATE) to prevent concurrent double-settlement races.
    """

    @staticmethod
    async def resolve_settlement(
        session: AsyncSession,
        trace_id: str,
        final_state: str,  # SETTLED or FAILED
        response_payload: dict = None
    ) -> bool:
        logger.info(f"Attempting to resolve settlement for trace '{trace_id}' into state '{final_state}'")

        # 1. Lock the transaction record using SELECT FOR UPDATE
        tx = await TransactionRepository.get_by_trace_id(session, trace_id, for_update=True)
        if not tx:
            logger.warning(f"No transaction log found for trace '{trace_id}'")
            return False

        # 2. Check if already in a terminal state to prevent double settlement
        if tx.transaction_state in (TransactionState.SETTLED, TransactionState.FAILED):
            logger.info(f"Transaction '{trace_id}' is already in terminal state '{tx.transaction_state}'. Ignoring settlement resolution.")
            return False

        was_ambiguous = (tx.transaction_state == TransactionState.AMBIGUOUS_TIMEOUT)

        # 3. Update transaction log status and increment version for optimistic audit
        tx.reconciliation_version += 1
        tx.worker_last_execution = datetime.now()
        await TransactionRepository.update_state(
            session=session,
            trace_id=trace_id,
            new_state=final_state,
            response_payload=response_payload
        )

        if was_ambiguous:
            TelemetryService.record_ambiguous_recovery_resolution()

        # 4. Update the corresponding idempotency lock status
        idempotency_status = "SUCCESS" if final_state == TransactionState.SETTLED else "FAILED"
        await IdempotencyEngine.update_status(session, trace_id, idempotency_status)

        # 5. Retrieve or create reconciliation log entry to track historical attempts
        from sqlalchemy import select
        stmt_rec = select(ReconciliationLog).filter_by(trace_id=trace_id)
        res_rec = await session.execute(stmt_rec)
        rec_log = res_rec.scalar_one_or_none()

        if not rec_log:
            rec_log = ReconciliationLog(
                id=uuid.uuid4(),
                trace_id=trace_id,
                polling_attempts=1,
                resolved_state=final_state,
                reconciliation_status="RESOLVED"
            )
            session.add(rec_log)
        else:
            rec_log.polling_attempts += 1
            rec_log.resolved_state = final_state
            rec_log.reconciliation_status = "RESOLVED"
            session.add(rec_log)

        # 6. Commit transaction atomically
        await session.commit()
        logger.info(f"Successfully resolved and committed settlement for trace '{trace_id}' as '{final_state}'")
        return True
