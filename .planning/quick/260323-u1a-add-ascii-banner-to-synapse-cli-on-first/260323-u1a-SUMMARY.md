---
phase: quick
plan: 260323-u1a
subsystem: cli
tags: [rich, ascii-art, banner, typer]

requires:
  - phase: none
    provides: standalone quick task
provides:
  - print_banner() function in synapse.cli.banner module
  - First-run banner display on initial project index
affects: []

tech-stack:
  added: []
  patterns: [DI-friendly banner function with optional Console injection]

key-files:
  created:
    - src/synapse/cli/banner.py
    - tests/unit/test_banner.py
  modified:
    - src/synapse/cli/app.py
    - tests/unit/test_cli.py

key-decisions:
  - "print_banner accepts optional Console parameter for DI/testability (CLAUDE.md requirement)"
  - "Module-level import of print_banner in app.py for patchable test targets (consistent with existing check import pattern)"
  - "Banner fires before smart_index, gated on get_index_status returning None"

patterns-established:
  - "DI Console injection: print_banner(console=None) pattern for testable rich output"

requirements-completed: [QUICK-BANNER]

duration: 3min
completed: 2026-03-24
---

# Quick Plan 260323-u1a: Add ASCII Banner to Synapse CLI Summary

**B2 block-letter "SYNAPSE" banner with alternating dark/light green, displayed once on first project index via get_index_status gate**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-24T01:40:12Z
- **Completed:** 2026-03-24T01:44:01Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Created banner.py with B2-style block-letter "SYNAPSE" in alternating #2D6A4F/#74C69D green
- Circle-dash accent line renders below the banner text
- Banner only displays on first-ever index (get_index_status returns None), not on re-index
- 10 new tests (7 banner + 3 CLI wiring), all 1167 unit tests pass

## Task Commits

Each task was committed atomically (TDD: RED then GREEN):

1. **Task 1: Create banner.py with print_banner() and unit tests**
   - `e8afae3` (test) — failing tests for print_banner
   - `3e2d7b4` (feat) — implement print_banner with B2 block letters
2. **Task 2: Wire banner into CLI index command with first-index detection**
   - `c648ce2` (test) — failing tests for banner wiring in index command
   - `b69489b` (feat) — wire banner into CLI index command

## Files Created/Modified
- `src/synapse/cli/banner.py` — print_banner() with B2 block-letter art and rich markup
- `tests/unit/test_banner.py` — 7 tests covering text content, colors, accent line, DI
- `src/synapse/cli/app.py` — import print_banner, gate on get_index_status in index command
- `tests/unit/test_cli.py` — 3 tests for first-run banner, re-index skip, end-to-end

## Decisions Made
- print_banner() accepts an optional `Console` parameter for dependency injection and testability, per CLAUDE.md
- Module-level import of print_banner in app.py (not lazy) — consistent with existing pattern for all check classes, required for patch() targets in tests
- Banner fires based on `svc.get_index_status(abs_path) is None` — no Repository node means first-ever index

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Known Stubs
None - all functionality is fully wired.

## Next Phase Readiness
- Banner module is self-contained and ready for future customization (version display, taglines)
- No blockers

## Self-Check: PASSED

All 4 files found. All 4 commits verified.

---
*Plan: quick-260323-u1a*
*Completed: 2026-03-24*
