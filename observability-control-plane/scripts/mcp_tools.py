#!/usr/bin/env python3
"""
MCP tool execution patterns for common observability fixes.

This module provides pre-defined tool execution patterns that can be used
to address common infrastructure issues identified by the observability system.
"""

from typing import Dict, Any, Optional

# Common tool execution patterns
TOOL_PATTERNS = {
    "restart_container": {
        "tool": "docker",
        "arguments": {
            "command": "restart",
            "container": "{container_name}"
        },
        "description": "Restart a Docker container"
    },
    "prune_system": {
        "tool": "docker",
        "arguments": {
            "command": "system prune",
            "flags": ["-f"]
        },
        "description": "Remove unused Docker resources"
    },
    "check_disk": {
        "tool": "filesystem",
        "arguments": {
            "command": "df",
            "path": "/"
        },
        "description": "Check disk usage"
    },
    "check_logs": {
        "tool": "filesystem",
        "arguments": {
            "command": "tail",
            "path": "/var/log/{service}.log",
            "lines": 100
        },
        "description": "Check recent service logs"
    },
    "inspect_container": {
        "tool": "docker",
        "arguments": {
            "command": "inspect",
            "container": "{container_name}"
        },
        "description": "Get detailed container information"
    },
    "container_stats": {
        "tool": "docker",
        "arguments": {
            "command": "stats",
            "container": "{container_name}",
            "no_stream": True
        },
        "description": "Get container resource usage statistics"
    },
    "check_network": {
        "tool": "docker",
        "arguments": {
            "command": "network inspect",
            "network": "{network_name}"
        },
        "description": "Inspect Docker network configuration"
    },
    "query_database": {
        "tool": "postgresql",
        "arguments": {
            "query": "{sql_query}"
        },
        "description": "Execute PostgreSQL query"
    },
    "query_graph": {
        "tool": "neo4j",
        "arguments": {
            "query": "{cypher_query}"
        },
        "description": "Execute Neo4j Cypher query"
    },
    "check_github_status": {
        "tool": "github",
        "arguments": {
            "command": "repo info",
            "repo": "{repo_name}"
        },
        "description": "Get GitHub repository information"
    }
}


# Issue type to tool pattern mapping
ISSUE_TO_TOOL_MAPPING = {
    "container_down": "restart_container",
    "container_unhealthy": "inspect_container",
    "disk_full": "prune_system",
    "high_disk_usage": "check_disk",
    "service_error": "check_logs",
    "high_memory": "container_stats",
    "network_issue": "check_network",
    "database_slow": "query_database",
    "graph_query_slow": "query_graph"
}


def get_tool_for_issue(issue_type: str) -> Optional[Dict[str, Any]]:
    """
    Get appropriate tool pattern based on issue type.

    Args:
        issue_type: Type of issue (e.g., "container_down", "disk_full")

    Returns:
        Tool pattern dictionary or None if no pattern found
    """
    pattern_name = ISSUE_TO_TOOL_MAPPING.get(issue_type)
    if pattern_name:
        return TOOL_PATTERNS.get(pattern_name)
    return None


def format_tool_arguments(pattern: Dict[str, Any], **kwargs) -> Dict[str, Any]:
    """
    Format tool arguments by replacing placeholders with actual values.

    Args:
        pattern: Tool pattern dictionary
        **kwargs: Values to substitute in placeholders

    Returns:
        Tool pattern with placeholders replaced

    Example:
        >>> pattern = TOOL_PATTERNS["restart_container"]
        >>> format_tool_arguments(pattern, container_name="nginx")
        {
            "tool": "docker",
            "arguments": {"command": "restart", "container": "nginx"}
        }
    """
    import copy
    import re

    formatted_pattern = copy.deepcopy(pattern)

    def replace_placeholders(obj):
        if isinstance(obj, dict):
            return {k: replace_placeholders(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [replace_placeholders(item) for item in obj]
        elif isinstance(obj, str):
            # Replace {placeholder} with actual value
            for key, value in kwargs.items():
                obj = obj.replace(f"{{{key}}}", str(value))
            return obj
        return obj

    formatted_pattern["arguments"] = replace_placeholders(formatted_pattern["arguments"])
    return formatted_pattern


def list_all_patterns() -> Dict[str, str]:
    """
    List all available tool patterns with descriptions.

    Returns:
        Dictionary mapping pattern names to descriptions
    """
    return {
        name: pattern.get("description", "No description")
        for name, pattern in TOOL_PATTERNS.items()
    }


def get_pattern_by_name(pattern_name: str) -> Optional[Dict[str, Any]]:
    """
    Get a specific tool pattern by name.

    Args:
        pattern_name: Name of the pattern

    Returns:
        Tool pattern dictionary or None if not found
    """
    return TOOL_PATTERNS.get(pattern_name)
