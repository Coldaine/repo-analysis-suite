"""
Type-safe configuration management for Multi-Agent PR Review System.

This module provides Pydantic-based settings that validate and load configuration
from environment variables and .env files.
"""

import os
from typing import Literal, Optional

from pydantic import Field, PostgresDsn, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _get_default_git_command() -> str:
    """Get the default command for the Git MCP server"""
    # User prefers UVX for Python tools
    return "uvx"


def _get_default_filesystem_command() -> str:
    """Get the default command for the Filesystem MCP server"""
    # User prefers UVX for Python tools
    return "uvx"


class DatabaseSettings(BaseSettings):
    """Type-safe database configuration"""

    model_config = SettingsConfigDict(env_prefix="DB_", case_sensitive=False)

    # PostgreSQL for checkpointing and storage
    postgres_url: PostgresDsn = Field(
        default="postgresql://multiagentpanic:password@localhost:5432/multiagentpanic",
        description="PostgreSQL connection URL for checkpoints and storage",
    )
    postgres_pool_size: int = Field(
        default=10, ge=1, le=100, description="Connection pool size"
    )
    postgres_pool_timeout: int = Field(
        default=30, ge=1, description="Pool timeout in seconds"
    )

    # Redis for caching and queues
    redis_url: str = Field(
        default="redis://localhost:6379/0", description="Redis connection URL"
    )
    redis_pool_size: int = Field(
        default=10, ge=1, le=100, description="Redis connection pool size"
    )
    redis_db: int = Field(default=0, ge=0, le=15, description="Redis database number")
    redis_timeout: int = Field(default=5, ge=1, description="Redis timeout in seconds")

    # Learning settings
    learning_enabled: bool = Field(default=True, description="Enable cross-PR learning")
    learning_cache_ttl: int = Field(
        default=86400, ge=60, description="Cache TTL for learning in seconds"
    )


class LLMProviderSettings(BaseSettings):
    """LLM provider configuration and API keys"""

    model_config = SettingsConfigDict(
        env_prefix="LLM_", case_sensitive=False, extra="allow"
    )

    # Primary provider selection
    primary_provider: Literal["openai", "anthropic", "google"] = "openai"

    # Testing controls
    allow_test_keys: bool = Field(
        default=False, description="Allow placeholder API keys (for tests/sandboxes)"
    )

    # OpenAI configuration (for z.ai, OpenAI, etc.)
    # Can be set via LLM_OPENAI_API_KEY or Z_AI_API_KEY
    openai_api_key: Optional[SecretStr] = Field(
        default=None, description="OpenAI API key"
    )
    openai_base_url: Optional[str] = Field(
        default=None, description="OpenAI-compatible base URL (e.g., z.ai)"
    )

    # Anthropic configuration (Claude)
    anthropic_api_key: Optional[SecretStr] = Field(
        default=None, description="Anthropic API key"
    )

    # Google configuration (Gemini)
    google_api_key: Optional[SecretStr] = Field(
        default=None, description="Google API key"
    )

    # Model tier settings
    model_tier: Literal["simple", "advanced"] = "simple"

    # Cost controls
    max_tokens_per_request: int = Field(default=4000, ge=1, le=128000)
    max_cost_per_review: float = Field(default=1.0, ge=0.01, le=100.0)

    def model_post_init(self, __context) -> None:
        """Load from global env vars if prefixed ones are not set"""

        # Fallback: Z_AI_API_KEY -> openai_api_key (z.ai uses OpenAI-compatible API)
        if not self.openai_api_key:
            z_ai_key = os.environ.get("Z_AI_API_KEY")
            if z_ai_key:
                self.openai_api_key = SecretStr(z_ai_key)
                # z.ai uses a specific base URL
                if not self.openai_base_url:
                    self.openai_base_url = "https://api.z.ai/api/coding/paas/v4/"

    @field_validator("openai_api_key", "anthropic_api_key", "google_api_key")
    def _validate_api_keys(
        cls, value: Optional[SecretStr], info
    ) -> Optional[SecretStr]:
        # `info.data` contains the current model data dict for validation context
        allow_test = info.data.get("allow_test_keys", True)
        if value is None:
            return value
        key_str = (
            value.get_secret_value() if isinstance(value, SecretStr) else str(value)
        )
        if not allow_test and key_str.startswith("test"):
            raise ValueError(
                "Test API keys are not allowed in production configuration"
            )
        return value


class ModelTierSettings(BaseSettings):
    """Model pool configuration for different agent types"""

    model_config = SettingsConfigDict(env_prefix="MODEL_TIER_", case_sensitive=False)

    # Simple mode: fixed models for predictable behavior
    simple_orchestrator_model: str = Field(default="glm-4.6")
    simple_review_agent_model: str = Field(default="glm-4.6")
    simple_context_agent_model: str = Field(default="glm-4.6")

    # Advanced mode: model pools for experimentation
    expensive_coding_models: str = Field(
        default="glm-4.6,claude-3-5-sonnet-20241022,gpt-4o,gemini-2.0-flash-thinking-exp,deepseek-chat",
        description="Comma-separated list of expensive coding models",
    )
    cheap_coding_models: str = Field(
        default="glm-4.6,minimax-2,grok-fast,gemini-1.5-flash,gpt-4o-mini",
        description="Comma-separated list of cheap coding models",
    )
    cheap_tool_use_models: str = Field(
        default="glm-4.6,grok-fast,minimax-2,gemini-1.5-flash",
        description="Comma-separated list of cheap tool-use models",
    )
    orchestrator_models: str = Field(
        default="glm-4.6,claude-3-5-sonnet-20241022,o1-preview,gemini-2.0-flash-thinking-exp,deepseek-reasoner",
        description="Comma-separated list of orchestrator models",
    )


class ObservabilitySettings(BaseSettings):
    """Self-hosted observability configuration"""

    model_config = SettingsConfigDict(env_prefix="OBS_", case_sensitive=False)

    # Langfuse (self-hosted tracing)
    langfuse_enabled: bool = Field(default=True, description="Enable Langfuse tracing")
    langfuse_host: str = Field(
        default="http://localhost:3000", description="Langfuse server host"
    )
    langfuse_public_key: Optional[str] = Field(
        default=None, description="Langfuse public key"
    )
    langfuse_secret_key: Optional[SecretStr] = Field(
        default=None, description="Langfuse secret key"
    )
    langfuse_project: str = Field(
        default="multiagent-panic", description="Langfuse project name"
    )

    # OpenTelemetry + Tempo
    opentelemetry_enabled: bool = Field(
        default=True, description="Enable OpenTelemetry"
    )
    tempo_endpoint: str = Field(
        default="http://localhost:4317", description="Tempo OTLP endpoint"
    )

    # Prometheus metrics
    prometheus_enabled: bool = Field(
        default=True, description="Enable Prometheus metrics"
    )
    prometheus_port: int = Field(
        default=8000, ge=1024, le=65535, description="Prometheus metrics port"
    )

    # Grafana
    grafana_enabled: bool = Field(default=True, description="Enable Grafana dashboards")
    grafana_host: str = Field(
        default="http://localhost:3001", description="Grafana host"
    )

    # Loki logging
    loki_enabled: bool = Field(default=True, description="Enable Loki logging")
    loki_endpoint: str = Field(
        default="http://localhost:3100", description="Loki endpoint"
    )

    # Structured logging
    structured_logging_enabled: bool = Field(
        default=True, description="Enable structured logging"
    )
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    # Alerting
    slack_webhook_url: Optional[str] = Field(
        default=None, description="Slack webhook for alerts"
    )
    pagerduty_api_key: Optional[SecretStr] = Field(
        default=None, description="PagerDuty API key"
    )


class MCPClientSettings(BaseSettings):
    """Model Context Protocol client configuration"""

    model_config = SettingsConfigDict(env_prefix="MCP_", case_sensitive=False)

    # Zoekt search integration
    zoekt_enabled: bool = Field(default=True, description="Enable Zoekt search")
    zoekt_server_command: str = Field(
        default="", description="Zoekt MCP server command"
    )
    zoekt_server_args: list[str] = Field(
        default=[], description="Zoekt MCP server arguments"
    )

    # LSP integration
    lsp_enabled: bool = Field(default=True, description="Enable LSP support")
    lsp_server_command: str = Field(default="", description="LSP MCP server command")
    lsp_server_args: list[str] = Field(
        default=[], description="LSP MCP server arguments"
    )

    # Git integration
    git_enabled: bool = Field(default=True, description="Enable Git analysis")
    git_server_command: str = Field(
        default_factory=_get_default_git_command,
        description="Git MCP server command (e.g. uvx, npx)",
    )
    git_server_args: list[str] = Field(
        default=["mcp-server-git", "--repository", "."],
        description="Git MCP server arguments",
    )

    # Filesystem integration
    filesystem_enabled: bool = Field(
        default=True, description="Enable Filesystem access"
    )
    filesystem_server_command: str = Field(
        default_factory=_get_default_filesystem_command,
        description="Filesystem MCP server command (e.g. uvx, npx)",
    )
    filesystem_server_args: list[str] = Field(
        default=["mcp-server-filesystem", "."],
        description="Filesystem MCP server arguments",
    )

    # General MCP settings
    mcp_timeout: int = Field(
        default=30, ge=1, description="MCP tool timeout in seconds"
    )
    mcp_max_retries: int = Field(default=3, ge=0, description="Maximum retry attempts")
    mcp_retry_delay: float = Field(
        default=1.0, ge=0.1, description="Retry delay in seconds"
    )


class WorkflowAgentSettings(BaseSettings):
    """Workflow agent singleton configuration"""

    model_config = SettingsConfigDict(
        env_prefix="WORKFLOW_", case_sensitive=False, extra="allow"
    )

    # GitHub integration
    github_enabled: bool = Field(default=True, description="Enable GitHub integration")
    github_token: Optional[SecretStr] = Field(
        default=None, description="GitHub personal access token"
    )
    github_api_url: str = Field(
        default="https://api.github.com", description="GitHub API URL"
    )

    # CI/CD integration
    ci_enabled: bool = Field(default=True, description="Enable CI/CD integration")
    ci_provider: Literal["github", "gitlab", "jenkins", "none"] = "github"
    ci_timeout: int = Field(default=600, ge=60, description="CI timeout in seconds")

    # Workflow queue settings
    queue_enabled: bool = Field(default=True, description="Enable workflow queue")
    queue_max_size: int = Field(default=1000, ge=10, description="Maximum queue size")
    queue_processing_timeout: int = Field(
        default=300, ge=30, description="Queue processing timeout"
    )

    # Resource optimization
    max_concurrent_workflows: int = Field(
        default=5, ge=1, le=50, description="Maximum concurrent workflows"
    )
    workflow_memory_limit: int = Field(
        default=1024, ge=256, description="Memory limit per workflow (MB)"
    )
    workflow_cpu_limit: float = Field(
        default=1.0, ge=0.1, description="CPU limit per workflow"
    )

    def model_post_init(self, __context) -> None:
        """Load from global env vars if prefixed ones are not set"""
        # Fallback: GITHUB_TOKEN -> github_token
        if not self.github_token:
            gh_token = os.environ.get("GITHUB_TOKEN")
            if gh_token:
                self.github_token = SecretStr(gh_token)


class SearchAPISettings(BaseSettings):
    """Search API configuration for web/code search tools"""

    model_config = SettingsConfigDict(case_sensitive=False, extra="allow")

    # Exa.ai - semantic web search
    exa_api_key: Optional[SecretStr] = Field(default=None, description="Exa.ai API key")

    # SerpAPI - Google search
    serpapi_key: Optional[SecretStr] = Field(default=None, description="SerpAPI key")

    def model_post_init(self, __context) -> None:
        """Load from global env vars"""
        if not self.exa_api_key:
            exa_key = os.environ.get("EXA_API_KEY")
            if exa_key:
                self.exa_api_key = SecretStr(exa_key)

        if not self.serpapi_key:
            serp_key = os.environ.get("SERPAPI_KEY")
            if serp_key:
                self.serpapi_key = SecretStr(serp_key)


class EnvironmentSettings(BaseSettings):
    """Environment and application settings"""

    model_config = SettingsConfigDict(env_prefix="APP_", case_sensitive=False)

    # Environment
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = Field(default=False, description="Enable debug mode")

    # Application
    app_name: str = Field(default="Multi-Agent PR Review System")
    app_version: str = Field(default="0.1.0")
    app_description: str = Field(default="Intelligent multi-agent PR review system")

    # Server
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, ge=1024, le=65535, description="Server port")
    workers: int = Field(
        default=1, ge=1, le=16, description="Number of worker processes"
    )


class Settings(BaseSettings):
    """
    Root settings class that combines all configuration sections.

    This is the main entry point for configuration management.
    All settings are validated at startup and provide type safety.
    """

    model_config = SettingsConfigDict(
        env_file=[".env.local", ".env"],
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="allow",  # Allow extra fields in .env files
    )

    # Configuration sections
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    llm: LLMProviderSettings = Field(default_factory=LLMProviderSettings)
    model_tier: ModelTierSettings = Field(default_factory=ModelTierSettings)
    observability: ObservabilitySettings = Field(default_factory=ObservabilitySettings)
    mcp: MCPClientSettings = Field(default_factory=MCPClientSettings)
    workflow: WorkflowAgentSettings = Field(default_factory=WorkflowAgentSettings)
    search: SearchAPISettings = Field(default_factory=SearchAPISettings)
    app: EnvironmentSettings = Field(default_factory=EnvironmentSettings)

    # Derived properties
    @property
    def is_development(self) -> bool:
        """Check if running in development mode"""
        return self.app.environment == "development"

    @property
    def is_production(self) -> bool:
        """Check if running in production mode"""
        return self.app.environment == "production"

    @property
    def tracing_enabled(self) -> bool:
        """Check if tracing is enabled"""
        return self.observability.langfuse_enabled and bool(
            self.observability.langfuse_api_key
        )

    @property
    def metrics_enabled(self) -> bool:
        """Check if metrics are enabled"""
        return self.observability.prometheus_enabled

    @property
    def logging_enabled(self) -> bool:
        """Check if structured logging is enabled"""
        return self.observability.structured_logging_enabled


# Global settings instance
_settings_instance: Optional[Settings] = None


def get_settings() -> Settings:
    """
    Get the global settings instance.

    This ensures settings are loaded only once and provides a singleton pattern.

    Returns:
        Settings: The configured settings instance
    """
    global _settings_instance

    if _settings_instance is None:
        _settings_instance = Settings()

        # Validate critical configuration
        _validate_critical_settings(_settings_instance)

    return _settings_instance


def _validate_critical_settings(settings: Settings) -> None:
    """
    Validate that critical settings are configured correctly.

    Args:
        settings: The settings instance to validate

    Raises:
        ValueError: If critical settings are missing or invalid
    """
    import logging

    logger = logging.getLogger(__name__)

    errors = []

    # Security: Prevent test keys in production
    if settings.app.environment == "production" and settings.llm.allow_test_keys:
        errors.append(
            "SECURITY: allow_test_keys must be False in production environment"
        )

    # Warn if test keys are enabled
    if settings.llm.allow_test_keys:
        logger.warning(
            "⚠️  TEST MODE ACTIVE: API key validation is disabled. "
            "This should NEVER be used in production. "
            f"Environment: {settings.app.environment}"
        )
        return  # Skip further validation in test mode

    # Check at least one LLM provider has an API key
    if not any(
        [
            settings.llm.openai_api_key,
            settings.llm.anthropic_api_key,
            settings.llm.google_api_key,
        ]
    ):
        errors.append("At least one LLM provider API key must be configured")

    if errors:
        raise ValueError(f"Configuration validation failed: {'; '.join(errors)}")


def reload_settings() -> Settings:
    """
    Reload settings from environment variables.

    This is useful for testing and configuration changes without restart.

    Returns:
        Settings: The reloaded settings instance
    """
    global _settings_instance
    _settings_instance = None
    return get_settings()
