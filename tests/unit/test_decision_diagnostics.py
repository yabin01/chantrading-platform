from chantrading.runtime.decision_diagnostics import collect_decision_diagnostics
from chantrading.runtime.testnet_runtime import TestnetRuntime


def test_collect_decision_diagnostics_is_observational():
    runtime = TestnetRuntime()

    diagnostics = collect_decision_diagnostics(runtime)

    assert diagnostics.decision_count == 0
    assert diagnostics.execution_count == 0
    assert diagnostics.pending_trigger_side is None
    assert diagnostics.pending_trigger_ai_id is None


def test_runtime_snapshot_contains_diagnostics():
    runtime = TestnetRuntime()

    snapshot = runtime.snapshot()

    assert "diagnostics" in snapshot
    assert snapshot["diagnostics"]["decision_count"] == 0
