"""
Admin endpoints - Human-in-the-loop control layer.

DESIGN PRINCIPLES (CRITICAL):
- Humans review high-impact cases ONLY (not all reports)
- Humans do NOT verify truth - they assess risk and clarity
- Humans can upgrade confidence to HIGH (only upgrade, not downgrade)
- Humans can change report status for workflow management
- NO automated authority escalation from these endpoints
- NO auto-broadcasting or alert triggers

SCOPE OF ADMIN:
✅ Upgrade confidence MEDIUM → HIGH
✅ Change report status (workflow transitions)
✅ Add admin notes for transparency
✅ Provide human judgment on risk/clarity

❌ NOT verify truth or authenticity
❌ NOT edit report content
❌ NOT delete reports
❌ NOT contact authorities automatically
❌ NOT broadcast alerts
"""

from fastapi import APIRouter, HTTPException, status, Query
from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum
from app.services.report_service import (
    upgrade_report_confidence,
    get_report_by_id
)
from app.services.reviewer_service import get_reviewer_service
from app.services.status_workflow import ReportStatus, StatusWorkflowEngine
from app.services.priority_scoring import get_priority_scoring_service
from app.services.escalation_engine import get_escalation_engine
from app.services.whatsapp_service import get_whatsapp_service


router = APIRouter(prefix="/admin", tags=["Admin"])


# Phase 5B: Issue confidence recalculation
from app.services.issue_confidence_engine import (
    recalculate_issue_confidence,
    recalculate_all_issues_confidence
)


# Enums for validation
class ConfidenceLevel(str, Enum):
    """
    Valid confidence levels.
    Only HIGH is allowed for admin upgrades (cannot downgrade).
    """
    HIGH = "HIGH"


class ReportStatusEnum(str, Enum):
    """
    Valid report status values (Phase-2 strict workflow).
    Represents workflow states, NOT truth verification.
    """
    UNDER_REVIEW = "UNDER_REVIEW"      # Initial state, awaiting review
    VERIFIED = "VERIFIED"               # Reviewed and validated
    ACTION_TAKEN = "ACTION_TAKEN"       # Action initiated/resolved
    CLOSED = "CLOSED"                   # Final state, issue resolved


# Request models
class ConfidenceUpdateRequest(BaseModel):
    """
    Request to upgrade confidence to HIGH.
    Requires human judgment and optional explanation.
    """
    confidence: ConfidenceLevel = Field(..., description="Must be HIGH (upgrades only)")
    admin_note: Optional[str] = Field(None, max_length=500, description="Optional admin explanation")


class StatusUpdateRequest(BaseModel):
    """
    Request to change report status (Phase-2 strict workflow).
    Used for workflow management, NOT truth verification.
    """
    status: ReportStatusEnum = Field(..., description="New status value")
    reviewer_id: str = Field(..., description="Reviewer identifier")
    note: Optional[str] = Field(None, max_length=500, description="Optional note explaining the change")


class ReviewerNoteRequest(BaseModel):
    """Request to add a reviewer note."""
    note: str = Field(..., min_length=1, max_length=1000, description="Note text")
    reviewer_id: str = Field(..., description="Reviewer identifier")


class OverrideAIClassificationRequest(BaseModel):
    """Request to override AI classification."""
    override_category: str = Field(..., min_length=1, max_length=100, description="New category to use")
    reviewer_id: str = Field(..., description="Reviewer identifier")
    note: Optional[str] = Field(None, max_length=500, description="Optional note explaining override")


@router.patch("/reports/{report_id}/confidence")
async def upgrade_confidence(report_id: str, request: ConfidenceUpdateRequest):
    """
    Upgrade report confidence to HIGH (human-in-the-loop decision).
    
    **Human Role:**
    - Assess risk level and clarity
    - Confirm pattern consistency
    - Provide judgment on public awareness needs
    
    **NOT verifying truth** - just assessing impact and coherence.
    
    **Rules:**
    - Can only upgrade to HIGH (no downgrades)
    - Typically used for MEDIUM → HIGH upgrades
    - Adds transparency via admin_note
    - Records reviewed_at timestamp
    
    Args:
        report_id: Firestore document ID
        request: Confidence upgrade request with optional note
    
    Returns:
        Updated report with HIGH confidence
    
    Raises:
        404: Report not found
        400: Invalid upgrade (e.g., already HIGH)
        500: Server error
    """
    try:
        # Fetch existing report
        existing_report = await get_report_by_id(report_id)
        
        if not existing_report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Report {report_id} not found"
            )
        
        # Prevent redundant upgrades
        current_confidence = existing_report.get("confidence", "LOW")
        if current_confidence == "HIGH":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Report is already at HIGH confidence"
            )
        
        # Perform upgrade
        updated_report = await upgrade_report_confidence(
            report_id=report_id,
            confidence="HIGH",
            admin_note=request.admin_note
        )
        
        return {
            "success": True,
            "message": "Confidence upgraded to HIGH by admin",
            "report": updated_report
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upgrade confidence: {str(e)}"
        )


@router.patch("/reports/{report_id}/status")
async def change_status(report_id: str, request: StatusUpdateRequest):
    """
    Change report status (Phase-2 strict workflow).
    
    **Status Meanings:**
    - UNDER_REVIEW: Initial state, awaiting review
    - VERIFIED: Reviewed and validated
    - ACTION_TAKEN: Action initiated/resolved
    - CLOSED: Final state, issue resolved
    
    **Important:**
    - Status does NOT mean "verified as true"
    - Status reflects workflow state and reviewer judgment
    - Strict workflow: no skipping states, no backward transitions
    
    Args:
        report_id: Firestore document ID
        request: Status change request with reviewer_id and optional note
    
    Returns:
        Updated report with new status
    
    Raises:
        404: Report not found
        400: Invalid status transition
        500: Server error
    """
    try:
        reviewer_service = get_reviewer_service()
        
        # Perform status update with workflow validation
        updated_report = reviewer_service.update_status(
            report_id=report_id,
            new_status=request.status.value,
            reviewer_id=request.reviewer_id,
            note=request.note
        )
        
        return {
            "success": True,
            "message": f"Status updated to {request.status.value}",
            "report": updated_report
        }
    
    except ValueError as e:
        # Invalid transition or report not found
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update status: {str(e)}"
        )


@router.get("/reports")
async def get_reports(
    status: Optional[str] = Query(None, description="Filter by status"),
    confidence: Optional[str] = Query(None, description="Filter by confidence"),
    locality: Optional[str] = Query(None, description="Filter by locality"),
    issue_type: Optional[str] = Query(None, description="Filter by issue_type"),
    city: Optional[str] = Query(None, description="Filter by city"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of reports")
):
    """
    Get reports with filtering (Phase-2 reviewer endpoint).
    
    Args:
        status: Filter by status
        confidence: Filter by confidence level
        locality: Filter by locality
        issue_type: Filter by user-selected issue_type
        city: Filter by city
        limit: Maximum number of reports to return
    
    Returns:
        List of reports matching filters
    """
    try:
        reviewer_service = get_reviewer_service()
        reports = reviewer_service.get_reports(
            status=status,
            confidence=confidence,
            locality=locality,
            issue_type=issue_type,
            city=city,
            limit=limit
        )
        
        return {
            "success": True,
            "count": len(reports),
            "reports": reports
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve reports: {str(e)}"
        )


@router.post("/reports/{report_id}/notes")
async def add_reviewer_note(report_id: str, request: ReviewerNoteRequest):
    """
    Add a reviewer note to a report (Phase-2).
    
    Args:
        report_id: Firestore document ID
        request: Note request with reviewer_id
    
    Returns:
        Updated report with new note
    """
    try:
        reviewer_service = get_reviewer_service()
        updated_report = reviewer_service.add_reviewer_note(
            report_id=report_id,
            note=request.note,
            reviewer_id=request.reviewer_id
        )
        
        return {
            "success": True,
            "message": "Reviewer note added",
            "report": updated_report
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add note: {str(e)}"
        )


@router.post("/reports/{report_id}/override-ai")
async def override_ai_classification(report_id: str, request: OverrideAIClassificationRequest):
    """
    Override AI classification without deleting original AI data (Phase-2).
    
    Stores override in ai_metadata.override field, preserving original.
    
    Args:
        report_id: Firestore document ID
        request: Override request with reviewer_id
    
    Returns:
        Updated report with AI override
    """
    try:
        reviewer_service = get_reviewer_service()
        updated_report = reviewer_service.override_ai_classification(
            report_id=report_id,
            reviewer_id=request.reviewer_id,
            override_category=request.override_category,
            note=request.note
        )
        
        return {
            "success": True,
            "message": "AI classification overridden",
            "report": updated_report
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to override AI classification: {str(e)}"
        )


@router.get("/reports/{report_id}/allowed-transitions")
async def get_allowed_transitions(report_id: str):
    """
    Get allowed status transitions for a report (Phase-2 workflow).
    
    Args:
        report_id: Firestore document ID
    
    Returns:
        Current status and allowed next statuses
    """
    try:
        report = await get_report_by_id(report_id)
        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Report {report_id} not found"
            )
        
        current_status = report.get("status", "UNDER_REVIEW")
        workflow = StatusWorkflowEngine()
        allowed = workflow.get_allowed_transitions(current_status)
        
        return {
            "success": True,
            "current_status": current_status,
            "allowed_transitions": allowed
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get allowed transitions: {str(e)}"
        )


# PHASE-3: Priority and Escalation Endpoints

@router.post("/reports/{report_id}/recalculate-priority")
async def recalculate_priority(report_id: str):
    """
    Recalculate priority score for a report (Phase-3).
    
    Args:
        report_id: Firestore document ID
    
    Returns:
        Updated priority score and reason
    """
    try:
        priority_service = get_priority_scoring_service()
        result = priority_service.recalculate_priority(report_id)
        
        return {
            "success": True,
            "priority_score": result["priority_score"],
            "priority_reason": result["priority_reason"]
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to recalculate priority: {str(e)}"
        )


@router.post("/reports/{report_id}/escalate")
async def approve_escalation(
    report_id: str,
    reviewer_id: str = Query(..., description="Reviewer identifier"),
    note: Optional[str] = Query(None, description="Optional note")
):
    """
    Approve escalation for a report (Phase-3 reviewer action).
    
    Manually flags a report for escalation even if it doesn't meet automatic criteria.
    
    Args:
        report_id: Firestore document ID
        reviewer_id: Reviewer identifier
        note: Optional note explaining escalation
    
    Returns:
        Updated report with escalation flag set
    """
    try:
        escalation_engine = get_escalation_engine()
        
        # Get current report
        report = await get_report_by_id(report_id)
        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Report {report_id} not found"
            )
        
        # Evaluate escalation to get reason
        escalation_result = escalation_engine.evaluate_escalation(report)
        escalation_reason = escalation_result.get("escalation_reason") or note or "Manually escalated by reviewer"
        
        # Update escalation flag
        updated_report = escalation_engine.update_escalation_flag(
            report_id=report_id,
            escalation_flag=True,
            escalation_reason=escalation_reason,
            changed_by=reviewer_id
        )
        
        return {
            "success": True,
            "message": "Report escalated",
            "report": updated_report
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to escalate report: {str(e)}"
        )


@router.post("/reports/{report_id}/dismiss-escalation")
async def dismiss_escalation(
    report_id: str,
    reviewer_id: str = Query(..., description="Reviewer identifier"),
    note: Optional[str] = Query(None, description="Optional note explaining dismissal")
):
    """
    Dismiss escalation for a report (Phase-3 reviewer action).
    
    Removes escalation flag after reviewer review.
    
    Args:
        report_id: Firestore document ID
        reviewer_id: Reviewer identifier
        note: Optional note explaining dismissal
    
    Returns:
        Updated report with escalation flag cleared
    """
    try:
        escalation_engine = get_escalation_engine()
        
        # Get current report
        report = await get_report_by_id(report_id)
        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Report {report_id} not found"
            )
        
        dismissal_reason = note or "Escalation dismissed by reviewer"
        
        # Update escalation flag
        updated_report = escalation_engine.update_escalation_flag(
            report_id=report_id,
            escalation_flag=False,
            escalation_reason=dismissal_reason,
            changed_by=reviewer_id
        )
        
        return {
            "success": True,
            "message": "Escalation dismissed",
            "report": updated_report
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to dismiss escalation: {str(e)}"
        )


@router.get("/escalation-candidates")
async def get_escalation_candidates(
    limit: int = Query(50, ge=1, le=200, description="Maximum number of candidates")
):
    """
    Get all reports flagged for escalation (Phase-3).
    
    Returns reports sorted by priority_score (highest first).
    
    Args:
        limit: Maximum number of candidates to return
    
    Returns:
        List of escalated reports
    """
    try:
        escalation_engine = get_escalation_engine()
        candidates = escalation_engine.get_escalation_candidates(limit=limit)
        
        return {
            "success": True,
            "count": len(candidates),
            "candidates": candidates
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get escalation candidates: {str(e)}"
        )


@router.get("/whatsapp-alerts")
async def get_whatsapp_alert_logs(limit: int = 50):
    """
    Retrieve WhatsApp alert logs (simulated sends).
    
    This endpoint shows all alerts that have been generated.
    In production, these would be actual WhatsApp messages.
    In prototype mode, these are simulated and logged to Firestore.
    
    **What this shows:**
    - Alert messages generated
    - Reports that triggered alerts
    - Timestamps and locations
    
    **Note:**
    All alerts are SIMULATED in prototype mode.
    No real WhatsApp messages are sent.
    
    Args:
        limit: Maximum number of logs to retrieve (default 50)
    
    Returns:
        List of WhatsApp alert log entries
    """
    try:
        whatsapp_service = get_whatsapp_service()
        logs = whatsapp_service.get_alert_log(limit=limit)
        
        return {
            "success": True,
            "count": len(logs),
            "note": "SIMULATED ALERTS - No real messages sent (prototype mode)",
            "alerts": logs
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve alert logs: {str(e)}"
        )


@router.post("/issues/{issue_id}/recalculate-confidence")
async def recalculate_issue_confidence_endpoint(issue_id: str):
    """
    Recalculate confidence for a specific issue.
    
    Phase 5B: This endpoint triggers a deterministic recalculation
    of issue confidence based on current linked reports.
    
    **What this does:**
    - Recalculates confidence_score based on:
      * Additional reports beyond initial cluster
      * Unique reporters (IP diversity)
      * Time persistence
      * Media evidence
    - Updates confidence label (LOW/MEDIUM/HIGH)
    - Adds entry to confidence_timeline
    
    **When to use:**
    - After new reports link to an issue
    - Manual refresh of confidence scores
    - Scheduled maintenance
    
    Args:
        issue_id: The issue document ID
    
    Returns:
        Updated issue data with new confidence
    """
    try:
        result = recalculate_issue_confidence(issue_id)
        
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Issue {issue_id} not found"
            )
        
        return {
            "success": True,
            "issue_id": issue_id,
            "confidence": result.get("confidence"),
            "confidence_score": result.get("confidence_score"),
            "confidence_reason": result.get("confidence_reason"),
            "updated_at": result.get("updated_at")
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to recalculate confidence: {str(e)}"
        )


@router.post("/issues/recalculate-all-confidence")
async def recalculate_all_issues_confidence_endpoint():
    """
    Recalculate confidence for all issues in the system.
    
    Phase 5B: Batch operation to refresh all issue confidence scores.
    
    **Use cases:**
    - Scheduled maintenance
    - After bulk report imports
    - System recovery after data issues
    
    **Performance:**
    - Processes all issues sequentially
    - May take time for large datasets
    - Safe to run multiple times (idempotent)
    
    Returns:
        Summary of recalculation results
    """
    try:
        result = recalculate_all_issues_confidence()
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("error", "Unknown error")
            )
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to recalculate all confidence: {str(e)}"
        )
