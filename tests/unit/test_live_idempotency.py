from dataclasses import dataclass

from chantrading.runtime.live_recording import Live1MRecordedRuntime


@dataclass(frozen=True)
class C:
    coin: str = "ETH"
    interval: str = "1m"
    timestamp_ms: int = 60_000
    open: str = "9"
    high: str = "10"
    low: str = "8"
    close: str = "9"
    volume: str = "1"


def test_runtime_drops_an_old_accepted_candle_after_newer_candles(tmp_path):
    runtime = Live1MRecordedRuntime(str(tmp_path / "events.db"))
    try:
        runtime.on_candle(C())
        runtime.on_candle(C(timestamp_ms=120_000))
        runtime.on_candle(C(timestamp_ms=180_000))

        decision = runtime.classify_candle(C())

        assert decision.action == "DROP_DUPLICATE"
        assert decision.reason == "accepted_identity_already_seen"
        assert runtime.resync_required is False
    finally:
        runtime.close()


def test_duplicate_does_not_mutate_structure(tmp_path):
    runtime = Live1MRecordedRuntime(str(tmp_path / "events.db"))
    try:
        runtime.on_candle(C())
        before = runtime.engine.snapshot()
        runtime.on_candle(C())
        after = runtime.engine.snapshot()

        assert before == after
    finally:
        runtime.close()


def test_repeated_recovery_candle_is_idempotent(tmp_path):
    runtime = Live1MRecordedRuntime(str(tmp_path / "events.db"))
    try:
        runtime.on_candle(C())
        runtime.on_disconnect()
        runtime.on_reconnect()
        runtime.recover([C(timestamp_ms=120_000)])

        before = runtime.engine.snapshot()
        decision = runtime.classify_candle(C(timestamp_ms=120_000))

        assert decision.action == "DROP_DUPLICATE"
        assert runtime.engine.snapshot() == before
    finally:
        runtime.close()
