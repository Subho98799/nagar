"""
AI Provider Registry - Phase-3 Part 2.

Manages AI provider selection and fallback logic.
"""

from app.services.ai_plugin.base import AIProvider, AIResponse
from app.services.ai_plugin.gemini_provider import GeminiAIProvider
from app.services.ai_plugin.mock_provider import MockAIProvider
from app.core.settings import settings
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class AIProviderRegistry:
    """
    Registry for AI providers with fallback logic.
    
    Selects the best available provider based on configuration.
    Falls back gracefully if primary provider fails.
    """
    
    def __init__(self):
        self.providers: list[AIProvider] = []
        self._initialize_providers()
    
    def _initialize_providers(self):
        """Initialize available AI providers in priority order."""
        # Check if AI is globally enabled
        if not settings.AI_ENABLED:
            logger.info("⚠️ AI is disabled globally (AI_ENABLED=false), using mock provider only")
            # Only add mock provider when AI is disabled
            mock_provider = MockAIProvider()
            self.providers.append(mock_provider)
            logger.info("✅ Mock AI Provider registered (AI disabled mode)")
            return
        
        # Priority 1: Gemini (if enabled and API key available)
        gemini_provider = GeminiAIProvider()
        if gemini_provider.is_enabled():
            self.providers.append(gemini_provider)
            logger.info("✅ Gemini AI Provider registered")
        
        # Priority 2: Mock (always available as fallback)
        mock_provider = MockAIProvider()
        self.providers.append(mock_provider)
        logger.info("✅ Mock AI Provider registered (fallback)")
    
    def get_provider(self) -> Optional[AIProvider]:
        """
        Get the best available AI provider.
        
        Returns:
            First enabled provider, or None if no providers available
        """
        for provider in self.providers:
            if provider.is_enabled():
                return provider
        
        # Should never happen (mock provider is always enabled)
        logger.error("⚠️ No AI providers available (this should not happen)")
        return None
    
    def interpret_with_fallback(
        self,
        description: str,
        city: str = "",
        locality: str = ""
    ) -> AIResponse:
        """
        Interpret report using best available provider with fallback.
        
        Tries providers in priority order until one succeeds.
        Always returns a valid AIResponse.
        
        Args:
            description: Report description
            city: City name
            locality: Locality name
        
        Returns:
            AIResponse from first successful provider, or error response
        """
        for provider in self.providers:
            try:
                logger.info(f"Trying AI provider: {provider.get_model_info()['name']}")
                response = provider.interpret_report(description, city, locality)
                
                # Check if response has error
                if response.error:
                    logger.warning(f"Provider {provider.get_model_info()['name']} returned error: {response.error}")
                    continue  # Try next provider
                
                logger.info(f"✅ AI interpretation successful using {provider.get_model_info()['name']}")
                return response
            
            except Exception as e:
                logger.warning(f"Provider {provider.get_model_info()['name']} failed: {e}")
                continue  # Try next provider
        
        # All providers failed - return safe default from mock
        logger.error("⚠️ All AI providers failed, using safe defaults")
        mock_provider = MockAIProvider()
        return mock_provider.interpret_report(description, city, locality)


# Global registry instance (singleton)
_registry: Optional[AIProviderRegistry] = None


def get_ai_provider() -> Optional[AIProvider]:
    """
    Get the best available AI provider.
    
    Returns:
        First enabled provider, or None if unavailable
    """
    global _registry
    if _registry is None:
        _registry = AIProviderRegistry()
    return _registry.get_provider()


def interpret_report_with_fallback(
    description: str,
    city: str = "",
    locality: str = ""
) -> AIResponse:
    """
    Interpret report using best available provider with automatic fallback.
    
    This is the main entry point for AI interpretation.
    Always returns a valid AIResponse, even if all providers fail.
    
    Args:
        description: Report description
        city: City name
        locality: Locality name
    
    Returns:
        AIResponse from successful provider or safe defaults
    """
    global _registry
    if _registry is None:
        _registry = AIProviderRegistry()
    return _registry.interpret_with_fallback(description, city, locality)
