from chantrading.runtime.event_store import SQLiteEventStore
from chantrading.runtime.testnet_runtime import TestnetRuntime


def test_runtime_recover_from_store_restores_sequence(tmp_path):
    store = SQLiteEventStore(str(tmp_path / "events.db"))
    store.append(
        event_id="e1",
        name="CANDLE_ACCEPTED",
        timestamp_ms=1000,
        payload={"coin": "ETH"},
    )

    runtime = TestnetRuntime(event_store=store)

    assert runtime.recover_from_store() == 1
    assert runtime.snapshot()["event_sequence"] == 1
