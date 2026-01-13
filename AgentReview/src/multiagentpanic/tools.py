import subprocess
import os
from typing import List, Optional
from pathlib import Path
from langchain_core.tools import tool

# Global variable to store the repo root. 
# In a more advanced setup, this would be handled via config/context.
_REPO_ROOT: Optional[Path] = None

def set_repo_root(path: Path):
    global _REPO_ROOT
    _REPO_ROOT = path

def get_repo_root() -> Path:
    if _REPO_ROOT is None:
        raise ValueError("Repository root not set. Call set_repo_root() first.")
    return _REPO_ROOT

@tool
def list_files(directory: str = ".") -> str:
    """
    Lists files and directories in the given directory (relative to repo root).
    Use this to explore the file structure.
    """
    root = get_repo_root()
    target_path = (root / directory).resolve()
    
    # Security check to prevent escaping repo root
    try:
        target_path.relative_to(root)
    except ValueError:
        return f"Error: Access denied. Path {directory} is outside repository root."

    if not target_path.exists():
        return f"Error: Path {directory} does not exist."
    
    if not target_path.is_dir():
        return f"Error: Path {directory} is not a directory."

    try:
        items = []
        for item in target_path.iterdir():
            type_marker = "[DIR]" if item.is_dir() else "[FILE]"
            size_marker = f"({item.stat().st_size} bytes)" if item.is_file() else ""
            items.append(f"{type_marker} {item.name} {size_marker}")
        return "\n".join(sorted(items))
    except Exception as e:
        return f"Error listing directory: {e}"

@tool
def read_file(file_path: str) -> str:
    """
    Reads the content of a file (relative to repo root).
    Use this to examine code, tests, or documentation.
    """
    root = get_repo_root()
    target_path = (root / file_path).resolve()

    # Security check
    try:
        target_path.relative_to(root)
    except ValueError:
        return f"Error: Access denied. Path {file_path} is outside repository root."

    if not target_path.exists():
        return f"Error: File {file_path} does not exist."
    
    if not target_path.is_file():
        return f"Error: Path {file_path} is not a file."

    try:
        # Limit file size to avoid context explosion (e.g. 100KB limit)
        if target_path.stat().st_size > 100 * 1024:
            return f"Error: File is too large ({target_path.stat().st_size} bytes). Use 'grep' to search specific patterns instead."
        
        return target_path.read_text(encoding='utf-8', errors='replace')
    except Exception as e:
        return f"Error reading file: {e}"

@tool
def search_codebase(pattern: str, directory: str = ".") -> str:
    """
    Searches for a regex pattern in the codebase using 'grep' (or ripgrep if installed).
    Returns lines matching the pattern with line numbers.
    Useful for finding specific code snippets, function definitions, or usage.
    """
    root = get_repo_root()
    target_path = (root / directory).resolve()
    
    # Security check
    try:
        target_path.relative_to(root)
    except ValueError:
        return f"Error: Access denied. Path {directory} is outside repository root."

    # Try to use git grep first (fastest and respects .gitignore), then rg, then grep
    commands_to_try = [
        ["git", "grep", "-n", "-I", pattern, "--", str(target_path)], # -I ignores binary files
        ["rg", "-n", "--no-heading", pattern, str(target_path)],
        ["grep", "-r", "-n", pattern, str(target_path)]
    ]

    for cmd in commands_to_try:
        try:
            # simple check if command exists
            # On windows 'git' or 'rg' might be in path. 'grep' is usually not unless git bash / wsl.
            # We use shell=False for safety, but need full path if not in PATH.
            # We rely on the environment PATH.
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                cwd=root, # Run from root so paths are relative
                encoding='utf-8',
                errors='replace'
            )
            
            if result.returncode == 0:
                # Truncate output if too long (e.g. > 2000 chars)
                output = result.stdout
                if len(output) > 5000:
                    return output[:5000] + "\n... (Output truncated)"
                return output if output.strip() else "No matches found."
            elif result.returncode == 1:
                continue # Not found, try next tool or just return not found at end
            else:
                 # Command failed (e.g. executable not found), try next
                 continue
        except FileNotFoundError:
            continue
    
    return "No matches found (or search tools 'git grep'/'rg'/'grep' not available)."