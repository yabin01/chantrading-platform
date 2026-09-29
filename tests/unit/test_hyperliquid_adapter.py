from decimal import Decimal

from chantrading.adapters.hyperliquid.adapter import HyperliquidAdapter
from chantrading.adapters.hyperliquid.config import HyperliquidConfig
from chantrading.domain.execution import ExecutionResult, OrderIntent, OrderStatus, OrderType, Side


class FakeBackend:
    def submit(self, intent):
        return ExecutionResult(
            intent_id=intent.intent_id,
            status=OrderStatus.OPEN,
            venue_order_id="10001",
            client_order_id=intent.client_order_id,
        )

    def cancel(self, order_id):
        return ExecutionResult("cancel-" + order_id, OrderStatus.CANCELLED)

    def get_position(self, instrument_id):
        return None

    def get_open_orders(self, instrument_id):
        return []

    def get_recent_fills(self, instrument_id):
        return []

    def reconcile(self, instrument_id):
        return {"status": "MATCH"}


def test_submit_does_not_leak_backend_objects():
    adapter = HyperliquidAdapter(HyperliquidConfig(), backend=FakeBackend())
    intent = OrderIntent(
        intent_id="i-1",
        instrument_id="ETH-USD",
        side=Side.BUY,
        quantity=Decimal("0.01"),
        order_type=OrderType.MARKET,
        client_order_id="cl-1",
    )
    result = adapter.submit(intent)

    assert result.status is OrderStatus.OPEN
    assert result.venue_order_id == "10001"
    assert result.client_order_id == "cl-1"


def test_reduce_only_capability_is_explicit():
    adapter = HyperliquidAdapter(HyperliquidConfig(), backend=FakeBackend())
    assert adapter.capabilities.supports("reduce_only")
