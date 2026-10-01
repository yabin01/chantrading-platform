from decimal import Decimal

from chantrading.domain.execution import OrderType, Side
from chantrading.strategy.signal_order_intent import OrderIntentContext, SignalToOrderIntent
from chantrading.strategy.live_decision import DecisionSignal, DivergenceStatus, Eligibility, SignalSide
from chantrading.adapters.hyperliquid.testnet_execution import HyperliquidTestnetBackend


class FakeExchange:
    def __init__(self):
        self.calls = []
    def _slippage_price(self, name, is_buy, slippage):
        return 100.0
    def order(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return {"status":"ok","response":{"data":{"statuses":[{"resting":{"oid":12345}}]}}}


def make_intent():
    signal = DecisionSignal(
        side=SignalSide.LONG,
        reason="CONSOLIDATION_DIVERGENCE_CONFIRMED+FRACTAL_CONFIRMED",
        trigger_fractal_id="F_BOTTOM",
        ai_id="AI_C3_S8",
        comparison_ai_id="AI_C1_S4",
        divergence_status=DivergenceStatus.DIVERGENCE_CONFIRMED,
        eligibility=Eligibility.ELIGIBLE,
        price_extended=True,
        area_decay_ratio=0.72,
    )
    return SignalToOrderIntent().build(signal, OrderIntentContext(
        instrument_id="ETH",
        quantity=Decimal("0.01"),
        decision_id="D",
        signal_id="S",
        client_order_id="cloid-001",
    ))


def test_testnet_backend_maps_market_intent_to_ioc():
    ex = FakeExchange()
    result = HyperliquidTestnetBackend(ex, "0xabc").submit(make_intent())
    assert result.status.value == "OPEN"
    assert result.venue_order_id == "12345"
    assert ex.calls[0][0] == ("ETH", True, 0.01, 100.0, {"limit":{"tif":"Ioc"}})
    assert ex.calls[0][1]["cloid"] == "cloid-001"


def test_rejected_exchange_result_is_rejected():
    class RejectExchange(FakeExchange):
        def order(self, *args, **kwargs):
            return {"status":"err","response":"rejected"}
    result = HyperliquidTestnetBackend(RejectExchange(), "0xabc").submit(make_intent())
    assert result.status.value == "REJECTED"


def test_t3_does_not_accept_limit_intent():
    intent = make_intent()
    from dataclasses import replace
    limit_intent = replace(intent, order_type=OrderType.LIMIT)
    try:
        HyperliquidTestnetBackend(FakeExchange(), "0xabc").submit(limit_intent)
        assert False
    except ValueError as exc:
        assert "MARKET" in str(exc)
