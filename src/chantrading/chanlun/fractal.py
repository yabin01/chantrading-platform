"""Deterministic three-ProcessedCandle fractal engine."""
from __future__ import annotations
from dataclasses import dataclass, field
from .inclusion import InclusionProcessor
from .models import Candle, Fractal, FractalStatus, FractalType


@dataclass(frozen=True)
class FractalEvent:
    type: str
    fractal_id: str
    fractal: Fractal


@dataclass
class FractalEngine:
    inclusion: InclusionProcessor = field(default_factory=InclusionProcessor)
    fractals: dict[str, Fractal] = field(default_factory=dict)
    _by_center: dict[int, str] = field(default_factory=dict)

    def update(self, candle: Candle, raw_index: int | None = None) -> list[FractalEvent]:
        self.inclusion.update(candle, raw_index)
        candles = self.inclusion.processed
        if len(candles) < 3:
            return []

        center = len(candles) - 2
        left, mid, right = candles[-3:]
        events: list[FractalEvent] = []

        old_id = self._by_center.get(center)
        new_type = self._classify(left, mid, right)
        if old_id is not None:
            old = self.fractals[old_id]
            if new_type is None or old.type != new_type:
                old.status = FractalStatus.INVALIDATED
                events.append(FractalEvent("FRACTAL_INVALIDATED", old.id, old))
                del self._by_center[center]
            else:
                return events

        if new_type is None:
            return events

        fractal_id = f"F_{mid.end_timestamp}_{center}_{new_type.value}"
        fractal = Fractal(
            id=fractal_id,
            type=new_type,
            center_index=center,
            confirm_index=len(candles) - 1,
            top=mid.high,
            bottom=mid.low,
            source_processed_ids=(left.index, mid.index, right.index),
        )
        self.fractals[fractal_id] = fractal
        self._by_center[center] = fractal_id
        events.append(FractalEvent("FRACTAL_CONFIRMED", fractal_id, fractal))
        return events

    @staticmethod
    def _classify(left, mid, right) -> FractalType | None:
        if (
            mid.high > left.high and mid.high > right.high
            and mid.low > left.low and mid.low > right.low
        ):
            return FractalType.TOP
        if (
            mid.low < left.low and mid.low < right.low
            and mid.high < left.high and mid.high < right.high
        ):
            return FractalType.BOTTOM
        return None

    def confirmed_fractals(self) -> list[Fractal]:
        return [
            f for f in self.fractals.values()
            if f.status == FractalStatus.CONFIRMED
        ]

    def active_candidate(self):
        return None
