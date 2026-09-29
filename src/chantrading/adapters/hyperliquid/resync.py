"""REST-authoritative resynchronization coordinator."""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class ResyncResult:
    success: bool
    reason: str
    snapshots: dict


class ResyncCoordinator:
    def __init__(self, info_client):
        self.info_client = info_client

    def synchronize(self, user: str, instrument: str, coin: str = "ETH") -> ResyncResult:
        try:
            state = self.info_client.clearinghouse_state(user)
            orders = self.info_client.open_orders(user)
            fills = self.info_client.user_fills(user)
            return ResyncResult(
                True,
                "AUTHORITATIVE_REST_SNAPSHOT",
                {
                    "clearinghouseState": state,
                    "openOrders": orders,
                    "userFills": fills,
                    "instrument": instrument,
                    "coin": coin,
                },
            )
        except Exception as exc:
            return ResyncResult(False, f"REST_RESYNC_FAILED:{type(exc).__name__}", {})
