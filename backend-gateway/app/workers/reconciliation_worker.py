import asyncio
import time
from app.database.db import AsyncSessionLocal
from app.services.recovery_service import RecoveryService
from app.services.telemetry_service import TelemetryService
from loguru import logger

class ReconciliationWorker:
    """
    Background worker that runs a periodic loop to detect and reconcile
    transactions that are stuck in the AMBIGUOUS_TIMEOUT state.
    """
    def __init__(self, interval_seconds: float = 5.0):
        self.interval_seconds = interval_seconds
        self._task = None
        self._running = False

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info("Reconciliation background worker started.")

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
        logger.info("Reconciliation background worker stopped.")

    async def _loop(self) -> None:
        while self._running:
            start_time = time.time()
            try:
                # Open a database session
                async with AsyncSessionLocal() as session:
                    try:
                        # Run recovery scans
                        await RecoveryService.recover_ambiguous_transactions(session)
                        await session.commit()
                    except Exception as inner_ex:
                        await session.rollback()
                        raise inner_ex
            except asyncio.CancelledError:
                # Exit cleanly on cancellation
                break
            except Exception as e:
                logger.error(f"Error encountered in ReconciliationWorker loop: {e}")
                TelemetryService.record_reconciliation_failure()
            finally:
                duration_ms = (time.time() - start_time) * 1000.0
                TelemetryService.record_worker_latency("reconciliation_worker", duration_ms)
                
            try:
                await asyncio.sleep(self.interval_seconds)
            except asyncio.CancelledError:
                break

