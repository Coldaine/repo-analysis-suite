import pytest
import asyncio
import os
from types import SimpleNamespace

from multiagentpanic.factory.model_pools import ModelSelector
import multiagentpanic.factory.agent_factory as af_mod
from multiagentpanic.factory.agent_factory import AgentFactory
from multiagentpanic.factory.llm_factory import LLMFactory


class DummyTool:
    def __init__(self, name, result):
        self.name = name
        self.description = "dummy tool"
        self._result = result

    async def ainvoke(self, args):
        await asyncio.sleep(0.01)
        return self._result


class DummyProvider:
    def __init__(self, tools):
        self._tools = tools

    async def get_tools(self):
        return self._tools


class MalformedTool(DummyTool):
    async def ainvoke(self, args):
        # Return an unexpected type (int) to simulate malformed response
        await asyncio.sleep(0.01)
        return 12345


@pytest.mark.asyncio
async def test_integration_zoekt_search_fallback_flow():
    os.environ.setdefault("LLM_OPENAI_API_KEY", "test_key")
    # Monkey-patch get_settings and _get_llm to avoid external dependencies
    af_mod.get_settings = lambda: SimpleNamespace(
        llm=SimpleNamespace(openai_api_key=None, anthropic_api_key=None, google_api_key=None, model_tier="simple", primary_provider="openai", allow_test_keys=True),
        mcp=SimpleNamespace(zoekt_enabled=True, lsp_enabled=True, git_enabled=True, filesystem_enabled=True, zoekt_server_command="", lsp_server_command="", git_server_command="uvx", filesystem_server_command="uvx", mcp_timeout=30, mcp_max_retries=3, mcp_retry_delay=1.0),
        database=SimpleNamespace(redis_url="redis://localhost:6379/0", redis_timeout=1),
        model_tier=SimpleNamespace(simple_orchestrator_model="claude-3-5-sonnet-20241022", simple_review_agent_model="gpt-4o", simple_context_agent_model="grok-fast")
    )

    async def _dummy_get_llm(self, model_name: str):
        async def _ainvoke(messages):
            return SimpleNamespace(content="Summary: ok")
        return SimpleNamespace(ainvoke=_ainvoke)

    # Patch LLMFactory instead of AgentFactory
    LLMFactory.get_llm = _dummy_get_llm

    # Create provider with malformed tool only on zoekt, forcing filesystem fallback
    fs_tool = DummyTool("filesystem__search_files", [{"file": "src/file.py", "line": 10, "content": "# match"}])
    provider = DummyProvider([fs_tool])
    factory = AgentFactory(ModelSelector(mode="simple"), mcp_provider=provider)

    # Should use filesystem fallback tool
    agent = factory.create_async_context_agent("zoekt_search")
    result = await agent({"task": "zoekt_search", "target_files": [], "query": "pattern"})
    raw = result["context_found"]["raw"]
    assert raw.get("source") in ("fallback_tool", "mcp_filesystem_fallback", "mock_fallback")

    # Now test a malformed tool response (invalid type)
    malformed_tool = MalformedTool("zoekt__search", None)
    provider2 = DummyProvider([malformed_tool])
    factory2 = AgentFactory(ModelSelector(mode="simple"), mcp_provider=provider2)
    LLMFactory.get_llm = _dummy_get_llm
    agent2 = factory2.create_async_context_agent("zoekt_search")
    result2 = await agent2({"task": "zoekt_search", "target_files": [], "query": "pattern"})
    # Should still return a context_found but may include error or mock content
    assert "context_found" in result2
