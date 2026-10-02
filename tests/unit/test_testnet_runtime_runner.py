from chantrading.adapters.hyperliquid.live_testnet import LiveCandle, LiveTestnetCandleStream
from chantrading.runtime.testnet_runtime import TestnetRuntime
from chantrading.runtime.testnet_runtime_runner import TestnetRuntimeRunner, build_live_runner


class FakeStream:
    def __init__(self, on_candle):
        self.on_candle = on_candle
        self.calls = []

    def run(self, coin, duration_seconds):
        self.calls.append((coin, duration_seconds))
        self.on_candle(
            LiveCandle(
                coin="ETH",
                interval="1m",
                timestamp_ms=1000,
                open="100",
                high="101",
                low="99",
                close="100.5",
                volume="1",
            )
        )
        return 1


def test_runner_feeds_stream_candles_into_runtime():
    runtime = TestnetRuntime()
    holder = {}

    def factory(on_candle):
        stream = FakeStream(on_candle)
        holder["stream"] = stream
        return stream

    runner = TestnetRuntimeRunner(runtime, factory)

    assert runner.run("ETH", 7) == 1
    assert holder["stream"].calls == [("ETH", 7)]
    assert len(runtime.received_events) == 1
    assert runtime.received_events[0].type == "CANDLE_ACCEPTED"
    assert runtime.structure_engine.fractal.inclusion.processed


def test_build_live_runner_uses_testnet_stream():
    runtime = TestnetRuntime()
    runner = build_live_runner(runtime)
    assert isinstance(runner, TestnetRuntimeRunner)


def test_runner_captures_stream_health_snapshot():
    runtime = TestnetRuntime()
    class HealthyStream(FakeStream):
        def health_snapshot(self):
            return {"received": 3, "reconnects": 1, "gap_count": 2, "last_candle_ts": 2000}

    holder = {}
    def factory(on_candle):
        stream = HealthyStream(on_candle)
        holder["stream"] = stream
        return stream

    runner = TestnetRuntimeRunner(runtime, factory)
    assert runner.run("ETH", 1) == 1
    assert runner.last_stream_health == {
        "received": 3, "reconnects": 1, "gap_count": 2, "last_candle_ts": 2000
    }


def test_runner_marks_unhealthy_stream_when_gap_or_reconnect_present():
    runtime = TestnetRuntime()
    class UnhealthyStream(FakeStream):
        def health_snapshot(self):
            return {"received": 3, "reconnects": 1, "gap_count": 2, "last_candle_ts": 2000}
    runner = TestnetRuntimeRunner(runtime, lambda on_candle: UnhealthyStream(on_candle))
    runner.run("ETH", 1)
    assert runner.stream_health_ok is False


def test_runner_marks_healthy_stream_without_gap_or_reconnect():
    runtime = TestnetRuntime()
    class HealthyStream(FakeStream):
        def health_snapshot(self):
            return {"received": 3, "reconnects": 0, "gap_count": 0, "last_candle_ts": 2000}
    runner = TestnetRuntimeRunner(runtime, lambda on_candle: HealthyStream(on_candle))
    runner.run("ETH", 1)
    assert runner.stream_health_ok is True
