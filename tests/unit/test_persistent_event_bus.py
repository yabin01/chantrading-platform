from chantrading.runtime.event_bus import RuntimeEvent
from chantrading.runtime.event_store import SQLiteEventStore
from chantrading.runtime.persistent_event_bus import PersistentRuntimeEventBus


def test_persistent_bus_persists_before_dispatch(tmp_path):
    path=tmp_path/"events.db"
    with SQLiteEventStore(path) as store:
        bus=PersistentRuntimeEventBus(store)
        seen=[]
        bus.subscribe("X", lambda e: seen.append(e.name))
        assert bus.publish(RuntimeEvent("X",100,{"v":1}))
        assert seen==["X"]
        assert store.count()==1
