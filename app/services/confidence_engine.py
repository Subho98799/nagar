"""
Confidence Engine - Deterministic confidence progression based on pattern detection.

DESIGN PRINCIPLES (CRITICAL):
- Confidence is rule-based, NOT ML-based
- Confidence is explainable in plain language
- LOW → MEDIUM is automatic based on patterns
- MEDIUM → HIGH requires human approval (not implemented here)
- HIGH is NEVER auto-assigned

CONFIDENCE RULES (Phase-2):
1. LOW: Single report (default)
2. MEDIUM: 2-3 reports from same locality within time window
   - Same AI-classified category (from ai_metadata.ai_classified_category)
   - Same locality (exact match)
   - Within TIME_WINDOW_MINUTES
3. HIGH: 4+ reports OR media attached
   - 4+ similar reports (same criteria as MEDIUM)
   - OR report has media_urls (images/videos provide evidence)
4. HIGH can also be set by admin/reviewer (manual override)

NO ML. NO PROBABILISTIC SCORING. ONLY DETERMINISTIC RULES.
"""

from firebase_admin import firestore
from app.config.firebase import get_db
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import math
import logging

logger = logging.getLogger(__name__)


class ConfidenceEngine:
    """
    Deterministic confidence calculator based on spatial-temporal clustering.
    
    Uses simple rules to detect patterns and upgrade confidence from LOW to MEDIUM.
    Does NOT use machine learning or probabilistic models.
    """
    
    # Configuration constants (easy to adjust)
    PROXIMITY_THRESHOLD_METERS = 500  # Reports within 500m are considered "nearby"
    TIME_WINDOW_MINUTES = 30          # Reports within 30 minutes are considered "recent"
    MIN_SIMILAR_REPORTS = 2           # Need at least 2 similar reports (including current)
    
    def __init__(self):
        self.db = get_db()
    
    def recalculate_confidence(self, new_report: Dict) -> None:
        """
        Recalculate confidence for a newly submitted report and related reports.
        
        Phase-2 Logic:
        1. Check if report has media (images/videos) → HIGH
        2. Find reports matching:
           - Same AI-classified category
           - Same locality (exact match)
           - Within TIME_WINDOW_MINUTES
        3. Apply rules:
           - LOW: Single report
           - MEDIUM: 2-3 similar reports
           - HIGH: 4+ similar reports OR media attached
        
        Args:
            new_report: The newly created report dict (must include id, ai_metadata, etc.)
        
        Returns:
            None (updates Firestore directly)
        """
        try:
            # Extract new report details
            new_report_id = new_report.get("id")
            new_locality = new_report.get("locality")
            new_created_at = new_report.get("created_at")
            new_ai_metadata = new_report.get("ai_metadata", {})
            new_media_urls = new_report.get("media_urls", [])
            # Use AI-classified category for pattern matching (distinct from user-selected issue_type)
            new_ai_category = new_ai_metadata.get("ai_classified_category", "")
            
            # Skip if missing critical data
            if not all([new_report_id, new_locality, new_created_at]):
                logger.warning(f"Skipping confidence calculation for report {new_report_id}: missing data")
                return
            
            # Check for media (images/videos) - automatic HIGH confidence
            if new_media_urls and len(new_media_urls) > 0:
                reason = f"Report includes media evidence ({len(new_media_urls)} file(s))"
                self._update_confidence(new_report_id, "HIGH", reason)
                logger.info(f"✅ Report {new_report_id} upgraded to HIGH: media attached")
                return
            
            # Skip if AI category is "Unclassified" (AI failed)
            if new_ai_category in ["Unclassified", "General", ""]:
                logger.info(f"Skipping confidence calculation for report {new_report_id}: unclassified AI category")
                reason = "Single report, awaiting corroboration"
                self._update_confidence(new_report_id, "LOW", reason)
                return
            
            logger.info(f"Calculating confidence for report {new_report_id} (AI category: {new_ai_category}, locality: {new_locality})")
            
            # STEP 1: Find similar reports (same locality, same AI category)
            similar_reports = self._find_similar_reports_by_locality(
                ai_category=new_ai_category,
                locality=new_locality,
                created_at=new_created_at,
                exclude_id=new_report_id
            )
            
            # STEP 2: Apply Phase-2 rules
            total_similar = len(similar_reports) + 1  # +1 for the new report itself
            
            if total_similar >= 4:
                # HIGH: 4+ reports
                reason = f"Multiple corroborating reports detected ({total_similar} reports in {new_locality} within {self.TIME_WINDOW_MINUTES} minutes)"
                self._update_confidence(new_report_id, "HIGH", reason)
                
                # Upgrade all similar reports to HIGH (if not already)
                for similar_report in similar_reports:
                    similar_id = similar_report.get("id")
                    current_confidence = similar_report.get("confidence", "LOW")
                    if current_confidence != "HIGH":
                        self._update_confidence(similar_id, "HIGH", reason)
                
                logger.info(f"✅ Pattern detected: {total_similar} similar reports → HIGH confidence")
            
            elif total_similar >= 2:
                # MEDIUM: 2-3 reports
                reason = f"Multiple similar reports detected ({total_similar} reports in {new_locality} within {self.TIME_WINDOW_MINUTES} minutes)"
                self._update_confidence(new_report_id, "MEDIUM", reason)
                
                # Upgrade all similar reports to MEDIUM (if currently LOW)
                for similar_report in similar_reports:
                    similar_id = similar_report.get("id")
                    current_confidence = similar_report.get("confidence", "LOW")
                    if current_confidence == "LOW":
                        self._update_confidence(similar_id, "MEDIUM", reason)
                
                logger.info(f"✅ Pattern detected: {total_similar} similar reports → MEDIUM confidence")
            
            else:
                # LOW: Single report
                reason = "Single report, awaiting corroboration"
                self._update_confidence(new_report_id, "LOW", reason)
                logger.info(f"No pattern detected: single report → LOW confidence")
        
        except Exception as e:
            # If confidence calculation fails, log but don't crash
            logger.error(f"⚠️ Confidence calculation failed for report {new_report.get('id')}: {str(e)}")
            logger.error("Report will remain at default confidence level")
    
    def _find_similar_reports_by_locality(
        self,
        ai_category: str,
        locality: str,
        created_at: datetime,
        exclude_id: str
    ) -> List[Dict]:
        """
        Find reports matching Phase-2 similarity criteria (locality-based).
        
        Criteria:
        1. Same AI-classified category (from ai_metadata.ai_classified_category)
        2. Same locality (exact match)
        3. Within TIME_WINDOW_MINUTES
        4. Not the current report itself
        
        Args:
            ai_category: AI-classified category to match (distinct from user-selected issue_type)
            locality: Locality string (exact match required)
            created_at: Report creation timestamp
            exclude_id: Report ID to exclude (usually the new report)
        
        Returns:
            List of similar report dicts
        """
        # Calculate time window
        time_threshold = created_at - timedelta(minutes=self.TIME_WINDOW_MINUTES)
        
        # Query Firestore for recent reports in same locality
        reports_ref = self.db.collection("reports")
        
        # Filter by locality and time window
        query = reports_ref.where("locality", "==", locality).where("created_at", ">=", time_threshold)
        
        # Fetch all matching reports
        docs = query.stream()
        
        similar_reports = []
        
        for doc in docs:
            report_data = doc.to_dict()
            report_id = doc.id
            
            # Skip the current report
            if report_id == exclude_id:
                continue
            
            # Check AI-classified category match (distinct from user-selected issue_type)
            report_ai_metadata = report_data.get("ai_metadata", {})
            report_ai_category = report_ai_metadata.get("ai_classified_category", "")
            
            if report_ai_category != ai_category:
                continue
            
            # This report matches all criteria
            report_data["id"] = report_id  # Add ID for later updates
            similar_reports.append(report_data)
            logger.debug(f"Found similar report: {report_id} (same locality: {locality})")
        
        return similar_reports
    
    def _haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate distance between two points using Haversine formula.
        
        Args:
            lat1, lon1: First point coordinates
            lat2, lon2: Second point coordinates
        
        Returns:
            Distance in meters
        """
        # Earth radius in meters
        R = 6371000
        
        # Convert to radians
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)
        
        # Haversine formula
        a = math.sin(delta_phi / 2) ** 2 + \
            math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        distance = R * c  # in meters
        
        return distance
    
    def _update_confidence(self, report_id: str, confidence: str, reason: str) -> None:
        """
        Update confidence and confidence_reason for a report in Firestore.
        
        Args:
            report_id: Firestore document ID
            confidence: New confidence level (LOW, MEDIUM, HIGH)
            reason: Explainable reason for this confidence level
        """
        try:
            doc_ref = self.db.collection("reports").document(report_id)
            doc_ref.update({
                "confidence": confidence,
                "confidence_reason": reason
            })
            logger.info(f"Updated report {report_id}: confidence={confidence}")
        
        except Exception as e:
            logger.error(f"Failed to update confidence for report {report_id}: {str(e)}")


# Global engine instance (singleton pattern)
_engine = None


def get_confidence_engine() -> ConfidenceEngine:
    """
    Get or create ConfidenceEngine singleton instance.
    
    Returns:
        ConfidenceEngine: The global confidence engine instance
    """
    global _engine
    if _engine is None:
        _engine = ConfidenceEngine()
    return _engine
