"""Reconnect backoff and retry policy."""
from __future__ import annotations
from dataclasses import dataclass
import random


@dataclass(frozen=True)
class ReconnectPolicy:
    max_attempts: int = 8
    base_delay_seconds: float = 1.0
    max_delay_seconds: float = 30.0
    jitter_ratio: float = 0.2

    def delay(self, attempt: int, rng=random.random) -> float:
        if attempt < 1:
            raise ValueError("attempt must be >= 1")
        raw = min(self.max_delay_seconds, self.base_delay_seconds * (2 ** (attempt - 1)))
        jitter = raw * self.jitter_ratio * (rng() * 2.0 - 1.0)
        return max(0.0, min(self.max_delay_seconds, raw + jitter))

    def allowed(self, attempt: int) -> bool:
        return 1 <= attempt <= self.max_attempts
