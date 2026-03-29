# Synapps

Code intelligence MCP server — gives AI coding agents a queryable graph of your codebase.

## What it does

- Indexes C#, Python, TypeScript/JavaScript, and Java codebases using tree-sitter and Language Server Protocol
- Stores symbols, call chains, and relationships in a Memgraph graph database
- Exposes semantic query tools as MCP tools — AI agents can find usages, trace call trees, and analyze change impact without reading every file
- Supports incremental sync via git-diff-based change detection and live file watching

## Install

```
pip install synapps-mcp
docker compose up -d
```

The `docker compose up -d` command starts a local Memgraph instance (required for the graph database).

## Configure your MCP client

Add Synapps to your MCP client configuration (e.g., Claude Code `~/.claude.json`):

```json
{
  "mcpServers": {
    "synapps": {
      "command": "synapps-mcp"
    }
  }
}
```

Then index your project:

```
synapps index /path/to/your/project
```

## Supported Languages

- C#
- Python
- TypeScript / JavaScript
- Java

## Key MCP Tools

- `get_context_for` — full context for a symbol before editing (callers, callees, tests); use `scope="impact"` for change impact analysis
- `find_usages` — who calls a method or uses any symbol across the codebase
- `find_callees` — what a method depends on downstream
- `find_entry_points` — find API/controller entry points reaching a method
- `search_symbols` — find symbols by name, kind, file, or namespace

## Links

- [GitHub](https://github.com/SynappsCodeComprehension/synapps)
- [Changelog](https://github.com/SynappsCodeComprehension/synapps/blob/main/CHANGELOG.md)
