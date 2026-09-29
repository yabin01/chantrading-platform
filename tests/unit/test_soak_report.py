import json
from chantrading.runtime.soak_report import SoakTestRecorder


def test_soak_report_is_deterministic_and_machine_readable():
    r=SoakTestRecorder(1000)
    r.order(2)
    r.fill()
    r.reconnect()
    r.recovery()
    r.drift()
    r.watchdog()
    r.set_replay_equivalent(True)
    m=r.finish(6000)
    assert m.duration_ms==5000
    payload=json.loads(m.to_json())
    assert payload["orders"]==2
    assert payload["fills"]==1
    assert payload["replay_equivalent"] is True
    assert payload["duration_ms"]==5000


def test_open_run_has_no_duration():
    r=SoakTestRecorder(1000)
    assert r.metrics.duration_ms is None
