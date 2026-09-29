"""Venue capability registry."""
from dataclasses import dataclass


@dataclass(frozen=True)
class HyperliquidCapabilities:
    reduce_only: bool = True
    post_only: bool = True
    client_order_id: bool = True
    websocket: bool = True
    candle_1m: bool = True
    reconciliation_queries: bool = True

    def supports(self, capability: str) -> bool:
        return bool(getattr(self, capability, False))
