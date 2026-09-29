from chantrading.adapters.hyperliquid.health import HealthState, StreamHealth
from chantrading.adapters.hyperliquid.reconnect import ReconnectPolicy
from chantrading.adapters.hyperliquid.supervisor import StreamSupervisor


def test_backoff_is_bounded():
    policy = ReconnectPolicy(base_delay_seconds=1, max_delay_seconds=8, jitter_ratio=0)
    assert policy.delay(1) == 1
    assert policy.delay(2) == 2
    assert policy.delay(4) == 8
    assert policy.delay(8) == 8
    assert policy.allowed(8)
    assert not policy.allowed(9)


def test_health_degrades_when_one_signal_is_stale():
    h = StreamHealth()
    h.observe_event(1000)
    h.observe_pong(1000)
    assert h.evaluate(1100, 500, 500) == HealthState.HEALTHY
    assert h.evaluate(1700, 500, 500) == HealthState.STALE


def test_disconnect_forces_resync():
    class WS:
        def mark_resyncing(self): pass

    class Info:
        def clearinghouse_state(self, user): return {}
        def open_orders(self, user): return []
        def user_fills(self, user): return []

    s = StreamSupervisor(WS(), Info())
    s.on_disconnect()
    assert s.status.health == HealthState.RESYNCING
    assert not s.status.ready
