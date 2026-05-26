from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database.models import PaymentIdempotency
from app.core.exceptions import IdempotencyViolationError
from loguru import logger
import uuid

class IdempotencyEngine:
    """
    Idempotency Protection Engine for processing payment requests concurrently.
    Uses PostgreSQL SELECT FOR UPDATE locks to avoid race conditions.
    """
    
    @staticmethod
    async def acquire_lock(
        session: AsyncSession,
        idempotency_key: str,
        payment_reference: str
    ) -> PaymentIdempotency:
        """
        Attempts to register and lock the idempotency key:
        1. Queries the payment_idempotency table with WITH_FOR_UPDATE row-locking.
        2. If no record is found: Inserts a new record in 'PENDING' status.
        3. If a record is found and is 'PENDING': Raises IdempotencyViolationError (in-flight transaction).
        4. If a record is found and is 'SUCCESS' or 'FAILED': Returns the record to allow cached response retrieval.
        """
        logger.info(f"Attempting to acquire idempotency lock for key: {idempotency_key}")
        
        # Execute query using SELECT FOR UPDATE locking
        stmt = (
            select(PaymentIdempotency)
            .filter_by(idempotency_key=idempotency_key)
            .with_for_update()
        )
        result = await session.execute(stmt)
        record = result.scalar_one_or_none()
        
        if record is None:
            # Key does not exist, safe to insert as PENDING
            logger.info(f"No existing record. Registering new key '{idempotency_key}' in PENDING state.")
            record = PaymentIdempotency(
                id=uuid.uuid4(),
                idempotency_key=idempotency_key,
                payment_reference=payment_reference,
                transaction_status="PENDING"
            )
            session.add(record)
            # Flush changes to acquire database lock and trigger unique constraints checks
            await session.flush()
            return record
            
        # Key exists. Verify status
        if record.transaction_status == "PENDING":
            logger.warning(f"Conflict: Transaction for key '{idempotency_key}' is already in progress.")
            raise IdempotencyViolationError(
                f"A transaction for key '{idempotency_key}' is already in progress."
            )
            
        logger.info(f"Existing transaction found for key '{idempotency_key}' in state '{record.transaction_status}'.")
        return record

    @staticmethod
    async def update_status(
        session: AsyncSession,
        idempotency_key: str,
        new_status: str
    ) -> None:
        """
        Updates the state of an existing idempotency lock (e.g. from PENDING to SUCCESS or FAILED).
        """
        stmt = (
            select(PaymentIdempotency)
            .filter_by(idempotency_key=idempotency_key)
            .with_for_update()
        )
        result = await session.execute(stmt)
        record = result.scalar_one_or_none()
        
        if record:
            record.transaction_status = new_status
            await session.flush()
            logger.info(f"Idempotency key '{idempotency_key}' updated to status '{new_status}'.")
        else:
            logger.error(f"Idempotency key '{idempotency_key}' not found for status update.")
