from chantrading.adapters.hyperliquid.info_client import HyperliquidInfoClient


class FakeRest:
    def __init__(self):
        self.payloads = []

    def post_info(self, payload):
        self.payloads.append(payload)
        return {"ok": True}


def test_candle_snapshot_builds_canonical_info_request():
    rest = FakeRest()
    client = HyperliquidInfoClient(rest)
    assert client.candle_snapshot("ETH", "1m", 1000, 2000) == {"ok": True}
    assert rest.payloads[-1] == {
        "type": "candleSnapshot",
        "req": {"coin": "ETH", "interval": "1m", "startTime": 1000, "endTime": 2000},
    }


def test_clearinghouse_state_is_read_only():
    rest = FakeRest()
    client = HyperliquidInfoClient(rest)
    client.clearinghouse_state("0xabc")
    assert rest.payloads[-1] == {"type": "clearinghouseState", "user": "0xabc"}
