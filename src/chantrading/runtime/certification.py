"""Testnet certification run coordinator."""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum

from .soak_runner import SoakRunConfig, SoakTestRunner
from chantrading.chanlun import CenterEngine, SegmentEngine


class CertificationStatus(str, Enum):
    PRECHECK="PRECHECK"
    RUNNING="RUNNING"
    PASSED="PASSED"
    FAILED="FAILED"


@dataclass(frozen=True)
class CertificationPrecheck:
    config_loaded: bool
    testnet_mode: bool
    trading_guard_enabled: bool
    event_store_ready: bool
    replay_ready: bool
    structural_certified: bool = True

    @property
    def passed(self) -> bool:
        return all((
            self.config_loaded,
            self.testnet_mode,
            self.trading_guard_enabled,
            self.event_store_ready,
            self.replay_ready,
            self.structural_certified,
        ))


class TestnetCertificationRun:
    def __init__(self, duration_ms: int, clock_ms=None):
        self.runner=SoakTestRunner(SoakRunConfig(duration_ms=duration_ms), clock_ms=clock_ms)
        self.status=CertificationStatus.PRECHECK
        self.precheck: CertificationPrecheck | None=None

    @staticmethod
    def structural_contract_ready() -> bool:
        """Verify that the strict 1M structural engine exposes its frozen layers."""
        required = (
            hasattr(CenterEngine, "classify_extension_count"),
            hasattr(CenterEngine, "classify_center_pair"),
            hasattr(CenterEngine, "classify_center_expansion"),
            hasattr(SegmentEngine, "update"),
        )
        return all(required)

    def run_precheck(self, precheck: CertificationPrecheck):
        self.precheck=precheck
        self.status=CertificationStatus.PRECHECK
        return precheck.passed

    def start(self, started_at_ms=None):
        if self.precheck is None or not self.precheck.passed:
            raise RuntimeError("Testnet certification precheck failed")
        self.runner.start(started_at_ms)
        self.status=CertificationStatus.RUNNING

    def stop(self, ended_at_ms=None):
        if self.status is not CertificationStatus.RUNNING:
            raise RuntimeError("certification is not running")
        report=self.runner.stop(ended_at_ms)
        self.status=(
            CertificationStatus.PASSED
            if report.replay_equivalent is True and report.drift_events == 0
            else CertificationStatus.FAILED
        )
        return report
