from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database.models import TransactionLog
from app.core.state_machine import validate_state_transition
from app.core.constants import TransactionState
from loguru import logger
import uuid

class TransactionRepository:
    """
    Repository class to manage persistence of transaction log records.
    """
    
    @staticmethod
    async def create_log(
        session: AsyncSession,
        trace_id: str,
        customer_id: str,
        biller_id: str,
        amount: float,
        request_payload: dict
    ) -> TransactionLog:
        """
        Creates and returns a new TransactionLog in INITIALIZED state.
        """
        log = TransactionLog(
            id=uuid.uuid4(),
            trace_id=trace_id,
            customer_id=customer_id,
            biller_id=biller_id,
            amount=amount,
            transaction_state=TransactionState.INITIALIZED,
            request_payload=request_payload
        )
        session.add(log)
        await session.flush()
        logger.info(f"Created transaction log for trace '{trace_id}' in INITIALIZED state.")
        return log

    @staticmethod
    async def get_by_trace_id(
        session: AsyncSession,
        trace_id: str,
        for_update: bool = False
    ) -> TransactionLog:
        """
        Queries and returns a TransactionLog by its trace_id.
        Allows row-locking if for_update is True.
        """
        stmt = select(TransactionLog).filter_by(trace_id=trace_id)
        if for_update:
            stmt = stmt.with_for_update()
            
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def update_state(
        session: AsyncSession,
        trace_id: str,
        new_state: str,
        response_payload: dict = None
    ) -> TransactionLog:
        """
        Transitions the state of a transaction log record, validating the transition
        via the state machine beforehand.
        """
        # Lock row to prevent concurrent updates
        log = await TransactionRepository.get_by_trace_id(session, trace_id, for_update=True)
        if not log:
            logger.error(f"Transaction log for trace '{trace_id}' not found for status update.")
            raise ValueError(f"Transaction log '{trace_id}' not found.")

        # Validate transition using state machine validator
        validate_state_transition(log.transaction_state, new_state)

        log.transaction_state = new_state
        if response_payload is not None:
            log.response_payload = response_payload

        await session.flush()
        logger.info(f"Trace '{trace_id}' transitioned to '{new_state}' state successfully.")
        return log
