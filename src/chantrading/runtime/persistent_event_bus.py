"""Event bus with durable persistence."""
from __future__ import annotations
import hashlib
import json
from .event_bus import RuntimeEvent, RuntimeEventBus
from .event_store import SQLiteEventStore


class PersistentRuntimeEventBus(RuntimeEventBus):
    def __init__(self, store: SQLiteEventStore):
        super().__init__()
        self.store=store

    @staticmethod
    def event_id(event: RuntimeEvent) -> str:
        raw=json.dumps(
            {"name":event.name,"timestamp_ms":event.timestamp_ms,"payload":event.payload},
            sort_keys=True,separators=(",",":"),
        ).encode()
        return hashlib.sha256(raw).hexdigest()

    def publish(self, event: RuntimeEvent):
        event_id=self.event_id(event)
        sequence=self.store.append(event_id,event.name,event.timestamp_ms,event.payload)
        if sequence is None:
            return False
        super().publish(event)
        return True
