"""Deterministic failure-injection scenarios for execution recovery."""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum


class FailureScenario(str, Enum):
    WS_DISCONNECT="WS_DISCONNECT"
    MISSED_ORDER_UPDATE="MISSED_ORDER_UPDATE"
    MISSED_FILL="MISSED_FILL"
    DUPLICATE_FILL="DUPLICATE_FILL"
    REST_TIMEOUT="REST_TIMEOUT"
    SIGNED_ORDER_TIMEOUT="SIGNED_ORDER_TIMEOUT"
    UNKNOWN_ORDER="UNKNOWN_ORDER"
    POSITION_DRIFT="POSITION_DRIFT"


@dataclass(frozen=True)
class FailureCase:
    scenario: FailureScenario
    description: str
    trading_must_be_blocked: bool = True


CASES=(
    FailureCase(FailureScenario.WS_DISCONNECT,"WebSocket disconnects during live stream"),
    FailureCase(FailureScenario.MISSED_ORDER_UPDATE,"Order update is absent from local event stream"),
    FailureCase(FailureScenario.MISSED_FILL,"Fill event is absent locally"),
    FailureCase(FailureScenario.DUPLICATE_FILL,"Same fill arrives more than once"),
    FailureCase(FailureScenario.REST_TIMEOUT,"Authoritative REST query times out"),
    FailureCase(FailureScenario.SIGNED_ORDER_TIMEOUT,"Signed order request times out after signing"),
    FailureCase(FailureScenario.UNKNOWN_ORDER,"Exchange result cannot yet be determined"),
    FailureCase(FailureScenario.POSITION_DRIFT,"Local and venue position differ"),
)


def assert_fail_safe(case: FailureCase, trading_authorized: bool) -> None:
    if case.trading_must_be_blocked and trading_authorized:
        raise AssertionError(f"fail-safe violation: {case.scenario}")
