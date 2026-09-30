from chantrading.adapters.hyperliquid.live_testnet import LiveCandle
from chantrading.runtime.deterministic_replay import DeterministicRecorder, DeterministicReplay, events_hash

def candle(ts, high, low, close):
    return LiveCandle(coin="ETH", interval="1m", timestamp_ms=ts, open=str(close),
        high=str(high), low=str(low), close=str(close), volume="1")

def sequence():
    return [candle(1,10,8,9), candle(2,11,9,10), candle(3,7,5,6),
            candle(4,6,4,5), candle(5,12,8,11), candle(6,8,5,7)]

def test_recorder_assigns_contiguous_sequences():
    r=DeterministicRecorder()
    a,b=r.record(sequence()[0]),r.record(sequence()[1])
    assert (a.sequence,b.sequence)==(1,2)

def test_recorder_rejects_duplicate_or_out_of_order_timestamp():
    r=DeterministicRecorder(); r.record(sequence()[1])
    try:
        r.record(sequence()[0]); assert False
    except ValueError:
        assert True

def test_replay_produces_stable_event_hash_and_snapshot():
    replay=DeterministicReplay(); a=replay.replay_live(sequence()); b=replay.replay_live(sequence())
    assert a.state_hash==b.state_hash
    assert a.snapshot==b.snapshot
    assert a.events==b.events

def test_event_hash_changes_when_event_payload_changes():
    result=DeterministicReplay().replay_live(sequence())
    altered=list(result.events); first=altered[0]
    altered[0]=type(first)(first.type,first.timestamp_ms,{"coin":"BTC","interval":"1m"})
    assert events_hash(altered)!=result.state_hash

def test_replay_does_not_mutate_recorded_candles():
    r=DeterministicRecorder()
    for c in sequence(): r.record(c)
    before=r.candles(); DeterministicReplay().replay(before)
    assert r.candles()==before
