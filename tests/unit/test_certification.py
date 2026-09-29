from chantrading.adapters.hyperliquid.certification import (
    Gate, Network, evaluate_certification, production_authorized,
)


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
