from __future__ import annotations

import shutil
import subprocess

from synapse.doctor.base import CheckResult

_FIX = "Install csharp-ls: `dotnet tool install -g csharp-ls`"


class CSharpLSCheck:
    group = "csharp"

    def run(self) -> CheckResult:
        # Skip if dotnet runtime absent — cannot meaningfully check csharp-ls
        if shutil.which("dotnet") is None:
            return CheckResult(
                name="csharp-ls",
                status="warn",
                detail="dotnet not available — cannot check csharp-ls",
                fix=None,
                group=self.group,
            )
        path = shutil.which("csharp-ls")
        if path is None:
            return CheckResult(
                name="csharp-ls",
                status="fail",
                detail="csharp-ls not found on PATH",
                fix=_FIX,
                group=self.group,
            )
        try:
            result = subprocess.run(
                ["csharp-ls", "--version"],
                capture_output=True,
                timeout=10,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
            return CheckResult(
                name="csharp-ls",
                status="fail",
                detail=f"csharp-ls invocation failed: {exc}",
                fix=_FIX,
                group=self.group,
            )
        if result.returncode != 0:
            return CheckResult(
                name="csharp-ls",
                status="fail",
                detail=f"csharp-ls exited with code {result.returncode}",
                fix=_FIX,
                group=self.group,
            )
        return CheckResult(
            name="csharp-ls",
            status="pass",
            detail=f"Found at {path}",
            fix=None,
            group=self.group,
        )
