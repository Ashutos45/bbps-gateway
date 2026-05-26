from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database.models import NonceRegistry
from loguru import logger
import uuid

class NonceRepository:
    """
    Repository class to persist and query request nonces for replay attack prevention.
    """
    
    @staticmethod
    async def is_nonce_used(session: AsyncSession, nonce: str) -> bool:
        """
        Queries if the nonce exists in the database.
        """
        stmt = select(NonceRegistry).filter_by(nonce=nonce)
        result = await session.execute(stmt)
        return result.scalar_one_or_none() is not None

    @staticmethod
    async def add_nonce(session: AsyncSession, nonce: str, source_id: str) -> None:
        """
        Inserts a new nonce record in the database.
        """
        nonce_record = NonceRegistry(
            id=uuid.uuid4(),
            nonce=nonce,
            source_id=source_id
        )
        session.add(nonce_record)
        await session.flush()
        logger.debug(f"Nonce '{nonce}' successfully registered in database.")
