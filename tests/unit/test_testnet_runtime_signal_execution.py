from chantrading.domain.execution import ExecutionResult, OrderStatus
from chantrading.runtime.testnet_runtime import TestnetRuntime
from chantrading.strategy.live_decision import (
    DecisionSignal, DivergenceStatus, Eligibility, SignalSide,
)


class FakeExecutor:
    def __init__(self):
        self.calls = []

    def execute(self, signal):
        self.calls.append(signal)
        if signal.side is SignalSide.HOLD:
            return None
        return ExecutionResult(
            intent_id="OI-1",
            status=OrderStatus.FILLED,
            venue_order_id="123",
        )


def signal(side):
    return DecisionSignal(
        side=side,
        reason="test",
        trigger_fractal_id="F1",
        ai_id="AI1",
        comparison_ai_id="AI0",
        divergence_status=DivergenceStatus.DIVERGENCE_CONFIRMED,
        eligibility=Eligibility.ELIGIBLE,
        price_extended=True,
        area_decay_ratio=0.5,
    )


def test_record_decisions_executes_only_when_bridge_is_configured():
    runtime = TestnetRuntime()
    executor = FakeExecutor()
    runtime.signal_executor = executor

    runtime._record_decisions([signal(SignalSide.HOLD), signal(SignalSide.LONG)])

    assert len(runtime.decision_events) == 2
    assert len(executor.calls) == 2
    assert len(runtime.execution_results) == 1
    assert runtime.execution_results[0].status is OrderStatus.FILLED


def test_record_decisions_remains_observational_without_bridge():
    runtime = TestnetRuntime()

    runtime._record_decisions([signal(SignalSide.LONG)])

    assert len(runtime.decision_events) == 1
    assert runtime.execution_results == []
