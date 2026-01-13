#!/usr/bin/env python3
"""
Test script for MCP client integration.

This script tests the MCP client's ability to:
- Connect to the MCP server
- List available tools
- Execute simple tool commands
- Handle errors gracefully
"""

import os
import sys
import json
import logging
from mcp_client import MCPClient
from mcp_tools import (
    get_tool_for_issue,
    format_tool_arguments,
    list_all_patterns,
    get_pattern_by_name
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_connection(mcp_url: str) -> bool:
    """Test basic connection to MCP server."""
    logger.info(f"Testing connection to {mcp_url}")
    try:
        with MCPClient(mcp_url) as client:
            if client.health_check():
                logger.info("✓ MCP server is reachable")
                return True
            else:
                logger.error("✗ MCP server health check failed")
                return False
    except Exception as e:
        logger.error(f"✗ Connection test failed: {e}")
        return False


def test_list_tools(mcp_url: str) -> bool:
    """Test listing available tools."""
    logger.info("Testing tool listing")
    try:
        with MCPClient(mcp_url) as client:
            tools = client.list_tools()
            if tools:
                logger.info(f"✓ Retrieved {len(tools)} tools:")
                for tool in tools:
                    tool_name = tool.get('name', 'unknown')
                    tool_desc = tool.get('description', 'No description')
                    logger.info(f"  - {tool_name}: {tool_desc}")
                return True
            else:
                logger.warning("✗ No tools returned (or error occurred)")
                return False
    except Exception as e:
        logger.error(f"✗ Tool listing failed: {e}")
        return False


def test_tool_execution(mcp_url: str) -> bool:
    """Test executing a simple tool."""
    logger.info("Testing tool execution")
    try:
        with MCPClient(mcp_url) as client:
            # Try to execute a simple filesystem command
            result = client.call_tool("filesystem", {"command": "pwd"})

            if "error" in result:
                logger.warning(f"✗ Tool execution returned error: {result['error']}")
                return False
            else:
                logger.info(f"✓ Tool executed successfully: {json.dumps(result, indent=2)}")
                return True
    except Exception as e:
        logger.error(f"✗ Tool execution failed: {e}")
        return False


def test_tool_patterns():
    """Test tool pattern utilities."""
    logger.info("Testing tool pattern utilities")

    # Test listing patterns
    patterns = list_all_patterns()
    logger.info(f"✓ Found {len(patterns)} predefined patterns:")
    for name, desc in patterns.items():
        logger.info(f"  - {name}: {desc}")

    # Test getting pattern by issue type
    issue_type = "container_down"
    pattern = get_tool_for_issue(issue_type)
    if pattern:
        logger.info(f"✓ Pattern for '{issue_type}': {pattern.get('description')}")
    else:
        logger.warning(f"✗ No pattern found for '{issue_type}'")

    # Test formatting arguments
    restart_pattern = get_pattern_by_name("restart_container")
    if restart_pattern:
        formatted = format_tool_arguments(restart_pattern, container_name="nginx")
        logger.info(f"✓ Formatted pattern: {json.dumps(formatted, indent=2)}")
        return True
    else:
        logger.error("✗ Failed to get restart_container pattern")
        return False


def test_error_handling(mcp_url: str):
    """Test error handling for invalid requests."""
    logger.info("Testing error handling")
    try:
        with MCPClient(mcp_url) as client:
            # Try to call a non-existent tool
            result = client.call_tool("nonexistent_tool", {})
            if "error" in result:
                logger.info(f"✓ Error handling works: {result['error']}")
            else:
                logger.warning("✗ Expected error for non-existent tool, but got success")
    except Exception as e:
        logger.error(f"✗ Error handling test failed: {e}")


def main():
    """Run all MCP integration tests."""
    print("=" * 60)
    print("MCP Client Integration Tests")
    print("=" * 60)

    # Get MCP URL from environment or use default
    mcp_url = os.getenv("MCP_URL", "http://localhost:8433")
    print(f"\nMCP Server URL: {mcp_url}")
    print()

    # Track test results
    results = {
        "Connection Test": test_connection(mcp_url),
        "List Tools Test": test_list_tools(mcp_url),
        "Tool Execution Test": test_tool_execution(mcp_url),
        "Tool Patterns Test": test_tool_patterns(),
    }

    # Run error handling test (doesn't affect pass/fail)
    print()
    test_error_handling(mcp_url)

    # Print summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    passed = sum(1 for result in results.values() if result)
    total = len(results)

    for test_name, result in results.items():
        status = "PASS" if result else "FAIL"
        symbol = "✓" if result else "✗"
        print(f"{symbol} {test_name}: {status}")

    print()
    print(f"Overall: {passed}/{total} tests passed")

    # Exit with appropriate code
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
