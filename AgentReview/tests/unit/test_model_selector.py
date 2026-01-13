"""
Expanded unit tests for ModelSelector with comprehensive coverage.
Tests model selection logic, fallback mechanisms, and edge cases.
"""

import random

import pytest
from unittest.mock import Mock, patch
from multiagentpanic.factory.model_pools import ModelSelector, ModelPool, ModelTier, ModelPoolConfig, ModelConfig

class TestModelSelector:
    """Test model selection logic in isolation"""

    def test_simple_mode_returns_configured_model(self):
        """Simple mode should always return pre-configured model"""
        selector = ModelSelector(mode=ModelTier.SIMPLE)

        # Should return same model regardless of pool
        model1 = selector.get_model("orchestrator", ModelPool.ORCHESTRATOR, "random")
        model2 = selector.get_model("orchestrator", ModelPool.ORCHESTRATOR, "best_available")

        assert model1 == model2
        assert model1 == selector.simple_selections["orchestrator"]

    def test_advanced_mode_random_selection(self):
        """Advanced mode with random should select from pool"""
        # Use deterministic seed for reproducible test
        random.seed(42)
        selector = ModelSelector(mode=ModelTier.ADVANCED)

        # Run multiple times to ensure we're actually selecting randomly
        selections = set()
        for _ in range(20):
            model = selector.get_model("context_agent", ModelPool.CHEAP_TOOL_USE, "random")
            selections.add(model)
            assert model in ModelPool.CHEAP_TOOL_USE.value

        # With seed 42 and 20 selections from 3 models, we get variation
        assert len(selections) > 1, "Random selection should vary"

    def test_advanced_mode_best_available_fallback(self):
        """Best available should try models in order until one is available"""
        selector = ModelSelector(mode=ModelTier.ADVANCED)

        # Mock availability checker
        availability_map = {
            "claude-3-5-sonnet-20241022": False,  # Not available
            "gpt-4o": False,  # Not available
            "gemini-2.0-flash-thinking-exp": True,  # Available
            "deepseek-reasoner": True
        }

        with patch.object(selector, '_check_availability', side_effect=lambda m: availability_map.get(m, False)):
            model = selector.get_model("orchestrator", ModelPool.ORCHESTRATOR, "best_available")

            # Should skip first two and return first available
            assert model == "gemini-2.0-flash-thinking-exp"

    def test_advanced_mode_all_unavailable_returns_last(self):
        """If all models unavailable, fallback to last in list"""
        selector = ModelSelector(mode=ModelTier.ADVANCED)

        with patch.object(selector, '_check_availability', return_value=False):
            model = selector.get_model("orchestrator", ModelPool.ORCHESTRATOR, "best_available")

            # Should return last model as ultimate fallback
            assert model == ModelPool.ORCHESTRATOR.value[-1]

    def test_pool_validation(self):
        """Ensure all pools have valid models"""
        for pool in ModelPool:
            assert len(pool.value) > 0, f"{pool.name} pool is empty"

            # All entries should be strings
            for model in pool.value:
                assert isinstance(model, str)
                assert len(model) > 0

    def test_model_pool_config_fallback_logic(self):
        """Test ModelPoolConfig fallback logic"""
        config = ModelPoolConfig(
            default_tier=ModelTier.SIMPLE,
            pools={
                ModelTier.SIMPLE: {
                    "default": ModelConfig(provider="openai", model_name="gpt-4o-mini", api_key_env="OPENAI_API_KEY"),
                    "Test Killer Agent": ModelConfig(provider="openai", model_name="gpt-4o", api_key_env="OPENAI_API_KEY"),
                },
                ModelTier.ADVANCED: {
                    "default": ModelConfig(provider="anthropic", model_name="claude-3-5-sonnet-20241022", api_key_env="ANTHROPIC_API_KEY"),
                }
            }
        )

        # Test getting specific agent config
        simple_config = config.get_model_config("Test Killer Agent", ModelTier.SIMPLE)
        assert simple_config.model_name == "gpt-4o"

        # Test fallback to default when specific agent not found
        fallback_config = config.get_model_config("Unknown Agent", ModelTier.SIMPLE)
        assert fallback_config.model_name == "gpt-4o-mini"  # Should fallback to default

        # Test tier fallback
        advanced_config = config.get_model_config("Unknown Agent", ModelTier.ADVANCED)
        assert advanced_config.model_name == "claude-3-5-sonnet-20241022"

    def test_model_pool_config_validation(self):
        """Test ModelPoolConfig validation"""
        # Test invalid provider (should raise ValueError)
        with pytest.raises(ValueError):
            ModelConfig(provider="", model_name="test", api_key_env="KEY")  # Empty provider

        # Test invalid model name (should raise ValueError)
        with pytest.raises(ValueError):
            ModelConfig(provider="openai", model_name="", api_key_env="OPENAI_API_KEY")  # Empty model name

        # Test valid config
        valid_config = ModelConfig(provider="openai", model_name="gpt-4o", api_key_env="OPENAI_API_KEY")
        assert valid_config.provider == "openai"
        assert valid_config.model_name == "gpt-4o"

    def test_model_selector_edge_cases(self):
        """Test edge cases in model selection"""
        selector = ModelSelector(mode=ModelTier.ADVANCED)

        # Test unknown strategy (should default to first)
        model = selector.get_model("test", ModelPool.CHEAP_CODING, "unknown_strategy")
        assert model == ModelPool.CHEAP_CODING.value[0]  # Should default to first

        # Test with empty pool by creating a custom pool with empty list for testing
        # Note: We can't actually create invalid ModelPool enums, but we can test
        # that the selection logic handles edge cases gracefully
        with patch.object(selector, '_check_availability', return_value=True):
            # Test that it returns the first model when all are available
            model = selector.get_model("test", ModelPool.CHEAP_CODING, "best_available")
            assert model in ModelPool.CHEAP_CODING.value  # Should be a valid model

    def test_model_selector_consistency(self):
        """Test that model selection is consistent for same inputs"""
        selector = ModelSelector(mode=ModelTier.SIMPLE)

        # Simple mode should always return same model
        for _ in range(10):
            model = selector.get_model("review_agent", ModelPool.EXPENSIVE_CODING, "random")
            assert model == selector.simple_selections["review_agent"]

        # Advanced mode with fixed strategy should be consistent
        selector_advanced = ModelSelector(mode=ModelTier.ADVANCED)
        for _ in range(5):
            model = selector_advanced.get_model("context_agent", ModelPool.CHEAP_TOOL_USE, "first")
            assert model == ModelPool.CHEAP_TOOL_USE.value[0]

    def test_model_pool_enum_completeness(self):
        """Test that ModelPool enum covers all expected categories"""
        expected_pools = [
            "CHEAP_CODING", "EXPENSIVE_CODING",
            "CHEAP_TOOL_USE", "EXPENSIVE_TOOL_USE",
            "ORCHESTRATOR"
        ]

        for expected_pool in expected_pools:
            assert hasattr(ModelPool, expected_pool), f"Missing expected pool: {expected_pool}"

        # Verify no unexpected pools
        actual_pools = [pool.name for pool in ModelPool]
        for actual_pool in actual_pools:
            assert actual_pool in expected_pools, f"Unexpected pool: {actual_pool}"

    def test_model_selector_initialization(self):
        """Test ModelSelector initialization with different modes"""
        # Test simple mode
        simple_selector = ModelSelector(mode=ModelTier.SIMPLE)
        assert simple_selector.mode == ModelTier.SIMPLE
        assert len(simple_selector.simple_selections) > 0

        # Test advanced mode
        advanced_selector = ModelSelector(mode=ModelTier.ADVANCED)
        assert advanced_selector.mode == ModelTier.ADVANCED
        assert len(advanced_selector.simple_selections) > 0  # Should still have simple selections for fallback

        # Test default mode
        default_selector = ModelSelector()
        assert default_selector.mode == ModelTier.SIMPLE  # Should default to simple