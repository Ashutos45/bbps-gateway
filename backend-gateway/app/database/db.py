from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.core.config import settings
from loguru import logger

# Base class for SQLAlchemy models
Base = declarative_base()

DATABASE_URL = settings.async_database_url

logger.info(f"Configuring Async PostgreSQL engine with URL scheme: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else DATABASE_URL}")

# Create Async Engine with Connection Pooling
engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # Set to True for verbose SQL output in debugging
    pool_size=10,
    max_overflow=20,
    pool_recycle=1800,  # Recycle connections after 30 minutes
    pool_pre_ping=True   # Check connection health before checkout
)

# Async Session Factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

async def get_db():
    """
    FastAPI dependency that yields an asynchronous database session.
    Automatically handles rollback on exceptions and final session cleanup.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            logger.error(f"Database session encountered exception: {e}. Rolling back transaction.")
            await session.rollback()
            raise
        finally:
            await session.close()
