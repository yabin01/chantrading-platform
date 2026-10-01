from chantrading.runtime.idempotency import CandleIdempotencyLedger


def test_first_identity_is_admitted():
    ledger = CandleIdempotencyLedger()
    assert ledger.admit(("ETH", "1m", 60_000)) is True


def test_same_identity_is_admitted_only_once():
    ledger = CandleIdempotencyLedger()
    identity = ("ETH", "1m", 60_000)
    assert ledger.admit(identity) is True
    assert ledger.admit(identity) is False
    assert ledger.admit(identity) is False
    assert len(ledger) == 1


def test_different_timestamp_is_distinct_identity():
    ledger = CandleIdempotencyLedger()
    assert ledger.admit(("ETH", "1m", 60_000)) is True
    assert ledger.admit(("ETH", "1m", 120_000)) is True
    assert len(ledger) == 2


def test_different_symbol_is_distinct_identity():
    ledger = CandleIdempotencyLedger()
    assert ledger.admit(("ETH", "1m", 60_000)) is True
    assert ledger.admit(("BTC", "1m", 60_000)) is True
    assert len(ledger) == 2


def test_payload_identity_can_distinguish_conflicting_versions():
    ledger = CandleIdempotencyLedger()
    original = ("ETH", "1m", 60_000, "10", "8", "9")
    conflicting = ("ETH", "1m", 60_000, "11", "8", "10")
    assert ledger.admit(original) is True
    assert ledger.admit(conflicting) is True
    assert len(ledger) == 2


def test_contains_does_not_mutate_ledger():
    ledger = CandleIdempotencyLedger()
    identity = ("ETH", "1m", 60_000)
    assert ledger.contains(identity) is False
    assert len(ledger) == 0
