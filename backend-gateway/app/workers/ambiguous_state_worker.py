import asyncio
import time
from datetime import datetime, timedelta
from sqlalchemy import select, or_
from app.database.db import AsyncSessionLocal
from app.database.models import TransactionLog
from app.core.constants import TransactionState
from app.database.repositories.transaction_repository import TransactionRepository
from app.core.idempotency import IdempotencyEngine
from app.services.telemetry_service import TelemetryService
from loguru import logger

class AmbiguousStateWorker:
    """
    Background worker that detects transactions stuck in non-terminal, in-flight states
    (e.g., INITIALIZED, PENDING_SUBMISSION, NETWORK_IN_FLIGHT) for too long (e.g., 15s)
    and transitions them into AMBIGUOUS_TIMEOUT.
    """
    def __init__(self, stale_timeout_seconds: float = 15.0, interval_seconds: float = 5.0):
        self.stale_timeout_seconds = stale_timeout_seconds
        self.interval_seconds = interval_seconds
        self._task = None
        self._running = False

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info("Ambiguous State background worker started.")

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
        logger.info("Ambiguous State background worker stopped.")

    async def _loop(self) -> None:
        while self._running:
            start_time = time.time()
            try:
                async with AsyncSessionLocal() as session:
                    try:
                        # Find rows stuck in-flight
                        cutoff_time = datetime.now() - timedelta(seconds=self.stale_timeout_seconds)
                        
                        stmt = select(TransactionLog).where(
                            TransactionLog.transaction_state.in_([
                                TransactionState.INITIALIZED,
                                TransactionState.PENDING_SUBMISSION,
                                TransactionState.NETWORK_IN_FLIGHT
                            ]),
                            TransactionLog.updated_at <= cutoff_time
                        ).with_for_update()
                        
                        res = await session.execute(stmt)
                        stale_txs = res.scalars().all()
                        
                        for tx in stale_txs:
                            logger.warning(f"Transaction trace '{tx.trace_id}' has been in '{tx.transaction_state}' state too long. Marking as AMBIGUOUS_TIMEOUT.")
                            
                            # Use a nested transaction block to update state and idempotency lock status
                            async with session.begin_nested():
                                await TransactionRepository.update_state(
                                    session=session,
                                    trace_id=tx.trace_id,
                                    new_state=TransactionState.AMBIGUOUS_TIMEOUT
                                )
                                # Update idempotency status to PENDING for reconciliation recovery
                                await IdempotencyEngine.update_status(session, tx.trace_id, "PENDING")
                            
                            await session.commit()
                            logger.info(f"Stuck transaction '{tx.trace_id}' successfully transitioned to AMBIGUOUS_TIMEOUT.")
                    except Exception as inner_ex:
                        await session.rollback()
                        raise inner_ex
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error encountered in AmbiguousStateWorker loop: {e}")
            finally:
                duration_ms = (time.time() - start_time) * 1000.0
                TelemetryService.record_worker_latency("ambiguous_state_worker", duration_ms)
                
            try:
                await asyncio.sleep(self.interval_seconds)
            except asyncio.CancelledError:
                break

