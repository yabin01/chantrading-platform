from chantrading.runtime.event_store import SQLiteEventStore


def test_event_store_replay_and_latest_sequence(tmp_path):
    store = SQLiteEventStore(tmp_path / "events.db")
    store.append("e1", "A", 1000, {"x": 1})
    store.append("e2", "B", 2000, {"x": 2})

    received = []
    assert store.replay(received.append) == 2
    assert [event.name for event in received] == ["A", "B"]
    assert store.latest_sequence() == 2
    store.close()
