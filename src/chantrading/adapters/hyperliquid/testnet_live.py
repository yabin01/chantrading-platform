"""Controlled Hyperliquid Testnet live execution boundary."""
from __future__ import annotations

import os
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from chantrading.adapters.hyperliquid.testnet import Network, TestnetConfig
from chantrading.domain.execution import OrderIntent, OrderStatus, OrderType, Side

TESTNET_API_URL = "https://api.hyperliquid-testnet.xyz"


@dataclass(frozen=True)
class LiveTestnetConfig:
    account_address: str
    api_url: str = TESTNET_API_URL
    network: Network = Network.TESTNET
    confirm_testnet: bool = False

    @classmethod
    def from_env(cls) -> "LiveTestnetConfig":
        return cls(
            account_address=os.environ.get("HL_TESTNET_ACCOUNT", "").strip(),
            api_url=os.environ.get("HL_TESTNET_API_URL", TESTNET_API_URL).strip(),
            confirm_testnet=os.environ.get("HL_TESTNET_CONFIRM", "").strip().upper() == "YES",
        )

    def validate(self) -> None:
        TestnetConfig(self.network, "wss://api.hyperliquid-testnet.xyz/ws", self.api_url).validate()
        if not self.account_address:
            raise ValueError("HL_TESTNET_ACCOUNT is required")
        if not self.account_address.startswith("0x") or len(self.account_address) != 42:
            raise ValueError("HL_TESTNET_ACCOUNT must be a 20-byte 0x address")
        if self.api_url != TESTNET_API_URL:
            raise ValueError("T4 only permits the official Hyperliquid Testnet endpoint")
        if not self.confirm_testnet:
            raise RuntimeError("Testnet order submission requires HL_TESTNET_CONFIRM=YES")


class HyperliquidSdkClient:
    def __init__(self, config: LiveTestnetConfig, wallet: Any):
        config.validate()
        try:
            from hyperliquid.exchange import Exchange
        except ImportError as exc:
            raise RuntimeError("hyperliquid-python-sdk is required for live Testnet execution") from exc
        self.exchange = Exchange(wallet, config.api_url, account_address=config.account_address)

    def submit(self, intent: OrderIntent, limit_price: Decimal) -> dict:
        if intent.order_type not in {OrderType.MARKET, OrderType.LIMIT}:
            raise ValueError("T4 live canary accepts MARKET or LIMIT intents only")
        if intent.quantity <= 0:
            raise ValueError("quantity must be positive")

        tif = "Ioc" if intent.order_type is OrderType.MARKET else "Gtc"
        cloid = None
        if intent.client_order_id:
            try:
                from hyperliquid.utils.types import Cloid
                cloid = Cloid.from_str(intent.client_order_id)
            except (ImportError, TypeError, ValueError) as exc:
                raise ValueError(
                    "client_order_id must be a Hyperliquid Cloid hex string (0x + 32 hex digits)"
                ) from exc

        return self.exchange.order(
            intent.instrument_id,
            intent.side is Side.BUY,
            float(intent.quantity),
            float(limit_price),
            {"limit": {"tif": tif}},
            reduce_only=intent.reduce_only,
            cloid=cloid,
        )

    def cancel(self, instrument_id: str, venue_order_id: int) -> dict:
        return self.exchange.cancel(instrument_id, venue_order_id)

    def query(self, account_address: str, venue_order_id: int) -> dict:
        return self.exchange.info.query_order_by_oid(account_address, venue_order_id)


def classify_order_response(result: dict) -> OrderStatus:
    if not isinstance(result, dict) or result.get("status") != "ok":
        return OrderStatus.REJECTED
    statuses = result.get("response", {}).get("data", {}).get("statuses", [])
    if not statuses:
        return OrderStatus.UNKNOWN
    status = statuses[0]
    if "filled" in status:
        return OrderStatus.FILLED
    if "resting" in status:
        return OrderStatus.OPEN
    if "error" in status:
        return OrderStatus.REJECTED
    return OrderStatus.UNKNOWN
