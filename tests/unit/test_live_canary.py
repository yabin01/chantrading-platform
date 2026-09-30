from chantrading.adapters.hyperliquid.live_testnet import LiveCandle
from chantrading.runtime.live_canary import Live1MCanary


def candle(ts, close="100"):
    return LiveCandle(
        coin="ETH",
        interval="1m",
        timestamp_ms=ts,
        open=close,
        high=close,
        low=close,
        close=close,
        volume="1",
    )


def test_canary_feeds_live_engine_and_exposes_snapshot():
    canary = Live1MCanary()
    canary.on_candle(candle(1))
    canary.on_candle(candle(2))

    snapshot = canary.snapshot()
    assert snapshot["candles_received"] == 2
    assert snapshot["last_candle_timestamp_ms"] == 2
    assert snapshot["candles_processed"] == 2


def test_canary_rejects_duplicate_or_out_of_order_candles():
    canary = Live1MCanary()
    canary.on_candle(candle(10))

    try:
        canary.on_candle(candle(10))
        assert False
    except RuntimeError:
        pass

    try:
        canary.on_candle(candle(9))
        assert False
    except RuntimeError:
        pass


def test_canary_is_read_only_and_has_no_execution_surface():
    canary = Live1MCanary()
    assert not hasattr(canary, "submit_order")
    assert not hasattr(canary, "place_order")
    assert not hasattr(canary, "execute")
