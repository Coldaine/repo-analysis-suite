import logging
from typing import Optional
from langchain_core.language_models import BaseChatModel
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)

class LLMFactory:
    """Factory for creating LLM instances based on configuration"""

    def __init__(self, settings):
        self.settings = settings

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((Exception,))
    )
    async def get_llm(self, model_name: str) -> BaseChatModel:
        """Get LLM instance based on settings and model name"""
        
        try:
            # Determine provider based on model name and settings
            primary_provider = self.settings.llm.primary_provider
            
            # Map model names to providers
            if model_name.startswith(("gpt-", "gpt-4o")):
                provider = "openai"
            elif model_name.startswith("claude-") or model_name.startswith("claude3"):
                provider = "anthropic"
            elif model_name.startswith("gemini"):
                provider = "google"
            else:
                # Default to primary provider from settings
                provider = primary_provider
            
            # Create LLM based on provider
            if provider == "openai":
                return await self._create_openai_llm(model_name)
            elif provider == "anthropic":
                return await self._create_anthropic_llm(model_name)
            elif provider == "google":
                return await self._create_google_llm(model_name)
            else:
                raise ValueError(f"Unsupported provider: {provider}")
                
        except Exception as e:
            logger.error(f"Failed to create LLM for model {model_name}: {e}")
            # Fallback to a simple model if available
            return await self._create_simple_fallback()
    
    async def _create_openai_llm(self, model_name: str) -> BaseChatModel:
        """Create OpenAI-compatible LLM"""
        from langchain_openai import ChatOpenAI
        
        api_key = self.settings.llm.openai_api_key.get_secret_value() if self.settings.llm.openai_api_key else None
        
        # Check if we have an API key
        if not api_key:
            logger.warning("No OpenAI API key found. Using dummy key for testing.")
            api_key = "dummy"
            
        llm = ChatOpenAI(
            model=model_name,
            api_key=api_key,
            base_url=self.settings.llm.openai_base_url,  # For z.ai, etc.
            max_tokens=self.settings.llm.max_tokens_per_request,
            temperature=0.0  # Deterministic for code review
        )
        return llm
    
    async def _create_anthropic_llm(self, model_name: str) -> BaseChatModel:
        """Create Anthropic LLM"""
        from langchain_anthropic import ChatAnthropic
        
        api_key = self.settings.llm.anthropic_api_key.get_secret_value() if self.settings.llm.anthropic_api_key else None
        
        if not api_key:
            logger.warning("No Anthropic API key found. Cannot create Anthropic LLM.")
            raise ValueError("Anthropic API key required for Claude models")
            
        return ChatAnthropic(
            model=model_name,
            api_key=api_key,
            max_tokens=self.settings.llm.max_tokens_per_request,
            temperature=0.0
        )
    
    async def _create_google_llm(self, model_name: str) -> BaseChatModel:
        """Create Google LLM"""
        from langchain_google_genai import ChatGoogleGenerativeAI
        
        api_key = self.settings.llm.google_api_key.get_secret_value() if self.settings.llm.google_api_key else None
        
        if not api_key:
            logger.warning("No Google API key found. Cannot create Google LLM.")
            raise ValueError("Google API key required for Gemini models")
            
        return ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=api_key,
            max_tokens=self.settings.llm.max_tokens_per_request,
            temperature=0.0
        )
    
    async def _create_simple_fallback(self) -> BaseChatModel:
        """Create a simple fallback LLM when all else fails"""
        logger.warning("Using fallback LLM with dummy configuration")
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model="gpt-4o-mini",  # Use a basic model
            api_key="dummy",
            max_tokens=1000,  # Limit tokens to prevent excessive usage
            temperature=0.0
        )
