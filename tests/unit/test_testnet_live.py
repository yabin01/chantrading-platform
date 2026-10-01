from decimal import Decimal

import pytest

from chantrading.adapters.hyperliquid.testnet_live import (
    LiveTestnetConfig,
    classify_order_response,
)
from chantrading.domain.execution import OrderStatus


ADDRESS = "0x" + "1" * 40


def test_live_config_defaults_to_unconfirmed():
    config = LiveTestnetConfig(account_address=ADDRESS)
    with pytest.raises(RuntimeError, match="HL_TESTNET_CONFIRM"):
        config.validate()


def test_live_config_rejects_mainnet():
    config = LiveTestnetConfig(
        account_address=ADDRESS,
        api_url="https://api.hyperliquid.xyz",
        confirm_testnet=True,
    )
    with pytest.raises(ValueError, match="official Hyperliquid Testnet"):
        config.validate()


def test_live_config_requires_valid_account():
    config = LiveTestnetConfig(
        account_address="not-an-address",
        confirm_testnet=True,
    )
    with pytest.raises(ValueError, match="20-byte"):
        config.validate()


def test_classify_filled_response():
    result = {"status": "ok", "response": {"data": {"statuses": [
        {"filled": {"oid": 123}}
    ]}}}
    assert classify_order_response(result) is OrderStatus.FILLED


def test_classify_resting_response():
    result = {"status": "ok", "response": {"data": {"statuses": [
        {"resting": {"oid": 123}}
    ]}}}
    assert classify_order_response(result) is OrderStatus.OPEN


def test_classify_rejected_response():
    assert classify_order_response({"status": "err"}) is OrderStatus.REJECTED


def test_classify_unknown_response():
    assert classify_order_response({"status": "ok", "response": {"data": {"statuses": []}}) is OrderStatus.UNKNOWN
