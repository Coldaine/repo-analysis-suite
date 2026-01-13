#!/usr/bin/env python3
"""
MCP (Model Context Protocol) client for tool execution.

This client connects to an MCP server and provides methods to:
- List available tools
- Execute tools with arguments
- Handle errors gracefully
"""

import httpx
import json
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


class MCPClient:
    """Model Context Protocol client for tool execution"""

    def __init__(self, base_url: str = "http://localhost:8433"):
        """
        Initialize MCP client.

        Args:
            base_url: Base URL of the MCP server (default: http://localhost:8433)
        """
        self.base_url = base_url.rstrip('/')
        self.client = httpx.Client(timeout=30.0)
        logger.info(f"MCP client initialized for {self.base_url}")

    def list_tools(self) -> List[Dict[str, Any]]:
        """
        List available tools from MCP server.

        Returns:
            List of tool definitions, each containing name, description, and schema.
            Returns empty list on error.
        """
        try:
            response = self.client.get(f"{self.base_url}/tools")
            response.raise_for_status()
            tools = response.json()
            logger.info(f"Retrieved {len(tools)} tools from MCP server")
            return tools
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error listing tools: {e.response.status_code} - {e.response.text}")
            return []
        except httpx.RequestError as e:
            logger.error(f"Connection error listing tools: {e}")
            return []
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON response from MCP server: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error listing tools: {e}")
            return []

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a tool via MCP server.

        Args:
            tool_name: Name of the tool to execute
            arguments: Dictionary of arguments to pass to the tool

        Returns:
            Tool execution result as a dictionary.
            Returns {"error": "..."} on failure.
        """
        try:
            logger.info(f"Calling tool '{tool_name}' with args: {arguments}")
            response = self.client.post(
                f"{self.base_url}/tools/{tool_name}/execute",
                json=arguments,
                timeout=60.0  # Longer timeout for tool execution
            )
            response.raise_for_status()
            result = response.json()
            logger.info(f"Tool '{tool_name}' executed successfully")
            return result
        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP {e.response.status_code}: {e.response.text}"
            logger.error(f"Failed to call tool {tool_name}: {error_msg}")
            return {"error": error_msg, "tool": tool_name}
        except httpx.RequestError as e:
            error_msg = f"Connection error: {e}"
            logger.error(f"Failed to call tool {tool_name}: {error_msg}")
            return {"error": error_msg, "tool": tool_name}
        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON response: {e}"
            logger.error(f"Failed to parse response from {tool_name}: {error_msg}")
            return {"error": error_msg, "tool": tool_name}
        except Exception as e:
            error_msg = f"Unexpected error: {e}"
            logger.error(f"Failed to call tool {tool_name}: {error_msg}")
            return {"error": error_msg, "tool": tool_name}

    def health_check(self) -> bool:
        """
        Check if MCP server is reachable.

        Returns:
            True if server responds, False otherwise
        """
        try:
            response = self.client.get(f"{self.base_url}/health", timeout=5.0)
            response.raise_for_status()
            logger.info("MCP server health check passed")
            return True
        except Exception as e:
            logger.warning(f"MCP server health check failed: {e}")
            return False

    def close(self):
        """Close the HTTP client connection."""
        try:
            self.client.close()
            logger.debug("MCP client connection closed")
        except Exception as e:
            logger.warning(f"Error closing MCP client: {e}")

    def __del__(self):
        """Cleanup on deletion."""
        self.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
