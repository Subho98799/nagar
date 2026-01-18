"""
Timeline Service - Manages timeline feed, votes, comments, and analytics.
"""

from firebase_admin import firestore
from app.config.firebase import get_db
from app.models.timeline import TimelineIssue, VoteType, SourceType, IssueAnalytics, CommentResponse
from app.utils.firestore_helpers import where_filter
from datetime import datetime, timedelta
from typing import List, Optional, Dict
import logging

logger = logging.getLogger(__name__)


class TimelineService:
    """Service for timeline operations."""
    
    def __init__(self):
        self.db = get_db()
    
    def get_timeline_feed(
        self,
        city: Optional[str] = None,
        limit: int = 50,
        user_id: Optional[str] = None
    ) -> List[TimelineIssue]:
        """
        Get timeline feed of issues (Facebook-like).
        
        Args:
            city: Filter by city
            limit: Maximum number of issues
            user_id: User ID for personalized data (votes, bookmarks)
        
        Returns:
            List of timeline issues
        """
        try:
            reports_ref = self.db.collection("reports")
            
            # Build query
            query = reports_ref.order_by("created_at", direction=firestore.Query.DESCENDING)
            
            if city:
                query = where_filter(query, "city", "==", city)
            
            # Execute query
            docs = query.limit(limit).stream()
            
            issues = []
            for doc in docs:
                try:
                    data = doc.to_dict()
                    issue_id = doc.id
                    
                    # Get votes for this issue
                    votes = self._get_issue_votes(issue_id)
                    upvote_count = sum(1 for v in votes if v.get("vote_type") == "UPVOTE")
                    downvote_count = sum(1 for v in votes if v.get("vote_type") == "DOWNVOTE")
                    popularity_score = upvote_count - downvote_count
                    
                    # Get user's vote if authenticated
                    user_vote = None
                    if user_id:
                        votes_ref = self.db.collection("votes")
                        query = where_filter(votes_ref, "issue_id", "==", issue_id)
                        query = where_filter(query, "user_id", "==", user_id)
                        user_vote_doc = query.limit(1).stream()
                        user_vote_list = list(user_vote_doc)
                        if user_vote_list:
                            user_vote = VoteType(user_vote_list[0].to_dict().get("vote_type"))
                    
                    # Get comment count
                    comment_count = self._get_comment_count(issue_id)
                    
                    # Get sources
                    sources = self._get_issue_sources(issue_id, data)
                    
                    # Get confidence score from AI metadata
                    ai_metadata = data.get("ai_metadata", {})
                    confidence_score = ai_metadata.get("ai_confidence_score", 0.0)
                    if not confidence_score:
                        # Fallback to confidence level
                        confidence = data.get("confidence", "LOW")
                        confidence_score = {"LOW": 0.3, "MEDIUM": 0.6, "HIGH": 0.9}.get(confidence, 0.3)
                    
                    # Build timeline issue
                    timeline_issue = TimelineIssue(
                        id=issue_id,
                        title=data.get("description", "")[:100] or "Untitled Issue",
                        description=data.get("description", ""),
                        issue_type=data.get("issue_type", "Other"),
                        severity=data.get("ai_metadata", {}).get("severity_hint", "Low"),
                        confidence=data.get("confidence", "LOW"),
                        status=data.get("status", "UNDER_REVIEW"),
                        city=data.get("city"),
                        locality=data.get("locality"),
                        latitude=data.get("latitude"),
                        longitude=data.get("longitude"),
                        created_at=data.get("created_at").isoformat() if isinstance(data.get("created_at"), datetime) else str(data.get("created_at", "")),
                        updated_at=data.get("updated_at").isoformat() if isinstance(data.get("updated_at"), datetime) else str(data.get("updated_at", "")),
                        popularity_score=popularity_score,
                        confidence_score=confidence_score,
                        priority_score=data.get("priority_score"),
                        upvote_count=upvote_count,
                        downvote_count=downvote_count,
                        comment_count=comment_count,
                        report_count=data.get("report_count", 1),
                        user_vote=user_vote,
                        sources=sources,
                        media_urls=data.get("media_urls", [])
                    )
                    
                    issues.append(timeline_issue)
                
                except Exception as e:
                    logger.warning(f"Failed to process issue {doc.id}: {e}")
                    continue
            
            return issues
        
        except Exception as e:
            logger.error(f"Failed to get timeline feed: {e}", exc_info=True)
            return []
    
    def get_issue_analytics(self, issue_id: str, user_id: Optional[str] = None) -> Optional[IssueAnalytics]:
        """
        Get comprehensive analytics for an issue.
        
        Args:
            issue_id: Issue ID
            user_id: User ID for personalized data
        
        Returns:
            IssueAnalytics or None if issue not found
        """
        try:
            # Get issue document
            issue_doc = self.db.collection("reports").document(issue_id).get()
            if not issue_doc.exists:
                return None
            
            issue_data = issue_doc.to_dict()
            
            # Get votes
            votes = self._get_issue_votes(issue_id)
            upvote_count = sum(1 for v in votes if v.get("vote_type") == "UPVOTE")
            downvote_count = sum(1 for v in votes if v.get("vote_type") == "DOWNVOTE")
            popularity_score = upvote_count - downvote_count
            
            # Get votes over time
            votes_over_time = self._get_votes_over_time(issue_id)
            
            # Get comments
            comments = self._get_issue_comments(issue_id, user_id)
            
            # Get source breakdown
            source_breakdown = self._get_source_breakdown(issue_id, issue_data)
            
            # Get reports over time
            reports_over_time = self._get_reports_over_time(issue_id)
            
            # Get confidence over time
            confidence_over_time = self._get_confidence_over_time(issue_id)
            
            # Get distributions
            issue_type_dist = {issue_data.get("issue_type", "Other"): 1}
            severity_dist = {issue_data.get("ai_metadata", {}).get("severity_hint", "Low"): 1}
            status_dist = {issue_data.get("status", "UNDER_REVIEW"): 1}
            
            # Get location heatmap
            location_heatmap = self._get_location_heatmap(issue_id, issue_data)
            
            # Get confidence score
            ai_metadata = issue_data.get("ai_metadata", {})
            confidence_score = ai_metadata.get("ai_confidence_score", 0.0)
            if not confidence_score:
                confidence = issue_data.get("confidence", "LOW")
                confidence_score = {"LOW": 0.3, "MEDIUM": 0.6, "HIGH": 0.9}.get(confidence, 0.3)
            
            return IssueAnalytics(
                issue_id=issue_id,
                popularity_score=popularity_score,
                confidence_score=confidence_score,
                priority_score=issue_data.get("priority_score"),
                source_breakdown=source_breakdown,
                reports_over_time=reports_over_time,
                confidence_over_time=confidence_over_time,
                votes_over_time=votes_over_time,
                issue_type_distribution=issue_type_dist,
                severity_distribution=severity_dist,
                status_distribution=status_dist,
                location_heatmap=location_heatmap,
                ai_metadata=ai_metadata,
                comments=comments,
                total_upvotes=upvote_count,
                total_downvotes=downvote_count,
                total_comments=len(comments),
                total_reports=issue_data.get("report_count", 1)
            )
        
        except Exception as e:
            logger.error(f"Failed to get issue analytics: {e}", exc_info=True)
            return None
    
    def vote_on_issue(self, issue_id: str, user_id: str, vote_type: VoteType) -> Dict:
        """
        Vote on an issue (upvote or downvote).
        
        Args:
            issue_id: Issue ID
            user_id: User ID
            vote_type: Vote type (UPVOTE or DOWNVOTE)
        
        Returns:
            Dict with success status and updated counts
        """
        try:
            # Check if user already voted
            votes_ref = self.db.collection("votes")
            query = where_filter(votes_ref, "issue_id", "==", issue_id)
            query = where_filter(query, "user_id", "==", user_id)
            existing_vote = query.limit(1).stream()
            existing_vote_list = list(existing_vote)
            
            if existing_vote_list:
                # Update existing vote
                vote_doc = existing_vote_list[0]
                old_vote_type = vote_doc.to_dict().get("vote_type")
                
                if old_vote_type == vote_type.value:
                    # Same vote - remove it (toggle off)
                    vote_doc.reference.delete()
                    action = "removed"
                else:
                    # Different vote - update it
                    vote_doc.reference.update({
                        "vote_type": vote_type.value,
                        "updated_at": firestore.SERVER_TIMESTAMP
                    })
                    action = "updated"
            else:
                # Create new vote
                vote_ref = votes_ref.document()
                vote_ref.set({
                    "issue_id": issue_id,
                    "user_id": user_id,
                    "vote_type": vote_type.value,
                    "created_at": firestore.SERVER_TIMESTAMP,
                    "updated_at": firestore.SERVER_TIMESTAMP
                })
                action = "created"
            
            # Get updated counts
            votes = self._get_issue_votes(issue_id)
            upvote_count = sum(1 for v in votes if v.get("vote_type") == "UPVOTE")
            downvote_count = sum(1 for v in votes if v.get("vote_type") == "DOWNVOTE")
            popularity_score = upvote_count - downvote_count
            
            # Get user's current vote
            query = where_filter(votes_ref, "issue_id", "==", issue_id)
            query = where_filter(query, "user_id", "==", user_id)
            user_vote_doc = query.limit(1).stream()
            user_vote_list = list(user_vote_doc)
            user_vote = None
            if user_vote_list:
                user_vote = VoteType(user_vote_list[0].to_dict().get("vote_type"))
            
            return {
                "success": True,
                "action": action,
                "upvote_count": upvote_count,
                "downvote_count": downvote_count,
                "popularity_score": popularity_score,
                "user_vote": user_vote.value if user_vote else None
            }
        
        except Exception as e:
            logger.error(f"Failed to vote on issue: {e}", exc_info=True)
            return {
                "success": False,
                "message": str(e)
            }
    
    def add_comment(self, issue_id: str, user_id: str, text: str, parent_comment_id: Optional[str] = None) -> Optional[CommentResponse]:
        """
        Add a comment to an issue.
        
        Args:
            issue_id: Issue ID
            user_id: User ID
            text: Comment text
            parent_comment_id: Parent comment ID for nested comments
        
        Returns:
            CommentResponse or None if failed
        """
        try:
            # Get user data
            user_doc = self.db.collection("users").document(user_id).get()
            user_data = user_doc.to_dict() if user_doc.exists else {}
            user_phone = user_data.get("phone_number")
            
            # Create comment
            comment_ref = self.db.collection("comments").document()
            comment_data = {
                "issue_id": issue_id,
                "user_id": user_id,
                "user_phone": user_phone,
                "text": text,
                "parent_comment_id": parent_comment_id,
                "created_at": firestore.SERVER_TIMESTAMP,
                "upvote_count": 0,
                "downvote_count": 0
            }
            comment_ref.set(comment_data)
            
            # Get created comment
            created_doc = comment_ref.get()
            created_data = created_doc.to_dict()
            
            return CommentResponse(
                id=created_doc.id,
                issue_id=issue_id,
                user_id=user_id,
                user_phone=user_phone,
                text=text,
                parent_comment_id=parent_comment_id,
                created_at=created_data.get("created_at").isoformat() if isinstance(created_data.get("created_at"), datetime) else str(created_data.get("created_at", "")),
                upvote_count=0,
                downvote_count=0
            )
        
        except Exception as e:
            logger.error(f"Failed to add comment: {e}", exc_info=True)
            return None
    
    # Helper methods
    
    def _get_issue_votes(self, issue_id: str) -> List[Dict]:
        """Get all votes for an issue."""
        try:
            votes_ref = self.db.collection("votes")
            votes = where_filter(votes_ref, "issue_id", "==", issue_id).stream()
            return [doc.to_dict() for doc in votes]
        except:
            return []
    
    def _get_comment_count(self, issue_id: str) -> int:
        """Get comment count for an issue."""
        try:
            comments_ref = self.db.collection("comments")
            comments = where_filter(comments_ref, "issue_id", "==", issue_id).stream()
            return len(list(comments))
        except:
            return 0
    
    def _get_issue_comments(self, issue_id: str, user_id: Optional[str] = None) -> List[CommentResponse]:
        """Get all comments for an issue."""
        try:
            comments_ref = self.db.collection("comments")
            query = where_filter(comments_ref, "issue_id", "==", issue_id)
            comments = query.order_by("created_at", direction=firestore.Query.DESCENDING).stream()
            
            result = []
            for doc in comments:
                data = doc.to_dict()
                
                # Get user vote if authenticated
                user_vote = None
                if user_id:
                    comment_votes_ref = self.db.collection("comment_votes")
                    query = where_filter(comment_votes_ref, "comment_id", "==", doc.id)
                    query = where_filter(query, "user_id", "==", user_id)
                    vote_doc = query.limit(1).stream()
                    vote_list = list(vote_doc)
                    if vote_list:
                        user_vote = VoteType(vote_list[0].to_dict().get("vote_type"))
                
                result.append(CommentResponse(
                    id=doc.id,
                    issue_id=issue_id,
                    user_id=data.get("user_id"),
                    user_phone=data.get("user_phone"),
                    text=data.get("text", ""),
                    parent_comment_id=data.get("parent_comment_id"),
                    created_at=data.get("created_at").isoformat() if isinstance(data.get("created_at"), datetime) else str(data.get("created_at", "")),
                    upvote_count=data.get("upvote_count", 0),
                    downvote_count=data.get("downvote_count", 0),
                    user_vote=user_vote
                ))
            
            return result
        except:
            return []
    
    def _get_issue_sources(self, issue_id: str, issue_data: Dict) -> List[Dict]:
        """Get sources for an issue."""
        sources = []
        
        # Check if issue has source information
        source_type = issue_data.get("source_type", "CITIZEN")
        sources.append({
            "type": source_type,
            "count": issue_data.get("report_count", 1),
            "description": "Citizen reports" if source_type == "CITIZEN" else "Website scraper"
        })
        
        return sources
    
    def _get_source_breakdown(self, issue_id: str, issue_data: Dict) -> Dict[str, int]:
        """Get source breakdown for analytics."""
        source_type = issue_data.get("source_type", "CITIZEN")
        return {source_type: issue_data.get("report_count", 1)}
    
    def _get_reports_over_time(self, issue_id: str) -> List[Dict]:
        """Get reports over time for charts."""
        # Simplified - in production, aggregate from reports collection
        issue_doc = self.db.collection("reports").document(issue_id).get()
        if issue_doc.exists:
            data = issue_doc.to_dict()
            created_at = data.get("created_at")
            if isinstance(created_at, datetime):
                return [{"date": created_at.strftime("%Y-%m-%d"), "count": data.get("report_count", 1)}]
        return []
    
    def _get_confidence_over_time(self, issue_id: str) -> List[Dict]:
        """Get confidence over time for charts."""
        issue_doc = self.db.collection("reports").document(issue_id).get()
        if issue_doc.exists:
            data = issue_doc.to_dict()
            created_at = data.get("created_at")
            ai_metadata = data.get("ai_metadata", {})
            confidence_score = ai_metadata.get("ai_confidence_score", 0.0)
            if not confidence_score:
                confidence = data.get("confidence", "LOW")
                confidence_score = {"LOW": 0.3, "MEDIUM": 0.6, "HIGH": 0.9}.get(confidence, 0.3)
            
            if isinstance(created_at, datetime):
                return [{"date": created_at.strftime("%Y-%m-%d"), "confidence": confidence_score}]
        return []
    
    def _get_votes_over_time(self, issue_id: str) -> List[Dict]:
        """Get votes over time for charts."""
        try:
            votes_ref = self.db.collection("votes")
            query = where_filter(votes_ref, "issue_id", "==", issue_id)
            votes = query.order_by("created_at").stream()
            
            # Aggregate by date
            daily_votes = {}
            for vote_doc in votes:
                vote_data = vote_doc.to_dict()
                created_at = vote_data.get("created_at")
                if isinstance(created_at, datetime):
                    date_str = created_at.strftime("%Y-%m-%d")
                    if date_str not in daily_votes:
                        daily_votes[date_str] = {"upvotes": 0, "downvotes": 0}
                    
                    if vote_data.get("vote_type") == "UPVOTE":
                        daily_votes[date_str]["upvotes"] += 1
                    else:
                        daily_votes[date_str]["downvotes"] += 1
            
            return [{"date": date, **counts} for date, counts in daily_votes.items()]
        except:
            return []
    
    def _get_location_heatmap(self, issue_id: str, issue_data: Dict) -> List[Dict]:
        """Get location heatmap data."""
        lat = issue_data.get("latitude")
        lng = issue_data.get("longitude")
        
        if lat and lng:
            return [{
                "lat": lat,
                "lng": lng,
                "intensity": issue_data.get("report_count", 1)
            }]
        
        return []


# Global service instance (singleton pattern)
_timeline_service = None


def get_timeline_service() -> TimelineService:
    """Get or create TimelineService singleton instance."""
    global _timeline_service
    if _timeline_service is None:
        _timeline_service = TimelineService()
    return _timeline_service
