from decimal import Decimal

from chantrading.adapters.hyperliquid.mappers import map_fill, map_position
from chantrading.domain.execution import Side


def test_map_fill():
    fill = map_fill({
        "tid": "t1",
        "oid": 7,
        "coin": "ETH",
        "side": "B",
        "sz": "0.01",
        "px": "2000",
        "time": 100,
    })
    assert fill.instrument_id == "ETH"
    assert fill.quantity == Decimal("0.01")
    assert fill.price == Decimal("2000")
    assert fill.side is Side.BUY


def test_map_position():
    position = map_position({
        "coin": "ETH",
        "szi": "0.5",
        "entryPx": "2000",
        "liquidationPx": "1500",
        "unrealizedPnl": "10",
        "leverage": {"value": "3"},
    })
    assert position.size == Decimal("0.5")
    assert position.entry_price == Decimal("2000")
    assert position.leverage == 3
