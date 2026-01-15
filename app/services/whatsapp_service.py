"""
WhatsApp Alert Service - Gated alert generation for citizen awareness.

DESIGN PRINCIPLES (CRITICAL):
- WhatsApp is a COMMUNICATION CHANNEL, not a broadcast engine
- Alerts are GATED by strict eligibility rules
- Only HIGH confidence + CONFIRMED reports are eligible
- Alerts are LOCALIZED and MINIMAL
- Alerts are SIMULATED in this prototype (no real API)

ELIGIBILITY RULES:
1. confidence == "HIGH"
2. status == "CONFIRMED"
3. Admin must have reviewed (reviewed_at exists)

ALERT MESSAGE RULES:
- Maximum 2 lines
- Calm, neutral tone
- Location-specific
- NO urgency language
- NO alarming words

WHAT THIS SERVICE DOES:
✅ Check eligibility for WhatsApp alerts
✅ Generate calm, localized alert messages
✅ Log alerts to Firestore (simulated send)
✅ Update report with alert status

WHAT THIS SERVICE DOES NOT:
❌ Send real WhatsApp messages (prototype only)
❌ Broadcast city-wide
❌ Trigger without admin review
❌ Use alarming language
"""

from firebase_admin import firestore
from app.config.firebase import get_db
from datetime import datetime
from typing import Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class WhatsAppService:
    """
    WhatsApp alert gating and message generation service.
    
    This is a SIMULATED service for prototype purposes.
    Real WhatsApp integration (Twilio) can replace the send logic later.
    """
    
    # Alert status values
    STATUS_NOT_SENT = "NOT_SENT"
    STATUS_SENT = "SENT"
    STATUS_NOT_ELIGIBLE = "NOT_ELIGIBLE"
    
    def __init__(self):
        self.db = get_db()
    
    def should_send_whatsapp_alert(self, report: Dict) -> Tuple[bool, str]:
        """
        Check if a report is eligible for WhatsApp alert.
        
        STRICT ELIGIBILITY RULES:
        1. confidence == "HIGH"
        2. status == "CONFIRMED"
        3. reviewed_at exists (admin has reviewed)
        4. whatsapp_alert_status != "SENT" (not already sent)
        
        Args:
            report: Report dictionary with all fields
        
        Returns:
            Tuple of (is_eligible: bool, reason: str)
        """
        # Rule 1: Must have HIGH confidence
        confidence = report.get("confidence", "LOW")
        if confidence != "HIGH":
            return False, f"Confidence is {confidence}, must be HIGH"
        
        # Rule 2: Must be CONFIRMED status
        status = report.get("status", "UNDER_OBSERVATION")
        if status != "CONFIRMED":
            return False, f"Status is {status}, must be CONFIRMED"
        
        # Rule 3: Must be admin-reviewed
        reviewed_at = report.get("reviewed_at")
        if not reviewed_at:
            return False, "Report has not been reviewed by admin"
        
        # Rule 4: Must not already be sent
        alert_status = report.get("whatsapp_alert_status", self.STATUS_NOT_SENT)
        if alert_status == self.STATUS_SENT:
            return False, "WhatsApp alert already sent"
        
        # All rules passed
        return True, "Report is eligible for WhatsApp alert"
    
    def generate_alert_message(self, report: Dict) -> str:
        """
        Generate a calm, localized WhatsApp alert message.
        
        MESSAGE RULES:
        - Maximum 2 lines
        - Calm, neutral tone
        - Location-specific
        - NO urgency language ("emergency", "urgent", "critical")
        - NO alarming words ("danger", "warning", "alert")
        
        Args:
            report: Report dictionary
        
        Returns:
            str: Formatted alert message (2 lines max)
        """
        # Extract location info
        locality = report.get("locality", "the area")
        city = report.get("city", "")
        
        # Get issue type (prefer AI-classified category, fallback to user-selected issue_type)
        ai_metadata = report.get("ai_metadata", {})
        issue_type = ai_metadata.get("ai_classified_category", "")
        if not issue_type:
            # Fallback to user-selected issue_type
            issue_type = report.get("issue_type", "")
        if not issue_type:
            issue_type = "An issue"
        
        # Build location string
        if city:
            location = f"{locality}, {city}"
        else:
            location = locality
        
        # Generate calm message based on issue type
        message = self._build_calm_message(issue_type, location)
        
        return message
    
    def _build_calm_message(self, issue_type: str, location: str) -> str:
        """
        Build a calm, 2-line message based on issue type.
        
        Uses neutral language and avoids:
        - Urgency words
        - Alarming words
        - Predictions
        - Recommendations
        """
        # Normalize issue type
        issue_lower = issue_type.lower()
        
        # Line 1: What and where (factual, calm)
        if "traffic" in issue_lower or "road" in issue_lower:
            line1 = f"Traffic disruption reported near {location}."
        elif "water" in issue_lower or "sanitation" in issue_lower:
            line1 = f"Water supply issue reported in {location}."
        elif "electricity" in issue_lower or "power" in issue_lower:
            line1 = f"Power supply issue reported in {location}."
        elif "waste" in issue_lower or "garbage" in issue_lower:
            line1 = f"Waste management issue reported in {location}."
        elif "health" in issue_lower or "medical" in issue_lower:
            line1 = f"Healthcare-related issue reported in {location}."
        elif "safety" in issue_lower:
            line1 = f"Public safety concern reported in {location}."
        elif "infrastructure" in issue_lower or "building" in issue_lower:
            line1 = f"Infrastructure issue reported in {location}."
        else:
            line1 = f"{issue_type} issue reported in {location}."
        
        # Line 2: Purpose (always the same, calm)
        line2 = "Shared for public awareness."
        
        # Combine (2 lines max)
        return f"{line1}\n{line2}"
    
    def process_alert(self, report: Dict) -> Dict:
        """
        Process a report for WhatsApp alert eligibility and send (simulated).
        
        Flow:
        1. Check eligibility
        2. If eligible:
           - Generate message
           - Log to Firestore (whatsapp_alert_log collection)
           - Update report (whatsapp_alert_status = SENT)
        3. If not eligible:
           - Return reason
        
        Args:
            report: Report dictionary (must include 'id')
        
        Returns:
            dict: Processing result with status and details
        """
        report_id = report.get("id")
        
        if not report_id:
            return {
                "success": False,
                "error": "Report ID is missing"
            }
        
        # Step 1: Check eligibility
        is_eligible, reason = self.should_send_whatsapp_alert(report)
        
        if not is_eligible:
            logger.info(f"Report {report_id} not eligible for WhatsApp: {reason}")
            return {
                "success": False,
                "eligible": False,
                "reason": reason,
                "whatsapp_alert_status": self.STATUS_NOT_ELIGIBLE
            }
        
        # Step 2: Generate message
        message = self.generate_alert_message(report)
        
        # Step 3: Log to Firestore (SIMULATED SEND)
        try:
            alert_log = self._log_alert(report, message)
            
            # Step 4: Update report status
            self._update_report_alert_status(report_id)
            
            logger.info(f"✅ WhatsApp alert SIMULATED for report {report_id}")
            
            return {
                "success": True,
                "eligible": True,
                "whatsapp_alert_status": self.STATUS_SENT,
                "message": message,
                "alert_log_id": alert_log.get("id"),
                "note": "SIMULATED - No real message sent (prototype mode)"
            }
        
        except Exception as e:
            logger.error(f"❌ Failed to process WhatsApp alert for {report_id}: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _log_alert(self, report: Dict, message: str) -> Dict:
        """
        Log the alert to Firestore's whatsapp_alert_log collection.
        
        This creates an audit trail of all alerts sent (simulated).
        
        Args:
            report: Original report dictionary
            message: Generated alert message
        
        Returns:
            dict: Alert log entry with ID
        """
        report_id = report.get("id")
        
        # Build alert log entry
        alert_entry = {
            "report_id": report_id,
            "city": report.get("city", ""),
            "locality": report.get("locality", ""),
            "issue_type": report.get("ai_metadata", {}).get("ai_classified_category", "") or report.get("issue_type", ""),
            "message": message,
            "confidence": report.get("confidence", ""),
            "status": report.get("status", ""),
            "admin_note": report.get("admin_note", ""),
            "simulated": True,  # Flag indicating this is a prototype
            "created_at": firestore.SERVER_TIMESTAMP
        }
        
        # Store in Firestore
        doc_ref = self.db.collection("whatsapp_alert_log").document()
        doc_ref.set(alert_entry)
        
        logger.info(f"Alert logged to Firestore: {doc_ref.id}")
        
        # Return with ID
        alert_entry["id"] = doc_ref.id
        return alert_entry
    
    def _update_report_alert_status(self, report_id: str) -> None:
        """
        Update the report's whatsapp_alert_status to SENT.
        
        Args:
            report_id: Firestore document ID of the report
        """
        doc_ref = self.db.collection("reports").document(report_id)
        doc_ref.update({
            "whatsapp_alert_status": self.STATUS_SENT,
            "whatsapp_alert_sent_at": firestore.SERVER_TIMESTAMP
        })
        
        logger.info(f"Report {report_id} updated: whatsapp_alert_status = SENT")
    
    def get_alert_log(self, limit: int = 50) -> list:
        """
        Retrieve recent WhatsApp alert logs.
        
        Args:
            limit: Maximum number of logs to retrieve (default 50)
        
        Returns:
            list: Recent alert log entries
        """
        logs_ref = self.db.collection("whatsapp_alert_log")
        query = logs_ref.order_by("created_at", direction=firestore.Query.DESCENDING).limit(limit)
        
        docs = query.stream()
        
        logs = []
        for doc in docs:
            data = doc.to_dict()
            data["id"] = doc.id
            logs.append(data)
        
        return logs


# Global service instance (singleton pattern)
_whatsapp_service = None


def get_whatsapp_service() -> WhatsAppService:
    """
    Get or create WhatsAppService singleton instance.
    
    Returns:
        WhatsAppService: The global WhatsApp service instance
    """
    global _whatsapp_service
    if _whatsapp_service is None:
        _whatsapp_service = WhatsAppService()
    return _whatsapp_service
