from datetime import datetime
import re

TIMESTAMP_FORMAT = "%Y%m%d%H%M%S"

def get_current_timestamp() -> str:
    """
    Generate a current timestamp in the format: yyyymmddhh24miss (e.g. 20160528121320).
    """
    return datetime.utcnow().strftime(TIMESTAMP_FORMAT)

def validate_timestamp(timestamp_str: str) -> bool:
    """
    Validates if a timestamp matches the format yyyymmddhh24miss and represents a valid date/time.
    """
    if not re.match(r"^\d{14}$", timestamp_str):
        return False
    try:
        datetime.strptime(timestamp_str, TIMESTAMP_FORMAT)
        return True
    except ValueError:
        return False

def parse_timestamp(timestamp_str: str) -> datetime:
    """
    Parses a yyyymmddhh24miss string into a python datetime object.
    """
    return datetime.strptime(timestamp_str, TIMESTAMP_FORMAT)

def format_timestamp(dt: datetime) -> str:
    """
    Formats a datetime object to yyyymmddhh24miss format.
    """
    return dt.strftime(TIMESTAMP_FORMAT)
