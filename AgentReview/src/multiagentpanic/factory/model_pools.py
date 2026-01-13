from typing import Dict, Any, Optional, List
from enum import Enum
from pydantic import BaseModel, Field

class ModelTier(str, Enum):
    SIMPLE = "simple"
    ADVANCED = "advanced"

class ModelConfig(BaseModel):
    provider: str = Field(min_length=1)
    model_name: str = Field(min_length=1)
    temperature: float = 0.0
    api_key_env: str = Field(min_length=1)

class ModelPool(Enum):
    """Model pools for different agent types"""

    CHEAP_CODING = [
        "minimax-2",
        "grok-fast",
        "gemini-1.5-flash",
        "gpt-4o-mini"
    ]

    EXPENSIVE_CODING = [
        "claude-3-5-sonnet-20241022",
        "gpt-4o",
        "gemini-2.0-flash-thinking-exp",
        "deepseek-chat"
    ]

    CHEAP_TOOL_USE = [
        "grok-fast",  # Free right now
        "minimax-2",
        "gemini-1.5-flash"
    ]

    EXPENSIVE_TOOL_USE = [
        "claude-3-5-sonnet-20241022",  # Best tool use
        "gpt-4o",
        "gemini-2.0-flash-thinking-exp"
    ]

    ORCHESTRATOR = [
        "claude-3-5-sonnet-20241022",
        "o1-preview",
        "gemini-2.0-flash-thinking-exp",
        "deepseek-reasoner"
    ]

class ModelSelector:
    """Handles simple vs advanced mode model selection"""

    def __init__(self, mode: ModelTier = ModelTier.SIMPLE):
        self.mode = mode
        self.simple_selections = {
            "orchestrator": "claude-3-5-sonnet-20241022",
            "review_agent": "gpt-4o",
            "context_agent": "grok-fast"
        }

    def get_model(self, agent_type: str, pool: ModelPool, strategy: str = "random") -> str:
        """
        Simple mode: Returns pre-configured model
        Advanced mode: Returns model from pool based on strategy
        """

        if self.mode == ModelTier.SIMPLE:
            return self.simple_selections.get(agent_type, pool.value[0])

        # Advanced mode
        if strategy == "random":
            import random
            return random.choice(pool.value)

        elif strategy == "best_available":
            # Try models in order until one is available
            for model in pool.value:
                if self._check_availability(model):
                    return model
            # Fallback to last in list
            return pool.value[-1]

        else:
            return pool.value[0]  # Default to first

    def _check_availability(self, model: str) -> bool:
        """Check if model is available (not rate-limited, API up, etc.)"""
        # TODO: Implement actual availability check
        # Could check rate limits, API status, cost budgets
        return True

class ModelPoolConfig(BaseModel):
    """Configuration for model pools"""

    default_tier: ModelTier = ModelTier.SIMPLE
    pools: Dict[ModelTier, Dict[str, ModelConfig]] = Field(default_factory=dict)

    def get_model_config(self, agent_name: str, tier: Optional[ModelTier] = None) -> ModelConfig:
        target_tier = tier or self.default_tier
        # Fallback logic: try specific agent in tier, then default in tier
        tier_pool = self.pools.get(target_tier, {})
        return tier_pool.get(agent_name) or tier_pool.get("default")

# Simple in-memory implementation for now
DEFAULT_MODEL_POOL = ModelPoolConfig(
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
