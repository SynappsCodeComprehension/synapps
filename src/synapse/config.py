from __future__ import annotations

import json
import logging
import os
from pathlib import Path

log = logging.getLogger(__name__)


def is_http_endpoints_enabled(project_path: str) -> bool:
    """Check if experimental HTTP endpoint extraction is enabled for a project."""
    config_path = os.path.join(project_path, ".synapse", "config.json")
    try:
        with open(config_path, encoding="utf-8") as f:
            config = json.load(f)
        return bool(config.get("experimental", {}).get("http_endpoints", False))
    except (OSError, json.JSONDecodeError, AttributeError):
        return False


_GLOBAL_CONFIG_DEFAULTS = {
    "shared_container_name": "synapse-shared",
    "shared_port": 7687,
    "external_host": None,
    "external_port": None,
}


def is_dedicated_instance(project_path: str) -> bool:
    """Check if a project opts out of the shared Memgraph instance."""
    config_path = os.path.join(project_path, ".synapse", "config.json")
    try:
        with open(config_path, encoding="utf-8") as f:
            config = json.load(f)
        return bool(config.get("dedicated_instance", False))
    except (OSError, json.JSONDecodeError, AttributeError):
        return False


def load_global_config() -> dict:
    """Load global Synapse config from ~/.synapse/config.json, with defaults."""
    config_path = Path.home() / ".synapse" / "config.json"
    config = dict(_GLOBAL_CONFIG_DEFAULTS)
    try:
        with open(config_path, encoding="utf-8") as f:
            stored = json.load(f)
        config.update(stored)
    except (OSError, json.JSONDecodeError):
        pass
    return config
