"""
Escalation Engine - Phase-3 rule-based escalation system.

DESIGN PRINCIPLES:
- Escalation is ADVISORY, NOT authoritative
- Escalation does NOT auto-notify authorities
- Escalation only marks reports as "ESCALATION_CANDIDATE"
- Escalation is a PARALLEL signal to status workflow
- All escalation changes are logged for auditability
"""

from firebase_admin import firestore
from app.config.firebase import get_db
from datetime import datetime, timedelta
from typing import Dict, Optional, List
import logging

logger = logging.getLogger(__name__)


class EscalationEngine:
    """
    Rule-based escalation engine that marks reports for escalation.
    
    Escalation triggers:
    1. HIGH confidence + repeated locality reports
    2. VERIFIED issues persisting beyond time threshold
    3. Safety-critical issue_types
    4. High priority_score threshold
    """
    
    # Configuration: Escalation thresholds
    ESCALATION_PRIORITY_THRESHOLD = 70  # Priority score >= 70 triggers escalation
    ESCALATION_PERSISTENCE_HOURS = 48   # VERIFIED issues open >48 hours
    ESCALATION_LOCALITY_REPORT_COUNT = 5  # 5+ reports in same locality
    
    # Configuration: Safety-critical issue types
    SAFETY_CRITICAL_ISSUE_TYPES = [
        "Safety",
        "Safety Concern",
        "Public Safety"
    ]
    
    def __init__(self):
        self.db = get_db()
    
    def evaluate_escalation(self, report: Dict) -> Dict:
        """
        Evaluate if a report should be escalated.
        
        Args:
            report: Report dictionary with all fields
        
        Returns:
            Dict with escalation_flag, escalation_reason, and trigger details
        """
        try:
            escalation_flag = False
            escalation_reasons = []
            trigger_details = {}
            
            # Rule 1: High priority score
            priority_score = report.get("priority_score", 0)
            if priority_score >= self.ESCALATION_PRIORITY_THRESHOLD:
                escalation_flag = True
                escalation_reasons.append(f"High priority score ({priority_score} >= {self.ESCALATION_PRIORITY_THRESHOLD})")
                trigger_details["priority_score"] = priority_score
            
            # Rule 2: HIGH confidence + locality repetition
            confidence = report.get("confidence", "LOW")
            locality = report.get("locality")
            city = report.get("city")
            
            if confidence == "HIGH" and locality and city:
                locality_count = self._count_reports_in_locality(
                    locality=locality,
                    city=city,
                    exclude_report_id=report.get("id")
                )
                
                if locality_count >= self.ESCALATION_LOCALITY_REPORT_COUNT:
                    escalation_flag = True
                    escalation_reasons.append(
                        f"HIGH confidence + {locality_count} reports in {locality}"
                    )
                    trigger_details["locality_count"] = locality_count
            
            # Rule 3: VERIFIED status + time persistence
            report_status = report.get("status", "UNDER_REVIEW")
            created_at = report.get("created_at")
            
            if report_status == "VERIFIED" and created_at:
                persistence_hours = self._calculate_persistence_hours(created_at)
                if persistence_hours >= self.ESCALATION_PERSISTENCE_HOURS:
                    escalation_flag = True
                    escalation_reasons.append(
                        f"VERIFIED issue persisting for {persistence_hours:.1f} hours"
                    )
                    trigger_details["persistence_hours"] = persistence_hours
            
            # Rule 4: Safety-critical issue type
            issue_type = report.get("issue_type", "")
            if issue_type in self.SAFETY_CRITICAL_ISSUE_TYPES:
                escalation_flag = True
                escalation_reasons.append(f"Safety-critical issue type: {issue_type}")
                trigger_details["issue_type"] = issue_type
            
            # Build escalation reason string
            escalation_reason = " | ".join(escalation_reasons) if escalation_reasons else None
            
            if escalation_flag:
                logger.info(f"Report {report.get('id')} flagged for escalation: {escalation_reason}")
            else:
                logger.debug(f"Report {report.get('id')} does not meet escalation criteria")
            
            return {
                "escalation_flag": escalation_flag,
                "escalation_reason": escalation_reason,
                "trigger_details": trigger_details
            }
        
        except Exception as e:
            logger.error(f"Failed to evaluate escalation for report {report.get('id')}: {str(e)}")
            # Default to no escalation on error
            return {
                "escalation_flag": False,
                "escalation_reason": "Escalation evaluation failed",
                "trigger_details": {}
            }
    
    def update_escalation_flag(
        self,
        report_id: str,
        escalation_flag: bool,
        escalation_reason: Optional[str] = None,
        changed_by: str = "system"
    ) -> Dict:
        """
        Update escalation flag and log change in escalation_history.
        
        Args:
            report_id: Firestore document ID
            escalation_flag: New escalation flag value
            escalation_reason: Reason for escalation (if flagging)
            changed_by: Who/what changed the flag (system or reviewer_id)
        
        Returns:
            Updated report dictionary
        """
        doc_ref = self.db.collection("reports").document(report_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            raise ValueError(f"Report {report_id} not found")
        
        current_data = doc.to_dict()
        current_escalation_flag = current_data.get("escalation_flag", False)
        
        # Only update if flag changed
        if current_escalation_flag != escalation_flag:
            # Get existing escalation_history
            escalation_history = current_data.get("escalation_history", [])
            if not isinstance(escalation_history, list):
                escalation_history = []
            
            # Create history entry
            history_entry = {
                "from_flag": current_escalation_flag,
                "to_flag": escalation_flag,
                "changed_by": changed_by,
                "timestamp": firestore.SERVER_TIMESTAMP,
                "reason": escalation_reason or ""
            }
            
            escalation_history.append(history_entry)
            
            # Update document
            update_data = {
                "escalation_flag": escalation_flag,
                "escalation_history": escalation_history
            }
            
            if escalation_reason:
                update_data["escalation_reason"] = escalation_reason
            
            doc_ref.update(update_data)
            
            logger.info(
                f"Escalation flag updated for report {report_id}: "
                f"{current_escalation_flag} → {escalation_flag} by {changed_by}"
            )
        
        # Retrieve updated document
        updated_doc = doc_ref.get()
        updated_data = updated_doc.to_dict()
        updated_data["id"] = updated_doc.id
        
        return updated_data
    
    def _count_reports_in_locality(
        self,
        locality: str,
        city: str,
        exclude_report_id: Optional[str]
    ) -> int:
        """Count non-closed reports in same locality."""
        try:
            reports_ref = self.db.collection("reports")
            query = reports_ref.where("locality", "==", locality).where("city", "==", city)
            
            count = 0
            for doc in query.stream():
                if doc.id != exclude_report_id:
                    data = doc.to_dict()
                    status = data.get("status", "UNDER_REVIEW")
                    if status != "CLOSED":
                        count += 1
            
            return count
        
        except Exception as e:
            logger.warning(f"Failed to count reports in locality: {e}")
            return 0
    
    def _calculate_persistence_hours(self, created_at: datetime) -> float:
        """Calculate hours since report creation."""
        try:
            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            
            now = datetime.utcnow()
            if isinstance(created_at, datetime) and created_at.tzinfo:
                now = datetime.now(created_at.tzinfo)
            
            age_hours = (now - created_at).total_seconds() / 3600
            return age_hours
        
        except Exception as e:
            logger.warning(f"Failed to calculate persistence hours: {e}")
            return 0.0
    
    def get_escalation_candidates(self, limit: int = 50) -> List[Dict]:
        """
        Get all reports flagged for escalation.
        
        Args:
            limit: Maximum number of reports to return
        
        Returns:
            List of escalated report dictionaries
        """
        try:
            reports_ref = self.db.collection("reports")
            query = reports_ref.where("escalation_flag", "==", True).limit(limit)
            
            candidates = []
            for doc in query.stream():
                data = doc.to_dict()
                data["id"] = doc.id
                candidates.append(data)
            
            # Sort by priority_score descending
            candidates.sort(key=lambda x: x.get("priority_score", 0), reverse=True)
            
            logger.info(f"Found {len(candidates)} escalation candidates")
            return candidates
        
        except Exception as e:
            logger.error(f"Failed to get escalation candidates: {str(e)}")
            return []


# Global service instance (singleton pattern)
_escalation_engine = None


def get_escalation_engine() -> EscalationEngine:
    """
    Get or create EscalationEngine singleton instance.
    
    Returns:
        EscalationEngine: The global escalation engine instance
    """
    global _escalation_engine
    if _escalation_engine is None:
        _escalation_engine = EscalationEngine()
    return _escalation_engine
