from chantrading.runtime.soak_runner import SoakRunConfig, SoakTestRunner


def test_runner_collects_and_finishes():
    r=SoakTestRunner(SoakRunConfig(duration_ms=1000), clock_ms=lambda: 2000)
    r.start(started_at_ms=1000)
    r.record_order(2)
    r.record_fill()
    r.record_reconnect()
    r.record_recovery()
    r.record_watchdog()
    r.set_replay_equivalent(True)
    assert r.should_stop(now_ms=2000)
    report=r.stop(2000)
    assert report.duration_ms==1000
    assert report.orders==2
    assert report.fills==1
    assert report.replay_equivalent is True


def test_runner_rejects_events_after_stop():
    r=SoakTestRunner(SoakRunConfig(duration_ms=1000))
    r.start(100)
    r.stop(1100)
    try:
        r.record_order()
        assert False
    except RuntimeError:
        assert True
