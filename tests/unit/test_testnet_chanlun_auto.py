import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).parents[2] / "scripts" / "testnet_chanlun_auto.py"
SPEC = importlib.util.spec_from_file_location("testnet_chanlun_auto", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)
build_runtime = MODULE.build_runtime


class FakeWallet:
    address = "0x94368f8B3AcC189d1cE9455C5b0CEB9B8864a24B"


def test_build_runtime_assembles_execution_boundary(monkeypatch):
    monkeypatch.setenv("HL_TESTNET_ACCOUNT", FakeWallet.address)
    monkeypatch.setenv("HL_TESTNET_PRIVATE_KEY", "0x" + "11" * 32)
    monkeypatch.setenv("HL_TESTNET_CONFIRM", "YES")
    monkeypatch.setenv("HL_TESTNET_AUTO_EXECUTE", "YES")
    monkeypatch.setenv("HL_TESTNET_ORDER_SIZE", "0.01")

    class FakeAccount:
        @staticmethod
        def from_key(_):
            return FakeWallet()

    import eth_account
    monkeypatch.setattr(eth_account, "Account", FakeAccount)

    import chantrading.adapters.hyperliquid.testnet_live as live
    monkeypatch.setattr(live.HyperliquidSdkClient, "__init__", lambda self, config, wallet: None)

    import chantrading.runtime.testnet_signal_execution as execution
    monkeypatch.setattr(
        execution.TestnetSignalExecutor,
        "__post_init__",
        lambda self: None,
    )

    runtime = build_runtime()

    assert runtime.signal_executor is not None
    assert runtime.signal_executor.config.enabled is True
    assert runtime.signal_executor.config.quantity > 0
