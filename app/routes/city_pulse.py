"""
City Pulse endpoints - Aggregated city situation summary.

DESIGN PRINCIPLES (CRITICAL):
- City Pulse is a SNAPSHOT, not a prediction
- City Pulse is CALM and NEUTRAL, not alarming
- City Pulse does NOT trigger actions
- City Pulse does NOT recommend responses

WHAT CITY PULSE PROVIDES:
✅ Current active issues by type
✅ Confidence breakdown (LOW/MEDIUM/HIGH)
✅ Affected localities
✅ Human-readable summary

WHAT CITY PULSE DOES NOT PROVIDE:
❌ Predictions or forecasts
❌ Trend analysis
❌ Recommendations
❌ Urgency indicators
❌ Historical comparisons
"""

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field
from typing import Dict, List, Optional
from datetime import datetime
from app.services.city_pulse_service import get_city_pulse_service


router = APIRouter(prefix="/city-pulse", tags=["City Pulse"])


# Response models
class CityPulseResponse(BaseModel):
    """
    City Pulse response model.
    
    Represents the current situation in a city as a calm, structured summary.
    """
    city: str = Field(..., description="City name")
    report_count: int = Field(..., description="Number of active reports")
    active_issues: Dict[str, int] = Field(
        ..., 
        description="Count of reports by issue type"
    )
    confidence_breakdown: Dict[str, int] = Field(
        ..., 
        description="Count of reports by confidence level (LOW/MEDIUM/HIGH)"
    )
    affected_localities: List[str] = Field(
        ..., 
        description="List of localities with active reports"
    )
    summary: str = Field(
        ..., 
        description="Human-readable summary of city situation"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "city": "Ranchi",
                "report_count": 7,
                "active_issues": {
                    "Traffic & Roads": 5,
                    "Water & Sanitation": 2
                },
                "confidence_breakdown": {
                    "LOW": 4,
                    "MEDIUM": 2,
                    "HIGH": 1
                },
                "affected_localities": [
                    "Lalpur",
                    "Main Chowk",
                    "Ratu Road"
                ],
                "summary": "Traffic & Roads along with water & sanitation issues are currently reported in Ranchi across 3 localities. 1 report(s) have been reviewed and confirmed."
            }
        }


@router.get("", response_model=CityPulseResponse)
async def get_city_pulse(
    city: str = Query(
        ..., 
        min_length=2, 
        max_length=100,
        description="City name to get pulse for",
        examples=["Ranchi", "Nashik", "Bhopal"]
    )
):
    """
    Get the current City Pulse for a given city.
    
    **What is City Pulse?**
    
    City Pulse is a calm, human-readable summary of the current situation
    in a city. It aggregates active citizen reports into structured data.
    
    **What City Pulse shows:**
    - Active issues by type (Traffic, Water, etc.)
    - Confidence breakdown (how many reports are corroborated)
    - Affected localities
    - Natural language summary
    
    **What City Pulse does NOT do:**
    - Predict future events
    - Recommend actions
    - Trigger alerts
    - Contact authorities
    
    **Active Reports Include:**
    - Status: UNDER_OBSERVATION
    - Status: CONFIRMED
    
    (RESOLVED reports are excluded - they're no longer active)
    
    Args:
        city: City name (required query parameter)
    
    Returns:
        CityPulseResponse: Structured summary of city situation
    
    Example:
        GET /city-pulse?city=Ranchi
    """
    try:
        # Get the city pulse service
        pulse_service = get_city_pulse_service()
        
        # Generate city pulse
        pulse_data = pulse_service.get_city_pulse(city)
        
        return CityPulseResponse(
            city=pulse_data["city"],
            report_count=pulse_data["report_count"],
            active_issues=pulse_data["active_issues"],
            confidence_breakdown=pulse_data["confidence_breakdown"],
            affected_localities=pulse_data["affected_localities"],
            summary=pulse_data["summary"]
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate City Pulse: {str(e)}"
        )


@router.get("/cities")
async def list_available_cities():
    """
    List all cities that have reports in the system.
    
    This is a helper endpoint to discover which cities have data.
    Useful for frontends that need to show city selection.
    
    Returns:
        List of city names with active reports
    """
    try:
        from app.config.firebase import get_db
        
        db = get_db()
        reports_ref = db.collection("reports")
        
        # Get all unique cities
        docs = reports_ref.stream()
        
        cities = set()
        for doc in docs:
            data = doc.to_dict()
            city = data.get("city", "").strip()
            if city:
                cities.add(city)
        
        return {
            "cities": sorted(list(cities)),
            "count": len(cities)
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list cities: {str(e)}"
        )
