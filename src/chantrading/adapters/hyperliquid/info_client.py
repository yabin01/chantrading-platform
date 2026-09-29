"""Read-only Hyperliquid Info API client."""
from __future__ import annotations

from .rest import HyperliquidRestClient


class HyperliquidInfoClient:
    def __init__(self, rest: HyperliquidRestClient) -> None:
        self.rest = rest

    def meta(self) -> object:
        return self.rest.post_info({"type": "meta"})

    def clearinghouse_state(self, user: str, dex: str | None = None) -> object:
        payload = {"type": "clearinghouseState", "user": user}
        if dex:
            payload["dex"] = dex
        return self.rest.post_info(payload)

    def open_orders(self, user: str, dex: str | None = None) -> object:
        payload = {"type": "openOrders", "user": user}
        if dex:
            payload["dex"] = dex
        return self.rest.post_info(payload)

    def user_fills(self, user: str, aggregate_by_time: bool = False) -> object:
        return self.rest.post_info({
            "type": "userFills",
            "user": user,
            "aggregateByTime": aggregate_by_time,
        })

    def order_status(self, user: str, oid: int | str) -> object:
        return self.rest.post_info({
            "type": "orderStatus",
            "user": user,
            "oid": oid,
        })

    def candle_snapshot(
        self,
        coin: str,
        interval: str = "1m",
        start_time_ms: int | None = None,
        end_time_ms: int | None = None,
    ) -> object:
        req = {"coin": coin, "interval": interval}
        if start_time_ms is not None:
            req["startTime"] = start_time_ms
        if end_time_ms is not None:
            req["endTime"] = end_time_ms
        return self.rest.post_info({
            "type": "candleSnapshot",
            "req": req,
        })
