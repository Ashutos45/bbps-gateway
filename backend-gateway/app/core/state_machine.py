from app.core.constants import TransactionState
from app.core.exceptions import TransactionFailedError
from loguru import logger

# Defined transition matrix
ALLOWED_TRANSITIONS = {
    TransactionState.INITIALIZED: [TransactionState.PENDING_SUBMISSION, TransactionState.PENDING_RETRY, TransactionState.FAILED],
    TransactionState.PENDING_SUBMISSION: [TransactionState.NETWORK_IN_FLIGHT, TransactionState.PENDING_RETRY, TransactionState.FAILED],
    TransactionState.NETWORK_IN_FLIGHT: [TransactionState.AMBIGUOUS_TIMEOUT, TransactionState.PENDING_RETRY, TransactionState.SETTLED, TransactionState.FAILED],
    TransactionState.AMBIGUOUS_TIMEOUT: [TransactionState.SETTLED, TransactionState.PENDING_RETRY, TransactionState.FAILED, TransactionState.FAILED_DLQ],
    TransactionState.PENDING_RETRY: [TransactionState.PENDING_SUBMISSION, TransactionState.NETWORK_IN_FLIGHT, TransactionState.SETTLED, TransactionState.FAILED, TransactionState.FAILED_DLQ],
    TransactionState.SETTLED: [],  # Terminal state
    TransactionState.FAILED: [],   # Terminal state
    TransactionState.FAILED_DLQ: [],  # Terminal state
}

def validate_state_transition(current_state: str, new_state: str) -> None:
    """
    Asserts if a transaction transition from current_state to new_state is allowed.
    Raises TransactionFailedError if the transition is illegal.
    """
    if current_state == new_state:
        return

    allowed = ALLOWED_TRANSITIONS.get(current_state, [])
    if new_state not in allowed:
        logger.error(f"Illegal state transition transition attempted: {current_state} -> {new_state}")
        raise TransactionFailedError(
            f"Invalid transaction state transition: Cannot transition from '{current_state}' to '{new_state}'"
        )
        
    logger.info(f"Transaction state transition validated: {current_state} -> {new_state}")
