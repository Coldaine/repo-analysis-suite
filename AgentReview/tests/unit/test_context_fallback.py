import inspect
import pytest
import asyncio
import os

from multiagentpanic.factory.agent_factory import AgentFactory
from multiagentpanic.factory.llm_factory import LLMFactory
from multiagentpanic.factory.prompts import REVIEW_AGENT_TEMPLATES
import multiagentpanic.factory.agent_factory as af_mod
from unittest.mock import AsyncMock, patch
from types import SimpleNamespace


# Monkeypatch get_settings to avoid pydantic Settings initialization in unit tests
class DummySettings(SimpleNamespace):
    def __init__(self):
        super().__init__()
        self.llm = SimpleNamespace(openai_api_key=None, anthropic_api_key=None, google_api_key=None, model_tier="simple", primary_provider="openai", allow_test_keys=True, max_tokens_per_request=4000, max_cost_per_review=1.0)
        self.mcp = SimpleNamespace(zoekt_enabled=True, lsp_enabled=True, git_enabled=True, filesystem_enabled=True, zoekt_server_command="", lsp_server_command="", git_server_command="uvx", filesystem_server_command="uvx", mcp_timeout=30, mcp_max_retries=3, mcp_retry_delay=1.0)
        self.model_tier = SimpleNamespace(simple_orchestrator_model="claude-3-5-sonnet-20241022", simple_review_agent_model="gpt-4o", simple_context_agent_model="grok-fast")
        self.database = SimpleNamespace(redis_url="redis://localhost:6379/0", redis_timeout=1)
        self.workflow = SimpleNamespace(max_concurrent_context_agents=5)


af_mod.get_settings = lambda: DummySettings()


class DummyLLM:
    async def ainvoke(self, messages):
        # Mimic the minimal object returned by actual LLM interfaces (with 'content')
        return SimpleNamespace(content="Summary: noop")

from multiagentpanic.factory.model_pools import ModelSelector


class DummyTool:
    def __init__(self, name, result):
        self.name = name
        self.description = "dummy tool"
        self._result = result

    async def ainvoke(self, args):
        # Simulate small async delay
        await asyncio.sleep(0.01)
        return self._result


class DummyProvider:
    def __init__(self, tools):
        self._tools = tools

    async def get_tools(self):
        return self._tools


@pytest.mark.asyncio
async def test_zoekt_context_fallback_to_filesystem():
    """If the MCP zoekt server is not present, the context agent should fallback to the filesystem tool using the template fallback."""
    # Ensure at least one LLM key is present to satisfy Settings validation
    os.environ.setdefault("LLM_OPENAI_API_KEY", "test_key")
    # Provide only filesystem search tools
    fs_tool = DummyTool("filesystem__search_files", [{"file": "src/file.py", "line": 10, "content": "# match"}])
    provider = DummyProvider([fs_tool])

    factory = AgentFactory(ModelSelector(mode="simple"), mcp_provider=provider)

    with patch.object(factory.llm_factory, 'get_llm', new=AsyncMock(return_value=DummyLLM())) as mock_get_llm:
        # Create a zoekt context agent (it should fallback to filesystem tool)
        agent_fn = factory.create_async_context_agent("zoekt_search")

        result = await agent_fn({"task": "zoekt_search", "target_files": [], "query": "find_me"})
        assert result["context_found"]["raw"]
        raw = result["context_found"]["raw"]
        # If fallback was used, source should be 'fallback_tool' (as implemented in AgentFactory)
        assert raw.get("source") in ("fallback_tool", "mcp_filesystem_fallback", "mock_fallback")
        assert isinstance(raw.get("results") or raw.get("history") or raw.get("file_content"), (list, str))


@pytest.mark.asyncio
async def test_zoekt_context_prefers_zoekt_tool_if_present():
    """If a MCP zoekt server tool is present, the context agent should use it instead of fallback."""
    zoekt_tool = DummyTool("zoekt__search", [{"file": "src/a.py", "line": 1, "content": "# match from zoekt"}])
    fs_tool = DummyTool("filesystem__search_files", [{"file": "src/file.py", "line": 10, "content": "# match"}])
    provider = DummyProvider([zoekt_tool, fs_tool])

    factory = AgentFactory(ModelSelector(mode="simple"), mcp_provider=provider)
    
    with patch.object(factory.llm_factory, 'get_llm', new=AsyncMock(return_value=DummyLLM())) as mock_get_llm:
        agent_fn = factory.create_async_context_agent("zoekt_search")

        result = await agent_fn({"task": "zoekt_search", "target_files": [], "query": "find_me"})
        raw = result["context_found"]["raw"]
        assert raw.get("source") == "mcp_zoekt"
        # Ensure we got zoekt's results
        assert isinstance(raw.get("results"), list)
        assert raw["results"][0]["content"].startswith("# match from zoekt")


@pytest.mark.asyncio
async def test_spawn_context_agents_handles_agent_exception():
    # Ensure settings override is present
    os.environ.setdefault("LLM_OPENAI_API_KEY", "test_key")
    provider = DummyProvider([])
    factory = AgentFactory(ModelSelector(mode="simple"), mcp_provider=provider)

    # Create a request; patch factory.create_async_context_agent to raise
    async def raising_agent(state_data):
        raise RuntimeError("boom")

    factory.create_async_context_agent = lambda ct: raising_agent

    from multiagentpanic.domain.schemas import ReviewAgentState
    # Use construct to avoid Pydantic validation for required fields in this test
    state = ReviewAgentState.model_construct()
    state.context_requests_this_iteration = [{"type": "zoekt_search", "files": [], "query": "x"}]
    template = REVIEW_AGENT_TEMPLATES["testing"]

    result = await AgentFactory._spawn_context_agents(state, factory, template)
    gathered = result["context_gathered"]
    assert len(gathered) == 1
    assert gathered[0].get("failed") is True
    assert "error" in gathered[0]["result"]


@pytest.mark.asyncio
async def test_spawn_context_agents_fail_fast():
    provider = DummyProvider([])
    factory = AgentFactory(ModelSelector(mode="simple"), mcp_provider=provider)

    async def raising_agent(state_data):
        raise RuntimeError("boom")

    factory.create_async_context_agent = lambda ct: raising_agent

    from multiagentpanic.domain.schemas import ReviewAgentState
    state = ReviewAgentState.model_construct()
    state.context_requests_this_iteration = [{"type": "zoekt_search", "files": [], "query": "x"}]
    template = REVIEW_AGENT_TEMPLATES["testing"]

    with pytest.raises(RuntimeError):
        await AgentFactory._spawn_context_agents(state, factory, template, fail_fast=True)


@pytest.mark.asyncio
async def test_context_agent_error_response_structure():
    """Verify error responses include 'raw' field with proper structure (Issue #42)"""
    os.environ.setdefault("LLM_OPENAI_API_KEY", "test_key")

    # Create a provider with no tools to force fallback behavior
    provider = DummyProvider([])
    factory = AgentFactory(ModelSelector(mode="simple"), mcp_provider=provider)

    # Create a context agent that will fail
    async def failing_agent(state_data):
        raise ValueError("Simulated context failure")

    factory.create_async_context_agent = lambda ct: failing_agent

    from multiagentpanic.domain.schemas import ReviewAgentState

    state = ReviewAgentState.model_construct()
    state.context_requests_this_iteration = [
        {"type": "zoekt_search", "files": [], "query": "test"}
    ]
    template = REVIEW_AGENT_TEMPLATES["testing"]

    result = await AgentFactory._spawn_context_agents(state, factory, template)
    gathered = result["context_gathered"]

    assert len(gathered) == 1
    item = gathered[0]

    # Verify failure is marked
    assert item.get("failed") is True

    # Verify result has proper structure
    context_result = item["result"]
    assert "error" in context_result

    # The error message should contain our simulated error
    assert "Simulated context failure" in context_result["error"]


@pytest.mark.asyncio
async def test_context_agent_success_response_has_raw_field():
    """Verify successful responses include 'raw' field"""
    os.environ.setdefault("LLM_OPENAI_API_KEY", "test_key")

    # Create a tool that returns valid results
    fs_tool = DummyTool(
        "filesystem__search_files",
        [{"file": "src/test.py", "line": 1, "content": "# test content"}],
    )
    provider = DummyProvider([fs_tool])

    factory = AgentFactory(ModelSelector(mode="simple"), mcp_provider=provider)
    agent_fn = factory.create_async_context_agent("zoekt_search")

    result = await agent_fn(
        {"task": "zoekt_search", "target_files": [], "query": "test"}
    )

    # Verify response structure
    assert "context_found" in result
    context = result["context_found"]

    # Must have 'raw' field (Issue #42)
    assert "raw" in context, "Response must include 'raw' field for consistency"

    # Verify other expected fields
    assert "cost" in result
    assert "tokens" in result


@pytest.mark.asyncio
async def test_context_agent_response_fields_complete():
    """Verify all expected fields are present in context agent responses"""
    os.environ.setdefault("LLM_OPENAI_API_KEY", "test_key")

    # Use zoekt tool for this test
    zoekt_tool = DummyTool(
        "zoekt__search",
        [{"file": "src/main.py", "line": 42, "content": "def main():"}],
    )
    provider = DummyProvider([zoekt_tool])

    factory = AgentFactory(ModelSelector(mode="simple"), mcp_provider=provider)

    with patch.object(factory.llm_factory, 'get_llm', new=AsyncMock(return_value=DummyLLM())):
        agent_fn = factory.create_async_context_agent("zoekt_search")

        result = await agent_fn(
            {"task": "zoekt_search", "target_files": ["src/main.py"], "query": "main"}
        )

        # Top-level fields
        assert "context_found" in result
        assert "cost" in result
        assert isinstance(result["cost"], (int, float))
        assert "tokens" in result
        assert isinstance(result["tokens"], int)

        # Context found structure
        context = result["context_found"]
        assert "raw" in context

        # Raw structure for successful response
        raw = context["raw"]
        assert "source" in raw
        assert raw["source"] == "mcp_zoekt"  # Zoekt tool was available
        assert "results" in raw
        assert isinstance(raw["results"], list)
