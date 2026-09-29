"""Hyperliquid adapter configuration."""
from dataclasses import dataclass


@dataclass(frozen=True)
class HyperliquidConfig:
    base_url: str = "https://api.hyperliquid.xyz"
    websocket_url: str = "wss://api.hyperliquid.xyz/ws"
    account_address: str = ""
    environment: str = "mainnet"
    request_timeout_seconds: float = 10.0
    max_retries: int = 2
