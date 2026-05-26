import jwt
from datetime import datetime, timedelta
from app.core.config import settings

def generate_signed_download_token(file_id: str, client_id: str, expires_in_sec: int = 300) -> str:
  """
  Generates a short-lived cryptographic download token using JWT.
  URL signatures expire automatically after expires_in_sec (default 5 minutes).
  """
  payload = {
    "file_id": file_id,
    "client_id": client_id,
    "exp": datetime.utcnow() + timedelta(seconds=expires_in_sec)
  }
  return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

def verify_download_token(token: str, expected_file_id: str) -> bool:
  """
  Decodes and verifies the download token signature and expiry.
  Verifies that the token corresponds to the requested file_id.
  """
  try:
    payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    if payload.get("file_id") != expected_file_id:
      return False
    return True
  except jwt.PyJWTError:
    return False
