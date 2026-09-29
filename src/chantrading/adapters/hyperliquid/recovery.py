"""Deterministic Testnet recovery orchestration."""
from __future__ import annotations
from enum import Enum


class RecoveryState(str, Enum):
    HEALTHY="HEALTHY"
    FREEZE="FREEZE"
    SNAPSHOT="SNAPSHOT"
    REBUILD="REBUILD"
    RECONCILE="RECONCILE"
    REPLAY_VERIFY="REPLAY_VERIFY"
    RESUME="RESUME"
    HALTED="HALTED"


class RecoveryOrchestrator:
    def __init__(self):
        self.state=RecoveryState.HEALTHY
        self.trading_enabled=True

    def trigger(self):
        self.state=RecoveryState.FREEZE
        self.trading_enabled=False

    def snapshot_complete(self):
        if self.state is not RecoveryState.FREEZE:
            raise ValueError("recovery snapshot not expected")
        self.state=RecoveryState.SNAPSHOT

    def rebuild_complete(self):
        if self.state is not RecoveryState.SNAPSHOT:
            raise ValueError("rebuild not expected")
        self.state=RecoveryState.REBUILD

    def reconciliation_complete(self, consistent: bool):
        if self.state is not RecoveryState.REBUILD:
            raise ValueError("reconciliation not expected")
        self.state=RecoveryState.RECONCILE if consistent else RecoveryState.HALTED

    def replay_verified(self, verified: bool):
        if self.state is not RecoveryState.RECONCILE:
            raise ValueError("replay verification not expected")
        self.state=RecoveryState.REPLAY_VERIFY if verified else RecoveryState.HALTED

    def resume(self):
        if self.state is not RecoveryState.REPLAY_VERIFY:
            raise ValueError("resume not authorized")
        self.state=RecoveryState.RESUME
        self.trading_enabled=True
