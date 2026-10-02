"""Hyperliquid Testnet -> live 1M ChanLun runtime bridge."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from chantrading.adapters.hyperliquid.live_testnet import LiveTestnetCandleStream
from chantrading.runtime.live_chanlun import Live1MStructureEngine, LiveStructureEvent
from chantrading.runtime.event_store import SQLiteEventStore
from chantrading.runtime.testnet_signal_execution import TestnetSignalExecutor
from chantrading.runtime.decision_diagnostics import collect_decision_diagnostics
from chantrading.runtime.execution_audit import ExecutionAuditRecord, ExecutionAuditTrail
from chantrading.strategy.live_decision import DecisionSignal, Live1MDecisionEngine


@dataclass
class TestnetRuntime:
    """Live 1M runtime with an optional Testnet signal execution boundary."""

    structure_engine: Live1MStructureEngine = field(default_factory=Live1MStructureEngine)
    decision_engine: Live1MDecisionEngine = field(default_factory=Live1MDecisionEngine)
    received_events: list[LiveStructureEvent] = field(default_factory=list)
    decision_events: list[DecisionSignal] = field(default_factory=list)
    execution_results: list[Any] = field(default_factory=list)
    event_store: SQLiteEventStore | None = None
    signal_executor: TestnetSignalExecutor | None = None
    execution_audit: ExecutionAuditTrail = field(default_factory=ExecutionAuditTrail)
    _event_sequence: int = 0

    def on_candle(self, candle: Any) -> None:
        events = self.structure_engine.on_candle(candle)
        self.received_events.extend(events)
        self._process_decisions(events)
        self._persist(events)

    def _process_decisions(self, events: list[LiveStructureEvent]) -> None:
        for event in events:
            if event.type == "FRACTAL_CONFIRMED":
                fractal = self.structure_engine.latest_fractal
                if fractal is not None:
                    self._record_decisions(self.decision_engine.on_fractal(fractal))
            elif event.type == "CENTER_TERMINATED":
                center_id = event.payload.get("center_id")
                center = next((item for item in self.structure_engine.center.centers if item.id == center_id), None)
                if center is None:
                    continue
                self._record_decisions(self.decision_engine.on_structure(
                    center=center,
                    segments=self.structure_engine.segment.confirmed_segments(),
                    processed_candles=self.structure_engine.fractal.inclusion.processed,
                    latest_fractal=self.structure_engine.latest_fractal,
                ))

    def _record_decisions(self, signals: list[DecisionSignal]) -> None:
        for signal in signals:
            self.decision_events.append(signal)
            if self.signal_executor is not None:
                result = self.signal_executor.execute(signal)
                if result is not None:
                    self.execution_results.append(result)
                    self.execution_audit.append(ExecutionAuditRecord(
                        signal_id=signal.ai_id or "unknown",
                        intent_id=getattr(result, "intent_id", "unknown"),
                        status=getattr(result.status, "value", str(result.status)),
                        venue_order_id=getattr(result, "venue_order_id", None),
                    ))

    def _persist(self, events: list[LiveStructureEvent]) -> None:
        if self.event_store is None:
            return
        for event in events:
            self._event_sequence += 1
            self.event_store.append(
                event_id=f"testnet-runtime-{self._event_sequence}",
                name=event.type,
                timestamp_ms=event.timestamp_ms,
                payload=event.payload,
            )

    def restore_event_count(self) -> int:
        if self.event_store is None:
            return 0
        self._event_sequence = self.event_store.count()
        return self._event_sequence

    def create_candle_stream(self, ws_factory: Any) -> LiveTestnetCandleStream:
        return LiveTestnetCandleStream(ws_factory=ws_factory, on_candle=self.on_candle)

    def diagnostics(self) -> dict[str, Any]:
        return collect_decision_diagnostics(self).as_dict()

    def snapshot(self) -> dict[str, Any]:
        return {
            "structure": self.structure_engine.snapshot(),
            "decision": self.decision_engine.snapshot(),
            "diagnostics": self.diagnostics(),
            "audit": self.execution_audit.snapshot(),
            "runtime_events": len(self.received_events),
            "decision_events": len(self.decision_events),
            "execution_results": len(self.execution_results),
            "stored_events": self.event_store.count() if self.event_store is not None else 0,
            "event_sequence": self._event_sequence,
        }
