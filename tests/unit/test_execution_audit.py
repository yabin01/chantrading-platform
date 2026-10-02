from chantrading.runtime.execution_audit import ExecutionAuditRecord, ExecutionAuditTrail


def test_execution_audit_trail_snapshot():
    trail = ExecutionAuditTrail()
    trail.append(
        ExecutionAuditRecord(
            signal_id="SIG-1",
            intent_id="OI-1",
            status="FILLED",
            venue_order_id="123",
        )
    )

    snapshot = trail.snapshot()

    assert snapshot["count"] == 1
    assert snapshot["latest"]["signal_id"] == "SIG-1"
