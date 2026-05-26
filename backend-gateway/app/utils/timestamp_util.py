import time
from datetime import datetime, timezone
from typing import Union

TIMESTAMP_FORMAT = "%Y%m%d%H%M%S"

def get_current_unix_timestamp() -> int:
    """
    Returns the current UNIX epoch timestamp in seconds.
    """
    return int(time.time())

def get_current_bob_timestamp() -> str:
    """
    Generates a timestamp in Bank of Baroda format: yyyymmddhh24miss.
    """
    return datetime.now(timezone.utc).strftime(TIMESTAMP_FORMAT)

def convert_unix_to_bob_timestamp(unix_ts: Union[int, str]) -> str:
    """
    Converts a UNIX epoch timestamp (seconds) into the Bank of Baroda format.
    """
    dt = datetime.fromtimestamp(int(unix_ts), tz=timezone.utc)
    return dt.strftime(TIMESTAMP_FORMAT)

def is_timestamp_valid(unix_ts: Union[int, str], window_seconds: int = 300) -> bool:
    """
    Validates if the provided UNIX timestamp is within the acceptable window
    compared to the current server time to prevent replay attacks.
    """
    try:
        ts = int(unix_ts)
        current = int(time.time())
        return abs(current - ts) <= window_seconds
    except (ValueError, TypeError):
        return False
