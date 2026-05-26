import asyncio
from datetime import datetime, timedelta
from sqlalchemy import select
from app.database.db import AsyncSessionLocal
from app.database.models import TransactionLog
from app.core.constants import TransactionState
from app.database.repositories.transaction_repository import TransactionRepository
from app.services.settlement_service import SettlementService
from app.services.telemetry_service import TelemetryService
from loguru import logger
import random

class RetryWorker:
    """
    Background worker that runs a periodic loop to identify transactions stuck in PENDING_RETRY.
    Executes retries using an exponential backoff strategy, and moves persistent failures
    exceeding 5 attempts to FAILED_DLQ.
    """
    def __init__(self, interval_seconds: float = 3.0, max_retries: int = 5):
        self.interval_seconds = interval_seconds
        self.max_retries = max_retries
        self._task = None
        self._running = False

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info("Retry background worker started.")

    async def stop(self) -> None:
        if not self._running:
            return
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Retry background worker stopped.")

    async def _loop(self) -> None:
        import time
        while self._running:
            start_time = time.time()
            try:
                async with AsyncSessionLocal() as session:
                    try:
                        now = datetime.now()
                        
                        # Query transactions in PENDING_RETRY where next_retry_at is in the past
                        stmt = select(TransactionLog).where(
                            TransactionLog.transaction_state == TransactionState.PENDING_RETRY,
                            TransactionLog.next_retry_at <= now
                        ).with_for_update()
                        
                        res = await session.execute(stmt)
                        retry_txs = res.scalars().all()
                        
                        for tx in retry_txs:
                            logger.info(f"Retrying transaction '{tx.trace_id}' (Attempt: {tx.retry_attempts + 1})")
                            TelemetryService.record_retry_execution()
    
                            # 1. Check if we exceeded retry threshold
                            if tx.retry_attempts >= self.max_retries:
                                logger.warning(f"Retry threshold exhausted for trace '{tx.trace_id}'. Transitioning to FAILED_DLQ.")
                                async with session.begin_nested():
                                    await TransactionRepository.update_state(
                                        session=session,
                                        trace_id=tx.trace_id,
                                        new_state=TransactionState.FAILED_DLQ
                                    )
                                    tx.next_retry_at = None
                                    tx.worker_last_execution = datetime.now()
                                await session.commit()
                                TelemetryService.record_dlq_transition()
                                continue
    
                            # 2. Increment retry count and update timestamp
                            async with session.begin_nested():
                                tx.retry_attempts += 1
                                tx.worker_last_execution = datetime.now()
                            await session.flush()
    
                            # 3. Simulate retry processing (e.g. 80% success, 20% transient fail)
                            if random.random() < 0.8:
                                logger.info(f"Retry succeeded for trace '{tx.trace_id}'. Settling...")
                                # Resolve settlement via SettlementService (handles commit internally)
                                await SettlementService.resolve_settlement(
                                    session=session,
                                    trace_id=tx.trace_id,
                                    final_state=TransactionState.SETTLED,
                                    response_payload={
                                        "status": "SETTLED",
                                        "payment_reference": f"RETRY-PAY-{str(uuid_int())[:12]}",
                                        "payment_date": datetime.now().strftime("%d-%m-%Y %H:%M:%S")
                                    }
                                )
                            else:
                                # Transient failure: calculate exponential backoff
                                # Delay: Base (2s) * 2^attempt
                                delay_sec = 2 * (2 ** tx.retry_attempts)
                                next_run = datetime.now() + timedelta(seconds=delay_sec)
                                logger.warning(f"Retry failed transiently for trace '{tx.trace_id}'. Next retry scheduled in {delay_sec}s at {next_run}")
                                
                                async with session.begin_nested():
                                    tx.next_retry_at = next_run
                                await session.commit()
                        
                        await session.commit()
                    except Exception as inner_ex:
                        await session.rollback()
                        raise inner_ex
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error encountered in RetryWorker loop: {e}")
            finally:
                duration_ms = (time.time() - start_time) * 1000.0
                TelemetryService.record_worker_latency("retry_worker", duration_ms)
                
            try:
                await asyncio.sleep(self.interval_seconds)
            except asyncio.CancelledError:
                break

def uuid_int() -> int:
    import uuid
    return uuid.uuid4().int
