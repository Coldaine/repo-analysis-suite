"""
Pytest fixtures for MultiagentPanic2 testing infrastructure.
This file provides shared fixtures for testing the multi-agent PR review system.
"""

import os
from unittest.mock import MagicMock, Mock

import pytest
from langgraph.checkpoint.memory import MemorySaver

from multiagentpanic.domain.schemas import PRMetadata


# ═══════════════════════════════════════════════════════════════
# FIXTURE: mock_settings (auto-use for all tests)
# ═══════════════════════════════════════════════════════════════
@pytest.fixture(autouse=True)
def mock_settings(monkeypatch, request):
    """
    Auto-use fixture that sets mock environment variables for LLM API keys.
    This prevents configuration validation errors in unit tests.
    Skips mocking for integration tests to allow live execution.
    """
    # Skip for integration tests
    if "integration" in str(request.path):
        yield
        return

    monkeypatch.setenv("LLM_OPENAI_API_KEY", "sk-test-fake-key-for-unit-testing")
    monkeypatch.setenv("LLM_PRIMARY_PROVIDER", "openai")

    # Reset the settings singleton before each test
    from multiagentpanic.config import settings as settings_module

    settings_module._settings_instance = None

    yield

    # Clean up after test
    settings_module._settings_instance = None


# ═══════════════════════════════════════════════════════════════
# FIXTURE: mock_pr_data
# ═══════════════════════════════════════════════════════════════
@pytest.fixture(scope="session")
def mock_pr_data():
    """
    Pydantic models simulating GitHub PR data.
    Uses dummy_repo/src/bad_code.py for diff content.
    """
    # Read the bad_code.py content from dummy_repo
    bad_code_path = os.path.join(
        os.path.dirname(__file__), "dummy_repo", "src", "bad_code.py"
    )

    # Read the file content (handle binary/encoding issues)
    try:
        with open(bad_code_path, "r", encoding="utf-8", errors="replace") as f:
            pr_diff_content = f.read()
    except Exception:
        # Fallback to a simple diff if file reading fails
        pr_diff_content = """class AbstractFactoryBuilderManager:
    def __init__(self, factory):
        self.factory = factory

    def build(self, data):
        # TODO: Refactor this later
        try:
            return self.factory.create_item(data)
        except Exception:
            pass  # Swallow error to keep running
"""

    # Create PR metadata
    pr_metadata = PRMetadata(
        pr_number=123,
        pr_url="https://github.com/owner/repo/pull/123",
        pr_branch="feature-branch",
        base_branch="main",
        pr_title="Add new feature for user authentication",
        pr_complexity="medium",
        pr_body="This PR adds a new authentication system with proper error handling.",
        pr_diff=pr_diff_content,
    )

    return {
        "pr_metadata": pr_metadata,
        "pr_diff": pr_diff_content,
        "changed_files": ["src/auth.py", "tests/test_auth.py"],
        "repo": "owner/repo",
        "pr": 123,
    }


# ═══════════════════════════════════════════════════════════════
# FIXTURE: memory_saver
# ═══════════════════════════════════════════════════════════════
@pytest.fixture(scope="session")
def memory_saver():
    """
    langgraph.checkpoint.memory.MemorySaver() instance for testing.
    """
    return MemorySaver()


# ═══════════════════════════════════════════════════════════════
# FIXTURE: mock_github
# ═══════════════════════════════════════════════════════════════
@pytest.fixture(scope="session")
def mock_github():
    """
    Mock GitHub client/API for PR fetch and comments using unittest.mock.
    """
    mock_client = Mock()

    # Mock PR data
    mock_pr_data = {
        "number": 123,
        "title": "Add new feature for user authentication",
        "body": "This PR adds a new authentication system with proper error handling.",
        "head": {"ref": "feature-branch"},
        "base": {"ref": "main"},
        "user": {"login": "testuser"},
        "html_url": "https://github.com/owner/repo/pull/123",
    }

    # Mock comments
    mock_comments = [
        {
            "id": 1,
            "user": {"login": "reviewer1"},
            "body": "This looks good overall!",
            "created_at": "2023-01-01T00:00:00Z",
        },
        {
            "id": 2,
            "user": {"login": "reviewer2"},
            "body": "Could you add more tests?",
            "created_at": "2023-01-02T00:00:00Z",
        },
    ]

    # Setup mock methods
    mock_client.get_pull_request.return_value = mock_pr_data
    mock_client.get_comments.return_value = mock_comments
    mock_client.create_comment.return_value = {"id": 3, "body": "Test comment"}

    return mock_client


# ═══════════════════════════════════════════════════════════════
# FIXTURE: mock_mcp
# ═══════════════════════════════════════════════════════════════
@pytest.fixture(scope="session")
def mock_mcp():
    """
    Mock MCP tools (Zoekt search, LSP symbols, Git history) returning dummy data.
    """
    mock_mcp_client = MagicMock()

    # Mock Zoekt search results
    zoekt_results = {
        "results": [
            {
                "repository": "owner/repo",
                "file": "src/auth.py",
                "line": 10,
                "content": "def authenticate_user(username, password):",
                "score": 0.95,
            }
        ],
        "stats": {"total_files_searched": 100, "total_matches": 1, "duration_ms": 45},
    }

    # Mock LSP symbols
    lsp_symbols = {
        "symbols": [
            {
                "name": "authenticate_user",
                "kind": "function",
                "location": {
                    "uri": "file:///src/auth.py",
                    "range": {
                        "start": {"line": 9, "character": 0},
                        "end": {"line": 15, "character": 20},
                    },
                },
            }
        ],
        "diagnostics": [],
    }

    # Mock Git history
    git_history = {
        "commits": [
            {
                "sha": "abc123",
                "message": "Initial auth implementation",
                "author": "testuser",
                "date": "2023-01-01T00:00:00Z",
            }
        ],
        "file_history": {"src/auth.py": [{"commit": "abc123", "changes": "+10 -0"}]},
    }

    # Setup mock methods
    mock_mcp_client.zoekt_search.return_value = zoekt_results
    mock_mcp_client.lsp_symbols.return_value = lsp_symbols
    mock_mcp_client.git_history.return_value = git_history

    # Mock file reading from dummy_repo
    def mock_read_file(filepath):
        if "bad_code.py" in filepath:
            try:
                with open(
                    os.path.join(
                        os.path.dirname(__file__), "dummy_repo", "src", "bad_code.py"
                    ),
                    "r",
                    encoding="utf-8",
                    errors="replace",
                ) as f:
                    return f.read()
            except:
                return """class AbstractFactoryBuilderManager:
    def __init__(self, factory):
        self.factory = factory
"""

        return f"Mock content for {filepath}"

    mock_mcp_client.read_file.side_effect = mock_read_file

    return mock_mcp_client
