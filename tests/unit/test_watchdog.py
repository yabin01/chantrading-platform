from chantrading.runtime.watchdog import (
    BackoffPolicy, RuntimeEventType, RuntimeWatchdog,
)


def test_heartbeat_timeout_freezes():
    w=RuntimeWatchdog(heartbeat_timeout_ms=100)
    e=w.check_heartbeat(250,100)
    assert e.type is RuntimeEventType.HEARTBEAT_MISSED
    assert w.frozen


def test_backoff_is_bounded():
    p=BackoffPolicy(1000,5000)
    assert [p.delay(i) for i in range(6)]==[1000,2000,4000,5000,5000,5000]


def test_reconnect_attempts_are_bounded():
    w=RuntimeWatchdog(max_reconnect_attempts=2)
    w.schedule_reconnect(0)
    w.schedule_reconnect(1)
    e=w.schedule_reconnect(2)
    assert e.type is RuntimeEventType.WATCHDOG_HALTED
    assert w.halted


def test_recovery_timeout_freezes():
    w=RuntimeWatchdog(recovery_timeout_ms=100)
    e=w.check_recovery(250,100)
    assert e.type is RuntimeEventType.RECOVERY_TIMEOUT
    assert w.frozen
