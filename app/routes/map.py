"""Map routes - expose aggregated issues for frontend mapping.

This route returns a strict JSON shape expected by the frontend. We
use a Pydantic model so FastAPI validates and coerces types (timestamps
are returned as ISO strings by the service).
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from app.services.map_service import get_city_issues


class TimelineEvent(BaseModel):
    id: str
    timestamp: str
    time: str
    confidence: str
    description: Optional[str] = ""


class MapIssue(BaseModel):
    id: str
    title: str
    description: str
    issue_type: str
    severity: str
    confidence: str
    status: str
    latitude: float
    longitude: float
    locality: Optional[str] = ""
    city: Optional[str] = ""
    report_count: int
    created_at: str
    updated_at: str
    timeline: Optional[List[TimelineEvent]] = []
    operatorNotes: Optional[str] = None


router = APIRouter(prefix="/map", tags=["Map"])


@router.get("/issues", response_model=List[MapIssue])
async def map_issues(city: str = Query("Default", description="City name")):
    try:
        issues = get_city_issues(city)
        return issues
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get map issues: {str(e)}")
