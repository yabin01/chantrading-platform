from chantrading.adapters.hyperliquid.recovery import RecoveryOrchestrator, RecoveryState


def test_recovery_freezes_trading_until_verified():
    r=RecoveryOrchestrator()
    r.trigger()
    assert r.state is RecoveryState.FREEZE
    assert r.trading_enabled is False
    r.snapshot_complete()
    r.rebuild_complete()
    r.reconciliation_complete(True)
    r.replay_verified(True)
    r.resume()
    assert r.state is RecoveryState.RESUME
    assert r.trading_enabled is True


def test_inconsistent_reconciliation_halts():
    r=RecoveryOrchestrator()
    r.trigger()
    r.snapshot_complete()
    r.rebuild_complete()
    r.reconciliation_complete(False)
    assert r.state is RecoveryState.HALTED
    assert r.trading_enabled is False


def test_replay_failure_halts():
    r=RecoveryOrchestrator()
    r.trigger()
    r.snapshot_complete()
    r.rebuild_complete()
    r.reconciliation_complete(True)
    r.replay_verified(False)
    assert r.state is RecoveryState.HALTED
    assert r.trading_enabled is False
