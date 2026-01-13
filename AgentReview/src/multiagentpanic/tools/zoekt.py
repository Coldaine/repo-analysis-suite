"""
Zoekt Code Search Tool - MCP Integration

Zoekt is a fast text search engine for source code, originally from Google.
This tool provides code search capabilities for context agents.

References:
- https://github.com/sourcegraph/zoekt
- MCP server: Acemcp (89.6K downloads) for incremental indexing
"""

import subprocess
import json
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from langchain_core.tools import tool

logger = logging.getLogger(__name__)


@dataclass
class ZoektSearchResult:
    """A single search result from Zoekt"""
    file: str
    line: int
    content: str
    score: float
    repository: str = ""
    

@dataclass
class ZoektSearchResponse:
    """Complete response from Zoekt search"""
    results: List[ZoektSearchResult]
    total_matches: int
    files_searched: int
    duration_ms: float


class ZoektTool:
    """
    Zoekt code search tool for fast codebase-wide text search.
    
    Supports:
    - Regex pattern matching
    - File type filtering
    - Repository filtering
    - Case sensitivity options
    """
    
    def __init__(self, zoekt_url: str = "http://localhost:6070", repo_root: str = "."):
        """
        Initialize Zoekt tool.
        
        Args:
            zoekt_url: URL of the Zoekt web server
            repo_root: Root directory of the repository
        """
        self.zoekt_url = zoekt_url
        self.repo_root = repo_root
        self._available = None
    
    def is_available(self) -> bool:
        """Check if Zoekt server is available"""
        if self._available is not None:
            return self._available
            
        try:
            import requests
            response = requests.get(f"{self.zoekt_url}/api/search", timeout=2)
            self._available = response.status_code in [200, 400]  # 400 = missing query, but server is up
        except Exception:
            self._available = False
            
        return self._available
    
    def search(
        self,
        query: str,
        file_pattern: Optional[str] = None,
        repo_filter: Optional[str] = None,
        max_results: int = 50,
        case_sensitive: bool = False
    ) -> ZoektSearchResponse:
        """
        Search codebase using Zoekt.
        
        Args:
            query: Search query (supports regex)
            file_pattern: Filter by file pattern (e.g., "*.py")
            repo_filter: Filter by repository name
            max_results: Maximum number of results to return
            case_sensitive: Whether search is case sensitive
            
        Returns:
            ZoektSearchResponse with search results
        """
        if not self.is_available():
            # Fallback to git grep
            return self._fallback_search(query, file_pattern, max_results)
        
        try:
            import requests
            
            # Build Zoekt query
            zoekt_query = query
            if file_pattern:
                zoekt_query = f"file:{file_pattern} {zoekt_query}"
            if repo_filter:
                zoekt_query = f"repo:{repo_filter} {zoekt_query}"
            if case_sensitive:
                zoekt_query = f"case:yes {zoekt_query}"
                
            params = {
                "q": zoekt_query,
                "num": max_results,
                "format": "json"
            }
            
            response = requests.get(
                f"{self.zoekt_url}/api/search",
                params=params,
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            
            results = []
            for file_match in data.get("FileMatches", []):
                for line_match in file_match.get("LineMatches", []):
                    results.append(ZoektSearchResult(
                        file=file_match.get("FileName", ""),
                        line=line_match.get("LineNumber", 0),
                        content=line_match.get("Line", ""),
                        score=file_match.get("Score", 0.0),
                        repository=file_match.get("Repository", "")
                    ))
                    
            return ZoektSearchResponse(
                results=results[:max_results],
                total_matches=data.get("MatchCount", len(results)),
                files_searched=data.get("FilesConsidered", 0),
                duration_ms=data.get("Duration", 0) / 1_000_000  # ns to ms
            )
            
        except Exception as e:
            logger.warning(f"Zoekt search failed: {e}, falling back to git grep")
            return self._fallback_search(query, file_pattern, max_results)
    
    def _fallback_search(
        self,
        query: str,
        file_pattern: Optional[str] = None,
        max_results: int = 50
    ) -> ZoektSearchResponse:
        """Fallback to git grep when Zoekt is unavailable"""
        try:
            cmd = ["git", "grep", "-n", "-I", "--no-color"]
            
            if file_pattern:
                cmd.extend(["--", file_pattern])
            
            cmd.append(query)
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=self.repo_root,
                timeout=30
            )
            
            results = []
            for line in result.stdout.strip().split("\n")[:max_results]:
                if ":" in line:
                    parts = line.split(":", 2)
                    if len(parts) >= 3:
                        results.append(ZoektSearchResult(
                            file=parts[0],
                            line=int(parts[1]) if parts[1].isdigit() else 0,
                            content=parts[2],
                            score=1.0
                        ))
                        
            return ZoektSearchResponse(
                results=results,
                total_matches=len(results),
                files_searched=0,
                duration_ms=0
            )
            
        except Exception as e:
            logger.error(f"Fallback search failed: {e}")
            return ZoektSearchResponse(
                results=[],
                total_matches=0,
                files_searched=0,
                duration_ms=0
            )


# Global instance for convenience
_zoekt_tool: Optional[ZoektTool] = None


def get_zoekt_tool(repo_root: str = ".") -> ZoektTool:
    """Get or create the global Zoekt tool instance"""
    global _zoekt_tool
    if _zoekt_tool is None:
        _zoekt_tool = ZoektTool(repo_root=repo_root)
    return _zoekt_tool


@tool
def zoekt_search(
    query: str,
    file_pattern: str = "",
    max_results: int = 20
) -> str:
    """
    Search the codebase for code matching the query pattern.
    
    Use this to find:
    - Function definitions and usages
    - Class implementations
    - Import statements
    - Configuration patterns
    - Similar code snippets
    
    Args:
        query: Search pattern (supports regex)
        file_pattern: Optional file filter (e.g., "*.py", "test_*.py")
        max_results: Maximum results to return (default 20)
        
    Returns:
        Formatted search results with file paths, line numbers, and content
    """
    tool = get_zoekt_tool()
    response = tool.search(
        query=query,
        file_pattern=file_pattern if file_pattern else None,
        max_results=max_results
    )
    
    if not response.results:
        return f"No matches found for: {query}"
    
    output_lines = [f"Found {response.total_matches} matches:\n"]
    
    for result in response.results:
        output_lines.append(f"{result.file}:{result.line}: {result.content.strip()}")
    
    return "\n".join(output_lines)
