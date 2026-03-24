from __future__ import annotations

from synapse.indexer.http.interface import (
    HttpClientCall,
    HttpEndpointDef,
    HttpExtractionResult,
)


def test_endpoint_def_fields() -> None:
    ep = HttpEndpointDef(
        route="/api/items/{id}",
        http_method="GET",
        handler_full_name="ItemsController.GetById",
        line=10,
    )
    assert ep.route == "/api/items/{id}"
    assert ep.http_method == "GET"
    assert ep.handler_full_name == "ItemsController.GetById"
    assert ep.line == 10


def test_client_call_fields() -> None:
    call = HttpClientCall(
        route="/items/{id}",
        http_method="GET",
        caller_full_name="itemService.getById",
        line=5,
        col=4,
    )
    assert call.route == "/items/{id}"
    assert call.http_method == "GET"
    assert call.caller_full_name == "itemService.getById"
    assert call.line == 5
    assert call.col == 4


def test_extraction_result_defaults_empty() -> None:
    result = HttpExtractionResult()
    assert result.endpoint_defs == []
    assert result.client_calls == []


def test_extraction_result_with_data() -> None:
    ep = HttpEndpointDef("/api/items", "POST", "ItemsController.Create", 20)
    call = HttpClientCall("/items", "POST", "itemService.create", 8, 2)
    result = HttpExtractionResult(endpoint_defs=[ep], client_calls=[call])
    assert len(result.endpoint_defs) == 1
    assert len(result.client_calls) == 1
