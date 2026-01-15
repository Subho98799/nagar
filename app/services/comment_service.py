"""
Comment Service - Handle comments on issues.
"""

from firebase_admin import firestore
from app.config.firebase import get_db
from app.models.timeline import CommentResponse
from app.services.user_service import get_user_service
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class CommentService:
    """Service for managing comments on issues."""
    
    def __init__(self):
        self.db = get_db()
    
    def add_comment(self, issue_id: str, text: str, user_id: Optional[str] = None) -> Dict:
        """
        Add a comment to an issue.
        
        Args:
            issue_id: Issue to comment on
            text: Comment text
            user_id: Optional user ID (if authenticated)
        
        Returns:
            CommentResponse dict
        """
        try:
            # Get user info if authenticated
            user_phone = None
            if user_id:
                user_service = get_user_service()
                user = user_service.get_user_by_phone(user_id)  # Assuming user_id is phone for now
                if user:
                    user_phone = user.get("phone_number")
            
            # Create comment
            comment_ref = self.db.collection("comments").document()
            comment_data = {
                "issue_id": issue_id,
                "text": text,
                "user_id": user_id,
                "user_phone": user_phone,
                "likes": 0,
                "created_at": firestore.SERVER_TIMESTAMP
            }
            comment_ref.set(comment_data)
            
            return {
                "id": comment_ref.id,
                "issue_id": issue_id,
                "text": text,
                "user_id": user_id,
                "user_phone": user_phone,
                "created_at": comment_data.get("created_at"),
                "likes": 0
            }
        
        except Exception as e:
            logger.error(f"Failed to add comment: {str(e)}", exc_info=True)
            raise
    
    def get_comments(self, issue_id: str) -> List[Dict]:
        """
        Get all comments for an issue, sorted by creation time.
        
        Returns:
            List of CommentResponse dicts
        """
        try:
            comments_ref = self.db.collection("comments")
            query = comments_ref.where("issue_id", "==", issue_id).order_by("created_at", direction=firestore.Query.DESCENDING)
            
            comments = []
            for doc in query.stream():
                comment_data = doc.to_dict()
                comments.append({
                    "id": doc.id,
                    "issue_id": issue_id,
                    "text": comment_data.get("text", ""),
                    "user_id": comment_data.get("user_id"),
                    "user_phone": comment_data.get("user_phone"),
                    "created_at": comment_data.get("created_at"),
                    "likes": comment_data.get("likes", 0)
                })
            
            return comments
        
        except Exception as e:
            logger.error(f"Failed to get comments: {str(e)}")
            return []


# Global service instance
_comment_service = None


def get_comment_service() -> CommentService:
    """Get or create CommentService singleton."""
    global _comment_service
    if _comment_service is None:
        _comment_service = CommentService()
    return _comment_service
