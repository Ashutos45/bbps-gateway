from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database.models import TransactionLog
from app.database.repositories.transaction_repository import TransactionRepository
from app.core.constants import TransactionState
from app.services.settlement_service import SettlementService
from app.services.telemetry_service import TelemetryService
from loguru import logger
from datetime import datetime
import random
import uuid

class RecoveryService:
    """
    Coordinates detection and resolution of transactions stuck in AMBIGUOUS_TIMEOUT.
    """

    @staticmethod
    async def recover_ambiguous_transactions(session: AsyncSession) -> int:
        logger.info("Scanning for transactions stuck in AMBIGUOUS_TIMEOUT...")

        # 1. Query all trace IDs in AMBIGUOUS_TIMEOUT state
        stmt = select(TransactionLog.trace_id).filter_by(transaction_state=TransactionState.AMBIGUOUS_TIMEOUT)
        res = await session.execute(stmt)
        ambiguous_trace_ids = res.scalars().all()

        recovered_count = 0
        for trace_id in ambiguous_trace_ids:
            logger.info(f"Initiating recovery processing for ambiguous transaction trace: '{trace_id}'")
            
            try:
                # Acquire SELECT FOR UPDATE lock on the specific record
                tx = await TransactionRepository.get_by_trace_id(session, trace_id, for_update=True)
                if not tx:
                    logger.warning(f"Transaction trace '{trace_id}' no longer exists.")
                    continue
                
                # Verify that transaction is still in AMBIGUOUS_TIMEOUT state under the lock
                if tx.transaction_state != TransactionState.AMBIGUOUS_TIMEOUT:
                    logger.info(f"Transaction trace '{trace_id}' is already resolved to state '{tx.transaction_state}'. Skipping.")
                    continue

                # 2. Simulate polling downstream merchant settlement
                # We'll resolve as SETTLED 80% of the time, FAILED 20% of the time.
                resolved_state = TransactionState.SETTLED if random.random() < 0.8 else TransactionState.FAILED
                
                # Format a mock response payload if settled
                res_payload = None
                if resolved_state == TransactionState.SETTLED:
                    payment_ref = tx.response_payload.get("payment_reference") if tx.response_payload else f"PAY-{str(uuid.uuid4().int)[:16]}"
                    res_payload = tx.request_payload.copy() if tx.request_payload else {}
                    res_payload.update({
                        "status": "SETTLED",
                        "payment_reference": payment_ref,
                        "payment_date": datetime.now().strftime("%d-%m-%Y %H:%M:%S")
                    })
                
                # Update retry counters on the locked transaction
                async with session.begin_nested():
                    tx.retry_attempts += 1
                    tx.worker_last_execution = datetime.now()
                await session.flush()
                
                # 3. Resolve transaction terminal state safely via SettlementService
                did_settle = await SettlementService.resolve_settlement(
                    session=session,
                    trace_id=trace_id,
                    final_state=resolved_state,
                    response_payload=res_payload
                )

                if did_settle:
                    recovered_count += 1
                    logger.info(f"Successfully recovered trace '{trace_id}' as '{resolved_state}'")
            except Exception as e:
                logger.error(f"Error during recovery processing for trace '{trace_id}': {e}")
                TelemetryService.record_reconciliation_failure()
                await session.rollback()
                continue

        logger.info(f"Recovery scan completed. Total recovered: {recovered_count}")
        return recovered_count

