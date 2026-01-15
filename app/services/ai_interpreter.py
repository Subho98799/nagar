"""
AI Interpreter Service - Phase-3 Part 2 AI Plug-in Integration.

DESIGN PRINCIPLES (CRITICAL):
- AI assists interpretation, does NOT verify truth
- AI does NOT assign confidence or authenticity
- AI does NOT trigger actions or alerts
- AI output is advisory only
- System must work even if AI fails
- AI is OPTIONAL and can be disabled

SCOPE OF AI:
✅ Classify issue type
✅ Suggest severity level
✅ Extract keywords
✅ Generate neutral summaries

❌ NOT verify reports
❌ NOT assign confidence
❌ NOT detect fake reports
❌ NOT predict events
❌ NOT trigger escalations
"""

from typing import Dict, Optional
from app.services.ai_plugin.registry import interpret_report_with_fallback
from app.core.settings import settings
import logging

logger = logging.getLogger(__name__)


class AIInterpreter:
    """
    AI-powered report interpretation assistant (Phase-3 Part 2).
    
    Uses plug-in architecture with automatic fallback.
    Supports multiple AI providers (Gemini, Mock) with graceful degradation.
    
    The AI's role is STRICTLY LIMITED to classification and summarization.
    It does NOT make decisions about report validity or urgency.
    """
    
    def __init__(self):
        """Initialize AI interpreter with plug-in architecture."""
        self.ai_enabled = settings.AI_ENABLED
        logger.info(f"✅ AI Interpreter initialized (AI enabled: {self.ai_enabled})")
    
    def interpret_report(
        self, 
        description: str, 
        city: str = "", 
        locality: str = ""
    ) -> Dict:
        """
        Interpret a citizen report using AI assistance (Phase-3 Part 2).
        
        Uses plug-in architecture with automatic fallback.
        Always returns valid result even if AI fails.
        
        Args:
            description: The citizen's observation
            city: City name (provides context)
            locality: Locality name (provides context)
        
        Returns:
            dict: AI interpretation with Phase-3 Part 2 metadata:
                - ai_classified_category: AI-inferred issue category
                - severity_hint: Suggested severity (Low/Medium/High)
                - keywords: Extracted relevant terms
                - summary: Short neutral summary
                - model_name: AI model used
                - model_version: Model version
                - inference_timestamp: When inference occurred
                - ai_confidence_score: Optional confidence (0.0-1.0)
                - error: Optional error message if AI failed
        
        Note: If AI fails, returns safe defaults (system continues working)
        """
        try:
            # Log the interpretation request
            logger.info(f"AI interpreting report from {city}, {locality}")
            
            # Use plug-in architecture with automatic fallback
            ai_response = interpret_report_with_fallback(
                description=description,
                city=city or "",
                locality=locality or ""
            )
            
            # Convert to dictionary format (includes Phase-3 Part 2 metadata)
            result = ai_response.to_dict()
            
            logger.info(
                f"AI interpretation completed: {result.get('ai_classified_category', 'Unclassified')} "
                f"(model: {result.get('model_name', 'unknown')})"
            )
            
            return result
        
        except Exception as e:
            # If AI fails completely, system continues with defaults
            logger.error(f"⚠️ AI interpretation failed: {str(e)}")
            return self._get_default_interpretation()
    
    def _mock_interpret(self, description: str, city: str, locality: str) -> Dict:
        """
        Mock interpretation logic (placeholder for development).
        
        This simulates AI response using simple keyword matching.
        Will be replaced with actual Gemini API call in production.
        
        The logic here demonstrates what the AI SHOULD do:
        - Classify based on content
        - Suggest severity based on language
        - Extract meaningful keywords
        - Create neutral summary
        """
        desc_lower = description.lower()
        
        # 1. CLASSIFY ISSUE CATEGORY (AI-inferred, distinct from user-selected issue_type)
        # Based on keywords in description
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
        # Based on urgency language (NOT verification)
        severity_hint = "Low"
        
        if any(word in desc_lower for word in ["urgent", "serious", "major", "severe", "dangerous", "blocking"]):
            severity_hint = "High"
        elif any(word in desc_lower for word in ["moderate", "significant", "concerning", "growing"]):
            severity_hint = "Medium"
        
        # 3. EXTRACT KEYWORDS
        # Important words that help categorize the report
        words = description.split()
        # Filter out common words, keep meaningful ones
        stop_words = {"the", "and", "is", "in", "on", "at", "to", "a", "an", "of", "for"}
        keywords = [
            w.strip(".,!?").lower() 
            for w in words 
            if len(w) > 3 and w.lower() not in stop_words
        ][:5]  # Top 5 keywords
        
        # 4. GENERATE NEUTRAL SUMMARY
        # First sentence or first 100 chars
        summary = description.split('.')[0].strip()
        if len(summary) > 100:
            summary = summary[:97] + "..."
        
        return {
            "ai_classified_category": ai_classified_category,
            "severity_hint": severity_hint,
            "keywords": keywords,
            "summary": summary
        }
    
    def _get_default_interpretation(self) -> Dict:
        """
        Return safe default interpretation when AI fails completely.
        
        This ensures the system continues to work even if AI is unavailable.
        Reports are still accepted and stored.
        Includes Phase-3 Part 2 metadata fields.
        """
        from datetime import datetime
        return {
            "ai_classified_category": "Unclassified",
            "severity_hint": "Unknown",
            "keywords": [],
            "summary": "AI interpretation unavailable",
            "model_name": "fallback",
            "model_version": "1.0.0",
            "inference_timestamp": datetime.utcnow().isoformat(),
            "error": "All AI providers failed"
        }


# Global interpreter instance (singleton pattern)
_interpreter = None


def get_ai_interpreter() -> AIInterpreter:
    """
    Get or create AI interpreter singleton instance.
    
    Returns:
        AIInterpreter: The global AI interpreter instance
    """
    global _interpreter
    if _interpreter is None:
        _interpreter = AIInterpreter()
    return _interpreter
