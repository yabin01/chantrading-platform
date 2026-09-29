from chantrading.adapters.hyperliquid.order_lifecycle import OrderLifecycle, OrderState, resolve_order_status


def test_unknown_must_not_be_retryable():
    o = OrderLifecycle(OrderState.UNKNOWN)
    assert not o.retry_allowed


def test_filled_is_terminal():
    o = OrderLifecycle(OrderState.RESTING)
    o.transition(OrderState.FILLED, 11)
    assert o.execution_final
    assert o.native_oid == 11


def test_status_resolution():
    assert resolve_order_status({"status": "unknownOid"}) is OrderState.UNKNOWN
    assert resolve_order_status({"order": {"status": "open"}}) is OrderState.RESTING
    assert resolve_order_status({"order": {"status": "filled"}}) is OrderState.FILLED
    assert resolve_order_status({"order": {"status": "rejected"}}) is OrderState.REJECTED
