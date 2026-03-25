---
phase: 05-expand-http-endpoint-mapping-to-all-languages
plan: "03"
subsystem: indexer/java
tags: [java, http-extraction, spring, resttemplate, webclient, tree-sitter, tdd]
dependency_graph:
  requires:
    - src/synapse/indexer/http/interface.py
    - src/synapse/indexer/http/route_utils.py
    - src/synapse/indexer/tree_sitter_util.py
    - src/synapse/lsp/interface.py
  provides:
    - JavaHttpExtractor implementing HttpExtractor protocol
    - JavaPlugin.create_http_extractor() factory method
  affects:
    - src/synapse/plugin/java.py
    - tests/unit/plugin/test_http_extractor_wiring.py
tech_stack:
  added: []
  patterns:
    - TDD (RED-GREEN) for extractor implementation
    - Lazy-import factory pattern for plugin wiring
    - AST parent-chain traversal for WebClient/java.net.http builder chains
    - _method_invocation_name() helper to identify method name before argument_list in chained calls
key_files:
  created:
    - src/synapse/indexer/java/java_http_extractor.py
    - tests/unit/indexer/http/test_java_http_extractor.py
  modified:
    - src/synapse/plugin/java.py
    - tests/unit/plugin/test_http_extractor_wiring.py
decisions:
  - _method_invocation_name() scans backwards from argument_list to find the identifier immediately before it — handles both simple (foo.bar()) and chained (a.b().c()) method invocations where the first identifier child would be the receiver, not the method name
  - WebClient verb detected by inspecting the "object" field of the .uri() invocation (its receiver is .get()/.post()), not by walking up the parent chain
  - java.net.http verb detected by walking parent chain from URI.create() through argument_list to .uri() invocation and then up to the .GET()/.POST() invocation
  - test_java_plugin_no_http_extractor_yet renamed to test_java_plugin_has_http_extractor — the old test was a placeholder asserting Java extractor was not yet implemented; it inverted the correct post-implementation assertion
metrics:
  duration: "5 min"
  completed: "2026-03-25"
  tasks_completed: 2
  files_created: 2
  files_modified: 2
---

# Phase 05 Plan 03: Java HTTP Extractor Summary

**One-liner:** JavaHttpExtractor extracts Spring @XxxMapping SERVES edges and RestTemplate/WebClient/java.net.http HTTP_CALLS edges from Java AST using tree-sitter parent-chain traversal.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create JavaHttpExtractor with TDD tests | 9f3782f | src/synapse/indexer/java/java_http_extractor.py, tests/unit/indexer/http/test_java_http_extractor.py |
| 2 | Wire JavaPlugin.create_http_extractor() | c189bb0 | src/synapse/plugin/java.py, tests/unit/plugin/test_http_extractor_wiring.py |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated inverted placeholder test for JavaPlugin.create_http_extractor()**
- **Found during:** Task 2
- **Issue:** `test_java_plugin_no_http_extractor_yet` asserted `not hasattr(plugin, "create_http_extractor")` — a placeholder test written before the implementation existed. After adding the method it caused a regression.
- **Fix:** Renamed test to `test_java_plugin_has_http_extractor` and changed assertion to verify the extractor is returned (matching the pattern of C#, TypeScript, and Python plugin wiring tests).
- **Files modified:** tests/unit/plugin/test_http_extractor_wiring.py
- **Commit:** c189bb0

**2. [Rule 1 - Bug] Fixed _method_invocation_name() for chained builder calls**
- **Found during:** Task 1 GREEN phase debugging
- **Issue:** Initial implementation used `_find_child_text_by_type(node, "identifier")` to get the method name from a `method_invocation` node. For chained calls like `restTemplate.getForObject(...)`, the first identifier child is the receiver (`restTemplate`), not the method name (`getForObject`). This caused all RestTemplate/WebClient/java.net.http tests to return no results.
- **Fix:** Introduced `_method_invocation_name()` which scans backwards from the `argument_list` child to find the identifier immediately before it — always the method name regardless of chaining depth.
- **Files modified:** src/synapse/indexer/java/java_http_extractor.py
- **Commit:** 9f3782f (inline during GREEN phase)

## Known Stubs

None — all extraction patterns are wired and tested.

## Self-Check: PASSED

- src/synapse/indexer/java/java_http_extractor.py exists and contains `class JavaHttpExtractor`
- tests/unit/indexer/http/test_java_http_extractor.py exists with 19 test functions
- src/synapse/plugin/java.py contains `def create_http_extractor(self):`
- Commits 843273c (test RED), 9f3782f (impl GREEN), c189bb0 (plugin wiring) all present
- All 1294 unit tests pass
