import os
import sys
import csv
import asyncio
import time
from datetime import datetime

# Setup PYTHONPATH to include backend root directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.db import AsyncSessionLocal, engine
from app.database.models import Biller
from sqlalchemy.dialects.postgresql import insert
from loguru import logger

async def seed_from_csv(csv_path: str, chunk_size: int = 1000):
  """
  Reads the mock billers CSV in chunks and inserts them asynchronously in PostgreSQL.
  """
  if not os.path.exists(csv_path):
    logger.error(f"Seeding source CSV not found: {csv_path}")
    return

  logger.info(f"Starting bulk seeding from CSV: {csv_path}")
  start_time = time.time()
  
  records_processed = 0
  
  try:
    with open(csv_path, "r", encoding="utf-8") as f:
      reader = csv.DictReader(f)
      
      chunk = []
      
      for row in reader:
        # Construct metadata dictionary containing extra attributes
        metadata = {
          "state": row["state"],
          "city": row["city"],
          "support_email": row["support_email"],
          "support_phone": row["support_phone"],
          "payment_modes": row["payment_modes"].split(";"),
          "min_amount": row["minimum_amount"],
          "max_amount": row["maximum_amount"],
          "active_status": row["active_status"],
          "provider_latency_ms": int(row["provider_latency_ms"]),
          "failure_probability": float(row["failure_probability"])
        }
        
        # Parse created_at
        created_at_dt = datetime.fromisoformat(row["created_at"].replace("Z", "+00:00"))
        
        biller_data = {
          "biller_id": row["biller_id"],
          "biller_name": row["biller_name"],
          "category": row["category"],
          "region": row["region"],
          "biller_metadata": metadata,
          "created_at": created_at_dt
        }
        
        chunk.append(biller_data)
        
        if len(chunk) >= chunk_size:
          await insert_chunk(chunk)
          records_processed += len(chunk)
          logger.info(f"Inserted {records_processed} records...")
          chunk = []
          # Yield control to event loop
          await asyncio.sleep(0.01)
          
      # Insert remaining records
      if chunk:
        await insert_chunk(chunk)
        records_processed += len(chunk)
        logger.info(f"Inserted remaining {len(chunk)} records.")
        
    duration = time.time() - start_time
    logger.info(f"Seeding completed. Total records loaded: {records_processed}. Duration: {duration:.2f} seconds.")
    
  except Exception as e:
    logger.exception(f"Fatal error during database seeding: {e}")

async def insert_chunk(chunk_data: list):
  """
  Performs insert with ON CONFLICT DO NOTHING to avoid duplicate key errors.
  """
  async with AsyncSessionLocal() as session:
    async with session.begin():
      stmt = insert(Biller).values(chunk_data)
      stmt = stmt.on_conflict_do_nothing(index_elements=["biller_id"])
      await session.execute(stmt)

async def main():
  csv_file = os.environ.get("SEED_CSV_PATH", "mock_billers_10000.csv")
  # Look in scripts or root depending on run location
  if not os.path.exists(csv_file):
    csv_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "mock_billers_10000.csv")
    
  await seed_from_csv(csv_file)
  await engine.dispose()

if __name__ == "__main__":
  # Support Windows event loop policy
  if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
  asyncio.run(main())
