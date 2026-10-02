"""Execution audit trail primitives.

Pure observability layer. It does not change execution decisions.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ExecutionAuditRecord:
    signal_id: str
    intent_id: str
    status: str
    venue_order_id: str | None = None
    evidence: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionAuditTrail:
    records: list[ExecutionAuditRecord] = field(default_factory=list)

    def append(self, record: ExecutionAuditRecord) -> None:
        self.records.append(record)

    def snapshot(self) -> dict[str, Any]:
        return {
            "count": len(self.records),
            "latest": (
                self.records[-1].__dict__
                if self.records
                else None
            ),
        }
