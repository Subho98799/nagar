"""
AI Issue Enrichment Service

OPTIONAL, SAFE, NON-BLOCKING LLM-based issue enrichment.

CRITICAL GUARANTEES:
- ONLY summarizes existing issues
- NEVER makes decisions
- NEVER affects confidence, status, severity, priority
- FAILS SILENTLY
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional
import logging
import json
import requests

from app.core.settings import settings

logger = logging.getLogger(__name__)


def enrich_issue(issue: Dict, reports: List[Dict]) -> Dict:
    """
    Enrich an issue with AI-generated summary, title, keywords, and language detection.
    
    This is a safe, non-blocking operation.
    Never raises exceptions. Returns empty dict on failure.
    
    Args:
        issue: The issue document dict (from Firestore)
        reports: List of report dicts that are linked to this issue
    
    Returns:
        Dict with enrichment data:
        {
            "summary": string (1-2 lines, civic tone),
            "title": string (≤8 words),
            "keywords": [string],
            "language": "English" | "Hinglish" | "Hindi"
        }
        Returns empty dict {} on failure or if AI disabled.
    """
    # Check if AI is enabled
    if not settings.AI_ENABLED:
        return {}
    
    try:
        # Build prompt from issue and reports
        prompt = _build_enrichment_prompt(issue, reports)
        
        # Call LLM (with timeout protection)
        ai_result = _call_llm_api(prompt)
        
        if ai_result:
            return {
                "summary": ai_result.get("summary", ""),
                "title": ai_result.get("title", ""),
                "keywords": ai_result.get("keywords", []),
                "language": ai_result.get("language", "English")
            }
        else:
            return {}
    
    except Exception as e:
        # Fail silently - log warning but don't raise
        logger.warning(f"⚠️ AI enrichment failed: {e}", exc_info=False)
        return {}


def _build_enrichment_prompt(issue: Dict, reports: List[Dict]) -> str:
    """
    Build a neutral, civic-focused prompt for LLM enrichment.
    
    Guidelines:
    - Civic neutral tone
    - No speculation
    - No authority claims
    - Simple public-facing language
    - Support Hinglish inputs
    """
    issue_type = issue.get("issue_type", "Unknown")
    city = issue.get("city", "")
    locality = issue.get("locality", "")
    report_count = len(reports)
    
    # Collect report descriptions (may be in Hinglish)
    descriptions = []
    for report in reports[:15]:  # Limit to first 15 reports
        desc = report.get("description", "").strip()
        if desc:
            descriptions.append(desc)
    
    combined_descriptions = "\n".join([f"- {desc}" for desc in descriptions])
    
    prompt = f"""You are assisting a civic intelligence system that aggregates citizen reports.

Issue Context:
- Type: {issue_type}
- Location: {locality or city}
- Number of reports: {report_count}

Report Descriptions (may be in English, Hindi, or Hinglish):
{combined_descriptions}

Task:
Provide a JSON response with:
{{
  "summary": "A neutral 1-2 sentence summary in civic tone. Use simple, public-facing language. Preserve meaning from Hinglish if present.",
  "title": "A concise title (≤8 words) in English",
  "keywords": ["keyword1", "keyword2", "keyword3"],
  "language": "English | Hinglish | Hindi"
}}

Guidelines:
- Use calm, factual, civic-neutral language
- Do NOT speculate or make claims about authority
- Do NOT use words like "urgent", "critical", "emergency" unless explicitly stated
- Focus on WHAT was reported, not urgency or verification
- If input is Hinglish, understand it and output in neutral English
- Title should be clear and concise (≤8 words)
- Keywords should be relevant and specific (3-5 items)
- language should indicate the primary language detected in reports"""
    
    return prompt


def _call_llm_api(prompt: str) -> Optional[Dict]:
    """
    Call LLM API based on AI_PROVIDER setting.
    
    Returns:
        Dict with enrichment result, or None on failure
    """
    if not settings.AI_ENABLED:
        return None
    
    # Determine provider
    ai_provider = getattr(settings, 'AI_PROVIDER', 'openai').lower()
    
    if ai_provider == 'openai':
        return _call_openai_api(prompt)
    elif ai_provider == 'gemini':
        return _call_gemini_api(prompt)
    else:
        logger.warning(f"Unknown AI_PROVIDER: {ai_provider}")
        return None


def _call_openai_api(prompt: str) -> Optional[Dict]:
    """Call OpenAI API for enrichment."""
    api_key = settings.OPENAI_API_KEY
    if not api_key:
        logger.debug("OpenAI API key not configured")
        return None
    
    try:
        url = "https://api.openai.com/v1/chat/completions"
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "gpt-3.5-turbo",
            "messages": [
                {
                    "role": "system",
                    "content": "You are a helpful assistant for a civic intelligence system. Output only valid JSON."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.3,
            "max_tokens": 300
        }
        
        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=6.0  # 6 second timeout as per requirements
        )
        
        if response.status_code != 200:
            logger.warning(f"OpenAI API returned status {response.status_code}")
            return None
        
        data = response.json()
        text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        
        # Parse JSON response
        return _parse_llm_response(text)
    
    except Exception as e:
        logger.warning(f"OpenAI API call failed: {e}")
        return None


def _call_gemini_api(prompt: str) -> Optional[Dict]:
    """Call Gemini API for enrichment."""
    api_key = settings.GEMINI_API_KEY
    if not api_key:
        logger.debug("Gemini API key not configured")
        return None
    
    try:
        # Use HTTP API (no external dependencies)
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={api_key}"
        
        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }]
        }
        
        response = requests.post(
            url,
            json=payload,
            timeout=6.0  # 6 second timeout as per requirements
        )
        
        if response.status_code != 200:
            logger.warning(f"Gemini API returned status {response.status_code}")
            return None
        
        data = response.json()
        text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
        
        # Parse JSON response
        return _parse_llm_response(text)
    
    except Exception as e:
        logger.warning(f"Gemini API call failed: {e}")
        return None


def _parse_llm_response(text: str) -> Optional[Dict]:
    """
    Parse LLM response into required schema.
    
    Expected schema:
    {
      "summary": string,
      "title": string,
      "keywords": [string],
      "language": "English" | "Hinglish" | "Hindi"
    }
    """
    try:
        # Try to extract JSON from response
        # LLM might wrap JSON in markdown code blocks
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
        
        # Parse JSON
        parsed = json.loads(text)
        
        # Build result with required schema
        result = {
            "summary": parsed.get("summary", ""),
            "title": parsed.get("title", ""),
            "keywords": parsed.get("keywords", []),
            "language": parsed.get("language", "English")
        }
        
        # Validate required fields
        if not result["summary"]:
            logger.warning("LLM response missing summary")
            return None
        
        # Ensure keywords is a list
        if not isinstance(result["keywords"], list):
            result["keywords"] = []
        
        # Validate language
        if result["language"] not in ["English", "Hinglish", "Hindi"]:
            result["language"] = "English"
        
        # Ensure title is ≤8 words
        title_words = result["title"].split()
        if len(title_words) > 8:
            result["title"] = " ".join(title_words[:8])
        
        return result
    
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse LLM JSON response: {e}")
        return None
    except Exception as e:
        logger.warning(f"Failed to process LLM response: {e}")
        return None
