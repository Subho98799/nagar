"""
Duplicate Detection Service - Phase-2 anti-spam and data integrity.

DESIGN PRINCIPLES:
- Prevent obvious duplicate reports from same source/locality
- Rate limiting based on IP hash and locality
- Time window-based deduplication
"""

from firebase_admin import firestore
from app.config.firebase import get_db
from datetime import datetime, timedelta
from typing import Optional, Dict
import logging

logger = logging.getLogger(__name__)


class DuplicateDetectionService:
    """
    Service for detecting and preventing duplicate reports.
    """
    
    # Configuration constants
    DUPLICATE_TIME_WINDOW_MINUTES = 15  # Reports within 15 minutes are checked for duplicates
    DUPLICATE_DISTANCE_THRESHOLD_METERS = 50  # Reports within 50m are considered duplicates
    MAX_REPORTS_PER_IP_PER_HOUR = 5  # Rate limit: max 5 reports per IP per hour
    
    def __init__(self):
        self.db = get_db()
    
    def check_duplicate(
        self,
        ip_address_hash: Optional[str],
        locality: str,
        latitude: Optional[float],
        longitude: Optional[float],
        description: str
    ) -> Dict:
        """
        Check if a report is a duplicate of an existing report.
        
        Criteria for duplicate:
        1. Same IP hash (if available)
        2. Same locality
        3. Within DUPLICATE_DISTANCE_THRESHOLD_METERS (if coordinates available)
        4. Within DUPLICATE_TIME_WINDOW_MINUTES
        5. Similar description (simple text similarity)
        
        Args:
            ip_address_hash: Hashed IP address
            locality: Locality string
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            description: Report description
        
        Returns:
            Dict with is_duplicate flag and duplicate_report_id if found
        """
        now = datetime.utcnow()
        time_threshold = now - timedelta(minutes=self.DUPLICATE_TIME_WINDOW_MINUTES)
        
        reports_ref = self.db.collection("reports")
        
        # Query recent reports in same locality
        query = reports_ref.where("locality", "==", locality).where("created_at", ">=", time_threshold)
        
        duplicates = []
        
        for doc in query.stream():
            report_data = doc.to_dict()
            report_id = doc.id
            
            # Check IP hash match (if available)
            if ip_address_hash:
                report_ip_hash = report_data.get("ip_address_hash")
                if report_ip_hash == ip_address_hash:
                    duplicates.append((report_id, report_data, "same_ip"))
                    continue
            
            # Check distance (if coordinates available)
            if latitude is not None and longitude is not None:
                report_lat = report_data.get("latitude")
                report_lon = report_data.get("longitude")
                
                if report_lat is not None and report_lon is not None:
                    distance = self._haversine_distance(
                        latitude, longitude,
                        report_lat, report_lon
                    )
                    
                    if distance <= self.DUPLICATE_DISTANCE_THRESHOLD_METERS:
                        duplicates.append((report_id, report_data, "same_location"))
                        continue
            
            # Check description similarity (simple word overlap)
            similarity = self._text_similarity(description, report_data.get("description", ""))
            if similarity > 0.7:  # 70% similarity threshold
                duplicates.append((report_id, report_data, "similar_description"))
        
        if duplicates:
            # Return the most recent duplicate
            duplicate_id, duplicate_data, reason = duplicates[0]
            logger.warning(f"Duplicate report detected: {reason} (matches report {duplicate_id})")
            return {
                "is_duplicate": True,
                "duplicate_report_id": duplicate_id,
                "reason": reason,
                "duplicate_data": duplicate_data
            }
        
        return {
            "is_duplicate": False,
            "duplicate_report_id": None,
            "reason": None
        }
    
    def check_rate_limit(self, ip_address_hash: Optional[str]) -> Dict:
        """
        Check if IP address has exceeded rate limit.
        
        Args:
            ip_address_hash: Hashed IP address
        
        Returns:
            Dict with is_rate_limited flag and details
        """
        if not ip_address_hash:
            # No IP hash available, allow submission
            return {"is_rate_limited": False, "remaining": None}
        
        now = datetime.utcnow()
        hour_threshold = now - timedelta(hours=1)
        
        reports_ref = self.db.collection("reports")
        query = reports_ref.where("ip_address_hash", "==", ip_address_hash).where("created_at", ">=", hour_threshold)
        
        recent_count = len(list(query.stream()))
        
        if recent_count >= self.MAX_REPORTS_PER_IP_PER_HOUR:
            logger.warning(f"Rate limit exceeded for IP hash {ip_address_hash[:8]}... ({recent_count} reports in last hour)")
            return {
                "is_rate_limited": True,
                "remaining": 0,
                "limit": self.MAX_REPORTS_PER_IP_PER_HOUR,
                "reset_at": hour_threshold + timedelta(hours=1)
            }
        
        return {
            "is_rate_limited": False,
            "remaining": self.MAX_REPORTS_PER_IP_PER_HOUR - recent_count,
            "limit": self.MAX_REPORTS_PER_IP_PER_HOUR
        }
    
    def _haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points using Haversine formula."""
        import math
        R = 6371000  # Earth radius in meters
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)
        a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c
    
    def _text_similarity(self, text1: str, text2: str) -> float:
        """
        Simple text similarity using word overlap.
        
        Returns similarity score between 0.0 and 1.0.
        """
        if not text1 or not text2:
            return 0.0
        
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        if not union:
            return 0.0
        
        return len(intersection) / len(union)


# Global service instance (singleton pattern)
_duplicate_service = None


def get_duplicate_detection_service() -> DuplicateDetectionService:
    """
    Get or create DuplicateDetectionService singleton instance.
    
    Returns:
        DuplicateDetectionService: The global duplicate detection service instance
    """
    global _duplicate_service
    if _duplicate_service is None:
        _duplicate_service = DuplicateDetectionService()
    return _duplicate_service
