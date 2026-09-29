"""Core models for the first ChanLun engine layer."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum


class FractalType(str, Enum):
    TOP = "TOP"
    BOTTOM = "BOTTOM"


class FractalStatus(str, Enum):
    CANDIDATE = "CANDIDATE"
    CONFIRMED = "CONFIRMED"
    INVALIDATED = "INVALIDATED"
    RELAY = "RELAY"
    SUPERSEDED = "SUPERSEDED"


@dataclass(frozen=True)
class Candle:
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass
class ProcessedCandle:
    index: int
    start_timestamp: int
    end_timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    source_raw_ids: list[int] = field(default_factory=list)


@dataclass
class Fractal:
    id: str
    type: FractalType
    center_index: int
    confirm_index: int
    top: float
    bottom: float
    source_processed_ids: tuple[int, int, int]
    status: FractalStatus = FractalStatus.CONFIRMED
