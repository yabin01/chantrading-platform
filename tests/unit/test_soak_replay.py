from chantrading.adapters.hyperliquid.live_testnet import LiveCandle
from chantrading.runtime.soak_replay import SQLiteCandleRecorder

def candle(ts, high=10, low=8, close=9):
    return LiveCandle("ETH","1m",ts,str(close),str(high),str(low),str(close),"1")

def test_sqlite_recording_and_replay_are_deterministic(tmp_path):
    with SQLiteCandleRecorder(tmp_path/"events.db") as recorder:
        for c in [candle(1), candle(2,11,9,10), candle(3,7,5,6), candle(4,6,4,5), candle(5,12,8,11)]:
            assert recorder.append(c) is not None
        verification = recorder.verify_replay()
        assert verification.accepted_candles == 5
        assert verification.recorded_events == 5
        assert verification.replay.state_hash

def test_sqlite_candle_recording_is_idempotent(tmp_path):
    with SQLiteCandleRecorder(tmp_path/"events.db") as recorder:
        c=candle(1)
        assert recorder.append(c) is not None
        assert recorder.append(c) is None
        assert recorder.store.count() == 1

def test_sqlite_recorder_rejects_non_1m(tmp_path):
    with SQLiteCandleRecorder(tmp_path/"events.db") as recorder:
        c=LiveCandle("ETH","5m",1,"9","10","8","9","1")
        try:
            recorder.append(c)
            assert False
        except ValueError:
            assert True
