"""Tests for the transport-agnostic live recovery state machine."""
from chantrading.runtime.recovery import RecoveryState, RecoveryStateMachine


def test_recovery_state_machine_happy_path():
    machine = RecoveryStateMachine()

    assert machine.state is RecoveryState.HEALTHY
    assert machine.transition(RecoveryState.GAP_DETECTED) is RecoveryState.GAP_DETECTED
    assert machine.transition(RecoveryState.WAITING_RECONNECT) is RecoveryState.WAITING_RECONNECT
    assert machine.transition(RecoveryState.RECOVERING) is RecoveryState.RECOVERING
    assert machine.transition(RecoveryState.VERIFYING) is RecoveryState.VERIFYING
    assert machine.transition(RecoveryState.RECOVERED) is RecoveryState.RECOVERED
    assert machine.reset() is RecoveryState.HEALTHY


def test_recovery_state_machine_rejects_invalid_transition():
    machine = RecoveryStateMachine()

    try:
        machine.transition(RecoveryState.RECOVERING)
    except ValueError as exc:
        assert "invalid recovery transition" in str(exc)
    else:
        raise AssertionError("invalid recovery transition was accepted")


def test_recovery_state_machine_can_retry_after_verification_failure():
    machine = RecoveryStateMachine()
    machine.transition(RecoveryState.GAP_DETECTED)
    machine.transition(RecoveryState.WAITING_RECONNECT)
    machine.transition(RecoveryState.RECOVERING)
    machine.transition(RecoveryState.VERIFYING)

    assert machine.transition(RecoveryState.GAP_DETECTED) is RecoveryState.GAP_DETECTED
