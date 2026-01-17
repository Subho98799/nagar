"""
WhatsApp Alert Simulator

SIMULATED WhatsApp alert generation for civic issues.
No actual sending, credentials, or webhooks.

This is a read-only preview service for demonstration.
"""

from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


def generate_whatsapp_alert(issue: Dict) -> Dict:
    """
    Generate a simulated WhatsApp alert preview for an issue.
    
    This is a SIMULATION - no messages are sent.
    Returns preview data for dashboard display.
    
    Args:
        issue: The issue document dict (from Firestore)
    
    Returns:
        Dict with alert preview:
        {
            "message_preview": string,
            "audience_scope": string,
            "language": string,
            "issue_id": string
        }
    """
    try:
        issue_id = issue.get("id", "")
        issue_type = issue.get("issue_type", "Issue")
        city = issue.get("city", "")
        locality = issue.get("locality", "")
        confidence = issue.get("confidence", "LOW")
        report_count = issue.get("report_count", 0)
        
        # Get AI metadata if available
        ai_metadata = issue.get("ai_metadata", {})
        ai_summary = ai_metadata.get("summary", "")
        ai_language = ai_metadata.get("language", "English")
        
        # Build message preview
        location = locality if locality else city
        if not location:
            location = "the area"
        
        # Use AI summary if available, otherwise generate basic message
        if ai_summary:
            message_preview = f"🚨 {issue_type} Alert\n\n{ai_summary}\n\n📍 Location: {location}\n📊 Reports: {report_count}\n\nStay informed. Report updates: nagaralert.in"
        else:
            message_preview = f"🚨 {issue_type} Alert\n\nMultiple reports received about {issue_type.lower()} issues in {location}.\n\n📊 Total Reports: {report_count}\n\nStay informed. Report updates: nagaralert.in"
        
        # Determine audience scope based on confidence
        if confidence == "HIGH":
            audience_scope = f"All residents in {locality or city}"
        elif confidence == "MEDIUM":
            audience_scope = f"Residents in {locality or city} (targeted)"
        else:
            audience_scope = f"Local area residents (limited)"
        
        return {
            "message_preview": message_preview,
            "audience_scope": audience_scope,
            "language": ai_language if ai_language else "English",
            "issue_id": issue_id
        }
    
    except Exception as e:
        logger.warning(f"Failed to generate WhatsApp alert preview: {e}")
        return {
            "message_preview": "Alert preview unavailable",
            "audience_scope": "Unknown",
            "language": "English",
            "issue_id": issue.get("id", "")
        }
