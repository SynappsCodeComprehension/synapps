"""Server-level instructions sent to every MCP client during initialization."""

SERVER_INSTRUCTIONS = """\
Synapps is a code intelligence graph. Use Synapps tools instead of grep or file reads \
for understanding code structure, relationships, and navigating symbols.

PRIMARY TOOLS (use these first):
- read_symbol(full_name, max_lines=100) — Read a symbol's source code. \
Instead of cat file.py or reading line ranges, use read_symbol. \
Falls back to member overview when source is large.
- search_symbols(query, kind=, namespace=, file_path=, language=) — Find symbols by name. \
Instead of grep -r "def my_function" or guessing full_name strings, use search_symbols. \
Strips language keywords and syntax automatically.
- find_usages(full_name, kind=) — Find all code that uses a symbol. \
Instead of grep -r "MyClass" for callers or manual cross-reference tracing, use find_usages.

SECONDARY TOOLS (deeper analysis):
- get_context_for(full_name, members_only=False) — Full symbol context: source, containing type, \
interfaces, callees, dependencies, summaries. \
Instead of reading multiple files to understand a class, use get_context_for. \
Use members_only=True for quick member overview. No callers or tests — use assess_impact for those.
- assess_impact(full_name) — Change risk: direct callers, transitive callers, test coverage, \
interface contract, HTTP endpoints. \
Instead of manually tracing callers and tests, use assess_impact.
- find_callees(full_name, depth=) — What a method calls. Use depth param for reachable call tree.
- find_implementations(full_name) — Classes implementing an interface.
- get_architecture(path) — Project overview: packages, hotspots, HTTP map, stats.
- find_http_endpoints(route=, http_method=, trace=) — HTTP endpoint search and tracing.
- find_dead_code(path) — [Experimental] Methods with zero callers.
- find_untested(path) — [Experimental] Production methods with no test coverage.

UTILITY TOOLS:
- summary(action, full_name=, content=) — Persist non-derivable context on symbols. \
Do NOT store structural descriptions — those are queryable live via get_context_for, find_usages, etc.
- get_schema() — Graph schema for Cypher queries.
- execute_query(cypher) — Last resort raw Cypher. Prefer dedicated tools.

WORKFLOW:
- Projects must be indexed before querying. Call list_projects to check what is indexed, \
index_project to index a new project, sync_project to refresh a stale index.
- If queries return empty results, call list_projects(path=...) to check whether the project is indexed.

INSTEAD OF GREP/READ:
- Instead of cat file.py or reading line ranges → read_symbol(full_name="...")
- Instead of grep -r "ClassName" → search_symbols(query="ClassName")
- Instead of grep -r "def method_name" → search_symbols(query="method_name")
- Instead of grep for callers → find_usages(full_name="...")
- Instead of reading files to understand a class → get_context_for(full_name="...")
- Instead of manual impact analysis → assess_impact(full_name="...")

AVOID:
- Do not use execute_query when a dedicated tool exists for the task.
- Do not read files with grep or cat when read_symbol or get_context_for can retrieve the exact code.
- Do not guess symbol names — use search_symbols to discover them first.
- Do not skip get_context_for before modifying a method — it shows dependencies and structure. \
Use assess_impact for callers and tests.

KNOWN GRAPH BOUNDARIES:
- Only project-defined symbols are indexed. Calls to external framework types (Spring Data, \
RestTemplate, JDK stdlib, .NET BCL, Entity Framework) do not appear as CALLS edges. \
Use get_context_for to read call sites directly when framework method calls are needed.

CLI-ONLY TOOLS (not available via MCP):
- synapps doctor -- check runtime environment and dependencies
- synapps delete <path> -- delete a project and all its graph data
- synapps status <path> -- detailed index status (also available via list_projects(path=...))\
"""
