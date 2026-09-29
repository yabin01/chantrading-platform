"""Authoritative order-status query boundary."""
from __future__ import annotations


class OrderStatusResolver:
    def __init__(self, info_client):
        self.info_client = info_client

    def by_oid(self, user: str, oid: int) -> dict:
        return self.info_client.order_status(user, oid)

    def by_cloid(self, user: str, cloid: str) -> dict:
        return self.info_client.order_status(user, cloid)
