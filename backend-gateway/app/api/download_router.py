import os
from fastapi import APIRouter, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from app.auth.token_service import verify_download_token
from app.auth.auth_middleware import record_security_metric
from loguru import logger

router = APIRouter(prefix="/download", tags=["Biller Master Download"])

BILLER_DIR = "biller_list"

def file_chunk_generator(file_path: str, chunk_size: int = 8192):
  """
  Helper generator to read a file on disk chunk-by-chunk for low-memory streaming.
  """
  try:
    with open(file_path, "rb") as f:
      while True:
        chunk = f.read(chunk_size)
        if not chunk:
          break
        yield chunk
  except Exception as e:
    logger.error(f"Error during file streaming: {e}")
    raise HTTPException(
      status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
      detail="Error occurred during file download streaming"
    )

@router.get("/file/{fileid}")
async def download_zipped_biller_file(
  fileid: str,
  token: str = Query(..., description="Short-lived cryptographic URL signature token")
):
  """
  Exposes tokenized secure downloads for compiled biller master files.
  Requires URL signature verification. Streams the zipped archive to prevent high RAM allocation.
  """
  # 1. Cryptographically verify the signed temporary download token
  is_valid = verify_download_token(token, fileid)
  if not is_valid:
    logger.warning(f"Unauthorized or expired download token access attempt. Token: {token}, File: {fileid}")
    # Record telemetry for unauthorized / expired token usage
    record_security_metric("expired_token")
    raise HTTPException(
      status_code=status.HTTP_401_UNAUTHORIZED,
      detail="Unauthorized or expired signed URL token."
    )

  # 2. Audit successful authenticated download telemetry
  record_security_metric("download_audit")
  
  zip_path = os.path.join(BILLER_DIR, f"{fileid}.zip")
  if not os.path.exists(zip_path):
    logger.warning(f"File not found on gateway disk: {zip_path}")
    raise HTTPException(
      status_code=status.HTTP_404_NOT_FOUND,
      detail=f"Biller master archive '{fileid}' not found."
    )

  # 3. Stream ZIP file content safely in 8KB chunks
  file_size = os.path.getsize(zip_path)
  logger.info(f"Audited download of archive {fileid}.zip. Size: {file_size} bytes. Streaming started...")
  
  return StreamingResponse(
    file_chunk_generator(zip_path),
    media_type="application/zip",
    headers={
      "Content-Disposition": f"attachment; filename={fileid}.zip",
      "Content-Length": str(file_size)
    }
  )
