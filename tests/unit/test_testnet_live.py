from decimal import Decimal
import pytest

from chantrading.adapters.hyperliquid.testnet_live import (
    HyperliquidSdkClient, LiveTestnetConfig, classify_order_response,
)
from chantrading.domain.execution import OrderIntent, OrderStatus, OrderType, Side

ADDRESS = "0x" + "1" * 40
CLOID = "0x00000000000000000000000000000001"


def test_live_config_defaults_to_unconfirmed():
    with pytest.raises(RuntimeError, match="HL_TESTNET_CONFIRM"):
        LiveTestnetConfig(account_address=ADDRESS).validate()


def test_live_config_rejects_mainnet():
    config = LiveTestnetConfig(
        account_address=ADDRESS,
        api_url="https://api.hyperliquid.xyz",
        confirm_testnet=True,
    )
    with pytest.raises(ValueError, match="official Hyperliquid Testnet"):
        config.validate()


def test_live_config_requires_valid_account():
    config = LiveTestnetConfig(account_address="not-an-address", confirm_testnet=True)
    with pytest.raises(ValueError, match="20-byte"):
        config.validate()


def test_classify_responses():
    assert classify_order_response({"status": "ok", "response": {"data": {"statuses": [{"filled": {"oid": 1}}]}}}) is OrderStatus.FILLED
    assert classify_order_response({"status": "ok", "response": {"data": {"statuses": [{"resting": {"oid": 1}}]}}}) is OrderStatus.OPEN
    assert classify_order_response({"status": "err"}) is OrderStatus.REJECTED
    assert classify_order_response({"status": "ok", "response": {"data": {"statuses": []}}}) is OrderStatus.UNKNOWN


class FakeExchange:
    def __init__(self):
        self.calls = []

    def order(self, *args, **kwargs):
        self.calls.append(("order", args, kwargs))
        return {"status": "ok", "response": {"data": {"statuses": [{"resting": {"oid": 7}}]}}}

    def cancel(self, instrument, oid):
        self.calls.append(("cancel", instrument, oid))
        return {"status": "ok"}


class FakeClient(HyperliquidSdkClient):
    def __init__(self):
        self.exchange = FakeExchange()


def intent(order_type):
    return OrderIntent("i", "ETH", Side.BUY, Decimal("0.01"), order_type, client_order_id=CLOID)


def test_client_maps_limit_to_gtc():
    client = FakeClient()
    result = client.submit(intent(OrderType.LIMIT), Decimal("100"))
    assert result["status"] == "ok"
    assert client.exchange.calls[0][2]["cloid"].to_raw() == CLOID
    assert client.exchange.calls[0][1][4] == {"limit": {"tif": "Gtc"}}


def test_client_maps_market_to_ioc():
    client = FakeClient()
    client.submit(intent(OrderType.MARKET), Decimal("100"))
    assert client.exchange.calls[0][1][4] == {"limit": {"tif": "Ioc"}}


def test_client_rejects_unsupported_order_type():
    client = FakeClient()
    with pytest.raises(ValueError, match="MARKET or LIMIT"):
        client.submit(intent(OrderType.STOP_MARKET), Decimal("100"))
    assert client.exchange.calls == []


def test_client_rejects_invalid_cloid():
    client = FakeClient()
    invalid = OrderIntent("i", "ETH", Side.BUY, Decimal("0.01"), OrderType.LIMIT, client_order_id="cloid")
    with pytest.raises(ValueError, match="Cloid hex string"):
        client.submit(invalid, Decimal("100"))
    assert client.exchange.calls == []
