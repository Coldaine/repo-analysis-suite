"""
MCP Tools Integration using langchain-mcp-adapters.

This module provides MCP (Model Context Protocol) tool integration using the official
langchain-mcp-adapters library pattern with MultiServerMCPClient.

Usage:
    from multiagentpanic.tools.mcp_tools import MCPToolProvider

    # Create provider (typically singleton in app lifecycle)
    provider = MCPToolProvider()

    # Get tools for binding to agents
    tools = await provider.get_tools()

    # Use with LangGraph agents
    agent = create_react_agent(model, tools)

    # Clean up when done (important for resource management)
    await provider.close()
"""

import asyncio
import atexit
import logging
from typing import Dict, Any, List, Optional
from langchain_core.tools import BaseTool

from multiagentpanic.config.settings import get_settings

logger = logging.getLogger(__name__)


class MCPToolProvider:
    """
    Provides MCP tools via langchain-mcp-adapters MultiServerMCPClient.
    
    This class wraps the MultiServerMCPClient to provide a consistent interface
    for MCP tool access throughout the application. Tools are lazily loaded on
    first access and cached for subsequent calls.
    
    The provider reads MCP server configuration from application settings and
    dynamically constructs the server connection parameters.
    """
    
    def __init__(self, settings=None):
        """
        Initialize the MCP tool provider.
        
        Args:
            settings: Optional settings override. Uses get_settings() if not provided.
        """
        self.settings = settings or get_settings()
        self._client: Optional[Any] = None
        self._tools: Optional[List[BaseTool]] = None
        self._initialized = False
        
    def _build_server_config(self) -> Dict[str, Dict[str, Any]]:
        """
        Build MCP server configuration from application settings.
        
        Returns:
            Dictionary mapping server names to their connection parameters.
        """
        mcp_settings = self.settings.mcp
        servers = {}
        
        # Git server (mcp-server-git)
        if mcp_settings.git_enabled:
            servers["git"] = {
                "command": mcp_settings.git_server_command,
                "args": mcp_settings.git_server_args,
                "transport": "stdio",
            }
            logger.debug(f"Configured git MCP server: {servers['git']}")
        
        # Filesystem server (mcp-server-filesystem)
        if mcp_settings.filesystem_enabled:
            servers["filesystem"] = {
                "command": mcp_settings.filesystem_server_command,
                "args": mcp_settings.filesystem_server_args,
                "transport": "stdio",
            }
            logger.debug(f"Configured filesystem MCP server: {servers['filesystem']}")
        
        # Zoekt search server (when available)
        if mcp_settings.zoekt_enabled and mcp_settings.zoekt_server_command:
            servers["zoekt"] = {
                "command": mcp_settings.zoekt_server_command,
                "args": mcp_settings.zoekt_server_args,
                "transport": "stdio",
            }
            logger.debug(f"Configured zoekt MCP server: {servers['zoekt']}")
        
        # LSP server (when available)
        if mcp_settings.lsp_enabled and mcp_settings.lsp_server_command:
            servers["lsp"] = {
                "command": mcp_settings.lsp_server_command,
                "args": mcp_settings.lsp_server_args,
                "transport": "stdio",
            }
            logger.debug(f"Configured LSP MCP server: {servers['lsp']}")
        
        return servers
    
    async def get_tools(self) -> List[BaseTool]:
        """
        Get all available MCP tools as LangChain-compatible tools.
        
        This method lazily initializes the MultiServerMCPClient and retrieves
        tools from all configured MCP servers. Tools are cached after first retrieval.
        
        Returns:
            List of LangChain BaseTool objects that can be bound to agents.
            
        Raises:
            RuntimeError: If no MCP servers are configured.
            Exception: If tool loading fails from any configured server.
        """
        if self._tools is not None:
            return self._tools
        
        server_config = self._build_server_config()
        
        if not server_config:
            logger.warning("No MCP servers configured. Returning empty tool list.")
            self._tools = []
            return self._tools
        
        try:
            from langchain_mcp_adapters.client import MultiServerMCPClient
            
            # Create the multi-server client
            self._client = MultiServerMCPClient(server_config)
            
            # Get tools from all configured servers
            self._tools = await self._client.get_tools()
            self._initialized = True
            
            logger.info(f"Loaded {len(self._tools)} MCP tools from {len(server_config)} servers")
            for tool in self._tools:
                logger.debug(f"  - {tool.name}: {tool.description[:50]}...")
                
            return self._tools
            
        except ImportError as e:
            logger.error(
                "langchain-mcp-adapters not installed. "
                "Install with: pip install langchain-mcp-adapters"
            )
            raise RuntimeError(
                "Missing dependency: langchain-mcp-adapters. "
                "Run 'pip install langchain-mcp-adapters' to install."
            ) from e
            
        except Exception as e:
            logger.error(f"Failed to load MCP tools: {e}")
            raise
    
    async def get_tools_by_server(self, server_name: str) -> List[BaseTool]:
        """
        Get tools from a specific MCP server.
        
        Args:
            server_name: Name of the server (e.g., "git", "filesystem", "zoekt")
            
        Returns:
            List of tools from the specified server only.
        """
        all_tools = await self.get_tools()
        
        # Tools from langchain-mcp-adapters are prefixed with server name
        # e.g., "git__git_log", "filesystem__read_file"
        return [t for t in all_tools if t.name.startswith(f"{server_name}__")]
    
    def get_tool_names(self) -> List[str]:
        """
        Get list of available tool names.
        
        Returns:
            List of tool name strings.
        """
        if self._tools is None:
            return []
        return [tool.name for tool in self._tools]
    
    @property
    def is_initialized(self) -> bool:
        """Check if the provider has been initialized with tools."""
        return self._initialized

    async def close(self) -> None:
        """
        Close the MCP client and release resources.

        This should be called when the provider is no longer needed to properly
        clean up subprocess connections to MCP servers.
        """
        if self._client is not None:
            try:
                # MultiServerMCPClient has a close method for cleanup
                if hasattr(self._client, 'close'):
                    await self._client.close()
                elif hasattr(self._client, '__aexit__'):
                    await self._client.__aexit__(None, None, None)
                logger.debug("MCP client closed successfully")
            except Exception as e:
                logger.warning(f"Error closing MCP client: {e}")
            finally:
                self._client = None
                self._tools = None
                self._initialized = False

    def close_sync(self) -> None:
        """
        Synchronous wrapper for close() for use in atexit handlers.

        This creates a new event loop if needed to run the async close.
        When called from within a running event loop, uses run_coroutine_threadsafe
        to ensure cleanup actually completes before returning.
        """
        if self._client is None:
            return

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop is not None and loop.is_running():
            # Use run_coroutine_threadsafe to wait for completion
            future = asyncio.run_coroutine_threadsafe(self.close(), loop)
            try:
                future.result(timeout=5.0)  # Wait up to 5 seconds
            except Exception as e:
                logger.warning(f"Error during MCP cleanup in running loop: {e}")
                # Fall back to direct cleanup
                self._client = None
                self._tools = None
                self._initialized = False
        else:
            # Create new loop for cleanup
            try:
                asyncio.run(self.close())
            except RuntimeError:
                # If we can't run async, try direct cleanup
                if hasattr(self._client, '_cleanup'):
                    self._client._cleanup()
                self._client = None
                self._tools = None
                self._initialized = False


# Module-level singleton for convenience
_provider: Optional[MCPToolProvider] = None


def get_mcp_tool_provider() -> MCPToolProvider:
    """
    Get the singleton MCP tool provider instance.
    
    Returns:
        MCPToolProvider singleton instance.
    """
    global _provider
    if _provider is None:
        _provider = MCPToolProvider()
    return _provider


async def get_mcp_tools() -> List[BaseTool]:
    """
    Convenience function to get all MCP tools.

    This is a shortcut for get_mcp_tool_provider().get_tools().

    Returns:
        List of LangChain BaseTool objects.
    """
    return await get_mcp_tool_provider().get_tools()


def reset_mcp_tool_provider() -> None:
    """
    Reset the singleton provider (useful for testing).

    This closes and removes the current singleton instance.
    """
    global _provider
    if _provider is not None:
        _provider.close_sync()
        _provider = None


def _cleanup_on_exit() -> None:
    """Atexit handler to clean up MCP resources on process exit."""
    global _provider
    if _provider is not None:
        logger.debug("Cleaning up MCP provider on exit")
        _provider.close_sync()


# Register cleanup handler
atexit.register(_cleanup_on_exit)
