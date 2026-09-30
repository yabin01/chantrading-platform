"""Strict 1M ChanLun Center Engine.

Consumes confirmed same-level Segments and builds the minimum ChanLun
center from the intersection of three consecutive segment price ranges.

This layer deliberately does not create Ai objects, buy/sell signals, or
upgrade the 1M analysis to another timeframe.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .segment import Segment


class CenterState(str, Enum):
    CANDIDATE = "CANDIDATE"
    CONFIRMED = "CONFIRMED"
    EXTENDING = "EXTENDING"
    TERMINATED = "TERMINATED"


class CenterEventType(str, Enum):
    CENTER_CANDIDATE = "CENTER_CANDIDATE"
    CENTER_CONFIRMED = "CENTER_CONFIRMED"
    CENTER_EXTENDED = "CENTER_EXTENDED"
    CENTER_TERMINATED = "CENTER_TERMINATED"
    CENTER_NEW = "CENTER_NEW"
    CENTER_EXPANSION_TOUCH = "CENTER_EXPANSION_TOUCH"


@dataclass
class Center:
    id: str
    state: CenterState
    segment_ids: list[str]
    zg: float
    zd: float
    gg: float
    dd: float
    extension_count: int = 0
    start_index: int | None = None
    end_index: int | None = None
    terminated_by_segment_id: str | None = None

    @property
    def width(self) -> float:
        return self.zg - self.zd

    @property
    def confirmed(self) -> bool:
        return self.state in {
            CenterState.CONFIRMED,
            CenterState.EXTENDING,
        }


@dataclass(frozen=True)
class CenterEvent:
    type: CenterEventType
    center_id: str
    segment_id: str
    center: Center


class CenterEngine:
    """Deterministic 1M center state machine fed by confirmed Segments."""

    def __init__(self) -> None:
        self.segments: list[Segment] = []
        self.centers: list[Center] = []
        self._current: Center | None = None
        self._last_terminated: Center | None = None
        self._seen_segment_ids: set[str] = set()

    def update(self, segment: Segment) -> list[CenterEvent]:
        if segment.id in self._seen_segment_ids:
            return []
        if not segment.confirmed:
            raise ValueError("CenterEngine accepts confirmed segments only")
        if self.segments and segment.start_index < (self.segments[-1].end_index or -1):
            raise ValueError("Segments must be supplied in chronological order")

        self._seen_segment_ids.add(segment.id)
        self.segments.append(segment)

        if self._current is not None and self._overlaps(
            self._current.zd, self._current.zg, segment.low, segment.high
        ):
            self._extend(segment)
            return [
                CenterEvent(
                    CenterEventType.CENTER_EXTENDED,
                    self._current.id,
                    segment.id,
                    self._current,
                )
            ]

        events: list[CenterEvent] = []
        if self._current is not None:
            self._current.state = CenterState.TERMINATED
            self._current.terminated_by_segment_id = segment.id
            self._last_terminated = self._current
            events.append(
                CenterEvent(
                    CenterEventType.CENTER_TERMINATED,
                    self._current.id,
                    segment.id,
                    self._current,
                )
            )
            self._current = None

        if len(self.segments) >= 3:
            a, b, c = self.segments[-3:]
            zd = max(a.low, b.low, c.low)
            zg = min(a.high, b.high, c.high)
            previous = self._last_terminated
            new_center_is_disjoint = previous is None or not self._overlaps(previous.zd, previous.zg, zd, zg)
            if zd < zg and new_center_is_disjoint:
                center = Center(
                    id=f"CENTER_{c.id}",
                    state=CenterState.CONFIRMED,
                    segment_ids=[a.id, b.id, c.id],
                    zg=zg,
                    zd=zd,
                    gg=max(a.high, b.high, c.high),
                    dd=min(a.low, b.low, c.low),
                    extension_count=0,
                    start_index=a.start_index,
                    end_index=c.end_index,
                )
                self.centers.append(center)
                self._current = center
                self._last_terminated = None
                events.append(
                    CenterEvent(
                        CenterEventType.CENTER_NEW if previous is not None else CenterEventType.CENTER_CONFIRMED,
                        center.id,
                        c.id,
                        center,
                    )
                )
            else:
                events.append(
                    CenterEvent(
                        CenterEventType.CENTER_CANDIDATE,
                        f"CANDIDATE_{c.id}",
                        c.id,
                        Center(
                            id=f"CANDIDATE_{c.id}",
                            state=CenterState.CANDIDATE,
                            segment_ids=[a.id, b.id, c.id],
                            zg=zg,
                            zd=zd,
                            gg=max(a.high, b.high, c.high),
                            dd=min(a.low, b.low, c.low),
                            start_index=a.start_index,
                            end_index=c.end_index,
                        ),
                    )
                )
        return events

    def _extend(self, segment: Segment) -> None:
        assert self._current is not None
        self._current.segment_ids.append(segment.id)
        # ZD/ZG define the original center interval and remain fixed.
        self._current.gg = max(self._current.gg, segment.high)
        self._current.dd = min(self._current.dd, segment.low)
        self._current.extension_count += 1
        self._current.end_index = segment.end_index
        self._current.state = CenterState.EXTENDING

    @staticmethod
    def _overlaps(zd: float, zg: float, low: float, high: float) -> bool:
        return max(zd, low) < min(zg, high)

    def latest_relation(self, segment: Segment) -> str:
        """Classify a confirmed Segment against the current center geometry.

        Structural classification only; no trade signal or timeframe change.
        """
        if self._current is None:
            return "NO_CURRENT_CENTER"
        if self._overlaps(self._current.zd, self._current.zg, segment.low, segment.high):
            return "CENTER_EXTENSION"
        if segment.low >= self._current.zg:
            return "ABOVE_CENTER"
        if segment.high <= self._current.zd:
            return "BELOW_CENTER"
        return "NON_OVERLAP"

    def center_bounds(self) -> tuple[float, float] | None:
        if self._current is None:
            return None
        return self._current.zd, self._current.zg

    @staticmethod
    def classify_center_expansion(previous: Center, following: Center) -> str:
        """Detect higher-level center expansion from two same-level centers.

        The higher-level relation is created by overlap of the two centers'
        surrounding fluctuation ranges [DD, GG] while their own center
        intervals [ZD, ZG] remain disjoint. This is a structural fact only.
        """
        centers_overlap = CenterEngine._overlaps(
            previous.zd, previous.zg, following.zd, following.zg
        )
        peripheral_overlap = CenterEngine._overlaps(
            previous.dd, previous.gg, following.dd, following.gg
        )
        if not centers_overlap and peripheral_overlap:
            return "HIGHER_LEVEL_EXPANSION"
        return "NO_HIGHER_LEVEL_EXPANSION"

    CENTER_RELATIONS = (
        "UP_CONTINUATION",
        "DOWN_CONTINUATION",
        "HIGHER_LEVEL_OVERLAP",
        "UNCLASSIFIED",
    )

    @staticmethod
    def classify_center_pair(previous: Center, following: Center) -> str:
        """Classify two same-level centers using Lesson 20 center theorem II.

        Structural relation only. HIGHER_LEVEL_OVERLAP means the pair satisfies
        the theorem-II condition for a higher-level center; it does not change
        the engine's 1M operating timeframe.
        """
        if following.gg < previous.dd:
            return "DOWN_CONTINUATION"
        if following.dd > previous.gg:
            return "UP_CONTINUATION"
        if following.zg < previous.zd and following.gg >= previous.dd:
            return "HIGHER_LEVEL_OVERLAP"
        if following.zd > previous.zg and following.dd <= previous.gg:
            return "HIGHER_LEVEL_OVERLAP"
        return "UNCLASSIFIED"

    def current(self) -> Center | None:
        return self._current

    def confirmed_centers(self) -> list[Center]:
        return list(self.centers)

    def snapshot(self) -> dict:
        return {
            "current_center_id": self._current.id if self._current else None,
            "segments_seen": [x.id for x in self.segments],
            "centers": [
                {
                    "id": c.id,
                    "state": c.state.value,
                    "segment_ids": list(c.segment_ids),
                    "zg": c.zg,
                    "zd": c.zd,
                    "gg": c.gg,
                    "dd": c.dd,
                    "extension_count": c.extension_count,
                }
                for c in self.centers
            ],
        }
