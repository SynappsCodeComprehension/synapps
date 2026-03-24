from __future__ import annotations

import subprocess

from synapse.doctor.base import CheckResult

_FIX = "Install pyright: `pip install pyright` (or ensure it is in your project's dependencies)"


class PylspCheck:
    """Checks for pyright — the Python language server used by Synapse."""

    group = "python"

    def run(self) -> CheckResult:
        # Skip if python3 not available
        try:
            result = subprocess.run(
                ["python3", "--version"],
                capture_output=True,
                timeout=10,
            )
            if result.returncode != 0:
                return CheckResult(
                    name="pyright",
                    status="warn",
                    detail="python3 not available — cannot check pyright",
                    fix=None,
                    group=self.group,
                )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return CheckResult(
                name="pyright",
                status="warn",
                detail="python3 not available — cannot check pyright",
                fix=None,
                group=self.group,
            )

        # Check if pyright module is importable
        try:
            result = subprocess.run(
                ["python3", "-c", "import pyright; print(pyright.__file__)"],
                capture_output=True,
                timeout=10,
                text=True,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
            return CheckResult(
                name="pyright",
                status="fail",
                detail=f"pyright check failed: {exc}",
                fix=_FIX,
                group=self.group,
            )
        if result.returncode != 0:
            return CheckResult(
                name="pyright",
                status="fail",
                detail="pyright module not found",
                fix=_FIX,
                group=self.group,
            )
        path = result.stdout.strip()
        return CheckResult(
            name="pyright",
            status="pass",
            detail=f"Found at {path}",
            fix=None,
            group=self.group,
        )
