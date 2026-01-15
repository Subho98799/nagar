"""
Report endpoints - API routes for citizen report submission and retrieval.
Handles incoming reports from citizens and provides access to stored reports.
"""

from fastapi import APIRouter, HTTPException, status
from app.models.report import ReportCreate, ReportResponse
from app.services.report_service import create_report, get_all_reports
from typing import List


router = APIRouter(prefix="/reports", tags=["Reports"])


@router.post("", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
async def submit_report(report: ReportCreate):
    """
    Submit a new citizen report.
    
    This endpoint accepts observations from citizens and stores them.
    
    **Design Note:**
    - This does NOT verify the truth of the report
    - This does NOT auto-broadcast alerts
    - This does NOT contact authorities
    - Reports start with LOW confidence and UNDER_OBSERVATION status
    
    Args:
        report: Report data from citizen
    
    Returns:
        ReportResponse: The created report with ID and timestamp
    """
    try:
        created_report = await create_report(report)
        return created_report
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create report: {str(e)}"
        )


@router.get("", response_model=List[ReportResponse])
async def get_reports():
    """
    Retrieve all citizen reports.
    
    Returns reports sorted by creation time (newest first).
    
    **Future Enhancement:**
    - Add filtering by city, locality, status
    - Add pagination
    - Add date range filtering
    
    Returns:
        List[ReportResponse]: All reports in the system
    """
    try:
        reports = await get_all_reports()
        return reports
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve reports: {str(e)}"
        )
