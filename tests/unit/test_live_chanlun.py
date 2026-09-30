from chantrading.adapters.hyperliquid.live_testnet import LiveCandle
from chantrading.runtime.live_chanlun import Live1MStructureEngine


def candle(ts, high, low, close):
    return LiveCandle(
        coin="ETH",
        interval="1m",
        timestamp_ms=ts,
        open=str(close),
        high=str(high),
        low=str(low),
        close=str(close),
        volume="1",
    )


def test_live_1m_feeds_fractal_engine():
    engine = Live1MStructureEngine()
    engine.on_candle(candle(1, 10, 8, 9))
    engine.on_candle(candle(2, 11, 9, 10))
    events = engine.on_candle(candle(3, 7, 5, 6))

    assert engine.candles_processed == 3
    assert any(e.type == "CANDLE_ACCEPTED" for e in events)
    assert engine.latest_fractal is not None
    assert engine.latest_fractal.type.value == "TOP"


def test_live_1m_strict_bi_is_downstream_of_confirmed_fractal():
    engine = Live1MStructureEngine()
    sequence = [
        candle(1, 10, 8, 9),
        candle(2, 11, 9, 10),
        candle(3, 7, 5, 6),
        candle(4, 6, 4, 5),
        candle(5, 12, 8, 11),
    ]

    emitted = []
    for item in sequence:
        emitted.extend(engine.on_candle(item))

    assert any(e.type == "FRACTAL_CONFIRMED" for e in emitted)
    assert any(e.type == "BI_ANCHOR_SET" for e in emitted)


def test_live_1m_replay_is_deterministic():
    sequence = [
        candle(1, 10, 8, 9),
        candle(2, 11, 9, 10),
        candle(3, 7, 5, 6),
        candle(4, 6, 4, 5),
        candle(5, 12, 8, 11),
        candle(6, 8, 5, 7),
    ]

    def run():
        e = Live1MStructureEngine()
        for item in sequence:
            e.on_candle(item)
        return [
            (x.type, x.timestamp_ms, tuple(sorted(x.payload.items())))
            for x in e.events
        ]

    assert run() == run()


def test_live_1m_rejects_non_1m():
    engine = Live1MStructureEngine()
    event = candle(1, 10, 8, 9)
    event = LiveCandle(
        coin=event.coin,
        interval="5m",
        timestamp_ms=event.timestamp_ms,
        open=event.open,
        high=event.high,
        low=event.low,
        close=event.close,
        volume=event.volume,
    )

    try:
        engine.on_candle(event)
        assert False
    except ValueError:
        assert True
