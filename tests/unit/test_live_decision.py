from chantrading.chanlun import Center, CenterState, Segment, SegmentDirection, SegmentState
from chantrading.chanlun.models import Fractal, FractalStatus, FractalType, ProcessedCandle
from chantrading.strategy.live_decision import Live1MDecisionEngine, SignalSide


def segment(sid, direction, start, end, high, low):
    return Segment(
        id=sid,
        direction=direction,
        state=SegmentState.CONFIRMED,
        start_bi_id=f"{sid}-B0",
        current_end_bi_id=f"{sid}-B1",
        confirmed_end_bi_id=f"{sid}-B1",
        start_index=start,
        end_index=end,
        high=high,
        low=low,
    )


def candles(n=80):
    return [
        ProcessedCandle(
            i, i, i + 1,
            100.0 + i * 0.1,
            100.0 + i * 0.1,
            100.0 + i * 0.1,
            100.0 + i * 0.1,
            1.0,
            [i],
        )
        for i in range(n)
    ]


def test_decision_holds_until_three_completed_ais():
    engine = Live1MDecisionEngine()
    center = Center(
        id="C1",
        state=CenterState.TERMINATED,
        segment_ids=["S1", "S2", "S3"],
        zg=105,
        zd=100,
        gg=110,
        dd=95,
        start_index=2,
        end_index=8,
        terminated_by_segment_id="S4",
    )
    result = engine.on_structure(
        center=center,
        segments=[
            segment("S0", SegmentDirection.UP, 0, 1, 101, 99),
            segment("S1", SegmentDirection.UP, 2, 4, 105, 100),
            segment("S2", SegmentDirection.DOWN, 4, 6, 106, 99),
            segment("S3", SegmentDirection.UP, 6, 8, 110, 101),
            segment("S4", SegmentDirection.DOWN, 8, 10, 111, 98),
        ],
        processed_candles=candles(),
        latest_fractal=None,
    )
    assert result[0].side is SignalSide.HOLD
    assert result[0].reason == "HOLD_CANNOT_COMPARE"


def test_trigger_requires_confirmed_top_fractal():
    engine = Live1MDecisionEngine()
    from chantrading.strategy.live_decision import DivergenceStatus, _PendingTrigger

    engine.pending_trigger = _PendingTrigger(
        side=SignalSide.SHORT,
        ai_id="AI_C3_S8",
        comparison_ai_id="AI_C1_S4",
        divergence_status=DivergenceStatus.DIVERGENCE_CONFIRMED,
        area_decay_ratio=0.72,
        trigger_type=FractalType.TOP,
    )
    bottom = Fractal(
        id="F_BOTTOM",
        type=FractalType.BOTTOM,
        center_index=20,
        confirm_index=21,
        top=120,
        bottom=110,
        source_processed_ids=(19, 20, 21),
        status=FractalStatus.CONFIRMED,
    )
    assert engine.on_fractal(bottom) == []

    top = Fractal(
        id="F_TOP",
        type=FractalType.TOP,
        center_index=22,
        confirm_index=23,
        top=130,
        bottom=120,
        source_processed_ids=(21, 22, 23),
        status=FractalStatus.CONFIRMED,
    )
    signals = engine.on_fractal(top)
    assert len(signals) == 1
    assert signals[0].side is SignalSide.SHORT
    assert signals[0].trigger_fractal_id == "F_TOP"


def test_macd_area_is_directional_and_deterministic():
    engine = Live1MDecisionEngine()
    data = candles()
    up = engine._macd_area(
        data, start_index=0, end_index=79, direction=SegmentDirection.UP
    )
    down = engine._macd_area(
        data, start_index=0, end_index=79, direction=SegmentDirection.DOWN
    )
    assert up >= 0
    assert down >= 0
    assert engine._macd_area(
        data, start_index=0, end_index=79, direction=SegmentDirection.UP
    ) == up
