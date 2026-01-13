"""
Git History Tool - MCP Integration

Provides git history analysis for understanding code evolution.
Useful for context gathering to understand why code is the way it is.

References:
- Built-in git commands
- MCP: Git history context for PR reviews
"""

import subprocess
import json
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from langchain_core.tools import tool
from multiagentpanic.tools.mcp_client import run_mcp_tool
import asyncio

logger = logging.getLogger(__name__)


@dataclass
class Commit:
    """A git commit"""
    sha: str
    message: str
    author: str
    date: datetime
    files_changed: List[str] = field(default_factory=list)


@dataclass
class BlameLine:
    """A line with blame information"""
    line_number: int
    content: str
    commit_sha: str
    author: str
    date: str
    

@dataclass
class FileDiff:
    """Diff information for a file"""
    file: str
    additions: int
    deletions: int
    patch: str


class GitTool:
    """
    Git tool for history analysis and blame information.
    
    Provides:
    - File history
    - Line-by-line blame
    - Commit information
    - Diff between refs
    """
    
    def __init__(self, repo_root: str = "."):
        """
        Initialize Git tool.
        
        Args:
            repo_root: Root directory of the git repository
        """
        self.repo_root = Path(repo_root).resolve()
        
    def get_status_mcp(self) -> str:
        """Get status using MCP server"""
        try:
            result = asyncio.run(run_mcp_tool("git", "git_status", {"repo_path": str(self.repo_root)}))
            if result.content and hasattr(result.content[0], 'text'):
                return result.content[0].text
            return str(result)
        except Exception as e:
            logger.error(f"MCP git_status failed: {e}")
            return f"Error: {e}"

    def get_diff_mcp(self, target: str) -> str:
        """Get diff using MCP server"""
        try:
            result = asyncio.run(run_mcp_tool("git", "git_diff", {"repo_path": str(self.repo_root), "target": target}))
            if result.content and hasattr(result.content[0], 'text'):
                return result.content[0].text
            return ""
        except Exception as e:
            logger.error(f"MCP git_diff failed: {e}")
            return ""

    def _run_git(self, args: List[str], timeout: int = 30) -> subprocess.CompletedProcess:
        """Run a git command"""
        return subprocess.run(
            ["git"] + args,
            capture_output=True,
            text=True,
            cwd=self.repo_root,
            timeout=timeout,
            encoding='utf-8',
            errors='replace'
        )
    
    def get_file_history(
        self,
        file_path: str,
        max_commits: int = 10
    ) -> List[Commit]:
        """
        Get commit history for a file.
        
        Args:
            file_path: Path to the file (relative to repo root)
            max_commits: Maximum number of commits to return
            
        Returns:
            List of Commit objects
        """
        try:
            result = self._run_git([
                "log",
                f"-n{max_commits}",
                "--format=%H|%s|%an|%aI",
                "--",
                file_path
            ])
            
            if result.returncode != 0:
                logger.warning(f"git log failed: {result.stderr}")
                return []
                
            commits = []
            for line in result.stdout.strip().split("\n"):
                if "|" in line:
                    parts = line.split("|", 3)
                    if len(parts) >= 4:
                        try:
                            date = datetime.fromisoformat(parts[3].replace("Z", "+00:00"))
                        except:
                            date = datetime.now()
                            
                        commits.append(Commit(
                            sha=parts[0],
                            message=parts[1],
                            author=parts[2],
                            date=date
                        ))
                        
            return commits
            
        except Exception as e:
            logger.error(f"Error getting file history: {e}")
            return []
    
    def get_blame(
        self,
        file_path: str,
        start_line: Optional[int] = None,
        end_line: Optional[int] = None
    ) -> List[BlameLine]:
        """
        Get blame information for a file.
        
        Args:
            file_path: Path to the file
            start_line: Optional start line (1-indexed)
            end_line: Optional end line (1-indexed)
            
        Returns:
            List of BlameLine objects
        """
        try:
            args = ["blame", "--porcelain"]
            
            if start_line and end_line:
                args.extend(["-L", f"{start_line},{end_line}"])
                
            args.append(file_path)
            
            result = self._run_git(args)
            
            if result.returncode != 0:
                logger.warning(f"git blame failed: {result.stderr}")
                return []
                
            blame_lines = []
            current_sha = ""
            current_author = ""
            current_date = ""
            line_num = start_line or 1
            
            for line in result.stdout.split("\n"):
                if line.startswith("author "):
                    current_author = line[7:]
                elif line.startswith("author-time "):
                    try:
                        timestamp = int(line[12:])
                        current_date = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d")
                    except:
                        current_date = ""
                elif line.startswith("\t"):
                    # This is the actual line content
                    blame_lines.append(BlameLine(
                        line_number=line_num,
                        content=line[1:],  # Remove leading tab
                        commit_sha=current_sha[:8],
                        author=current_author,
                        date=current_date
                    ))
                    line_num += 1
                elif len(line) >= 40 and line[0] not in " \t":
                    # This is a commit SHA line
                    current_sha = line.split()[0]
                    
            return blame_lines
            
        except Exception as e:
            logger.error(f"Error getting blame: {e}")
            return []
    
    def get_diff(
        self,
        ref1: str = "HEAD~1",
        ref2: str = "HEAD",
        file_path: Optional[str] = None
    ) -> List[FileDiff]:
        """
        Get diff between two refs.
        
        Args:
            ref1: First reference (default: HEAD~1)
            ref2: Second reference (default: HEAD)
            file_path: Optional file to limit diff to
            
        Returns:
            List of FileDiff objects
        """
        try:
            args = ["diff", "--stat", ref1, ref2]
            
            if file_path:
                args.extend(["--", file_path])
                
            result = self._run_git(args)
            
            if result.returncode != 0:
                logger.warning(f"git diff failed: {result.stderr}")
                return []
                
            diffs = []
            
            # Parse stat output
            for line in result.stdout.strip().split("\n")[:-1]:  # Skip summary line
                if "|" in line:
                    parts = line.split("|")
                    file_name = parts[0].strip()
                    changes = parts[1].strip()
                    
                    additions = changes.count("+")
                    deletions = changes.count("-")
                    
                    diffs.append(FileDiff(
                        file=file_name,
                        additions=additions,
                        deletions=deletions,
                        patch=""  # Could add full patch if needed
                    ))
                    
            return diffs
            
        except Exception as e:
            logger.error(f"Error getting diff: {e}")
            return []
    
    def get_commit_info(self, sha: str) -> Optional[Commit]:
        """
        Get detailed information about a commit.
        
        Args:
            sha: Commit SHA (can be abbreviated)
            
        Returns:
            Commit object or None
        """
        try:
            result = self._run_git([
                "show",
                "--format=%H|%s|%an|%aI",
                "--stat",
                "--no-patch",
                sha
            ])
            
            if result.returncode != 0:
                return None
                
            lines = result.stdout.strip().split("\n")
            if not lines or "|" not in lines[0]:
                return None
                
            parts = lines[0].split("|", 3)
            if len(parts) < 4:
                return None
                
            files = []
            for line in lines[1:]:
                if "|" in line:
                    files.append(line.split("|")[0].strip())
                    
            try:
                date = datetime.fromisoformat(parts[3].replace("Z", "+00:00"))
            except:
                date = datetime.now()
                
            return Commit(
                sha=parts[0],
                message=parts[1],
                author=parts[2],
                date=date,
                files_changed=files
            )
            
        except Exception as e:
            logger.error(f"Error getting commit info: {e}")
            return None


# Global instance
_git_tool: Optional[GitTool] = None


def get_git_tool(repo_root: str = ".") -> GitTool:
    """Get or create the global Git tool instance"""
    global _git_tool
    if _git_tool is None:
        _git_tool = GitTool(repo_root=repo_root)
    return _git_tool


@tool
def git_history(file_path: str, max_commits: int = 10) -> str:
    """
    Get the commit history for a file.
    
    Use this to understand how a file has evolved and why changes were made.
    
    Args:
        file_path: Path to the file (relative to repo root)
        max_commits: Maximum number of commits to show (default 10)
        
    Returns:
        Formatted commit history with authors and messages
    """
    tool = get_git_tool()
    commits = tool.get_file_history(file_path, max_commits)
    
    if not commits:
        return f"No history found for: {file_path}"
    
    output_lines = [f"History for {file_path}:\n"]
    
    for commit in commits:
        date_str = commit.date.strftime("%Y-%m-%d")
        output_lines.append(f"  {commit.sha[:8]} | {date_str} | {commit.author}")
        output_lines.append(f"    {commit.message[:80]}")
        output_lines.append("")
        
    return "\n".join(output_lines)


@tool
def git_blame(file_path: str, start_line: int = 0, end_line: int = 0) -> str:
    """
    Get blame information showing who last modified each line.
    
    Use this to understand who wrote specific code and when.
    
    Args:
        file_path: Path to the file
        start_line: Start line (0 for beginning of file)
        end_line: End line (0 for end of file)
        
    Returns:
        Annotated file content with author and date per line
    """
    tool = get_git_tool()
    
    start = start_line if start_line > 0 else None
    end = end_line if end_line > 0 else None
    
    blame_lines = tool.get_blame(file_path, start, end)
    
    if not blame_lines:
        return f"No blame information for: {file_path}"
    
    output_lines = [f"Blame for {file_path}:\n"]
    
    for bl in blame_lines[:100]:  # Limit output
        output_lines.append(
            f"{bl.line_number:4d} | {bl.commit_sha} | {bl.author[:15]:15s} | {bl.content}"
        )
        
    if len(blame_lines) > 100:
        output_lines.append(f"\n... and {len(blame_lines) - 100} more lines")
        
    return "\n".join(output_lines)


@tool
def git_status() -> str:
    """
    Get the current working tree status.
    
    Returns:
        Status of changed files
    """
    tool = get_git_tool()
    return tool.get_status_mcp()


@tool
def git_diff(ref1: str = "HEAD~1", ref2: str = "HEAD", file_path: str = "") -> str:
    """
    Get the diff between two git references.
    
    Use this to see what changed between commits or branches.
    
    Args:
        ref1: First reference (commit, branch, tag) - default HEAD~1
        ref2: Second reference - default HEAD
        file_path: Optional file to limit diff to
        
    Returns:
        Summary of changes with files and stats
    """
    tool = get_git_tool()
    
    # Use MCP if no file path is specified (MCP doesn't support file filtering yet)
    if not file_path and ref2 == "HEAD":
        return tool.get_diff_mcp(ref1)

    diffs = tool.get_diff(ref1, ref2, file_path if file_path else None)
    
    if not diffs:
        return f"No differences between {ref1} and {ref2}"
    
    output_lines = [f"Diff {ref1}..{ref2}:\n"]
    
    total_add = 0
    total_del = 0
    
    for diff in diffs:
        output_lines.append(f"  {diff.file}: +{diff.additions} -{diff.deletions}")
        total_add += diff.additions
        total_del += diff.deletions
        
    output_lines.append(f"\nTotal: +{total_add} -{total_del} in {len(diffs)} files")
    
    return "\n".join(output_lines)
