---
doc_type: reference
subsystem: agents/context
domain_code: ctx
version: 1.1.0
status: draft
owners: pmacl
last_reviewed: 2025-01-13
---

# Context Agents Domain

Three context-gathering agents that provide supporting information to review agents.

## Agent Types

| Agent | Purpose | Tool | Status |
|-------|---------|------|--------|
| Zoekt | Code search across repository | `zoekt_search` | ✅ Implemented (fallback to git grep) |
| LSP | Symbol resolution, definitions | `lsp_get_symbols`, `lsp_get_references`, `lsp_get_definition` | ✅ Implemented (AST-based fallback) |
| Git | History, blame, changes | `git_history`, `git_blame`, `git_diff` | ✅ Implemented |

## Characteristics

- **Disposable**: Created on-demand, discarded after use
- **Cheap**: Use inexpensive models (haiku, gpt-4o-mini)
- **Single-purpose**: Each handles one type of context

## Tool Implementations

All tools are implemented in `src/multiagentpanic/tools/`:

### Zoekt Tools (`zoekt.py`)
- `ZoektTool` class with `search()` method
- Falls back to `git grep` when Zoekt server unavailable
- `zoekt_search()` - LangChain tool decorator for agent use

### LSP Tools (`lsp.py`)
- `LSPTool` class with AST-based symbol extraction
- Python AST parsing for accurate symbol detection
- `lsp_get_symbols()` - Get symbols in a file
- `lsp_get_references()` - Find all references to a symbol
- `lsp_get_definition()` - Find where a symbol is defined

### Git Tools (`git.py`)
- `GitTool` class wrapping git commands
- `git_history()` - Commit history for a file
- `git_blame()` - Line-by-line authorship
- `git_diff()` - Changes between refs

## Code Location

- Tools: `src/multiagentpanic/tools/`
- Context agents: `src/multiagentpanic/agents/context/` (TODO)

## Domain Documents

- `ctx-zoekt.md` - Zoekt agent details (TODO)
- `ctx-lsp.md` - LSP agent details (TODO)
- `ctx-git.md` - Git agent details (TODO)

## Related Documentation

- [Review Agents](../review/rev-overview.md) - Agents that spawn context agents
- [Configuration](../../../guides/configuration.md) - MCP server setup
