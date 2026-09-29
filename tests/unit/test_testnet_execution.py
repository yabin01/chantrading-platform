from chantrading.adapters.hyperliquid.testnet_execution import (
    OrderState, TestnetExecutionLifecycle, TestnetOrderRequest, transition,
)


def req(i="cl-1"):
    return TestnetOrderRequest(i,"ETH","BUY","0.01","LIMIT")


def test_lifecycle_reaches_fill():
    l=TestnetExecutionLifecycle()
    l.create(req())
    l.update("cl-1",OrderState.SIGNING)
    l.update("cl-1",OrderState.SUBMITTED,"oid-1")
    l.update("cl-1",OrderState.OPEN,"oid-1")
    final=l.update("cl-1",OrderState.FILLED,"oid-1","0.01")
    assert final.state is OrderState.FILLED
    assert final.filled_quantity=="0.01"


def test_unknown_cannot_be_blindly_recreated():
    l=TestnetExecutionLifecycle()
    l.create(req())
    l.update("cl-1",OrderState.UNKNOWN)
    assert not l.can_retry("cl-1")
    try:
        transition(OrderState.UNKNOWN,OrderState.CREATED)
        assert False
    except ValueError:
        pass


def test_terminal_order_cannot_change():
    assert transition(OrderState.FILLED,OrderState.FILLED) is OrderState.FILLED
    try:
        transition(OrderState.FILLED,OrderState.CANCELED)
        assert False
    except ValueError:
        pass


def test_duplicate_client_order_id_rejected():
    l=TestnetExecutionLifecycle()
    l.create(req())
    try:
        l.create(req())
        assert False
    except ValueError:
        pass
