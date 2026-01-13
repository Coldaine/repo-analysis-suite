# src/multiagentpanic/observability/config.py
"""
Observability configuration for the multi-agent PR review system.

Integrates:
- Langfuse: LLM tracing, cost tracking, prompt analysis
- Prometheus: Time-series metrics
- OpenTelemetry: Distributed tracing
"""

import os
import logging
from typing import Optional, Dict, Any, List
from contextlib import contextmanager
from datetime import datetime

from prometheus_client import Counter, Histogram, Gauge, start_http_server, REGISTRY
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# =============================================================================
# Prometheus Metrics
# =============================================================================

# Review metrics
PR_REVIEWS_TOTAL = Counter(
    'pr_reviews_total',
    'Total number of PR reviews executed',
    ['complexity_level', 'verdict']
)

PR_REVIEW_DURATION = Histogram(
    'pr_review_duration_seconds',
    'Time spent on PR reviews',
    ['complexity_level'],
    buckets=[1, 5, 10, 30, 60, 120, 300, 600]
)

PR_ERRORS_TOTAL = Counter(
    'pr_review_errors_total',
    'Total number of errors in PR reviews',
    ['component', 'error_type']
)

# Agent metrics
AGENT_SPAWNS_TOTAL = Counter(
    'agents_spawned_total',
    'Number of agents spawned per type',
    ['agent_type', 'model']
)

AGENT_ITERATIONS = Histogram(
    'agent_iterations_total',
    'Number of iterations per agent review',
    ['agent_type'],
    buckets=[1, 2, 3, 4, 5]
)

AGENT_ACTIVE = Gauge(
    'agents_active',
    'Number of currently active agents',
    ['agent_type']
)

# Context gathering metrics
CONTEXT_REQUESTS_TOTAL = Counter(
    'context_requests_total',
    'Total context gathering requests',
    ['context_type', 'status']
)

CONTEXT_GATHERED_BYTES = Counter(
    'context_gathered_bytes_total',
    'Total bytes of context gathered',
    ['context_type']
)

# LLM/Cost metrics
LLM_TOKENS_TOTAL = Counter(
    'llm_tokens_total',
    'Total LLM tokens used',
    ['model', 'token_type']  # token_type: input, output
)

LLM_COST_USD = Counter(
    'llm_cost_usd_total',
    'Total LLM costs in USD',
    ['model', 'agent_type']
)

LLM_LATENCY = Histogram(
    'llm_request_duration_seconds',
    'LLM request latency',
    ['model'],
    buckets=[0.1, 0.5, 1, 2, 5, 10, 30]
)

# Workflow metrics
WORKFLOW_QUEUE_SIZE = Gauge(
    'workflow_queue_size',
    'Current size of the workflow queue'
)

WORKFLOW_REQUESTS_TOTAL = Counter(
    'workflow_requests_total',
    'Total workflow requests',
    ['request_type', 'status']
)


# =============================================================================
# Langfuse Integration
# =============================================================================

class LangfuseTracer:
    """
    Langfuse integration for LLM tracing.
    
    Provides:
    - Automatic trace creation for PR reviews
    - Cost tracking per model
    - Prompt/completion logging
    - Span creation for agent iterations
    """
    
    _instance: Optional['LangfuseTracer'] = None
    
    def __init__(self):
        self._client = None
        self._enabled = False
        self._initialize()
    
    @classmethod
    def get_instance(cls) -> 'LangfuseTracer':
        """Get singleton instance"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def _initialize(self):
        """Initialize Langfuse client if configured"""
        try:
            from multiagentpanic.config.settings import get_settings
            settings = get_settings()
            
            public_key = settings.observability.langfuse_public_key
            secret_key = settings.observability.langfuse_secret_key
            host = settings.observability.langfuse_host
            
            if public_key and secret_key:
                try:
                    from langfuse import Langfuse
                    self._client = Langfuse(
                        public_key=public_key,
                        secret_key=secret_key.get_secret_value() if hasattr(secret_key, 'get_secret_value') else secret_key,
                        host=host
                    )
                    self._enabled = True
                    logger.info(f"Langfuse tracing enabled, host: {host}")
                except ImportError:
                    logger.warning("langfuse package not installed, tracing disabled")
            else:
                logger.info("Langfuse credentials not configured, tracing disabled")
                
        except Exception as e:
            logger.warning(f"Failed to initialize Langfuse: {e}")
            self._enabled = False
    
    @property
    def enabled(self) -> bool:
        return self._enabled
    
    @property
    def client(self):
        return self._client
    
    def create_trace(
        self,
        name: str,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None
    ):
        """Create a new trace for a PR review"""
        if not self._enabled:
            return None
            
        try:
            return self._client.trace(
                name=name,
                metadata=metadata or {},
                tags=tags or []
            )
        except Exception as e:
            logger.warning(f"Failed to create Langfuse trace: {e}")
            return None
    
    def create_span(
        self,
        trace,
        name: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Create a span within a trace"""
        if not self._enabled or trace is None:
            return None
            
        try:
            return trace.span(name=name, metadata=metadata or {})
        except Exception as e:
            logger.warning(f"Failed to create Langfuse span: {e}")
            return None
    
    def log_generation(
        self,
        trace,
        name: str,
        model: str,
        prompt: str,
        completion: str,
        usage: Optional[Dict[str, int]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Log an LLM generation"""
        if not self._enabled or trace is None:
            return
            
        try:
            trace.generation(
                name=name,
                model=model,
                input=prompt,
                output=completion,
                usage=usage,
                metadata=metadata or {}
            )
        except Exception as e:
            logger.warning(f"Failed to log Langfuse generation: {e}")
    
    def flush(self):
        """Flush pending traces"""
        if self._enabled and self._client:
            try:
                self._client.flush()
            except Exception as e:
                logger.warning(f"Failed to flush Langfuse: {e}")


def get_langfuse_callback():
    """
    Get a LangChain callback handler for Langfuse.
    
    Returns None if Langfuse is not configured.
    """
    tracer = LangfuseTracer.get_instance()
    if not tracer.enabled:
        return None
        
    try:
        from langfuse.callback import CallbackHandler
        from multiagentpanic.config.settings import get_settings
        settings = get_settings()
        
        return CallbackHandler(
            public_key=settings.observability.langfuse_public_key,
            secret_key=settings.observability.langfuse_secret_key.get_secret_value() 
                if hasattr(settings.observability.langfuse_secret_key, 'get_secret_value') 
                else settings.observability.langfuse_secret_key,
            host=settings.observability.langfuse_host
        )
    except Exception as e:
        logger.warning(f"Failed to create Langfuse callback handler: {e}")
        return None


# =============================================================================
# Cost Tracking
# =============================================================================

# Model pricing per 1K tokens (as of late 2024)
MODEL_PRICING = {
    # OpenAI
    "gpt-4o": {"input": 0.0025, "output": 0.01},
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    "gpt-4-turbo": {"input": 0.01, "output": 0.03},
    "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
    # Anthropic
    "claude-3-5-sonnet-20241022": {"input": 0.003, "output": 0.015},
    "claude-3-5-haiku-20241022": {"input": 0.0008, "output": 0.004},
    "claude-3-opus-20240229": {"input": 0.015, "output": 0.075},
    # Google
    "gemini-1.5-pro": {"input": 0.00125, "output": 0.005},
    "gemini-1.5-flash": {"input": 0.000075, "output": 0.0003},
}


class CostTracker:
    """
    Track LLM costs across the review session.
    
    Updates both Prometheus metrics and returns cost data
    for inclusion in review state.
    """
    
    def __init__(self):
        self.total_cost = 0.0
        self.costs_by_model: Dict[str, float] = {}
        self.costs_by_agent: Dict[str, float] = {}
        self.tokens_by_model: Dict[str, Dict[str, int]] = {}
    
    def record_usage(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        agent_type: str = "unknown"
    ) -> float:
        """
        Record token usage and calculate cost.
        
        Returns the cost for this usage in USD.
        """
        pricing = MODEL_PRICING.get(model, {"input": 0.01, "output": 0.03})
        
        input_cost = (input_tokens / 1000) * pricing["input"]
        output_cost = (output_tokens / 1000) * pricing["output"]
        total = input_cost + output_cost
        
        # Update internal tracking
        self.total_cost += total
        self.costs_by_model[model] = self.costs_by_model.get(model, 0) + total
        self.costs_by_agent[agent_type] = self.costs_by_agent.get(agent_type, 0) + total
        
        if model not in self.tokens_by_model:
            self.tokens_by_model[model] = {"input": 0, "output": 0}
        self.tokens_by_model[model]["input"] += input_tokens
        self.tokens_by_model[model]["output"] += output_tokens
        
        # Update Prometheus metrics
        LLM_TOKENS_TOTAL.labels(model=model, token_type="input").inc(input_tokens)
        LLM_TOKENS_TOTAL.labels(model=model, token_type="output").inc(output_tokens)
        LLM_COST_USD.labels(model=model, agent_type=agent_type).inc(total)
        
        return total
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of all costs"""
        return {
            "total_cost_usd": round(self.total_cost, 6),
            "costs_by_model": {k: round(v, 6) for k, v in self.costs_by_model.items()},
            "costs_by_agent": {k: round(v, 6) for k, v in self.costs_by_agent.items()},
            "tokens_by_model": self.tokens_by_model
        }


# =============================================================================
# Observability Manager
# =============================================================================

class ObservabilityManager:
    """
    Central manager for all observability features.
    
    Usage:
        obs = ObservabilityManager.get_instance()
        obs.start_metrics_server()
        
        with obs.trace_review(pr_number=123) as trace:
            # ... review logic ...
            obs.record_agent_spawn("alignment", "gpt-4o")
    """
    
    _instance: Optional['ObservabilityManager'] = None
    
    def __init__(self):
        self.langfuse = LangfuseTracer.get_instance()
        self.cost_tracker = CostTracker()
        self._metrics_server_started = False
    
    @classmethod
    def get_instance(cls) -> 'ObservabilityManager':
        """Get singleton instance"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def start_metrics_server(self, port: int = 8000):
        """Start Prometheus metrics HTTP server"""
        if not self._metrics_server_started:
            try:
                start_http_server(port)
                self._metrics_server_started = True
                logger.info(f"Prometheus metrics server started on port {port}")
            except Exception as e:
                logger.warning(f"Failed to start metrics server: {e}")
    
    @contextmanager
    def trace_review(self, pr_number: int, pr_title: str = "", complexity: str = "medium"):
        """Context manager for tracing a full PR review"""
        start_time = datetime.now()
        trace = None
        
        try:
            # Create Langfuse trace
            trace = self.langfuse.create_trace(
                name=f"pr-review-{pr_number}",
                metadata={
                    "pr_number": pr_number,
                    "pr_title": pr_title,
                    "complexity": complexity
                },
                tags=["pr-review", complexity]
            )
            
            yield trace
            
            # Record successful completion
            PR_REVIEWS_TOTAL.labels(complexity_level=complexity, verdict="completed").inc()
            
        except Exception as e:
            PR_ERRORS_TOTAL.labels(component="orchestrator", error_type=type(e).__name__).inc()
            raise
            
        finally:
            # Record duration
            duration = (datetime.now() - start_time).total_seconds()
            PR_REVIEW_DURATION.labels(complexity_level=complexity).observe(duration)
            
            # Flush Langfuse
            self.langfuse.flush()
    
    def record_agent_spawn(self, agent_type: str, model: str):
        """Record an agent being spawned"""
        AGENT_SPAWNS_TOTAL.labels(agent_type=agent_type, model=model).inc()
        AGENT_ACTIVE.labels(agent_type=agent_type).inc()
    
    def record_agent_complete(self, agent_type: str, iterations: int):
        """Record an agent completing its work"""
        AGENT_ACTIVE.labels(agent_type=agent_type).dec()
        AGENT_ITERATIONS.labels(agent_type=agent_type).observe(iterations)
    
    def record_context_request(self, context_type: str, success: bool, bytes_gathered: int = 0):
        """Record a context gathering request"""
        status = "success" if success else "failure"
        CONTEXT_REQUESTS_TOTAL.labels(context_type=context_type, status=status).inc()
        if success and bytes_gathered > 0:
            CONTEXT_GATHERED_BYTES.labels(context_type=context_type).inc(bytes_gathered)
    
    def record_llm_call(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        latency_seconds: float,
        agent_type: str = "unknown"
    ):
        """Record an LLM API call"""
        self.cost_tracker.record_usage(model, input_tokens, output_tokens, agent_type)
        LLM_LATENCY.labels(model=model).observe(latency_seconds)
    
    def record_workflow_request(self, request_type: str, success: bool):
        """Record a workflow request (CI trigger, test run, etc)"""
        status = "success" if success else "failure"
        WORKFLOW_REQUESTS_TOTAL.labels(request_type=request_type, status=status).inc()
    
    def get_cost_summary(self) -> Dict[str, Any]:
        """Get current cost tracking summary"""
        return self.cost_tracker.get_summary()


# =============================================================================
# Module-level convenience functions
# =============================================================================

def get_observability() -> ObservabilityManager:
    """Get the global observability manager"""
    return ObservabilityManager.get_instance()


def record_review_error(component: str, error: Exception):
    """Record an error that occurred during review"""
    PR_ERRORS_TOTAL.labels(component=component, error_type=type(error).__name__).inc()
    logger.error(f"Error in {component}: {error}")