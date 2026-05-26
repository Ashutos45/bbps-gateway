import pytest
from app.database.db import AsyncSessionLocal
from app.database.repositories.transaction_repository import TransactionRepository
from app.core.constants import TransactionState
from sqlalchemy import delete
from app.database.models import TransactionLog

@pytest.mark.asyncio
async def test_transaction_persistence_lifecycle():
    """
    Validates the end-to-end database persistence flow for transactions:
    1. Create a transaction log in INITIALIZED state.
    2. Retrieve it to verify parameters.
    3. Update the state to PENDING_SUBMISSION and then to NETWORK_IN_FLIGHT.
    4. Transition to final SETTLED state with response payload.
    """
    trace_id = "persistence-test-trace-888"
    customer_id = "cust-888"
    biller_id = "biller-888"
    amount = 1500.50
    req_payload = {"billerid": biller_id, "amount": amount}
    res_payload = {"status": "SUCCESS", "ref_no": "TXN888"}

    # 1. Clean up stale records
    async with AsyncSessionLocal() as session:
        await session.execute(delete(TransactionLog).filter_by(trace_id=trace_id))
        await session.commit()

    # 2. Initialize log entry
    async with AsyncSessionLocal() as session:
        async with session.begin():
            log = await TransactionRepository.create_log(
                session=session,
                trace_id=trace_id,
                customer_id=customer_id,
                biller_id=biller_id,
                amount=amount,
                request_payload=req_payload
            )
            assert log.trace_id == trace_id
            assert log.transaction_state == TransactionState.INITIALIZED

    # 3. Retrieve and transition state
    async with AsyncSessionLocal() as session:
        async with session.begin():
            # Update to PENDING_SUBMISSION
            log = await TransactionRepository.update_state(
                session=session,
                trace_id=trace_id,
                new_state=TransactionState.PENDING_SUBMISSION
            )
            assert log.transaction_state == TransactionState.PENDING_SUBMISSION

    # 4. Final transition to settled with response payload
    async with AsyncSessionLocal() as session:
        async with session.begin():
            log = await TransactionRepository.update_state(
                session=session,
                trace_id=trace_id,
                new_state=TransactionState.NETWORK_IN_FLIGHT
            )
            assert log.transaction_state == TransactionState.NETWORK_IN_FLIGHT

            log = await TransactionRepository.update_state(
                session=session,
                trace_id=trace_id,
                new_state=TransactionState.SETTLED,
                response_payload=res_payload
            )
            assert log.transaction_state == TransactionState.SETTLED
            assert log.response_payload == res_payload

    # 5. Retrieve from database again to ensure persistence
    async with AsyncSessionLocal() as session:
        log = await TransactionRepository.get_by_trace_id(session, trace_id)
        assert log is not None
        assert log.trace_id == trace_id
        assert log.customer_id == customer_id
        assert log.amount == amount
        assert log.transaction_state == TransactionState.SETTLED
        assert log.response_payload == res_payload

    # 6. Clean up
    async with AsyncSessionLocal() as session:
        await session.execute(delete(TransactionLog).filter_by(trace_id=trace_id))
        await session.commit()

    from app.database.db import engine
    await engine.dispose()

