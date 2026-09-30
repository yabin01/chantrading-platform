from chantrading.adapters.hyperliquid.live_testnet import LiveCandle
from chantrading.runtime.live_recording import Live1MRecordedRuntime


def c(ts, high="10", low="8", close="9"):
    return LiveCandle("ETH", "1m", ts, close, high, low, close, "1")


def test_live_recording_replay_matches_live(tmp_path):
    with Live1MRecordedRuntime(tmp_path / "runtime.db") as runtime:
        for item in [
            c(1),
            c(60_001, "11", "9", "10"),
            c(120_001, "7", "5", "6"),
            c(180_001, "6", "4", "5"),
            c(240_001, "12", "8", "11"),
        ]:
            runtime.on_candle(item)
        result = runtime.verification()
        assert result.matched
        assert result.candle_count == 5


def test_duplicate_candle_is_not_forwarded_to_engine(tmp_path):
    with Live1MRecordedRuntime(tmp_path / "runtime.db") as runtime:
        first = c(1)
        runtime.on_candle(first)
        runtime.on_candle(first)
        assert runtime.engine.candles_processed == 1
        recovery = [row for row in runtime.store.iter_events() if row.name == "CANDLE_RECOVERY"]
        assert recovery[-1].payload["action"] == "DROP_DUPLICATE"


def test_gap_requires_resync_and_is_not_forwarded(tmp_path):
    with Live1MRecordedRuntime(tmp_path / "runtime.db") as runtime:
        runtime.on_candle(c(1))
        runtime.on_candle(c(120_001))
        assert runtime.resync_required
        assert runtime.engine.candles_processed == 1
        recovery = [row for row in runtime.store.iter_events() if row.name == "CANDLE_RECOVERY"]
        assert recovery[-1].payload["reason"] == "timestamp_gap"


def test_old_accepted_candle_is_dropped_as_idempotent_duplicate(tmp_path):
    with Live1MRecordedRuntime(tmp_path / "runtime.db") as runtime:
        runtime.on_candle(c(1))
        runtime.on_candle(c(60_001))
        runtime.on_candle(c(1))
        assert not runtime.resync_required
        assert runtime.engine.candles_processed == 2
        recovery = [row for row in runtime.store.iter_events() if row.name == "CANDLE_RECOVERY"]
        assert recovery[-1].payload["action"] == "DROP_DUPLICATE"
        assert recovery[-1].payload["reason"] == "accepted_identity_already_seen"


def test_conflicting_duplicate_requires_resync(tmp_path):
    with Live1MRecordedRuntime(tmp_path / "runtime.db") as runtime:
        runtime.on_candle(c(1))
        runtime.on_candle(c(1, high="11"))
        assert runtime.resync_required
        assert runtime.engine.candles_processed == 1
        recovery = [row for row in runtime.store.iter_events() if row.name == "CANDLE_RECOVERY"]
        assert recovery[-1].payload["reason"] == "conflicting_duplicate_timestamp"


def test_disconnect_reconnect_requires_fresh_contiguous_candle(tmp_path):
    with Live1MRecordedRuntime(tmp_path / "runtime.db") as runtime:
        runtime.on_candle(c(1))
        runtime.on_disconnect("socket_closed")
        assert runtime.resync_required
        runtime.on_reconnect()
        assert runtime.connection_generation == 1
        runtime.on_candle(c(60_001))
        assert not runtime.resync_required
        names = [row.name for row in runtime.store.iter_events()]
        assert names == [
            "CANDLE_ACCEPTED",
            "WS_DISCONNECTED",
            "WS_RECONNECTED",
            "CANDLE_ACCEPTED",
        ]


def test_live_recording_keeps_structural_events_separate_from_candles(tmp_path):
    with Live1MRecordedRuntime(tmp_path / "runtime.db") as runtime:
        runtime.on_candle(c(1))
        names = [row.name for row in runtime.store.iter_events()]
        assert names[0] == "CANDLE_ACCEPTED"
        assert all(name != "CANDLE_ACCEPTED" for name in names[1:])


def test_duplicate_is_dropped_without_replaying_structure(tmp_path):
    with Live1MRecordedRuntime(tmp_path/"runtime.db") as runtime:
        first = c(60_000)
        runtime.on_candle(first)
        runtime.on_candle(first)
        names = [row.name for row in runtime.store.iter_events()]
        assert names.count("CANDLE_ACCEPTED") == 1
        assert "CANDLE_RECOVERY" in names
        assert runtime.resync_required is False


def test_resync_gate_requires_fresh_reconnect_before_accepting_candle(tmp_path):
    with Live1MRecordedRuntime(tmp_path/"runtime.db") as runtime:
        runtime.on_candle(c(60_000))
        runtime.on_candle(c(180_000))
        assert runtime.resync_required is True
        processed = runtime.engine.candles_processed

        runtime.on_candle(c(120_000))
        assert runtime.engine.candles_processed == processed
        assert runtime.resync_required is True

        recovery = [
            row for row in runtime.store.iter_events()
            if row.name == "CANDLE_RECOVERY"
        ]
        assert recovery[-1].payload["action"] == "RESYNC_REQUIRED"
        assert recovery[-1].payload["reason"] == "fresh_reconnect_required"

        runtime.on_reconnect()
        runtime.on_candle(c(120_000))
        assert runtime.resync_required is False
        assert runtime.engine.candles_processed == processed + 1


def test_gap_requires_resync_and_recovery_is_contiguous(tmp_path):
    with Live1MRecordedRuntime(tmp_path/"runtime.db") as runtime:
        runtime.on_candle(c(60_000))
        runtime.on_candle(c(180_000))
        assert runtime.resync_required is True

        runtime.on_disconnect("test_gap")
        runtime.on_reconnect()
        runtime.recover([c(120_000), c(180_000)])
        assert runtime.resync_required is False
        assert runtime.connection_generation == 1

        names = [row.name for row in runtime.store.iter_events()]
        assert "WS_DISCONNECTED" in names
        assert "WS_RECONNECTED" in names
        assert "WS_RESYNC_COMPLETE" in names


def test_recovery_verification_excludes_lifecycle_events(tmp_path):
    path = tmp_path / "runtime.db"
    with Live1MRecordedRuntime(path) as runtime:
        runtime.on_candle(c(60_000))
        runtime.on_disconnect("test_gap")
        runtime.on_reconnect()
        runtime.recover([c(120_000), c(180_000)])
        result = runtime.verification()

    assert result.matched
    assert result.candle_count == 3


def test_conflicting_duplicate_enters_resync(tmp_path):
    with Live1MRecordedRuntime(tmp_path/"runtime.db") as runtime:
        runtime.on_candle(c(60_000, "10", "8", "9"))
        runtime.on_candle(c(60_000, "11", "8", "10"))
        assert runtime.resync_required is True


def test_recovery_rejects_out_of_order_batch(tmp_path):
    with Live1MRecordedRuntime(tmp_path/"runtime.db") as runtime:
        runtime.on_candle(c(60_000))
        runtime.on_candle(c(180_000))
        with __import__("pytest").raises(ValueError):
            runtime.recover([c(180_000), c(120_000)])


def test_recovery_rejects_duplicate_batch_without_partial_apply(tmp_path):
    with Live1MRecordedRuntime(tmp_path/"runtime.db") as runtime:
        runtime.on_candle(c(60_000))
        runtime.on_candle(c(180_000))
        processed = runtime.engine.candles_processed
        snapshot = runtime.engine.snapshot()
        event_count = len(list(runtime.store.iter_events()))

        runtime.on_disconnect("test_duplicate_batch")
        runtime.on_reconnect()

        with __import__("pytest").raises(ValueError):
            runtime.recover([c(120_000), c(180_000), c(180_000)])

        assert runtime.engine.candles_processed == processed
        assert runtime.engine.snapshot() == snapshot
        assert len(list(runtime.store.iter_events())) == event_count + 2
        assert runtime.resync_required is True


def test_recovery_rejects_out_of_order_batch_without_partial_apply(tmp_path):
    with Live1MRecordedRuntime(tmp_path/"runtime.db") as runtime:
        runtime.on_candle(c(60_000))
        runtime.on_candle(c(180_000))
        processed = runtime.engine.candles_processed
        snapshot = runtime.engine.snapshot()
        event_count = len(list(runtime.store.iter_events()))

        with __import__("pytest").raises(ValueError):
            runtime.recover([c(120_000), c(180_000), c(240_000), c(300_000)])

        assert runtime.engine.candles_processed == processed
        assert runtime.engine.snapshot() == snapshot
        assert len(list(runtime.store.iter_events())) == event_count
        assert runtime.resync_required is True


def test_restart_restores_idempotency_and_structure(tmp_path):
    path = tmp_path / "runtime.db"
    with Live1MRecordedRuntime(path) as runtime:
        runtime.on_candle(c(60_000))
        runtime.on_candle(c(120_000, "11", "9", "10"))
        snapshot = runtime.engine.snapshot()
        processed = runtime.engine.candles_processed
        generation = runtime.connection_generation

    with Live1MRecordedRuntime(path) as runtime:
        assert runtime.engine.snapshot() == snapshot
        assert runtime.engine.candles_processed == processed
        assert runtime.connection_generation == generation

        decision = runtime.classify_candle(c(60_000))
        assert decision.action == "DROP_DUPLICATE"
        assert runtime.engine.candles_processed == processed


def test_restart_preserves_resync_required_state(tmp_path):
    path = tmp_path / "runtime.db"
    with Live1MRecordedRuntime(path) as runtime:
        runtime.on_candle(c(60_000))
        runtime.on_disconnect("process_restart")

    with Live1MRecordedRuntime(path) as runtime:
        assert runtime.resync_required is True
        assert runtime.connection_generation == 0

        runtime.on_reconnect()
        runtime.recover([c(120_000)])
        assert runtime.resync_required is False
        assert runtime.connection_generation == 1


def test_recovery_state_machine_is_integrated_with_live_runtime(tmp_path):
    from chantrading.runtime.recovery import RecoveryState

    with Live1MRecordedRuntime(tmp_path / "runtime.db") as runtime:
        assert runtime.recovery_state is RecoveryState.HEALTHY
        runtime.on_candle(c(60_000))
        runtime.on_candle(c(180_000))
        assert runtime.recovery_state is RecoveryState.GAP_DETECTED

        runtime.on_reconnect()
        assert runtime.recovery_state is RecoveryState.WAITING_RECONNECT
        runtime.recover([c(120_000)])
        assert runtime.recovery_state is RecoveryState.HEALTHY




def test_successful_recovery_has_deterministic_lifecycle_boundary(tmp_path):
    path = tmp_path / "runtime.db"
    with Live1MRecordedRuntime(path) as runtime:
        runtime.on_candle(c(60_000))
        runtime.on_candle(c(180_000))
        runtime.on_disconnect("test_gap")
        runtime.on_reconnect()
        runtime.recover([c(120_000)])

        rows = list(runtime.store.iter_events())
        names = [row.name for row in rows]
        assert names[-3:] == ["CANDLE_ACCEPTED", "WS_RECOVERY_STARTED", "WS_RESYNC_COMPLETE"]
        complete = rows[-1]
        assert complete.payload["connection_generation"] == 1
        assert complete.payload["batch_size"] == 1
        assert complete.payload["last_candle_timestamp_ms"] == 120_000


def test_recovery_cannot_be_replayed_after_completion(tmp_path):
    with Live1MRecordedRuntime(tmp_path / "runtime.db") as runtime:
        runtime.on_candle(c(60_000))
        runtime.on_candle(c(180_000))
        runtime.on_disconnect("test_gap")
        runtime.on_reconnect()
        runtime.recover([c(120_000)])

        with __import__("pytest").raises(RuntimeError):
            runtime.recover([c(180_000)])

        decision = runtime.classify_candle(c(120_000))
        assert decision.action == "DROP_DUPLICATE"


def test_recovery_completion_survives_restart_without_requiring_resync(tmp_path):
    path = tmp_path / "runtime.db"
    with Live1MRecordedRuntime(path) as runtime:
        runtime.on_candle(c(60_000))
        runtime.on_candle(c(180_000))
        runtime.on_disconnect("test_gap")
        runtime.on_reconnect()
        runtime.recover([c(120_000)])

    with Live1MRecordedRuntime(path) as runtime:
        assert runtime.resync_required is False
        assert runtime.recovery_state.value == "healthy"
        assert runtime.connection_generation == 1
        assert runtime.engine.candles_processed == 3

def test_restart_downgrades_interrupted_recovery_to_gap_detected(tmp_path):
    from chantrading.runtime.recovery import RecoveryState

    path = tmp_path / "runtime.db"
    with Live1MRecordedRuntime(path) as runtime:
        runtime.on_candle(c(60_000))
        runtime.on_disconnect("recovery_restart")
        runtime.on_reconnect()
        assert runtime.recovery_state is RecoveryState.WAITING_RECONNECT
        runtime._append_lifecycle(
            "WS_RECOVERY_STARTED",
            {"last_candle_timestamp_ms": 60_000, "batch_size": 1},
        )

    with Live1MRecordedRuntime(path) as runtime:
        assert runtime.resync_required is True
        assert runtime.recovery_state is RecoveryState.GAP_DETECTED
        runtime.on_reconnect()
        assert runtime.recovery_state is RecoveryState.WAITING_RECONNECT
        runtime.recover([c(120_000)])
        assert runtime.recovery_state is RecoveryState.HEALTHY
        assert runtime.resync_required is False

def test_invalid_recovery_batch_does_not_advance_recovery_state(tmp_path):
    from chantrading.runtime.recovery import RecoveryState

    with Live1MRecordedRuntime(tmp_path / "runtime.db") as runtime:
        runtime.on_candle(c(60_000))
        runtime.on_candle(c(180_000))
        runtime.on_reconnect()
        assert runtime.recovery_state is RecoveryState.WAITING_RECONNECT

        with __import__("pytest").raises(ValueError):
            runtime.recover([c(180_000), c(120_000)])

        assert runtime.recovery_state is RecoveryState.WAITING_RECONNECT
