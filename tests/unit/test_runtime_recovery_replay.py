from chantrading.runtime.event_store import SQLiteEventStore
from chantrading.runtime.recovery import RuntimeRecovery


def test_runtime_recovery_replays_events(tmp_path):
    store = SQLiteEventStore(tmp_path / "events.db")
    store.append("e1", "CANDLE_ACCEPTED", 1, {"coin": "ETH"})

    seen = []
    result = RuntimeRecovery(store).replay(lambda event: seen.append(event.name))

    assert seen == ["CANDLE_ACCEPTED"]
    assert result.restored_events == 1
    assert result.latest_sequence == 1
