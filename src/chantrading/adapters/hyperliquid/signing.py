"""Signing boundary for Hyperliquid L1 actions.

The domain never receives private keys. A signer is injected and may live in
an MPC/HSM/process-isolated gateway in production.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol


class ActionSigner(Protocol):
    def sign(self, action: dict, nonce: int, expires_after: int | None, mainnet: bool) -> object: ...


@dataclass(frozen=True)
class SignedAction:
    action: dict
    nonce: int
    expires_after: int | None
    signature: object
    mainnet: bool


class SigningGateway:
    def __init__(self, signer: ActionSigner, mainnet: bool = False):
        self.signer = signer
        self.mainnet = mainnet

    def sign(self, action: dict, nonce: int, expires_after: int | None = None) -> SignedAction:
        if nonce <= 0:
            raise ValueError("nonce must be positive")
        return SignedAction(
            action=action,
            nonce=nonce,
            expires_after=expires_after,
            signature=self.signer.sign(action, nonce, expires_after, self.mainnet),
            mainnet=self.mainnet,
        )
