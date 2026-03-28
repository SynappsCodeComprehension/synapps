# Distribution & Onboarding

## Problem

The gap between "heard about Synapps" and "my AI agent is using it" requires 5+ manual steps across different tools (pip, Docker, language servers, MCP config, first index). Each step is a drop-off point.

## Current State

| Step | Experience | Friction |
|------|-----------|----------|
| Install | `pip install -e .` from source | No PyPI package; requires git clone |
| Prerequisites | `synapps doctor` checks 8 dependencies | Reports problems but doesn't fix them |
| Container | Auto-provisions shared Memgraph via Docker | Docker must be installed and running; no guidance if it's not |
| Language servers | Manual install per language (.NET SDK, Pyright, ts-server, JDTLS) | No install commands provided; doctor only says "not found" |
| MCP config | Manual JSON edit in `claude_desktop_config.json` | Copy-paste from README; different per client (Claude, Cursor, Windsurf) |
| First index | `synapps index <path>` or auto on first MCP query | Works well once everything else is in place |

**`synapps doctor` output today:** Structured Rich table with pass/warn/fail per check. Includes version info and basic install hints, but hints are generic (e.g., "Install .NET SDK from microsoft.com") rather than platform-specific commands.

## Proposed Changes

### 1. Publish to PyPI

**Goal:** `pip install synapps-mcp` or `pipx install synapps-mcp`

**Work required:**
- Choose package name (check PyPI availability — `synapps` is taken, `synapps-mcp` or `synapps-code` likely available)
- Add PyPI publish workflow to `.github/workflows/` (triggered on git tag)
- Add `classifiers`, `project.urls`, and `long_description` to `pyproject.toml`
- Verify `solidlsp` bundling works correctly in wheel builds (it's a sub-package in `src/`)
- Add `__version__` attribute for runtime version checking

**Scope:** Small. Mostly CI/CD configuration.

### 2. `synapps init` Command

**Goal:** Single interactive command that takes a user from zero to working setup.

**Behavior:**
```
$ synapps init
Detecting project languages... C#, TypeScript found.

Checking prerequisites:
  Docker .............. OK (v27.5.1)
  Memgraph ........... starting shared container... OK (port 7687)
  .NET SDK ........... OK (v9.0.200)
  TypeScript LS ...... not found

  To install typescript-language-server:
    npm install -g typescript-language-server typescript

  Run `synapps init` again after installing, or continue without TypeScript support.

  [c]ontinue without TypeScript / [q]uit? c

Indexing project (482 files, 2 languages)... done (14.2s)
  3,241 symbols indexed
  12,847 relationships mapped

MCP configuration:
  Detected: Claude Code
  Add this to your MCP config? [Y/n] y
  Written to ~/.claude/settings.json

Ready. Your AI agent can now use Synapps tools.
```

**Design decisions:**
- Auto-detect languages from file extensions in project root
- Only check/install language servers for detected languages (not all 4)
- Offer platform-specific install commands (brew on macOS, apt on Ubuntu, winget on Windows)
- No auto-install of language servers (project constraint: "report + instructions only")
- Auto-detect MCP client (Claude Code, Claude Desktop, Cursor, Windsurf) and offer to write config
- Store completion state so re-running `synapps init` skips completed steps

**Scope:** Medium. New CLI command, platform detection logic, MCP client config generation.

### 3. Improved Error Recovery

**Goal:** Every error message tells the user what to do next.

**Current gaps and fixes:**

| Scenario | Current | Proposed |
|----------|---------|----------|
| Docker not running | `RuntimeError: Docker is not available` | `Docker is not running. Start it with: open -a Docker (macOS) / sudo systemctl start docker (Linux)` |
| Language server missing | `WARNING: pyright not found` | `Pyright not found. Install: pip install pyright \| Python symbols will be extracted via tree-sitter only (reduced accuracy)` |
| Memgraph connection lost | Raw `neo4j.exceptions.ServiceUnavailable` | `Lost connection to Memgraph. Check container: docker ps \| grep synapps \| Restart: synapps init` |
| Indexing timeout | `TimeoutError` from LSP | `Language server timed out processing <file>. This file may be too large or have circular imports. Skipping. Use --verbose for details.` |
| Project not indexed | Empty query results | `No symbols found. Index this project first: synapps index <path>` |

**Scope:** Small-medium. Wrap existing exception handlers with user-facing messages. No architectural changes.

### 4. Pre-built Docker Image (stretch goal)

**Goal:** Single-command evaluation without any local Python install.

```bash
docker run -v $(pwd):/workspace ghcr.io/SynappsCodeComprehension/synapps-mcp
```

**What it includes:** Python runtime, Synapps, Memgraph, all 4 language servers.

**Trade-offs:**
- Large image (~2-3 GB with all language servers)
- Memgraph inside same container vs. sidecar (simpler but less flexible)
- Stdio MCP transport works through Docker with `-i` flag
- Not suitable for production (all-in-one); useful for evaluation only

**Scope:** Medium. Dockerfile, multi-stage build, CI publish workflow. Consider whether this is worth the maintenance burden vs. just making pip install smoother.

## Suggested Execution Order

1. **PyPI publishing** — unblocks everything else; small scope
2. **Error recovery** — quick wins; improves experience for existing users immediately
3. **`synapps init`** — the big UX improvement; depends on error recovery patterns
4. **Docker image** — only if adoption data shows install friction persists after 1-3

## Success Metrics

- Time from `pip install` to first successful MCP query < 5 minutes
- `synapps doctor` pass rate on first run > 80% (currently unknown)
- Zero raw exception traces in normal error paths
