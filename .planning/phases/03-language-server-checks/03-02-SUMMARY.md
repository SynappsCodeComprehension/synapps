---
phase: 03-language-server-checks
plan: "02"
subsystem: doctor
tags: [node, typescript-language-server, subprocess, shutil, binary-check, tdd]

# Dependency graph
requires:
  - phase: 03-language-server-checks/03-01
    provides: DotNetCheck pattern — standard binary subprocess check (shutil.which + subprocess.run + TimeoutExpired)
provides:
  - NodeCheck class implementing DoctorCheck protocol (src/synapse/doctor/checks/node.py)
  - TypeScriptLSCheck class implementing DoctorCheck protocol (src/synapse/doctor/checks/typescript_ls.py)
  - Unit tests covering all pass/fail/warn paths for both checks
affects:
  - 03-language-server-checks/03-04 (CLI integration registering TypeScript group checks)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Binary subprocess check: shutil.which -> subprocess.run(capture_output=True, timeout=10) -> returncode"
    - "Skip-if-runtime-absent guard: check runtime (node) before checking dependent tool (typescript-language-server)"
    - "warn (not fail) when prerequisite runtime is absent — degraded-but-working semantics"

key-files:
  created:
    - src/synapse/doctor/checks/node.py
    - src/synapse/doctor/checks/typescript_ls.py
    - tests/unit/doctor/test_typescript.py
  modified: []

key-decisions:
  - "TypeScriptLSCheck returns warn (not fail) when node is absent — consistent with D-05 degraded-but-working semantics; typescript-language-server cannot be meaningfully checked without node"
  - "Module-level _FIX constant for fix strings — avoids string duplication across multiple return sites"
  - "capture_output=True without text=True — returncode is the only signal; no string parsing needed"

patterns-established:
  - "Skip-if-runtime-absent: any language server check that depends on a runtime binary should return warn when runtime is absent, not fail"
  - "TimeoutExpired caught alongside FileNotFoundError — both indicate invocation failure"

requirements-completed:
  - LANG-03
  - LANG-04

# Metrics
duration: 8min
completed: 2026-03-23
---

# Phase 03 Plan 02: NodeCheck and TypeScriptLSCheck Summary

**NodeCheck (LANG-03) and TypeScriptLSCheck (LANG-04) using shutil.which + subprocess.run pattern, with TypeScriptLSCheck returning warn instead of fail when node is absent**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-03-23T22:21:00Z
- **Completed:** 2026-03-23T22:29:53Z
- **Tasks:** 2
- **Files modified:** 3 (2 created implementations + 1 test file)

## Accomplishments

- NodeCheck returns pass with binary path in detail when `node --version` exits 0; returns fail with nodejs.org fix URL when node not on PATH; catches TimeoutExpired
- TypeScriptLSCheck implements skip-if-runtime-absent pattern: returns warn with no fix when node is absent, fail with npm install fix when typescript-language-server is absent, pass when both present and version exits 0
- 12 unit tests covering all pass/fail/warn paths for both checks (TDD RED->GREEN)

## Task Commits

Each task was committed atomically:

1. **Task 1: NodeCheck with TDD (LANG-03)** - `d971584` (feat)
2. **Task 2: TypeScriptLSCheck with TDD (LANG-04)** - `2d80129` (feat)

_Note: TDD tasks compressed to single commits (RED test file written then implementation added before commit) due to import-error RED phase being unambiguous._

## Files Created/Modified

- `src/synapse/doctor/checks/node.py` - NodeCheck implementing DoctorCheck protocol via standard binary subprocess check pattern
- `src/synapse/doctor/checks/typescript_ls.py` - TypeScriptLSCheck with skip-if-runtime-absent guard for node, then checks typescript-language-server binary
- `tests/unit/doctor/test_typescript.py` - 12 unit tests: 6 for NodeCheck + 6 for TypeScriptLSCheck covering pass/fail/warn/timeout/nonzero-exit paths

## Decisions Made

- TypeScriptLSCheck returns warn (not fail) when node is absent — matches D-05 degraded-but-working semantics established in Phase 02; typescript-language-server is meaningless to check without a working node runtime
- Module-level `_FIX` constant holds fix strings to avoid duplication across multiple return sites
- `capture_output=True` without `text=True` — returncode is the only signal for both checks; no stdout/stderr parsing needed (consistent with all other binary checks)

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

Pre-existing issue (out of scope): `tests/unit/doctor/test_python.py` (committed in `027efb3`) imports `synapse.doctor.checks.pylsp` which does not exist. This causes a collection error when running `pytest tests/unit/ -v` without `--ignore`. This is unrelated to plan 03-02 (it predates our commits). The full unit suite runs clean with `--ignore=tests/unit/doctor/test_python.py` (1141 passed). This should be resolved when plan 03-03 creates `pylsp.py`, or the test file was committed prematurely.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- NodeCheck and TypeScriptLSCheck are ready for integration into the doctor service registry (plan 03-04)
- Both follow the same DoctorCheck protocol and group = "typescript" — they will be discovered together by the CLI and MCP doctor commands
- Pre-existing test_python.py import error for pylsp must be resolved (plan 03-03 or equivalent) before full `pytest tests/unit/` runs clean

---
*Phase: 03-language-server-checks*
*Completed: 2026-03-23*
