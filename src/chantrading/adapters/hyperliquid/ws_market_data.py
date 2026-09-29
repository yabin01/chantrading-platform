"""Hyperliquid Testnet WebSocket market-data boundary."""
from __future__ import annotations
import json
from dataclasses import dataclass
from typing import Callable


TESTNET_WS_URL = "wss://api.hyperliquid-testnet.xyz/ws"


@dataclass(frozen=True)
class CandleEvent:
    coin: str
    interval: str
    timestamp: int
    open: str
    high: str
    low: str
    close: str
    volume: str


def parse_candle_message(message: str | bytes) -> CandleEvent:
    payload = json.loads(message)
    data = payload.get("data", {})
    if data.get("channel") != "candle":
        raise ValueError("not a candle message")
    candle = data.get("data")
    if not candle:
        raise ValueError("missing candle payload")
    return CandleEvent(
        coin=str(candle["s"]),
        interval=str(candle["i"]),
        timestamp=int(candle["t"]),
        open=str(candle["o"]),
        high=str(candle["h"]),
        low=str(candle["l"]),
        close=str(candle["c"]),
        volume=str(candle["v"]),
    )


def candle_subscription(coin: str, interval: str = "1m") -> dict:
    if interval != "1m":
        raise ValueError("ChanLun integration requires 1m candles")
    return {
        "method": "subscribe",
        "subscription": {"type": "candle", "coin": coin, "interval": interval},
    }


class WebSocketMarketDataTransport:
    def __init__(self, ws_factory: Callable, on_candle: Callable[[CandleEvent], None]):
        self.ws_factory = ws_factory
        self.on_candle = on_candle
        self.connected = False

    def connect(self):
        self.ws = self.ws_factory(TESTNET_WS_URL)
        self.connected = True

    def subscribe(self, coin: str):
        self.ws.send(json.dumps(candle_subscription(coin)))
    
    def handle_message(self, message: str | bytes):
        event = parse_candle_message(message)
        self.on_candle(event)

    def mark_disconnected(self):
        self.connected = False
