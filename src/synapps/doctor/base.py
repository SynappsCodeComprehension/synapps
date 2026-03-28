from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Literal, Protocol, runtime_checkable

log = logging.getLogger(__name__)

CheckStatus = Literal["pass", "warn", "fail"]


@dataclass(frozen=True)
class CheckResult:
    name: str
    status: CheckStatus
    detail: str
    fix: str | None
    group: str

    @property
    def is_ok(self) -> bool:
        # Convenience for CLI rendering in Phase 2
        return self.status == "pass"


@runtime_checkable
class DoctorCheck(Protocol):
    def run(self) -> CheckResult: ...
