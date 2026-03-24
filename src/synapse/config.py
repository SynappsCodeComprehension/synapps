from __future__ import annotations

import json
import logging
import os

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
