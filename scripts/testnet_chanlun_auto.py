"""Run the real ChanLun 1M decision pipeline against Hyperliquid Testnet."""
from __future__ import annotations

import os

from chantrading.adapters.hyperliquid.testnet_live import (
    HyperliquidSdkClient,
    LiveTestnetConfig,
)
from chantrading.runtime.testnet_runtime import TestnetRuntime
from chantrading.runtime.testnet_runtime_runner import build_live_runner
from chantrading.runtime.testnet_signal_execution import (
    TestnetAutoExecutionConfig,
    TestnetSignalExecutor,
)


def build_runtime() -> TestnetRuntime:
    config = LiveTestnetConfig.from_env()
    config.validate()

    private_key = os.environ.get("HL_TESTNET_PRIVATE_KEY", "").strip()
    if not private_key:
        raise RuntimeError("HL_TESTNET_PRIVATE_KEY is required and must never be committed")

    try:
        from eth_account import Account
    except ImportError as exc:
        raise RuntimeError("eth-account is required for Testnet execution") from exc

    wallet = Account.from_key(private_key)
    if wallet.address.lower() != config.account_address.lower():
        raise RuntimeError("private key address does not match HL_TESTNET_ACCOUNT")

    auto = TestnetAutoExecutionConfig.from_env()
    auto.validate()
    client = HyperliquidSdkClient(config, wallet)
    executor = TestnetSignalExecutor(client=client, config=auto)

    return TestnetRuntime(signal_executor=executor)


def main() -> int:
    runtime = build_runtime()
    duration = int(os.environ.get("HL_TESTNET_RUN_SECONDS", "600"))
    coin = os.environ.get("HL_TESTNET_INSTRUMENT", "ETH").strip() or "ETH"

    runner = build_live_runner(runtime)

    print("TESTNET_AUTO_EXECUTION: ENABLED")
    print("TESTNET_INSTRUMENT:", coin)
    print("TESTNET_DURATION_SECONDS:", duration)
    print("TESTNET_ORDER_SIZE:", TestnetAutoExecutionConfig.from_env().quantity)

    received = runner.run(coin=coin, duration_seconds=duration)

    print("CANDLES_RECEIVED:", received)
    print("DECISION_EVENTS:", len(runtime.decision_events))
    print("EXECUTION_RESULTS:", len(runtime.execution_results))
    print("RUNTIME_SNAPSHOT:", runtime.snapshot())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
