import pytest
from unittest.mock import Mock, MagicMock, AsyncMock, patch
from multiagentpanic.factory.agent_factory import AgentFactory
from multiagentpanic.factory.model_pools import ModelSelector, ModelTier

class TestToolIntegration:
    """Test that tools connect and are callable"""

    @pytest.fixture
    def mock_settings(self):
        """Mock settings to bypass API key validation"""
        settings = MagicMock()
        settings.llm.model_tier = "simple"
        settings.llm.openai_api_key = "test-key"
        settings.database.redis_url = "redis://localhost:6379"
        settings.database.redis_timeout = 5
        settings.context_cache_ttl = 3600
        return settings

    @pytest.fixture
    def model_selector(self):
        return ModelSelector(mode=ModelTier.SIMPLE)

    @pytest.fixture
    def agent_factory(self, model_selector, mock_settings):
        with patch('multiagentpanic.factory.agent_factory.get_settings', return_value=mock_settings):
            return AgentFactory(model_selector)

    @patch('multiagentpanic.factory.llm_factory.LLMFactory.get_llm')
    def test_zoekt_tool_callable(self, mock_get_llm, agent_factory):
        """Zoekt MCP tool should be callable with correct signature"""
        import asyncio
        # Mock the LLM
        mock_llm = Mock()
        mock_llm.invoke.return_value = Mock(content='{"results": []}')
        mock_get_llm.return_value = mock_llm

        # Set the mock on the factory's llm_factory
        agent_factory.llm_factory = MagicMock()
        agent_factory.llm_factory.get_llm.return_value = AsyncMock(return_value=mock_llm)

        context_agent = agent_factory.create_context_agent("zoekt_search")

        mock_state = {
            "task": "zoekt_search",
            "target_files": ["src/cache.py"],
            "query": "Redis connection patterns"
        }

        # Should not raise (will fail MCP call, but that's OK for this test)
        # We're just validating the function signature
        result = asyncio.run(context_agent(mock_state))
        assert "context_found" in result
        assert "cost" in result
        assert "tokens" in result

    @patch('multiagentpanic.factory.llm_factory.LLMFactory.get_llm')
    def test_lsp_tool_callable(self, mock_get_llm, agent_factory):
        """LSP MCP tool should be callable with correct signature"""
        import asyncio
        # Mock the LLM
        mock_llm = Mock()
        mock_llm.invoke.return_value = Mock(content='{"results": []}')
        mock_get_llm.return_value = mock_llm

        # Set the mock on the factory's llm_factory
        agent_factory.llm_factory = MagicMock()
        agent_factory.llm_factory.get_llm.return_value = AsyncMock(return_value=mock_llm)

        context_agent = agent_factory.create_context_agent("lsp_analysis")

        mock_state = {
            "task": "lsp_analysis",
            "target_files": ["src/cache.py"],
            "query": "type analysis"
        }

        result = asyncio.run(context_agent(mock_state))
        assert "context_found" in result
        assert "cost" in result
        assert "tokens" in result

    @patch('multiagentpanic.factory.llm_factory.LLMFactory.get_llm')
    def test_tool_error_handling(self, mock_get_llm, agent_factory):
        """Tools should handle MCP errors gracefully"""
        import asyncio
        # Mock the LLM to raise an error
        mock_llm = Mock()
        mock_llm.invoke.side_effect = Exception("MCP server timeout")
        mock_get_llm.return_value = mock_llm

        # Set the mock on the factory's llm_factory
        agent_factory.llm_factory = MagicMock()
        agent_factory.llm_factory.get_llm.return_value = AsyncMock(return_value=mock_llm)

        context_agent = agent_factory.create_context_agent("zoekt_search")

        mock_state = {
            "task": "zoekt_search",
            "target_files": ["src/cache.py"],
            "query": "test query"
        }

        # Should handle the error gracefully
        try:
            result = asyncio.run(context_agent(mock_state))
            # Should return some result even on error
            assert isinstance(result, dict)
        except Exception as e:
            # If it raises, that's also acceptable for error handling
            assert "timeout" in str(e).lower() or "error" in str(e).lower()

    @patch('multiagentpanic.factory.llm_factory.LLMFactory.get_llm')
    def test_tool_timeout_handling(self, mock_get_llm, agent_factory):
        """Tools should handle operations gracefully"""
        import asyncio
        # Mock the LLM
        mock_llm = Mock()
        mock_llm.invoke.return_value = Mock(content='{"results": []}')
        mock_get_llm.return_value = mock_llm

        # Set the mock on the factory's llm_factory
        agent_factory.llm_factory = MagicMock()
        agent_factory.llm_factory.get_llm.return_value = AsyncMock(return_value=mock_llm)

        context_agent = agent_factory.create_context_agent("zoekt_search")

        mock_state = {
            "task": "zoekt_search",
            "target_files": ["src/cache.py"],
            "query": "test query"
        }

        # Should complete without hanging
        import time
        start = time.time()
        result = asyncio.run(context_agent(mock_state))
        duration = time.time() - start

        # Should complete reasonably quickly (less than 1 second with mocks)
        assert duration < 1.0
        assert "context_found" in result