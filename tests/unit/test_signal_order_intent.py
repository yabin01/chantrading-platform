from decimal import Decimal

import pytest

from chantrading.domain.execution import OrderType, Side
from chantrading.strategy.live_decision import (
    DecisionSignal, DivergenceStatus, Eligibility, SignalSide,
)
from chantrading.strategy.signal_order_intent import (
    OrderIntentContext, SignalToOrderIntent,
)


def signal(side, trigger="F_TOP"):
    return DecisionSignal(
        side=side,
        reason="CONSOLIDATION_DIVERGENCE_CONFIRMED+FRACTAL_CONFIRMED",
        trigger_fractal_id=trigger,
        ai_id="AI_C3_S8",
        comparison_ai_id="AI_C1_S4",
        divergence_status=DivergenceStatus.DIVERGENCE_CONFIRMED,
        eligibility=Eligibility.ELIGIBLE,
        price_extended=True,
        area_decay_ratio=0.72,
    )


def context():
    return OrderIntentContext(
        instrument_id="ETH-USD", quantity=Decimal("0.01"),
        decision_id="D-001", signal_id="S-001", client_order_id="cloid-001",
    )


def test_hold_does_not_create_order_intent():
    assert SignalToOrderIntent().build(signal(SignalSide.HOLD), context()) is None


def test_long_maps_to_buy_and_is_deterministic():
    intent = SignalToOrderIntent().build(signal(SignalSide.LONG, "F_BOTTOM"), context())
    assert intent is not None and intent.side is Side.BUY
    assert intent.order_type is OrderType.MARKET
    assert intent.quantity == Decimal("0.01")
    again = SignalToOrderIntent().build(signal(SignalSide.LONG, "F_BOTTOM"), context())
    assert again.intent_id == intent.intent_id


def test_short_maps_to_sell():
    intent = SignalToOrderIntent().build(signal(SignalSide.SHORT), context())
    assert intent is not None and intent.side is Side.SELL


def test_unconfirmed_signal_cannot_create_intent():
    with pytest.raises(ValueError, match="confirmed trigger fractal"):
        SignalToOrderIntent().build(signal(SignalSide.LONG, trigger=None), context())


def test_non_positive_quantity_is_rejected():
    bad = OrderIntentContext(
        instrument_id="ETH-USD", quantity=Decimal("0"),
        decision_id="D", signal_id="S", client_order_id="C",
    )
    with pytest.raises(ValueError, match="quantity"):
        SignalToOrderIntent().build(signal(SignalSide.LONG), bad)
