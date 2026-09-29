"""Runtime supervisor for reconnect, resync and stream health."""
from __future__ import annotations
from dataclasses import dataclass
from .health import HealthState, StreamHealth
from .reconnect import ReconnectPolicy
from .resync import ResyncCoordinator


@dataclass
class SupervisorStatus:
    health: HealthState
    reconnect_attempt: int = 0
    ready: bool = False


class StreamSupervisor:
    def __init__(self, websocket_manager, info_client, policy: ReconnectPolicy | None = None):
        self.ws = websocket_manager
        self.resync = ResyncCoordinator(info_client)
        self.policy = policy or ReconnectPolicy()
        self.health = StreamHealth()
        self.status = SupervisorStatus(self.health.state)

    def on_disconnect(self) -> None:
        self.ws.mark_resyncing()
        self.health.mark_resyncing()
        self.status.ready = False
        self.status.health = self.health.state

    def on_pong(self, now_ms: int) -> None:
        self.health.observe_pong(now_ms)

    def on_event(self, now_ms: int) -> None:
        self.health.observe_event(now_ms)

    def resynchronize(self, user: str, instrument: str, coin: str = "ETH") -> bool:
        result = self.resync.synchronize(user, instrument, coin)
        if not result.success:
            self.status.health = HealthState.STALE
            self.status.ready = False
            return False
        self.health.observe_event(0)
        self.status.health = HealthState.HEALTHY
        self.status.ready = True
        return True
