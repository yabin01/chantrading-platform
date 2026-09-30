from chantrading.adapters.hyperliquid.live_testnet import LiveCandle
from chantrading.runtime.live_recording import Live1MRecordedRuntime

def c(ts, high="10", low="8", close="9"):
    return LiveCandle("ETH","1m",ts,close,high,low,close,"1")

def test_live_recording_replay_matches_live(tmp_path):
    with Live1MRecordedRuntime(tmp_path/"runtime.db") as runtime:
        for item in [c(1), c(2,"11","9","10"), c(3,"7","5","6"), c(4,"6","4","5"), c(5,"12","8","11")]:
            runtime.on_candle(item)
        result = runtime.verification()
        assert result.matched
        assert result.candle_count == 5

def test_live_recording_keeps_structural_events_separate_from_candles(tmp_path):
    with Live1MRecordedRuntime(tmp_path/"runtime.db") as runtime:
        runtime.on_candle(c(1))
        names = [row.name for row in runtime.store.iter_events()]
        assert names[0] == "CANDLE_ACCEPTED"
        assert all(name != "CANDLE_ACCEPTED" for name in names[1:])
