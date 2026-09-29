"""Hyperliquid WebSocket lifecycle supervisor."""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Callable

class StreamState(str, Enum):
    DISCONNECTED="DISCONNECTED"; CONNECTING="CONNECTING"; CONNECTED="CONNECTED"; RESYNCING="RESYNCING"; READY="READY"; STOPPED="STOPPED"

@dataclass
class Subscription:
    subscription_id: str
    payload: dict
    callback: Callable[[dict], None]
    snapshot_required: bool = True

class HyperliquidWebSocketManager:
    def __init__(self, transport=None):
        self.transport=transport; self.state=StreamState.DISCONNECTED
        self.subscriptions={}; self.snapshot_received=set(); self.last_pong_ms=None

    def register(self, subscription): self.subscriptions[subscription.subscription_id]=subscription
    def connect(self):
        if self.transport is None: raise RuntimeError("WebSocket transport is not configured")
        self.state=StreamState.CONNECTING
        self.transport.connect(self.on_message,self.on_close)
    def on_open(self):
        self.state=StreamState.CONNECTED
        for s in self.subscriptions.values():
            self.transport.send({"method":"subscribe","subscription":s.payload})
    def on_message(self,message,now_ms=None):
        if message.get("channel")=="pong":
            self.last_pong_ms=now_ms; return
        sid=message.get("_subscription_id")
        if sid in self.subscriptions and self.state in {StreamState.CONNECTED,StreamState.RESYNCING}:
            self.subscriptions[sid].callback(message)
    def on_close(self):
        if self.state != StreamState.STOPPED:
            self.state=StreamState.RESYNCING; self.snapshot_received.clear()
    def mark_snapshot(self,subscription_id):
        self.snapshot_received.add(subscription_id)
        required={s.subscription_id for s in self.subscriptions.values() if s.snapshot_required}
        if required.issubset(self.snapshot_received): self.state=StreamState.READY
    def mark_resyncing(self):
        self.state=StreamState.RESYNCING; self.snapshot_received.clear()
    def stop(self):
        self.state=StreamState.STOPPED
        if self.transport is not None: self.transport.close()
