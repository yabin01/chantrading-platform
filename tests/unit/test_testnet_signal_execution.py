from decimal import Decimal

import pytest

from chantrading.domain.execution import ExecutionResult, OrderStatus
from chantrading.runtime.testnet_signal_execution import (
    TestnetAutoExecutionConfig,
    TestnetSignalExecutor,
)
from chantrading.strategy.live_decision import (
    DecisionSignal, DivergenceStatus, Eligibility, SignalSide,
)


class FakeExchange:
    def _slippage_price(self, instrument, is_buy, slippage):
        assert instrument == "ETH"
        assert is_buy is True
        assert slippage == 0.05
        return "2500.0"


class FakeClient:
    def __init__(self):
        self.exchange = FakeExchange()
        self.calls = []

    def submit(self, intent, price):
        self.calls.append((intent, price))
        return {"status": "ok", "response": {"data": {"statuses": [{"filled": {"oid": 123}}]}}}

    def execution_result(self, intent, result):
        return ExecutionResult(
            intent.intent_id,
            OrderStatus.FILLED,
            venue_order_id="123",
            client_order_id=intent.client_order_id,
        )


def signal(side=SignalSide.LONG):
    return DecisionSignal(
        side=side,
        reason="CONSOLIDATION_DIVERGENCE_CONFIRMED+FRACTAL_CONFIRMED",
        trigger_fractal_id="F_TOP",
        ai_id="AI_1",
        comparison_ai_id="AI_0",
        divergence_status=DivergenceStatus.DIVERGENCE_CONFIRMED,
        eligibility=Eligibility.ELIGIBLE,
        price_extended=True,
        area_decay_ratio=0.72,
    )


def executor(enabled=True):
    return TestnetSignalExecutor(
        client=FakeClient(),
        config=TestnetAutoExecutionConfig(
            instrument_id="ETH",
            quantity=Decimal("0.01"),
            enabled=enabled,
        ),
    )


def test_requires_explicit_auto_execute():
    with pytest.raises(RuntimeError, match="HL_TESTNET_AUTO_EXECUTE"):
        executor(False)


def test_hold_is_not_executed():
    ex = executor()
    assert ex.execute(signal(SignalSide.HOLD)) is None
    assert ex.client.calls == []


def test_signal_maps_to_market_execution():
    ex = executor()
    result = ex.execute(signal())
    assert result is not None
    assert result.status is OrderStatus.FILLED
    assert len(ex.client.calls) == 1
    intent, price = ex.client.calls[0]
    assert intent.instrument_id == "ETH"
    assert intent.quantity == Decimal("0.01")
    assert intent.client_order_id.startswith("0x")
    assert len(intent.client_order_id) == 34
    assert price == Decimal("2500.0")


def test_same_signal_executes_once():
    ex = executor()
    first = ex.execute(signal())
    second = ex.execute(signal())
    assert first is not None
    assert second is None
    assert len(ex.client.calls) == 1


def test_quantity_cap():
    with pytest.raises(ValueError, match="capped"):
        TestnetSignalExecutor(
            client=FakeClient(),
            config=TestnetAutoExecutionConfig(
                quantity=Decimal("0.010001"),
                enabled=True,
            ),
        )
