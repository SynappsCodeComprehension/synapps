"""
API HTTP integration tests for all 5 FastAPI route modules.

Exercises the full request-to-graph-to-JSON path using a real SynappsService
backed by live Memgraph. These tests catch serialization bugs on real neo4j
driver objects that unit tests (which mock the service layer) cannot.

Run with:
    pytest tests/integration/test_api.py -v -m api_integration --timeout=30
"""
from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from synapps.web.app import create_app
from synapps.web.serialization import serialize_result

pytestmark = [pytest.mark.api_integration, pytest.mark.timeout(30)]


@pytest.fixture(scope="session")
def web_client(service):
    """TestClient connected to a real SynappsService backed by live Memgraph."""
    app = create_app(service, static_dir=None)
    with TestClient(app) as client:
        yield client


# ---------------------------------------------------------------------------
# Search routes
# ---------------------------------------------------------------------------


def test_search_symbols_returns_results(web_client):
    resp = web_client.get("/api/search_symbols", params={"query": "TaskService", "kind": "Class"})
    assert resp.status_code == 200
    assert "application/json" in resp.headers["content-type"]
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert "full_name" in data[0]
    assert "kind" in data[0]


def test_search_symbols_no_match_returns_empty_list(web_client):
    resp = web_client.get("/api/search_symbols", params={"query": "__zzz_nonexistent_xyz__"})
    assert resp.status_code == 200
    data = resp.json()
    assert data == []


def test_read_symbol_returns_content(web_client):
    resp = web_client.get("/api/read_symbol", params={"full_name": "SynappsTest.Services.TaskService"})
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, dict)
    assert "content" in data
    assert isinstance(data["content"], str)
    assert len(data["content"]) > 0


def test_read_symbol_not_found_returns_error(web_client):
    # _resolve() raises ValueError for unknown symbols → 400; the 404 path only
    # fires when read_symbol() itself returns None for a known-but-unreadable symbol.
    resp = web_client.get("/api/read_symbol", params={"full_name": "__nonexistent_symbol_xyz__"})
    assert resp.status_code in (400, 404)
    data = resp.json()
    assert "detail" in data


# ---------------------------------------------------------------------------
# Navigate routes
# ---------------------------------------------------------------------------


def test_find_usages_returns_results(web_client):
    resp = web_client.get("/api/find_usages", params={"full_name": "SynappsTest.Services.TaskService"})
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, dict)
    assert "usages" in data
    assert isinstance(data["usages"], list)
    assert "queried_kind" in data
    assert isinstance(data["queried_kind"], str)


def test_find_usages_nonexistent_returns_400(web_client):
    resp = web_client.get("/api/find_usages", params={"full_name": "__nonexistent_xyz__"})
    assert resp.status_code == 400
    data = resp.json()
    assert "detail" in data


def test_get_hierarchy_returns_dict(web_client):
    resp = web_client.get("/api/get_hierarchy", params={"full_name": "SynappsTest.Services.TaskService"})
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, dict)


def test_get_context_for_returns_dict(web_client):
    resp = web_client.get("/api/get_context_for", params={"full_name": "SynappsTest.Services.TaskService"})
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, dict)


def test_find_callees_returns_dict(web_client):
    resp = web_client.get("/api/find_callees", params={"full_name": "SynappsTest.Services.TaskService.CreateTaskAsync"})
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, dict)
    assert "callees" in data


def test_explore_returns_dict(web_client):
    resp = web_client.get("/api/explore", params={"full_name": "SynappsTest.Services.TaskService"})
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, dict)


# ---------------------------------------------------------------------------
# Analysis routes
# ---------------------------------------------------------------------------


def test_get_architecture_returns_dict(web_client):
    resp = web_client.get("/api/get_architecture")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, dict)


def test_find_dead_code_returns_dict(web_client):
    resp = web_client.get("/api/find_dead_code")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, dict)


def test_find_untested_returns_dict(web_client):
    resp = web_client.get("/api/find_untested")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, dict)


def test_assess_impact_returns_content(web_client):
    resp = web_client.get("/api/assess_impact", params={"full_name": "SynappsTest.Services.TaskService.CreateTaskAsync"})
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, dict)
    assert "content" in data


def test_assess_impact_nonexistent_returns_400(web_client):
    resp = web_client.get("/api/assess_impact", params={"full_name": "__nonexistent_xyz__"})
    assert resp.status_code == 400
    data = resp.json()
    assert "detail" in data


# ---------------------------------------------------------------------------
# Query routes
# ---------------------------------------------------------------------------


def test_execute_query_returns_list(web_client):
    resp = web_client.post("/api/execute_query", json={"cypher": "MATCH (n:Class) RETURN n.name LIMIT 3"})
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


def test_execute_query_invalid_cypher_returns_400(web_client):
    resp = web_client.post("/api/execute_query", json={"cypher": "NOT VALID CYPHER !!!"})
    assert resp.status_code == 400
    data = resp.json()
    assert "detail" in data


def test_find_http_endpoints_returns_list(web_client):
    resp = web_client.get("/api/find_http_endpoints")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


# ---------------------------------------------------------------------------
# Config routes
# ---------------------------------------------------------------------------


def test_config_returns_project_root(web_client):
    resp = web_client.get("/api/config")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, dict)
    assert "project_root" in data
    assert isinstance(data["project_root"], str)


# ---------------------------------------------------------------------------
# Serialization tests (API-03) — exercise real neo4j Node/Relationship objects
# ---------------------------------------------------------------------------


def test_serialize_real_neo4j_node(service):
    records = service._conn.query("MATCH (n:Class) RETURN n LIMIT 1")
    assert len(records) > 0, "No Class nodes found — fixture may not be indexed"
    node = records[0][0]
    assert hasattr(node, "element_id")
    assert hasattr(node, "items")
    result = serialize_result(node)
    assert isinstance(result, dict)
    # Verify the result is fully JSON-serializable
    json.dumps(result)


def test_serialize_real_neo4j_relationship(service):
    records = service._conn.query("MATCH (a)-[r:CALLS]->(b) RETURN r LIMIT 1")
    if not records:
        pytest.skip("No CALLS relationship found in fixture")
    rel = records[0][0]
    assert hasattr(rel, "element_id")
    result = serialize_result(rel)
    assert isinstance(result, dict)
    # Verify the result is fully JSON-serializable
    json.dumps(result)
