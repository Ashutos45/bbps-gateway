import asyncio
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from app.auth.auth_middleware import require_roles
from app.auth.role_manager import Role
from app.database.db import AsyncSessionLocal
from app.database.models import Biller
from sqlalchemy import select
from loguru import logger

router = APIRouter(prefix="/BOBCOU/BBPS", tags=["Biller Stream API"])

async def biller_csv_generator(sourceid: str, chunk_size: int = 1000):
  """
  Asynchronous generator to query the Biller table in chunks and yield CSV rows.
  Keeps the server RAM footprint near zero for 10,000+ records.
  """
  logger.info(f"Initiated CSV database stream for source channel: {sourceid}")
  
  # Yield CSV Header line
  headers = [
    "biller_id", "biller_name", "category", "region", "state", "city", 
    "support_email", "support_phone", "payment_modes", "minimum_amount", 
    "maximum_amount", "active_status", "provider_latency_ms", "failure_probability", 
    "created_at"
  ]
  yield ",".join(headers) + "\n"

  offset = 0
  records_count = 0
  
  while True:
    async with AsyncSessionLocal() as session:
      stmt = select(Biller).offset(offset).limit(chunk_size)
      res = await session.execute(stmt)
      chunk = res.scalars().all()
      if not chunk:
        break
      
      for biller in chunk:
        meta = biller.biller_metadata or {}
        payment_modes = ";".join(meta.get("payment_modes", []))
        
        row = [
          biller.biller_id,
          biller.biller_name,
          biller.category,
          biller.region,
          meta.get("state", ""),
          meta.get("city", ""),
          meta.get("support_email", ""),
          meta.get("support_phone", ""),
          payment_modes,
          meta.get("min_amount", "0.00"),
          meta.get("max_amount", "0.00"),
          meta.get("active_status", "ACTIVE"),
          str(meta.get("provider_latency_ms", 100)),
          str(meta.get("failure_probability", 0.0)),
          biller.created_at.isoformat() if biller.created_at else ""
        ]
        
        # Simple escape quotes for names containing commas
        row_escaped = []
        for val in row:
          val_str = str(val)
          if "," in val_str or '"' in val_str:
            val_str = '"' + val_str.replace('"', '""') + '"'
          row_escaped.append(val_str)
          
        yield ",".join(row_escaped) + "\n"
        records_count += 1
        
    offset += chunk_size
    # Yield control to prevent event loop starvation
    await asyncio.sleep(0.01)
    
  logger.info(f"Database stream completed for channel {sourceid}. Streamed {records_count} records.")

@router.get("/{sourceid}/billpay/billers/stream")
async def stream_biller_dataset(
  sourceid: str,
  request: Request,
  user: dict = Depends(require_roles([Role.CLIENT, Role.ADMIN]))
):
  """
  Streams the entire 10,000+ records of the Biller master file directly from PostgreSQL database.
  Requires role authorization (CLIENT or ADMIN). Uses chunked, iterator-based HTTP streaming.
  """
  return StreamingResponse(
    biller_csv_generator(sourceid),
    media_type="text/csv",
    headers={
      "Content-Disposition": "attachment; filename=billers_stream.csv"
    }
  )
