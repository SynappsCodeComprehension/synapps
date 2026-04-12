"""
Contract validation tests — asserts that real SynappsService output conforms to
each TypedDict shape defined in tests/fixtures/contract_fixtures.py.

When a method's return shape changes, these tests fail, signaling that
contract_fixtures.py needs updating. Structural assertions only (keys + types),
no exact-value comparisons.

Requires Memgraph on localhost:7687 and .NET SDK.
Run with: pytest tests/integration/test_contract_validation.py -v -m integration
"""
from __future__ import annotations

import pytest
from typing import get_type_hints

from fixtures.contract_fixtures import (
    SearchSymbolsResult,
    FindCallersResult,
    FindCalleesResult,
    FindImplementationsResult,
    FindUsagesResult,
    FindDependenciesResult,
    GetHierarchyResult,
    GetSymbolResult,
    GetContextForResult,
    GetCallDepthResult,
    GetIndexStatusResult,
    GetArchitectureOverviewResult,
    FindDeadCodeResult,
    FindUntestedResult,
    FindHttpEndpointsResult,
    TraceHttpDependencyResult,
    FindTypeReferencesResult,
    ListProjectsResult,
    ListSummarizedResult,
)
from tests.integration.conftest import FIXTURE_PATH


def _assert_conforms(result: dict, shape: type, *, context: str = "") -> None:
    """Assert that result has all required keys of shape with correct types.

    Structural assertion only — does not check exact values.
    Uses __required_keys__ to distinguish required from optional fields.
    """
    hints = get_type_hints(shape)
    required = shape.__required_keys__
    prefix = f"[{context}] " if context else ""
    for key in required:
        assert key in result, f"{prefix}Missing required key {key!r}"
    for key, expected in hints.items():
        if key not in result:
            continue
        check = getattr(expected, "__origin__", expected)
        assert isinstance(result[key], check), (
            f"{prefix}Key {key!r}: expected {check.__name__}, got {type(result[key]).__name__}"
        )


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

@pytest.mark.integration
@pytest.mark.timeout(30)
def test_search_symbols_conforms(service) -> None:
    results = service.search_symbols("TaskService")
    assert isinstance(results, list) and results, "Expected non-empty list from search_symbols"
    _assert_conforms(results[0], SearchSymbolsResult, context="search_symbols")


# ---------------------------------------------------------------------------
# Navigate
# ---------------------------------------------------------------------------

@pytest.mark.integration
@pytest.mark.timeout(30)
def test_find_callers_conforms(service) -> None:
    results = service.find_callers("SynappsTest.Services.TaskService.CreateTaskAsync")
    if isinstance(results, dict):
        items = results.get("results", [])
    else:
        items = results
    if not items:
        pytest.skip("No callers found for TaskService.CreateTaskAsync in fixture")
    _assert_conforms(items[0], FindCallersResult, context="find_callers")


@pytest.mark.integration
@pytest.mark.timeout(30)
def test_find_callees_conforms(service) -> None:
    results = service.find_callees("SynappsTest.Controllers.TaskController.Create")
    if isinstance(results, dict):
        items = results.get("results", [])
    else:
        items = results
    if not items:
        pytest.skip("No callees found for TaskController.Create in fixture")
    _assert_conforms(items[0], FindCalleesResult, context="find_callees")


@pytest.mark.integration
@pytest.mark.timeout(30)
def test_find_implementations_conforms(service) -> None:
    results = service.find_implementations("SynappsTest.Services.ITaskService")
    if isinstance(results, dict):
        items = results.get("results", [])
    else:
        items = results
    if not items:
        pytest.skip("No implementations found for ITaskService in fixture")
    _assert_conforms(items[0], FindImplementationsResult, context="find_implementations")


@pytest.mark.integration
@pytest.mark.timeout(30)
def test_find_usages_conforms(service) -> None:
    # Use exclude_test_callers=False to ensure references are found even if only test files use the type
    results = service.find_usages(
        "SynappsTest.Services.TaskService",
        structured=True,
        exclude_test_callers=False,
    )
    if isinstance(results, str):
        pytest.skip("find_usages returned string summary instead of list")
    if not (isinstance(results, list) and results):
        pytest.skip("No usages found for TaskService in fixture")
    _assert_conforms(results[0], FindUsagesResult, context="find_usages")


@pytest.mark.integration
@pytest.mark.timeout(30)
def test_find_dependencies_conforms(service) -> None:
    results = service.find_dependencies("SynappsTest.Services.TaskService")
    # find_dependencies may return list or dict (with dependencies + fields)
    if isinstance(results, dict):
        items = results.get("dependencies", [])
    else:
        items = results
    if not items:
        pytest.skip("No dependencies found for TaskService in fixture")
    _assert_conforms(items[0], FindDependenciesResult, context="find_dependencies")


@pytest.mark.integration
@pytest.mark.timeout(30)
def test_get_hierarchy_conforms(service) -> None:
    result = service.get_hierarchy("SynappsTest.Services.TaskService")
    assert isinstance(result, dict), "Expected dict from get_hierarchy"
    _assert_conforms(result, GetHierarchyResult, context="get_hierarchy")


@pytest.mark.integration
@pytest.mark.timeout(30)
def test_get_symbol_conforms(service) -> None:
    result = service.get_symbol("SynappsTest.Services.TaskService")
    if result is None:
        pytest.skip("get_symbol returned None for TaskService")
    assert isinstance(result, dict), "Expected dict from get_symbol"
    _assert_conforms(result, GetSymbolResult, context="get_symbol")


@pytest.mark.integration
@pytest.mark.timeout(30)
def test_get_context_for_conforms(service) -> None:
    result = service.get_context_for(
        "SynappsTest.Services.TaskService.CreateTaskAsync", structured=True
    )
    if isinstance(result, str) or result is None:
        pytest.skip("get_context_for returned string or None instead of dict")
    assert isinstance(result, dict), "Expected dict from get_context_for"
    _assert_conforms(result, GetContextForResult, context="get_context_for")


@pytest.mark.integration
@pytest.mark.timeout(30)
def test_get_call_depth_conforms(service) -> None:
    result = service.get_call_depth("SynappsTest.Services.TaskService.CreateTaskAsync")
    assert isinstance(result, dict), "Expected dict from get_call_depth"
    _assert_conforms(result, GetCallDepthResult, context="get_call_depth")


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

@pytest.mark.integration
@pytest.mark.timeout(30)
def test_get_index_status_conforms(service) -> None:
    result = service.get_index_status(FIXTURE_PATH)
    if result is None:
        pytest.skip("get_index_status returned None for FIXTURE_PATH")
    assert isinstance(result, dict), "Expected dict from get_index_status"
    _assert_conforms(result, GetIndexStatusResult, context="get_index_status")


@pytest.mark.integration
@pytest.mark.timeout(30)
def test_get_architecture_overview_conforms(service) -> None:
    result = service.get_architecture_overview()
    assert isinstance(result, dict), "Expected dict from get_architecture_overview"
    _assert_conforms(result, GetArchitectureOverviewResult, context="get_architecture_overview")


@pytest.mark.integration
@pytest.mark.timeout(30)
def test_find_dead_code_conforms(service) -> None:
    result = service.find_dead_code()
    assert isinstance(result, dict), "Expected dict from find_dead_code"
    _assert_conforms(result, FindDeadCodeResult, context="find_dead_code")


@pytest.mark.integration
@pytest.mark.timeout(30)
def test_find_untested_conforms(service) -> None:
    result = service.find_untested()
    assert isinstance(result, dict), "Expected dict from find_untested"
    _assert_conforms(result, FindUntestedResult, context="find_untested")


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------

@pytest.mark.integration
@pytest.mark.timeout(30)
def test_find_http_endpoints_conforms(service) -> None:
    results = service.find_http_endpoints()
    if isinstance(results, dict):
        items = results.get("results", [])
    else:
        items = results
    if not items:
        pytest.skip("No HTTP endpoints found in fixture")
    _assert_conforms(items[0], FindHttpEndpointsResult, context="find_http_endpoints")


@pytest.mark.integration
@pytest.mark.timeout(30)
def test_trace_http_dependency_conforms(service) -> None:
    # Find an endpoint first to get a valid route
    endpoints = service.find_http_endpoints()
    if isinstance(endpoints, dict):
        ep_list = endpoints.get("results", [])
    else:
        ep_list = endpoints
    if not ep_list:
        pytest.skip("No HTTP endpoints found in fixture for trace_http_dependency")
    ep = ep_list[0]
    route = ep.get("route")
    http_method = ep.get("http_method")
    if not route or not http_method:
        pytest.skip("Endpoint missing route or http_method fields")
    result = service.trace_http_dependency(route, http_method)
    assert isinstance(result, dict), "Expected dict from trace_http_dependency"
    _assert_conforms(result, TraceHttpDependencyResult, context="trace_http_dependency")


# ---------------------------------------------------------------------------
# Misc
# ---------------------------------------------------------------------------

@pytest.mark.integration
@pytest.mark.timeout(30)
def test_find_type_references_conforms(service) -> None:
    results = service.find_type_references("SynappsTest.Services.ITaskService")
    if isinstance(results, dict):
        items = results.get("results", [])
    else:
        items = results
    if not items:
        pytest.skip("No type references found for ITaskService in fixture")
    _assert_conforms(items[0], FindTypeReferencesResult, context="find_type_references")


@pytest.mark.integration
@pytest.mark.timeout(30)
def test_list_projects_conforms(service) -> None:
    results = service.list_projects()
    assert isinstance(results, list) and results, "Expected non-empty list from list_projects"
    _assert_conforms(results[0], ListProjectsResult, context="list_projects")


@pytest.mark.integration
@pytest.mark.timeout(30)
def test_list_summarized_conforms(service) -> None:
    results = service.list_summarized()
    if not results:
        pytest.skip("No summarized symbols found in fixture")
    _assert_conforms(results[0], ListSummarizedResult, context="list_summarized")
