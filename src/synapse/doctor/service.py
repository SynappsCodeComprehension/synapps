from __future__ import annotations

import logging
from dataclasses import dataclass

from synapse.doctor.base import CheckResult, DoctorCheck

log = logging.getLogger(__name__)


@dataclass
class DoctorReport:
    checks: list[CheckResult]

    @property
    def has_failures(self) -> bool:
        # Only "fail" counts as a failure — "warn" is a degraded-but-working state
        return any(r.status == "fail" for r in self.checks)


class DoctorService:
    def __init__(self, checks: list[DoctorCheck]) -> None:
        self._checks = checks

    def run(self) -> DoctorReport:
        results: list[CheckResult] = []
        for check in self._checks:
            try:
                results.append(check.run())
            except Exception as exc:
                log.warning("Check %r raised unexpectedly: %s", check, exc)
                results.append(CheckResult(
                    name=repr(check),
                    status="fail",
                    detail=str(exc),
                    fix=None,
                    group="unknown",
                ))
        return DoctorReport(checks=results)
