from dataclasses import replace
from chantrading.adapters.hyperliquid.market_event import to_canonical_event
from chantrading.adapters.hyperliquid.ws_market_data import CandleEvent
from chantrading.state.replay_store import DeterministicEventStore, replay_events


def candle(ts):
    return CandleEvent("ETH","1m",ts,"2000","2010","1990","2005","10")


def test_append_assigns_monotonic_sequence():
    s=DeterministicEventStore()
    a=s.append(to_canonical_event(candle(60_000)))
    b=s.append(to_canonical_event(candle(120_000)))
    assert (a.sequence,b.sequence)==(0,1)


def test_duplicate_append_is_rejected():
    s=DeterministicEventStore()
    e=to_canonical_event(candle(60_000))
    s.append(e)
    try:
        s.append(e)
        assert False
    except ValueError:
        pass


def test_replay_is_deterministic():
    s=DeterministicEventStore()
    s.append(to_canonical_event(candle(60_000)))
    s.append(to_canonical_event(candle(120_000)))
    reducer=lambda state,event: state + 1
    assert s.replay(reducer,0)==2
    assert s.replay(reducer,0)==2


def test_live_and_replay_equivalent():
    events=[to_canonical_event(candle(60_000)),to_canonical_event(candle(120_000))]
    reducer=lambda state,event: state + (int(event.close) - 2000)
    live=0
    for e in events:
        live=reducer(live,e)
    s=DeterministicEventStore()
    for e in events:
        s.append(e)
    replayed=s.replay(reducer,0)
    assert live == replayed
