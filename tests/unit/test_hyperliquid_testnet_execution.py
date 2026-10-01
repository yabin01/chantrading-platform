from decimal import Decimal

from chantrading.adapters.hyperliquid.testnet_execution import HyperliquidTestnetBackend
from chantrading.domain.execution import OrderStatus, OrderType
from chantrading.strategy.live_decision import (
    DecisionSignal, DivergenceStatus, Eligibility, SignalSide,
)
from chantrading.strategy.signal_order_intent import OrderIntentContext, SignalToOrderIntent


class FakeExchange:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def _slippage_price(self, name, is_buy, slippage):
        self.calls.append(("price", name, is_buy, slippage))
        return 100.0

    def order(self, *args, **kwargs):
        self.calls.append(("order", args, kwargs))
        return self.response


def make_intent(order_type=OrderType.MARKET):
    signal = DecisionSignal(
        side=SignalSide.LONG,
        reason="CONSOLIDATION_DIVERGENCE_CONFIRMED+FRACTAL_CONFIRMED",
        trigger_fractal_id="F_BOTTOM",
        ai_id="AI_C3_S8",
        comparison_ai_id="AI_C1_S4",
        divergence_status=DivergenceStatus.DIVERGENCE_CONFIRMED,
        eligibility=Eligibility.ELIGIBLE,
        price_extended=True,
        area_decay_ratio=Decimal("0.72"),
    )
    return SignalToOrderIntent().build(
        signal,
        OrderIntentContext(
            instrument_id="ETH",
            quantity=Decimal("0.01"),
            decision_id="D",
            signal_id="S",
            client_order_id="cloid-001",
            order_type=order_type,
        ),
    )


def test_market_intent_maps_to_hyperliquid_ioc():
    exchange = FakeExchange({
        "status": "ok",
        "response": {"data": {"statuses": [{"resting": {"oid": 12345}}]}},
    })
    result = HyperliquidTestnetBackend(exchange, "0xabc").submit(make_intent())
    assert result.status is OrderStatus.OPEN
    assert result.venue_order_id == "12345"
    assert exchange.calls[-1][1] == (
        "ETH", True, 0.01, 100.0, {"limit": {"tif": "Ioc"}}
    )
    assert exchange.calls[-1][2]["cloid"] == "cloid-001"


def test_rejected_exchange_result_is_rejected():
    exchange = FakeExchange({"status": "err", "response": "rejected"})
    result = HyperliquidTestnetBackend(exchange, "0xabc").submit(make_intent())
    assert result.status is OrderStatus.REJECTED


def test_non_market_intent_is_rejected_before_exchange_call():
    exchange = FakeExchange({"status": "ok"})
    try:
        HyperliquidTestnetBackend(exchange, "0xabc").submit(
            make_intent(OrderType.LIMIT)
        )
        assert False
    except ValueError as exc:
        assert "MARKET" in str(exc)
    assert not any(call[0] == "order" for call in exchange.calls)
