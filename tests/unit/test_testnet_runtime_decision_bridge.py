from dataclasses import dataclass

from chantrading.runtime.testnet_runtime import TestnetRuntime
from chantrading.runtime.live_chanlun import LiveStructureEvent
from chantrading.strategy.live_decision import (
    DecisionSignal, DivergenceStatus, Eligibility, SignalSide,
)


def make_signal():
    return DecisionSignal(
        side=SignalSide.LONG,
        reason="CONSOLIDATION_DIVERGENCE_CONFIRMED+FRACTAL_CONFIRMED",
        trigger_fractal_id="F_TOP",
        ai_id="AI_1",
        comparison_ai_id="AI_0",
        divergence_status=DivergenceStatus.DIVERGENCE_CONFIRMED,
        eligibility=Eligibility.ELIGIBLE,
        price_extended=True,
        area_decay_ratio=0.72,
    )


@dataclass
class FakeCenter:
    id: str


class FakeCenterEngine:
    def __init__(self):
        self.centers = [FakeCenter("C1")]


class FakeSegmentEngine:
    def confirmed_segments(self):
        return ["SEGMENT"]


class FakeFractalEngine:
    class Inclusion:
        processed = ["CANDLE"]
    inclusion = Inclusion()


class FakeStructureEngine:
    def __init__(self):
        self.center = FakeCenterEngine()
        self.segment = FakeSegmentEngine()
        self.fractal = FakeFractalEngine()
        self.latest_fractal = "FRACTAL"


class FakeDecisionEngine:
    def __init__(self):
        self.structure_calls = []
        self.fractal_calls = []

    def on_structure(self, **kwargs):
        self.structure_calls.append(kwargs)
        return [make_signal()]

    def on_fractal(self, fractal):
        self.fractal_calls.append(fractal)
        return []


class FakeExecutor:
    def __init__(self):
        self.calls = []

    def execute(self, signal):
        self.calls.append(signal)
        return "EXECUTED"


def test_center_termination_dispatches_real_decision_signal_to_executor():
    runtime = TestnetRuntime()
    runtime.structure_engine = FakeStructureEngine()
    runtime.decision_engine = FakeDecisionEngine()
    runtime.signal_executor = FakeExecutor()

    events = [
        LiveStructureEvent(
            "CENTER_TERMINATED",
            1000,
            {"center_id": "C1"},
        )
    ]

    runtime._process_decisions(events)

    assert len(runtime.decision_engine.structure_calls) == 1
    call = runtime.decision_engine.structure_calls[0]
    assert call["center"].id == "C1"
    assert call["segments"] == ["SEGMENT"]
    assert call["processed_candles"] == ["CANDLE"]
    assert call["latest_fractal"] == "FRACTAL"

    assert len(runtime.decision_events) == 1
    assert runtime.decision_events[0].side is SignalSide.LONG
    assert runtime.signal_executor.calls == [runtime.decision_events[0]]
    assert runtime.execution_results == ["EXECUTED"]
