import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from multiagentpanic.factory.agent_factory import AgentFactory
from multiagentpanic.factory.model_pools import ModelSelector, ModelTier, ModelPool
from multiagentpanic.factory.prompts import REVIEW_AGENT_TEMPLATES, CONTEXT_AGENT_TEMPLATES
from multiagentpanic.domain.schemas import ReviewAgentState
import inspect


class TestNodeCreation:
    """Test that nodes are created correctly from templates"""

    @pytest.fixture
    def model_selector(self):
        return ModelSelector(mode=ModelTier.SIMPLE)

    def test_review_agent_node_creation(self):
        """Review agent nodes should be created with correct signature"""
        # Create nodes
        plan_node = AgentFactory._review_agent_plan
        spawn_node = AgentFactory._spawn_context_agents
        analyze_node = AgentFactory._review_agent_analyze
        finalize_node = AgentFactory._review_agent_finalize

        # Verify signatures (they should accept state, factory, template)
        plan_sig = inspect.signature(plan_node)
        assert len(plan_sig.parameters) == 3  # state, factory, template
        assert list(plan_sig.parameters.keys()) == ["state", "factory", "template"]

    @pytest.mark.asyncio
    @patch('multiagentpanic.factory.llm_factory.LLMFactory.get_llm')
    async def test_node_state_type_compatibility(self, mock_get_llm):
        """Nodes should accept correct state types"""
        template = REVIEW_AGENT_TEMPLATES["alignment"]

        # Mock the LLM (async)
        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = Mock(content='{"context_requests": [], "reasoning": "test"}')
        mock_get_llm.return_value = mock_llm

        # Create a mock factory
        mock_factory = MagicMock(spec=AgentFactory)
        mock_factory.get_model_for_agent.return_value = "gpt-4o"
        mock_factory.llm_factory = MagicMock()
        mock_factory.llm_factory.get_llm = AsyncMock(return_value=mock_llm)

        # Create a proper ReviewAgentState
        from multiagentpanic.domain.schemas import PRMetadata
        pr_metadata = PRMetadata(
            pr_number=1,
            pr_url="https://github.com/test/repo/pull/1",
            pr_branch="feature",
            base_branch="main",
            pr_title="Test PR",
            pr_complexity="simple"
        )

        mock_state = ReviewAgentState(
            pr_metadata=pr_metadata,
            pr_diff="test diff",
            changed_files=[],
            repo_memory={},
            specialty="alignment",
            agent_id="test-agent",
            marching_orders="test"
        )

        # These should not raise type errors (async call)
        result = await AgentFactory._review_agent_plan(mock_state, mock_factory, template)
        # If it returns, structure is valid
        assert isinstance(result, dict)
        assert "context_requests_this_iteration" in result

    @patch('multiagentpanic.factory.agent_factory.get_settings')
    def test_factory_handles_template_modifications(self, mock_get_settings, model_selector):
        """Factory should work even if templates are modified"""
        # Mock settings
        mock_settings = MagicMock()
        mock_settings.llm.model_tier = "simple"
        mock_settings.llm.openai_api_key = "test-key"
        mock_settings.database.redis_url = "redis://localhost:6379"
        mock_settings.database.redis_timeout = 5
        mock_settings.context_cache_ttl = 3600
        mock_get_settings.return_value = mock_settings

        # Add a new template
        REVIEW_AGENT_TEMPLATES["experimental"] = {
            "name": "Experimental Reviewer",
            "prompt_template": "You are experimental",
            "model_pool": ModelPool.EXPENSIVE_CODING,
            "max_iterations": 2,
            "context_agent_budget": 1
        }

        # Should still work
        subgraph = AgentFactory.create_review_agent_subgraph("experimental", model_selector)
        assert subgraph is not None

        # Cleanup
        del REVIEW_AGENT_TEMPLATES["experimental"]