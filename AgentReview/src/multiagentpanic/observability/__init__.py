# src/multiagentpanic/observability/__init__.py
"""
Observability module for multi-agent PR review system.

Provides:
- Prometheus metrics for monitoring
- Langfuse integration for LLM tracing
- Cost tracking for budget management
"""

from multiagentpanic.observability.config import (
    # Main manager
    ObservabilityManager,
    get_observability,
    
    # Langfuse
    LangfuseTracer,
    get_langfuse_callback,
    
    # Cost tracking
    CostTracker,
    MODEL_PRICING,
    
    # Prometheus metrics
    PR_REVIEWS_TOTAL,
    PR_REVIEW_DURATION,
    PR_ERRORS_TOTAL,
    AGENT_SPAWNS_TOTAL,
    AGENT_ITERATIONS,
    AGENT_ACTIVE,
    CONTEXT_REQUESTS_TOTAL,
    CONTEXT_GATHERED_BYTES,
    LLM_TOKENS_TOTAL,
    LLM_COST_USD,
    LLM_LATENCY,
    WORKFLOW_QUEUE_SIZE,
    WORKFLOW_REQUESTS_TOTAL,
    
    # Convenience functions
    record_review_error,
)

__all__ = [
    # Main manager
    "ObservabilityManager",
    "get_observability",
    
    # Langfuse
    "LangfuseTracer", 
    "get_langfuse_callback",
    
    # Cost tracking
    "CostTracker",
    "MODEL_PRICING",
    
    # Prometheus metrics
    "PR_REVIEWS_TOTAL",
    "PR_REVIEW_DURATION",
    "PR_ERRORS_TOTAL",
    "AGENT_SPAWNS_TOTAL",
    "AGENT_ITERATIONS",
    "AGENT_ACTIVE",
    "CONTEXT_REQUESTS_TOTAL",
    "CONTEXT_GATHERED_BYTES",
    "LLM_TOKENS_TOTAL",
    "LLM_COST_USD",
    "LLM_LATENCY",
    "WORKFLOW_QUEUE_SIZE",
    "WORKFLOW_REQUESTS_TOTAL",
    
    # Convenience
    "record_review_error",
]
