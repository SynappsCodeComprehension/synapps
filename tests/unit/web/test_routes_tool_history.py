from __future__ import annotations

from unittest.mock import create_autospec

from fastapi import FastAPI
from fastapi.testclient import TestClient

from synapps.service import SynappsService
from synapps.web.routes.tool_history import router as tool_history_router


def _make_client(service=None):
    svc = service or create_autospec(SynappsService)
    app = FastAPI()
    app.include_router(tool_history_router(svc), prefix="/api")
    return TestClient(app), svc


def test_tool_history_basic():
    client, svc = _make_client()
    svc.get_tool_history.return_value = {"calls": [], "stats": {"total_count": 0, "limit": 50, "offset": 0}}
    response = client.get("/api/tool_history")
    assert response.status_code == 200
    assert response.json() == {"calls": [], "stats": {"total_count": 0, "limit": 50, "offset": 0}}
    svc.get_tool_history.assert_called_once_with(tool=None, status=None, limit=50, offset=0)


def test_tool_history_with_tool_filter():
    client, svc = _make_client()
    svc.get_tool_history.return_value = {"calls": [], "stats": {"total_count": 0, "limit": 50, "offset": 0}}
    response = client.get("/api/tool_history?tool=search_symbols")
    assert response.status_code == 200
    svc.get_tool_history.assert_called_once_with(tool="search_symbols", status=None, limit=50, offset=0)


def test_tool_history_with_status_filter():
    client, svc = _make_client()
    svc.get_tool_history.return_value = {"calls": [], "stats": {"total_count": 0, "limit": 50, "offset": 0}}
    response = client.get("/api/tool_history?status=error")
    assert response.status_code == 200
    svc.get_tool_history.assert_called_once_with(tool=None, status="error", limit=50, offset=0)


def test_tool_history_with_pagination():
    client, svc = _make_client()
    svc.get_tool_history.return_value = {"calls": [], "stats": {"total_count": 100, "limit": 10, "offset": 20}}
    response = client.get("/api/tool_history?limit=10&offset=20")
    assert response.status_code == 200
    svc.get_tool_history.assert_called_once_with(tool=None, status=None, limit=10, offset=20)
