"""Controlled Hyperliquid Testnet live execution boundary.

This module intentionally requires explicit Testnet configuration and an
explicit caller confirmation before any order is submitted. No private key
is read by the core runtime until the injected SDK Exchange is constructed.
"""
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
        TestnetConfig(
            network=self.network,
            ws_url="wss://api.hyperliquid-testnet.xyz/ws",
            api_url=self.api_url,
        ).validate()
        if not self.account_address:
            raise ValueError("HL_TESTNET_ACCOUNT is required")
        if not self.account_address.startswith("0x") or len(self.account_address) != 42:
            raise ValueError("HL_TESTNET_ACCOUNT must be a 20-byte 0x address")
        if self.api_url != TESTNET_API_URL:
            raise ValueError("T4 only permits the official Hyperliquid Testnet endpoint")
        if not self.confirm_testnet:
            raise RuntimeError("Testnet order submission requires HL_TESTNET_CONFIRM=YES")


class HyperliquidSdkClient:
    """Lazy SDK boundary. Construction fails clearly if the SDK is absent."""

    def __init__(self, config: LiveTestnetConfig, wallet: Any):
        config.validate()
        try:
            from hyperliquid.exchange import Exchange
        except ImportError as exc:
            raise RuntimeError(
                "hyperliquid-python-sdk is required for live Testnet execution"
            ) from exc
        self.exchange = Exchange(
            wallet,
            config.api_url,
            account_address=config.account_address,
        )

    def submit(self, intent: OrderIntent, limit_price: Decimal) -> dict:
        if intent.order_type is not OrderType.MARKET:
            raise ValueError("T4 live canary currently accepts MARKET intents only")
        if intent.quantity <= 0:
            raise ValueError("quantity must be positive")
        return self.exchange.order(
            intent.instrument_id,
            intent.side is Side.BUY,
            float(intent.quantity),
            float(limit_price),
            {"limit": {"tif": "Ioc"}},
            reduce_only=intent.reduce_only,
            cloid=intent.client_order_id,
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
