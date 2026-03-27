from __future__ import annotations

import json
from pathlib import Path

from unittest.mock import patch

from synapse.config import is_dedicated_instance, load_global_config


# --- is_dedicated_instance ---


def test_is_dedicated_instance_true(tmp_path: Path) -> None:
    config_dir = tmp_path / ".synapse"
    config_dir.mkdir()
    (config_dir / "config.json").write_text(json.dumps({"dedicated_instance": True}))
    assert is_dedicated_instance(str(tmp_path)) is True


def test_is_dedicated_instance_false_when_absent(tmp_path: Path) -> None:
    assert is_dedicated_instance(str(tmp_path)) is False


def test_is_dedicated_instance_false_when_not_set(tmp_path: Path) -> None:
    config_dir = tmp_path / ".synapse"
    config_dir.mkdir()
    (config_dir / "config.json").write_text(json.dumps({"experimental": {}}))
    assert is_dedicated_instance(str(tmp_path)) is False


# --- load_global_config ---


def test_load_global_config_defaults(tmp_path: Path) -> None:
    with patch("synapse.config.Path.home", return_value=tmp_path):
        config = load_global_config()
    assert config["shared_container_name"] == "synapse-shared"
    assert config["shared_port"] == 7687
    assert config["external_host"] is None
    assert config["external_port"] is None


def test_load_global_config_reads_file(tmp_path: Path) -> None:
    config_dir = tmp_path / ".synapse"
    config_dir.mkdir()
    (config_dir / "config.json").write_text(json.dumps({
        "shared_container_name": "my-memgraph",
        "shared_port": 9999,
        "external_host": "db.example.com",
        "external_port": 7688,
    }))
    with patch("synapse.config.Path.home", return_value=tmp_path):
        config = load_global_config()
    assert config["shared_container_name"] == "my-memgraph"
    assert config["shared_port"] == 9999
    assert config["external_host"] == "db.example.com"
    assert config["external_port"] == 7688


def test_load_global_config_merges_partial(tmp_path: Path) -> None:
    config_dir = tmp_path / ".synapse"
    config_dir.mkdir()
    (config_dir / "config.json").write_text(json.dumps({"shared_port": 8888}))
    with patch("synapse.config.Path.home", return_value=tmp_path):
        config = load_global_config()
    assert config["shared_port"] == 8888
    assert config["shared_container_name"] == "synapse-shared"
