"""Machine-readable extended Testnet soak-test report."""
from __future__ import annotations
from dataclasses import dataclass, asdict
import json


@dataclass
class SoakMetrics:
    started_at_ms: int
    ended_at_ms: int | None = None
    orders: int = 0
    fills: int = 0
    reconnects: int = 0
    recoveries: int = 0
    drift_events: int = 0
    watchdog_events: int = 0
    halted_duration_ms: int = 0
    replay_equivalent: bool | None = None

    @property
    def duration_ms(self):
        if self.ended_at_ms is None:
            return None
        return max(0, self.ended_at_ms - self.started_at_ms)

    def to_dict(self):
        data=asdict(self)
        data["duration_ms"]=self.duration_ms
        return data

    def to_json(self):
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))


class SoakTestRecorder:
    def __init__(self, started_at_ms: int):
        self.metrics=SoakMetrics(started_at_ms)

    def order(self, count=1):
        self.metrics.orders += count

    def fill(self, count=1):
        self.metrics.fills += count

    def reconnect(self, count=1):
        self.metrics.reconnects += count

    def recovery(self, count=1):
        self.metrics.recoveries += count

    def drift(self, count=1):
        self.metrics.drift_events += count

    def watchdog(self, count=1):
        self.metrics.watchdog_events += count

    def set_replay_equivalent(self, value: bool):
        self.metrics.replay_equivalent=value

    def finish(self, ended_at_ms: int):
        self.metrics.ended_at_ms=ended_at_ms
        return self.metrics
