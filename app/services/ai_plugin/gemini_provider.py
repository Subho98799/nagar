"""
Gemini AI Provider - Real LLM integration (Phase-3 Part 2).

Uses Google Gemini API for enhanced AI interpretation.
Fails gracefully and falls back to mock provider if unavailable.
"""

from app.services.ai_plugin.base import AIProvider, AIResponse
from app.core.settings import settings
from datetime import datetime
from typing import Dict, Optional
import logging
import json

logger = logging.getLogger(__name__)


class GeminiAIProvider(AIProvider):
    """
    Google Gemini API provider for AI interpretation.
    
    Requires GEMINI_API_KEY in environment variables.
    Fails gracefully if API key is missing or API call fails.
    """
    
    MODEL_NAME = "gemini-pro"
    MODEL_VERSION = "1.0"
    TIMEOUT_SECONDS = 10.0  # 10 second timeout
    API_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent"
    
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.enabled = bool(self.api_key and self.api_key.strip())
        
        if self.enabled:
            logger.info(f"✅ Gemini AI Provider initialized: {self.MODEL_NAME}")
        else:
            logger.info(f"⚠️ Gemini AI Provider disabled: No API key configured")
    
    def is_enabled(self) -> bool:
        """Check if provider is enabled (has API key)."""
        return self.enabled
    
    def get_model_info(self) -> Dict[str, str]:
        """Get model information."""
        return {
            "name": self.MODEL_NAME,
            "version": self.MODEL_VERSION
        }
    
    def get_timeout_seconds(self) -> float:
        """Get timeout for API calls."""
        return self.TIMEOUT_SECONDS
    
    def interpret_report(
        self,
        description: str,
        city: str = "",
        locality: str = ""
    ) -> AIResponse:
        """
        Interpret report using Gemini API.
        
        Returns safe defaults if API call fails.
        Never raises exceptions.
        """
        if not self.enabled:
            # Return error response if not enabled
            return AIResponse(
                ai_classified_category="Unclassified",
                severity_hint="Unknown",
                keywords=[],
                summary="AI interpretation unavailable (Gemini disabled)",
                model_name=self.MODEL_NAME,
                model_version=self.MODEL_VERSION,
                inference_timestamp=datetime.utcnow(),
                error="Gemini API key not configured"
            )
        
        try:
            # Build prompt
            prompt = self._build_prompt(description, city, locality)
            
            # Call Gemini API (with timeout handling)
            response_data = self._call_gemini_api(prompt)
            
            # Parse response
            ai_result = self._parse_gemini_response(response_data)
            
            return AIResponse(
                ai_classified_category=ai_result.get("ai_classified_category", "General"),
                severity_hint=ai_result.get("severity_hint", "Low"),
                keywords=ai_result.get("keywords", []),
                summary=ai_result.get("summary", description[:100]),
                model_name=self.MODEL_NAME,
                model_version=self.MODEL_VERSION,
                inference_timestamp=datetime.utcnow(),
                ai_confidence_score=ai_result.get("ai_confidence_score")  # Optional
            )
        
        except Exception as e:
            # Graceful failure - return error response
            logger.warning(f"⚠️ Gemini API call failed: {str(e)}")
            return AIResponse(
                ai_classified_category="Unclassified",
                severity_hint="Unknown",
                keywords=[],
                summary="AI interpretation unavailable (Gemini API error)",
                model_name=self.MODEL_NAME,
                model_version=self.MODEL_VERSION,
                inference_timestamp=datetime.utcnow(),
                error=f"Gemini API error: {str(e)}"
            )
    
    def _build_prompt(self, description: str, city: str, locality: str) -> str:
        """Build prompt for Gemini API."""
        return f"""You are an AI assistant helping to interpret citizen reports in Indian cities.

Your role is STRICTLY LIMITED to:
1. Classifying the type of issue
2. Suggesting a severity level
3. Extracting relevant keywords
4. Generating a neutral summary

You must NOT:
- Verify or confirm the report's authenticity
- Use words like "verified", "confirmed", "emergency", "critical alert"
- Make predictions about future events
- Suggest actions or escalations
- Judge the truthfulness of the report

---
REPORT DETAILS:
City: {city}
Locality: {locality}
Description: {description}

---
TASK:
Provide a JSON response with the following structure:

{{
  "ai_classified_category": "<one of: Traffic & Roads, Water & Sanitation, Electricity, Waste Management, Healthcare, Public Safety, Infrastructure, General>",
  "severity_hint": "<one of: Low, Medium, High>",
  "keywords": ["<keyword1>", "<keyword2>", "<keyword3>"],
  "summary": "<1-2 sentence neutral summary in simple English or Hinglish>",
  "ai_confidence_score": <optional float 0.0-1.0>
}}

Use calm, neutral, and factual language. Avoid dramatic or alarming words.
Focus on WHAT was reported, not whether it's true."""

    def _call_gemini_api(self, prompt: str) -> Dict:
        """
        Call Gemini API with timeout handling.
        
        In production, use google-generativeai library.
        For now, this is a placeholder that demonstrates the structure.
        """
        # TODO: Implement actual Gemini API call using google-generativeai
        # For now, raise NotImplementedError to trigger fallback
        raise NotImplementedError(
            "Gemini API integration not yet implemented. "
            "Install google-generativeai and implement _call_gemini_api method."
        )
        
        # Example implementation structure:
        # import google.generativeai as genai
        # genai.configure(api_key=self.api_key)
        # model = genai.GenerativeModel('gemini-pro')
        # response = model.generate_content(prompt)
        # return response.text
    
    def _parse_gemini_response(self, response_data: Dict) -> Dict:
        """Parse Gemini API response into structured format."""
        try:
            # Parse JSON response from Gemini
            if isinstance(response_data, str):
                parsed = json.loads(response_data)
            else:
                parsed = response_data
            
            # Validate required fields
            result = {
                "ai_classified_category": parsed.get("ai_classified_category", "General"),
                "severity_hint": parsed.get("severity_hint", "Low"),
                "keywords": parsed.get("keywords", []),
                "summary": parsed.get("summary", ""),
            }
            
            # Optional confidence score
            if "ai_confidence_score" in parsed:
                result["ai_confidence_score"] = float(parsed["ai_confidence_score"])
            
            return result
        
        except Exception as e:
            logger.error(f"Failed to parse Gemini response: {e}")
            raise
