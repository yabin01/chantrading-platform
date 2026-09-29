"""Runtime wiring between event bus and soak recorder."""
from __future__ import annotations
import json
from .event_bus import RuntimeEvent, RuntimeEventBus
from .soak_report import SoakTestRecorder
from .soak_runner import SoakRunConfig, SoakTestRunner


EVENT_TO_COUNTER = {
    "ORDER_ACCEPTED": "order",
    "FILL_CONFIRMED": "fill",
    "WS_RECONNECTED": "reconnect",
    "RECOVERY_COMPLETED": "recovery",
    "RECONCILIATION_DRIFT": "drift",
    "WATCHDOG_EVENT": "watchdog",
}


class SoakRuntime:
    def __init__(self, config: SoakRunConfig, clock_ms=None):
        self.runner = SoakTestRunner(config, clock_ms=clock_ms)
        self.bus = RuntimeEventBus()

    def start(self, started_at_ms=None) -> SoakTestRecorder:
        recorder = self.runner.start(started_at_ms)
        for name, method_name in EVENT_TO_COUNTER.items():
            self.bus.subscribe(name, getattr(self.runner, "record_" + method_name))
        return recorder

    def publish(self, name: str, timestamp_ms: int, payload=None):
        self.bus.publish(RuntimeEvent(name, timestamp_ms, payload or {}))

    def set_replay_equivalent(self, value: bool):
        self.runner.set_replay_equivalent(value)

    def stop(self, ended_at_ms=None):
        return self.runner.stop(ended_at_ms)

    def export_json(self, ended_at_ms=None):
        return self.stop(ended_at_ms).to_json()
