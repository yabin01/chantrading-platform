from chantrading.runtime.event_store import SQLiteEventStore
from chantrading.runtime.testnet_runtime import TestnetRuntime


def test_runtime_recovery_restores_stored_events_and_sequence():
    store = SQLiteEventStore(":memory:")
    store.append(
        event_id="e1",
        name="CANDLE_ACCEPTED",
        timestamp_ms=1000,
        payload={"coin": "ETH", "interval": "1m"},
    )

    runtime = TestnetRuntime(event_store=store)

    assert runtime.recover_from_store() == 1
    assert runtime.snapshot()["event_sequence"] == 1
    assert runtime.snapshot()["runtime_events"] == 1
