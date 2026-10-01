"""Deterministic live 1M ChanLun decision/signal adapter.

This module is downstream of the structural engines. It does not modify
Fractal/Bi/Segment/Center geometry and never changes timeframe.

A completed same-level Ai is materialized when a confirmed 1M Center is
terminated by the next confirmed Segment. Ai vs Ai+2 is compared using:
1) same-level eligibility,
2) price extension in the Ai direction,
3) directional MACD histogram area.

A qualifying consolidation divergence creates a pending trade direction.
The actual signal is emitted only after a confirmed 1M trigger fractal of the
opposite turning type is observed.

No order submission is performed here.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable

from chantrading.chanlun import Center, Segment, SegmentDirection
from chantrading.chanlun.models import Fractal, FractalType, ProcessedCandle


class SignalSide(str, Enum):
    HOLD = "HOLD"
    LONG = "LONG"
    SHORT = "SHORT"


class Eligibility(str, Enum):
    ELIGIBLE = "ELIGIBLE"
    HOLD_CANNOT_COMPARE = "HOLD_CANNOT_COMPARE"


class DivergenceStatus(str, Enum):
    NONE = "NONE"
    DIVERGENCE_CONFIRMED = "DIVERGENCE_CONFIRMED"


@dataclass(frozen=True)
class LiveAi:
    id: str
    direction: SegmentDirection
    entry_segment_id: str
    center_id: str
    center_segment_ids: tuple[str, ...]
    exit_segment_id: str
    start_index: int
    end_index: int
    high: float
    low: float
    macd_area: float


@dataclass(frozen=True)
class DecisionSignal:
    side: SignalSide
    reason: str
    trigger_fractal_id: str | None
    ai_id: str | None
    comparison_ai_id: str | None
    divergence_status: DivergenceStatus
    eligibility: Eligibility
    price_extended: bool
    area_decay_ratio: float | None


@dataclass
class _PendingTrigger:
    side: SignalSide
    ai_id: str
    comparison_ai_id: str
    divergence_status: DivergenceStatus
    area_decay_ratio: float
    trigger_type: FractalType


@dataclass
class Live1MDecisionEngine:
    """Turns completed structural Ai states into deterministic signals."""

    ais: list[LiveAi] = field(default_factory=list)
    decisions: list[DecisionSignal] = field(default_factory=list)
    pending_trigger: _PendingTrigger | None = None
    emitted_trigger_fractals: set[str] = field(default_factory=set)

    def on_structure(
        self,
        *,
        center: Center,
        segments: Iterable[Segment],
        processed_candles: Iterable[ProcessedCandle],
        latest_fractal: Fractal | None,
    ) -> list[DecisionSignal]:
        """Evaluate a newly terminated center.

        The caller invokes this for CENTER_TERMINATED. The generated Ai ID is
        stable, so replaying the same center is idempotent.
        """
        segment_list = sorted(
            [s for s in segments if s.confirmed],
            key=lambda item: (
                item.start_index,
                item.end_index or item.start_index,
                item.id,
            ),
        )
        exit_id = center.terminated_by_segment_id
        if exit_id is None:
            return [self._hold("CENTER_TERMINATED_WITHOUT_EXIT")]

        exit_segment = next((s for s in segment_list if s.id == exit_id), None)
        if exit_segment is None:
            return [self._hold("EXIT_SEGMENT_NOT_FOUND")]

        ai_id = f"AI_{center.id}_{exit_id}"
        if any(ai.id == ai_id for ai in self.ais):
            return []

        center_ids = set(center.segment_ids)
        first_center = next((s for s in segment_list if s.id in center_ids), None)
        if first_center is None:
            return [self._hold("CENTER_SEGMENTS_NOT_FOUND")]

        entry_candidates = [
            s
            for s in segment_list
            if s.id not in center_ids
            and s.id != exit_id
            and s.end_index is not None
            and s.end_index <= first_center.start_index
        ]
        if not entry_candidates:
            return [self._hold("AI_ENTRY_NOT_CONFIRMED")]

        entry = entry_candidates[-1]
        candles = list(processed_candles)
        end_index = exit_segment.end_index or entry.start_index
        area = self._macd_area(
            candles,
            start_index=entry.start_index,
            end_index=end_index,
            direction=exit_segment.direction,
        )

        ai = LiveAi(
            id=ai_id,
            direction=exit_segment.direction,
            entry_segment_id=entry.id,
            center_id=center.id,
            center_segment_ids=tuple(center.segment_ids),
            exit_segment_id=exit_id,
            start_index=entry.start_index,
            end_index=end_index,
            high=max(entry.high, center.gg, exit_segment.high),
            low=min(entry.low, center.dd, exit_segment.low),
            macd_area=area,
        )
        self.ais.append(ai)

        result = self._evaluate_sequence(ai)
        self.decisions.append(result)

        if result.divergence_status is DivergenceStatus.DIVERGENCE_CONFIRMED:
            assert result.area_decay_ratio is not None
            self.pending_trigger = _PendingTrigger(
                side=result.side,
                ai_id=ai.id,
                comparison_ai_id=result.comparison_ai_id or "",
                divergence_status=result.divergence_status,
                area_decay_ratio=result.area_decay_ratio,
                trigger_type=(
                    FractalType.TOP
                    if ai.direction is SegmentDirection.UP
                    else FractalType.BOTTOM
                ),
            )
            if latest_fractal is not None:
                return [result, *self.on_fractal(latest_fractal)]
        return [result]

    def on_fractal(self, fractal: Fractal) -> list[DecisionSignal]:
        """Emit a signal only on a completed 1M trigger fractal."""
        pending = self.pending_trigger
        if pending is None or fractal.id in self.emitted_trigger_fractals:
            return []
        if fractal.status.value != "CONFIRMED":
            return []
        if fractal.type is not pending.trigger_type:
            return []

        self.emitted_trigger_fractals.add(fractal.id)
        self.pending_trigger = None
        signal = DecisionSignal(
            side=pending.side,
            reason="CONSOLIDATION_DIVERGENCE_CONFIRMED+FRACTAL_CONFIRMED",
            trigger_fractal_id=fractal.id,
            ai_id=pending.ai_id,
            comparison_ai_id=pending.comparison_ai_id,
            divergence_status=pending.divergence_status,
            eligibility=Eligibility.ELIGIBLE,
            price_extended=True,
            area_decay_ratio=pending.area_decay_ratio,
        )
        self.decisions.append(signal)
        return [signal]

    def snapshot(self) -> dict:
        return {
            "ai_ids": [ai.id for ai in self.ais],
            "pending_trigger_side": (
                self.pending_trigger.side.value if self.pending_trigger else None
            ),
            "pending_trigger_ai_id": (
                self.pending_trigger.ai_id if self.pending_trigger else None
            ),
            "decision_count": len(self.decisions),
        }

    def _evaluate_sequence(self, current: LiveAi) -> DecisionSignal:
        if len(self.ais) < 3:
            return self._hold("HOLD_CANNOT_COMPARE", ai_id=current.id)

        previous = self.ais[-3]
        if previous.direction is not current.direction:
            return DecisionSignal(
                side=SignalSide.HOLD,
                reason="HOLD_CANNOT_COMPARE_DIRECTION",
                trigger_fractal_id=None,
                ai_id=current.id,
                comparison_ai_id=previous.id,
                divergence_status=DivergenceStatus.NONE,
                eligibility=Eligibility.HOLD_CANNOT_COMPARE,
                price_extended=False,
                area_decay_ratio=None,
            )

        if current.direction is SegmentDirection.UP:
            price_extended = current.high > previous.high
            side = SignalSide.SHORT
        else:
            price_extended = current.low < previous.low
            side = SignalSide.LONG

        if not price_extended:
            return DecisionSignal(
                side=SignalSide.HOLD,
                reason="HOLD_NO_PRICE_EXTENSION",
                trigger_fractal_id=None,
                ai_id=current.id,
                comparison_ai_id=previous.id,
                divergence_status=DivergenceStatus.NONE,
                eligibility=Eligibility.ELIGIBLE,
                price_extended=False,
                area_decay_ratio=None,
            )

        if previous.macd_area <= 0:
            return DecisionSignal(
                side=SignalSide.HOLD,
                reason="HOLD_MACD_AREA_UNAVAILABLE",
                trigger_fractal_id=None,
                ai_id=current.id,
                comparison_ai_id=previous.id,
                divergence_status=DivergenceStatus.NONE,
                eligibility=Eligibility.ELIGIBLE,
                price_extended=True,
                area_decay_ratio=None,
            )

        ratio = current.macd_area / previous.macd_area
        if current.macd_area < previous.macd_area:
            return DecisionSignal(
                side=side,
                reason="CONSOLIDATION_DIVERGENCE_CONFIRMED",
                trigger_fractal_id=None,
                ai_id=current.id,
                comparison_ai_id=previous.id,
                divergence_status=DivergenceStatus.DIVERGENCE_CONFIRMED,
                eligibility=Eligibility.ELIGIBLE,
                price_extended=True,
                area_decay_ratio=ratio,
            )

        return DecisionSignal(
            side=SignalSide.HOLD,
            reason="HOLD_MOMENTUM_NOT_WEAKER",
            trigger_fractal_id=None,
            ai_id=current.id,
            comparison_ai_id=previous.id,
            divergence_status=DivergenceStatus.NONE,
            eligibility=Eligibility.ELIGIBLE,
            price_extended=True,
            area_decay_ratio=ratio,
        )

    @staticmethod
    def _hold(reason: str, ai_id: str | None = None) -> DecisionSignal:
        return DecisionSignal(
            side=SignalSide.HOLD,
            reason=reason,
            trigger_fractal_id=None,
            ai_id=ai_id,
            comparison_ai_id=None,
            divergence_status=DivergenceStatus.NONE,
            eligibility=Eligibility.HOLD_CANNOT_COMPARE,
            price_extended=False,
            area_decay_ratio=None,
        )

    @staticmethod
    def _macd_area(
        candles: list[ProcessedCandle],
        *,
        start_index: int,
        end_index: int,
        direction: SegmentDirection,
    ) -> float:
        """Return directional MACD(12,26,9) histogram area."""
        if not candles:
            return 0.0

        closes = [float(c.close) for c in candles]
        ema12 = _ema_series(closes, 12)
        ema26 = _ema_series(closes, 26)
        dif = [a - b for a, b in zip(ema12, ema26)]
        dea = _ema_series(dif, 9)
        hist = [a - b for a, b in zip(dif, dea)]

        total = 0.0
        lo = max(0, start_index)
        hi = min(end_index, len(hist) - 1)
        if hi < lo:
            return 0.0

        for value in hist[lo : hi + 1]:
            if direction is SegmentDirection.UP:
                total += max(value, 0.0)
            else:
                total += max(-value, 0.0)
        return total


def _ema_series(values: list[float], period: int) -> list[float]:
    if not values:
        return []
    alpha = 2.0 / (period + 1.0)
    result = [values[0]]
    for value in values[1:]:
        result.append(alpha * value + (1.0 - alpha) * result[-1])
    return result
