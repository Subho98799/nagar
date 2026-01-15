"""
Timeline models for issue feed, interactions, and analytics.
"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List, Dict
from enum import Enum


class VoteType(str, Enum):
    """Vote types."""
    UPVOTE = "UPVOTE"
    DOWNVOTE = "DOWNVOTE"


class SourceType(str, Enum):
    """Source types for reports."""
    CITIZEN = "CITIZEN"
    WEBSITE_SCRAPER = "WEBSITE_SCRAPER"
    API = "API"
    ADMIN = "ADMIN"


class TimelineIssue(BaseModel):
    """Issue model for timeline feed."""
    id: str
    title: str
    description: str
    issue_type: str
    severity: str
    confidence: str
    status: str
    city: Optional[str] = None
    locality: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    created_at: str
    updated_at: str
    
    # Scores
    popularity_score: int = Field(default=0, description="Popularity score (upvotes - downvotes)")
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0, description="AI confidence score")
    priority_score: Optional[int] = Field(None, ge=0, le=100, description="Priority score")
    
    # Interaction counts
    upvote_count: int = Field(default=0)
    downvote_count: int = Field(default=0)
    comment_count: int = Field(default=0)
    report_count: int = Field(default=1)
    
    # User interaction (if authenticated)
    user_vote: Optional[VoteType] = None
    is_bookmarked: bool = Field(default=False)
    
    # Source information
    sources: List[Dict] = Field(default_factory=list, description="List of sources (citizens, scrapers, etc.)")
    
    # Media
    media_urls: List[str] = Field(default_factory=list)


class CommentCreate(BaseModel):
    """Model for creating a comment."""
    issue_id: str
    text: str = Field(..., min_length=1, max_length=1000)
    parent_comment_id: Optional[str] = None  # For nested comments


class CommentResponse(BaseModel):
    """Comment response model."""
    id: str
    issue_id: str
    user_id: Optional[str] = None
    user_phone: Optional[str] = None
    text: str
    parent_comment_id: Optional[str] = None
    created_at: str
    upvote_count: int = Field(default=0)
    downvote_count: int = Field(default=0)
    user_vote: Optional[VoteType] = None


class VoteRequest(BaseModel):
    """Vote request model."""
    issue_id: str
    vote_type: VoteType


class IssueAnalytics(BaseModel):
    """Analytics data for an issue."""
    issue_id: str
    
    # Scores
    popularity_score: int
    confidence_score: float
    priority_score: Optional[int]
    
    # Source breakdown
    source_breakdown: Dict[str, int] = Field(default_factory=dict)  # {CITIZEN: 5, WEBSITE_SCRAPER: 2}
    
    # Time series data for charts
    reports_over_time: List[Dict] = Field(default_factory=list)  # [{date: "2024-01-15", count: 5}]
    confidence_over_time: List[Dict] = Field(default_factory=list)  # [{date: "2024-01-15", confidence: 0.8}]
    votes_over_time: List[Dict] = Field(default_factory=list)  # [{date: "2024-01-15", upvotes: 10, downvotes: 2}]
    
    # Distribution data for pie charts
    issue_type_distribution: Dict[str, int] = Field(default_factory=dict)
    severity_distribution: Dict[str, int] = Field(default_factory=dict)
    status_distribution: Dict[str, int] = Field(default_factory=dict)
    
    # Heatmap data (location-based)
    location_heatmap: List[Dict] = Field(default_factory=list)  # [{lat: 18.5, lng: 73.8, intensity: 5}]
    
    # AI metadata
    ai_metadata: Optional[Dict] = None
    
    # Comments
    comments: List[CommentResponse] = Field(default_factory=list)
    
    # Total interactions
    total_upvotes: int = Field(default=0)
    total_downvotes: int = Field(default=0)
    total_comments: int = Field(default=0)
    total_reports: int = Field(default=0)
