"""Transport-neutral WebSocket supervisor for Hyperliquid."""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Callable


class StreamState(str, Enum):
    DISCONNECTED = "DISCONNECTED"
    CONNECTING = "CONNECTING"
    CONNECTED = "CONNECTED"
    RESYNCING = "RESYNCING"
    READY = "READY"
    STOPPED = "STOPPED"


@dataclass
class Subscription:
    subscription_id: str
    payload: dict
    callback: Callable[[dict], None]
    snapshot_required: bool = True


class HyperliquidWebSocketManager:
    """Lifecycle shell.

    A concrete transport can be injected later; this layer owns state,
    subscriptions and reconnect/resync semantics.
    """

    def __init__(self, transport=None):
        self.transport = transport
        self.state = StreamState.DISCONNECTED
        self.subscriptions: dict[str, Subscription] = {}
        self.snapshot_received: set[str] = set()

    def register(self, subscription: Subscription) -> None:
        self.subscriptions[subscription.subscription_id] = subscription

    def mark_connected(self) -> None:
        self.state = StreamState.CONNECTED

    def mark_resyncing(self) -> None:
        self.state = StreamState.RESYNCING
        self.snapshot_received.clear()

    def mark_snapshot(self, subscription_id: str) -> None:
        self.snapshot_received.add(subscription_id)
        required = {
            sid for sid, sub in self.subscriptions.items() if sub.snapshot_required
        }
        if required.issubset(self.snapshot_received):
            self.state = StreamState.READY

    def mark_disconnected(self) -> None:
        self.state = StreamState.DISCONNECTED

    def stop(self) -> None:
        self.state = StreamState.STOPPED
        if self.transport is not None:
            self.transport.close()
