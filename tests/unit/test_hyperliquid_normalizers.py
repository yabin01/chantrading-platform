from decimal import Decimal
from chantrading.adapters.hyperliquid.normalizers import normalize_candle, normalize_user_fills


def test_normalize_1m_candle():
    event = normalize_candle({
        "channel": "candle",
        "data": {
            "t": 1000, "T": 1999, "s": "ETH", "i": "1m",
            "o": "2000", "h": "2010", "l": "1990", "c": "2005", "v": "12.5"
        },
    }, 2000)
    assert event.channel == "candle"
    assert event.data["interval"] == "1m"
    assert event.data["open"] == Decimal("2000")
    assert event.data["final"] is True


def test_normalize_user_fills():
    events = normalize_user_fills({
        "channel": "userFills",
        "data": {"user": "0xabc", "isSnapshot": False, "fills": [
            {"tid": "t1", "coin": "ETH", "px": "2000", "sz": "0.1", "time": 123}
        ]},
    }, 200)
    assert len(events) == 1
    assert events[0].event_id == "fill:t1"
