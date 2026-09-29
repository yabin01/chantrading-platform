from chantrading.runtime.event_store import SQLiteEventStore


def test_event_store_is_durable_and_idempotent(tmp_path):
    path=tmp_path/"events.db"
    with SQLiteEventStore(path) as store:
        assert store.append("e1","X",100,{"a":1})==1
        assert store.append("e1","X",100,{"a":1}) is None
        assert store.count()==1

    with SQLiteEventStore(path) as reopened:
        events=list(reopened.iter_events())
        assert len(events)==1
        assert events[0].name=="X"
        assert events[0].payload=={"a":1}
