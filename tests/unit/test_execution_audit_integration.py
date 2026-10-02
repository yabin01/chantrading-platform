from types import SimpleNamespace

from chantrading.runtime.execution_audit import ExecutionAuditRecord
from chantrading.runtime.testnet_runtime import TestnetRuntime


def test_runtime_snapshot_exposes_audit_trail():
    runtime = TestnetRuntime()
    runtime.execution_audit.append(
        ExecutionAuditRecord(
            signal_id="SIG-1",
            intent_id="OI-1",
            status="FILLED",
            venue_order_id="123",
        )
    )

    snapshot = runtime.snapshot()

    assert snapshot["audit"]["count"] == 1
    assert snapshot["audit"]["latest"]["intent_id"] == "OI-1"
