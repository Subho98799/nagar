"""
Mock AI Provider - Fallback provider when AI is disabled.

Provides rule-based interpretation without external AI calls.
Always available and never fails.
"""

from app.services.ai_plugin.base import AIProvider, AIResponse
from datetime import datetime
from typing import Dict
import logging

logger = logging.getLogger(__name__)


class MockAIProvider(AIProvider):
    """
    Mock AI provider using rule-based keyword matching.
    
    This is the fallback provider when:
    - AI is disabled in config
    - Real AI provider fails
    - No API key is available
    
    Always succeeds and provides reasonable defaults.
    """
    
    MODEL_NAME = "mock-rules-v1"
    MODEL_VERSION = "1.0.0"
    TIMEOUT_SECONDS = 0.1  # Instant (no network call)
    
    def __init__(self):
        logger.info(f"✅ Mock AI Provider initialized: {self.MODEL_NAME}")
    
    def is_enabled(self) -> bool:
        """Mock provider is always enabled (fallback)."""
        return True
    
    def get_model_info(self) -> Dict[str, str]:
        """Get model information."""
        return {
            "name": self.MODEL_NAME,
            "version": self.MODEL_VERSION
        }
    
    def get_timeout_seconds(self) -> float:
        """Get timeout (instant for mock)."""
        return self.TIMEOUT_SECONDS
    
    def interpret_report(
        self,
        description: str,
        city: str = "",
        locality: str = ""
    ) -> AIResponse:
        """
        Interpret report using rule-based keyword matching.
        
        This is a deterministic, fast, always-available fallback.
        """
        try:
            desc_lower = description.lower()
            
            # 1. CLASSIFY ISSUE CATEGORY
            ai_classified_category = "General"
            
            if any(word in desc_lower for word in ["traffic", "jam", "congestion", "road", "pothole", "accident"]):
                ai_classified_category = "Traffic & Roads"
            elif any(word in desc_lower for word in ["water", "leak", "supply", "drainage", "tap", "pipeline"]):
                ai_classified_category = "Water & Sanitation"
            elif any(word in desc_lower for word in ["electricity", "power", "light", "outage", "transformer"]):
                ai_classified_category = "Electricity"
            elif any(word in desc_lower for word in ["garbage", "waste", "trash", "cleanliness", "dump"]):
                ai_classified_category = "Waste Management"
            elif any(word in desc_lower for word in ["health", "hospital", "medical", "doctor", "clinic"]):
                ai_classified_category = "Healthcare"
            elif any(word in desc_lower for word in ["safety", "crime", "theft", "security"]):
                ai_classified_category = "Public Safety"
            elif any(word in desc_lower for word in ["building", "construction", "infrastructure", "bridge"]):
                ai_classified_category = "Infrastructure"
            
            # 2. SUGGEST SEVERITY HINT
            severity_hint = "Low"
            
            if any(word in desc_lower for word in ["urgent", "serious", "major", "severe", "dangerous", "blocking"]):
                severity_hint = "High"
            elif any(word in desc_lower for word in ["moderate", "significant", "concerning", "growing"]):
                severity_hint = "Medium"
            
            # 3. EXTRACT KEYWORDS
            words = description.split()
            stop_words = {"the", "and", "is", "in", "on", "at", "to", "a", "an", "of", "for"}
            keywords = [
                w.strip(".,!?").lower() 
                for w in words 
                if len(w) > 3 and w.lower() not in stop_words
            ][:5]
            
            # 4. GENERATE NEUTRAL SUMMARY
            summary = description.split('.')[0].strip()
            if len(summary) > 100:
                summary = summary[:97] + "..."
            
            return AIResponse(
                ai_classified_category=ai_classified_category,
                severity_hint=severity_hint,
                keywords=keywords,
                summary=summary,
                model_name=self.MODEL_NAME,
                model_version=self.MODEL_VERSION,
                inference_timestamp=datetime.utcnow(),
                ai_confidence_score=0.5  # Medium confidence for rule-based
            )
        
        except Exception as e:
            # Even mock provider should handle errors gracefully
            logger.error(f"Mock AI provider error: {e}")
            return AIResponse(
                ai_classified_category="Unclassified",
                severity_hint="Unknown",
                keywords=[],
                summary="AI interpretation unavailable",
                model_name=self.MODEL_NAME,
                model_version=self.MODEL_VERSION,
                inference_timestamp=datetime.utcnow(),
                error=str(e)
            )
