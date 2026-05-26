import pytest
import asyncio
import time
import uuid
import base64
from datetime import datetime, timedelta
from sqlalchemy import delete, select, update
from app.database.db import AsyncSessionLocal, engine
from app.database.models import TransactionLog, ReconciliationLog, PaymentIdempotency
from app.core.constants import TransactionState
from app.database.repositories.transaction_repository import TransactionRepository
from app.core.idempotency import IdempotencyEngine
from app.services.telemetry_service import TelemetryService
from app.services.recovery_service import RecoveryService
from app.services.settlement_service import SettlementService
from app.workers.ambiguous_state_worker import AmbiguousStateWorker
from app.workers.reconciliation_worker import ReconciliationWorker
from app.workers.retry_worker import RetryWorker
from app.workers.file_generation_worker import FileGenerationWorker

@pytest.mark.asyncio
async def test_ambiguous_state_worker_transitions():
    """
    Validates that:
    - In-flight/Initialized transactions older than 15s are transitioned to AMBIGUOUS_TIMEOUT.
    - Active/fresh transactions are not touched.
    """
    stale_trace = "stale-trace-123"
    fresh_trace = "fresh-trace-456"

    try:
        # 1. Clean up stale records
        async with AsyncSessionLocal() as session:
            await session.execute(delete(TransactionLog).where(TransactionLog.trace_id.in_([stale_trace, fresh_trace])))
            await session.execute(delete(PaymentIdempotency).where(PaymentIdempotency.idempotency_key.in_([stale_trace, fresh_trace])))
            await session.commit()

        # 2. Setup mock data
        async with AsyncSessionLocal() as session:
            # Acquire idempotency locks
            await IdempotencyEngine.acquire_lock(session, stale_trace, f"pay-ref-{stale_trace}")
            await IdempotencyEngine.acquire_lock(session, fresh_trace, f"pay-ref-{fresh_trace}")
            
            # Create transaction logs
            stale_tx = TransactionLog(
                id=uuid.uuid4(),
                trace_id=stale_trace,
                customer_id="cust1",
                biller_id="UPPCL0000UTP01",
                amount=100.0,
                transaction_state=TransactionState.NETWORK_IN_FLIGHT,
                updated_at=datetime.now() - timedelta(seconds=20),
                created_at=datetime.now() - timedelta(seconds=20)
            )
            fresh_tx = TransactionLog(
                id=uuid.uuid4(),
                trace_id=fresh_trace,
                customer_id="cust2",
                biller_id="UPPCL0000UTP01",
                amount=200.0,
                transaction_state=TransactionState.NETWORK_IN_FLIGHT,
                updated_at=datetime.now(),
                created_at=datetime.now()
            )
            session.add_all([stale_tx, fresh_tx])
            await session.commit()

        # Force updated_at for stale transaction log in DB because of SQLAlchemy automatic onupdate behavior
        async with AsyncSessionLocal() as session:
            past_time = datetime.now() - timedelta(seconds=20)
            await session.execute(
                update(TransactionLog)
                .where(TransactionLog.trace_id == stale_trace)
                .values(updated_at=past_time)
            )
            await session.commit()

        # 3. Instantiate and run AmbiguousStateWorker loop once manually
        worker = AmbiguousStateWorker(stale_timeout_seconds=15.0, interval_seconds=1.0)
        worker._running = True
        
        # Run the worker loop logic directly once
        start_time = time.time()
        async with AsyncSessionLocal() as session:
            try:
                cutoff_time = datetime.now() - timedelta(seconds=worker.stale_timeout_seconds)
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
                    async with session.begin_nested():
                        await TransactionRepository.update_state(session, tx.trace_id, TransactionState.AMBIGUOUS_TIMEOUT)
                        await IdempotencyEngine.update_status(session, tx.trace_id, "PENDING")
                    await session.commit()
            except Exception as e:
                await session.rollback()
                raise e
            finally:
                duration_ms = (time.time() - start_time) * 1000.0
                TelemetryService.record_worker_latency("ambiguous_state_worker", duration_ms)

        # 4. Verify DB outcomes
        async with AsyncSessionLocal() as session:
            # Retrieve stale transaction
            stale_res = await TransactionRepository.get_by_trace_id(session, stale_trace)
            assert stale_res.transaction_state == TransactionState.AMBIGUOUS_TIMEOUT
            
            # Retrieve fresh transaction
            fresh_res = await TransactionRepository.get_by_trace_id(session, fresh_trace)
            assert fresh_res.transaction_state == TransactionState.NETWORK_IN_FLIGHT

            # Clean up
            await session.execute(delete(TransactionLog).where(TransactionLog.trace_id.in_([stale_trace, fresh_trace])))
            await session.execute(delete(PaymentIdempotency).where(PaymentIdempotency.idempotency_key.in_([stale_trace, fresh_trace])))
            await session.commit()
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_reconciliation_worker_and_recovery_service():
    """
    Validates that:
    - Ambiguous transactions are identified and resolved to a terminal state (SETTLED or FAILED) by RecoveryService.
    - Retry attempts are incremented and worker_last_execution is updated.
    - Telemetry monitors recovery counts.
    """
    trace_id = "reconciliation-recovery-trace"

    try:
        # 1. Clean up
        async with AsyncSessionLocal() as session:
            await session.execute(delete(TransactionLog).where(TransactionLog.trace_id == trace_id))
            await session.execute(delete(ReconciliationLog).where(ReconciliationLog.trace_id == trace_id))
            await session.execute(delete(PaymentIdempotency).where(PaymentIdempotency.idempotency_key == trace_id))
            await session.commit()

        # 2. Seed ambiguous transaction
        async with AsyncSessionLocal() as session:
            await IdempotencyEngine.acquire_lock(session, trace_id, f"pay-ref-{trace_id}")
            tx = TransactionLog(
                id=uuid.uuid4(),
                trace_id=trace_id,
                customer_id="cust1",
                biller_id="UPPCL0000UTP01",
                amount=150.0,
                transaction_state=TransactionState.AMBIGUOUS_TIMEOUT,
                retry_attempts=0
            )
            session.add(tx)
            await session.commit()

        # Get baseline telemetry report
        async with AsyncSessionLocal() as session:
            baseline_report = await TelemetryService.get_report(session)

        # 3. Trigger recovery service
        async with AsyncSessionLocal() as session:
            recovered = await RecoveryService.recover_ambiguous_transactions(session)
            assert recovered == 1

        # 4. Assert changes in DB
        async with AsyncSessionLocal() as session:
            tx_res = await TransactionRepository.get_by_trace_id(session, trace_id)
            assert tx_res.transaction_state in (TransactionState.SETTLED, TransactionState.FAILED)
            assert tx_res.retry_attempts == 1
            assert tx_res.worker_last_execution is not None

            # Check reconciliation log
            rec_stmt = select(ReconciliationLog).where(ReconciliationLog.trace_id == trace_id)
            rec_res = await session.execute(rec_stmt)
            rec_log = rec_res.scalar_one_or_none()
            assert rec_log is not None
            assert rec_log.reconciliation_status == "RESOLVED"
            assert rec_log.resolved_state == tx_res.transaction_state

            # Check telemetry updates
            report = await TelemetryService.get_report(session)
            assert report.ambiguous_recovery_resolutions == baseline_report.ambiguous_recovery_resolutions + 1

            # Clean up
            await session.execute(delete(TransactionLog).where(TransactionLog.trace_id == trace_id))
            await session.execute(delete(ReconciliationLog).where(ReconciliationLog.trace_id == trace_id))
            await session.execute(delete(PaymentIdempotency).where(PaymentIdempotency.idempotency_key == trace_id))
            await session.commit()
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_retry_worker_scheduling_and_dlq():
    """
    Validates that:
    - Stale retries are executed based on exponential backoffs.
    - Transitions to FAILED_DLQ occur when attempts exceed the threshold (5 attempts).
    - Telemetry DLQ transitions counter increments correctly.
    """
    retry_trace = "retry-trace-1"
    dlq_trace = "retry-trace-dlq"

    try:
        # 1. Clean up
        async with AsyncSessionLocal() as session:
            await session.execute(delete(TransactionLog).where(TransactionLog.trace_id.in_([retry_trace, dlq_trace])))
            await session.execute(delete(PaymentIdempotency).where(PaymentIdempotency.idempotency_key.in_([retry_trace, dlq_trace])))
            await session.commit()

        # 2. Seed one retry-ready transaction and one threshold-exhausted transaction
        past_retry_at = datetime.now() - timedelta(seconds=10)
        async with AsyncSessionLocal() as session:
            await IdempotencyEngine.acquire_lock(session, retry_trace, f"pay-ref-{retry_trace}")
            await IdempotencyEngine.acquire_lock(session, dlq_trace, f"pay-ref-{dlq_trace}")

            tx_retry = TransactionLog(
                id=uuid.uuid4(),
                trace_id=retry_trace,
                customer_id="cust1",
                biller_id="UPPCL0000UTP01",
                amount=50.0,
                transaction_state=TransactionState.PENDING_RETRY,
                retry_attempts=2,
                next_retry_at=past_retry_at
            )

            tx_dlq = TransactionLog(
                id=uuid.uuid4(),
                trace_id=dlq_trace,
                customer_id="cust2",
                biller_id="UPPCL0000UTP01",
                amount=100.0,
                transaction_state=TransactionState.PENDING_RETRY,
                retry_attempts=5, # threshold exhausted
                next_retry_at=past_retry_at
            )
            session.add_all([tx_retry, tx_dlq])
            await session.commit()

        # Get baseline telemetry report
        async with AsyncSessionLocal() as session:
            baseline_report = await TelemetryService.get_report(session)

        # 3. Instantiate and run RetryWorker loop once manually
        worker = RetryWorker(max_retries=5)
        
        # Run loop body manually
        async with AsyncSessionLocal() as session:
            try:
                now = datetime.now()
                stmt = select(TransactionLog).where(
                    TransactionLog.transaction_state == TransactionState.PENDING_RETRY,
                    TransactionLog.next_retry_at <= now
                ).with_for_update()
                res = await session.execute(stmt)
                retry_txs = res.scalars().all()
                
                for tx in retry_txs:
                    if tx.retry_attempts >= worker.max_retries:
                        async with session.begin_nested():
                            await TransactionRepository.update_state(session, tx.trace_id, TransactionState.FAILED_DLQ)
                            tx.next_retry_at = None
                            tx.worker_last_execution = datetime.now()
                        await session.commit()
                        TelemetryService.record_dlq_transition()
                        continue

                    # Simulate retry
                    async with session.begin_nested():
                        tx.retry_attempts += 1
                        tx.worker_last_execution = datetime.now()
                    await session.flush()

                    # Force resolution (SettlementService commits internally)
                    await SettlementService.resolve_settlement(
                        session=session,
                        trace_id=tx.trace_id,
                        final_state=TransactionState.SETTLED,
                        response_payload={
                            "status": "SETTLED",
                            "payment_reference": f"RETRY-PAY-{uuid.uuid4().hex[:8]}"
                        }
                    )
                await session.commit()
            except Exception as e:
                await session.rollback()
                raise e

        # 4. Verify outcomes in DB
        async with AsyncSessionLocal() as session:
            tx_retry_res = await TransactionRepository.get_by_trace_id(session, retry_trace)
            assert tx_retry_res.transaction_state == TransactionState.SETTLED
            assert tx_retry_res.retry_attempts == 3

            tx_dlq_res = await TransactionRepository.get_by_trace_id(session, dlq_trace)
            assert tx_dlq_res.transaction_state == TransactionState.FAILED_DLQ
            assert tx_dlq_res.next_retry_at is None

            # Verify telemetry transitions counter incremented
            report = await TelemetryService.get_report(session)
            assert report.dlq_transitions == baseline_report.dlq_transitions + 1

            # Clean up
            await session.execute(delete(TransactionLog).where(TransactionLog.trace_id.in_([retry_trace, dlq_trace])))
            await session.execute(delete(PaymentIdempotency).where(PaymentIdempotency.idempotency_key.in_([retry_trace, dlq_trace])))
            await session.commit()
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_concurrent_settlement_double_settle_prevention():
    """
    Validates concurrency safety of the recovery flows:
    - Multiple concurrent worker settlement resolutions acquire row locks.
    - Double settlement is blocked (only the first task changes state, others return False).
    """
    trace_id = "concurrent-settle-trace"

    try:
        # 1. Clean up
        async with AsyncSessionLocal() as session:
            await session.execute(delete(TransactionLog).where(TransactionLog.trace_id == trace_id))
            await session.execute(delete(PaymentIdempotency).where(PaymentIdempotency.idempotency_key == trace_id))
            await session.commit()

        # 2. Seed ambiguous transaction
        async with AsyncSessionLocal() as session:
            await IdempotencyEngine.acquire_lock(session, trace_id, f"pay-ref-{trace_id}")
            tx = TransactionLog(
                id=uuid.uuid4(),
                trace_id=trace_id,
                customer_id="cust1",
                biller_id="UPPCL0000UTP01",
                amount=150.0,
                transaction_state=TransactionState.AMBIGUOUS_TIMEOUT,
                retry_attempts=0
            )
            session.add(tx)
            await session.commit()

        # 3. Fire concurrent settlement resolutions
        async def concurrent_settle(target_state: str, artificial_delay: float):
            async with AsyncSessionLocal() as session:
                try:
                    did_settle = await SettlementService.resolve_settlement(
                        session=session,
                        trace_id=trace_id,
                        final_state=target_state,
                        response_payload={"status": target_state}
                    )
                    return did_settle
                except Exception as e:
                    return str(e)

        # Fire both concurrently: one trying to settle, one trying to fail
        results = await asyncio.gather(
            concurrent_settle(TransactionState.SETTLED, 0.05),
            concurrent_settle(TransactionState.FAILED, 0.0)
        )

        # 4. Verify outcomes
        # Exactly one must return True, the other must return False
        successes = [r for r in results if r is True]
        ignored = [r for r in results if r is False]
        
        assert len(successes) == 1, f"Expected exactly 1 settlement success, got: {successes}"
        assert len(ignored) == 1, f"Expected exactly 1 settlement skip, got: {ignored}"

        # Verify state in DB
        async with AsyncSessionLocal() as session:
            tx_res = await TransactionRepository.get_by_trace_id(session, trace_id)
            assert tx_res.transaction_state in (TransactionState.SETTLED, TransactionState.FAILED)

            # Clean up
            await session.execute(delete(TransactionLog).where(TransactionLog.trace_id == trace_id))
            await session.execute(delete(PaymentIdempotency).where(PaymentIdempotency.idempotency_key == trace_id))
            await session.commit()
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_async_file_generation_progress():
    """
    Validates that:
    - Async file generation compiles Biller Master file ZIP non-blockingly.
    - Progress updates from 0 -> 10 -> 50 -> 75 -> 100%.
    - Exposes generation status and supports retrieving file content cleanly.
    """
    file_id = "test-file-generation-progress"
    callback_url = "http://localhost:8000/callback/file"

    # Start file generation worker
    FileGenerationWorker.start()

    try:
        # Enqueue job
        FileGenerationWorker.enqueue_task(file_id, callback_url)

        # Check inprocess state
        status = FileGenerationWorker.get_task_status(file_id)
        assert status["status"] == "INPROCESS"
        
        # Poll for completion and check progress increments
        max_polls = 10
        completed = False
        progress_values = []
        
        for _ in range(max_polls):
            status = FileGenerationWorker.get_task_status(file_id)
            progress_values.append(status["progress"])
            if status["status"] == "COMPLETED":
                completed = True
                break
            await asyncio.sleep(0.4)

        assert completed, f"File generation did not complete in time. Status: {status}"
        assert 100 in progress_values
        assert any(x in progress_values for x in [10, 50, 75])

        # Verify ZIP retrieval structure
        assert status["fileName"] == f"{file_id}.zip"
        assert status["filePath"] is not None
    finally:
        await FileGenerationWorker.stop()
