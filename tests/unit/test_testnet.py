from chantrading.adapters.hyperliquid.testnet import (
    Candle, Network, TestnetConfig, TestnetExecutionGate, validate_candle_continuity,
)


def config():
    return TestnetConfig(
        Network.TESTNET,
        "wss://api.hyperliquid-testnet.xyz/ws",
        "https://api.hyperliquid-testnet.xyz",
    )


def test_testnet_config_accepts_1m():
    config().validate()


def test_mainnet_cannot_enter_testnet_boundary():
    try:
        TestnetConfig(Network.MAINNET, "ws", "http").validate()
        assert False
    except ValueError:
        pass


def test_candle_continuity():
    candles=[
        Candle(0,1,1,1,1,1),
        Candle(60_000,1,1,1,1,1),
        Candle(120_000,1,1,1,1,1),
    ]
    assert validate_candle_continuity(candles)


def test_candle_gap_is_detected():
    candles=[Candle(0,1,1,1,1,1), Candle(120_000,1,1,1,1,1)]
    assert not validate_candle_continuity(candles)


def test_testnet_execution_gate():
    assert TestnetExecutionGate(config()).authorize()
