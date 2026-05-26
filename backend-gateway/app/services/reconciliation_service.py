from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.database.repositories.transaction_repository import TransactionRepository
from app.database.models import ReconciliationLog, TransactionLog
from app.core.idempotency import IdempotencyEngine
from app.core.constants import TransactionState
from app.schemas.reconciliation_schema import ReconciliationResponse
from app.services.telemetry_service import TelemetryService
from loguru import logger
import uuid
from datetime import datetime

class ReconciliationService:
    """
    Reconciliation Engine that polls and resolves ambiguous payment transactions,
    transitioning them to terminal states (SETTLED or FAILED).
    """

    @staticmethod
    async def reconcile_transaction(
        session: AsyncSession,
        trace_id: str
    ) -> ReconciliationResponse:
        logger.info(f"Reconciliation requested for trace ID: {trace_id}")

        # 1. Fetch transaction log
        tx = await TransactionRepository.get_by_trace_id(session, trace_id, for_update=True)
        if not tx:
            logger.warning(f"Transaction trace '{trace_id}' not found for reconciliation.")
            return ReconciliationResponse(
                trace_id=trace_id,
                polling_attempts=0,
                reconciliation_status="UNRESOLVED",
                message="Transaction trace not found."
            )

        # 2. Check if already settled or failed
        if tx.transaction_state in (TransactionState.SETTLED, TransactionState.FAILED):
            logger.info(f"Transaction '{trace_id}' is already in terminal state '{tx.transaction_state}'. No reconciliation needed.")
            return ReconciliationResponse(
                trace_id=trace_id,
                polling_attempts=1,
                resolved_state=tx.transaction_state,
                reconciliation_status="RESOLVED",
                message=f"Transaction already in terminal state: {tx.transaction_state}."
            )

        was_ambiguous = (tx.transaction_state == TransactionState.AMBIGUOUS_TIMEOUT)

        # 3. Handle AMBIGUOUS_TIMEOUT resolution
        # Fetch or initialize reconciliation log
        stmt_rec = select(ReconciliationLog).filter_by(trace_id=trace_id)
        res_rec = await session.execute(stmt_rec)
        rec_log = res_rec.scalar_one_or_none()

        if not rec_log:
            rec_log = ReconciliationLog(
                id=uuid.uuid4(),
                trace_id=trace_id,
                polling_attempts=1,
                reconciliation_status="PENDING"
            )
            session.add(rec_log)
        else:
            rec_log.polling_attempts += 1

        # Simulate polling downstream settlement engine
        # In this simulation, we'll resolve as SETTLED with an 80% chance
        # and FAILED with a 20% chance.
        resolved_state = TransactionState.SETTLED if random_choice_settled() else TransactionState.FAILED
        
        # Format response payload if settled
        res_payload = None
        if resolved_state == TransactionState.SETTLED:
            payment_ref = tx.response_payload.get("payment_reference") if tx.response_payload else f"PAY-{str(uuid.uuid4().int)[:16]}"
            res_payload = tx.request_payload.copy() if tx.request_payload else {}
            res_payload.update({
                "status": "SETTLED",
                "payment_reference": payment_ref,
                "payment_date": datetime.now().strftime("%d-%m-%Y %H:%M:%S")
            })

        # Update database logs
        # Update transaction log state
        await TransactionRepository.update_state(
            session=session,
            trace_id=trace_id,
            new_state=resolved_state,
            response_payload=res_payload
        )
        if was_ambiguous:
            TelemetryService.record_ambiguous_recovery_resolution()

        # Update idempotency status
        idempotency_status = "SUCCESS" if resolved_state == TransactionState.SETTLED else "FAILED"
        await IdempotencyEngine.update_status(session, trace_id, idempotency_status)
        
        # Update reconciliation log
        rec_log.resolved_state = resolved_state
        rec_log.reconciliation_status = "RESOLVED"
        session.add(rec_log)
        
        # Commit transaction atomically
        await session.commit()

        logger.info(f"Reconciliation resolved trace '{trace_id}' as '{resolved_state}' (Attempts: {rec_log.polling_attempts})")
        return ReconciliationResponse(
            trace_id=trace_id,
            polling_attempts=rec_log.polling_attempts,
            resolved_state=resolved_state,
            reconciliation_status="RESOLVED",
            message=f"Transaction successfully reconciled and transitioned to {resolved_state}."
        )

def random_choice_settled() -> bool:
    """
    Returns True with an 80% probability to simulate settlement success rate.
    """
    import random
    return random.random() < 0.8
