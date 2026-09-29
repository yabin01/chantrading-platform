import json
from chantrading.adapters.hyperliquid.live_testnet import (
    LiveTestnetCandleStream,
    normalize_candle_message,
    candle_subscription,
)


def msg(ts=1700000000000, interval="1m"):
    return json.dumps({
        "channel": "candle",
        "data": {
            "s": "ETH",
            "i": interval,
            "t": ts,
            "o": "2000",
            "h": "2010",
            "l": "1990",
            "c": "2005",
            "v": "12",
        },
    })


def test_normalize_live_1m_candle():
    event = normalize_candle_message(msg())
    assert event.coin == "ETH"
    assert event.interval == "1m"
    assert event.close == "2005"


def test_ignore_subscription_response():
    raw = json.dumps({
        "channel": "subscriptionResponse",
        "data": {"method": "subscribe"},
    })
    try:
        normalize_candle_message(raw)
        assert False
    except ValueError:
        assert True


def test_reject_non_1m():
    try:
        normalize_candle_message(msg(interval="5m"))
        assert False
    except ValueError:
        assert True


def test_subscription_uses_1m():
    payload = json.loads(candle_subscription("ETH"))
    assert payload["subscription"]["type"] == "candle"
    assert payload["subscription"]["coin"] == "ETH"
    assert payload["subscription"]["interval"] == "1m"


def test_stream_deduplicates_same_candle():
    class FakeWS:
        def __init__(self):
            self.items = [msg(1000), msg(1000), msg(1060000)]

        def send(self, _):
            pass

        def recv(self):
            return self.items.pop(0)

        def close(self):
            pass

    seen = []
    stream = LiveTestnetCandleStream(lambda _: FakeWS(), seen.append)
    try:
        stream.run("ETH", duration_seconds=1)
    except IndexError:
        pass
    assert len(seen) == 2
