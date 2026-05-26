import jwt
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from app.core.config import settings

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
  """
  Creates a signed JWT access token containing claims.
  """
  to_encode = data.copy()
  if expires_delta:
    expire = datetime.utcnow() + expires_delta
  else:
    expire = datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRY_MINUTES)
  
  to_encode.update({"exp": expire})
  encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
  return encoded_jwt

def decode_access_token(token: str) -> Dict[str, Any]:
  """
  Decodes and verifies a JWT token.
  Raises jwt.PyJWTError on validation failure (expired, invalid signature, etc.).
  """
  payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
  return payload
