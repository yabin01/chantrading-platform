import json
from chantrading.runtime.soak_runtime import SoakRuntime
from chantrading.runtime.soak_runner import SoakRunConfig


def test_runtime_wires_events_to_report():
    runtime=SoakRuntime(SoakRunConfig(duration_ms=1000))
    runtime.start(100)
    runtime.publish("ORDER_ACCEPTED", 110)
    runtime.publish("FILL_CONFIRMED", 120)
    runtime.publish("WS_RECONNECTED", 130)
    runtime.publish("RECOVERY_COMPLETED", 140)
    runtime.publish("WATCHDOG_EVENT", 150)
    runtime.publish("RECONCILIATION_DRIFT", 160)
    runtime.set_replay_equivalent(True)
    report=json.loads(runtime.export_json(1100))
    assert report["orders"]==1
    assert report["fills"]==1
    assert report["reconnects"]==1
    assert report["recoveries"]==1
    assert report["watchdog_events"]==1
    assert report["drift_events"]==1
    assert report["replay_equivalent"] is True
