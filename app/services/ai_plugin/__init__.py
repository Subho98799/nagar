"""
AI Plug-in Architecture - Phase-3 Part 2.

Provides optional AI enhancement that can be enabled/disabled.
Fails gracefully and never blocks report ingestion.
"""

from app.services.ai_plugin.base import AIProvider, AIResponse
from app.services.ai_plugin.gemini_provider import GeminiAIProvider
from app.services.ai_plugin.mock_provider import MockAIProvider
from app.services.ai_plugin.registry import get_ai_provider

__all__ = [
    "AIProvider",
    "AIResponse",
    "GeminiAIProvider",
    "MockAIProvider",
    "get_ai_provider",
]
