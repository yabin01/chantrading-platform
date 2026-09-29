"""Durable append-only runtime event store backed by SQLite."""
from __future__ import annotations
from dataclasses import dataclass
import json
import sqlite3
from pathlib import Path
from typing import Any, Iterable


@dataclass(frozen=True)
class StoredEvent:
    sequence: int
    name: str
    timestamp_ms: int
    payload: dict[str, Any]


class SQLiteEventStore:
    def __init__(self, path: str | Path):
        self.path=str(path)
        self._db=sqlite3.connect(self.path)
        self._db.execute(
            """CREATE TABLE IF NOT EXISTS runtime_events (
                sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                timestamp_ms INTEGER NOT NULL,
                payload_json TEXT NOT NULL
            )"""
        )
        self._db.commit()

    def append(self, event_id: str, name: str, timestamp_ms: int, payload: dict[str, Any]):
        try:
            cur=self._db.execute(
                "INSERT INTO runtime_events(event_id,name,timestamp_ms,payload_json) VALUES(?,?,?,?)",
                (event_id,name,timestamp_ms,json.dumps(payload,sort_keys=True,separators=(",",":"))),
            )
            self._db.commit()
            return cur.lastrowid
        except sqlite3.IntegrityError as exc:
            if "event_id" in str(exc):
                return None
            raise

    def iter_events(self) -> Iterable[StoredEvent]:
        rows=self._db.execute(
            "SELECT sequence,name,timestamp_ms,payload_json FROM runtime_events ORDER BY sequence"
        )
        for sequence,name,timestamp_ms,payload_json in rows:
            yield StoredEvent(sequence,name,timestamp_ms,json.loads(payload_json))

    def count(self) -> int:
        return int(self._db.execute("SELECT COUNT(*) FROM runtime_events").fetchone()[0])

    def close(self):
        self._db.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
