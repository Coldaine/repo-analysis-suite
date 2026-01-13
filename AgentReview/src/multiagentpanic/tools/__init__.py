"""
MCP Tool integrations for context gathering.

This package provides tools for:
- Zoekt: Code search across the codebase
- LSP: Language server protocol for symbol analysis
- Git: Git history and blame information
- Filesystem: File system operations for code exploration

Primary Interface:
    MCPToolProvider - Central interface for MCP tools via langchain-mcp-adapters
    get_mcp_tools() - Convenience function to get all MCP tools
    
Legacy Interfaces (for backward compatibility):
    ZoektTool, GitTool, LSPTool - Individual tool classes with mock implementations
"""

# New MCP tools interface (recommended)
from multiagentpanic.tools.mcp_tools import (
    MCPToolProvider,
    get_mcp_tool_provider,
    get_mcp_tools,
)

# Legacy tool implementations (backward compatibility)
from multiagentpanic.tools.zoekt import ZoektTool, zoekt_search
from multiagentpanic.tools.lsp import LSPTool, lsp_get_symbols, lsp_get_references, lsp_get_definition
from multiagentpanic.tools.git import GitTool, git_history, git_blame, git_diff, git_status
from multiagentpanic.tools.filesystem import list_files, read_file, search_codebase

__all__ = [
    # New MCP interface (recommended)
    "MCPToolProvider",
    "get_mcp_tool_provider",
    "get_mcp_tools",
    # Zoekt tools (legacy)
    "ZoektTool",
    "zoekt_search",
    # LSP tools (legacy)
    "LSPTool",
    "lsp_get_symbols",
    "lsp_get_references",
    "lsp_get_definition",
    # Git tools (legacy)
    "GitTool",
    "git_history",
    "git_blame",
    "git_diff",
    "git_status",
    # Filesystem tools (legacy)
    "list_files",
    "read_file",
    "search_codebase"
]
