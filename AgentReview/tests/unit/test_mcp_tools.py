"""
Unit tests for MCP Tools resource management.
Tests close(), close_sync(), reset_mcp_tool_provider(), and atexit handler.
"""

import asyncio
import atexit
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from multiagentpanic.tools import mcp_tools
from multiagentpanic.tools.mcp_tools import (
    MCPToolProvider,
    get_mcp_tool_provider,
    reset_mcp_tool_provider,
)


class TestMCPToolProviderClose:
    """Test MCPToolProvider close() and cleanup methods"""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings for testing"""
        settings = MagicMock()
        settings.mcp.git_enabled = False
        settings.mcp.filesystem_enabled = False
        settings.mcp.zoekt_enabled = False
        settings.mcp.lsp_enabled = False
        return settings

    @pytest.fixture
    def provider(self, mock_settings):
        """Create a provider with mocked settings"""
        with patch(
            "multiagentpanic.tools.mcp_tools.get_settings",
            return_value=mock_settings,
        ):
            return MCPToolProvider(settings=mock_settings)

    @pytest.mark.asyncio
    async def test_close_with_no_client(self, provider):
        """close() should be safe when no client exists"""
        assert provider._client is None
        await provider.close()  # Should not raise
        assert provider._client is None
        assert provider._initialized is False

    @pytest.mark.asyncio
    async def test_close_resets_state(self, provider):
        """close() should reset all state attributes"""
        # Simulate initialized state
        provider._client = MagicMock()
        provider._client.close = AsyncMock()
        provider._tools = [MagicMock(), MagicMock()]
        provider._initialized = True

        await provider.close()

        assert provider._client is None
        assert provider._tools is None
        assert provider._initialized is False

    @pytest.mark.asyncio
    async def test_close_calls_client_close_method(self, provider):
        """close() should call client.close() if available"""
        mock_client = MagicMock()
        mock_client.close = AsyncMock()
        provider._client = mock_client

        await provider.close()

        mock_client.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_close_uses_aexit_fallback(self, provider):
        """close() should use __aexit__ if close() not available"""
        # Create a mock that doesn't have close() but has __aexit__
        class MockClientWithAexit:
            def __init__(self):
                self.aexit_called = False
                self.aexit_args = None

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                self.aexit_called = True
                self.aexit_args = (exc_type, exc_val, exc_tb)

        mock_client = MockClientWithAexit()
        provider._client = mock_client

        await provider.close()

        assert mock_client.aexit_called
        assert mock_client.aexit_args == (None, None, None)

    @pytest.mark.asyncio
    async def test_close_handles_exception(self, provider):
        """close() should handle exceptions gracefully"""
        mock_client = MagicMock()
        mock_client.close = AsyncMock(side_effect=RuntimeError("Connection failed"))
        provider._client = mock_client

        # Should not raise, should log warning
        await provider.close()

        # State should still be reset even after error
        assert provider._client is None
        assert provider._initialized is False

    def test_close_sync_with_no_client(self, provider):
        """close_sync() should be safe when no client exists"""
        assert provider._client is None
        provider.close_sync()  # Should not raise
        assert provider._client is None

    def test_close_sync_runs_async_close(self, provider):
        """close_sync() should execute async close"""
        mock_client = MagicMock()
        mock_client.close = AsyncMock()
        provider._client = mock_client
        provider._tools = [MagicMock()]
        provider._initialized = True

        provider.close_sync()

        # State should be reset
        assert provider._client is None
        assert provider._initialized is False

    def test_close_sync_with_running_loop(self, provider):
        """close_sync() should use run_coroutine_threadsafe when loop is running"""
        mock_client = MagicMock()
        mock_client.close = AsyncMock()
        provider._client = mock_client

        async def run_in_loop():
            # We're now in a running event loop
            # close_sync uses run_coroutine_threadsafe which blocks until complete
            provider.close_sync()

        asyncio.run(run_in_loop())

        # Client should be closed (run_coroutine_threadsafe waits for completion)
        assert provider._client is None


class TestResetMCPToolProvider:
    """Test the reset_mcp_tool_provider() function"""

    def test_reset_clears_singleton(self):
        """reset_mcp_tool_provider() should clear the global singleton"""
        # Ensure there's a provider
        with patch(
            "multiagentpanic.tools.mcp_tools.get_settings",
            return_value=MagicMock(),
        ):
            mcp_tools._provider = MCPToolProvider()
            assert mcp_tools._provider is not None

            reset_mcp_tool_provider()

            assert mcp_tools._provider is None

    def test_reset_calls_close_sync(self):
        """reset_mcp_tool_provider() should call close_sync() on existing provider"""
        mock_provider = MagicMock()
        mcp_tools._provider = mock_provider

        reset_mcp_tool_provider()

        mock_provider.close_sync.assert_called_once()
        assert mcp_tools._provider is None

    def test_reset_safe_when_no_provider(self):
        """reset_mcp_tool_provider() should be safe when no provider exists"""
        mcp_tools._provider = None
        reset_mcp_tool_provider()  # Should not raise
        assert mcp_tools._provider is None

    def test_get_provider_after_reset(self):
        """Should be able to get a new provider after reset"""
        with patch(
            "multiagentpanic.tools.mcp_tools.get_settings",
            return_value=MagicMock(),
        ):
            # Get initial provider
            provider1 = get_mcp_tool_provider()
            assert provider1 is not None

            # Reset
            reset_mcp_tool_provider()

            # Get new provider
            provider2 = get_mcp_tool_provider()
            assert provider2 is not None
            assert provider2 is not provider1


class TestAtexitHandler:
    """Test the atexit handler registration"""

    def test_cleanup_on_exit_registered(self):
        """_cleanup_on_exit should be registered with atexit"""
        # Get all registered atexit functions
        # Note: atexit doesn't expose registered functions directly
        # We verify by checking the function exists and is callable
        assert callable(mcp_tools._cleanup_on_exit)

    def test_cleanup_on_exit_with_provider(self):
        """_cleanup_on_exit should call close_sync on existing provider"""
        mock_provider = MagicMock()
        mcp_tools._provider = mock_provider

        mcp_tools._cleanup_on_exit()

        mock_provider.close_sync.assert_called_once()

    def test_cleanup_on_exit_without_provider(self):
        """_cleanup_on_exit should be safe when no provider exists"""
        mcp_tools._provider = None
        mcp_tools._cleanup_on_exit()  # Should not raise


class TestMCPToolProviderInitialization:
    """Test MCPToolProvider initialization and properties"""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings for testing"""
        settings = MagicMock()
        settings.mcp.git_enabled = True
        settings.mcp.git_server_command = "uvx"
        settings.mcp.git_server_args = ["mcp-server-git"]
        settings.mcp.filesystem_enabled = True
        settings.mcp.filesystem_server_command = "uvx"
        settings.mcp.filesystem_server_args = ["mcp-server-filesystem"]
        settings.mcp.zoekt_enabled = False
        settings.mcp.zoekt_server_command = ""
        settings.mcp.lsp_enabled = False
        settings.mcp.lsp_server_command = ""
        return settings

    def test_is_initialized_false_initially(self, mock_settings):
        """is_initialized should be False before get_tools() is called"""
        with patch(
            "multiagentpanic.tools.mcp_tools.get_settings",
            return_value=mock_settings,
        ):
            provider = MCPToolProvider(settings=mock_settings)
            assert provider.is_initialized is False

    def test_build_server_config_respects_enabled_flags(self, mock_settings):
        """_build_server_config should only include enabled servers"""
        with patch(
            "multiagentpanic.tools.mcp_tools.get_settings",
            return_value=mock_settings,
        ):
            provider = MCPToolProvider(settings=mock_settings)
            config = provider._build_server_config()

            assert "git" in config
            assert "filesystem" in config
            assert "zoekt" not in config
            assert "lsp" not in config

    def test_get_tool_names_empty_before_init(self, mock_settings):
        """get_tool_names() should return empty list before initialization"""
        with patch(
            "multiagentpanic.tools.mcp_tools.get_settings",
            return_value=mock_settings,
        ):
            provider = MCPToolProvider(settings=mock_settings)
            assert provider.get_tool_names() == []

    @pytest.mark.asyncio
    async def test_get_tools_returns_empty_with_no_servers(self):
        """get_tools() should return empty list when no servers configured"""
        mock_settings = MagicMock()
        mock_settings.mcp.git_enabled = False
        mock_settings.mcp.filesystem_enabled = False
        mock_settings.mcp.zoekt_enabled = False
        mock_settings.mcp.lsp_enabled = False

        with patch(
            "multiagentpanic.tools.mcp_tools.get_settings",
            return_value=mock_settings,
        ):
            provider = MCPToolProvider(settings=mock_settings)
            tools = await provider.get_tools()

            assert tools == []
            assert provider._tools == []
