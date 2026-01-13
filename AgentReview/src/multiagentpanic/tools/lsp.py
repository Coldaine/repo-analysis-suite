"""
LSP (Language Server Protocol) Tool - MCP Integration

Provides semantic code analysis capabilities via LSP servers.
Enables type-aware code navigation and symbol analysis.

References:
- https://microsoft.github.io/language-server-protocol/
- MCP servers: Sourcerer (Tree-sitter AST + semantic search)
"""

import subprocess
import json
import logging
from typing import Dict, Any, List, Optional, Literal
from dataclasses import dataclass, field
from pathlib import Path
from langchain_core.tools import tool

logger = logging.getLogger(__name__)


@dataclass
class Symbol:
    """A code symbol (function, class, variable, etc.)"""
    name: str
    kind: str  # function, class, variable, method, etc.
    file: str
    line: int
    column: int = 0
    end_line: Optional[int] = None
    end_column: Optional[int] = None
    container: Optional[str] = None  # Parent class/function
    

@dataclass
class Reference:
    """A reference to a symbol"""
    file: str
    line: int
    column: int
    context: str = ""  # Line content


@dataclass 
class Definition:
    """Symbol definition location"""
    file: str
    line: int
    column: int
    kind: str = ""
    documentation: str = ""


class LSPTool:
    """
    Language Server Protocol tool for semantic code analysis.
    
    Provides:
    - Symbol lookup (functions, classes, variables)
    - Find references
    - Go to definition
    - Type information
    """
    
    # Mapping of file extensions to LSP servers
    LANGUAGE_SERVERS = {
        ".py": "pylsp",      # Python Language Server
        ".ts": "typescript-language-server",
        ".js": "typescript-language-server", 
        ".go": "gopls",
        ".rs": "rust-analyzer",
        ".java": "jdtls",
    }
    
    def __init__(self, repo_root: str = "."):
        """
        Initialize LSP tool.
        
        Args:
            repo_root: Root directory of the repository
        """
        self.repo_root = Path(repo_root).resolve()
        self._server_processes: Dict[str, subprocess.Popen] = {}
        
    def _get_language(self, file_path: str) -> Optional[str]:
        """Get language from file extension"""
        ext = Path(file_path).suffix.lower()
        return self.LANGUAGE_SERVERS.get(ext)
    
    def get_symbols(
        self,
        file_path: str,
        symbol_kind: Optional[str] = None
    ) -> List[Symbol]:
        """
        Get all symbols defined in a file.
        
        Args:
            file_path: Path to the file (relative to repo root)
            symbol_kind: Optional filter by kind (function, class, etc.)
            
        Returns:
            List of Symbol objects
        """
        # Fallback to AST-based symbol extraction when LSP unavailable
        return self._extract_symbols_ast(file_path, symbol_kind)
    
    def _extract_symbols_ast(
        self,
        file_path: str,
        symbol_kind: Optional[str] = None
    ) -> List[Symbol]:
        """Extract symbols using AST parsing (fallback when LSP unavailable)"""
        full_path = self.repo_root / file_path
        
        if not full_path.exists():
            logger.warning(f"File not found: {file_path}")
            return []
            
        ext = full_path.suffix.lower()
        
        if ext == ".py":
            return self._extract_python_symbols(full_path, symbol_kind)
        else:
            # For other languages, use regex-based extraction
            return self._extract_symbols_regex(full_path, symbol_kind)
    
    def _extract_python_symbols(
        self,
        file_path: Path,
        symbol_kind: Optional[str] = None
    ) -> List[Symbol]:
        """Extract symbols from Python files using AST"""
        import ast
        
        try:
            content = file_path.read_text(encoding='utf-8', errors='replace')
            tree = ast.parse(content)
        except SyntaxError as e:
            logger.warning(f"Syntax error parsing {file_path}: {e}")
            return []
            
        symbols = []
        relative_path = str(file_path.relative_to(self.repo_root))
        
        for node in ast.walk(tree):
            symbol = None
            
            if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                if symbol_kind and symbol_kind not in ["function", "method"]:
                    continue
                symbol = Symbol(
                    name=node.name,
                    kind="function",
                    file=relative_path,
                    line=node.lineno,
                    column=node.col_offset,
                    end_line=node.end_lineno
                )
                
            elif isinstance(node, ast.ClassDef):
                if symbol_kind and symbol_kind != "class":
                    continue
                symbol = Symbol(
                    name=node.name,
                    kind="class",
                    file=relative_path,
                    line=node.lineno,
                    column=node.col_offset,
                    end_line=node.end_lineno
                )
                
            elif isinstance(node, ast.Assign):
                if symbol_kind and symbol_kind != "variable":
                    continue
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        symbols.append(Symbol(
                            name=target.id,
                            kind="variable",
                            file=relative_path,
                            line=node.lineno,
                            column=node.col_offset
                        ))
                continue
                
            if symbol:
                symbols.append(symbol)
                
        return symbols
    
    def _extract_symbols_regex(
        self,
        file_path: Path,
        symbol_kind: Optional[str] = None
    ) -> List[Symbol]:
        """Extract symbols using regex patterns (language-agnostic fallback)"""
        import re
        
        patterns = {
            "function": [
                r"^\s*(?:async\s+)?def\s+(\w+)",  # Python
                r"^\s*(?:export\s+)?(?:async\s+)?function\s+(\w+)",  # JS/TS
                r"^\s*func\s+(\w+)",  # Go
                r"^\s*fn\s+(\w+)",  # Rust
            ],
            "class": [
                r"^\s*class\s+(\w+)",  # Python, JS/TS
                r"^\s*type\s+(\w+)\s+struct",  # Go
                r"^\s*struct\s+(\w+)",  # Rust
            ]
        }
        
        symbols = []
        relative_path = str(file_path.relative_to(self.repo_root))
        
        try:
            lines = file_path.read_text(encoding='utf-8', errors='replace').split('\n')
        except Exception as e:
            logger.warning(f"Error reading {file_path}: {e}")
            return []
            
        for line_num, line in enumerate(lines, 1):
            for kind, pattern_list in patterns.items():
                if symbol_kind and symbol_kind != kind:
                    continue
                for pattern in pattern_list:
                    match = re.match(pattern, line)
                    if match:
                        symbols.append(Symbol(
                            name=match.group(1),
                            kind=kind,
                            file=relative_path,
                            line=line_num,
                            column=0
                        ))
                        break
                        
        return symbols
    
    def find_references(
        self,
        symbol_name: str,
        file_path: Optional[str] = None
    ) -> List[Reference]:
        """
        Find all references to a symbol.
        
        Args:
            symbol_name: Name of the symbol to find
            file_path: Optional file to search in (searches all files if None)
            
        Returns:
            List of Reference objects
        """
        # Use grep-based search as fallback
        return self._find_references_grep(symbol_name, file_path)
    
    def _find_references_grep(
        self,
        symbol_name: str,
        file_path: Optional[str] = None
    ) -> List[Reference]:
        """Find references using grep"""
        try:
            cmd = ["git", "grep", "-n", "-w", symbol_name]
            if file_path:
                cmd.extend(["--", file_path])
                
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=self.repo_root,
                timeout=30
            )
            
            references = []
            for line in result.stdout.strip().split("\n"):
                if ":" in line:
                    parts = line.split(":", 2)
                    if len(parts) >= 3:
                        references.append(Reference(
                            file=parts[0],
                            line=int(parts[1]) if parts[1].isdigit() else 0,
                            column=0,
                            context=parts[2].strip()
                        ))
                        
            return references
            
        except Exception as e:
            logger.error(f"Reference search failed: {e}")
            return []
    
    def get_definition(
        self,
        symbol_name: str,
        file_path: str,
        line: int
    ) -> Optional[Definition]:
        """
        Get the definition location of a symbol.
        
        Args:
            symbol_name: Name of the symbol
            file_path: File where symbol is used
            line: Line number where symbol is used
            
        Returns:
            Definition object or None if not found
        """
        # Search for definition patterns
        patterns = [
            f"def {symbol_name}",
            f"class {symbol_name}",
            f"async def {symbol_name}",
            f"{symbol_name} = ",
            f"function {symbol_name}",
        ]
        
        for pattern in patterns:
            refs = self._find_references_grep(pattern)
            for ref in refs:
                # Return first match that looks like a definition
                if "def " in ref.context or "class " in ref.context or " = " in ref.context:
                    return Definition(
                        file=ref.file,
                        line=ref.line,
                        column=ref.column,
                        kind="definition"
                    )
                    
        return None


# Global instance
_lsp_tool: Optional[LSPTool] = None


def get_lsp_tool(repo_root: str = ".") -> LSPTool:
    """Get or create the global LSP tool instance"""
    global _lsp_tool
    if _lsp_tool is None:
        _lsp_tool = LSPTool(repo_root=repo_root)
    return _lsp_tool


@tool
def lsp_get_symbols(file_path: str, kind: str = "") -> str:
    """
    Get all symbols (functions, classes, variables) defined in a file.
    
    Use this to understand the structure of a file and what it defines.
    
    Args:
        file_path: Path to the file (relative to repo root)
        kind: Optional filter by symbol kind: "function", "class", "variable"
        
    Returns:
        Formatted list of symbols with their types and locations
    """
    tool = get_lsp_tool()
    symbols = tool.get_symbols(file_path, kind if kind else None)
    
    if not symbols:
        return f"No symbols found in {file_path}"
    
    output_lines = [f"Symbols in {file_path}:\n"]
    
    for sym in symbols:
        output_lines.append(f"  [{sym.kind}] {sym.name} - line {sym.line}")
        
    return "\n".join(output_lines)


@tool
def lsp_get_references(symbol_name: str, file_path: str = "") -> str:
    """
    Find all references to a symbol in the codebase.
    
    Use this to understand how a function/class/variable is used.
    
    Args:
        symbol_name: Name of the symbol to find references for
        file_path: Optional file to limit search to
        
    Returns:
        List of files and lines where the symbol is referenced
    """
    tool = get_lsp_tool()
    references = tool.find_references(symbol_name, file_path if file_path else None)
    
    if not references:
        return f"No references found for: {symbol_name}"
    
    output_lines = [f"Found {len(references)} references to '{symbol_name}':\n"]
    
    for ref in references[:50]:  # Limit output
        output_lines.append(f"  {ref.file}:{ref.line}: {ref.context[:80]}")
        
    if len(references) > 50:
        output_lines.append(f"\n  ... and {len(references) - 50} more")
        
    return "\n".join(output_lines)


@tool
def lsp_get_definition(symbol_name: str, file_path: str, line: int) -> str:
    """
    Get the definition location of a symbol.
    
    Use this to find where a function/class/variable is defined.
    
    Args:
        symbol_name: Name of the symbol
        file_path: File where the symbol is used
        line: Line number where symbol appears
        
    Returns:
        Location of the symbol's definition
    """
    tool = get_lsp_tool()
    definition = tool.get_definition(symbol_name, file_path, line)
    
    if not definition:
        return f"Definition not found for: {symbol_name}"
    
    return f"Definition of '{symbol_name}' found at:\n  {definition.file}:{definition.line}"
