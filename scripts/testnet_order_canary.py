"""One-order Hyperliquid Testnet connectivity canary.

Places a deliberately non-marketable ETH GTC limit order and immediately
cancels it. It verifies credentials, signing, order submission, venue response,
and cancellation without intentionally taking a position.

Required environment:
  HL_TESTNET_ACCOUNT=0x...
  HL_TESTNET_PRIVATE_KEY=0x...
  HL_TESTNET_CONFIRM=YES
"""
from __future__ import annotations
import os
from decimal import Decimal
from chantrading.adapters.hyperliquid.testnet_live import LiveTestnetConfig, HyperliquidSdkClient, classify_order_response
from chantrading.domain.execution import OrderIntent, OrderType, Side, OrderStatus

def main() -> int:
    config = LiveTestnetConfig.from_env()
    config.validate()
    private_key = os.environ.get("HL_TESTNET_PRIVATE_KEY", "").strip()
    if not private_key:
        raise RuntimeError("HL_TESTNET_PRIVATE_KEY is required and must never be committed")
    try:
        from eth_account import Account
    except ImportError as exc:
        raise RuntimeError("eth-account is required for the live Testnet canary") from exc
    wallet = Account.from_key(private_key)
    if wallet.address.lower() != config.account_address.lower():
        raise RuntimeError("private key address does not match HL_TESTNET_ACCOUNT")
    client = HyperliquidSdkClient(config, wallet)
    intent = OrderIntent(
        intent_id="testnet-canary",
        instrument_id="ETH",
        side=Side.BUY,
        quantity=Decimal("0.01"),
        order_type=OrderType.LIMIT,
        client_order_id="chanlun-testnet-canary",
    )
    result = client.submit(intent, Decimal("100.00"))
    status = classify_order_response(result)
    print("submit_status:", status.value)
    print("submit_response:", result)
    statuses = result.get("response", {}).get("data", {}).get("statuses", [])
    if not statuses or "resting" not in statuses[0]:
        return 1 if status is OrderStatus.REJECTED else 0
    oid = int(statuses[0]["resting"]["oid"])
    cancel_result = client.cancel("ETH", oid)
    print("cancel_response:", cancel_result)
    return 0 if cancel_result.get("status") == "ok" else 1

if __name__ == "__main__":
    raise SystemExit(main())
