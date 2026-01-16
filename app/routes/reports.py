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
    try:
        return await create_report(report)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Report creation failed: {str(e)}",
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
