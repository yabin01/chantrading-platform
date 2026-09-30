from chantrading.adapters.hyperliquid.live_testnet import LiveCandle
from chantrading.runtime.live_recording import Live1MRecordedRuntime


def c(ts, high="10", low="8", close="9"):
    return LiveCandle("ETH", "1m", ts, close, high, low, close, "1")


def test_live_recording_replay_matches_live(tmp_path):
    with Live1MRecordedRuntime(tmp_path / "runtime.db") as runtime:
        for item in [
            c(1),
            c(60_001, "11", "9", "10"),
            c(120_001, "7", "5", "6"),
            c(180_001, "6", "4", "5"),
            c(240_001, "12", "8", "11"),
        ]:
            runtime.on_candle(item)
        result = runtime.verification()
        assert result.matched
        assert result.candle_count == 5


def test_duplicate_candle_is_not_forwarded_to_engine(tmp_path):
    with Live1MRecordedRuntime(tmp_path / "runtime.db") as runtime:
        first = c(1)
        runtime.on_candle(first)
        runtime.on_candle(first)
        assert runtime.engine.candles_processed == 1
        recovery = [row for row in runtime.store.iter_events() if row.name == "CANDLE_RECOVERY"]
        assert recovery[-1].payload["action"] == "DROP_DUPLICATE"


def test_gap_requires_resync_and_is_not_forwarded(tmp_path):
    with Live1MRecordedRuntime(tmp_path / "runtime.db") as runtime:
        runtime.on_candle(c(1))
        runtime.on_candle(c(120_001))
        assert runtime.resync_required
        assert runtime.engine.candles_processed == 1
        recovery = [row for row in runtime.store.iter_events() if row.name == "CANDLE_RECOVERY"]
        assert recovery[-1].payload["reason"] == "timestamp_gap"


def test_out_of_order_requires_resync(tmp_path):
    with Live1MRecordedRuntime(tmp_path / "runtime.db") as runtime:
        runtime.on_candle(c(1))
        runtime.on_candle(c(60_001))
        runtime.on_candle(c(1))
        assert runtime.resync_required
        assert runtime.engine.candles_processed == 2
        recovery = [row for row in runtime.store.iter_events() if row.name == "CANDLE_RECOVERY"]
        assert recovery[-1].payload["reason"] == "out_of_order_timestamp"


def test_conflicting_duplicate_requires_resync(tmp_path):
    with Live1MRecordedRuntime(tmp_path / "runtime.db") as runtime:
        runtime.on_candle(c(1))
        runtime.on_candle(c(1, high="11"))
        assert runtime.resync_required
        assert runtime.engine.candles_processed == 1
        recovery = [row for row in runtime.store.iter_events() if row.name == "CANDLE_RECOVERY"]
        assert recovery[-1].payload["reason"] == "conflicting_duplicate_timestamp"


def test_disconnect_reconnect_requires_fresh_contiguous_candle(tmp_path):
    with Live1MRecordedRuntime(tmp_path / "runtime.db") as runtime:
        runtime.on_candle(c(1))
        runtime.on_disconnect("socket_closed")
        assert runtime.resync_required
        runtime.on_reconnect()
        assert runtime.connection_generation == 1
        runtime.on_candle(c(60_001))
        assert not runtime.resync_required
        names = [row.name for row in runtime.store.iter_events()]
        assert names == [
            "CANDLE_ACCEPTED",
            "WS_DISCONNECTED",
            "WS_RECONNECTED",
            "CANDLE_ACCEPTED",
        ]


def test_live_recording_keeps_structural_events_separate_from_candles(tmp_path):
    with Live1MRecordedRuntime(tmp_path / "runtime.db") as runtime:
        runtime.on_candle(c(1))
        names = [row.name for row in runtime.store.iter_events()]
        assert names[0] == "CANDLE_ACCEPTED"
        assert all(name != "CANDLE_ACCEPTED" for name in names[1:])
