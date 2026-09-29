"""Signed order gateway; transport remains injectable."""
from __future__ import annotations
from dataclasses import dataclass
from .signing import SigningGateway


@dataclass(frozen=True)
class MutationResult:
    status: str
    response: object | None = None
    request_id: str | None = None


class OrderGateway:
    def __init__(self, signer: SigningGateway, exchange_transport):
        self.signer = signer
        self.exchange_transport = exchange_transport

    def submit(self, action: dict, nonce: int, expires_after: int | None = None) -> MutationResult:
        signed = self.signer.sign(action, nonce, expires_after)
        response = self.exchange_transport.post_signed(signed)
        return MutationResult("SUBMITTED", response)

    def cancel(self, action: dict, nonce: int, expires_after: int | None = None) -> MutationResult:
        signed = self.signer.sign(action, nonce, expires_after)
        response = self.exchange_transport.post_signed(signed)
        return MutationResult("CANCEL_SUBMITTED", response)
