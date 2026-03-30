"""Tests for synapps install / uninstall CLI commands."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from synapps.cli.app import app

runner = CliRunner()


class TestInstallCommand:
    def test_install_writes_scripts_and_config(self, tmp_path: Path) -> None:
        home = tmp_path / "home"
        (home / ".claude").mkdir(parents=True)
        project = tmp_path / "project"
        project.mkdir()

        with patch.object(Path, "home", return_value=home):
            result = runner.invoke(app, ["install", str(project), "--agent", "claude"], input="y\n")

        assert result.exit_code == 0
        assert (home / ".synapps" / "hooks" / "claude-gate.sh").exists()
        settings = json.loads((home / ".claude" / "settings.json").read_text())
        assert "PreToolUse" in settings["hooks"]


class TestUninstallCommand:
    def test_uninstall_removes_scripts_and_config(self, tmp_path: Path) -> None:
        home = tmp_path / "home"
        hooks_dir = home / ".synapps" / "hooks"
        hooks_dir.mkdir(parents=True)
        (hooks_dir / "claude-gate.sh").write_text("#!/bin/bash\n")

        settings_path = home / ".claude" / "settings.json"
        settings_path.parent.mkdir(parents=True)
        settings_path.write_text(json.dumps({
            "hooks": {"PreToolUse": [
                {"matcher": "Grep|Glob", "hooks": [
                    {"type": "command", "command": "~/.synapps/hooks/claude-gate.sh"}
                ]}
            ]}
        }))

        with patch.object(Path, "home", return_value=home):
            result = runner.invoke(app, ["uninstall"], input="y\n")

        assert result.exit_code == 0
        assert not hooks_dir.exists()
