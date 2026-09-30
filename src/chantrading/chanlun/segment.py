"""Strict ChanLun 1M Segment Engine.

The implementation follows the repository's v1.2 historical specification:
a segment is not confirmed merely because it contains three Bi.  Its
opposite-direction Bi form a FeatureSequence; the sequence is normalized for
inclusion, feature fractals are detected, and TYPE_1 / TYPE_2 termination
rules are applied.

TYPE_2 is deliberately represented as a pending state until the reverse
feature sequence supplies the required opposite feature fractal.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable

from .bi import Bi, BiDirection


class SegmentDirection(str, Enum):
    UP = "UP"
    DOWN = "DOWN"

    @property
    def feature_direction(self) -> BiDirection:
        return BiDirection.DOWN if self is SegmentDirection.UP else BiDirection.UP


class SegmentState(str, Enum):
    EXTENDING = "EXTENDING"
    TYPE_2_PENDING = "TYPE_2_PENDING"
    CONFIRMED = "CONFIRMED"


class BreakType(str, Enum):
    NONE = "NONE"
    TYPE_1 = "TYPE_1"
    TYPE_2 = "TYPE_2"


@dataclass(frozen=True)
class FeatureElement:
    id: str
    source_bi_id: str
    direction: BiDirection
    high: float
    low: float
    start_index: int
    end_index: int


@dataclass(frozen=True)
class StandardFeatureElement:
    id: str
    source_feature_ids: tuple[str, ...]
    source_bi_ids: tuple[str, ...]
    direction: BiDirection
    high: float
    low: float
    start_index: int
    end_index: int


@dataclass(frozen=True)
class FeatureFractal:
    id: str
    type: str
    left_id: str
    center_id: str
    right_id: str
    high: float
    low: float
    has_gap: bool


@dataclass
class Segment:
    id: str
    direction: SegmentDirection
    state: SegmentState
    start_bi_id: str
    current_end_bi_id: str | None
    confirmed_end_bi_id: str | None
    start_index: int
    end_index: int | None
    high: float
    low: float
    feature_elements: list[FeatureElement] = field(default_factory=list)
    standard_features: list[StandardFeatureElement] = field(default_factory=list)
    feature_fractal_id: str | None = None
    break_type: BreakType = BreakType.NONE

    @property
    def confirmed(self) -> bool:
        return self.state is SegmentState.CONFIRMED


@dataclass(frozen=True)
class SegmentEvent:
    type: str
    segment_id: str | None
    bi_id: str | None = None
    feature_fractal_id: str | None = None
    break_type: BreakType = BreakType.NONE
    segment: Segment | None = None


class SegmentEngine:
    """Deterministic segment state machine fed by confirmed Bis."""

    def __init__(self) -> None:
        self.bis: list[Bi] = []
        self.segments: list[Segment] = []
        self._current: Segment | None = None
        self._pending_fractal: FeatureFractal | None = None
        self._pending_reverse_features: list[FeatureElement] = []
        self._pending_reverse_standard: list[StandardFeatureElement] = []
        self._seen_bi_ids: set[str] = set()

    def update(self, bi: Bi) -> list[SegmentEvent]:
        if bi.id in self._seen_bi_ids:
            return []
        if self.bis and bi.start_center_index < self.bis[-1].end_center_index:
            raise ValueError("Bis must be supplied in chronological order")
        self._seen_bi_ids.add(bi.id)
        self.bis.append(bi)

        if self._current is None:
            self._current = self._new_segment(bi)
            return [SegmentEvent("SEGMENT_STARTED", self._current.id, bi.id)]

        current = self._current

        # A confirmed segment starts the next segment with the new Bi.
        if current.state is SegmentState.CONFIRMED:
            self._current = self._new_segment(bi)
            self._clear_pending_type2()
            return [SegmentEvent("SEGMENT_STARTED", self._current.id, bi.id)]

        if current.state is SegmentState.TYPE_2_PENDING:
            reverse_feature = self._feature_from_bi(bi)
            self._pending_reverse_features.append(reverse_feature)
            self._rebuild_pending_reverse(current)
            reverse_fractal = self._detect_reverse_fractal(current)
            if reverse_fractal is None:
                return [SegmentEvent("TYPE_2_REVERSE_FEATURE_ADDED", current.id, bi.id,
                                      self._pending_fractal.id if self._pending_fractal else None,
                                      BreakType.TYPE_2, current)]
            pending = self._pending_fractal
            assert pending is not None
            current.state = SegmentState.CONFIRMED
            current.confirmed_end_bi_id = self._source_end_bi(current, pending)
            current.end_index = self._feature_end_index(current, pending)
            current.break_type = BreakType.TYPE_2
            self.segments.append(current)
            self._clear_pending_type2()
            return [
                SegmentEvent("TYPE_2_REVERSE_FRACTAL_CONFIRMED", current.id, bi.id,
                             reverse_fractal.id, BreakType.TYPE_2, current),
                SegmentEvent("SEGMENT_CONFIRMED", current.id, current.confirmed_end_bi_id,
                             pending.id, BreakType.TYPE_2, current),
            ]

        # A candidate segment can only accept its own direction and then its
        # opposite-direction feature elements.  Same-direction Bis extend the
        # segment skeleton but do not enter the feature sequence.
        if bi.direction == self._bi_direction(current.direction):
            current.current_end_bi_id = bi.id
            current.high = max(current.high, bi.start_price, bi.end_price)
            current.low = min(current.low, bi.start_price, bi.end_price)
            current.end_index = bi.end_center_index
            return [SegmentEvent("SEGMENT_EXTENDED", current.id, bi.id, segment=current)]

        feature = self._feature_from_bi(bi)
        current.feature_elements.append(feature)
        current.current_end_bi_id = bi.id
        current.high = max(current.high, bi.start_price, bi.end_price)
        current.low = min(current.low, bi.start_price, bi.end_price)
        current.end_index = bi.end_center_index
        self._rebuild_standard_features(current)

        events = [
            SegmentEvent("FEATURE_ELEMENT_ADDED", current.id, bi.id, segment=current)
        ]

        fractal = self._detect_target_fractal(current)
        if fractal is None:
            return events

        current.feature_fractal_id = fractal.id
        if not fractal.has_gap:
            current.state = SegmentState.CONFIRMED
            current.confirmed_end_bi_id = self._source_end_bi(current, fractal)
            current.end_index = self._feature_end_index(current, fractal)
            current.break_type = BreakType.TYPE_1
            self.segments.append(current)
            events.append(
                SegmentEvent(
                    "SEGMENT_CONFIRMED",
                    current.id,
                    current.confirmed_end_bi_id,
                    fractal.id,
                    BreakType.TYPE_1,
                    current,
                )
            )
            return events

        # A gap means TYPE_1 is not satisfied.  Keep the segment alive and
        # explicitly enter TYPE_2_PENDING.  Confirmation requires the reverse
        # feature sequence; it is not inferred from the gap alone.
        current.state = SegmentState.TYPE_2_PENDING
        self._pending_fractal = fractal
        self._pending_reverse_features = []
        self._pending_reverse_standard = []
        events.append(
            SegmentEvent(
                "SEGMENT_BREAK_CANDIDATE",
                current.id,
                bi.id,
                fractal.id,
                BreakType.TYPE_2,
                current,
            )
        )
        return events

    def _new_segment(self, bi: Bi) -> Segment:
        direction = (
            SegmentDirection.UP if bi.direction is BiDirection.UP
            else SegmentDirection.DOWN
        )
        return Segment(
            id=f"SEG_{bi.id}",
            direction=direction,
            state=SegmentState.EXTENDING,
            start_bi_id=bi.id,
            current_end_bi_id=bi.id,
            confirmed_end_bi_id=None,
            start_index=bi.start_center_index,
            end_index=bi.end_center_index,
            high=max(bi.start_price, bi.end_price),
            low=min(bi.start_price, bi.end_price),
        )

    @staticmethod
    def _bi_direction(direction: SegmentDirection) -> BiDirection:
        return BiDirection.UP if direction is SegmentDirection.UP else BiDirection.DOWN

    @staticmethod
    def _feature_from_bi(bi: Bi) -> FeatureElement:
        return FeatureElement(
            id=f"FE_{bi.id}",
            source_bi_id=bi.id,
            direction=bi.direction,
            high=max(bi.start_price, bi.end_price),
            low=min(bi.start_price, bi.end_price),
            start_index=bi.start_center_index,
            end_index=bi.end_center_index,
        )

    @staticmethod
    def _merge(left: StandardFeatureElement, right: FeatureElement, upward: bool) -> StandardFeatureElement:
        if upward:
            high = max(left.high, right.high)
            low = max(left.low, right.low)
        else:
            high = min(left.high, right.high)
            low = min(left.low, right.low)
        return StandardFeatureElement(
            id=f"SFE_{left.id}_{right.id}",
            source_feature_ids=left.source_feature_ids + (right.id,),
            source_bi_ids=left.source_bi_ids + (right.source_bi_id,),
            direction=right.direction,
            high=high,
            low=low,
            start_index=left.start_index,
            end_index=right.end_index,
        )

    def _rebuild_standard_features(self, segment: Segment) -> None:
        result: list[StandardFeatureElement] = []
        upward = segment.direction is SegmentDirection.UP

        for raw in segment.feature_elements:
            current = StandardFeatureElement(
                id=f"SFE_{raw.id}",
                source_feature_ids=(raw.id,),
                source_bi_ids=(raw.source_bi_id,),
                direction=raw.direction,
                high=raw.high,
                low=raw.low,
                start_index=raw.start_index,
                end_index=raw.end_index,
            )
            # The first and second elements of a candidate feature
            # fractal straddle the hypothesized turning point.  Lesson 71
            # makes this boundary explicit: they belong to the same feature
            # sequence but are not normalized across the turn.  Containment
            # normalization is applied only from the third element onward.
            if len(result) < 2:
                result.append(current)
                continue

            while result and self._contains(result[-1], current):
                left = result.pop()
                current = self._merge_standard(left, current, upward)
            result.append(current)

        segment.standard_features = result

    @staticmethod
    def _contains(a: StandardFeatureElement, b: StandardFeatureElement) -> bool:
        return (
            (a.low <= b.low and a.high >= b.high)
            or (b.low <= a.low and b.high >= a.high)
        )

    @staticmethod
    def _overlap_or_containment(a: StandardFeatureElement, b: StandardFeatureElement) -> bool:
        return SegmentEngine._contains(a, b)

    @staticmethod
    def _merge_standard(
        left: StandardFeatureElement,
        right: StandardFeatureElement,
        upward: bool,
    ) -> StandardFeatureElement:
        if upward:
            high = max(left.high, right.high)
            low = max(left.low, right.low)
        else:
            high = min(left.high, right.high)
            low = min(left.low, right.low)
        return StandardFeatureElement(
            id=f"SFE_{left.id}_{right.id}",
            source_feature_ids=left.source_feature_ids + right.source_feature_ids,
            source_bi_ids=left.source_bi_ids + right.source_bi_ids,
            direction=right.direction,
            high=high,
            low=low,
            start_index=left.start_index,
            end_index=right.end_index,
        )

    def _detect_target_fractal(self, segment: Segment) -> FeatureFractal | None:
        fs = segment.standard_features
        if len(fs) < 3:
            return None

        left, center, right = fs[-3:]
        if segment.direction is SegmentDirection.UP:
            is_target = center.high >= left.high and center.high >= right.high
            kind = "TOP"
        else:
            is_target = center.low <= left.low and center.low <= right.low
            kind = "BOTTOM"

        if not is_target:
            return None

        has_gap = max(left.low, center.low) > min(left.high, center.high)
        return FeatureFractal(
            id=f"SFF_{left.id}_{center.id}_{right.id}",
            type=kind,
            left_id=left.id,
            center_id=center.id,
            right_id=right.id,
            high=center.high,
            low=center.low,
            has_gap=has_gap,
        )

    @staticmethod
    def _source_end_bi(segment: Segment, fractal: FeatureFractal) -> str:
        for f in reversed(segment.standard_features):
            if f.id == fractal.center_id:
                return f.source_bi_ids[-1]
        return segment.current_end_bi_id or segment.start_bi_id

    @staticmethod
    def _feature_end_index(segment: Segment, fractal: FeatureFractal) -> int:
        for f in segment.standard_features:
            if f.id == fractal.center_id:
                return f.end_index
        return segment.end_index or segment.start_index


    def _clear_pending_type2(self) -> None:
        self._pending_fractal = None
        self._pending_reverse_features = []
        self._pending_reverse_standard = []

    def _rebuild_pending_reverse(self, segment: Segment) -> None:
        result: list[StandardFeatureElement] = []
        upward = segment.direction is SegmentDirection.DOWN
        for raw in self._pending_reverse_features:
            current = StandardFeatureElement(
                id=f"RSFE_{raw.id}",
                source_feature_ids=(raw.id,),
                source_bi_ids=(raw.source_bi_id,),
                direction=raw.direction,
                high=raw.high,
                low=raw.low,
                start_index=raw.start_index,
                end_index=raw.end_index,
            )
            while result and self._overlap_or_containment(result[-1], current):
                left = result.pop()
                current = self._merge_standard(left, current, upward)
            result.append(current)
        self._pending_reverse_standard = result

    def _detect_reverse_fractal(self, segment: Segment) -> FeatureFractal | None:
        fs = self._pending_reverse_standard
        if len(fs) < 3:
            return None
        left, center, right = fs[-3:]
        if segment.direction is SegmentDirection.UP:
            is_target = center.low <= left.low and center.low <= right.low
            kind = "BOTTOM"
        else:
            is_target = center.high >= left.high and center.high >= right.high
            kind = "TOP"
        if not is_target:
            return None
        return FeatureFractal(
            id=f"RSFF_{left.id}_{center.id}_{right.id}",
            type=kind,
            left_id=left.id,
            center_id=center.id,
            right_id=right.id,
            high=center.high,
            low=center.low,
            has_gap=max(left.low, center.low) > min(left.high, center.high),
        )

    def current(self) -> Segment | None:
        return self._current

    def confirmed_segments(self) -> list[Segment]:
        return list(self.segments)

    def snapshot(self) -> dict:
        current = self._current
        return {
            "current_segment_id": current.id if current else None,
            "current_state": current.state.value if current else None,
            "confirmed_segment_ids": [s.id for s in self.segments],
            "pending_feature_fractal_id": (
                self._pending_fractal.id if self._pending_fractal else None
            ),
            "pending_reverse_feature_ids": [
                x.id for x in self._pending_reverse_standard
            ],
        }
