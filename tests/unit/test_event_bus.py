from chantrading.runtime.event_bus import RuntimeEvent, RuntimeEventBus


def test_event_bus_is_deterministic():
    bus=RuntimeEventBus()
    seen=[]
    bus.subscribe("X", lambda event: seen.append(event.payload["n"]))
    bus.publish(RuntimeEvent("X", 1, {"n": 1}))
    bus.publish(RuntimeEvent("X", 2, {"n": 2}))
    assert seen == [1, 2]
    assert [e.timestamp_ms for e in bus.history] == [1, 2]
