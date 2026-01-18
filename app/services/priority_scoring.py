"""
Priority Scoring Service - Phase-3 system-derived priority calculation.

DESIGN PRINCIPLES:
- Priority is SYSTEM-DERIVED, NOT user-editable
- Priority is ADVISORY for escalation ordering
- Priority does NOT override human review
- Priority is recalculable
- Priority score: 0-100 (higher = more urgent)
"""

from firebase_admin import firestore
from app.config.firebase import get_db
from app.utils.firestore_helpers import where_filter
from datetime import datetime, timedelta
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class PriorityScoringService:
    """
    Calculates priority score (0-100) based on multiple factors.
    
    Factors:
    1. Confidence level (LOW/MEDIUM/HIGH)
    2. Issue type (safety-critical vs general)
    3. Locality repetition frequency
    4. Time persistence (how long issue has been open)
    5. Media presence
    6. Status (VERIFIED vs UNDER_REVIEW)
    """
    
    # Configuration: Issue type weights (safety-critical issues get higher priority)
    ISSUE_TYPE_WEIGHTS = {
        "Safety": 30,           # Safety concerns
        "Safety Concern": 30,
        "Public Safety": 30,
        "Traffic": 20,          # Traffic issues
        "Roadblock": 20,
        "Power": 15,            # Power outages
        "Water": 15,            # Water supply issues
        "Infrastructure": 10,   # General infrastructure
        "Other": 5,             # Other issues
    }
    
    # Configuration: Confidence level weights
    CONFIDENCE_WEIGHTS = {
        "HIGH": 30,
        "MEDIUM": 15,
        "LOW": 5
    }
    
    # Configuration: Status weights
    STATUS_WEIGHTS = {
        "VERIFIED": 20,         # Verified issues are more urgent
        "ACTION_TAKEN": 10,     # Action taken, less urgent
        "UNDER_REVIEW": 15,     # Under review, moderate urgency
        "CLOSED": 0             # Closed, no priority
    }
    
    # Configuration: Time persistence thresholds
    PERSISTENCE_THRESHOLD_HOURS = 24  # Issues open >24 hours get bonus
    PERSISTENCE_BONUS_PER_DAY = 5    # +5 points per day beyond threshold
    
    # Configuration: Media bonus
    MEDIA_BONUS = 10  # Reports with media get +10 points
    
    # Configuration: Locality repetition bonus
    LOCALITY_REPETITION_BONUS = 5  # +5 points per additional report in same locality
    
    def __init__(self):
        self.db = get_db()
    
    def calculate_priority(self, report: Dict) -> Dict:
        """
        Calculate priority score (0-100) for a report.
        
        Args:
            report: Report dictionary with all fields
        
        Returns:
            Dict with priority_score and priority_reason
        """
        try:
            score = 0
            reasons = []
            
            # Factor 1: Confidence level
            confidence = report.get("confidence", "LOW")
            confidence_score = self.CONFIDENCE_WEIGHTS.get(confidence, 5)
            score += confidence_score
            reasons.append(f"Confidence: {confidence} (+{confidence_score})")
            
            # Factor 2: Issue type
            issue_type = report.get("issue_type", "Other")
            issue_score = self.ISSUE_TYPE_WEIGHTS.get(issue_type, 5)
            score += issue_score
            reasons.append(f"Issue type: {issue_type} (+{issue_score})")
            
            # Factor 3: Status
            report_status = report.get("status", "UNDER_REVIEW")
            status_score = self.STATUS_WEIGHTS.get(report_status, 10)
            score += status_score
            reasons.append(f"Status: {report_status} (+{status_score})")
            
            # Factor 4: Media presence
            media_urls = report.get("media_urls", [])
            if media_urls and len(media_urls) > 0:
                score += self.MEDIA_BONUS
                reasons.append(f"Media attached (+{self.MEDIA_BONUS})")
            
            # Factor 5: Time persistence
            created_at = report.get("created_at")
            if created_at:
                persistence_score = self._calculate_persistence_score(created_at)
                if persistence_score > 0:
                    score += persistence_score
                    reasons.append(f"Time persistence (+{persistence_score})")
            
            # Factor 6: Locality repetition
            locality = report.get("locality")
            city = report.get("city")
            if locality and city:
                repetition_score = self._calculate_locality_repetition_score(
                    locality=locality,
                    city=city,
                    exclude_report_id=report.get("id")
                )
                if repetition_score > 0:
                    score += repetition_score
                    reasons.append(f"Locality repetition (+{repetition_score})")
            
            # Clamp score to 0-100
            score = max(0, min(100, score))
            
            # Build explainable reason
            priority_reason = " | ".join(reasons)
            
            logger.info(f"Calculated priority score {score} for report {report.get('id')}: {priority_reason}")
            
            return {
                "priority_score": score,
                "priority_reason": priority_reason
            }
        
        except Exception as e:
            logger.error(f"Failed to calculate priority for report {report.get('id')}: {str(e)}")
            # Return default low priority on error
            return {
                "priority_score": 10,
                "priority_reason": "Priority calculation failed, defaulting to low priority"
            }
    
    def _calculate_persistence_score(self, created_at: datetime) -> int:
        """
        Calculate score based on how long issue has been open.
        
        Issues open longer than threshold get bonus points.
        
        Args:
            created_at: Report creation timestamp
        
        Returns:
            Persistence score (0 or positive)
        """
        try:
            if isinstance(created_at, str):
                # Parse ISO string
                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            
            now = datetime.utcnow()
            if isinstance(created_at, datetime):
                # Handle timezone-aware datetime
                if created_at.tzinfo:
                    now = datetime.now(created_at.tzinfo)
            
            age_hours = (now - created_at).total_seconds() / 3600
            
            if age_hours > self.PERSISTENCE_THRESHOLD_HOURS:
                days_beyond = (age_hours - self.PERSISTENCE_THRESHOLD_HOURS) / 24
                bonus = int(days_beyond * self.PERSISTENCE_BONUS_PER_DAY)
                return min(bonus, 20)  # Cap at +20 points
        
        except Exception as e:
            logger.warning(f"Failed to calculate persistence score: {e}")
        
        return 0
    
    def _calculate_locality_repetition_score(self, locality: str, city: str, exclude_report_id: Optional[str]) -> int:
        """
        Calculate score based on number of reports in same locality.
        
        More reports in same locality = higher priority.
        
        Args:
            locality: Locality string
            city: City string
            exclude_report_id: Report ID to exclude from count
        
        Returns:
            Locality repetition score (0 or positive)
        """
        try:
            reports_ref = self.db.collection("reports")
            query = where_filter(reports_ref, "locality", "==", locality)
            query = where_filter(query, "city", "==", city)
            
            count = 0
            for doc in query.stream():
                if doc.id != exclude_report_id:
                    # Only count non-closed reports
                    data = doc.to_dict()
                    status = data.get("status", "UNDER_REVIEW")
                    if status != "CLOSED":
                        count += 1
            
            # Bonus: +5 points per additional report (beyond the current one)
            if count > 0:
                bonus = min(count * self.LOCALITY_REPETITION_BONUS, 15)  # Cap at +15 points
                return bonus
        
        except Exception as e:
            logger.warning(f"Failed to calculate locality repetition score: {e}")
        
        return 0
    
    def recalculate_priority(self, report_id: str) -> Dict:
        """
        Recalculate priority for an existing report.
        
        Args:
            report_id: Firestore document ID
        
        Returns:
            Dict with priority_score and priority_reason
        """
        doc_ref = self.db.collection("reports").document(report_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            raise ValueError(f"Report {report_id} not found")
        
        report_data = doc.to_dict()
        report_data["id"] = doc.id
        
        result = self.calculate_priority(report_data)
        
        # Update Firestore
        doc_ref.update({
            "priority_score": result["priority_score"],
            "priority_reason": result["priority_reason"]
        })
        
        logger.info(f"Recalculated priority for report {report_id}: {result['priority_score']}")
        
        return result


# Global service instance (singleton pattern)
_priority_service = None


def get_priority_scoring_service() -> PriorityScoringService:
    """
    Get or create PriorityScoringService singleton instance.
    
    Returns:
        PriorityScoringService: The global priority scoring service instance
    """
    global _priority_service
    if _priority_service is None:
        _priority_service = PriorityScoringService()
    return _priority_service
