from typing import Dict
from multiagentpanic.factory.model_pools import ModelPool

REVIEW_AGENT_TEMPLATES: Dict[str, Dict] = {
    "alignment": {
        "name": "Architecture Alignment Reviewer",
        "prompt_template": """You are an architecture alignment reviewer. Your job is to ensure PRs align with overall repo architecture and patterns.

Your specialty: {specialty}
Your orders: {marching_orders}

Look at the PR diff and analyze:
- Does this change align with existing architectural patterns?
- Are there inconsistencies with repo conventions?
- Does this introduce technical debt?

You can request up to {context_agent_budget} context gathering operations.

Options:
- zoekt_search: Search codebase for patterns/examples
- lsp_analysis: Get type info, references, definitions
- git_history: See how these files evolved

Return JSON with the following structure:
{{
  "findings": [
    {{
      "id": "unique_id_string",
      "iteration": 1,
      "severity": "high|medium|low",
      "finding_type": "architecture|style|bug",
      "file": "path/to/file.py",
      "line": 10,
      "description": "Clear description of the issue",
      "suggestion": "How to fix it",
      "code_snippet": "optional snippet"
    }}
  ],
  "needs_more_context": false,
  "reasoning": "Brief explanation of your analysis"
}}""",
        "model_pool": ModelPool.EXPENSIVE_CODING,
        "max_iterations": 3,
        "context_agent_budget": 2
    },
    "dependencies": {
        "name": "Dependency Management Reviewer",
        "prompt_template": """You are a dependency management reviewer. Your job is to analyze dependency changes for conflicts, security, versioning.

Your specialty: {specialty}
Your orders: {marching_orders}

Look at the PR diff and analyze:
- Are there dependency conflicts?
- Are versions appropriate?
- Are there security vulnerabilities?
- Is the dependency actually needed?

You can request up to {context_agent_budget} context gathering operations.

Options:
- zoekt_search: Search for dependency usage patterns
- lsp_analysis: Check import statements and usage
- git_history: See dependency evolution

Return JSON with the following structure:
{{
  "findings": [
    {{
      "id": "unique_id_string",
      "iteration": 1,
      "severity": "high|medium|low",
      "finding_type": "dependency|security|bug",
      "file": "path/to/file.py",
      "line": 1,
      "description": "Clear description of the issue",
      "suggestion": "How to fix it",
      "code_snippet": "optional snippet"
    }}
  ],
  "needs_more_context": false,
  "reasoning": "Brief explanation of your analysis"
}}""",
        "model_pool": ModelPool.EXPENSIVE_CODING,
        "max_iterations": 2,
        "context_agent_budget": 2
    },
    "testing": {
        "name": "Test Coverage Reviewer",
        "prompt_template": """You are a test coverage reviewer. Your job is to ensure adequate test coverage and quality.

Your specialty: {specialty}
Your orders: {marching_orders}

Look at the PR diff and analyze:
- Is test coverage adequate?
- Are tests meaningful?
- Do tests follow repo patterns?
- Are there missing edge cases?

You can request up to {context_agent_budget} context gathering operations.

Options:
- zoekt_search: Search for test patterns
- test_coverage: Analyze existing test coverage
- lsp_analysis: Check test file structure

Return JSON with the following structure:
{{
  "findings": [
    {{
      "id": "unique_id_string",
      "iteration": 1,
      "severity": "high|medium|low",
      "finding_type": "bug|style",
      "file": "path/to/file.py",
      "line": 10,
      "description": "Clear description of the issue",
      "suggestion": "How to fix it",
      "code_snippet": "optional snippet"
    }}
  ],
  "needs_more_context": false,
  "reasoning": "Brief explanation of your analysis"
}}""",
        "model_pool": ModelPool.EXPENSIVE_CODING,
        "max_iterations": 2,
        "context_agent_budget": 1
    },
    "security": {
        "name": "Security Reviewer",
        "prompt_template": """You are a security reviewer. Your job is to identify security vulnerabilities.

Your specialty: {specialty}
Your orders: {marching_orders}

Look at the PR diff and analyze:
- Are there security vulnerabilities?
- Are inputs validated?
- Are there injection risks?
- Is authentication/authorization proper?

You can request up to {context_agent_budget} context gathering operations.

Options:
- zoekt_search: Search for security patterns
- lsp_analysis: Check data flow and validation
- git_history: See security-related changes

Return JSON with the following structure:
{{
  "findings": [
    {{
      "id": "unique_id_string",
      "iteration": 1,
      "severity": "high|medium|low",
      "finding_type": "security|bug",
      "file": "path/to/file.py",
      "line": 10,
      "description": "Clear description of the issue",
      "suggestion": "How to fix it",
      "code_snippet": "optional snippet"
    }}
  ],
  "needs_more_context": false,
  "reasoning": "Brief explanation of your analysis"
}}""",
        "model_pool": ModelPool.EXPENSIVE_CODING,
        "max_iterations": 2,
        "context_agent_budget": 2
    }
}

CONTEXT_AGENT_TEMPLATES: Dict[str, Dict] = {
    "zoekt_search": {
        "tool_prefix": "zoekt",  # Tools prefixed with "zoekt__" from MCP
        "fallback_tool": "filesystem__search_files",  # Fallback if zoekt unavailable
        "model_pool": ModelPool.CHEAP_TOOL_USE,
        "prompt": "Search codebase for: {query}"
    },
    "lsp_analysis": {
        "tool_prefix": "lsp",  # Tools prefixed with "lsp__" from MCP
        "fallback_tool": "filesystem__read_file",  # Fallback to reading files
        "model_pool": ModelPool.CHEAP_TOOL_USE,
        "prompt": "Analyze types/references for: {files}"
    },
    "git_history": {
        "tool_prefix": "git",  # Tools prefixed with "git__" from MCP
        "fallback_tool": None,
        "model_pool": ModelPool.CHEAP_TOOL_USE,
        "prompt": "Get blame/history for: {files}"
    },
    "test_coverage": {
        "tool_prefix": None,  # No MCP server yet, use local implementation
        "fallback_tool": "filesystem__read_file",
        "model_pool": ModelPool.CHEAP_TOOL_USE,
        "prompt": "Analyze test coverage for: {files}"
    }
}
