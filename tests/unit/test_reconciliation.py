from decimal import Decimal
from chantrading.adapters.hyperliquid.reconciliation import (
    DriftType, ReconciliationEngine, reconcile_fills, reconcile_orders, reconcile_position,
)


def test_order_drift_is_detected():
    drifts = reconcile_orders({"1": {"oid": 1}}, [{"oid": 2}])
    assert {d.kind for d in drifts} == {DriftType.MISSING_VENUE_ORDER, DriftType.MISSING_LOCAL_ORDER}


def test_unprocessed_and_duplicate_fills():
    fills = [{"tid": 7, "oid": 1}, {"tid": 7, "oid": 1}]
    drifts = reconcile_fills(set(), fills)
    assert sum(d.kind is DriftType.UNPROCESSED_FILL for d in drifts) == 2
    assert sum(d.kind is DriftType.DUPLICATE_FILL for d in drifts) == 1


def test_position_drift():
    drifts = reconcile_position(Decimal("1"), Decimal("1.01"))
    assert drifts[0].kind is DriftType.POSITION_DRIFT


def test_consistent_report():
    report = ReconciliationEngine().reconcile(
        {"1": {"oid": 1}}, [{"oid": 1}], {"7"}, [{"tid": 7, "oid": 1}],
        Decimal("1"), Decimal("1"),
    )
    assert report.consistent
