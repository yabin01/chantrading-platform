"""Sequential left-to-right K-line inclusion processing."""
from __future__ import annotations
from dataclasses import dataclass, field
from .models import Candle, ProcessedCandle


@dataclass
class InclusionProcessor:
    processed: list[ProcessedCandle] = field(default_factory=list)
    direction: int | None = None
    _raw_counter: int = 0

    def _bootstrap_direction(self, candle: Candle) -> int:
        prev = self.processed[-1]
        if candle.close > prev.close:
            return 1
        if candle.close < prev.close:
            return -1
        prev_mid = (prev.high + prev.low) / 2.0
        cur_mid = (candle.high + candle.low) / 2.0
        return 1 if cur_mid >= prev_mid else -1

    @staticmethod
    def _contains(last: ProcessedCandle, candle: Candle) -> bool:
        return (
            last.high >= candle.high and last.low <= candle.low
        ) or (
            candle.high >= last.high and candle.low <= last.low
        )

    def update(self, candle: Candle, raw_index: int | None = None) -> ProcessedCandle:
        if raw_index is None:
            raw_index = self._raw_counter
        self._raw_counter = max(self._raw_counter, raw_index + 1)

        if not self.processed:
            item = ProcessedCandle(
                index=0,
                start_timestamp=candle.timestamp,
                end_timestamp=candle.timestamp,
                open=candle.open,
                high=candle.high,
                low=candle.low,
                close=candle.close,
                volume=candle.volume,
                source_raw_ids=[raw_index],
            )
            self.processed.append(item)
            return item

        if self.direction is None:
            self.direction = self._bootstrap_direction(candle)

        last = self.processed[-1]
        if self._contains(last, candle):
            if self.direction > 0:
                last.high = max(last.high, candle.high)
                last.low = max(last.low, candle.low)
            else:
                last.high = min(last.high, candle.high)
                last.low = min(last.low, candle.low)
            last.end_timestamp = candle.timestamp
            last.close = candle.close
            last.volume += candle.volume
            last.source_raw_ids.append(raw_index)
            return last

        if candle.high > last.high and candle.low > last.low:
            self.direction = 1
        elif candle.high < last.high and candle.low < last.low:
            self.direction = -1

        item = ProcessedCandle(
            index=len(self.processed),
            start_timestamp=candle.timestamp,
            end_timestamp=candle.timestamp,
            open=candle.open,
            high=candle.high,
            low=candle.low,
            close=candle.close,
            volume=candle.volume,
            source_raw_ids=[raw_index],
        )
        self.processed.append(item)
        return item
