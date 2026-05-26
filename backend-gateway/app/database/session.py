from contextlib import asynccontextmanager
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.db import AsyncSessionLocal
from loguru import logger

@asynccontextmanager
async def transactional_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Provide a transactional scope around a series of operations.
    Begins an async transaction block. Commits automatically on exit
    of the block, or rolls back if an exception occurs.
    """
    async with AsyncSessionLocal() as session:
        try:
            # session.begin() will start a transaction and automatically
            # commit it when the block exits, or rollback on exception
            async with session.begin():
                yield session
        except Exception as e:
            logger.error(f"Transaction block failed, transaction rolled back. Error: {e}")
            raise
        finally:
            await session.close()
