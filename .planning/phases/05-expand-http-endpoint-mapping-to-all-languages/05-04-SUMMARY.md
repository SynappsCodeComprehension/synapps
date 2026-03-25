---
phase: "05"
plan: "04"
subsystem: indexer/csharp
tags: [http, csharp, extraction, client-calls, httpclient, restsharp]
dependency_graph:
  requires: []
  provides: [HTTP_CALLS edges for C# HttpClient and RestSharp calls]
  affects: [csharp_http_extractor, http_extraction_pipeline]
tech_stack:
  added: []
  patterns: [enclosing-symbol lookup via sorted symbol ranges, interpolated string normalization]
key_files:
  created: []
  modified:
    - src/synapse/indexer/csharp/csharp_http_extractor.py
    - tests/unit/indexer/http/test_csharp_http_extractor.py
decisions:
  - "_HTTPCLIENT_VERB_MAP and _RESTSHARP_METHOD_MAP as module-level dicts — mirrors existing _HTTP_VERB_MAP pattern and aligns with D-07"
  - "SendAsync skipped — method is specified in HttpRequestMessage, not the call site; too complex for static analysis"
  - "enclosing-symbol lookup reuses sorted-range pattern from TypeScript extractor (mirrors _find_enclosing_symbol)"
  - "interpolated_string_expression uses string_content child for literal parts and replaces interpolation nodes with {param}"
metrics:
  duration: "3 minutes"
  completed_date: "2026-03-25"
  tasks: 1
  files: 2
---

# Phase 05 Plan 04: C# Client-Side HTTP Extraction Summary

**One-liner:** Added HttpClient and RestSharp HTTP_CALLS extraction to CSharpHttpExtractor using tree-sitter invocation and object_creation nodes, with C# interpolated string normalization.

## What Was Built

Extended `CSharpHttpExtractor` to detect client-side HTTP calls in C# code:

- **HttpClient verb map** (`_HTTPCLIENT_VERB_MAP`): GetAsync/GetStringAsync/GetByteArrayAsync → GET, PostAsync → POST, PutAsync → PUT, DeleteAsync → DELETE, PatchAsync → PATCH
- **RestSharp method map** (`_RESTSHARP_METHOD_MAP`): new RestRequest("/route", Method.Get) pattern → GET/POST/PUT/DELETE/PATCH
- **Interpolated string normalization**: `$"/api/items/{id}"` → `/api/items/{param}` by treating `interpolation` tree-sitter nodes as `{param}` placeholders
- **Enclosing method lookup**: same sorted-range pattern as TypeScript extractor — `(start_line_0, end_line_0, full_name)` list
- **URL false positive filter**: routes without `/` are rejected (avoids capturing map.get("key") style calls)
- **Backward-compatible**: existing ASP.NET controller SERVES extraction unchanged; same file can produce both endpoint_defs and client_calls

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 (RED) | Failing tests for C# client-side extraction | 34cdbfe | tests/unit/indexer/http/test_csharp_http_extractor.py |
| 1 (GREEN) | Implement HttpClient + RestSharp extraction | 3fc6eb4 | src/synapse/indexer/csharp/csharp_http_extractor.py |

## Verification

- `pytest tests/unit/indexer/http/test_csharp_http_extractor.py -v` — 22/22 passed (10 existing server + 12 new client)
- `pytest tests/unit/ --tb=short` — 1286 passed, 8 failed (all 8 failures are pre-existing in Java/Python HTTP extractors being built in parallel plans 05-03/05-05)

## Deviations from Plan

None — plan executed exactly as written. TDD RED/GREEN protocol followed strictly. No REFACTOR phase needed (code is clean and minimal).

## Pre-existing Failures (Out of Scope)

The following 8 test failures were pre-existing before this plan and are not caused by these changes:

- 7 failures in `tests/unit/indexer/http/test_java_http_extractor.py` (Java HTTP extraction — plan 05-03, in-progress)
- 1 failure in `tests/unit/indexer/http/test_python_http_extractor.py::test_requests_fstring_url` (Python f-string extraction)

These are tracked by their respective plans and deferred per scope boundary rules.

## Known Stubs

None — all extraction paths produce real data from tree-sitter AST nodes.

## Self-Check: PASSED
