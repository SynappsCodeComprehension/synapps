from __future__ import annotations

import glob
import subprocess
from pathlib import Path

from synapps.doctor.base import CheckResult

_FIX = (
    "Roslyn Language Server is auto-downloaded on first C# indexing. "
    "Ensure .NET SDK is installed and run `synapps index` on a C# project."
)


class CSharpLSCheck:
    group = "csharp"

    def run(self) -> CheckResult:
        # Roslyn LS requires dotnet — skip if absent
        try:
            result = subprocess.run(
                ["dotnet", "--list-runtimes"],
                capture_output=True,
                timeout=10,
                text=True,
            )
            if result.returncode != 0:
                return CheckResult(
                    name="Roslyn Language Server",
                    status="warn",
                    detail="dotnet not available — cannot check Roslyn Language Server",
                    fix=None,
                    group=self.group,
                )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return CheckResult(
                name="Roslyn Language Server",
                status="warn",
                detail="dotnet not available — cannot check Roslyn Language Server",
                fix=None,
                group=self.group,
            )

        # Check for the auto-downloaded Roslyn DLL in solidlsp cache
        solidlsp_dir = Path.home() / ".solidlsp" / "language_servers" / "static"
        pattern = str(solidlsp_dir / "roslyn-language-server.*" / "Microsoft.CodeAnalysis.LanguageServer.dll")
        matches = glob.glob(pattern)
        if matches:
            return CheckResult(
                name="Roslyn Language Server",
                status="pass",
                detail=f"Found at {matches[0]}",
                fix=None,
                group=self.group,
            )
        return CheckResult(
            name="Roslyn Language Server",
            status="warn",
            detail="Roslyn Language Server not yet downloaded (will be auto-installed on first C# indexing)",
            fix=_FIX,
            group=self.group,
        )
