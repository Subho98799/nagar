"""
Issue AI Enrichment Service

OPTIONAL, SAFE, NON-BLOCKING LLM-based issue summary layer.

CRITICAL GUARANTEES:
- ONLY summarizes existing issues
- NEVER makes decisions
- NEVER affects confidence, status, or escalation
- FAILS SILENTLY
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional
import logging
import json
import requests

from app.config.firebase import get_db
from app.core.settings import settings

logger = logging.getLogger(__name__)


def enrich_issue_with_ai(issue_id: str) -> None:
    """
    Enrich an issue with AI-generated summary.
    
    This is a fire-and-forget, non-blocking operation.
    Never raises exceptions. Fails silently.
    
    Args:
        issue_id: The issue document ID to enrich
    """
    # Check if AI is enabled
    if not settings.AI_ENABLED:
        return
    
    try:
        db = get_db()
        if db is None:
            return
        
        # Fetch issue document
        issue_ref = db.collection("issues").document(issue_id)
        issue_doc = issue_ref.get()
        
        if not issue_doc.exists:
            logger.warning(f"Issue {issue_id} not found for AI enrichment")
            return
        
        issue_data = issue_doc.to_dict()
        if not issue_data:
            return
        
        # Fetch linked reports
        report_ids = issue_data.get("report_ids", [])
        if not report_ids:
            logger.debug(f"Issue {issue_id} has no linked reports")
            return
        
        reports_ref = db.collection("reports")
        linked_reports = []
        
        for report_id in report_ids[:20]:  # Limit to first 20 reports
            try:
                report_doc = reports_ref.document(report_id).get()
                if report_doc.exists:
                    report_data = report_doc.to_dict()
                    if report_data:
                        linked_reports.append(report_data)
            except Exception:
                continue
        
        if not linked_reports:
            logger.debug(f"No valid reports found for issue {issue_id}")
            return
        
        # Build prompt from issue and reports
        prompt = _build_enrichment_prompt(issue_data, linked_reports)
        
        # Call LLM (non-blocking, with timeout)
        ai_result = _call_llm_api(prompt)
        
        if ai_result:
            # Store result in ai_metadata
            issue_ref.update({"ai_metadata": ai_result})
            logger.info(f"✅ AI enrichment completed for issue {issue_id}")
        else:
            logger.debug(f"AI enrichment returned no result for issue {issue_id}")
    
    except Exception as e:
        # Fail silently - log warning but don't raise
        logger.warning(f"⚠️ AI enrichment failed for issue {issue_id}: {e}", exc_info=False)


def _build_enrichment_prompt(issue: Dict, reports: List[Dict]) -> str:
    """
    Build a neutral, civic-focused prompt for LLM enrichment.
    
    Guidelines:
    - Neutral civic tone
    - No urgency language
    - No instructions
    - No verification claims
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
  "summary": "A neutral 1-2 sentence summary in calm English. Preserve meaning from Hinglish if present.",
  "key_patterns": ["pattern1", "pattern2", "pattern3"],
  "language": "en | hi | hinglish",
  "generated_at": "ISO timestamp",
  "model": "model-name"
}}

Guidelines:
- Use calm, factual language
- Do NOT use words like "urgent", "critical", "emergency" unless explicitly stated
- Do NOT claim verification or confirmation
- Focus on WHAT was reported, not urgency
- If input is Hinglish, understand it and output in neutral English
- key_patterns should be relevant keywords or themes (3-5 items)
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
            "max_tokens": 500
        }
        
        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=8.0  # 8 second timeout
        )
        
        if response.status_code != 200:
            logger.warning(f"OpenAI API returned status {response.status_code}")
            return None
        
        data = response.json()
        text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        
        # Parse JSON response
        return _parse_llm_response(text, "gpt-3.5-turbo")
    
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
        # Try HTTP API first (no external dependencies)
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={api_key}"
        
        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }]
        }
        
        response = requests.post(
            url,
            json=payload,
            timeout=8.0  # 8 second timeout
        )
        
        if response.status_code != 200:
            logger.warning(f"Gemini API returned status {response.status_code}")
            return None
        
        data = response.json()
        text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
        
        # Parse JSON response
        return _parse_llm_response(text, "gemini-pro")
    
    except Exception as e:
        logger.warning(f"Gemini API call failed: {e}")
        return None


def _parse_llm_response(text: str, model_name: str) -> Optional[Dict]:
    """
    Parse LLM response into required schema.
    
    Expected schema:
    {
      "summary": string,
      "key_patterns": [string],
      "language": "en | hi | hinglish",
      "generated_at": timestamp,
      "model": string
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
            "key_patterns": parsed.get("key_patterns", []),
            "language": parsed.get("language", "en"),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "model": model_name
        }
        
        # Validate required fields
        if not result["summary"]:
            logger.warning("LLM response missing summary")
            return None
        
        # Ensure key_patterns is a list
        if not isinstance(result["key_patterns"], list):
            result["key_patterns"] = []
        
        # Validate language
        if result["language"] not in ["en", "hi", "hinglish"]:
            result["language"] = "en"
        
        return result
    
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse LLM JSON response: {e}")
        return None
    except Exception as e:
        logger.warning(f"Failed to process LLM response: {e}")
        return None
