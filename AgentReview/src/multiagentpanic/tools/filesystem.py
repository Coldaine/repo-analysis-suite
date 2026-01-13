"""
File System Tools for code exploration.
These tools provide basic file system operations for agents to explore codebases.
"""

import os
import json
from typing import Dict, Any, List, Optional
from langchain_core.tools import tool

@tool
def list_files(directory: str = ".", file_pattern: str = "*") -> str:
    """
    List files in a directory with optional pattern matching.

    Args:
        directory: Directory path to list files from
        file_pattern: File pattern filter (e.g., "*.py", "test_*.py")

    Returns:
        Formatted list of files with paths
    """
    try:
        import glob
        files = glob.glob(os.path.join(directory, file_pattern), recursive=True)
        files = [f for f in files if os.path.isfile(f)]

        if not files:
            return f"No files found matching pattern '{file_pattern}' in {directory}"

        output_lines = [f"Found {len(files)} files matching '{file_pattern}':\n"]
        for file_path in sorted(files):
            try:
                size = os.path.getsize(file_path)
                size_str = f"{size:,} bytes"
                output_lines.append(f"- {file_path} ({size_str})")
            except:
                output_lines.append(f"- {file_path}")

        return "\n".join(output_lines)

    except Exception as e:
        return f"Error listing files: {str(e)}"

@tool
def read_file(file_path: str, max_lines: int = 100) -> str:
    """
    Read and return the content of a file.

    Args:
        file_path: Path to the file to read
        max_lines: Maximum number of lines to return (default: 100)

    Returns:
        File content with line numbers
    """
    try:
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()

        if not lines:
            return f"File {file_path} is empty"

        # Limit output to max_lines
        content_lines = lines[:max_lines]
        if len(lines) > max_lines:
            content_lines.append(f"\n... ({len(lines) - max_lines} more lines)\n")

        output_lines = [f"Content of {file_path} ({len(lines)} lines total):\n"]
        for i, line in enumerate(content_lines, 1):
            output_lines.append(f"{i:4d}: {line.rstrip()}")

        return "\n".join(output_lines)

    except FileNotFoundError:
        return f"File not found: {file_path}"
    except Exception as e:
        return f"Error reading file {file_path}: {str(e)}"

@tool
def search_codebase(query: str, file_pattern: str = "*", max_results: int = 20) -> str:
    """
    Search codebase for code matching the query pattern.

    Args:
        query: Search pattern (text to find in files)
        file_pattern: File pattern filter (e.g., "*.py", "test_*.py")
        max_results: Maximum results to return (default: 20)

    Returns:
        Formatted search results with file paths, line numbers, and content
    """
    try:
        import glob
        import re

        # Find all matching files
        files = glob.glob(os.path.join(".", file_pattern), recursive=True)
        files = [f for f in files if os.path.isfile(f)]

        results = []
        for file_path in files:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                    lines = f.readlines()

                for line_num, line_content in enumerate(lines, 1):
                    if query.lower() in line_content.lower():
                        results.append({
                            'file': file_path,
                            'line': line_num,
                            'content': line_content.strip()
                        })
                        if len(results) >= max_results:
                            break

                if len(results) >= max_results:
                    break

            except:
                continue

        if not results:
            return f"No matches found for '{query}' in files matching '{file_pattern}'"

        output_lines = [f"Found {len(results)} matches for '{query}':\n"]
        for result in results:
            output_lines.append(f"{result['file']}:{result['line']}: {result['content']}")

        if len(results) >= max_results:
            output_lines.append(f"\n(Showing first {max_results} results)")

        return "\n".join(output_lines)

    except Exception as e:
        return f"Error searching codebase: {str(e)}"