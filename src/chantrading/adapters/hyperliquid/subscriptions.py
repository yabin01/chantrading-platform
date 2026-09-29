"""Certified subscription builders."""
from __future__ import annotations


def candle_1m(coin: str) -> dict:
    return {"type": "candle", "coin": coin, "interval": "1m"}


def user_events(user: str) -> dict:
    return {"type": "userEvents", "user": user}


def user_fills(user: str) -> dict:
    return {"type": "userFills", "user": user}


def order_updates(user: str) -> dict:
    return {"type": "orderUpdates", "user": user}
