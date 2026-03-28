from __future__ import annotations

from synapps.indexer.http.interface import HttpClientCall, HttpEndpointDef
from synapps.indexer.http.matcher import match_endpoints, MatchedEndpoint


def _ep(route: str, method: str = "GET", handler: str = "Handler") -> HttpEndpointDef:
    return HttpEndpointDef(route=route, http_method=method, handler_full_name=handler, line=1)


def _call(route: str, method: str = "GET", caller: str = "Caller") -> HttpClientCall:
    return HttpClientCall(route=route, http_method=method, caller_full_name=caller, line=1, col=0)


def test_exact_match() -> None:
    result = match_endpoints([_ep("/api/items", "GET")], [_call("/api/items", "GET")])
    assert len(result) == 1
    assert result[0].endpoint_def is not None
    assert result[0].client_calls == [_call("/api/items", "GET")]


def test_parameterized_match() -> None:
    result = match_endpoints(
        [_ep("/api/items/{id}", "GET")],
        [_call("/api/items/{id}", "GET")],
    )
    assert len(result) == 1
    assert result[0].endpoint_def is not None


def test_param_names_ignored() -> None:
    """Server {id} matches client {itemId}."""
    result = match_endpoints(
        [_ep("/api/items/{id}", "GET")],
        [_call("/api/items/{itemId}", "GET")],
    )
    assert len(result) == 1
    assert result[0].endpoint_def is not None
    assert len(result[0].client_calls) == 1


def test_method_mismatch_no_match() -> None:
    result = match_endpoints(
        [_ep("/api/items", "GET")],
        [_call("/api/items", "POST")],
    )
    # Both exist but no match between them
    matched_with_both = [r for r in result if r.endpoint_def is not None and r.client_calls]
    assert len(matched_with_both) == 0


def test_base_path_prefix_matching() -> None:
    """Client /items should match server /api/items via prefix fallback."""
    result = match_endpoints(
        [_ep("/api/items", "GET")],
        [_call("/items", "GET")],
    )
    matched_with_both = [r for r in result if r.endpoint_def is not None and r.client_calls]
    assert len(matched_with_both) == 1


def test_unmatched_server_endpoint() -> None:
    result = match_endpoints([_ep("/api/items", "GET")], [])
    assert len(result) == 1
    assert result[0].endpoint_def is not None
    assert result[0].client_calls == []


def test_unmatched_client_call() -> None:
    result = match_endpoints([], [_call("/external/api", "GET")])
    assert len(result) == 1
    assert result[0].endpoint_def is None
    assert len(result[0].client_calls) == 1


def test_multiple_clients_same_endpoint() -> None:
    result = match_endpoints(
        [_ep("/api/items", "GET", "Ctrl.Get")],
        [
            _call("/api/items", "GET", "svcA.get"),
            _call("/api/items", "GET", "svcB.get"),
        ],
    )
    matched = [r for r in result if r.endpoint_def is not None and r.client_calls]
    assert len(matched) == 1
    assert len(matched[0].client_calls) == 2


def test_param_vs_literal_no_match() -> None:
    """{param} on server should NOT match a literal on client."""
    result = match_endpoints(
        [_ep("/api/items/{id}", "GET")],
        [_call("/api/items/123", "GET")],
    )
    matched_with_both = [r for r in result if r.endpoint_def is not None and r.client_calls]
    assert len(matched_with_both) == 0


def test_empty_inputs() -> None:
    assert match_endpoints([], []) == []
