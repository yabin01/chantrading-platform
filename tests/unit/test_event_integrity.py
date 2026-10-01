from dataclasses import dataclass

import pytest

from chantrading.runtime.event_integrity import (
    CanonicalCandleIdentity,
    classify_1m_candle,
)


@dataclass(frozen=True)
class C:
    coin: str = "ETH"
    interval: str = "1m"
    timestamp_ms: int = 60_000
    open: str = "9"
    high: str = "10"
    low: str = "8"
    close: str = "9"
    volume: str = "1"

    def identity(self):
        return CanonicalCandleIdentity(
            self.coin,
            self.interval,
            self.timestamp_ms,
            self.open,
            self.high,
            self.low,
            self.close,
            self.volume,
        )


def test_initial_candle_is_accepted():
    d = classify_1m_candle(C().identity(), None)
    assert d.action == "ACCEPT"
    assert d.reason == "initial_candle"


def test_exact_next_1m_candle_is_accepted():
    d = classify_1m_candle(C( timestamp_ms=120_000).identity(), C().identity())
    assert d.action == "ACCEPT"
    assert d.reason == "contiguous_1m"
    assert d.expected_timestamp_ms == 120_000


def test_identical_timestamp_payload_is_idempotent_duplicate():
    d = classify_1m_candle(C().identity(), C().identity())
    assert d.action == "DROP_DUPLICATE"
    assert d.reason == "identical_timestamp_payload"


def test_conflicting_duplicate_is_resync():
    d = classify_1m_candle(
        C(high="11").identity(),
        C().identity(),
    )
    assert d.action == "RESYNC"
    assert d.reason == "conflicting_duplicate_timestamp"


def test_older_timestamp_is_out_of_order():
    d = classify_1m_candle(
        C(timestamp_ms=1).identity(),
        C().identity(),
    )
    assert d.action == "RESYNC"
    assert d.reason == "out_of_order_timestamp"


@pytest.mark.parametrize("timestamp", [120_001, 180_000, 300_000])
def test_non_contiguous_timestamp_is_gap(timestamp):
    d = classify_1m_candle(
        C(timestamp_ms=timestamp).identity(),
        C().identity(),
    )
    assert d.action == "RESYNC"
    assert d.reason == "timestamp_gap"


def test_symbol_change_is_resync():
    d = classify_1m_candle(
        C(coin="BTC", timestamp_ms=120_000).identity(),
        C().identity(),
    )
    assert d.action == "RESYNC"
    assert d.reason == "coin_changed"


def test_non_1m_interval_is_rejected():
    with pytest.raises(ValueError):
        classify_1m_candle(
            C(interval="5m").identity(),
            None,
        )


def test_classifier_is_pure_and_does_not_mutate_inputs():
    previous = C()
    observed = C(timestamp_ms=120_000)
    d = classify_1m_candle(observed.identity(), previous.identity())
    assert d.action == "ACCEPT"
    assert observed == C(timestamp_ms=120_000)
    assert previous == C()
