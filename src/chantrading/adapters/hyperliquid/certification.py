"""Production certification gates for the Hyperliquid adapter."""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum


class Network(str, Enum):
    TESTNET="testnet"
    MAINNET="mainnet"


class Gate(str, Enum):
    TESTS="TESTS"
    RECONCILIATION="RECONCILIATION"
    RECOVERY="RECOVERY"
    SIGNING_ISOLATION="SIGNING_ISOLATION"
    KILL_SWITCH="KILL_SWITCH"
    HEALTH="HEALTH"
    CONFIGURATION="CONFIGURATION"


@dataclass(frozen=True)
class CertificationResult:
    network: Network
    passed: frozenset[Gate]
    failed: frozenset[Gate]

    @property
    def certified(self) -> bool:
        return not self.failed


REQUIRED_GATES=frozenset(Gate)


def evaluate_certification(network: Network, passed: set[Gate]) -> CertificationResult:
    passed_fs=frozenset(passed)
    return CertificationResult(network, passed_fs, REQUIRED_GATES - passed_fs)


def production_authorized(result: CertificationResult) -> bool:
    return result.network is Network.MAINNET and result.certified
