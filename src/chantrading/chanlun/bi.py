"""Strict ChanLun Bi engine.

Rules implemented here:
- A Bi is formed only by adjacent effective TOP/BOTTOM fractals.
- The two fractal centers must have at least one complete ProcessedCandle
  strictly between them (center index difference >= 2).
- TOP -> BOTTOM is DOWN; BOTTOM -> TOP is UP.
- Same-type consecutive fractals do not form a Bi. A more extreme same-type
  fractal supersedes the previous endpoint.
- If an already-emitted Bi endpoint is superseded, the Bi is revised in place
  and a BI_ENDPOINT_REVISED event is emitted. Downstream engines must consume
  revision events rather than assuming historical endpoints are immutable.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .models import Fractal, FractalStatus, FractalType


class BiDirection(str, Enum):
    UP = "UP"
    DOWN = "DOWN"


class BiState(str, Enum):
    BUILDING = "BUILDING"
    EXTENDING = "EXTENDING"


@dataclass
class Bi:
    id: str
    start_fractal_id: str
    end_fractal_id: str
    start_center_index: int
    end_center_index: int
    start_price: float
    end_price: float
    direction: BiDirection
    state: BiState = BiState.BUILDING

    @property
    def processed_candles_between(self) -> int:
        return self.end_center_index - self.start_center_index - 1


@dataclass(frozen=True)
class BiEvent:
    type: str
    bi_id: str | None
    fractal_id: str
    bi: Bi | None = None
    previous_fractal_id: str | None = None


@dataclass
class BiEngine:
    """Consumes confirmed fractals in chronological order."""

    fractals: dict[str, Fractal] = field(default_factory=dict)
    bis: list[Bi] = field(default_factory=list)
    _anchor: Fractal | None = None
    _last_input_center: int = -1

    def update(self, fractal: Fractal) -> list[BiEvent]:
        if fractal.status != FractalStatus.CONFIRMED:
            return []

        # Determinism guard: a replayed event must not create a duplicate Bi.
        if fractal.center_index < self._last_input_center:
            raise ValueError(
                "Fractals must be supplied in non-decreasing center_index order"
            )
        if fractal.id in self.fractals:
            return []
        self._last_input_center = fractal.center_index
        self.fractals[fractal.id] = fractal

        if self._anchor is None:
            self._anchor = fractal
            return [BiEvent("BI_ANCHOR_SET", None, fractal.id)]

        anchor = self._anchor

        # Same type: keep only the more extreme endpoint.
        if fractal.type == anchor.type:
            if not self._more_extreme(fractal, anchor):
                return [BiEvent("FRACTAL_IGNORED_SAME_TYPE", None, fractal.id)]

            old_id = anchor.id
            self._anchor = fractal

            if self.bis and self.bis[-1].end_fractal_id == old_id:
                bi = self.bis[-1]
                old_end = bi.end_fractal_id
                bi.end_fractal_id = fractal.id
                bi.end_center_index = fractal.center_index
                bi.end_price = self._endpoint_price(fractal)
                bi.state = BiState.EXTENDING
                return [
                    BiEvent(
                        "BI_ENDPOINT_REVISED",
                        bi.id,
                        fractal.id,
                        bi=bi,
                        previous_fractal_id=old_end,
                    )
                ]

            return [
                BiEvent(
                    "FRACTAL_SUPERSEDED",
                    None,
                    fractal.id,
                    previous_fractal_id=old_id,
                )
            ]

        # Opposite fractal: strict minimum separation is one processed candle.
        if fractal.center_index - anchor.center_index < 2:
            # Do not consume the opposite fractal as a Bi endpoint. It remains
            # available as the next anchor only when it is structurally valid.
            return [
                BiEvent(
                    "FRACTAL_REJECTED_NO_INTERMEDIATE_CANDLE",
                    None,
                    fractal.id,
                    previous_fractal_id=anchor.id,
                )
            ]

        if not self._price_order_is_valid(anchor, fractal):
            return [
                BiEvent(
                    "FRACTAL_REJECTED_PRICE_ORDER",
                    None,
                    fractal.id,
                    previous_fractal_id=anchor.id,
                )
            ]

        direction = (
            BiDirection.UP
            if anchor.type == FractalType.BOTTOM
            else BiDirection.DOWN
        )
        bi = Bi(
            id=f"BI_{anchor.id}_{fractal.id}",
            start_fractal_id=anchor.id,
            end_fractal_id=fractal.id,
            start_center_index=anchor.center_index,
            end_center_index=fractal.center_index,
            start_price=self._endpoint_price(anchor),
            end_price=self._endpoint_price(fractal),
            direction=direction,
            state=BiState.BUILDING,
        )
        self.bis.append(bi)
        self._anchor = fractal
        return [BiEvent("BI_CONFIRMED", bi.id, fractal.id, bi=bi)]

    @staticmethod
    def _endpoint_price(fractal: Fractal) -> float:
        return fractal.top if fractal.type == FractalType.TOP else fractal.bottom

    @classmethod
    def _more_extreme(cls, candidate: Fractal, current: Fractal) -> bool:
        if candidate.type == FractalType.TOP:
            return candidate.top > current.top
        return candidate.bottom < current.bottom

    @classmethod
    def _price_order_is_valid(cls, start: Fractal, end: Fractal) -> bool:
        if start.type == FractalType.BOTTOM and end.type == FractalType.TOP:
            return end.top > start.bottom
        if start.type == FractalType.TOP and end.type == FractalType.BOTTOM:
            return end.bottom < start.top
        return False

    def confirmed_bis(self) -> list[Bi]:
        return list(self.bis)

    @property
    def state(self) -> tuple[int, int]:
        """Compatibility state machine.

        First bit: direction (0=DOWN, 1=UP).
        Second bit: phase (0=BUILDING, 1=EXTENDING).
        """
        if not self.bis:
            if self._anchor is None or self._anchor.type == FractalType.TOP:
                return (0, 0)
            return (1, 0)
        bi = self.bis[-1]
        return (
            1 if bi.direction == BiDirection.UP else 0,
            1 if bi.state == BiState.EXTENDING else 0,
        )
