"""Testnet-only bridge from ChanLun DecisionSignal to live execution."""
from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass, field
from decimal import Decimal

from chantrading.adapters.hyperliquid.testnet_live import HyperliquidSdkClient
from chantrading.domain.execution import ExecutionResult, OrderType, TimeInForce
from chantrading.strategy.live_decision import DecisionSignal, SignalSide
from chantrading.strategy.signal_order_intent import OrderIntentContext, SignalToOrderIntent


@dataclass(frozen=True)
class TestnetAutoExecutionConfig:
    instrument_id: str = "ETH"
    quantity: Decimal = Decimal("0.01")
    enabled: bool = False

    @classmethod
    def from_env(cls) -> "TestnetAutoExecutionConfig":
        raw_quantity = os.environ.get("HL_TESTNET_ORDER_SIZE", "0.01").strip()
        return cls(
            instrument_id=os.environ.get("HL_TESTNET_INSTRUMENT", "ETH").strip() or "ETH",
            quantity=Decimal(raw_quantity),
            enabled=os.environ.get("HL_TESTNET_AUTO_EXECUTE", "").strip().upper() == "YES",
        )

    def validate(self) -> None:
        if not self.instrument_id:
            raise ValueError("HL_TESTNET_INSTRUMENT must not be empty")
        if self.quantity <= 0:
            raise ValueError("HL_TESTNET_ORDER_SIZE must be positive")
        if self.quantity > Decimal("0.01"):
            raise ValueError("T5 Testnet auto-execution is capped at 0.01 units")


@dataclass
class TestnetSignalExecutor:
    """Execute each newly emitted eligible signal at most once."""

    client: HyperliquidSdkClient
    config: TestnetAutoExecutionConfig
    translator: SignalToOrderIntent = field(default_factory=SignalToOrderIntent)
    executed_signal_ids: set[str] = field(default_factory=set)

    def __post_init__(self) -> None:
        self.config.validate()
        if not self.config.enabled:
            raise RuntimeError("T5 auto-execution requires HL_TESTNET_AUTO_EXECUTE=YES")

    def execute(self, signal: DecisionSignal) -> ExecutionResult | None:
        if signal.side is SignalSide.HOLD:
            return None
        if signal.trigger_fractal_id is None:
            raise ValueError("cannot execute signal without confirmed trigger fractal")

        signal_id = self._signal_id(signal)
        if signal_id in self.executed_signal_ids:
            return None

        client_order_id = self._cloid(signal_id)
        context = OrderIntentContext(
            instrument_id=self.config.instrument_id,
            quantity=self.config.quantity,
            decision_id=signal.ai_id or "decision-unknown",
            signal_id=signal_id,
            client_order_id=client_order_id,
            order_type=OrderType.MARKET,
            time_in_force=TimeInForce.IOC,
        )
        intent = self.translator.build(signal, context)
        if intent is None:
            return None

        price = self._marketable_price(intent.side)
        result = self.client.submit(intent, price)
        self.executed_signal_ids.add(signal_id)
        return self.client.execution_result(intent, result)

    @staticmethod
    def _signal_id(signal: DecisionSignal) -> str:
        material = "|".join((
            signal.ai_id or "",
            signal.comparison_ai_id or "",
            signal.trigger_fractal_id or "",
            signal.side.value,
        ))
        return "SIG-" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:24]

    @staticmethod
    def _cloid(signal_id: str) -> str:
        digest = hashlib.sha256(signal_id.encode("utf-8")).hexdigest()[:32]
        return "0x" + digest

    def _marketable_price(self, side) -> Decimal:
        raw = self.client.exchange._slippage_price(
            self.config.instrument_id,
            side.value == "BUY",
            0.05,
        )
        return Decimal(str(raw))
