"""Executable extended Testnet soak-test runner."""
from __future__ import annotations
from dataclasses import dataclass
import time

from .soak_report import SoakTestRecorder


@dataclass(frozen=True)
class SoakRunConfig:
    duration_ms: int
    heartbeat_interval_ms: int = 1000


class SoakTestRunner:
    def __init__(self, config: SoakRunConfig, clock_ms=None):
        if config.duration_ms <= 0:
            raise ValueError("duration_ms must be positive")
        self.config = config
        self.clock_ms = clock_ms or (lambda: int(time.time() * 1000))
        self.recorder: SoakTestRecorder | None = None
        self.running = False

    def start(self, started_at_ms: int | None = None):
        now = self.clock_ms() if started_at_ms is None else started_at_ms
        self.recorder = SoakTestRecorder(now)
        self.running = True
        return self.recorder

    def record_order(self, count=1):
        self._require_running()
        self.recorder.order(count)

    def record_fill(self, count=1):
        self._require_running()
        self.recorder.fill(count)

    def record_reconnect(self, count=1):
        self._require_running()
        self.recorder.reconnect(count)

    def record_recovery(self, count=1):
        self._require_running()
        self.recorder.recovery(count)

    def record_drift(self, count=1):
        self._require_running()
        self.recorder.drift(count)

    def record_watchdog(self, count=1):
        self._require_running()
        self.recorder.watchdog(count)

    def set_replay_equivalent(self, value: bool):
        self._require_running()
        self.recorder.set_replay_equivalent(value)

    def should_stop(self, now_ms: int | None = None):
        self._require_running()
        now = self.clock_ms() if now_ms is None else now_ms
        return now - self.recorder.metrics.started_at_ms >= self.config.duration_ms

    def stop(self, ended_at_ms: int | None = None):
        self._require_running()
        now = self.clock_ms() if ended_at_ms is None else ended_at_ms
        self.running = False
        return self.recorder.finish(now)

    def _require_running(self):
        if not self.running or self.recorder is None:
            raise RuntimeError("soak test is not running")
