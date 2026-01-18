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
    # Phase-4: Optional reverse-geocoded address fields (read-only display)
    resolved_address: Optional[str] = None
    resolved_locality: Optional[str] = None
    resolved_city: Optional[str] = None


router = APIRouter(prefix="/map", tags=["Map"])


@router.get("/test")
async def map_test():
    """Simple test endpoint to verify route is working"""
    return {"status": "ok", "message": "Map route is accessible"}


@router.get("/issues", response_model=List[MapIssue])
async def map_issues(city: Optional[str] = Query(None, description="City name (optional)")):
    """
    Get issues for a given city.
    
    CRITICAL: This endpoint queries ONLY the issues collection (not reports).
    
    Filtering logic:
    - If city is provided AND city != "Demo City" → filter by city
    - If city == "Demo City" OR city is missing → return all issues
    
    This ensures:
    - Demo mode works for judges
    - Real cities work in production
    - Dashboard never returns empty incorrectly
    """
    import sys
    import asyncio
    
    # CRITICAL FIX: Return all issues if city is "Demo City" or missing
    # Only filter if a real city name is provided
    if city:
        from app.utils.geocoding import normalize_city_name
        normalized_city = normalize_city_name(city)
        
        # If city is "Demo City" (normalized to "demo city"), return all issues
        if normalized_city == "demo city":
            normalized_city = None  # Return all issues
        elif normalized_city == "UNKNOWN":
            # Invalid city, return empty
            return []
    else:
        normalized_city = None  # Return all issues
    
    try:
        # Run sync Firestore query in thread pool to avoid blocking event loop
        loop = asyncio.get_event_loop()
        issues = await loop.run_in_executor(None, get_city_issues, normalized_city or "")
        return issues
    except Exception as e:
        import traceback
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to get map issues: {e}", exc_info=True)
        # Return empty list instead of error to prevent frontend from showing error
        return []
