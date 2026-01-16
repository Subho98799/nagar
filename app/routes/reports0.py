"""
Report endpoints - API routes for citizen report submission and retrieval.
Handles incoming reports from citizens and provides access to stored reports.
"""

import logging
import sys
import traceback
from typing import List

from fastapi import APIRouter, HTTPException, Request, status

from app.models.report import ReportCreate, ReportResponse
from app.services.report_service import create_report, get_all_reports


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/reports", tags=["Reports"])


@router.post("/", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
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
    # CRITICAL: Print to stderr so uvicorn shows it
    sys.stderr.write("=" * 80 + "\n")
    sys.stderr.write("🔥 POST /reports ROUTE HANDLER CALLED\n")
    sys.stderr.write("=" * 80 + "\n")
    sys.stderr.flush()
    
    try:
        sys.stderr.write(f"✅ Route handler entered, calling create_report...\n")
        sys.stderr.flush()
        
        # existing logic
        created_report = await create_report(report)
        
        sys.stderr.write(f"✅ create_report returned successfully\n")
        sys.stderr.flush()
        
        return created_report
    except Exception as e:
        # Print full traceback to stderr for immediate visibility in uvicorn
        sys.stderr.write("=" * 80 + "\n")
        sys.stderr.write("🔥 POST /reports ROUTE HANDLER CAUGHT EXCEPTION\n")
        sys.stderr.write("=" * 80 + "\n")
        sys.stderr.write(traceback.format_exc())
        sys.stderr.write("=" * 80 + "\n")
        sys.stderr.flush()
        
        # Also log it
        logger.error("POST /reports failed:\n%s", traceback.format_exc(), exc_info=True)
        
        # Include exception details in response
        error_detail = f"Report creation failed: {str(e)}"
        sys.stderr.write(f"Raising HTTPException with detail: {error_detail}\n")
        sys.stderr.flush()
        
        raise HTTPException(status_code=500, detail=error_detail)


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
        # Keep existing behavior here; focus is POST /reports traceback
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve reports: {str(e)}"
        )
