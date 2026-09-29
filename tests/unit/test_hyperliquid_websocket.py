from chantrading.adapters.hyperliquid.websocket import HyperliquidWebSocketManager, StreamState, Subscription


def test_reconnect_enters_resyncing_and_requires_snapshot():
    ws = HyperliquidWebSocketManager()
    ws.register(Subscription("candle-1m", {"type": "candle"}, lambda _: None))
    ws.register(Subscription("orders", {"type": "orderUpdates"}, lambda _: None))

    ws.mark_connected()
    ws.mark_resyncing()
    assert ws.state is StreamState.RESYNCING

    ws.mark_snapshot("candle-1m")
    assert ws.state is StreamState.RESYNCING

    ws.mark_snapshot("orders")
    assert ws.state is StreamState.READY


def test_subscription_builders():
    from chantrading.adapters.hyperliquid.subscriptions import candle_1m
    assert candle_1m("ETH") == {"type": "candle", "coin": "ETH", "interval": "1m"}
