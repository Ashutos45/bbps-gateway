import pytest
from app.core.state_machine import validate_state_transition
from app.core.exceptions import TransactionFailedError
from app.core.constants import TransactionState

def test_valid_state_transitions():
    """
    Asserts that valid state transition pathways execute without raising errors.
    """
    # INITIALIZED -> PENDING_SUBMISSION -> NETWORK_IN_FLIGHT -> SETTLED (Terminal)
    validate_state_transition(TransactionState.INITIALIZED, TransactionState.PENDING_SUBMISSION)
    validate_state_transition(TransactionState.PENDING_SUBMISSION, TransactionState.NETWORK_IN_FLIGHT)
    validate_state_transition(TransactionState.NETWORK_IN_FLIGHT, TransactionState.SETTLED)
    
    # NETWORK_IN_FLIGHT -> AMBIGUOUS_TIMEOUT -> FAILED (Terminal)
    validate_state_transition(TransactionState.NETWORK_IN_FLIGHT, TransactionState.AMBIGUOUS_TIMEOUT)
    validate_state_transition(TransactionState.AMBIGUOUS_TIMEOUT, TransactionState.FAILED)

def test_invalid_state_transitions():
    """
    Asserts that invalid state transition attempts correctly raise TransactionFailedError.
    """
    # 1. Cannot skip states (e.g. from INITIALIZED straight to SETTLED)
    with pytest.raises(TransactionFailedError):
        validate_state_transition(TransactionState.INITIALIZED, TransactionState.SETTLED)

    # 2. Cannot transition out of terminal state SETTLED
    with pytest.raises(TransactionFailedError):
        validate_state_transition(TransactionState.SETTLED, TransactionState.INITIALIZED)

    # 3. Cannot transition out of terminal state FAILED
    with pytest.raises(TransactionFailedError):
        validate_state_transition(TransactionState.FAILED, TransactionState.NETWORK_IN_FLIGHT)

    # 4. Cannot skip from PENDING_SUBMISSION to AMBIGUOUS_TIMEOUT
    with pytest.raises(TransactionFailedError):
        validate_state_transition(TransactionState.PENDING_SUBMISSION, TransactionState.AMBIGUOUS_TIMEOUT)
