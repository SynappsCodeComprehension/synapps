## MCP Tools Consolidation

Reviewed 2026-03-24. Synapse has 30 MCP tools — goal is to reduce to ~20 by removing overlap and demoting admin/diagnostic tools to CLI-only.

### Merge: Type analysis tools (save 2 tools)
- `find_type_references` and `find_type_impact` overlap with `find_usages`
- Fold prod/test breakdown and kind filter into `find_usages` as optional params
- Remove `find_type_references` and `find_type_impact` as standalone tools

### Merge: Summary tools (save 2 tools)
- `set_summary`, `get_summary`, `list_summarized` → single `summary` tool with action param
- Or demote all three to CLI-only if agents don't actually use summaries

### Remove: `get_call_depth` (save 1 tool)
- Recursive `find_callees` with depth tracking — add `depth` param to `find_callees` instead

### Remove: `find_interface_contract` (save 1 tool)
- Achievable via `get_hierarchy` + `find_implementations`
- Rarely needed as standalone operation

### Remove: `audit_architecture` (save 1 tool)
- Only 2 hardcoded rules, C#-specific
- Too narrow for a tool slot — use `execute_query` instead

### Demote to CLI-only (save 3 tools)
- `check_environment` — agents don't need this; users run `synapse doctor`
- `delete_project` — destructive admin action, better as CLI-only
- `get_index_status` — merge into `list_projects` with optional path filter
