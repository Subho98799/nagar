"""
Vote Service - Handle voting (upvote/downvote) on issues.
"""

from firebase_admin import firestore
from app.config.firebase import get_db
from app.models.timeline import VoteResponse
from typing import Optional, Dict
import logging

logger = logging.getLogger(__name__)


class VoteService:
    """Service for managing votes on issues."""
    
    def __init__(self):
        self.db = get_db()
    
    def add_vote(self, issue_id: str, vote_type: str, user_id: Optional[str] = None) -> Dict:
        """
        Add or update a vote on an issue.
        
        Args:
            issue_id: Issue to vote on
            vote_type: 'upvote' or 'downvote'
            user_id: Optional user ID (if authenticated)
        
        Returns:
            VoteResponse with updated counts
        """
        try:
            if vote_type not in ["upvote", "downvote"]:
                raise ValueError("vote_type must be 'upvote' or 'downvote'")
            
            # Check if user already voted
            existing_vote_id = None
            if user_id:
                votes_ref = self.db.collection("votes")
                query = votes_ref.where("issue_id", "==", issue_id).where("user_id", "==", user_id).limit(1)
                
                for doc in query.stream():
                    existing_vote_id = doc.id
                    break
            
            # Create or update vote
            vote_data = {
                "issue_id": issue_id,
                "vote_type": vote_type,
                "user_id": user_id,
                "created_at": firestore.SERVER_TIMESTAMP,
                "updated_at": firestore.SERVER_TIMESTAMP
            }
            
            if existing_vote_id:
                # Update existing vote
                self.db.collection("votes").document(existing_vote_id).update(vote_data)
            else:
                # Create new vote
                self.db.collection("votes").document().set(vote_data)
            
            # Get updated vote counts
            return self.get_votes(issue_id, user_id)
        
        except Exception as e:
            logger.error(f"Failed to add vote: {str(e)}", exc_info=True)
            raise
    
    def get_votes(self, issue_id: str, user_id: Optional[str] = None) -> Dict:
        """
        Get vote counts and user's vote (if authenticated).
        
        Returns:
            VoteResponse dict
        """
        try:
            votes_ref = self.db.collection("votes")
            query = votes_ref.where("issue_id", "==", issue_id)
            
            upvotes = 0
            downvotes = 0
            user_vote = None
            
            for doc in query.stream():
                vote_data = doc.to_dict()
                vote_type = vote_data.get("vote_type")
                
                if vote_type == "upvote":
                    upvotes += 1
                elif vote_type == "downvote":
                    downvotes += 1
                
                # Check if this is user's vote
                if user_id and vote_data.get("user_id") == user_id:
                    user_vote = vote_type
            
            return {
                "issue_id": issue_id,
                "upvotes": upvotes,
                "downvotes": downvotes,
                "user_vote": user_vote
            }
        
        except Exception as e:
            logger.error(f"Failed to get votes: {str(e)}")
            return {
                "issue_id": issue_id,
                "upvotes": 0,
                "downvotes": 0,
                "user_vote": None
            }


# Global service instance
_vote_service = None


def get_vote_service() -> VoteService:
    """Get or create VoteService singleton."""
    global _vote_service
    if _vote_service is None:
        _vote_service = VoteService()
    return _vote_service
