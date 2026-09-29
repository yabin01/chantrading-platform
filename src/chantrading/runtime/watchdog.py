"""Runtime watchdog, bounded reconnect backoff and safety events."""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum


class RuntimeEventType(str, Enum):
    HEARTBEAT_MISSED="HEARTBEAT_MISSED"
    RECONNECT_SCHEDULED="RECONNECT_SCHEDULED"
    RECOVERY_TIMEOUT="RECOVERY_TIMEOUT"
    SAFETY_FREEZE="SAFETY_FREEZE"
    WATCHDOG_HALTED="WATCHDOG_HALTED"


@dataclass(frozen=True)
class RuntimeEvent:
    type: RuntimeEventType
    timestamp_ms: int
    detail: str = ""


@dataclass(frozen=True)
class BackoffPolicy:
    base_ms: int = 1000
    max_ms: int = 30000

    def delay(self, attempt: int) -> int:
        if attempt < 0:
            raise ValueError("attempt must be non-negative")
        return min(self.max_ms, self.base_ms * (2 ** attempt))


class RuntimeWatchdog:
    def __init__(self, heartbeat_timeout_ms=15000, recovery_timeout_ms=60000, max_reconnect_attempts=8):
        self.heartbeat_timeout_ms=heartbeat_timeout_ms
        self.recovery_timeout_ms=recovery_timeout_ms
        self.max_reconnect_attempts=max_reconnect_attempts
        self.reconnect_attempts=0
        self.events:list[RuntimeEvent]=[]
        self.frozen=False
        self.halted=False

    def check_heartbeat(self, now_ms: int, last_heartbeat_ms: int | None):
        if last_heartbeat_ms is None or now_ms-last_heartbeat_ms > self.heartbeat_timeout_ms:
            self.frozen=True
            event=RuntimeEvent(RuntimeEventType.HEARTBEAT_MISSED,now_ms)
            self.events.append(event)
            return event
        return None

    def schedule_reconnect(self, now_ms: int, policy=BackoffPolicy()):
        if self.reconnect_attempts >= self.max_reconnect_attempts:
            self.halted=True
            event=RuntimeEvent(RuntimeEventType.WATCHDOG_HALTED,now_ms,"max reconnect attempts exceeded")
            self.events.append(event)
            return event
        delay=policy.delay(self.reconnect_attempts)
        self.reconnect_attempts += 1
        event=RuntimeEvent(RuntimeEventType.RECONNECT_SCHEDULED,now_ms,str(delay))
        self.events.append(event)
        return event

    def check_recovery(self, now_ms: int, recovery_started_ms: int | None):
        if recovery_started_ms is None or now_ms-recovery_started_ms <= self.recovery_timeout_ms:
            return None
        self.frozen=True
        event=RuntimeEvent(RuntimeEventType.RECOVERY_TIMEOUT,now_ms)
        self.events.append(event)
        return event

    def reset_after_recovery(self):
        self.reconnect_attempts=0
        self.frozen=False
