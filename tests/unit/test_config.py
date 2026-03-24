from __future__ import annotations

import json
from pathlib import Path

from synapse.config import is_http_endpoints_enabled


def test_enabled_when_flag_true(tmp_path: Path) -> None:
    config_dir = tmp_path / ".synapse"
    config_dir.mkdir()
    config_file = config_dir / "config.json"
    config_file.write_text(json.dumps({"experimental": {"http_endpoints": True}}))
    assert is_http_endpoints_enabled(str(tmp_path)) is True


def test_disabled_when_flag_false(tmp_path: Path) -> None:
    config_dir = tmp_path / ".synapse"
    config_dir.mkdir()
    config_file = config_dir / "config.json"
    config_file.write_text(json.dumps({"experimental": {"http_endpoints": False}}))
    assert is_http_endpoints_enabled(str(tmp_path)) is False


def test_disabled_when_no_experimental_key(tmp_path: Path) -> None:
    config_dir = tmp_path / ".synapse"
    config_dir.mkdir()
    config_file = config_dir / "config.json"
    config_file.write_text(json.dumps({"port": 7687}))
    assert is_http_endpoints_enabled(str(tmp_path)) is False


def test_disabled_when_no_config_file(tmp_path: Path) -> None:
    assert is_http_endpoints_enabled(str(tmp_path)) is False


def test_disabled_when_malformed_json(tmp_path: Path) -> None:
    config_dir = tmp_path / ".synapse"
    config_dir.mkdir()
    config_file = config_dir / "config.json"
    config_file.write_text("not json")
    assert is_http_endpoints_enabled(str(tmp_path)) is False
