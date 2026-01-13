import asyncio
import logging
from typing import Any, Dict, List, Optional
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from multiagentpanic.config.settings import get_settings

logger = logging.getLogger(__name__)

async def run_mcp_tool(server_type: str, tool_name: str, arguments: Dict[str, Any]) -> Any:
    """
    Run a tool on an MCP server.
    
    Args:
        server_type: "git" or "filesystem"
        tool_name: Name of the tool to run
        arguments: Arguments for the tool
        
    Returns:
        The result of the tool execution
    """
    settings = get_settings()
    
    if server_type == "git":
        command = settings.mcp.git_server_command
        args = settings.mcp.git_server_args
    elif server_type == "filesystem":
        command = settings.mcp.filesystem_server_command
        args = settings.mcp.filesystem_server_args
    else:
        raise ValueError(f"Unknown server type: {server_type}")
        
    server_params = StdioServerParameters(
        command=command,
        args=args,
        env=None
    )
    
    logger.debug(f"Connecting to MCP server: {command} {args}")
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # List tools to verify availability (optional but good for debugging)
            # tools = await session.list_tools()
            
            result = await session.call_tool(tool_name, arguments)
            return result
