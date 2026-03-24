# HTTP Endpoint Extraction Design

**Date**: 2026-03-23
**Status**: Approved
**Feature flag**: `experimental.http_endpoints` (off by default)

## Problem

AI coding agents working in multi-language projects (e.g., C# backend + TypeScript/React frontend) cannot trace calls across the HTTP boundary. When modifying a backend controller action, the agent has no way to discover which frontend code calls it, and vice versa. This forces agents to grep for URL strings manually, which is unreliable and incomplete.

## Solution

Add an experimental feature to Synapse that extracts HTTP endpoint definitions (server-side) and HTTP client calls (client-side) from source code using tree-sitter, matches them by route pattern, and represents the relationships in the graph. This enables bidirectional tracing between frontend and backend across the HTTP boundary.

## Graph Model

### New Node: `Endpoint`

| Property | Type | Example | Description |
|----------|------|---------|-------------|
| `route` | string | `/api/action-items/{id}` | Normalized route pattern (always starts with `/`) |
| `http_method` | string | `GET` | HTTP verb (uppercase) |
| `name` | string | `GET /api/action-items/{id}` | Human-readable identifier |

### New Edges

| Edge | From | To | Properties | Meaning |
|------|------|----|------------|---------|
| `SERVES` | Method | Endpoint | -- | Controller method handles this endpoint |
| `HTTP_CALLS` | Method | Endpoint | `call_sites: [[line, col], ...]` | Frontend method makes HTTP request to this endpoint |

### Containment

`Repository -[:CONTAINS]-> Endpoint` -- endpoints belong to the project.

### Key Properties

- `SERVES` is expected to be 1:1 (one controller method per verb+route combination), but this is not enforced by the graph. Multiple `SERVES` edges on one `Endpoint` indicate a route conflict in the application code.
- `HTTP_CALLS` is many:1 (multiple frontend methods can call the same endpoint)
- An `Endpoint` with `SERVES` but no `HTTP_CALLS` = unused backend endpoint
- An `Endpoint` with `HTTP_CALLS` but no `SERVES` = external API call or missing backend route

### Graph Index

Add `("Endpoint", "route")` to `_INDEX_DEFS` in `schema.py` to ensure `MERGE` operations on `Endpoint` nodes do not require full label scans.

## Extraction Protocol

### Plugin Integration

The `create_http_extractor` method is **not** added to the `LanguagePlugin` protocol definition. Instead, it follows the same optional-method pattern used by `create_assignment_extractor`:

```python
# In the indexer, not on the Protocol:
self._http_extractor_factory = getattr(plugin, 'create_http_extractor', None)
```

Plugins that support HTTP extraction implement the method; those that don't simply lack it. This avoids a breaking change to the protocol and maintains backward compatibility.

### HttpExtractor Protocol

```python
class HttpExtractor(Protocol):
    def extract(
        self,
        file_path: str,
        tree: Tree,
        symbols: list[IndexSymbol],
    ) -> HttpExtractionResult: ...
```

The `symbols` parameter is the list of `IndexSymbol`s for the file (from the structural phase), used to resolve handler method full names for server-side endpoints.

### Common Data Types

```python
@dataclass
class HttpEndpointDef:
    route: str              # "/api/action-items/{id}"
    http_method: str        # "GET"
    handler_full_name: str  # "ActionItemsController.GetActionItemById"
    line: int

@dataclass
class HttpClientCall:
    route: str              # "/action-items/{id}"
    http_method: str        # "GET"
    caller_full_name: str   # "actionItemService.getActionItemById"
    line: int
    col: int

@dataclass
class HttpExtractionResult:
    endpoint_defs: list[HttpEndpointDef]    # server-side
    client_calls: list[HttpClientCall]      # client-side
```

A single extractor per language returns both sides. A language like TypeScript might contribute both (Express backend + React frontend). The protocol does not assume which role a language plays.

## Server-Side Extraction

Each language extractor detects framework-specific route declaration patterns using tree-sitter (no LSP):

| Language | Framework Patterns | Route Source |
|----------|-------------------|--------------|
| C# | `[ApiController]` + `[Route("...")]` + `[HttpGet("...")]` | Attribute arguments (tree-sitter string literals) |
| Python | `@app.route("/...")`, `@router.get("/...")` (Flask, FastAPI) | Decorator arguments |
| TypeScript/JS | `app.get("/...", handler)`, `router.post("/...")` (Express, Fastify, Hono) | First string argument to chained method calls |
| Java | `@GetMapping("/...")`, `@RequestMapping(path="...")` (Spring) | Annotation arguments |

### Route Normalization (shared across all languages)

- Strip type constraints: `{id:guid}` -> `{id}`, `{id:int}` -> `{id}`
- Strip regex constraints: `{slug:[a-z]+}` -> `{slug}`
- Ensure leading `/`
- Strip trailing `/`
- Collapse `//` -> `/`
- Preserve path case (routes are case-sensitive in most frameworks)

## Client-Side Extraction

### Detection Strategy

Identify calls to known HTTP client patterns and extract the URL path + HTTP method from call arguments.

| Language | Patterns | HTTP Method Source | URL Source |
|----------|----------|-------------------|------------|
| TypeScript/JS | `api.get("/...")`, `axios.post("/...")`, `fetch("/...")`, `HttpClient.get("/...")` | Method name or `method` property in options object | First string argument or template literal |
| C# | `HttpClient.GetAsync("/...")`, `HttpClient.PostAsync("/...")` | Method name (`GetAsync` -> GET) | First string argument |
| Python | `requests.get("/...")`, `httpx.post("/...")`, `session.get("/...")` | Method name | First string argument |
| Java | `RestTemplate.getForObject("/...")`, `WebClient.get().uri("/...")` | Method name or builder method | String argument |

### URL Resolution Tiers

**Tier 1 -- Inline strings:**
- `api.get('/action-items')` -> `/action-items`
- `` api.get(`/action-items/${id}`) `` -> `/action-items/{id}`

**Tier 2 -- Constant references:**
- `api.get(ACTION_ITEMS_ENDPOINT)` where `const ACTION_ITEMS_ENDPOINT = '/action-items'`
- Resolution: file-local constant assignments first, then one-hop import resolution
- Applies across languages: Python module-level assignments, C# `const`/`static readonly`, Java `static final`, TypeScript `const`/`export const`

**Tier 3 -- String concatenation/template literals:**
- `api.get('/action-items/' + id)` -> `/action-items/{param}`
- `` api.get(`${BASE}/action-items`) `` where `BASE` is a resolvable constant -> resolve and substitute

### What Gets Skipped

- Fully dynamic URLs: `api.get(buildUrl(resource))` -- no string literal to extract
- Computed constants: `const URL = getConfig().apiPath` -- not a string literal assignment
- Multi-hop indirection: constant assigned from another non-literal constant

### False Positive Prevention

When detecting `something.get("/path")` style calls, the first argument must look like a URL path (starts with `/` or contains `/`) to avoid false positives from `map.get("key")` or `cache.delete("token")`.

## Matching Phase

### Algorithm

1. Collect all `HttpEndpointDef`s across all languages -> server-side pool
2. Collect all `HttpClientCall`s across all languages -> client-side pool
3. For each client call, find the best matching server endpoint

### Route Matching Rules

Routes are compared segment-by-segment after splitting on `/`:

| Comparison | Result |
|---|---|
| Literal = Literal | Match if identical |
| `{param}` = `{param}` | Always matches (parameter names ignored) |
| `{param}` = Literal | No match (see Known Limitations) |

### Base Path Prefix Handling

Frontend clients often use a configured base URL (e.g., Axios `baseURL: '/api'`), so client routes may omit the prefix present in server routes. Matching strategy: try as-is first, then prepend common API prefixes (`/api`, `/api/v1`, `/api/v2`) to client routes. Projects with non-standard prefixes (e.g., `/services/api/`) will have unmatched client calls until configurable prefixes are added (see Future Enhancements).

### Graph Writes

For each matched pair:
1. `MERGE` an `Endpoint` node with `route` + `http_method` as composite key
2. `MERGE` a `SERVES` edge from handler method to Endpoint
3. `MERGE` an `HTTP_CALLS` edge from caller method to Endpoint (with `call_sites`)

Unmatched server endpoints: create `Endpoint` + `SERVES` (no client consumer yet).
Unmatched client calls: create `Endpoint` + `HTTP_CALLS` (external API or missing backend route).

## Indexer Integration

### Pipeline Position

```
Phase 1: Structural (symbols, types)         -- existing
Phase 2: Call resolution (CALLS edges)        -- existing
Phase 3: Attributes                           -- existing
Phase 4: HTTP endpoint extraction + matching  -- NEW
```

Phase 4 iterates the parsed tree cache (already available from earlier phases), calls each language's `http_extractor.extract(file_path, tree, symbols)`, collects all results, runs the matcher, and writes to the graph. Pure tree-sitter, no LSP.

### Sync Behavior

On `sync_project`, changed files get re-extracted. The matcher re-runs for the full project since a backend route change could affect frontend matches and vice versa.

**Edge cleanup:** `SERVES` and `HTTP_CALLS` must be added to the edge type list in `delete_outgoing_edges_for_file` (in `edges.py`) so that stale HTTP edges are removed when files change.

**Data source for matching during sync:** For changed files, extraction runs on the newly parsed trees. For unchanged files, the existing `Endpoint` nodes and their `SERVES`/`HTTP_CALLS` edges are queried from the graph to reconstruct the endpoint/client-call pools. The matcher then runs across the merged set.

**Orphan cleanup:** After the matching phase completes, delete any `Endpoint` nodes that have neither `SERVES` nor `HTTP_CALLS` edges (these are leftovers from removed routes).

## Experimental Status

### Opt-In Configuration

Off by default. Enabled in `.synapse/config.json`:

```json
{
  "experimental": {
    "http_endpoints": true
  }
}
```

When disabled, Phase 4 is skipped entirely -- zero overhead.

### User Communication

**Indexer log on activation:**
```
[EXPERIMENTAL] HTTP endpoint extraction is enabled. This feature is experimental
and may produce incomplete or incorrect endpoint mappings.
Disable with "experimental.http_endpoints": false in .synapse/config.json
```

**CLI output:**
```
[EXPERIMENTAL] HTTP endpoints: 12 server endpoints, 9 client calls, 8 matched
```

**MCP tool responses:** When query results include `Endpoint` nodes or `HTTP_CALLS`/`SERVES` edges, include a brief note: `Note: HTTP endpoint data is experimental and may be incomplete.`

### No New MCP Tools Initially

Endpoints are queryable through existing tools (`find_callers`, `find_usages`, `get_context_for`, `execute_query`). Dedicated tools can be added once the feature stabilizes.

## Query Patterns

### Bidirectional Tracing

Backend -> frontend ("what frontend code calls this controller method?"):
```cypher
MATCH (m:Method {full_name: $method})-[:SERVES]->(ep:Endpoint)<-[:HTTP_CALLS]-(caller:Method)
RETURN caller.full_name, ep.route, ep.http_method, caller.file_path, caller.line
```

Frontend -> backend ("what backend handler does this service method hit?"):
```cypher
MATCH (m:Method {full_name: $method})-[:HTTP_CALLS]->(ep:Endpoint)<-[:SERVES]-(handler:Method)
RETURN handler.full_name, ep.route, ep.http_method, handler.file_path, handler.line
```

### Full Stack Trace

```cypher
MATCH (fe:Method)-[:HTTP_CALLS]->(ep:Endpoint)<-[:SERVES]-(ctrl:Method),
      p = (ctrl)-[:CALLS*1..4]->(svc:Method)
WHERE fe.full_name = $frontend_method
RETURN ep.route, ctrl.full_name, [n IN nodes(p) | n.full_name]
```

### Discovery

All endpoints in a project:
```cypher
MATCH (r:Repository {path: $path})-[:CONTAINS]->(ep:Endpoint)
OPTIONAL MATCH (handler:Method)-[:SERVES]->(ep)
OPTIONAL MATCH (caller:Method)-[:HTTP_CALLS]->(ep)
RETURN ep.route, ep.http_method, handler.full_name, collect(caller.full_name)
```

Unused backend endpoints (no frontend consumer):
```cypher
MATCH (handler:Method)-[:SERVES]->(ep:Endpoint)
WHERE NOT ()-[:HTTP_CALLS]->(ep)
RETURN ep.route, ep.http_method, handler.full_name
```

Frontend calls to external APIs (no backend handler):
```cypher
MATCH (caller:Method)-[:HTTP_CALLS]->(ep:Endpoint)
WHERE NOT ()-[:SERVES]->(ep)
RETURN ep.route, ep.http_method, caller.full_name
```

## Testing Strategy

### Unit Tests (per extractor, tree-sitter only)

**Server-side extraction:**
- Basic controller with class-level route + method-level HTTP verbs
- Route parameter normalization (`{id:guid}` -> `{id}`)
- Route override with `~` prefix (C#) or absolute path
- Controller without framework marker -> skipped
- Multiple HTTP verbs on one method -> multiple endpoint defs
- Non-controller classes -> skipped
- Framework-specific patterns per language

**Client-side extraction:**
- String literal URL extraction with HTTP method detection
- Template literal with interpolation -> parameterized route
- Constant reference resolution (file-local)
- Imported constant resolution (one-hop)
- Dynamic URL (no string literal) -> skipped
- `fetch()` with method in options object
- False positive rejection (`map.get("key")` where arg is not path-like)

**Matching:**
- Exact route match (same path, same verb)
- Parameterized route match (`{id}` on both sides)
- Base path prefix matching (client `/items` matches server `/api/items`)
- No match -> unmatched endpoint and client call both still created
- Multiple client calls to same endpoint -> one Endpoint node, multiple HTTP_CALLS edges

### Integration Tests (require Memgraph)

- Index a test fixture project with backend controller and frontend service
- Verify Endpoint nodes, SERVES edges, and HTTP_CALLS edges created
- Verify bidirectional Cypher queries return expected results
- Verify `sync_project` correctly updates endpoints on route change
- Verify feature skipped when `experimental.http_endpoints` is false

## Scope

### Initial Implementation

- C#: ASP.NET Core (attributes)
- TypeScript/JS: Express-style (server) + Axios/fetch (client)
- Python: FastAPI + Flask (server) + requests/httpx (client)
- Java: Spring (server)

Each language extractor is independent and can ship incrementally.

### Known Limitations

- **Hardcoded literal paths vs parameterized server routes:** A client call like `api.get('/items/123')` (where `123` is an inline literal, not an interpolated variable) will not match a server route `/items/{id}`. Only interpolated/dynamic segments become `{param}` on the client side. This is an acceptable limitation — hardcoded IDs in client code are uncommon in practice.
- **Non-standard API prefixes:** The prefix fallback list (`/api`, `/api/v1`, `/api/v2`) is hardcoded. Projects using other prefixes will have unmatched client calls.
- **Dynamic/computed URLs:** URLs constructed via function calls or complex expressions are skipped entirely.
- **Constant resolution depth:** Only file-local and one-hop imported constants are resolved. Multi-hop or re-exported constants are not followed.

### Future Enhancements (out of scope)

- Cross-project endpoint matching
- Dedicated MCP tools for HTTP queries
- `find_entry_points` traversal across HTTP boundary
- `analyze_change_impact` incorporating HTTP edges
- Generated API client support (OpenAPI codegen, tRPC)
- Configurable base path prefixes
