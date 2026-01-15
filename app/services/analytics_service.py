"""
Analytics Service - Generate analytics data for issues (charts, heatmaps, etc.).
"""

from firebase_admin import firestore
from app.config.firebase import get_db
from app.models.timeline import IssueAnalytics, SourceInfo
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


class AnalyticsService:
    """Service for generating issue analytics."""
    
    def __init__(self):
        self.db = get_db()
    
    def get_issue_analytics(self, issue_id: str) -> Dict:
        """
        Get comprehensive analytics for a specific issue.
        
        Returns:
            Dict with charts data, distributions, heatmaps, etc.
        """
        try:
            # Get the issue/report
            report_doc = self.db.collection("reports").document(issue_id).get()
            if not report_doc.exists:
                return {}
            
            report = report_doc.to_dict()
            report["id"] = report_doc.id
            
            # Get all related reports (for aggregation)
            related_reports = self._get_related_reports(report)
            
            # Build analytics
            analytics = {
                "issue_id": issue_id,
                "popularity_score": self._calculate_popularity(report, related_reports),
                "confidence_score": report.get("confidence", "LOW"),
                "priority_score": report.get("priority_score"),
                "escalation_flag": report.get("escalation_flag", False),
                
                # Distributions
                "issue_type_distribution": self._get_issue_type_distribution(related_reports),
                "confidence_distribution": self._get_confidence_distribution(related_reports),
                "status_distribution": self._get_status_distribution(related_reports),
                
                # Time series
                "time_series_data": self._get_time_series_data(related_reports),
                
                # Location heatmap
                "location_heatmap": self._get_location_heatmap(related_reports),
                
                # Sources
                "sources": self._get_source_breakdown(related_reports),
                
                # Voting
                "upvotes": self._get_upvotes(issue_id),
                "downvotes": self._get_downvotes(issue_id),
                "vote_ratio": self._calculate_vote_ratio(issue_id),
                
                # Comments
                "comment_count": self._get_comment_count(issue_id)
            }
            
            return analytics
        
        except Exception as e:
            logger.error(f"Failed to get issue analytics: {str(e)}", exc_info=True)
            return {}
    
    def _get_related_reports(self, report: Dict) -> List[Dict]:
        """Get related reports (same locality, similar time, same issue type)."""
        try:
            locality = report.get("locality")
            issue_type = report.get("issue_type")
            created_at = report.get("created_at")
            
            if not locality or not created_at:
                return [report]
            
            # Get reports from same locality within 7 days
            reports_ref = self.db.collection("reports")
            query = reports_ref.where("locality", "==", locality)
            
            related = [report]
            for doc in query.stream():
                if doc.id == report.get("id"):
                    continue
                
                doc_data = doc.to_dict()
                doc_data["id"] = doc.id
                
                # Check if within time window
                doc_created = doc_data.get("created_at")
                if doc_created:
                    try:
                        if isinstance(doc_created, str):
                            doc_dt = datetime.fromisoformat(doc_created.replace('Z', '+00:00'))
                        else:
                            doc_dt = doc_created
                        
                        if isinstance(created_at, str):
                            ref_dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        else:
                            ref_dt = created_at
                        
                        days_diff = abs((doc_dt.replace(tzinfo=None) - ref_dt.replace(tzinfo=None)).days)
                        if days_diff <= 7:
                            related.append(doc_data)
                    except:
                        pass
            
            return related
        
        except Exception as e:
            logger.warning(f"Failed to get related reports: {e}")
            return [report]
    
    def _calculate_popularity(self, report: Dict, related: List[Dict]) -> float:
        """Calculate popularity score."""
        from app.services.timeline_service import TimelineService
        timeline_service = TimelineService()
        return timeline_service._calculate_popularity_score(report)
    
    def _get_issue_type_distribution(self, reports: List[Dict]) -> Dict[str, int]:
        """Get distribution by issue type."""
        distribution = defaultdict(int)
        for report in reports:
            issue_type = report.get("issue_type", "Other")
            distribution[issue_type] += 1
        return dict(distribution)
    
    def _get_confidence_distribution(self, reports: List[Dict]) -> Dict[str, int]:
        """Get distribution by confidence level."""
        distribution = defaultdict(int)
        for report in reports:
            confidence = report.get("confidence", "LOW")
            distribution[confidence] += 1
        return dict(distribution)
    
    def _get_status_distribution(self, reports: List[Dict]) -> Dict[str, int]:
        """Get distribution by status."""
        distribution = defaultdict(int)
        for report in reports:
            status = report.get("status", "UNDER_REVIEW")
            distribution[status] += 1
        return dict(distribution)
    
    def _get_time_series_data(self, reports: List[Dict]) -> List[Dict]:
        """Get time series data for histogram."""
        # Group by day
        daily_counts = defaultdict(int)
        
        for report in reports:
            created_at = report.get("created_at")
            if created_at:
                try:
                    if isinstance(created_at, str):
                        dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    else:
                        dt = created_at
                    
                    date_key = dt.strftime("%Y-%m-%d")
                    daily_counts[date_key] += 1
                except:
                    pass
        
        # Convert to list format
        time_series = []
        for date, count in sorted(daily_counts.items()):
            time_series.append({
                "date": date,
                "count": count
            })
        
        return time_series
    
    def _get_location_heatmap(self, reports: List[Dict]) -> List[Dict]:
        """Get location data for heatmap."""
        heatmap = []
        
        for report in reports:
            lat = report.get("latitude")
            lon = report.get("longitude")
            
            if lat and lon:
                heatmap.append({
                    "latitude": lat,
                    "longitude": lon,
                    "intensity": 1  # Can be weighted by confidence or report count
                })
        
        return heatmap
    
    def _get_source_breakdown(self, reports: List[Dict]) -> List[Dict]:
        """Get source breakdown (citizen, scraper, etc.)."""
        # For now, assume all are from citizens
        # In future, add source field to reports
        citizen_count = len(reports)
        
        return [
            {
                "source_type": "citizen",
                "count": citizen_count,
                "last_updated": reports[0].get("created_at") if reports else None
            }
        ]
    
    def _get_upvotes(self, issue_id: str) -> int:
        """Get upvote count."""
        try:
            votes_ref = self.db.collection("votes")
            query = votes_ref.where("issue_id", "==", issue_id).where("vote_type", "==", "upvote")
            return len(list(query.stream()))
        except:
            return 0
    
    def _get_downvotes(self, issue_id: str) -> int:
        """Get downvote count."""
        try:
            votes_ref = self.db.collection("votes")
            query = votes_ref.where("issue_id", "==", issue_id).where("vote_type", "==", "downvote")
            return len(list(query.stream()))
        except:
            return 0
    
    def _calculate_vote_ratio(self, issue_id: str) -> float:
        """Calculate vote ratio (upvotes / total votes)."""
        upvotes = self._get_upvotes(issue_id)
        downvotes = self._get_downvotes(issue_id)
        total = upvotes + downvotes
        
        if total == 0:
            return 0.0
        
        return upvotes / total
    
    def _get_comment_count(self, issue_id: str) -> int:
        """Get comment count."""
        try:
            comments_ref = self.db.collection("comments")
            query = comments_ref.where("issue_id", "==", issue_id)
            return len(list(query.stream()))
        except:
            return 0


# Global service instance
_analytics_service = None


def get_analytics_service() -> AnalyticsService:
    """Get or create AnalyticsService singleton."""
    global _analytics_service
    if _analytics_service is None:
        _analytics_service = AnalyticsService()
    return _analytics_service
