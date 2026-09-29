from decimal import Decimal
from chantrading.adapters.hyperliquid.order_mapper import map_limit_order, map_cancel
from chantrading.adapters.hyperliquid.order_requests import LimitOrderRequest, CancelOrderRequest, TimeInForce


def test_limit_order_mapping():
    req = LimitOrderRequest("ETH-USD", True, Decimal("0.1"), Decimal("2000"), TimeInForce.GTC, True, "cl-1")
    action = map_limit_order(req, 4)
    assert action["type"] == "order"
    assert action["orders"][0]["a"] == 4
    assert action["orders"][0]["r"] is True
    assert action["orders"][0]["c"] == "cl-1"


def test_cancel_requires_oid():
    try:
        map_cancel(CancelOrderRequest("ETH-USD"), 4)
        assert False
    except ValueError:
        assert True


def test_signing_gateway_isolated():
    class Signer:
        def sign(self, action, nonce, expires_after, mainnet):
            return "TEST_SIGNATURE"

    from chantrading.adapters.hyperliquid.signing import SigningGateway
    signed = SigningGateway(Signer()).sign({"type": "order"}, 1)
    assert signed.signature == "TEST_SIGNATURE"
    assert signed.mainnet is False
