import json
from typing import Optional
from app.core.config import settings

def validate_api_key(api_key: str) -> Optional[str]:
  """
  Validates the provided API key against configured key-role maps.
  Returns the associated role string if valid, otherwise None.
  """
  if not api_key:
    return None
  try:
    api_keys_map = json.loads(settings.API_KEYS_JSON)
    # Perform case-sensitive lookup
    if api_key in api_keys_map:
      return api_keys_map[api_key]
  except Exception:
    pass
  return None
