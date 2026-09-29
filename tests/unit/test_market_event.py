from chantrading.adapters.hyperliquid.market_event import (
    MarketEventGuard, canonical_event_id, to_canonical_event,
)
from chantrading.adapters.hyperliquid.ws_market_data import CandleEvent


def candle(ts=60_000):
    return CandleEvent("ETH","1m",ts,"2000","2010","1990","2005","10")


def test_event_id_is_deterministic():
    assert canonical_event_id("x","ETH","1m",1) == canonical_event_id("x","ETH","1m",1)


def test_canonical_conversion():
    e=to_canonical_event(candle())
    assert e.source == "hyperliquid.testnet"
    assert e.symbol == "ETH"


def test_duplicate_is_idempotent():
    g=MarketEventGuard()
    e=to_canonical_event(candle())
    assert g.accept(e) == "ACCEPTED"
    assert g.accept(e) == "DUPLICATE"


def test_gap_is_detected():
    g=MarketEventGuard()
    assert g.accept(to_canonical_event(candle(60_000))) == "ACCEPTED"
    assert g.accept(to_canonical_event(candle(180_000))) == "GAP"


def test_out_of_order_is_detected():
    g=MarketEventGuard()
    g.accept(to_canonical_event(candle(120_000)))
    assert g.accept(to_canonical_event(candle(60_000))) == "OUT_OF_ORDER"
