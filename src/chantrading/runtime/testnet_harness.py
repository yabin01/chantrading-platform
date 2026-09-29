"""Extended Testnet runtime harness and failure-injection boundary."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum


class RuntimeStatus(str, Enum):
    STARTING="STARTING"
    RUNNING="RUNNING"
    DEGRADED="DEGRADED"
    RECOVERING="RECOVERING"
    HALTED="HALTED"
    STOPPED="STOPPED"


@dataclass
class RuntimeMetrics:
    heartbeat_count: int = 0
    reconnect_count: int = 0
    recovery_count: int = 0
    order_count: int = 0
    fill_count: int = 0
    drift_count: int = 0
    last_heartbeat_ms: int | None = None


@dataclass
class TestnetRuntimeHarness:
    status: RuntimeStatus = RuntimeStatus.STARTING
    metrics: RuntimeMetrics = field(default_factory=RuntimeMetrics)
    trading_enabled: bool = False

    def start(self):
        if self.status not in {RuntimeStatus.STARTING, RuntimeStatus.STOPPED}:
            raise ValueError("runtime already started")
        self.status=RuntimeStatus.RUNNING
        self.trading_enabled=True

    def heartbeat(self, timestamp_ms: int):
        if self.status not in {RuntimeStatus.RUNNING, RuntimeStatus.DEGRADED}:
            raise ValueError("heartbeat not accepted")
        self.metrics.heartbeat_count += 1
        self.metrics.last_heartbeat_ms = timestamp_ms

    def websocket_disconnect(self):
        if self.status is RuntimeStatus.RUNNING:
            self.status=RuntimeStatus.DEGRADED
            self.trading_enabled=False

    def websocket_reconnect(self):
        if self.status is not RuntimeStatus.DEGRADED:
            raise ValueError("reconnect not expected")
        self.metrics.reconnect_count += 1
        self.status=RuntimeStatus.RECOVERING
        self.metrics.recovery_count += 1

    def recovery_complete(self, consistent: bool):
        if self.status is not RuntimeStatus.RECOVERING:
            raise ValueError("recovery not active")
        self.status=RuntimeStatus.RUNNING if consistent else RuntimeStatus.HALTED
        self.trading_enabled=consistent

    def record_order(self):
        if not self.trading_enabled:
            raise RuntimeError("trading is disabled")
        self.metrics.order_count += 1

    def record_fill(self):
        self.metrics.fill_count += 1

    def record_drift(self):
        self.metrics.drift_count += 1
        self.trading_enabled=False
        self.status=RuntimeStatus.RECOVERING

    def stop(self):
        self.trading_enabled=False
        self.status=RuntimeStatus.STOPPED
