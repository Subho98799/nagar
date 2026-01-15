"""
Timeline routes - Facebook-like feed with analytics and interactions.
"""

from fastapi import APIRouter, HTTPException, status, Query, Header
from typing import Optional, List
from app.models.timeline import (
    TimelineIssue, IssueAnalytics, CommentCreate, CommentResponse,
    VoteRequest, VoteType
)
from app.services.timeline_service import get_timeline_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/timeline", tags=["Timeline"])


@router.get("/feed", response_model=List[TimelineIssue])
async def get_timeline_feed(
    city: Optional[str] = Query(None, description="Filter by city"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of issues"),
    user_id: Optional[str] = Header(None, alias="X-User-ID", description="User ID for personalized data")
):
    """
    Get timeline feed of issues (Facebook-like).
    
    Returns issues sorted by creation time with popularity, confidence, and interaction data.
    """
    try:
        timeline_service = get_timeline_service()
        issues = timeline_service.get_timeline_feed(city=city, limit=limit, user_id=user_id)
        return issues
    except Exception as e:
        logger.error(f"Failed to get timeline feed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get timeline feed: {str(e)}"
        )


@router.get("/issue/{issue_id}/analytics", response_model=IssueAnalytics)
async def get_issue_analytics(
    issue_id: str,
    user_id: Optional[str] = Header(None, alias="X-User-ID", description="User ID for personalized data")
):
    """
    Get comprehensive analytics for an issue.
    
    Includes:
    - Scores (popularity, confidence, priority)
    - Source breakdown
    - Time series data for charts
    - Distribution data for pie charts
    - Location heatmap
    - Comments
    """
    try:
        timeline_service = get_timeline_service()
        analytics = timeline_service.get_issue_analytics(issue_id, user_id=user_id)
        
        if not analytics:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Issue {issue_id} not found"
            )
        
        return analytics
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get issue analytics: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get issue analytics: {str(e)}"
        )


@router.post("/issue/{issue_id}/vote")
async def vote_on_issue(
    issue_id: str,
    vote_type: VoteType,
    user_id: str = Header(..., alias="X-User-ID", description="User ID")
):
    """
    Vote on an issue (upvote or downvote).
    
    If user already voted with same type, vote is removed (toggle).
    If user voted with different type, vote is updated.
    """
    try:
        timeline_service = get_timeline_service()
        result = timeline_service.vote_on_issue(issue_id, user_id, vote_type)
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("message", "Failed to vote")
            )
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to vote on issue: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to vote on issue: {str(e)}"
        )


@router.post("/comment", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
async def add_comment(
    comment: CommentCreate,
    user_id: str = Header(..., alias="X-User-ID", description="User ID")
):
    """
    Add a comment to an issue.
    
    Supports nested comments via parent_comment_id.
    """
    try:
        timeline_service = get_timeline_service()
        result = timeline_service.add_comment(
            issue_id=comment.issue_id,
            user_id=user_id,
            text=comment.text,
            parent_comment_id=comment.parent_comment_id
        )
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to add comment"
            )
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add comment: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add comment: {str(e)}"
        )


@router.get("/issue/{issue_id}/comments", response_model=List[CommentResponse])
async def get_issue_comments(
    issue_id: str,
    user_id: Optional[str] = Header(None, alias="X-User-ID", description="User ID for personalized data")
):
    """
    Get all comments for an issue.
    
    Returns comments sorted by creation time (newest first).
    """
    try:
        timeline_service = get_timeline_service()
        comments = timeline_service._get_issue_comments(issue_id, user_id)
        return comments
    except Exception as e:
        logger.error(f"Failed to get comments: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get comments: {str(e)}"
        )
