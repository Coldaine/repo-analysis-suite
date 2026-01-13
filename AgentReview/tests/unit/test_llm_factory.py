import pytest
import sys
from unittest.mock import MagicMock, patch, AsyncMock
from multiagentpanic.factory.llm_factory import LLMFactory
from langchain_core.language_models import BaseChatModel

# Mock missing optional dependencies
sys.modules["langchain_openai"] = MagicMock()
sys.modules["langchain_anthropic"] = MagicMock()
sys.modules["langchain_google_genai"] = MagicMock()

class TestLLMFactory:
    
    @pytest.fixture
    def mock_settings(self):
        settings = MagicMock()
        settings.llm.model_tier = "simple"
        settings.llm.openai_api_key = MagicMock()
        settings.llm.openai_api_key.get_secret_value.return_value = "test-key"
        settings.llm.anthropic_api_key = MagicMock()
        settings.llm.anthropic_api_key.get_secret_value.return_value = "test-key"
        settings.llm.google_api_key = MagicMock()
        settings.llm.google_api_key.get_secret_value.return_value = "test-key"
        settings.llm.primary_provider = "openai"
        settings.llm.max_tokens_per_request = 1000
        settings.llm.openai_base_url = "https://api.openai.com/v1"
        return settings

    @pytest.mark.asyncio
    async def test_get_llm_openai(self, mock_settings):
        factory = LLMFactory(mock_settings)
        
        with patch("langchain_openai.ChatOpenAI") as MockOpenAI:
            MockOpenAI.return_value = AsyncMock(spec=BaseChatModel)
            llm = await factory.get_llm("gpt-4o")
            
            assert llm is not None
            MockOpenAI.assert_called_once()
            call_kwargs = MockOpenAI.call_args[1]
            assert call_kwargs["model"] == "gpt-4o"
            assert call_kwargs["api_key"] == "test-key"

    @pytest.mark.asyncio
    async def test_get_llm_anthropic(self, mock_settings):
        factory = LLMFactory(mock_settings)
        
        with patch("langchain_anthropic.ChatAnthropic") as MockAnthropic:
            MockAnthropic.return_value = AsyncMock(spec=BaseChatModel)
            llm = await factory.get_llm("claude-3-opus")
            
            assert llm is not None
            MockAnthropic.assert_called_once()
            call_kwargs = MockAnthropic.call_args[1]
            assert call_kwargs["model"] == "claude-3-opus"
            assert call_kwargs["api_key"] == "test-key"

    @pytest.mark.asyncio
    async def test_get_llm_google(self, mock_settings):
        factory = LLMFactory(mock_settings)
        
        with patch("langchain_google_genai.ChatGoogleGenerativeAI") as MockGoogle:
            MockGoogle.return_value = AsyncMock(spec=BaseChatModel)
            llm = await factory.get_llm("gemini-1.5-pro")
            
            assert llm is not None
            MockGoogle.assert_called_once()
            call_kwargs = MockGoogle.call_args[1]
            assert call_kwargs["model"] == "gemini-1.5-pro"
            assert call_kwargs["google_api_key"] == "test-key"

    @pytest.mark.asyncio
    async def test_fallback_on_error(self, mock_settings):
        factory = LLMFactory(mock_settings)
        
        # Simulate error during creation
        with patch("langchain_openai.ChatOpenAI", side_effect=[Exception("API Error"), AsyncMock(spec=BaseChatModel)]):
            llm = await factory.get_llm("gpt-4o")
            
            # Should fall back to simple fallback (which also uses ChatOpenAI with dummy key)
            assert llm is not None
            # Note: assert_called logic is tricky with side_effect, relying on return value check
