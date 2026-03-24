# HTTP Endpoint Extraction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enable bidirectional tracing between frontend HTTP clients and backend API handlers in the Synapse code intelligence graph.

**Architecture:** New Phase 4 in the indexing pipeline. Each language plugin optionally provides an `HttpExtractor` that returns server-side endpoint definitions and/or client-side HTTP calls. A route matcher connects them through intermediate `Endpoint` nodes. Feature is experimental and opt-in via config.

**Tech Stack:** Python 3.11, tree-sitter (all parsing), Memgraph (graph storage), existing plugin/indexer architecture.

**Spec:** `docs/superpowers/specs/2026-03-23-http-endpoint-extraction-design.md`

---

### Task 1: Core Data Types and HttpExtractor Protocol

**Files:**
- Create: `src/synapse/indexer/http/__init__.py`
- Create: `src/synapse/indexer/http/interface.py`
- Test: `tests/unit/indexer/http/test_interface.py`

- [ ] **Step 1: Create package directory**

```bash
mkdir -p src/synapse/indexer/http
mkdir -p tests/unit/indexer/http
mkdir -p tests/unit/graph
mkdir -p tests/unit/plugin
touch tests/unit/indexer/http/__init__.py
touch tests/unit/graph/__init__.py 2>/dev/null || true
touch tests/unit/plugin/__init__.py 2>/dev/null || true
```

- [ ] **Step 2: Write the failing test for data types**

```python
# tests/unit/indexer/http/test_interface.py
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
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd /Users/alex/Dev/synapse && source .venv/bin/activate && pytest tests/unit/indexer/http/test_interface.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 4: Write the interface module**

```python
# src/synapse/indexer/http/__init__.py
```

```python
# src/synapse/indexer/http/interface.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from tree_sitter import Tree

from synapse.lsp.interface import IndexSymbol


@dataclass(frozen=True)
class HttpEndpointDef:
    """A server-side HTTP endpoint definition extracted from source."""

    route: str
    http_method: str
    handler_full_name: str
    line: int


@dataclass(frozen=True)
class HttpClientCall:
    """A client-side HTTP call extracted from source."""

    route: str
    http_method: str
    caller_full_name: str
    line: int
    col: int


@dataclass
class HttpExtractionResult:
    """Combined result from an HTTP extractor — may contain server defs, client calls, or both."""

    endpoint_defs: list[HttpEndpointDef] = field(default_factory=list)
    client_calls: list[HttpClientCall] = field(default_factory=list)


class HttpExtractor(Protocol):
    """Protocol for language-specific HTTP extraction."""

    def extract(
        self,
        file_path: str,
        tree: Tree,
        symbols: list[IndexSymbol],
    ) -> HttpExtractionResult: ...
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd /Users/alex/Dev/synapse && source .venv/bin/activate && pytest tests/unit/indexer/http/test_interface.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/synapse/indexer/http/ tests/unit/indexer/http/
git commit -m "feat(http): add core data types and HttpExtractor protocol"
```

---

### Task 2: Route Normalization Utility

**Files:**
- Create: `src/synapse/indexer/http/route_utils.py`
- Test: `tests/unit/indexer/http/test_route_utils.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/indexer/http/test_route_utils.py
from __future__ import annotations

from synapse.indexer.http.route_utils import normalize_route


def test_strips_type_constraints() -> None:
    assert normalize_route("{id:guid}") == "/{id}"
    assert normalize_route("{id:int}") == "/{id}"
    assert normalize_route("items/{slug:alpha}") == "/items/{slug}"


def test_strips_regex_constraints() -> None:
    assert normalize_route("{slug:[a-z]+}") == "/{slug}"


def test_ensures_leading_slash() -> None:
    assert normalize_route("api/items") == "/api/items"


def test_strips_trailing_slash() -> None:
    assert normalize_route("/api/items/") == "/api/items"


def test_collapses_double_slashes() -> None:
    assert normalize_route("/api//items") == "/api/items"


def test_preserves_case() -> None:
    assert normalize_route("/Api/Items") == "/Api/Items"


def test_empty_returns_root() -> None:
    assert normalize_route("") == "/"


def test_already_normalized() -> None:
    assert normalize_route("/api/items/{id}") == "/api/items/{id}"


def test_combines_class_and_method_route() -> None:
    assert normalize_route("api/items", "{id:guid}") == "/api/items/{id}"


def test_method_route_only() -> None:
    assert normalize_route("", "items/{id}") == "/items/{id}"


def test_tilde_override_ignores_class_route() -> None:
    assert normalize_route("api/items", "~/api/auth/me") == "/api/auth/me"


def test_multiple_params() -> None:
    assert normalize_route("api/{org:guid}/items/{id:int}") == "/api/{org}/items/{id}"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/alex/Dev/synapse && source .venv/bin/activate && pytest tests/unit/indexer/http/test_route_utils.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write the implementation**

```python
# src/synapse/indexer/http/route_utils.py
from __future__ import annotations

import re

# Matches {name:constraint} or {name:regex} patterns — captures just the name
_PARAM_CONSTRAINT_RE = re.compile(r"\{(\w+):[^}]+\}")


def normalize_route(class_route: str, method_route: str = "") -> str:
    """Combine and normalize a server-side route pattern.

    Handles ASP.NET conventions:
    - Tilde prefix on method_route overrides the class route
    - Type constraints are stripped: {id:guid} -> {id}
    - Leading / ensured, trailing / stripped, // collapsed
    """
    if method_route.startswith("~"):
        raw = method_route.lstrip("~").lstrip("/")
    elif class_route and method_route:
        raw = class_route.strip("/") + "/" + method_route.strip("/")
    elif class_route:
        raw = class_route.strip("/")
    elif method_route:
        raw = method_route.strip("/")
    else:
        return "/"

    # Strip type/regex constraints from route parameters
    raw = _PARAM_CONSTRAINT_RE.sub(r"{\1}", raw)

    # Ensure leading slash, strip trailing, collapse doubles
    raw = "/" + raw.lstrip("/")
    raw = raw.rstrip("/") or "/"
    while "//" in raw:
        raw = raw.replace("//", "/")

    return raw
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/alex/Dev/synapse && source .venv/bin/activate && pytest tests/unit/indexer/http/test_route_utils.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/synapse/indexer/http/route_utils.py tests/unit/indexer/http/test_route_utils.py
git commit -m "feat(http): add route normalization utility"
```

---

### Task 3: Route Matcher

**Files:**
- Create: `src/synapse/indexer/http/matcher.py`
- Test: `tests/unit/indexer/http/test_matcher.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/indexer/http/test_matcher.py
from __future__ import annotations

from synapse.indexer.http.interface import HttpClientCall, HttpEndpointDef
from synapse.indexer.http.matcher import match_endpoints, MatchedEndpoint


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/alex/Dev/synapse && source .venv/bin/activate && pytest tests/unit/indexer/http/test_matcher.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write the implementation**

```python
# src/synapse/indexer/http/matcher.py
from __future__ import annotations

import re
from dataclasses import dataclass, field

from synapse.indexer.http.interface import HttpClientCall, HttpEndpointDef

_PARAM_RE = re.compile(r"^\{[^}]+\}$")
_API_PREFIXES = ["/api", "/api/v1", "/api/v2"]


@dataclass
class MatchedEndpoint:
    """Result of matching: an endpoint with its server def (if any) and client calls (if any)."""

    route: str
    http_method: str
    endpoint_def: HttpEndpointDef | None = None
    client_calls: list[HttpClientCall] = field(default_factory=list)


def _segments(route: str) -> list[str]:
    return [s for s in route.split("/") if s]


def _routes_match(server_segs: list[str], client_segs: list[str]) -> bool:
    if len(server_segs) != len(client_segs):
        return False
    for s_seg, c_seg in zip(server_segs, client_segs):
        s_is_param = bool(_PARAM_RE.match(s_seg))
        c_is_param = bool(_PARAM_RE.match(c_seg))
        if s_is_param and c_is_param:
            continue
        if s_is_param != c_is_param:
            return False
        if s_seg != c_seg:
            return False
    return True


def match_endpoints(
    endpoint_defs: list[HttpEndpointDef],
    client_calls: list[HttpClientCall],
) -> list[MatchedEndpoint]:
    """Match client HTTP calls to server endpoint definitions by route and HTTP method."""
    if not endpoint_defs and not client_calls:
        return []

    # Index server endpoints by (route_segments_tuple, http_method) for O(1) lookup
    # Also build a list keyed by http_method for prefix fallback
    server_by_method: dict[str, list[tuple[list[str], HttpEndpointDef]]] = {}
    results_by_key: dict[tuple[str, str], MatchedEndpoint] = {}

    for ep in endpoint_defs:
        segs = _segments(ep.route)
        server_by_method.setdefault(ep.http_method, []).append((segs, ep))
        key = (ep.route, ep.http_method)
        if key not in results_by_key:
            results_by_key[key] = MatchedEndpoint(
                route=ep.route, http_method=ep.http_method, endpoint_def=ep,
            )

    unmatched_calls: list[HttpClientCall] = []

    for call in client_calls:
        call_segs = _segments(call.route)
        matched = False

        # Try direct match first, then prefix fallback
        candidates = [call_segs]
        for prefix in _API_PREFIXES:
            candidates.append(_segments(prefix + "/" + call.route.lstrip("/")))

        for candidate_segs in candidates:
            if matched:
                break
            for server_segs, ep in server_by_method.get(call.http_method, []):
                if _routes_match(server_segs, candidate_segs):
                    key = (ep.route, ep.http_method)
                    results_by_key[key].client_calls.append(call)
                    matched = True
                    break

        if not matched:
            unmatched_calls.append(call)

    # Add unmatched client calls as standalone entries
    for call in unmatched_calls:
        key = (call.route, call.http_method)
        if key in results_by_key:
            results_by_key[key].client_calls.append(call)
        else:
            results_by_key[key] = MatchedEndpoint(
                route=call.route, http_method=call.http_method, client_calls=[call],
            )

    return list(results_by_key.values())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/alex/Dev/synapse && source .venv/bin/activate && pytest tests/unit/indexer/http/test_matcher.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/synapse/indexer/http/matcher.py tests/unit/indexer/http/test_matcher.py
git commit -m "feat(http): add route matcher with prefix fallback"
```

---

### Task 4: Graph Model — Endpoint Node, SERVES/HTTP_CALLS Edges

**Files:**
- Modify: `src/synapse/graph/schema.py:8-18` (add Endpoint to `_INDEX_DEFS`)
- Modify: `src/synapse/graph/nodes.py` (add `upsert_endpoint`)
- Modify: `src/synapse/graph/edges.py:36-55` (add `upsert_serves`, `upsert_http_calls`, `batch_upsert_serves`, `batch_upsert_http_calls`; update `delete_outgoing_edges_for_file` at line 203)
- Test: `tests/unit/graph/test_http_graph_ops.py`

The graph operations follow the exact same patterns as existing `upsert_calls`/`upsert_method` (see `edges.py:36-55`, `nodes.py:59-84`). Unit tests use a mock `GraphConnection` to verify correct Cypher is generated.

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/graph/test_http_graph_ops.py
from __future__ import annotations

from unittest.mock import MagicMock

from synapse.graph.nodes import upsert_endpoint
from synapse.graph.edges import (
    upsert_serves,
    upsert_http_calls,
    batch_upsert_serves,
    batch_upsert_http_calls,
    delete_orphan_endpoints,
)


def _mock_conn() -> MagicMock:
    return MagicMock()


def test_upsert_endpoint_executes_merge() -> None:
    conn = _mock_conn()
    upsert_endpoint(conn, route="/api/items/{id}", http_method="GET", name="GET /api/items/{id}")
    conn.execute.assert_called_once()
    cypher = conn.execute.call_args[0][0]
    assert "MERGE" in cypher
    assert "Endpoint" in cypher


def test_upsert_serves_executes_merge() -> None:
    conn = _mock_conn()
    upsert_serves(conn, handler_full_name="Ctrl.Get", route="/api/items", http_method="GET")
    conn.execute.assert_called_once()
    cypher = conn.execute.call_args[0][0]
    assert "SERVES" in cypher
    assert "Method" in cypher
    assert "Endpoint" in cypher


def test_upsert_http_calls_with_call_site() -> None:
    conn = _mock_conn()
    upsert_http_calls(conn, caller_full_name="svc.get", route="/api/items", http_method="GET", line=10, col=4)
    conn.execute.assert_called_once()
    cypher = conn.execute.call_args[0][0]
    assert "HTTP_CALLS" in cypher
    assert "call_sites" in cypher


def test_batch_upsert_serves_skips_empty() -> None:
    conn = _mock_conn()
    batch_upsert_serves(conn, [])
    conn.execute.assert_not_called()


def test_batch_upsert_http_calls_skips_empty() -> None:
    conn = _mock_conn()
    batch_upsert_http_calls(conn, [])
    conn.execute.assert_not_called()


def test_batch_upsert_serves_executes_unwind() -> None:
    conn = _mock_conn()
    batch_upsert_serves(conn, [{"handler": "Ctrl.Get", "route": "/api/items", "http_method": "GET"}])
    conn.execute.assert_called_once()
    cypher = conn.execute.call_args[0][0]
    assert "UNWIND" in cypher
    assert "SERVES" in cypher


def test_batch_upsert_http_calls_executes_unwind() -> None:
    conn = _mock_conn()
    batch_upsert_http_calls(conn, [{"caller": "svc.get", "route": "/api/items", "http_method": "GET", "line": 10, "col": 4}])
    conn.execute.assert_called_once()
    cypher = conn.execute.call_args[0][0]
    assert "UNWIND" in cypher
    assert "HTTP_CALLS" in cypher


def test_delete_orphan_endpoints() -> None:
    conn = _mock_conn()
    delete_orphan_endpoints(conn, "/repo/path")
    conn.execute.assert_called_once()
    cypher = conn.execute.call_args[0][0]
    assert "Endpoint" in cypher
    assert "DELETE" in cypher
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/alex/Dev/synapse && source .venv/bin/activate && pytest tests/unit/graph/test_http_graph_ops.py -v`
Expected: FAIL with `ImportError`

- [ ] **Step 3: Add Endpoint to graph schema index**

In `src/synapse/graph/schema.py`, add `("Endpoint", "route")` to `_INDEX_DEFS`:

```python
# After line 17: ("Field", "full_name"),
    ("Endpoint", "route"),
```

- [ ] **Step 4: Add `upsert_endpoint` to `nodes.py`**

Append to `src/synapse/graph/nodes.py` (after the existing `upsert_field` function):

```python
def upsert_endpoint(conn: GraphConnection, route: str, http_method: str, name: str) -> None:
    conn.execute(
        "MERGE (n:Endpoint {route: $route, http_method: $http_method}) "
        "SET n.name = $name",
        {"route": route, "http_method": http_method, "name": name},
    )
```

- [ ] **Step 5: Add HTTP edge functions to `edges.py`**

Append to `src/synapse/graph/edges.py`:

```python
def upsert_serves(conn: GraphConnection, handler_full_name: str, route: str, http_method: str) -> None:
    conn.execute(
        "MATCH (src:Method {full_name: $handler}), (dst:Endpoint {route: $route, http_method: $http_method}) "
        "MERGE (src)-[:SERVES]->(dst)",
        {"handler": handler_full_name, "route": route, "http_method": http_method},
    )


def upsert_http_calls(
    conn: GraphConnection,
    caller_full_name: str,
    route: str,
    http_method: str,
    line: int | None = None,
    col: int | None = None,
) -> None:
    if line is not None:
        conn.execute(
            "MATCH (src:Method {full_name: $caller}), (dst:Endpoint {route: $route, http_method: $http_method}) "
            "MERGE (src)-[r:HTTP_CALLS]->(dst) "
            "SET r.call_sites = coalesce(r.call_sites, []) + [[$line, $col]]",
            {"caller": caller_full_name, "route": route, "http_method": http_method, "line": line, "col": col},
        )
    else:
        conn.execute(
            "MATCH (src:Method {full_name: $caller}), (dst:Endpoint {route: $route, http_method: $http_method}) "
            "MERGE (src)-[:HTTP_CALLS]->(dst)",
            {"caller": caller_full_name, "route": route, "http_method": http_method},
        )


def batch_upsert_serves(conn: GraphConnection, batch: list[dict]) -> None:
    """Batch-write SERVES edges from Method nodes to Endpoint nodes."""
    if not batch:
        return
    conn.execute(
        "UNWIND $batch AS row "
        "MATCH (src:Method {full_name: row.handler}), (dst:Endpoint {route: row.route, http_method: row.http_method}) "
        "MERGE (src)-[:SERVES]->(dst)",
        {"batch": batch},
    )


def batch_upsert_http_calls(conn: GraphConnection, batch: list[dict]) -> None:
    """Batch-write HTTP_CALLS edges from Method nodes to Endpoint nodes."""
    if not batch:
        return
    conn.execute(
        "UNWIND $batch AS row "
        "MATCH (src:Method {full_name: row.caller}), (dst:Endpoint {route: row.route, http_method: row.http_method}) "
        "MERGE (src)-[r:HTTP_CALLS]->(dst) "
        "SET r.call_sites = coalesce(r.call_sites, []) + [[row.line, row.col]]",
        {"batch": batch},
    )


def delete_orphan_endpoints(conn: GraphConnection, repo_path: str) -> None:
    """Delete Endpoint nodes with no SERVES or HTTP_CALLS edges."""
    conn.execute(
        "MATCH (r:Repository {path: $repo})-[:CONTAINS]->(ep:Endpoint) "
        "WHERE NOT ()-[:SERVES]->(ep) AND NOT ()-[:HTTP_CALLS]->(ep) "
        "DETACH DELETE ep",
        {"repo": repo_path},
    )
```

- [ ] **Step 6: Update `delete_outgoing_edges_for_file` to include HTTP edges**

In `src/synapse/graph/edges.py:203`, add `'SERVES', 'HTTP_CALLS'` to the edge type list:

```python
# Before:
"WHERE type(r) IN ['CALLS', 'REFERENCES', 'INHERITS', 'IMPLEMENTS', 'DISPATCHES_TO', 'OVERRIDES'] "

# After:
"WHERE type(r) IN ['CALLS', 'REFERENCES', 'INHERITS', 'IMPLEMENTS', 'DISPATCHES_TO', 'OVERRIDES', 'SERVES', 'HTTP_CALLS'] "
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `cd /Users/alex/Dev/synapse && source .venv/bin/activate && pytest tests/unit/graph/test_http_graph_ops.py -v`
Expected: PASS

- [ ] **Step 8: Run existing tests to verify no regression**

Run: `cd /Users/alex/Dev/synapse && source .venv/bin/activate && pytest tests/unit/ -v`
Expected: All PASS

- [ ] **Step 9: Commit**

```bash
git add src/synapse/graph/schema.py src/synapse/graph/nodes.py src/synapse/graph/edges.py tests/unit/graph/test_http_graph_ops.py
git commit -m "feat(http): add Endpoint node and SERVES/HTTP_CALLS edge operations"
```

---

### Task 5: C# Server-Side HTTP Extractor

**Files:**
- Create: `src/synapse/indexer/csharp/csharp_http_extractor.py`
- Test: `tests/unit/indexer/http/test_csharp_http_extractor.py`

This extractor detects ASP.NET Core controller patterns: `[ApiController]` on the class, `[Route("...")]` for the base route, `[HttpGet("...")]` etc. on methods. It extracts attribute argument string values — a capability the existing `CSharpAttributeExtractor` does not have.

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/indexer/http/test_csharp_http_extractor.py
from __future__ import annotations

import tree_sitter_c_sharp
from tree_sitter import Language, Parser

from synapse.indexer.csharp.csharp_http_extractor import CSharpHttpExtractor
from synapse.lsp.interface import IndexSymbol, SymbolKind

_lang = Language(tree_sitter_c_sharp.language())
_parser = Parser(_lang)


def _parse(source: str):
    return _parser.parse(bytes(source, "utf-8"))


def _symbols(pairs: list[tuple[str, str, int]]) -> list[IndexSymbol]:
    """Build IndexSymbol list from (name, full_name, line) triples."""
    return [
        IndexSymbol(name=n, full_name=fn, kind=SymbolKind.METHOD, file_path="test.cs", line=ln)
        for n, fn, ln in pairs
    ]


def test_basic_controller_endpoint() -> None:
    source = '''
[ApiController]
[Route("api/items")]
public class ItemsController : ControllerBase {
    [HttpGet]
    public IActionResult GetAll() { }
}
'''
    extractor = CSharpHttpExtractor()
    result = extractor.extract("test.cs", _parse(source), _symbols([("GetAll", "ItemsController.GetAll", 5)]))
    assert len(result.endpoint_defs) == 1
    ep = result.endpoint_defs[0]
    assert ep.route == "/api/items"
    assert ep.http_method == "GET"
    assert ep.handler_full_name == "ItemsController.GetAll"


def test_method_route_suffix() -> None:
    source = '''
[ApiController]
[Route("api/items")]
public class ItemsController : ControllerBase {
    [HttpGet("{id:guid}")]
    public IActionResult GetById(Guid id) { }
}
'''
    extractor = CSharpHttpExtractor()
    result = extractor.extract("test.cs", _parse(source), _symbols([("GetById", "ItemsController.GetById", 5)]))
    assert len(result.endpoint_defs) == 1
    assert result.endpoint_defs[0].route == "/api/items/{id}"
    assert result.endpoint_defs[0].http_method == "GET"


def test_post_with_sub_route() -> None:
    source = '''
[ApiController]
[Route("api/meetings")]
public class MeetingsController : ControllerBase {
    [HttpPost("{id:guid}/complete")]
    public IActionResult Complete(Guid id) { }
}
'''
    extractor = CSharpHttpExtractor()
    result = extractor.extract("test.cs", _parse(source), _symbols([("Complete", "MeetingsController.Complete", 5)]))
    assert result.endpoint_defs[0].route == "/api/meetings/{id}/complete"
    assert result.endpoint_defs[0].http_method == "POST"


def test_tilde_overrides_class_route() -> None:
    source = '''
[ApiController]
[Route("api/users")]
public class UsersController : ControllerBase {
    [HttpGet("~/api/auth/me")]
    public IActionResult GetAuthMe() { }
}
'''
    extractor = CSharpHttpExtractor()
    result = extractor.extract("test.cs", _parse(source), _symbols([("GetAuthMe", "UsersController.GetAuthMe", 5)]))
    assert result.endpoint_defs[0].route == "/api/auth/me"


def test_multiple_verbs_on_class() -> None:
    source = '''
[ApiController]
[Route("api/items")]
public class ItemsController : ControllerBase {
    [HttpGet]
    public IActionResult GetAll() { }

    [HttpPost]
    public IActionResult Create() { }

    [HttpDelete("{id:guid}")]
    public IActionResult Delete(Guid id) { }
}
'''
    extractor = CSharpHttpExtractor()
    result = extractor.extract(
        "test.cs",
        _parse(source),
        _symbols([
            ("GetAll", "ItemsController.GetAll", 5),
            ("Create", "ItemsController.Create", 8),
            ("Delete", "ItemsController.Delete", 11),
        ]),
    )
    assert len(result.endpoint_defs) == 3
    routes = {(ep.route, ep.http_method) for ep in result.endpoint_defs}
    assert ("/api/items", "GET") in routes
    assert ("/api/items", "POST") in routes
    assert ("/api/items/{id}", "DELETE") in routes


def test_non_controller_class_skipped() -> None:
    source = '''
public class MyService {
    [HttpGet]
    public void DoSomething() { }
}
'''
    extractor = CSharpHttpExtractor()
    result = extractor.extract("test.cs", _parse(source), _symbols([("DoSomething", "MyService.DoSomething", 3)]))
    assert len(result.endpoint_defs) == 0


def test_no_client_calls_returned() -> None:
    """C# extractor only produces server-side defs."""
    source = '''
[ApiController]
[Route("api/items")]
public class ItemsController : ControllerBase {
    [HttpGet]
    public IActionResult GetAll() { }
}
'''
    extractor = CSharpHttpExtractor()
    result = extractor.extract("test.cs", _parse(source), _symbols([("GetAll", "ItemsController.GetAll", 5)]))
    assert result.client_calls == []


def test_empty_source() -> None:
    extractor = CSharpHttpExtractor()
    result = extractor.extract("test.cs", _parse(""), [])
    assert result.endpoint_defs == []
    assert result.client_calls == []


def test_controller_placeholder_in_route() -> None:
    source = '''
[ApiController]
[Route("api/[controller]")]
public class TasksController : ControllerBase {
    [HttpGet]
    public IActionResult GetAll() { }
}
'''
    extractor = CSharpHttpExtractor()
    result = extractor.extract("test.cs", _parse(source), _symbols([("GetAll", "TasksController.GetAll", 5)]))
    assert result.endpoint_defs[0].route == "/api/tasks"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/alex/Dev/synapse && source .venv/bin/activate && pytest tests/unit/indexer/http/test_csharp_http_extractor.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write the implementation**

```python
# src/synapse/indexer/csharp/csharp_http_extractor.py
from __future__ import annotations

import logging
import re

from tree_sitter import Tree

from synapse.indexer.http.interface import HttpEndpointDef, HttpExtractionResult
from synapse.indexer.http.route_utils import normalize_route
from synapse.indexer.tree_sitter_util import node_text
from synapse.lsp.interface import IndexSymbol

log = logging.getLogger(__name__)

_HTTP_VERB_MAP: dict[str, str] = {
    "HttpGet": "GET",
    "HttpPost": "POST",
    "HttpPut": "PUT",
    "HttpDelete": "DELETE",
    "HttpPatch": "PATCH",
}

_CONTROLLER_ATTRS = frozenset({"ApiController"})


class CSharpHttpExtractor:
    """Extract HTTP endpoint definitions from ASP.NET Core controllers."""

    def extract(
        self,
        file_path: str,
        tree: Tree,
        symbols: list[IndexSymbol],
    ) -> HttpExtractionResult:
        symbol_by_name_line: dict[tuple[str, int], IndexSymbol] = {}
        for sym in symbols:
            symbol_by_name_line[(sym.name, sym.line)] = sym

        endpoint_defs: list[HttpEndpointDef] = []
        self._walk(tree.root_node, endpoint_defs, symbol_by_name_line)
        return HttpExtractionResult(endpoint_defs=endpoint_defs)

    def _walk(
        self,
        node,
        results: list[HttpEndpointDef],
        symbol_map: dict[tuple[str, int], IndexSymbol],
    ) -> None:
        if node.type == "class_declaration":
            self._handle_class(node, results, symbol_map)
        for child in node.children:
            self._walk(child, results, symbol_map)

    def _handle_class(
        self,
        node,
        results: list[HttpEndpointDef],
        symbol_map: dict[tuple[str, int], IndexSymbol],
    ) -> None:
        attrs = _collect_attrs_with_args(node)
        attr_names = {name for name, _ in attrs}

        if not (_CONTROLLER_ATTRS & attr_names):
            return

        class_name = _extract_name(node)
        if not class_name:
            return

        # Extract class-level route
        class_route = ""
        for name, arg in attrs:
            if name == "Route" and arg:
                class_route = arg
                # Handle [controller] placeholder
                controller_name = class_name
                if controller_name.endswith("Controller"):
                    controller_name = controller_name[: -len("Controller")]
                class_route = re.sub(
                    r"\[controller\]", controller_name.lower(), class_route, flags=re.IGNORECASE,
                )
                break

        # Walk methods in this class
        for child in node.children:
            if child.type == "declaration_list":
                for member in child.children:
                    if member.type == "method_declaration":
                        self._handle_method(member, class_route, results, symbol_map)

    def _handle_method(
        self,
        node,
        class_route: str,
        results: list[HttpEndpointDef],
        symbol_map: dict[tuple[str, int], IndexSymbol],
    ) -> None:
        attrs = _collect_attrs_with_args(node)
        method_name = _extract_name(node)
        if not method_name:
            return

        # 1-indexed line for symbol lookup
        method_line = node.start_point[0] + 1

        # Find the full_name from the symbol map
        sym = symbol_map.get((method_name, method_line))
        if sym is None:
            # Try matching by name only (line might differ slightly)
            for (name, _line), s in symbol_map.items():
                if name == method_name:
                    sym = s
                    break
        if sym is None:
            return

        for attr_name, attr_arg in attrs:
            http_method = _HTTP_VERB_MAP.get(attr_name)
            if http_method is None:
                continue

            method_route = attr_arg or ""
            route = normalize_route(class_route, method_route)
            results.append(HttpEndpointDef(
                route=route,
                http_method=http_method,
                handler_full_name=sym.full_name,
                line=method_line,
            ))


def _collect_attrs_with_args(node) -> list[tuple[str, str]]:
    """Collect (attribute_name, first_string_arg_or_empty) from a declaration node."""
    attrs: list[tuple[str, str]] = []
    for child in node.children:
        if child.type == "attribute_list":
            for attr_child in child.children:
                if attr_child.type == "attribute":
                    name = _extract_attr_name(attr_child)
                    arg = _extract_first_string_arg(attr_child)
                    if name:
                        name = _normalize_attr_name(name)
                        attrs.append((name, arg))
    return attrs


def _extract_attr_name(attr_node) -> str | None:
    for child in attr_node.children:
        if child.type == "identifier":
            return node_text(child)
        if child.type == "qualified_name":
            return _extract_qualified_text(child)
    return None


def _extract_first_string_arg(attr_node) -> str:
    """Extract the first string literal argument from an attribute, or empty string."""
    for child in attr_node.children:
        if child.type == "attribute_argument_list":
            for arg_child in child.children:
                if arg_child.type == "attribute_argument":
                    return _find_string_literal(arg_child)
                # Direct string literal child
                text = _try_string_literal(arg_child)
                if text is not None:
                    return text
    return ""


def _find_string_literal(node) -> str:
    """Recursively find the first string literal in a node subtree."""
    text = _try_string_literal(node)
    if text is not None:
        return text
    for child in node.children:
        text = _find_string_literal(child)
        if text is not None:
            return text
    return ""


def _try_string_literal(node) -> str | None:
    if node.type in ("string_literal", "verbatim_string_literal"):
        raw = node_text(node)
        # Strip surrounding quotes
        if raw.startswith('"') and raw.endswith('"'):
            return raw[1:-1]
        if raw.startswith('@"') and raw.endswith('"'):
            return raw[2:-1]
    return None


def _extract_name(node) -> str | None:
    for child in node.children:
        if child.type == "identifier":
            return node_text(child)
    return None


def _normalize_attr_name(name: str) -> str:
    if name.endswith("Attribute") and name != "Attribute":
        parts = name.rsplit(".", 1)
        if parts[-1].endswith("Attribute") and parts[-1] != "Attribute":
            parts[-1] = parts[-1][: -len("Attribute")]
            return ".".join(parts)
    return name


def _extract_qualified_text(node) -> str:
    parts: list[str] = []
    for child in node.children:
        if child.type == "identifier":
            parts.append(node_text(child))
        elif child.type == "qualified_name":
            parts.append(_extract_qualified_text(child))
    return ".".join(parts)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/alex/Dev/synapse && source .venv/bin/activate && pytest tests/unit/indexer/http/test_csharp_http_extractor.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/synapse/indexer/csharp/csharp_http_extractor.py tests/unit/indexer/http/test_csharp_http_extractor.py
git commit -m "feat(http): add C# ASP.NET server-side HTTP extractor"
```

---

### Task 6: TypeScript Client-Side HTTP Extractor

**Files:**
- Create: `src/synapse/indexer/typescript/typescript_http_extractor.py`
- Test: `tests/unit/indexer/http/test_typescript_http_extractor.py`

This extractor detects HTTP client calls (`api.get(...)`, `fetch(...)`, `axios.post(...)`) and extracts URL paths with the three-tier resolution strategy (inline strings, constants, template literals).

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/indexer/http/test_typescript_http_extractor.py
from __future__ import annotations

import tree_sitter_typescript
from tree_sitter import Language, Parser

from synapse.indexer.typescript.typescript_http_extractor import TypeScriptHttpExtractor
from synapse.lsp.interface import IndexSymbol, SymbolKind

_lang = Language(tree_sitter_typescript.language_typescript())
_parser = Parser(_lang)


def _parse(source: str):
    return _parser.parse(bytes(source, "utf-8"))


def _symbols(pairs: list[tuple[str, str, int]]) -> list[IndexSymbol]:
    return [
        IndexSymbol(name=n, full_name=fn, kind=SymbolKind.METHOD, file_path="test.ts", line=ln)
        for n, fn, ln in pairs
    ]


def test_axios_style_get() -> None:
    source = """
function getItems() {
    return api.get('/items');
}
"""
    extractor = TypeScriptHttpExtractor()
    result = extractor.extract("test.ts", _parse(source), _symbols([("getItems", "mod.getItems", 2)]))
    assert len(result.client_calls) == 1
    call = result.client_calls[0]
    assert call.route == "/items"
    assert call.http_method == "GET"
    assert call.caller_full_name == "mod.getItems"


def test_axios_style_post() -> None:
    source = """
function createItem(data) {
    return api.post('/items', data);
}
"""
    extractor = TypeScriptHttpExtractor()
    result = extractor.extract("test.ts", _parse(source), _symbols([("createItem", "mod.createItem", 2)]))
    assert len(result.client_calls) == 1
    assert result.client_calls[0].http_method == "POST"


def test_fetch_with_method_option() -> None:
    source = """
function deleteItem(id) {
    return fetch('/items/' + id, { method: 'DELETE' });
}
"""
    extractor = TypeScriptHttpExtractor()
    result = extractor.extract("test.ts", _parse(source), _symbols([("deleteItem", "mod.deleteItem", 2)]))
    assert len(result.client_calls) == 1
    assert result.client_calls[0].http_method == "DELETE"


def test_fetch_defaults_to_get() -> None:
    source = """
function getItems() {
    return fetch('/items');
}
"""
    extractor = TypeScriptHttpExtractor()
    result = extractor.extract("test.ts", _parse(source), _symbols([("getItems", "mod.getItems", 2)]))
    assert len(result.client_calls) == 1
    assert result.client_calls[0].http_method == "GET"


def test_template_literal_parameterized() -> None:
    source = """
function getItem(id) {
    return api.get(`/items/${id}`);
}
"""
    extractor = TypeScriptHttpExtractor()
    result = extractor.extract("test.ts", _parse(source), _symbols([("getItem", "mod.getItem", 2)]))
    assert len(result.client_calls) == 1
    assert result.client_calls[0].route == "/items/{id}"


def test_constant_reference() -> None:
    source = """
const ITEMS_ENDPOINT = '/items';

function getItems() {
    return api.get(ITEMS_ENDPOINT);
}
"""
    extractor = TypeScriptHttpExtractor()
    result = extractor.extract("test.ts", _parse(source), _symbols([("getItems", "mod.getItems", 4)]))
    assert len(result.client_calls) == 1
    assert result.client_calls[0].route == "/items"


def test_false_positive_rejected_no_path() -> None:
    source = """
function lookup() {
    return map.get('some-key');
}
"""
    extractor = TypeScriptHttpExtractor()
    result = extractor.extract("test.ts", _parse(source), _symbols([("lookup", "mod.lookup", 2)]))
    assert len(result.client_calls) == 0


def test_dynamic_url_skipped() -> None:
    source = """
function getData() {
    return api.get(buildUrl('items'));
}
"""
    extractor = TypeScriptHttpExtractor()
    result = extractor.extract("test.ts", _parse(source), _symbols([("getData", "mod.getData", 2)]))
    assert len(result.client_calls) == 0


def test_no_server_defs_returned() -> None:
    """TypeScript client extractor only produces client calls (server-side is separate)."""
    source = """
function getItems() {
    return api.get('/items');
}
"""
    extractor = TypeScriptHttpExtractor()
    result = extractor.extract("test.ts", _parse(source), _symbols([("getItems", "mod.getItems", 2)]))
    assert result.endpoint_defs == []


def test_empty_source() -> None:
    extractor = TypeScriptHttpExtractor()
    result = extractor.extract("test.ts", _parse(""), [])
    assert result.client_calls == []
    assert result.endpoint_defs == []


def test_multiple_calls_in_one_function() -> None:
    source = """
async function sync() {
    await api.get('/items');
    await api.post('/items', data);
}
"""
    extractor = TypeScriptHttpExtractor()
    result = extractor.extract("test.ts", _parse(source), _symbols([("sync", "mod.sync", 2)]))
    assert len(result.client_calls) == 2
    methods = {c.http_method for c in result.client_calls}
    assert methods == {"GET", "POST"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/alex/Dev/synapse && source .venv/bin/activate && pytest tests/unit/indexer/http/test_typescript_http_extractor.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write the implementation**

```python
# src/synapse/indexer/typescript/typescript_http_extractor.py
from __future__ import annotations

import logging
import re

from tree_sitter import Tree

from synapse.indexer.http.interface import HttpClientCall, HttpExtractionResult
from synapse.indexer.tree_sitter_util import node_text
from synapse.lsp.interface import IndexSymbol

log = logging.getLogger(__name__)

_HTTP_VERBS = frozenset({"get", "post", "put", "delete", "patch"})
_TEMPLATE_EXPR_RE = re.compile(r"\$\{[^}]+\}")


class TypeScriptHttpExtractor:
    """Extract HTTP client calls from TypeScript/JavaScript source.

    Server-side extraction (Express, Fastify, Hono) will be added in a follow-up.
    """

    def extract(
        self,
        file_path: str,
        tree: Tree,
        symbols: list[IndexSymbol],
    ) -> HttpExtractionResult:
        # Build constants map: identifier -> string value
        constants: dict[str, str] = {}
        self._collect_constants(tree.root_node, constants)

        # Build scope lookup: (line range) -> symbol full_name
        sorted_symbols = sorted(
            [(s.line - 1, s.end_line - 1 if s.end_line else s.line - 1, s.full_name) for s in symbols],
            key=lambda t: t[0],
        )

        client_calls: list[HttpClientCall] = []
        self._walk(tree.root_node, client_calls, constants, sorted_symbols)
        return HttpExtractionResult(client_calls=client_calls)

    def _collect_constants(self, node, constants: dict[str, str]) -> None:
        """Collect top-level const/let assignments with string literal values."""
        if node.type in ("lexical_declaration",):
            for child in node.children:
                if child.type == "variable_declarator":
                    name_node = child.child_by_field_name("name")
                    value_node = child.child_by_field_name("value")
                    if name_node and value_node:
                        name = node_text(name_node)
                        val = _try_string_value(value_node)
                        if val is not None:
                            constants[name] = val
        for child in node.children:
            self._collect_constants(child, constants)

    def _walk(
        self,
        node,
        results: list[HttpClientCall],
        constants: dict[str, str],
        sorted_symbols: list[tuple[int, int, str]],
    ) -> None:
        if node.type == "call_expression":
            self._handle_call(node, results, constants, sorted_symbols)
        for child in node.children:
            self._walk(child, results, constants, sorted_symbols)

    def _handle_call(
        self,
        node,
        results: list[HttpClientCall],
        constants: dict[str, str],
        sorted_symbols: list[tuple[int, int, str]],
    ) -> None:
        func_node = node.child_by_field_name("function")
        if func_node is None:
            return

        http_method: str | None = None
        is_fetch = False

        if func_node.type == "member_expression":
            prop = func_node.child_by_field_name("property")
            if prop and node_text(prop).lower() in _HTTP_VERBS:
                http_method = node_text(prop).upper()
        elif func_node.type == "identifier" and node_text(func_node) == "fetch":
            is_fetch = True
            http_method = "GET"  # default, may be overridden by options

        if http_method is None and not is_fetch:
            return

        args_node = node.child_by_field_name("arguments")
        if args_node is None:
            return

        # Extract URL from first argument
        first_arg = _first_arg(args_node)
        if first_arg is None:
            return

        route = self._resolve_url(first_arg, constants)
        if route is None:
            return

        # Check URL looks like a path (false positive prevention)
        if "/" not in route:
            return

        # For fetch, check for method in options object
        if is_fetch:
            second_arg = _nth_arg(args_node, 1)
            if second_arg is not None:
                method_from_opts = _extract_method_from_object(second_arg)
                if method_from_opts:
                    http_method = method_from_opts.upper()

        # Find enclosing function
        line_0 = node.start_point[0]
        col_0 = node.start_point[1]
        caller = _find_enclosing(line_0, sorted_symbols)
        if caller is None:
            return

        results.append(HttpClientCall(
            route=route,
            http_method=http_method,
            caller_full_name=caller,
            line=line_0 + 1,
            col=col_0,
        ))

    def _resolve_url(self, node, constants: dict[str, str]) -> str | None:
        """Resolve the URL from a call argument node."""
        # Tier 1: string literal
        if node.type == "string":
            raw = node_text(node)
            return _strip_quotes(raw)

        # Tier 1: template literal
        if node.type == "template_string":
            return _template_to_route(node)

        # Tier 2: constant reference
        if node.type == "identifier":
            name = node_text(node)
            return constants.get(name)

        # Tier 3: binary expression (concatenation)
        if node.type == "binary_expression":
            return _concat_to_route(node, constants)

        return None


def _first_arg(args_node):
    """Get the first argument from an arguments node."""
    for child in args_node.children:
        if child.type not in ("(", ")", ","):
            return child
    return None


def _nth_arg(args_node, n: int):
    """Get the nth argument (0-indexed) from an arguments node."""
    idx = 0
    for child in args_node.children:
        if child.type not in ("(", ")", ","):
            if idx == n:
                return child
            idx += 1
    return None


def _try_string_value(node) -> str | None:
    if node.type == "string":
        return _strip_quotes(node_text(node))
    return None


def _strip_quotes(s: str) -> str:
    if len(s) >= 2 and s[0] in ('"', "'", "`") and s[-1] == s[0]:
        return s[1:-1]
    return s


def _template_to_route(node) -> str:
    """Convert a template literal to a parameterized route."""
    parts: list[str] = []
    for child in node.children:
        if child.type == "string_fragment":
            parts.append(node_text(child))
        elif child.type == "template_substitution":
            # Extract the expression name for the param placeholder
            expr = None
            for sub_child in child.children:
                if sub_child.type not in ("${", "}"):
                    expr = node_text(sub_child)
                    break
            parts.append("{" + (expr or "param") + "}")
        # Skip template_string start/end tokens
    return "".join(parts)


def _concat_to_route(node, constants: dict[str, str]) -> str | None:
    """Resolve string concatenation to a route, replacing dynamic parts with {param}."""
    left = node.child_by_field_name("left")
    right = node.child_by_field_name("right")
    if left is None or right is None:
        return None

    left_val = _resolve_simple(left, constants)
    right_val = _resolve_simple(right, constants)

    if left_val is None and right_val is None:
        return None

    left_str = left_val if left_val is not None else "{param}"
    right_str = right_val if right_val is not None else "{param}"
    return left_str + right_str


def _resolve_simple(node, constants: dict[str, str]) -> str | None:
    if node.type == "string":
        return _strip_quotes(node_text(node))
    if node.type == "identifier":
        return constants.get(node_text(node))
    return None


def _extract_method_from_object(node) -> str | None:
    """Extract 'method' property from an object literal like { method: 'DELETE' }."""
    if node.type != "object":
        return None
    for child in node.children:
        if child.type == "pair":
            key = child.child_by_field_name("key")
            value = child.child_by_field_name("value")
            if key and value and node_text(key) == "method":
                return _strip_quotes(node_text(value))
    return None


def _find_enclosing(line_0: int, sorted_symbols: list[tuple[int, int, str]]) -> str | None:
    """Find the innermost symbol enclosing the given 0-indexed line."""
    best: str | None = None
    best_start = -1
    for start, end, full_name in sorted_symbols:
        if start <= line_0 <= end and start > best_start:
            best = full_name
            best_start = start
    return best
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/alex/Dev/synapse && source .venv/bin/activate && pytest tests/unit/indexer/http/test_typescript_http_extractor.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/synapse/indexer/typescript/typescript_http_extractor.py tests/unit/indexer/http/test_typescript_http_extractor.py
git commit -m "feat(http): add TypeScript client-side HTTP extractor"
```

---

### Task 7: Wire Extractors into Language Plugins

**Files:**
- Modify: `src/synapse/plugin/csharp.py` (add `create_http_extractor` method)
- Modify: `src/synapse/plugin/typescript.py` (add `create_http_extractor` method)
- Test: `tests/unit/plugin/test_http_extractor_wiring.py`

Python and Java extractors will be added in follow-up tasks once the pipeline is proven end-to-end. For now, those plugins will lack the method (handled by `getattr` fallback).

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/plugin/test_http_extractor_wiring.py
from __future__ import annotations

from synapse.plugin.csharp import CSharpPlugin
from synapse.plugin.typescript import TypeScriptPlugin
from synapse.plugin.python import PythonPlugin
from synapse.plugin.java import JavaPlugin


def test_csharp_plugin_has_http_extractor() -> None:
    plugin = CSharpPlugin()
    extractor = plugin.create_http_extractor()
    assert extractor is not None


def test_typescript_plugin_has_http_extractor() -> None:
    plugin = TypeScriptPlugin()
    extractor = plugin.create_http_extractor()
    assert extractor is not None


def test_python_plugin_no_http_extractor_yet() -> None:
    plugin = PythonPlugin()
    assert not hasattr(plugin, "create_http_extractor")


def test_java_plugin_no_http_extractor_yet() -> None:
    plugin = JavaPlugin()
    assert not hasattr(plugin, "create_http_extractor")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/alex/Dev/synapse && source .venv/bin/activate && pytest tests/unit/plugin/test_http_extractor_wiring.py -v`
Expected: FAIL (CSharpPlugin has no `create_http_extractor`)

- [ ] **Step 3: Add `create_http_extractor` to CSharpPlugin**

In `src/synapse/plugin/csharp.py`, add the import and method. Add after the existing `create_assignment_extractor` method:

```python
    def create_http_extractor(self):
        from synapse.indexer.csharp.csharp_http_extractor import CSharpHttpExtractor
        return CSharpHttpExtractor()
```

- [ ] **Step 4: Add `create_http_extractor` to TypeScriptPlugin**

In `src/synapse/plugin/typescript.py`, add after the existing extractor methods:

```python
    def create_http_extractor(self):
        from synapse.indexer.typescript.typescript_http_extractor import TypeScriptHttpExtractor
        return TypeScriptHttpExtractor()
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd /Users/alex/Dev/synapse && source .venv/bin/activate && pytest tests/unit/plugin/test_http_extractor_wiring.py -v`
Expected: PASS

- [ ] **Step 6: Run all unit tests**

Run: `cd /Users/alex/Dev/synapse && source .venv/bin/activate && pytest tests/unit/ -v`
Expected: All PASS

- [ ] **Step 7: Commit**

```bash
git add src/synapse/plugin/csharp.py src/synapse/plugin/typescript.py tests/unit/plugin/test_http_extractor_wiring.py
git commit -m "feat(http): wire HTTP extractors into C# and TypeScript plugins"
```

---

### Task 8: Experimental Config Flag

**Files:**
- Create: `src/synapse/config.py`
- Test: `tests/unit/test_config.py`

Centralizes config reading (currently scattered across `container/manager.py` and `mcp/tools.py`). Reads `experimental.http_endpoints` from `.synapse/config.json`.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_config.py
from __future__ import annotations

import json
import os
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/alex/Dev/synapse && source .venv/bin/activate && pytest tests/unit/test_config.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write the implementation**

```python
# src/synapse/config.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/alex/Dev/synapse && source .venv/bin/activate && pytest tests/unit/test_config.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/synapse/config.py tests/unit/test_config.py
git commit -m "feat(http): add experimental config flag for HTTP endpoint extraction"
```

---

### Task 9: Indexer Phase 4 Integration

**Files:**
- Modify: `src/synapse/indexer/indexer.py:70-96` (constructor: add `_http_extractor_factory`)
- Modify: `src/synapse/indexer/indexer.py:213` (after attribute pass: add Phase 4)
- Modify: `src/synapse/indexer/indexer.py:293` (reindex_file: add HTTP extraction)
- Test: `tests/unit/indexer/test_http_phase.py`

This is the core integration — it wires the extractors, matcher, and graph operations into the indexing pipeline.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/indexer/test_http_phase.py
from __future__ import annotations

from unittest.mock import MagicMock, patch

from synapse.indexer.http.interface import HttpEndpointDef, HttpClientCall, HttpExtractionResult
from synapse.indexer.http_phase import HttpPhase


def _mock_conn() -> MagicMock:
    return MagicMock()


def test_phase_creates_endpoint_nodes_and_edges() -> None:
    """Verify that the phase creates Endpoint nodes and SERVES/HTTP_CALLS edges."""
    conn = _mock_conn()
    phase = HttpPhase(conn, repo_path="/repo")

    server_result = HttpExtractionResult(
        endpoint_defs=[HttpEndpointDef("/api/items", "GET", "Ctrl.GetAll", 10)],
    )
    client_result = HttpExtractionResult(
        client_calls=[HttpClientCall("/api/items", "GET", "svc.getAll", 5, 2)],
    )

    phase.run([server_result, client_result])

    # Should have called execute for: endpoint MERGE, CONTAINS, SERVES, HTTP_CALLS
    assert conn.execute.call_count >= 3


def test_phase_skips_when_no_results() -> None:
    conn = _mock_conn()
    phase = HttpPhase(conn, repo_path="/repo")
    phase.run([])
    conn.execute.assert_not_called()


def test_phase_handles_unmatched_server_endpoint() -> None:
    conn = _mock_conn()
    phase = HttpPhase(conn, repo_path="/repo")

    result = HttpExtractionResult(
        endpoint_defs=[HttpEndpointDef("/api/items", "GET", "Ctrl.GetAll", 10)],
    )
    phase.run([result])

    # Should still create endpoint and SERVES edge
    assert conn.execute.call_count >= 2


def test_phase_handles_unmatched_client_call() -> None:
    conn = _mock_conn()
    phase = HttpPhase(conn, repo_path="/repo")

    result = HttpExtractionResult(
        client_calls=[HttpClientCall("/external/api", "GET", "svc.fetch", 5, 2)],
    )
    phase.run([result])

    # Should create endpoint and HTTP_CALLS edge
    assert conn.execute.call_count >= 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/alex/Dev/synapse && source .venv/bin/activate && pytest tests/unit/indexer/test_http_phase.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write the HttpPhase class**

```python
# src/synapse/indexer/http_phase.py
from __future__ import annotations

import logging

from synapse.graph.connection import GraphConnection
from synapse.graph.edges import (
    batch_upsert_http_calls,
    batch_upsert_serves,
    delete_orphan_endpoints,
)
from synapse.graph.nodes import upsert_endpoint
from synapse.indexer.http.interface import HttpExtractionResult
from synapse.indexer.http.matcher import match_endpoints

log = logging.getLogger(__name__)


class HttpPhase:
    """Phase 4: HTTP endpoint extraction, matching, and graph writes."""

    def __init__(self, conn: GraphConnection, repo_path: str) -> None:
        self._conn = conn
        self._repo_path = repo_path

    def run(self, extraction_results: list[HttpExtractionResult]) -> None:
        """Run the matching phase and write results to the graph."""
        all_defs = []
        all_calls = []
        for result in extraction_results:
            all_defs.extend(result.endpoint_defs)
            all_calls.extend(result.client_calls)

        if not all_defs and not all_calls:
            return

        matched = match_endpoints(all_defs, all_calls)

        serves_batch: list[dict] = []
        http_calls_batch: list[dict] = []

        for m in matched:
            # Create endpoint node
            name = f"{m.http_method} {m.route}"
            upsert_endpoint(self._conn, route=m.route, http_method=m.http_method, name=name)

            # CONTAINS edge from repo
            self._conn.execute(
                "MATCH (r:Repository {path: $repo}), (ep:Endpoint {route: $route, http_method: $http_method}) "
                "MERGE (r)-[:CONTAINS]->(ep)",
                {"repo": self._repo_path, "route": m.route, "http_method": m.http_method},
            )

            # SERVES edge
            if m.endpoint_def is not None:
                serves_batch.append({
                    "handler": m.endpoint_def.handler_full_name,
                    "route": m.route,
                    "http_method": m.http_method,
                })

            # HTTP_CALLS edges
            for call in m.client_calls:
                http_calls_batch.append({
                    "caller": call.caller_full_name,
                    "route": m.route,
                    "http_method": m.http_method,
                    "line": call.line,
                    "col": call.col,
                })

        batch_upsert_serves(self._conn, serves_batch)
        batch_upsert_http_calls(self._conn, http_calls_batch)

        log.info(
            "[EXPERIMENTAL] HTTP endpoints: %d server endpoints, %d client calls, %d matched",
            len(all_defs),
            len(all_calls),
            sum(1 for m in matched if m.endpoint_def is not None and m.client_calls),
        )

    def cleanup_orphans(self) -> None:
        """Delete Endpoint nodes with no remaining edges."""
        delete_orphan_endpoints(self._conn, self._repo_path)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/alex/Dev/synapse && source .venv/bin/activate && pytest tests/unit/indexer/test_http_phase.py -v`
Expected: PASS

- [ ] **Step 5: Wire Phase 4 into `Indexer.__init__`**

In `src/synapse/indexer/indexer.py`, add to the constructor (after line 82):

```python
            self._http_extractor_factory = getattr(plugin, 'create_http_extractor', None)
```

And in the `else` branch (after line 94):

```python
            self._http_extractor_factory = None
```

- [ ] **Step 6: Wire Phase 4 into `Indexer.index_project`**

In `src/synapse/indexer/indexer.py`, after the attribute pass (after line 213, before MethodImplementsIndexer at line 215), add:

```python
        # Phase 4: HTTP endpoint extraction + matching (experimental, opt-in)
        if self._http_extractor_factory is not None:
            from synapse.config import is_http_endpoints_enabled
            if is_http_endpoints_enabled(root_path):
                t_http = time.monotonic()
                log.info(
                    "[EXPERIMENTAL] HTTP endpoint extraction is enabled. "
                    "This feature is experimental and may produce incomplete or incorrect endpoint mappings."
                )
                http_extractor = self._http_extractor_factory()
                http_results: list[HttpExtractionResult] = []
                for fp, pf in parsed_cache.items():
                    try:
                        file_symbols = symbols_by_file.get(fp, [])
                        http_results.append(http_extractor.extract(fp, pf.tree, file_symbols))
                    except Exception:
                        log.warning("Could not extract HTTP endpoints from %s", fp)

                from synapse.indexer.http_phase import HttpPhase
                http_phase = HttpPhase(self._conn, root_path)
                http_phase.run(http_results)
                http_phase.cleanup_orphans()
                log.info("HTTP endpoint extraction: %.1fs", time.monotonic() - t_http)
```

- [ ] **Step 7: Verify `reindex_file` HTTP edge cleanup**

No additional code needed — `delete_outgoing_edges_for_file` (called at `indexer.py:296`) already handles `SERVES` and `HTTP_CALLS` cleanup since we added them to the edge type list in Task 4, Step 6. Full HTTP re-matching on single-file reindex is deferred to `sync_project` level (Task 9a below).

- [ ] **Step 8: Run all unit tests**

Run: `cd /Users/alex/Dev/synapse && source .venv/bin/activate && pytest tests/unit/ -v`
Expected: All PASS

- [ ] **Step 9: Commit**

```bash
git add src/synapse/indexer/http_phase.py src/synapse/indexer/indexer.py tests/unit/indexer/test_http_phase.py
git commit -m "feat(http): integrate Phase 4 HTTP extraction into indexing pipeline"
```

---

### Task 9a: Sync-Level HTTP Re-Matching

**Files:**
- Modify: `src/synapse/service.py` (add post-sync HTTP re-match)
- Create: `src/synapse/indexer/http_phase.py` (add `rebuild_from_graph` method)
- Test: `tests/unit/indexer/test_http_phase.py` (add rebuild test)

The spec requires that on `sync_project`, the matcher re-runs for the full project. After all per-file reindex calls, we query existing HTTP data from the graph for unchanged files, merge with freshly extracted data from changed files, and re-match.

- [ ] **Step 1: Add `rebuild_from_graph` to HttpPhase**

In `src/synapse/indexer/http_phase.py`, add a method to reconstruct extraction results from existing graph data:

```python
    def rebuild_from_graph(self) -> tuple[list[HttpEndpointDef], list[HttpClientCall]]:
        """Reconstruct endpoint defs and client calls from existing graph data.

        Used during sync to get data for unchanged files.
        """
        from synapse.indexer.http.interface import HttpEndpointDef, HttpClientCall

        # Query existing server endpoints
        raw_defs = self._conn.query(
            "MATCH (m:Method)-[:SERVES]->(ep:Endpoint)<-[:CONTAINS]-(r:Repository {path: $repo}) "
            "RETURN ep.route, ep.http_method, m.full_name, m.line",
            {"repo": self._repo_path},
        )
        defs = [
            HttpEndpointDef(route=r[0], http_method=r[1], handler_full_name=r[2], line=r[3] or 0)
            for r in raw_defs
        ]

        # Query existing client calls
        raw_calls = self._conn.query(
            "MATCH (m:Method)-[r:HTTP_CALLS]->(ep:Endpoint)<-[:CONTAINS]-(repo:Repository {path: $repo}) "
            "RETURN ep.route, ep.http_method, m.full_name, m.line",
            {"repo": self._repo_path},
        )
        calls = [
            HttpClientCall(route=r[0], http_method=r[1], caller_full_name=r[2], line=r[3] or 0, col=0)
            for r in raw_calls
        ]

        return defs, calls
```

- [ ] **Step 2: Add test for rebuild_from_graph**

```python
# Append to tests/unit/indexer/test_http_phase.py

def test_rebuild_from_graph_queries_existing_data() -> None:
    conn = _mock_conn()
    conn.query = MagicMock(return_value=[])
    phase = HttpPhase(conn, repo_path="/repo")
    defs, calls = phase.rebuild_from_graph()
    assert defs == []
    assert calls == []
    assert conn.query.call_count == 2
```

- [ ] **Step 3: Hook re-matching into SynapseService.sync_project**

In `src/synapse/service.py`, after the per-file sync loop completes (around line 300, after `return total`), add a post-sync HTTP re-match step. This needs to be added to both `sync_project` and the git sync path in `smart_index`.

The exact integration point depends on the sync flow — look for where all per-file reindexing has completed and add:

```python
        # Post-sync HTTP re-matching (experimental)
        from synapse.config import is_http_endpoints_enabled
        if is_http_endpoints_enabled(path):
            from synapse.indexer.http_phase import HttpPhase
            http_phase = HttpPhase(self._conn, path)
            existing_defs, existing_calls = http_phase.rebuild_from_graph()
            from synapse.indexer.http.interface import HttpExtractionResult
            http_phase.run([HttpExtractionResult(endpoint_defs=existing_defs, client_calls=existing_calls)])
            http_phase.cleanup_orphans()
```

This is a lightweight operation — it queries existing endpoints from the graph (unchanged files) and re-runs the matcher. Changed files have already had their HTTP edges cleaned up by `delete_outgoing_edges_for_file` and their new data will be re-extracted by the per-file reindex.

- [ ] **Step 4: Run all unit tests**

Run: `cd /Users/alex/Dev/synapse && source .venv/bin/activate && pytest tests/unit/ -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add src/synapse/indexer/http_phase.py src/synapse/service.py tests/unit/indexer/test_http_phase.py
git commit -m "feat(http): add sync-level HTTP re-matching after per-file reindex"
```

---

### Task 10: MCP Instructions Update

**Files:**
- Modify: `src/synapse/mcp/instructions.py`

- [ ] **Step 1: Update MCP instructions**

In `src/synapse/mcp/instructions.py`, append to `SERVER_INSTRUCTIONS` (before the closing `"""`):

```python

HTTP ENDPOINTS (experimental):
- If a project has experimental.http_endpoints enabled in .synapse/config.json, \
the graph includes Endpoint nodes with SERVES and HTTP_CALLS edges for tracing \
frontend-to-backend HTTP dependencies.
- To find what frontend code calls a backend method: \
MATCH (m:Method)-[:SERVES]->(ep:Endpoint)<-[:HTTP_CALLS]-(caller) RETURN caller, ep
- To find what backend handler a frontend method hits: \
MATCH (m:Method)-[:HTTP_CALLS]->(ep:Endpoint)<-[:SERVES]-(handler) RETURN handler, ep
- Note: HTTP endpoint data is experimental and may be incomplete.\
```

- [ ] **Step 2: Run all unit tests**

Run: `cd /Users/alex/Dev/synapse && source .venv/bin/activate && pytest tests/unit/ -v`
Expected: All PASS

- [ ] **Step 3: Commit**

```bash
git add src/synapse/mcp/instructions.py
git commit -m "feat(http): add HTTP endpoint guidance to MCP instructions"
```

---

### Task 11: Integration Tests

**Files:**
- Create: `tests/fixtures/http_test_project/.synapse/config.json`
- Create: `tests/fixtures/http_test_project/backend/ItemsController.cs`
- Create: `tests/fixtures/http_test_project/frontend/itemService.ts`
- Modify: `tests/integration/conftest.py` (add HTTP fixture)
- Create: `tests/integration/test_http_endpoints.py`

These tests require Memgraph running (`docker compose up -d`). They index a fixture with C# controllers and TypeScript HTTP clients, then verify the graph.

**Important:** `SynapseService.execute_query` returns `[{"row": [val1, val2, ...]}, ...]` — values are positional, not keyed by column name. All assertions must use `r["row"][index]`.

- [ ] **Step 1: Create test fixture files**

```bash
mkdir -p tests/fixtures/http_test_project/.synapse
mkdir -p tests/fixtures/http_test_project/backend
mkdir -p tests/fixtures/http_test_project/frontend
```

```json
// tests/fixtures/http_test_project/.synapse/config.json
{
  "experimental": {
    "http_endpoints": true
  }
}
```

```csharp
// tests/fixtures/http_test_project/backend/ItemsController.cs
using Microsoft.AspNetCore.Mvc;

[ApiController]
[Route("api/items")]
public class ItemsController : ControllerBase
{
    [HttpGet]
    public IActionResult GetAll() { return Ok(); }

    [HttpGet("{id:guid}")]
    public IActionResult GetById(Guid id) { return Ok(); }

    [HttpPost]
    public IActionResult Create([FromBody] object request) { return Ok(); }
}
```

```typescript
// tests/fixtures/http_test_project/frontend/itemService.ts
const api = { get: (url: string) => {}, post: (url: string, data: any) => {} };

export const itemService = {
    getAll: () => api.get('/api/items'),
    getById: (id: string) => api.get(`/api/items/${id}`),
    create: (data: any) => api.post('/api/items', data),
};
```

- [ ] **Step 2: Add HTTP fixture to conftest.py**

In `tests/integration/conftest.py`, add the fixture path constant and session-scoped fixture:

```python
HTTP_FIXTURE_PATH = str(
    (pathlib.Path(__file__).parent.parent / "fixtures" / "http_test_project").resolve()
)

@pytest.fixture(scope="session")
def http_service():
    """Index the HTTP test fixture project (C# + TypeScript) and yield SynapseService."""
    conn = GraphConnection.create(database="memgraph")
    ensure_schema(conn)
    _delete_project(conn, HTTP_FIXTURE_PATH)

    svc = SynapseService(conn=conn)
    # Index both languages — C# first (server), then TypeScript (client)
    svc.index_project(HTTP_FIXTURE_PATH, "csharp")
    svc.index_project(HTTP_FIXTURE_PATH, "typescript")

    yield svc

    _delete_project(conn, HTTP_FIXTURE_PATH)
```

- [ ] **Step 3: Write the integration test**

```python
# tests/integration/test_http_endpoints.py
from __future__ import annotations

import json

import pytest

pytestmark = pytest.mark.integration


def test_endpoint_nodes_created(http_service) -> None:
    result = http_service.execute_query(
        "MATCH (ep:Endpoint) RETURN ep.route, ep.http_method ORDER BY ep.route, ep.http_method"
    )
    routes = [(r["row"][0], r["row"][1]) for r in result]
    assert ("/api/items", "GET") in routes
    assert ("/api/items", "POST") in routes
    assert ("/api/items/{id}", "GET") in routes


def test_serves_edges_created(http_service) -> None:
    result = http_service.execute_query(
        "MATCH (m:Method)-[:SERVES]->(ep:Endpoint) "
        "RETURN m.full_name, ep.route, ep.http_method"
    )
    serves = [(r["row"][0], r["row"][1], r["row"][2]) for r in result]
    assert any("GetAll" in s[0] and s[1] == "/api/items" and s[2] == "GET" for s in serves)
    assert any("Create" in s[0] and s[1] == "/api/items" and s[2] == "POST" for s in serves)


def test_http_calls_edges_created(http_service) -> None:
    result = http_service.execute_query(
        "MATCH (m:Method)-[:HTTP_CALLS]->(ep:Endpoint) "
        "RETURN m.full_name, ep.route, ep.http_method"
    )
    calls = [(r["row"][0], r["row"][1], r["row"][2]) for r in result]
    assert any("getAll" in c[0] and c[1] == "/api/items" and c[2] == "GET" for c in calls)


def test_bidirectional_query(http_service) -> None:
    result = http_service.execute_query(
        "MATCH (fe:Method)-[:HTTP_CALLS]->(ep:Endpoint)<-[:SERVES]-(be:Method) "
        "RETURN fe.full_name, ep.route, be.full_name"
    )
    assert len(result) >= 1


def test_feature_disabled_no_endpoints(http_service, tmp_path) -> None:
    """When experimental flag is off, no endpoints should be created."""
    config_dir = tmp_path / ".synapse"
    config_dir.mkdir()
    (config_dir / "config.json").write_text(json.dumps({"port": 7687}))

    backend = tmp_path / "Controller.cs"
    backend.write_text('''
[ApiController]
[Route("api/test")]
public class TestController : ControllerBase {
    [HttpGet]
    public IActionResult Get() { return Ok(); }
}
''')

    from synapse.graph.connection import GraphConnection
    from synapse.graph.schema import ensure_schema
    from synapse.service import SynapseService

    conn = GraphConnection.create(database="memgraph")
    ensure_schema(conn)
    svc = SynapseService(conn=conn)
    svc.index_project(str(tmp_path), "csharp")

    result = svc.execute_query(
        "MATCH (r:Repository {path: $path})-[:CONTAINS]->(ep:Endpoint) RETURN count(ep) as cnt"
    )
    # execute_query doesn't support parameters, so use the conn directly
    raw = conn.query(
        "MATCH (r:Repository {path: $path})-[:CONTAINS]->(ep:Endpoint) RETURN count(ep)",
        {"path": str(tmp_path)},
    )
    assert raw[0][0] == 0

    # Cleanup
    conn.execute("MATCH (r:Repository {path: $path})-[:CONTAINS*]->(n) DETACH DELETE n", {"path": str(tmp_path)})
    conn.execute("MATCH (r:Repository {path: $path}) DELETE r", {"path": str(tmp_path)})
```

- [ ] **Step 4: Run the integration test (requires Memgraph)**

Run: `cd /Users/alex/Dev/synapse && source .venv/bin/activate && docker compose up -d && pytest tests/integration/test_http_endpoints.py -v -m integration`
Expected: Adjust test details based on actual fixture behavior; iterate until PASS

- [ ] **Step 5: Commit**

```bash
git add tests/fixtures/http_test_project/ tests/integration/conftest.py tests/integration/test_http_endpoints.py
git commit -m "test(http): add integration tests for HTTP endpoint extraction"
```

---

### Task 12: Update Graph Schema Documentation

**Files:**
- Modify: `src/synapse/mcp/tools.py` (if `get_schema` is hardcoded — add Endpoint to schema output)

- [ ] **Step 1: Check how `get_schema` returns schema info**

Read `src/synapse/mcp/tools.py` and find the `get_schema` tool implementation. If the schema is dynamically derived from the graph, no change needed. If it's hardcoded, add the `Endpoint` node label and `SERVES`/`HTTP_CALLS` relationship types.

- [ ] **Step 2: Update schema output if needed**

Add to node_labels:
```python
"Endpoint": ["route", "http_method", "name"]
```

Add to relationship_types:
```python
"SERVES": "Method → Endpoint (controller method handles this HTTP endpoint)",
"HTTP_CALLS": "Method → Endpoint (frontend method makes HTTP request to this endpoint)",
```

Add to notes:
```python
"Endpoint nodes and SERVES/HTTP_CALLS edges are experimental (requires experimental.http_endpoints in config).",
```

- [ ] **Step 3: Run all unit tests**

Run: `cd /Users/alex/Dev/synapse && source .venv/bin/activate && pytest tests/unit/ -v`
Expected: All PASS

- [ ] **Step 4: Commit**

```bash
git add src/synapse/mcp/tools.py
git commit -m "feat(http): add Endpoint/SERVES/HTTP_CALLS to graph schema output"
```

---

## Summary

| Task | What it delivers | Key files |
|------|-----------------|-----------|
| 1 | Core data types + protocol | `indexer/http/interface.py` |
| 2 | Route normalization | `indexer/http/route_utils.py` |
| 3 | Route matcher | `indexer/http/matcher.py` |
| 4 | Graph operations | `graph/nodes.py`, `graph/edges.py`, `graph/schema.py` |
| 5 | C# server extractor | `indexer/csharp/csharp_http_extractor.py` |
| 6 | TypeScript client extractor | `indexer/typescript/typescript_http_extractor.py` |
| 7 | Plugin wiring | `plugin/csharp.py`, `plugin/typescript.py` |
| 8 | Config flag | `config.py` |
| 9 | Indexer Phase 4 | `indexer/indexer.py`, `indexer/http_phase.py` |
| 9a | Sync-level re-matching | `indexer/http_phase.py`, `service.py` |
| 10 | MCP instructions | `mcp/instructions.py` |
| 11 | Integration tests | `tests/integration/test_http_endpoints.py` |
| 12 | Schema docs | `mcp/tools.py` |

**Dependency order:** Tasks 1-4 are foundational (must be first). Tasks 5-6 depend on 1-2. Task 7 depends on 5-6. Task 8 is independent. Task 9 depends on all prior tasks. Task 9a depends on 9. Tasks 10-12 depend on 9a.

**Known scope reductions from the spec** (intentional — incremental delivery):
- TypeScript server-side extraction (Express/Fastify/Hono) is deferred — this plan implements client-side only
- C# client-side extraction (`HttpClient.GetAsync`) is deferred
- Python server/client extractors (FastAPI, Flask, requests, httpx) are deferred
- Java server extractor (Spring) is deferred
- Tier 2 constant resolution is file-local only — one-hop import resolution is deferred
- The core pipeline (C# server + TypeScript client) covers the primary use case (oneonone-style projects) end-to-end

**Follow-up work (not in this plan):**
- Python server/client extractors (FastAPI, Flask, requests, httpx)
- Java server extractor (Spring)
- TypeScript server extractor (Express, Fastify, Hono)
- C# client extractor (HttpClient)
- Imported constant resolution (one-hop via IMPORTS edges)
- `find_entry_points` traversal across HTTP boundary
- `analyze_change_impact` incorporating HTTP edges
