# HTTP Endpoint Tracing: Complete or Drop

## Problem

HTTP endpoint tracing is half-built. It covers C# server-side (ASP.NET controllers) and TypeScript client-side (axios/fetch), but has no MCP tool exposure, no Java/Python coverage, and is gated behind an experimental config flag. This creates three risks:

1. Users discover the feature, try it with unsupported languages, and lose trust
2. The experimental code accrues maintenance cost without delivering value
3. Competitors who ship full cross-language HTTP tracing will own this differentiator

## Current State

### What Exists

**Server-side extraction (SERVES edges):**
| Language | Framework | Status | Extractor |
|----------|-----------|--------|-----------|
| C# | ASP.NET (`[HttpGet]`, `[Route]`) | Working | `CSharpHttpEndpointExtractor` |
| TypeScript | Express, NestJS | Working | `TypeScriptHttpEndpointExtractor` |
| Python | Flask, Django | Working | `PythonHttpEndpointExtractor` |
| Java | Spring Boot (`@RequestMapping`) | Working | `JavaHttpEndpointExtractor` |

**Client-side extraction (HTTP_CALLS edges):**
| Language | Libraries | Status | Extractor |
|----------|-----------|--------|-----------|
| TypeScript | axios, fetch, template literals | Working | `TypeScriptHttpClientExtractor` |
| Python | requests, httpx, urllib | Working | `PythonHttpClientExtractor` |
| C# | HttpClient | Not implemented |  |
| Java | RestTemplate, WebClient, HttpClient | Not implemented |  |

**Route matching (SERVES <-> HTTP_CALLS resolution):**
- Pattern-based matching in `HttpRouteResolver`
- Handles path parameters (`/api/users/{id}` matches `/api/users/${userId}`)
- Base URL prefix stripping
- No query parameter matching

**Configuration:**
```json
// .synapps/config.json
{
  "experimental": {
    "http_endpoints": true
  }
}
```

**Graph model:**
- `(:Method)-[:SERVES]->(:HttpEndpoint {method: "GET", route: "/api/users/{id}"})`
- `(:Method)-[:HTTP_CALLS]->(:HttpEndpoint {method: "GET", route: "/api/users/{id}"})`
- Cross-language resolution: `(:Method)-[:HTTP_CALLS]->(:HttpEndpoint)<-[:SERVES]-(:Method)`

### What's Missing

1. **No MCP tool** — agents must use raw Cypher to query HTTP relationships
2. **No C#/Java client extraction** — only half the cross-language story
3. **No route conflict detection** — multiple methods serving the same route isn't flagged
4. **No test coverage in CI** — integration tests exist locally but aren't in the GitHub Actions pipeline
5. **No documentation** — README mentions it in one line; no usage examples
6. **Still behind experimental flag** — users must know to enable it

## Decision Framework

### Option A: Complete It

**Scope:**
1. Add C# `HttpClient` client-side extractor
2. Add Java `RestTemplate`/`WebClient` client-side extractor
3. Create dedicated MCP tool: `find_http_endpoints` and `trace_http_dependency`
4. Remove experimental flag (make it always-on for detected web projects)
5. Add to README with examples
6. Add route conflict detection as a warning during indexing

**Effort:** ~2-3 phases of work (medium-large)

**Value proposition:**
- Unique differentiator — no other code intelligence tool traces HTTP dependencies across language boundaries
- High value for microservice architectures where services communicate via HTTP
- Completes the "understand what happens if I change this endpoint" story
- Natural extension of existing call graph / impact analysis tools

**Risks:**
- Route matching is inherently fuzzy (dynamic routes, middleware rewrites, API gateways)
- Client-side extraction relies on static analysis of HTTP calls — dynamic URL construction will be missed
- Maintenance burden: 8 extractors (4 server + 4 client) across 4 languages

### Option B: Ship What Works, Document Limits

**Scope:**
1. Create MCP tool for existing HTTP data
2. Remove experimental flag
3. Document clearly: "Server-side extraction for all 4 languages. Client-side extraction for TypeScript and Python. C# and Java client-side planned."
4. Defer C#/Java client extractors to a future milestone

**Effort:** ~1 phase (small-medium)

**Value proposition:**
- Ships value now instead of blocking on completeness
- Server-side extraction alone is useful (find all endpoints in a service, detect route conflicts)
- TypeScript + Python client coverage handles the most common API consumer patterns (React/Next.js frontends, Python scripts/services)
- Honest documentation prevents trust erosion

**Risks:**
- Incomplete story may not be compelling enough to highlight as a feature
- Users with C#/Java API clients won't get cross-language tracing

### Option C: Drop It

**Scope:**
1. Remove all HTTP endpoint extraction code
2. Remove `HttpEndpoint` node type from graph schema
3. Remove experimental config flag
4. Remove from README

**Effort:** ~1 phase (small)

**Value proposition:**
- Eliminates maintenance burden for 8+ extractors
- Simplifies the graph model
- Focuses the product on its core strength (code-level call graphs, not network-level dependencies)

**Risks:**
- Loses a genuine differentiator
- Discards significant completed work
- Cross-language HTTP tracing is a real user need in microservice architectures

## Recommendation

**Option B: Ship what works, document limits.**

Rationale:
- The server-side extraction is done for all 4 languages — that's a complete, useful feature on its own
- TypeScript + Python client-side covers the most common consumer patterns
- An MCP tool exposing HTTP endpoints is a quick win (~1 tool, leveraging existing graph data)
- Honest documentation ("client-side for TS/Python, server-side for all 4") is better than either hiding the feature or overpromising
- C#/Java client extractors can follow in a later milestone driven by user demand

### Concrete deliverables for Option B:

1. **MCP tools** (2 new tools):
   - `find_http_endpoints(route_pattern?, method?, language?)` — search endpoints by route, HTTP method, or language
   - `trace_http_dependency(endpoint_route, method?)` — given an endpoint, find server handler + all client call sites

2. **Remove experimental gate** — enable by default; index HTTP endpoints whenever web framework patterns are detected

3. **Documentation** — README section with:
   - Supported frameworks table (server + client)
   - Example queries
   - Known limitations (dynamic routes, middleware, API gateways)

4. **Route conflict warning** — during indexing, log a warning when multiple methods serve the same `(method, route)` pair

## Appendix: Supported Framework Detection

For auto-enabling HTTP extraction (replacing experimental flag):

| Language | Detect via | Trigger |
|----------|-----------|---------|
| C# | `.csproj` references | `Microsoft.AspNetCore` namespace |
| TypeScript | `package.json` deps | `express`, `@nestjs/core`, `axios`, `next` |
| Python | `requirements.txt` / `pyproject.toml` | `flask`, `django`, `fastapi`, `requests`, `httpx` |
| Java | `pom.xml` / `build.gradle` | `spring-boot-starter-web` |
