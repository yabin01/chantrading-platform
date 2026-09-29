"""Testnet order submission mapping; signing remains an external boundary."""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class SignedAction:
    action: dict
    signature: object
    client_order_id: str


def build_order_action(request, asset: int, price: str | None = None) -> dict:
    if request.order_type not in {"LIMIT", "MARKET"}:
        raise ValueError("unsupported order type")
    side = "B" if request.side.upper() == "BUY" else "A"
    order = {
        "a": asset,
        "b": side == "B",
        "p": price or "0",
        "s": request.quantity,
        "r": request.reduce_only,
        "t": {"limit": {"tif": "Gtc"}} if request.order_type == "LIMIT" else {"market": {}},
    }
    return {"type": "order", "orders": [order], "grouping": "na"}


class SigningGateway:
    def sign(self, action: dict, client_order_id: str) -> SignedAction:
        raise NotImplementedError("real signer must be injected")


class TestnetOrderSubmitter:
    def __init__(self, exchange_post, signer: SigningGateway):
        self.exchange_post = exchange_post
        self.signer = signer

    def submit(self, request, asset: int, price: str | None = None):
        action = build_order_action(request, asset, price)
        signed = self.signer.sign(action, request.client_order_id)
        return self.exchange_post(signed)
