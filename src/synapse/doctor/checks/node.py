from __future__ import annotations

import shutil
import subprocess

from synapse.doctor.base import CheckResult

_FIX = "Install Node.js: https://nodejs.org/"


class NodeCheck:
    group = "typescript"

    def run(self) -> CheckResult:
        path = shutil.which("node")
        if path is None:
            return CheckResult(
                name="Node.js",
                status="fail",
                detail="node not found on PATH",
                fix=_FIX,
                group=self.group,
            )
        try:
            result = subprocess.run(["node", "--version"], capture_output=True, timeout=10)
        except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
            return CheckResult(
                name="Node.js",
                status="fail",
                detail=f"node invocation failed: {exc}",
                fix=_FIX,
                group=self.group,
            )
        if result.returncode != 0:
            return CheckResult(
                name="Node.js",
                status="fail",
                detail=f"node exited with code {result.returncode}",
                fix=_FIX,
                group=self.group,
            )
        return CheckResult(
            name="Node.js",
            status="pass",
            detail=f"Found at {path}",
            fix=None,
            group=self.group,
        )
