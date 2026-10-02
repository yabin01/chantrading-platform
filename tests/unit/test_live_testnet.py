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



def test_stream_reconnects_after_websocket_disconnect(monkeypatch):
    from websocket import WebSocketConnectionClosedException

    class DisconnectingWS:
        def send(self, _):
            pass
        def recv(self):
            raise WebSocketConnectionClosedException("lost")
        def close(self):
            pass

    class HealthyWS:
        def send(self, _):
            pass
        def recv(self):
            return msg(2000)
        def close(self):
            pass

    sockets = [DisconnectingWS(), HealthyWS()]
    monkeypatch.setattr("chantrading.adapters.hyperliquid.live_testnet.time.sleep", lambda _: None)
    calls = iter([1000.0, 1000.0, 1000.0, 1001.0])
    monkeypatch.setattr("chantrading.adapters.hyperliquid.live_testnet.time.time", lambda: next(calls))

    seen = []
    stream = LiveTestnetCandleStream(lambda _: sockets.pop(0), seen.append, max_reconnects=1)
    assert stream.run("ETH", duration_seconds=1) == 1
    assert stream.reconnects == 1
    assert len(seen) == 1

def test_stream_exposes_reconnect_health():
    class FakeWS:
        def __init__(self):
            self.items = [msg(1000)]
        def send(self, _): pass
        def recv(self): return self.items.pop(0)
        def close(self): pass

    seen = []
    stream = LiveTestnetCandleStream(lambda _: FakeWS(), seen.append)
    try:
        stream.run("ETH", duration_seconds=1)
    except IndexError:
        pass
    health = stream.health_snapshot()
    assert health["running"] is False
    assert health["received"] == 1
    assert health["last_candle_ts"] == 1000
    assert health["reconnects"] == 0


def test_stream_detects_one_minute_candle_gap():
    class FakeWS:
        def __init__(self):
            self.items = [msg(1000), msg(121000)]
        def send(self, _): pass
        def recv(self): return self.items.pop(0)
        def close(self): pass

    seen = []
    stream = LiveTestnetCandleStream(lambda _: FakeWS(), seen.append)
    try:
        stream.run("ETH", duration_seconds=1)
    except IndexError:
        pass
    health = stream.health_snapshot()
    assert len(seen) == 2
    assert health["gap_count"] == 1
    assert health["last_gap_ms"] == 120000
