"""Install / update Synapps instruction sections in per-agent config files.

Each agent has its own file format:
- CLAUDE.md        — Claude Code (markdown with HTML markers)
- AGENTS.md        — Generic agents (markdown with HTML markers)
- .cursor/rules/synapps.mdc — Cursor (standalone MDC rule file)
- .github/copilot-instructions.md — GitHub Copilot (markdown with HTML markers)

Markdown files use <!-- synapps:start --> / <!-- synapps:end --> markers so
the Synapps section can be upserted without clobbering user content.  The
Cursor MDC file is fully owned by Synapps (the entire file is replaced).
"""
from __future__ import annotations

import logging
import re
from pathlib import Path

log = logging.getLogger(__name__)

_MD_START = "<!-- synapps:start -->"
_MD_END = "<!-- synapps:end -->"

# ── Shared content ───────────────────────────────────────────────────

_SYNAPPS_BODY = """\
This project is indexed by the **Synapps** code-intelligence graph.
Use Synapps MCP tools instead of grep or file reads for understanding code structure, \
relationships, and navigating symbols.

### Workflow
- Projects must be indexed before querying. Call `list_projects` to check what is indexed, \
`index_project` to index a new project, `sync_project` to refresh a stale index.
- If queries return empty results, call `list_projects(path=...)` to check whether the project is indexed.

### Tool selection (by task)
| Task | Tool | Instead of |
|------|------|------------|
| Understand a symbol before editing | `get_context_for` with scope="edit" | manual file reads |
| Read source code of a symbol | `get_context_for` | reading files by line range |
| Symbol metadata (file, line, kind) | `get_context_for` with scope="structure" | — |
| Find a symbol by name | `search_symbols` | guessing full_name strings |
| Find who calls a method | `find_usages` | grep for method name |
| Find what a method calls | `find_callees` (use `depth` for reachable call tree) | `execute_query` |
| All usages of any symbol | `find_usages` (use `kind` to filter type refs) | grep |
| Impact analysis before changes | `get_context_for` with scope="impact" | manual caller tracing |
| Find API/controller entry points | `find_entry_points` | recursive find_callers |
| Find all implementations of an interface | `find_implementations` | — |
| Understand class inheritance | `get_hierarchy` | — |
| Find constructor/field dependencies | `find_dependencies` | — |
| Architecture overview | `get_architecture` | — |
| Custom graph queries | `get_schema` then `execute_query` (last resort) | — |

### Avoid
- Do not use `execute_query` when a dedicated tool exists for the task.
- Do not read files with grep or cat when `get_context_for` can retrieve the exact code.
- Do not guess symbol names — use `search_symbols` to discover them first.
- Do not skip `get_context_for` with scope="edit" before modifying a method — it shows \
callers, dependencies, and tests that might break."""

# ── Per-agent templates ──────────────────────────────────────────────


def _markdown_section() -> str:
    """Wrap the shared body in HTML markers for upsert in markdown files."""
    return f"{_MD_START}\n## Synapps MCP\n\n{_SYNAPPS_BODY}\n{_MD_END}"


def _cursor_mdc() -> str:
    """Return a complete Cursor MDC rule file."""
    return (
        "---\n"
        "description: Synapps code intelligence — use graph tools instead of grep/file reads\n"
        "globs: \n"
        "alwaysApply: true\n"
        "---\n\n"
        f"## Synapps MCP\n\n{_SYNAPPS_BODY}\n"
    )


# ── Upsert logic ────────────────────────────────────────────────────

_MARKER_RE = re.compile(
    rf"{re.escape(_MD_START)}.*?{re.escape(_MD_END)}",
    re.DOTALL,
)


def _upsert_markdown(path: Path, section: str) -> None:
    """Insert or replace the marked Synapps section in a markdown file."""
    if path.exists():
        text = path.read_text(encoding="utf-8")
        if _MARKER_RE.search(text):
            text = _MARKER_RE.sub(section, text)
        else:
            text = text.rstrip() + "\n\n" + section + "\n"
    else:
        text = section + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_cursor_mdc(path: Path) -> None:
    """Write the Cursor MDC rule file (fully owned by Synapps)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_cursor_mdc(), encoding="utf-8")


# ── Public API ───────────────────────────────────────────────────────

#: (relative path, writer callable)
_AGENT_FILES: list[tuple[str, str]] = [
    ("CLAUDE.md", "markdown"),
    ("AGENTS.md", "markdown"),
    (".cursor/rules/synapps.mdc", "cursor_mdc"),
    (".github/copilot-instructions.md", "markdown"),
]


def install_agent_instructions(project_path: Path) -> list[str]:
    """Write or update Synapps instruction sections for all known agents.

    Returns a list of relative paths that were written.
    """
    section = _markdown_section()
    written: list[str] = []

    for rel_path, kind in _AGENT_FILES:
        dest = project_path / rel_path
        try:
            if kind == "markdown":
                _upsert_markdown(dest, section)
            elif kind == "cursor_mdc":
                _write_cursor_mdc(dest)
            else:
                log.warning("Unknown agent file kind %r for %s", kind, rel_path)
                continue
            written.append(rel_path)
            log.debug("Wrote %s", dest)
        except OSError:
            log.warning("Could not write %s", dest, exc_info=True)

    return written
