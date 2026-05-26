import pytest
import asyncio
from app.database.db import AsyncSessionLocal
from app.core.idempotency import IdempotencyEngine
from app.core.exceptions import IdempotencyViolationError
from sqlalchemy import delete
from app.database.models import PaymentIdempotency

@pytest.mark.asyncio
async def test_concurrent_idempotency_locking():
    """
    Test scenario: Firing 10 concurrent requests to acquire a lock for the same idempotency key.
    Expected outcome: Only 1 request succeeds (acquires lock), and 9 receive an IdempotencyViolationError.
    This asserts that PostgreSQL row-level locks (SELECT FOR UPDATE) prevent double-payment.
    """
    idempotency_key = "test-concurrent-key-999"
    payment_reference = "ref-999"

    # 1. Clean up any stale test records
    async with AsyncSessionLocal() as session:
        await session.execute(delete(PaymentIdempotency).filter_by(idempotency_key=idempotency_key))
        await session.commit()

    # 2. Define concurrent lock task
    async def lock_task(task_id: int):
        # Each task gets a separate session/connection from the pool
        async with AsyncSessionLocal() as session:
            try:
                # Wrap in atomic database transaction
                async with session.begin():
                    record = await IdempotencyEngine.acquire_lock(
                        session=session,
                        idempotency_key=idempotency_key,
                        payment_reference=f"ref-task-{task_id}"
                    )
                    # Artificially delay transaction completion to force overlapping requests
                    await asyncio.sleep(0.05)
                    return "SUCCESS", task_id
            except IdempotencyViolationError:
                return "VIOLATION", task_id
            except Exception as e:
                return "ERROR", str(e)

    # 3. Fire all 10 tasks concurrently
    results = await asyncio.gather(*(lock_task(i) for i in range(10)))

    # 4. Filter results
    successes = [r for r in results if r[0] == "SUCCESS"]
    violations = [r for r in results if r[0] == "VIOLATION"]
    errors = [r for r in results if r[0] == "ERROR"]

    print(f"\nConcurrent lock acquisition results: {results}")

    # Assertions
    assert not errors, f"Unexpected errors encountered: {errors}"
    assert len(successes) == 1, f"Expected exactly 1 success, got {len(successes)}"
    assert len(violations) == 9, f"Expected exactly 9 violations, got {len(violations)}"

    # 5. Clean up database records
    async with AsyncSessionLocal() as session:
        await session.execute(delete(PaymentIdempotency).filter_by(idempotency_key=idempotency_key))
        await session.commit()

    from app.database.db import engine
    await engine.dispose()

