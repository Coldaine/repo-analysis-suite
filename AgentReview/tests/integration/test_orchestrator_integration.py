import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from multiagentpanic.agents.orchestrator import create_orchestrator_for_testing
from multiagentpanic.domain.schemas import PRReviewState, PRMetadata


@pytest.fixture
def mock_settings():
    """Mock settings to bypass API key validation"""
    settings = MagicMock()
    settings.llm.model_tier = "simple"
    settings.llm.openai_api_key = "test-key"
    settings.database.redis_url = "redis://localhost:6379"
    settings.database.redis_timeout = 5
    settings.context_cache_ttl = 3600
    return settings


@pytest.fixture
def dummy_repo_path():
    return Path("tests/dummy_repo").resolve()


def test_orchestrator_initialization(dummy_repo_path, mock_settings):
    """Test orchestrator initializes correctly"""
    with patch('multiagentpanic.factory.agent_factory.get_settings', return_value=mock_settings), \
         patch('multiagentpanic.tools.mcp_tools.get_settings', return_value=mock_settings):
        orchestrator = create_orchestrator_for_testing()
        assert orchestrator.graph is not None
        assert orchestrator.model_selector is not None
        assert hasattr(orchestrator, 'factory')
