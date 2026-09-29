from chantrading.runtime.testnet_harness import TestnetRuntimeHarness, RuntimeStatus


def test_runtime_starts_and_records_heartbeat():
    h=TestnetRuntimeHarness()
    h.start()
    h.heartbeat(1000)
    assert h.status is RuntimeStatus.RUNNING
    assert h.metrics.heartbeat_count==1


def test_disconnect_disables_trading_until_recovery():
    h=TestnetRuntimeHarness()
    h.start()
    h.websocket_disconnect()
    assert h.status is RuntimeStatus.DEGRADED
    assert h.trading_enabled is False
    h.websocket_reconnect()
    h.recovery_complete(True)
    assert h.status is RuntimeStatus.RUNNING
    assert h.trading_enabled is True


def test_failed_recovery_halts():
    h=TestnetRuntimeHarness()
    h.start()
    h.websocket_disconnect()
    h.websocket_reconnect()
    h.recovery_complete(False)
    assert h.status is RuntimeStatus.HALTED
    assert h.trading_enabled is False


def test_drift_disables_trading():
    h=TestnetRuntimeHarness()
    h.start()
    h.record_drift()
    assert h.status is RuntimeStatus.RECOVERING
    assert h.trading_enabled is False
