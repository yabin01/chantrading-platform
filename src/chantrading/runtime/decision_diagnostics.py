"""Decision diagnostics helpers.

Diagnostics are observational only. They must not alter trading decisions
or execution behavior.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DecisionDiagnostics:
    """Immutable diagnostic view of decision runtime state."""

    decision_count: int
    execution_count: int
    pending_trigger_side: str | None
    pending_trigger_ai_id: str | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "decision_count": self.decision_count,
            "execution_count": self.execution_count,
            "pending_trigger_side": self.pending_trigger_side,
            "pending_trigger_ai_id": self.pending_trigger_ai_id,
        }


def collect_decision_diagnostics(runtime: Any) -> DecisionDiagnostics:
    """Collect runtime diagnostics without changing runtime state."""
    decision = runtime.decision_engine.snapshot()
    return DecisionDiagnostics(
        decision_count=len(runtime.decision_events),
        execution_count=len(runtime.execution_results),
        pending_trigger_side=decision.get("pending_trigger_side"),
        pending_trigger_ai_id=decision.get("pending_trigger_ai_id"),
    )
