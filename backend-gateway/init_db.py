import asyncio
import sys
import os

# Setup PYTHONPATH to include backend root directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database.db import engine, Base
from app.database.models import *
from app.core.logger import setup_logger
from scripts.seed_billers import seed_from_csv
from loguru import logger

async def initialize_database():
    """
    Create all database tables and seed billers data
    """
    setup_logger()
    
    logger.info("Starting database initialization...")

    # retry-safe DB connection check
    max_retries = 5
    retry_delay = 3
    connected = False
    for attempt in range(1, max_retries + 1):
        try:
            from sqlalchemy import text
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            connected = True
            logger.info("Database connectivity check succeeded.")
            break
        except Exception as e:
            logger.warning(f"Database connection attempt {attempt} failed: {e}. Retrying in {retry_delay}s...")
            await asyncio.sleep(retry_delay)
            retry_delay *= 1.5
    
    if not connected:
        logger.critical("Could not connect to database after several attempts. Exiting.")
        sys.exit(1)
    
    try:
        # Create all tables
        logger.info("Creating database tables...")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully.")
        
        # Seed billers data
        logger.info("Seeding biller data from CSV...")
        csv_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mock_billers_10000.csv")
        await seed_from_csv(csv_file)
        logger.info("Biller data seeded successfully.")
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise
    finally:
        await engine.dispose()

if __name__ == "__main__":
    # Support Windows event loop policy
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(initialize_database())
