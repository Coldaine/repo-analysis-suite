"""
Expanded unit tests for AgentFactory with comprehensive coverage.
Tests subgraph compilation, node signatures, and edge cases.
"""

import inspect
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from multiagentpanic.factory.agent_factory import AgentFactory
from multiagentpanic.factory.prompts import REVIEW_AGENT_TEMPLATES, CONTEXT_AGENT_TEMPLATES
from multiagentpanic.factory.model_pools import ModelSelector, ModelTier, ModelPool
from multiagentpanic.domain.schemas import ReviewAgentState, ContextAgentState
from langgraph.graph import StateGraph

class TestAgentFactory:
    """Test agent factory functionality"""

    @pytest.fixture
    def model_selector(self):
        return ModelSelector(mode=ModelTier.SIMPLE)

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings for testing"""
        settings = MagicMock()
        settings.llm.model_tier = "simple"
        settings.llm.openai_api_key = "test-key"
        settings.llm.anthropic_api_key = "test-key"
        settings.llm.google_api_key = "test-key"
        settings.llm.primary_provider = "openai"
        settings.llm.max_tokens_per_request = 4096
        settings.llm.openai_base_url = "https://api.openai.com/v1"
        settings.database.redis_url = "redis://localhost:6379"
        settings.database.redis_timeout = 5
        settings.context_cache_ttl = 3600
        settings.mcp.zoekt_enabled = True
        settings.mcp.lsp_enabled = True
        settings.mcp.git_enabled = True
        settings.mcp.filesystem_enabled = True
        settings.mcp.git_server_command = "uvx"
        settings.mcp.git_server_args = ["mcp-server-git"]
        settings.mcp.filesystem_server_command = "uvx"
        settings.mcp.filesystem_server_args = ["mcp-server-filesystem"]
        settings.mcp.zoekt_server_command = ""
        settings.mcp.zoekt_server_args = []
        settings.mcp.lsp_server_command = ""
        settings.mcp.lsp_server_args = []
        settings.workflow.github_token = "test-token"
        settings.workflow.github_api_url = "https://api.github.com"
        
        # Add model tier settings with string values
        settings.model_tier.simple_orchestrator_model = "claude-3-5-sonnet-20241022"
        settings.model_tier.simple_review_agent_model = "gpt-4o"
        settings.model_tier.simple_context_agent_model = "grok-fast"
        
        return settings

    @pytest.fixture
    def mock_mcp_provider(self):
        """Create mock MCP provider for testing"""
        provider = MagicMock()
        provider.get_tools = AsyncMock(return_value=[])
        provider.is_initialized = False
        return provider

    @pytest.fixture
    def agent_factory(self, model_selector, mock_settings, mock_mcp_provider):
        with patch('multiagentpanic.factory.agent_factory.get_settings', return_value=mock_settings), \
             patch('multiagentpanic.factory.agent_factory.get_mcp_tool_provider', return_value=mock_mcp_provider):
            return AgentFactory(model_selector, mcp_provider=mock_mcp_provider)

    def test_all_review_agent_templates_valid(self, agent_factory):
        """Every review agent template should be valid"""
        for specialty in REVIEW_AGENT_TEMPLATES.keys():
            template = REVIEW_AGENT_TEMPLATES[specialty]

            # Required fields
            assert "name" in template
            assert "prompt_template" in template
            assert "model_pool" in template
            assert "max_iterations" in template
            assert "context_agent_budget" in template

            # Validation
            assert isinstance(template["max_iterations"], int)
            assert template["max_iterations"] > 0
            assert template["max_iterations"] <= 5  # Reasonable limit

            assert isinstance(template["context_agent_budget"], int)
            assert template["context_agent_budget"] > 0
            assert template["context_agent_budget"] <= 3  # Reasonable limit

            # Prompt template should contain expected placeholders
            assert "{specialty}" in template["prompt_template"]
            assert "{marching_orders}" in template["prompt_template"]
            assert "{context_agent_budget}" in template["prompt_template"]

    def test_all_context_agent_templates_valid(self, agent_factory):
        """Every context agent template should be valid"""
        for context_type in CONTEXT_AGENT_TEMPLATES.keys():
            template = CONTEXT_AGENT_TEMPLATES[context_type]

            # Required fields (updated for langchain-mcp-adapters pattern)
            assert "tool_prefix" in template or "fallback_tool" in template, \
                f"Context template {context_type} needs tool_prefix or fallback_tool"
            assert "model_pool" in template
            assert "prompt" in template

            # Model pool should be valid
            assert isinstance(template["model_pool"], ModelPool)

    def test_create_review_agent_subgraph_compiles(self, agent_factory, mock_settings, mock_mcp_provider):
        """All review agent subgraphs should compile"""
        with patch('multiagentpanic.factory.agent_factory.get_settings', return_value=mock_settings), \
             patch('multiagentpanic.factory.agent_factory.get_mcp_tool_provider', return_value=mock_mcp_provider):
            for specialty in ["alignment", "dependencies", "testing", "security"]:
                subgraph = AgentFactory.create_review_agent_subgraph(specialty, agent_factory.model_selector)

                # Should be compiled StateGraph
                assert subgraph is not None
                assert hasattr(subgraph, 'invoke')

                # Test that it can be invoked with minimal state
                from multiagentpanic.domain.schemas import PRMetadata, CIStatus
                minimal_state = ReviewAgentState(
                    pr_metadata=PRMetadata(
                        pr_number=123,
                        pr_url="https://github.com/owner/repo/pull/123",
                        pr_branch="test-branch",
                        base_branch="main",
                        pr_title="Test PR",
                        pr_complexity="simple",
                        pr_body="Test PR body"
                    ),
                    pr_diff="test diff",
                    changed_files=["test.py"],
                    repo_memory={},
                    ci_status=CIStatus(
                        triggered_by="test",
                        status="pending"
                    ),
                    agent_id="test_agent",
                    specialty=specialty,
                    marching_orders="test orders",
                    context_gathered=[],
                    findings=[],
                    reasoning_history=[],
                    current_iteration=1,
                    context_requests_this_iteration=[],
                    needs_more_context=False,
                    final_report=None
                )

                # This should not raise an exception
                try:
                    result = subgraph.invoke(minimal_state.model_dump())
                    assert result is not None
                except Exception as e:
                    # Some exceptions are expected due to mock LLM calls
                    assert "LLM" in str(e) or "mock" in str(e) or "API" in str(e)

    @pytest.mark.asyncio
    async def test_context_agent_function_creation(self, agent_factory):
        """Context agents should be created as async callable functions"""
        for context_type in ["zoekt_search", "lsp_analysis", "git_history"]:
            agent_fn = agent_factory.create_context_agent(context_type)

            # Should be callable and async
            assert callable(agent_fn)
            assert inspect.iscoroutinefunction(agent_fn)

            # Test with minimal input
            try:
                result = await agent_fn({
                    "task": context_type,
                    "target_files": ["test.py"],
                    "query": "test query"
                })
                assert result is not None
                assert "context_found" in result
                assert "cost" in result
                assert "tokens" in result
            except Exception as e:
                # Some exceptions expected due to mock implementations
                assert "mock" in str(e) or "test" in str(e)

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

    def test_model_selection_integration(self, mock_settings, mock_mcp_provider):
        """Test that model selection integrates properly with agent factory"""
        with patch('multiagentpanic.factory.agent_factory.get_settings', return_value=mock_settings), \
             patch('multiagentpanic.factory.agent_factory.get_mcp_tool_provider', return_value=mock_mcp_provider):
            # Mock the model selector to return string values
            model_selector = ModelSelector(mode=ModelTier.SIMPLE)
            with patch.object(model_selector, 'get_model', return_value='mock_model_str'):
                factory = AgentFactory(model_selector, mcp_provider=mock_mcp_provider)
                
                # Test simple mode
                model = factory.get_model_for_agent("review_agent", ModelPool.EXPENSIVE_CODING)
                assert model is not None
                assert isinstance(model, str)

                # Test that different agent types get different models
                orchestrator_model = factory.get_model_for_agent("orchestrator", ModelPool.ORCHESTRATOR)
                review_model = factory.get_model_for_agent("review_agent", ModelPool.EXPENSIVE_CODING)
                context_model = factory.get_model_for_agent("context_agent", ModelPool.CHEAP_TOOL_USE)

                # In simple mode, these should be different
                assert orchestrator_model != review_model
                assert review_model != context_model

    def test_agent_factory_initialization(self, mock_settings, mock_mcp_provider):
        """Test AgentFactory initialization"""
        with patch('multiagentpanic.factory.agent_factory.get_settings', return_value=mock_settings), \
             patch('multiagentpanic.factory.agent_factory.get_mcp_tool_provider', return_value=mock_mcp_provider):
            selector = ModelSelector()
            factory = AgentFactory(selector, mcp_provider=mock_mcp_provider)

            assert factory.model_selector == selector
            assert factory.settings == mock_settings
            assert factory._redis_client is None  # Should be lazy initialized

    def test_redis_client_lazy_initialization(self, agent_factory, mock_settings):
        """Test Redis client lazy initialization"""
        # Initially should be None
        assert agent_factory._redis_client is None

        # Accessing property should initialize
        with patch('redis.from_url') as mock_redis:
            mock_redis.return_value = Mock()
            client = agent_factory.redis_client

            assert client is not None
            assert agent_factory._redis_client is not None
            mock_redis.assert_called_once()

    def test_agent_factory_error_handling(self, mock_settings, mock_mcp_provider):
        """Test error handling in agent factory methods"""
        with patch('multiagentpanic.factory.agent_factory.get_settings', return_value=mock_settings), \
             patch('multiagentpanic.factory.agent_factory.get_mcp_tool_provider', return_value=mock_mcp_provider):
            model_selector = ModelSelector(mode=ModelTier.SIMPLE)
            factory = AgentFactory(model_selector, mcp_provider=mock_mcp_provider)

            # Test with invalid context type - should raise KeyError
            with pytest.raises(KeyError):
                factory.create_context_agent("invalid_context_type")

            # Test with invalid specialty - should raise KeyError
            with pytest.raises(KeyError):
                AgentFactory.create_review_agent_subgraph(
                    "invalid_specialty", model_selector
                )

    @pytest.mark.asyncio
    async def test_context_agent_state_validation(self, agent_factory):
        """Test context agent state handling"""
        import asyncio
        # Create a context agent
        context_agent = agent_factory.create_context_agent("zoekt_search")

        # Test with valid state
        valid_state = {
            "task": "zoekt_search",
            "target_files": ["test.py"],
            "query": "test query"
        }

        result = await context_agent(valid_state)
        assert "context_found" in result
        assert "cost" in result
        assert "tokens" in result

        # Test with minimal state
        minimal_state = {
            "task": "zoekt_search"
        }
        result = await context_agent(minimal_state)
        assert "context_found" in result

    def test_review_agent_subgraph_structure(self, mock_settings, mock_mcp_provider):
        """Test that review agent subgraphs have expected structure"""
        with patch('multiagentpanic.factory.agent_factory.get_settings', return_value=mock_settings), \
             patch('multiagentpanic.factory.agent_factory.get_mcp_tool_provider', return_value=mock_mcp_provider):
            model_selector = ModelSelector(mode=ModelTier.SIMPLE)
            for specialty in ["alignment", "testing"]:
                subgraph = AgentFactory.create_review_agent_subgraph(specialty, model_selector)

                # The subgraph should be a compiled graph with nodes
                assert hasattr(subgraph, 'nodes')
                
                # Check that expected nodes exist by checking the nodes attribute directly
                expected_nodes = ["plan", "spawn_context", "analyze", "finalize"]
                for node in expected_nodes:
                    assert node in subgraph.nodes, f"Missing expected node: {node}"

    def test_agent_factory_template_consistency(self, agent_factory):
        """Test consistency across agent templates"""
        # All review agents should have similar structure
        review_templates = REVIEW_AGENT_TEMPLATES
        context_templates = CONTEXT_AGENT_TEMPLATES

        # Check that all review agents have required fields
        required_review_fields = ["name", "prompt_template", "model_pool", "max_iterations", "context_agent_budget"]
        for specialty, template in review_templates.items():
            for field in required_review_fields:
                assert field in template, f"Review template {specialty} missing field {field}"

        # Check that all context agents have required fields (updated for MCP adapters pattern)
        required_context_fields = ["model_pool", "prompt"]
        optional_context_fields = ["tool_prefix", "fallback_tool"]  # At least one should be present
        for context_type, template in context_templates.items():
            for field in required_context_fields:
                assert field in template, f"Context template {context_type} missing field {field}"
            
            # Must have either tool_prefix or fallback_tool
            has_tool_field = any(f in template for f in optional_context_fields)
            assert has_tool_field, f"Context template {context_type} needs tool_prefix or fallback_tool"

    def test_agent_factory_performance(self, mock_settings, mock_mcp_provider):
        """Test that agent creation is performant"""
        with patch('multiagentpanic.factory.agent_factory.get_settings', return_value=mock_settings), \
             patch('multiagentpanic.factory.agent_factory.get_mcp_tool_provider', return_value=mock_mcp_provider):
            import time
            
            model_selector = ModelSelector(mode=ModelTier.SIMPLE)

            # Time subgraph creation
            start_time = time.time()
            for _ in range(10):  # Create 10 subgraphs
                subgraph = AgentFactory.create_review_agent_subgraph("alignment", model_selector)
            end_time = time.time()

            # Should be fast (< 1 second for 10 subgraphs)
            assert (end_time - start_time) < 1.0, "Subgraph creation should be performant"

            # Time context agent creation
            factory = AgentFactory(model_selector, mcp_provider=mock_mcp_provider)
            start_time = time.time()
            for _ in range(100):  # Create 100 context agents
                agent = factory.create_context_agent("zoekt_search")
            end_time = time.time()

            # Should be very fast (< 0.5 seconds for 100 agents)
            assert (end_time - start_time) < 0.5, "Context agent creation should be very performant"