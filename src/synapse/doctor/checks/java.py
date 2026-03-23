from __future__ import annotations

import shutil
import subprocess

from synapse.doctor.base import CheckResult

_FIX = "Install Java: https://adoptium.net/"


class JavaCheck:
    group = "java"

    def run(self) -> CheckResult:
        path = shutil.which("java")
        if path is None:
            return CheckResult(
                name="Java",
                status="fail",
                detail="java not found on PATH",
                fix=_FIX,
                group=self.group,
            )
        try:
            # java -version writes version info to stderr (JVM convention); use returncode as pass signal
            result = subprocess.run(["java", "-version"], capture_output=True, timeout=10)
        except subprocess.TimeoutExpired:
            return CheckResult(
                name="Java",
                status="fail",
                detail="java -version timed out",
                fix=_FIX,
                group=self.group,
            )
        if result.returncode == 0:
            return CheckResult(
                name="Java",
                status="pass",
                detail=f"Found at {path}",
                fix=None,
                group=self.group,
            )
        return CheckResult(
            name="Java",
            status="fail",
            detail="java -version exited with non-zero status",
            fix=_FIX,
            group=self.group,
        )
