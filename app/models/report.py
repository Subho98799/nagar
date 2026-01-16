"""
Pydantic models for citizen reports.
These models handle validation for report submission and responses.
"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List, Dict
from enum import Enum


class ReporterContext(str, Enum):
    """
    Optional context about who is reporting.
    Helps understand perspective but does NOT verify identity.
    """
    CITIZEN = "Citizen"
    SHOP_OWNER = "Shop Owner"
    STUDENT = "Student"
    HEALTHCARE_WORKER = "Healthcare Worker"
    DELIVERY_WORKER = "Delivery Worker"


class ReportCreate(BaseModel):
    """
    Model for creating a new report (incoming POST request).
    These are the fields citizens provide when submitting a report.
    """
    description: str = Field(..., min_length=5, max_length=1000, description="What the citizen observed")
    
    #issue_type: str = Field(..., min_length=1, max_length=100, description="Type of issue (from form select)")
    issue_type: Optional[str] = Field(
    None,
    max_length=100,
    description="Type of issue (optional during submission)"
)
    # City is optional and may be omitted or sent as an empty string by the frontend.
    # Do NOT enforce a minimum length here; backend will normalize via ensure_city_not_null.
    city: Optional[str] = Field(None, max_length=100, description="City name (optional until frontend sends)")
    locality: str = Field(..., min_length=1, max_length=200, description="Neighborhood or locality")
    latitude: Optional[float] = Field(None, ge=-90, le=90, description="Latitude coordinate (optional if frontend omits)")
    longitude: Optional[float] = Field(None, ge=-180, le=180, description="Longitude coordinate (optional if frontend omits)")
    reporter_name: Optional[str] = Field(None, description="Name of the reporter (form field, may be blank)")
    ip_address: Optional[str] = Field(None, description="Reporter IP address (best-effort capture)")
    reporter_context: ReporterContext = Field(default=ReporterContext.CITIZEN, description="Optional reporter context")
    media_urls: Optional[List[str]] = Field(None, description="Optional list of image/video URLs")
    # Frontend location fields (user-initiated geocoding)
    resolved_address: Optional[str] = Field(None, max_length=500, description="Address resolved from coordinates (frontend geocoding)")
    user_entered_location: Optional[str] = Field(None, max_length=500, description="Location text entered/edited by user")
    location_source: Optional[str] = Field(None, description="Source: frontend-geocoded | backend-geocoded | manual")

    class Config:
        json_schema_extra = {
            "example": {
                "description": "Water leakage near community hall.",
                "issue_type": "Water",
                "city": "Pune",
                "locality": "Kothrud",
                "latitude": 18.5074,
                "longitude": 73.8077,
                "reporter_name": "Asha",
                "ip_address": "203.0.113.10",
                "reporter_context": "Citizen",
                "media_urls": ["https://example.com/photo.jpg"],
            }
        }
        extra = "ignore"


class ReviewerNote(BaseModel):
    """Reviewer note entry."""
    note: str = Field(..., description="Reviewer note text")
    reviewer_id: str = Field(..., description="Reviewer identifier")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="When note was added")


class StatusHistoryEntry(BaseModel):
    """Status transition history entry."""
    from_status: str = Field(..., description="Previous status")
    to_status: str = Field(..., description="New status")
    changed_by: str = Field(..., description="User/reviewer who made the change")
    timestamp: datetime = Field(..., description="When change occurred")
    note: Optional[str] = Field(None, description="Optional note explaining the change")


class ReportResponse(BaseModel):
    """
    Model for report responses (what API returns).
    Includes system-generated fields like ID and timestamps.
    Phase-2: Enhanced with reviewer metadata and status history.
    """
    id: str = Field(..., description="Firestore document ID")
    description: str
    issue_type: Optional[str] = None
    city: str = Field(..., description="City name (never null, defaults to UNKNOWN)")
    locality: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    reporter_context: Optional[str] = None
    media_urls: Optional[List[str]] = Field(default_factory=list, description="Media URLs")
    confidence: str = Field(default="LOW", description="Confidence level (default: LOW)")
    confidence_reason: Optional[str] = Field(default=None, description="Explainable reason for confidence level")
    status: str = Field(default="UNDER_REVIEW", description="Report status (Phase-2 workflow)")
    ai_metadata: Optional[Dict] = Field(default=None, description="AI-assisted interpretation (advisory only)")
    reviewer_notes: List[Dict] = Field(default_factory=list, description="Reviewer notes array")
    status_history: List[Dict] = Field(default_factory=list, description="Status transition history")
    admin_note: Optional[str] = Field(default=None, description="Legacy admin note (deprecated, use reviewer_notes)")
    reviewed_at: Optional[datetime] = Field(default=None, description="When admin reviewed this report")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="When report was created")
    # WhatsApp alert fields (Step 7)
    whatsapp_alert_status: str = Field(default="NOT_SENT", description="WhatsApp alert status: NOT_SENT, SENT, NOT_ELIGIBLE")
    whatsapp_alert_sent_at: Optional[datetime] = Field(default=None, description="When WhatsApp alert was sent")
    reporter_name: Optional[str] = None
    ip_address_hash: Optional[str] = Field(None, description="Hashed IP address (privacy-protected)")
    # Phase-3: Priority scoring and escalation
    priority_score: Optional[int] = Field(None, ge=0, le=100, description="System-derived priority score (0-100)")
    priority_reason: Optional[str] = Field(None, description="Explainable reason for priority score")
    escalation_flag: bool = Field(default=False, description="Whether report is flagged for escalation")
    escalation_reason: Optional[str] = Field(None, description="Reason for escalation flag")
    escalation_history: List[Dict] = Field(default_factory=list, description="Escalation flag change history")
    # Phase-4: Optional reverse-geocoded address fields (additive only)
    resolved_address: Optional[str] = Field(default=None, description="Human-readable address derived from coordinates")
    resolved_locality: Optional[str] = Field(default=None, description="Resolved neighbourhood/locality (if available)")
    resolved_city: Optional[str] = Field(default=None, description="Resolved city (if available)")
    resolved_state: Optional[str] = Field(default=None, description="Resolved state/region (if available)")
    resolved_country: Optional[str] = Field(default=None, description=" Resolved country (if available)")
    geocoding_provider: Optional[str] = Field(default=None, description="Which provider was used for reverse geocoding")
    geocoded_at: Optional[datetime] = Field(default=None, description="When reverse geocoding was attempted")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "abc123",
                "description": "Large pothole on MG Road near school",
                "issue_type": "Infrastructure",
                "city": "Nashik",
                "locality": "College Road",
                "latitude": 19.9975,
                "longitude": 73.7898,
                "reporter_context": "Citizen",
                "media_urls": ["https://example.com/image1.jpg"],
                "confidence": "HIGH",
                "confidence_reason": "Multiple similar reports detected nearby (3 reports within 500m and 30 minutes)",
                "status": "CONFIRMED",
                "ai_metadata": {
                    "ai_classified_category": "Traffic & Roads",
                    "severity_hint": "Medium",
                    "keywords": ["pothole", "school", "road"],
                    "summary": "Large pothole on MG Road near school"
                },
                "admin_note": "Reviewed cluster consistency. Approved for public awareness.",
                "reviewed_at": "2024-01-15T11:00:00Z",
                "created_at": "2024-01-15T10:30:00Z",
                "whatsapp_alert_status": "SENT",
                "whatsapp_alert_sent_at": "2024-01-15T11:05:00Z"
            }
        }
