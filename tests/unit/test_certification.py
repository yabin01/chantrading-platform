from chantrading.adapters.hyperliquid.certification import (
    Gate, Network, evaluate_certification, production_authorized,
)
from chantrading.runtime.certification import (
    CertificationPrecheck, CertificationStatus, TestnetCertificationRun,
)
import pytest


def test_incomplete_certification_blocks():
    result=evaluate_certification(Network.MAINNET, {Gate.TESTS, Gate.HEALTH})
    assert not result.certified
    assert not production_authorized(result)


def test_testnet_never_authorizes_production():
    result=evaluate_certification(Network.TESTNET, set(Gate))
    assert result.certified
    assert not production_authorized(result)


def test_all_mainnet_gates_are_required():
    result=evaluate_certification(Network.MAINNET, set(Gate))
    assert result.certified
    assert production_authorized(result)


def ok():
    return CertificationPrecheck(True, True, True, True, True)


def test_runtime_certification_requires_precheck():
    c=TestnetCertificationRun(1000)
    with pytest.raises(RuntimeError):
        c.start(100)


def test_runtime_clean_run_passes():
    c=TestnetCertificationRun(1000)
    assert c.run_precheck(ok())
    c.start(100)
    c.runner.set_replay_equivalent(True)
    report=c.stop(1100)
    assert c.status is CertificationStatus.PASSED
    assert report.drift_events==0


def test_runtime_drift_fails_certification():
    c=TestnetCertificationRun(1000)
    c.run_precheck(ok())
    c.start(100)
    c.runner.record_drift()
    c.runner.set_replay_equivalent(True)
    c.stop(1100)
    assert c.status is CertificationStatus.FAILED


def test_runtime_replay_mismatch_fails_certification():
    c=TestnetCertificationRun(1000)
    c.run_precheck(ok())
    c.start(100)
    c.runner.set_replay_equivalent(False)
    c.stop(1100)
    assert c.status is CertificationStatus.FAILED
