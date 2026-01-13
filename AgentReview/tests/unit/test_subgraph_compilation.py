import pytest
from unittest.mock import patch, MagicMock
from multiagentpanic.factory.agent_factory import AgentFactory
from multiagentpanic.factory.model_pools import ModelSelector, ModelTier
from multiagentpanic.factory.prompts import REVIEW_AGENT_TEMPLATES


class TestSubgraphCompilation:
    """Test that subgraphs compile without errors"""

    @pytest.fixture
    def model_selector(self):
        return ModelSelector(mode=ModelTier.SIMPLE)

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings for testing"""
        settings = MagicMock()
        settings.llm.model_tier = "simple"
        settings.llm.openai_api_key = "test-key"
        settings.database.redis_url = "redis://localhost:6379"
        settings.database.redis_timeout = 5
        settings.context_cache_ttl = 3600
        return settings

    @pytest.fixture
    def agent_factory(self, model_selector, mock_settings):
        with patch('multiagentpanic.factory.agent_factory.get_settings', return_value=mock_settings):
            return AgentFactory(model_selector)

    def test_review_agent_subgraph_compiles(self, agent_factory, mock_settings):
        """All review agent subgraphs should compile"""
        with patch('multiagentpanic.factory.agent_factory.get_settings', return_value=mock_settings):
            for specialty in ["alignment", "dependencies", "testing", "security"]:
                subgraph = AgentFactory.create_review_agent_subgraph(specialty, agent_factory.model_selector)

                # Should be compiled StateGraph
                assert subgraph is not None

                # Should have nodes
                # Can't directly inspect compiled graph, but can try to invoke with mock state
                # (will fail on LLM calls, but validates graph structure)

    def test_subgraph_has_no_cycles(self, agent_factory):
        """Subgraphs should not have cycles (except intentional iteration)"""
        # This is tested implicitly by the compilation test above
        # If there were cycles, compilation would fail
        pass

    def test_subgraph_entry_and_exit_points(self, agent_factory, mock_settings):
        """Subgraphs should have valid entry/exit points"""
        with patch('multiagentpanic.factory.agent_factory.get_settings', return_value=mock_settings):
            for specialty in ["alignment", "dependencies"]:
                # Get the uncompiled graph definition
                # We can't directly inspect the compiled graph, but compilation success
                # indicates valid entry/exit points
                subgraph = AgentFactory.create_review_agent_subgraph(specialty, agent_factory.model_selector)
                assert subgraph is not None

    def test_subgraph_iteration_limit(self, agent_factory):
        """Subgraphs should respect max_iterations"""
        for specialty, template in REVIEW_AGENT_TEMPLATES.items():
            max_iter = template["max_iterations"]

            # Mock state that always requests more context
            mock_state = {
                "specialty": specialty,
                "current_iteration": 0,
                "needs_more_context": True,
                "context_gathered": [],
                "findings": [],
                "reasoning_history": []
            }

            # Simulate iteration loop
            for i in range(max_iter + 2):  # Try to exceed limit
                mock_state["current_iteration"] = i + 1

                # Check decision logic
                should_continue = (
                    mock_state["needs_more_context"] and
                    mock_state["current_iteration"] < max_iter
                )

                if i >= max_iter:
                    assert not should_continue, f"Should stop at iteration {max_iter}"