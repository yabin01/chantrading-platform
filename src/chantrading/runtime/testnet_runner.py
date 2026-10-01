"""Hyperliquid Testnet runtime entrypoint.

First step of the Testnet trading pipeline:
- connect to Hyperliquid Testnet candle stream
- consume ETH 1m candles
- provide a stable runtime entrypoint

This module is intentionally read-only. Execution will be added after the
market-data pipeline is validated.
"""
from __future__ import annotations

import os
from typing import Callable

from chantrading.adapters.hyperliquid.live_testnet import (
    LiveCandle,
    LiveTestnetCandleStream,
)


class TestnetRunner:
    def __init__(self, stream_factory: Callable[..., LiveTestnetCandleStream]):
        self.stream_factory = stream_factory
        self.candles_received = 0
        self.last_candle: LiveCandle | None = None

    def on_candle(self, candle: LiveCandle) -> None:
        self.candles_received += 1
        self.last_candle = candle
        print(
            f"CANDLE {candle.coin} {candle.interval} "
            f"close={candle.close} ts={candle.timestamp_ms}"
        )

    def run(self, coin: str = "ETH", duration_seconds: int = 600) -> int:
        stream = self.stream_factory(self.on_candle)
        return stream.run(coin=coin, duration_seconds=duration_seconds)


def main() -> None:
    raise RuntimeError(
        "Use TestnetRunner with a configured websocket factory. "
        "Direct live connection wiring will be enabled in the next commit."
    )


if __name__ == "__main__":
    main()
