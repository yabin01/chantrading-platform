"""Controlled 1M Hyperliquid Testnet runtime entrypoint."""
from __future__ import annotations

import os
from typing import Any, Callable

from chantrading.adapters.hyperliquid.live_testnet import LiveTestnetCandleStream
from chantrading.runtime.testnet_runtime import TestnetRuntime


class TestnetRuntimeRunner:
    def __init__(
        self,
        runtime: TestnetRuntime,
        stream_factory: Callable[..., LiveTestnetCandleStream],
    ):
        self.runtime = runtime
        self.stream_factory = stream_factory
        self.last_stream_health: dict[str, Any] | None = None
        self.stream_health_ok: bool | None = None
        self.stream_health_reason: str | None = None

    def on_candle(self, candle: Any) -> None:
        self.runtime.on_candle(candle)

    def run(self, coin: str = "ETH", duration_seconds: int = 600) -> int:
        stream = self.stream_factory(self.on_candle)
        result = stream.run(coin=coin, duration_seconds=duration_seconds)
        health = getattr(stream, "health_snapshot", None)
        if callable(health):
            self.last_stream_health = health()
            self.stream_health_ok, self.stream_health_reason = self._evaluate_stream_health(self.last_stream_health)
        else:
            self.stream_health_ok = None
            self.stream_health_reason = "HEALTH_SNAPSHOT_UNAVAILABLE"
        return result

    @staticmethod
    def _evaluate_stream_health(health: dict[str, Any]) -> tuple[bool, str]:
        if health.get("gap_count", 0):
            return False, "CANDLE_GAP_DETECTED"
        if health.get("reconnects", 0):
            return False, "WEBSOCKET_RECONNECTED"
        return True, "HEALTHY"


def websocket_factory(url: str) -> Any:
    from websocket import create_connection

    return create_connection(
        url,
        timeout=float(os.environ.get("HL_TESTNET_WS_TIMEOUT", "30")),
    )


def build_live_runner(runtime: TestnetRuntime) -> TestnetRuntimeRunner:
    def stream_factory(on_candle):
        from chantrading.adapters.hyperliquid.live_testnet import LiveTestnetCandleStream

        return LiveTestnetCandleStream(
            ws_factory=websocket_factory,
            on_candle=on_candle,
        )

    return TestnetRuntimeRunner(runtime, stream_factory)
