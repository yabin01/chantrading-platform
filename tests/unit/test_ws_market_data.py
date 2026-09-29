import json
from chantrading.adapters.hyperliquid.ws_market_data import (
    TESTNET_WS_URL, WebSocketMarketDataTransport, candle_subscription, parse_candle_message,
)


def msg():
    return json.dumps({
        "channel": "candle",
        "data": {
            "s": "ETH",
            "i": "1m",
            "t": 1710000000000,
            "o": "2000",
            "h": "2010",
            "l": "1990",
            "c": "2005",
            "v": "123.45",
        },
    })


def test_parse_candle():
    e=parse_candle_message(msg())
    assert e.coin == "ETH"
    assert e.interval == "1m"
    assert e.timestamp == 1710000000000
    assert e.close == "2005"


def test_subscription():
    assert candle_subscription("ETH")["subscription"]["interval"] == "1m"


def test_wrong_interval_rejected():
    try:
        candle_subscription("ETH", "5m")
        assert False
    except ValueError:
        pass


def test_transport_uses_testnet_endpoint():
    captured=[]
    class WS:
        def send(self, value): captured.append(value)
    t=WebSocketMarketDataTransport(lambda url: (captured.append(url) or WS()), lambda e: captured.append(e))
    t.connect()
    assert captured[0] == TESTNET_WS_URL
    t.subscribe("ETH")
    assert '"channel"' not in captured[1]
    t.handle_message(msg())
    assert captured[-1].coin == "ETH"
