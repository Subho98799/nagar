"""
LLM Provider for Issue Enrichment - Phase 6

Real LLM integration for enriching issues with summaries, keywords, etc.
Supports Gemini and OpenAI-style APIs.
Handles Hinglish (Hindi + English mix) input.
"""

from app.services.ai_enrichment.base import IssueEnrichmentProvider, IssueEnrichmentResponse
from app.core.settings import settings
from datetime import datetime
from typing import Dict, List, Optional
import logging
import json
import requests

logger = logging.getLogger(__name__)


class LLMEnrichmentProvider(IssueEnrichmentProvider):
    """
    Real LLM provider for issue enrichment.
    
    Supports:
    - Google Gemini API (via GEMINI_API_KEY)
    - OpenAI API (via OPENAI_API_KEY)
    
    Falls back gracefully if API key is missing or API call fails.
    """
    
    MODEL_NAME = "llm-enrichment"
    MODEL_VERSION = "1.0"
    TIMEOUT_SECONDS = 5.0  # 5 second timeout as per requirements (≤5 seconds)
    
    def __init__(self):
        self.gemini_api_key = settings.GEMINI_API_KEY
        self.openai_api_key = getattr(settings, 'OPENAI_API_KEY', None)
        self.enabled = bool(
            (self.gemini_api_key and self.gemini_api_key.strip()) or
            (self.openai_api_key and self.openai_api_key.strip())
        )
        
        if self.enabled:
            provider = "Gemini" if self.gemini_api_key else "OpenAI"
            logger.info(f"✅ LLM Enrichment Provider initialized: {provider}")
        else:
            logger.info(f"⚠️ LLM Enrichment Provider disabled: No API key configured")
    
    def is_enabled(self) -> bool:
        """Check if provider is enabled (has API key)."""
        return self.enabled
    
    def get_model_info(self) -> Dict[str, str]:
        """Get model information."""
        provider = "gemini" if self.gemini_api_key else "openai"
        return {
            "name": f"{provider}-{self.MODEL_NAME}",
            "version": self.MODEL_VERSION
        }
    
    def get_timeout_seconds(self) -> float:
        """Get timeout for API calls."""
        return self.TIMEOUT_SECONDS
    
    def enrich_issue(
        self,
        issue: Dict,
        reports: List[Dict]
    ) -> IssueEnrichmentResponse:
        """
        Enrich issue using LLM API.
        
        Returns safe defaults if API call fails.
        Never raises exceptions.
        """
        if not self.enabled:
            return IssueEnrichmentResponse(
                summary="",
                keywords=[],
                severity_hint="Low",
                title_suggestion="",
                summary_hinglish="",
                language_detected="English",
                model_name=self.MODEL_NAME,
                model_version=self.MODEL_VERSION,
                inference_timestamp=datetime.utcnow(),
                error="LLM API key not configured"
            )
        
        try:
            # Build prompt from issue and reports
            prompt = self._build_prompt(issue, reports)
            
            # Call LLM API (with timeout handling)
            if self.gemini_api_key:
                response_data = self._call_gemini_api(prompt)
            elif self.openai_api_key:
                response_data = self._call_openai_api(prompt)
            else:
                raise ValueError("No API key available")
            
            # Parse response
            enrichment_result = self._parse_llm_response(response_data)
            
            return IssueEnrichmentResponse(
                summary=enrichment_result.get("summary", ""),
                keywords=enrichment_result.get("keywords", []),
                severity_hint=enrichment_result.get("severity_hint", "Low"),
                title_suggestion=enrichment_result.get("title_suggestion", ""),
                summary_hinglish=enrichment_result.get("summary_hinglish", ""),
                language_detected=enrichment_result.get("language_detected", "English"),
                model_name=self.get_model_info()["name"],
                model_version=self.MODEL_VERSION,
                inference_timestamp=datetime.utcnow()
            )
        
        except Exception as e:
            # Graceful failure - return error response
            logger.warning(f"⚠️ LLM enrichment API call failed: {str(e)}")
            return IssueEnrichmentResponse(
                summary="",
                keywords=[],
                severity_hint="Low",
                title_suggestion="",
                summary_hinglish="",
                language_detected="English",
                model_name=self.MODEL_NAME,
                model_version=self.MODEL_VERSION,
                inference_timestamp=datetime.utcnow(),
                error=f"LLM API error: {str(e)}"
            )
    
    def _build_prompt(self, issue: Dict, reports: List[Dict]) -> str:
        """
        Build prompt for LLM API with Hinglish support.
        
        CRITICAL: AI must NEVER affect control flow, confidence, status, or escalation.
        This prompt is designed to only generate summaries and hints.
        """
        # Collect report descriptions (may be in Hinglish)
        report_descriptions = []
        for report in reports[:15]:  # Limit to first 15 reports for context
            desc = report.get("description", "").strip()
            if desc:
                report_descriptions.append(desc)
        
        # Combine descriptions
        combined_descriptions = "\n".join([f"- {desc}" for desc in report_descriptions])
        
        issue_type = issue.get("issue_type", "Unknown")
        city = issue.get("city", "")
        locality = issue.get("locality", "")
        report_count = len(reports)
        
        return f"""You are assisting a civic intelligence system for citizen-reported issues.

CRITICAL CONSTRAINTS:
- You ONLY summarize and extract information
- You NEVER make decisions about confidence, status, or escalation
- You NEVER affect control flow
- Output calm, neutral, citizen-readable English

---
ISSUE CONTEXT:
Type: {issue_type}
City: {city}
Locality: {locality}
Number of reports: {report_count}

REPORT DESCRIPTIONS (may be in English, Hindi, or Hinglish):
{combined_descriptions}

---
TASK:
Analyze the reports and provide a JSON response with:

{{
  "summary": "<1-2 sentence citizen-readable summary in calm English. If input is Hinglish, understand it and output in neutral English. Focus on WHAT was reported, not urgency.>",
  "summary_hinglish": "<Optional: Same summary in Hinglish if reports contain Hinglish, otherwise empty string>",
  "keywords": ["<keyword1>", "<keyword2>", "<keyword3>", "<keyword4>", "<keyword5>"],
  "severity_hint": "<one of: Low, Medium, High - based on issue type and description patterns only, NOT urgency>",
  "language_detected": "<one of: English, Hinglish, Hindi - detected from report descriptions>"
}}

REQUIREMENTS:
1. SUMMARY: Citizen-readable, calm, factual. Preserve meaning from Hinglish if present.
2. SUMMARY_HINGLISH: Provide Hinglish version if reports contain Hinglish, otherwise empty string.
3. KEYWORDS: Extract 3-5 relevant keywords from the reports (e.g., "pothole", "water leakage", "street light").
4. SEVERITY_HINT: Based on issue type and description patterns (Low/Medium/High). Do NOT infer urgency.
5. LANGUAGE_DETECTED: Detect primary language in reports (English/Hinglish/Hindi).

IMPORTANT:
- Do NOT use words like "urgent", "critical", "emergency" unless explicitly stated in reports
- Do NOT claim verification or confirmation
- Keep language calm and factual
- If input is Hinglish, understand it and output in neutral English
- Severity hint is advisory only, not a decision"""
    
    def _call_gemini_api(self, prompt: str) -> Dict:
        """Call Gemini API with timeout handling."""
        try:
            import google.generativeai as genai
            
            genai.configure(api_key=self.gemini_api_key)
            model = genai.GenerativeModel('gemini-pro')
            
            # Generate with timeout
            response = model.generate_content(
                prompt,
                request_options={"timeout": self.TIMEOUT_SECONDS}
            )
            
            return {"text": response.text}
        
        except ImportError:
            # Fallback to HTTP API if library not installed
            return self._call_gemini_http_api(prompt)
        except Exception as e:
            logger.error(f"Gemini API call failed: {e}")
            raise
    
    def _call_gemini_http_api(self, prompt: str) -> Dict:
        """Fallback: Call Gemini API via HTTP."""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={self.gemini_api_key}"
        
        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }]
        }
        
        response = requests.post(
            url,
            json=payload,
            timeout=self.TIMEOUT_SECONDS
        )
        
        if response.status_code != 200:
            raise Exception(f"Gemini API returned status {response.status_code}: {response.text}")
        
        data = response.json()
        text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
        
        return {"text": text}
    
    def _call_openai_api(self, prompt: str) -> Dict:
        """Call OpenAI API with timeout handling."""
        url = "https://api.openai.com/v1/chat/completions"
        
        headers = {
            "Authorization": f"Bearer {self.openai_api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "gpt-3.5-turbo",
            "messages": [
                {"role": "system", "content": "You are a helpful assistant for a civic intelligence system. Output only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 500
        }
        
        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=self.TIMEOUT_SECONDS
        )
        
        if response.status_code != 200:
            raise Exception(f"OpenAI API returned status {response.status_code}: {response.text}")
        
        data = response.json()
        text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        
        return {"text": text}
    
    def _parse_llm_response(self, response_data: Dict) -> Dict:
        """
        Parse LLM API response into structured format.
        
        Required fields:
        - summary: Citizen-readable summary (English)
        - summary_hinglish: Optional Hinglish summary
        - keywords: List of extracted keywords
        - severity_hint: Low/Medium/High (advisory only)
        - language_detected: English/Hinglish/Hindi
        """
        try:
            text = response_data.get("text", "")
            
            # Try to extract JSON from response
            # LLM might wrap JSON in markdown code blocks
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()
            
            # Parse JSON
            parsed = json.loads(text)
            
            # Validate and extract required fields
            result = {
                "summary": parsed.get("summary", "").strip(),
                "summary_hinglish": parsed.get("summary_hinglish", "").strip(),
                "keywords": parsed.get("keywords", []),
                "severity_hint": parsed.get("severity_hint", "Low"),
                "language_detected": parsed.get("language_detected", "English")
            }
            
            # Validate summary is present (required field)
            if not result["summary"]:
                logger.warning("LLM response missing required 'summary' field")
                raise ValueError("Missing required 'summary' field")
            
            # Ensure keywords is a list
            if not isinstance(result["keywords"], list):
                result["keywords"] = []
            # Limit keywords to 5
            result["keywords"] = result["keywords"][:5]
            
            # Validate severity_hint
            severity = result["severity_hint"].capitalize()
            if severity not in ["Low", "Medium", "High"]:
                result["severity_hint"] = "Low"
            else:
                result["severity_hint"] = severity
            
            # Validate language_detected
            language = result["language_detected"]
            if language not in ["English", "Hinglish", "Hindi"]:
                result["language_detected"] = "English"
            
            return result
        
        except Exception as e:
            logger.error(f"Failed to parse LLM response: {e}")
            logger.debug(f"Response text: {response_data.get('text', '')}")
            raise ValueError(f"Failed to parse LLM response: {str(e)}")
