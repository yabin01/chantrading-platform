from pathlib import Path

from chantrading.adapters.hyperliquid.live_testnet import LiveCandle
from chantrading.runtime.event_store import SQLiteEventStore
from chantrading.runtime.testnet_runtime import TestnetRuntime


def _candle(ts: int = 1) -> LiveCandle:
    return LiveCandle(
        coin="ETH",
        interval="1m",
        timestamp_ms=ts,
        open="100",
        high="101",
        low="99",
        close="100",
        volume="1",
    )


def test_runtime_restore_event_sequence_after_restart(tmp_path: Path):
    db = tmp_path / "runtime.db"

    with SQLiteEventStore(db) as store:
        runtime = TestnetRuntime(event_store=store)
        runtime.on_candle(_candle(1))
        assert store.count() == 1

        restarted = TestnetRuntime(event_store=store)
        assert restarted.restore_event_count() == 1
        assert restarted.snapshot()["event_sequence"] == 1

        restarted.on_candle(_candle(2))
        assert store.count() == 2

        ids = [event.name for event in store.iter_events()]
        assert ids == ["CANDLE_ACCEPTED", "CANDLE_ACCEPTED"]
