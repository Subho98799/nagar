"""
Report endpoints - API routes for citizen report submission and retrieval.
"""

from typing import List
from fastapi import APIRouter, HTTPException, status

from app.models.report import ReportCreate, ReportResponse
from app.services.report_service import create_report, get_all_reports

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def submit_report(report: ReportCreate):
    """
    Submit a new citizen report.
    
    This endpoint:
    1. Validates the report data
    2. Stores it in Firestore (reports collection)
    3. Triggers issue aggregation (non-blocking)
    
    Returns the created report with generated ID.
    """
    import logging
    import traceback
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"📝 POST /reports - Creating report: city={report.city}, issue_type={report.issue_type}")
        
        # Verify Firestore is initialized
        from app.config.firebase import get_db
        db = get_db()
        if db is None:
            logger.error("❌ Firestore DB not initialized")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database not initialized. Please check Firebase configuration."
            )
        
        result = await create_report(report)
        logger.info(f"✅ Report created successfully: {result.id}")
        return result
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"❌ POST /reports - Report creation failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Report creation failed: {str(e)}"
        )


@router.get("", response_model=List[ReportResponse])
async def get_reports():
    try:
        return await get_all_reports()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve reports: {str(e)}",
        )
