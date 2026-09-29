"""Hyperliquid Testnet integration boundary."""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum


class Network(str, Enum):
    TESTNET="testnet"
    MAINNET="mainnet"


@dataclass(frozen=True)
class TestnetConfig:
    network: Network
    ws_url: str
    api_url: str
    symbol: str = "ETH"
    interval: str = "1m"

    def validate(self) -> None:
        if self.network is not Network.TESTNET:
            raise ValueError("Testnet adapter requires TESTNET network")
        if not self.ws_url or not self.api_url:
            raise ValueError("Testnet endpoints are required")
        if self.interval != "1m":
            raise ValueError("ChanLun testnet validation requires 1m candles")


@dataclass(frozen=True)
class Candle:
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float


def validate_candle_continuity(candles: list[Candle], interval_ms: int = 60_000) -> bool:
    if len(candles) < 2:
        return True
    ordered=sorted(candles, key=lambda x: x.timestamp)
    return all(b.timestamp - a.timestamp == interval_ms for a,b in zip(ordered, ordered[1:]))


class TestnetExecutionGate:
    def __init__(self, config: TestnetConfig):
        config.validate()
        self.config=config

    def authorize(self) -> bool:
        return self.config.network is Network.TESTNET
