import uuid
import re

TRACE_ID_REGEX = re.compile(r"^[a-zA-Z0-9]{1,30}$")

def generate_trace_id() -> str:
    """
    Generates a unique, alphanumeric trace ID of length 24.
    Uses uuid4 hex representation stripped of dashes.
    """
    return uuid.uuid4().hex[:24]

def is_valid_trace_id(trace_id: str) -> bool:
    """
    Validates if a trace ID is alphanumeric, without spaces or special characters,
    and has a length between 1 and 30 characters.
    """
    if not trace_id:
        return False
    return bool(TRACE_ID_REGEX.match(trace_id))
