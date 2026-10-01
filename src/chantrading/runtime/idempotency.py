"""Idempotency contract for canonical Live 1M candles.

The contract is intentionally transport-level: one canonical candle identity
may cause at most one accepted structural-engine input.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Hashable


@dataclass
class CandleIdempotencyLedger:
    """In-memory ledger for identities already admitted to the canonical stream."""

    _accepted: set[Hashable]

    def __init__(self) -> None:
        self._accepted = set()

    def admit(self, identity: Hashable) -> bool:
        """Return True exactly once for an identity; False thereafter."""
        if identity in self._accepted:
            return False
        self._accepted.add(identity)
        return True

    def contains(self, identity: Hashable) -> bool:
        return identity in self._accepted

    def __len__(self) -> int:
        return len(self._accepted)
