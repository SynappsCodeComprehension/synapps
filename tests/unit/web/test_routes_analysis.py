from __future__ import annotations

from unittest.mock import MagicMock, create_autospec

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from synapps.service import SynappsService
from synapps.web.routes.analysis import router as analysis_router


def _make_client(service=None):
    svc = service or create_autospec(SynappsService)
    app = FastAPI()
    app.include_router(analysis_router(svc), prefix="/api")
    return TestClient(app), svc


def test_get_architecture_basic():
    client, svc = _make_client()
    svc.get_architecture_overview.return_value = {"packages": [], "stats": {}}
    response = client.get("/api/get_architecture?path=/foo")
    assert response.status_code == 200
    assert response.json() == {"packages": [], "stats": {}}
    svc.get_architecture_overview.assert_called_once_with(limit=10)


def test_find_dead_code_basic():
    client, svc = _make_client()
    svc.find_dead_code.return_value = {"methods": [], "total": 0}
    response = client.get("/api/find_dead_code?path=/foo")
    assert response.status_code == 200
    assert response.json() == {"methods": [], "total": 0}
    svc.find_dead_code.assert_called_once_with(exclude_pattern="", exclude_file_pattern="", limit=15, offset=0, subdirectory="")


def test_find_dead_code_with_limit_and_offset():
    client, svc = _make_client()
    svc.find_dead_code.return_value = {"methods": [], "total": 0}
    response = client.get("/api/find_dead_code?path=/foo&limit=5&offset=10")
    assert response.status_code == 200
    svc.find_dead_code.assert_called_once_with(exclude_pattern="", exclude_file_pattern="", limit=5, offset=10, subdirectory="")


def test_find_untested_basic():
    client, svc = _make_client()
    svc.find_untested.return_value = {"methods": [], "total": 0}
    response = client.get("/api/find_untested?path=/foo")
    assert response.status_code == 200
    assert response.json() == {"methods": [], "total": 0}
    svc.find_untested.assert_called_once_with(exclude_pattern="", exclude_file_pattern="", limit=15, offset=0, subdirectory="")


def test_get_architecture_value_error_returns_400():
    client, svc = _make_client()
    svc.get_architecture_overview.side_effect = ValueError("No project indexed")
    response = client.get("/api/get_architecture?path=/foo")
    assert response.status_code == 400
    assert response.json()["detail"] == "No project indexed"


def test_find_dead_code_value_error_returns_400():
    client, svc = _make_client()
    svc.find_dead_code.side_effect = ValueError("Not indexed")
    response = client.get("/api/find_dead_code?path=/foo")
    assert response.status_code == 400
    assert response.json()["detail"] == "Not indexed"


def test_get_architecture_no_path():
    """D-07: path is now optional — request without path returns 200."""
    client, svc = _make_client()
    svc.get_architecture_overview.return_value = {"packages": [], "stats": {}}
    response = client.get("/api/get_architecture")
    assert response.status_code == 200
    svc.get_architecture_overview.assert_called_once_with(limit=10)


def test_find_dead_code_no_path():
    """D-07: path is now optional."""
    client, svc = _make_client()
    svc.find_dead_code.return_value = {"methods": [], "total": 0}
    response = client.get("/api/find_dead_code")
    assert response.status_code == 200
    svc.find_dead_code.assert_called_once_with(exclude_pattern="", exclude_file_pattern="", limit=15, offset=0, subdirectory="")


def test_find_dead_code_with_subdirectory():
    """D-08: subdirectory param is passed through to service."""
    client, svc = _make_client()
    svc.find_dead_code.return_value = {"methods": [], "total": 0}
    response = client.get("/api/find_dead_code?subdirectory=src/api")
    assert response.status_code == 200
    svc.find_dead_code.assert_called_once_with(exclude_pattern="", exclude_file_pattern="", limit=15, offset=0, subdirectory="src/api")


def test_find_untested_with_subdirectory():
    """subdirectory param is passed through to service for find_untested."""
    client, svc = _make_client()
    svc.find_untested.return_value = {"methods": [], "total": 0}
    response = client.get("/api/find_untested?subdirectory=src/services")
    assert response.status_code == 200
    svc.find_untested.assert_called_once_with(exclude_pattern="", exclude_file_pattern="", limit=15, offset=0, subdirectory="src/services")


def test_find_dead_code_with_exclude_file_pattern():
    client, svc = _make_client()
    svc.find_dead_code.return_value = {"methods": [], "total": 0}
    response = client.get("/api/find_dead_code?exclude_file_pattern=.*gen.*")
    assert response.status_code == 200
    svc.find_dead_code.assert_called_once_with(
        exclude_pattern="", exclude_file_pattern=".*gen.*",
        limit=15, offset=0, subdirectory="",
    )


def test_find_untested_with_exclude_file_pattern():
    client, svc = _make_client()
    svc.find_untested.return_value = {"methods": [], "total": 0}
    response = client.get("/api/find_untested?exclude_file_pattern=.*gen.*")
    assert response.status_code == 200
    svc.find_untested.assert_called_once_with(
        exclude_pattern="", exclude_file_pattern=".*gen.*",
        limit=15, offset=0, subdirectory="",
    )
