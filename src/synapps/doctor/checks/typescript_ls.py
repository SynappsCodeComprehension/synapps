from __future__ import annotations

import platform
import shutil

from synapps.doctor.base import CheckResult


def _fix() -> str:
    if platform.system() == "Darwin":
        return "Install npm (bundled with Node.js): brew install node\nOr download: https://nodejs.org/"
    return "Install npm: sudo apt-get install npm\nOr download: https://nodejs.org/"


class TypeScriptLSCheck:
    """Checks for npm — required for Synapps to auto-install typescript-language-server."""

    group = "typescript"

    def run(self) -> CheckResult:
        # Skip if node not available
        if shutil.which("node") is None:
            return CheckResult(
                name="npm",
                status="warn",
                detail="node not available — cannot check npm",
                fix=None,
                group=self.group,
            )
        # Synapps auto-installs typescript-language-server via npm,
        # so we just need to verify npm is available
        path = shutil.which("npm")
        if path is None:
            return CheckResult(
                name="npm",
                status="fail",
                detail="npm not found on PATH (required for Synapps to install typescript-language-server)",
                fix=_fix(),
                group=self.group,
            )
        return CheckResult(
            name="npm",
            status="pass",
            detail=f"Found at {path} (typescript-language-server auto-installed by Synapps)",
            fix=None,
            group=self.group,
        )
