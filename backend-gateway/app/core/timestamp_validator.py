from app.utils.timestamp_util import is_timestamp_valid
from app.core.exceptions import InvalidTimestampError
from loguru import logger

def validate_request_timestamp(timestamp_str: str, window_seconds: int = 300) -> None:
    """
    Validates the incoming X-Timestamp.
    Raises InvalidTimestampError if the timestamp is missing, invalid, or outside
    the acceptable time skew window (300 seconds).
    """
    if not timestamp_str:
        logger.warning("X-Timestamp header is missing.")
        raise InvalidTimestampError("X-Timestamp header is missing.")

    if not is_timestamp_valid(timestamp_str, window_seconds):
        logger.warning(f"X-Timestamp validation failed for timestamp: {timestamp_str}")
        raise InvalidTimestampError(
            f"X-Timestamp skew is excessive. Request must be within {window_seconds} seconds of server time."
        )
