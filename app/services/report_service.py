"""
Report service - Business logic for citizen report handling.
Handles Firestore CRUD operations for reports.

DESIGN NOTE:
- Stores citizen reports in Firestore
- Calls AI interpreter for assistance (Step 3)
- AI output is advisory only, does NOT verify truth
- No auto-escalation or broadcasting here
"""

from firebase_admin import firestore
from app.config.firebase import get_db
from app.models.report import ReportCreate, ReportResponse
from app.services.ai_interpreter import get_ai_interpreter
from app.services.confidence_engine import get_confidence_engine
from app.services.duplicate_detection import get_duplicate_detection_service
from app.services.status_workflow import StatusWorkflowEngine, ReportStatus
from app.services.priority_scoring import get_priority_scoring_service
from app.services.escalation_engine import get_escalation_engine
from app.utils.security import hash_ip_address
from app.utils.geocoding import ensure_city_not_null
from datetime import datetime
from typing import List
import logging

logger = logging.getLogger(__name__)


async def create_report(report_data: ReportCreate) -> ReportResponse:
    """
    Create a new citizen report and store it in Firestore.
    
    Flow:
    1. Store report in Firestore (primary action)
    2. Call AI interpreter for assistance (advisory only)
    3. Update report with AI metadata
    4. Calculate confidence based on pattern detection
    5. Return complete report
    
    IMPORTANT: If AI fails, report is still stored and returned.
    AI interpretation is helpful but NOT required.
    
    Args:
        report_data: Validated report data from POST request
    
    Returns:
        ReportResponse: The created report with generated ID, timestamp, and AI metadata
    """
    db = get_db()
    
    # PHASE-2: Duplicate detection and rate limiting
    duplicate_service = get_duplicate_detection_service()
    
    # Hash IP address for privacy protection
    ip_address_hash = hash_ip_address(report_data.ip_address)
    
    # Check rate limit
    rate_limit_check = duplicate_service.check_rate_limit(ip_address_hash)
    if rate_limit_check.get("is_rate_limited"):
        raise ValueError(
            f"Rate limit exceeded. Maximum {rate_limit_check['limit']} reports per hour. "
            f"Please try again later."
        )
    
    # Check for duplicates
    duplicate_check = duplicate_service.check_duplicate(
        ip_address_hash=ip_address_hash,
        locality=report_data.locality,
        latitude=report_data.latitude,
        longitude=report_data.longitude,
        description=report_data.description
    )
    
    if duplicate_check.get("is_duplicate"):
        raise ValueError(
            f"Duplicate report detected. Similar report already exists: {duplicate_check['duplicate_report_id']}"
        )
    
    # PHASE-2: Ensure city is never null
    city = ensure_city_not_null(
        city=report_data.city,
        locality=report_data.locality,
        latitude=report_data.latitude,
        longitude=report_data.longitude
    )
    
    # PHASE-2: Initialize status history with initial state
    workflow = StatusWorkflowEngine()
    initial_status = ReportStatus.UNDER_REVIEW.value
    status_history = [workflow.create_status_history_entry(
        from_status="",
        to_status=initial_status,
        changed_by="system",
        note="Report created"
    )]
    
    # STEP 1: Prepare document reference and base data (without AI metadata first)
    doc_ref = db.collection("reports").document()  # Auto-generate unique ID
    report_dict = {
        "id": doc_ref.id,
        "description": report_data.description,
        "issue_type": report_data.issue_type or "",  # User-selected (source of truth)
        "city": city,  # PHASE-2: Never null
        "locality": report_data.locality,
        "latitude": report_data.latitude,
        "longitude": report_data.longitude,
        "reporter_name": report_data.reporter_name if hasattr(report_data, 'reporter_name') else None,
        "ip_address_hash": ip_address_hash,  # PHASE-2: Hashed IP (privacy-protected)
        "reporter_context": report_data.reporter_context.value if report_data.reporter_context else None,
        "media_urls": report_data.media_urls or [],
        "confidence": "LOW",  # Default confidence level (will be recalculated)
        "confidence_reason": "Single report, awaiting corroboration",  # Default reason
        "status": initial_status,  # PHASE-2: Strict workflow
        "status_history": status_history,  # PHASE-2: Audit trail
        "reviewer_notes": [],  # PHASE-2: Reviewer notes array
        "ai_metadata": {},  # Will be populated by AI (best-effort, non-blocking)
        # PHASE-3: Priority scoring and escalation (initialized as null/false)
        "priority_score": None,  # Will be calculated after confidence
        "priority_reason": None,
        "escalation_flag": False,
        "escalation_reason": None,
        "escalation_history": [],
        "created_at": firestore.SERVER_TIMESTAMP,  # Server-side timestamp
    }
    
    # STEP 2: Store report in Firestore (MUST succeed)
    try:
        doc_ref.set(report_dict)
        logger.info(f"Report saved to Firestore: {doc_ref.id}")
    except Exception as e:
        # Explicitly log Firestore write failures for debugging/demo confidence
        logger.error(f"Failed to save report to Firestore: {e}", exc_info=True)
        raise
    
    # STEP 3: Call AI interpreter for assistance (OPTIONAL, NON-BLOCKING)
    # PHASE-3 PART 2: AI runs AFTER report ingestion, BEFORE confidence calculation
    # AI is advisory only and never blocks report creation
    try:
        from app.core.settings import settings
        
        if settings.AI_ENABLED:
            logger.info(f"Requesting AI interpretation for report {doc_ref.id}")
            
            ai_interpreter = get_ai_interpreter()
            ai_result = ai_interpreter.interpret_report(
                description=report_data.description,
                city=report_data.city or "",
                locality=report_data.locality
            )
            
            # Update report with AI metadata (includes Phase-3 Part 2 extensions)
            doc_ref.update({"ai_metadata": ai_result})
            
            # Log AI model used for auditability
            model_name = ai_result.get("model_name", "unknown")
            if ai_result.get("error"):
                logger.warning(f"⚠️ AI interpretation completed with errors for report {doc_ref.id} (model: {model_name})")
            else:
                logger.info(f"✅ AI interpretation added to report {doc_ref.id} (model: {model_name})")
        else:
            logger.info(f"AI disabled (AI_ENABLED=false), skipping AI interpretation for report {doc_ref.id}")
            # ai_metadata remains empty {} - system continues working normally
        
    except Exception as e:
        # If AI fails, log but continue (report is already stored)
        # This ensures AI never blocks report ingestion
        logger.error(f"⚠️ AI interpretation failed for report {doc_ref.id}: {str(e)}", exc_info=True)
        logger.warning("Report stored successfully, but without AI metadata")
        
        # Store failure reason in ai_metadata for auditability
        try:
            doc_ref.update({
                "ai_metadata": {
                    "error": f"AI interpretation failed: {str(e)}",
                    "model_name": "error",
                    "model_version": "1.0.0",
                    "inference_timestamp": firestore.SERVER_TIMESTAMP
                }
            })
        except Exception as update_error:
            # Even updating failure metadata failed - log and continue
            logger.error(f"Failed to update AI failure metadata: {update_error}")
        
        # System continues working - ai_metadata may be empty or contain error
    
    # STEP 4: Calculate confidence based on pattern detection
    try:
        logger.info(f"Calculating confidence for report {doc_ref.id}")
        
        # Retrieve the report data (need it for confidence calculation)
        created_doc = doc_ref.get()
        created_data = created_doc.to_dict()
        created_data["id"] = created_doc.id  # Add ID for confidence engine
        
        # Call confidence engine
        confidence_engine = get_confidence_engine()
        confidence_engine.recalculate_confidence(created_data)
        
        logger.info(f"✅ Confidence calculated for report {doc_ref.id}")
        
    except Exception as e:
        # If confidence calculation fails, log but continue (report is already stored)
        logger.warning(f"⚠️ Confidence calculation failed for report {doc_ref.id}: {str(e)}")
        logger.warning("Report stored successfully, but confidence remains at default")
    
    # PHASE-3: Calculate priority score and evaluate escalation
    try:
        logger.info(f"Calculating priority and escalation for report {doc_ref.id}")
        
        # Retrieve updated report data (with confidence)
        updated_doc = doc_ref.get()
        updated_data = updated_doc.to_dict()
        updated_data["id"] = updated_doc.id
        
        # Calculate priority score
        priority_service = get_priority_scoring_service()
        priority_result = priority_service.calculate_priority(updated_data)
        
        # Update priority fields
        doc_ref.update({
            "priority_score": priority_result["priority_score"],
            "priority_reason": priority_result["priority_reason"]
        })
        
        # Update report data with priority for escalation evaluation
        updated_data["priority_score"] = priority_result["priority_score"]
        updated_data["priority_reason"] = priority_result["priority_reason"]
        
        # Evaluate escalation
        escalation_engine = get_escalation_engine()
        escalation_result = escalation_engine.evaluate_escalation(updated_data)
        
        # Update escalation flag if needed
        if escalation_result["escalation_flag"]:
            escalation_engine.update_escalation_flag(
                report_id=doc_ref.id,
                escalation_flag=True,
                escalation_reason=escalation_result["escalation_reason"],
                changed_by="system"
            )
        
        logger.info(f"✅ Priority and escalation evaluated for report {doc_ref.id}")
        
    except Exception as e:
        # If priority/escalation fails, log but continue (report is already stored)
        logger.warning(f"⚠️ Priority/escalation calculation failed for report {doc_ref.id}: {str(e)}")
        logger.warning("Report stored successfully, but priority/escalation not calculated")
    
    # STEP 5: Retrieve the final document with all updates (AI + confidence + priority + escalation)
    final_doc = doc_ref.get()
    final_data = final_doc.to_dict()
    
    # Return as response model
    return ReportResponse(
        id=final_doc.id,
        description=final_data["description"],
        issue_type=final_data.get("issue_type") or None,
        city=final_data["city"],
        locality=final_data["locality"],
        latitude=final_data["latitude"],
        longitude=final_data["longitude"],
        reporter_context=final_data.get("reporter_context"),
        media_urls=final_data.get("media_urls", []),
        confidence=final_data["confidence"],
        confidence_reason=final_data.get("confidence_reason"),
        status=final_data["status"],
        ai_metadata=final_data.get("ai_metadata"),
        reviewer_notes=final_data.get("reviewer_notes", []),  # PHASE-2
        status_history=final_data.get("status_history", []),  # PHASE-2
        reporter_name=final_data.get("reporter_name"),
        ip_address_hash=final_data.get("ip_address_hash"),  # PHASE-2: Hashed IP
        priority_score=final_data.get("priority_score"),  # PHASE-3
        priority_reason=final_data.get("priority_reason"),  # PHASE-3
        escalation_flag=final_data.get("escalation_flag", False),  # PHASE-3
        escalation_reason=final_data.get("escalation_reason"),  # PHASE-3
        escalation_history=final_data.get("escalation_history", []),  # PHASE-3
        created_at=final_data["created_at"]
    )


async def get_all_reports() -> List[ReportResponse]:
    """
    Retrieve all reports from Firestore.
    Sorted by created_at in descending order (newest first).
    
    Returns:
        List[ReportResponse]: All reports in the system
    """
    db = get_db()
    
    # Query all reports, ordered by creation time
    reports_ref = db.collection("reports").order_by("created_at", direction=firestore.Query.DESCENDING)
    docs = reports_ref.stream()
    
    # Convert Firestore documents to response models
    reports = []
    for doc in docs:
        data = doc.to_dict()
        reports.append(
            ReportResponse(
                id=doc.id,
                description=data["description"],
                issue_type=data.get("issue_type") or None,
                city=data["city"],
                locality=data["locality"],
                latitude=data["latitude"],
                longitude=data["longitude"],
                reporter_context=data.get("reporter_context"),
                media_urls=data.get("media_urls"),
                confidence=data["confidence"],
                confidence_reason=data.get("confidence_reason"),
                status=data["status"],
                ai_metadata=data.get("ai_metadata"),
                reviewer_notes=data.get("reviewer_notes", []),  # PHASE-2
                status_history=data.get("status_history", []),  # PHASE-2
                admin_note=data.get("admin_note"),  # Legacy field
                reviewed_at=data.get("reviewed_at"),
                created_at=data["created_at"],
                whatsapp_alert_status=data.get("whatsapp_alert_status", "NOT_SENT"),
                whatsapp_alert_sent_at=data.get("whatsapp_alert_sent_at"),
                ip_address_hash=data.get("ip_address_hash"),  # PHASE-2
                priority_score=data.get("priority_score"),  # PHASE-3
                priority_reason=data.get("priority_reason"),  # PHASE-3
                escalation_flag=data.get("escalation_flag", False),  # PHASE-3
                escalation_reason=data.get("escalation_reason"),  # PHASE-3
                escalation_history=data.get("escalation_history", [])  # PHASE-3
            )
        )
    
    return reports


async def get_report_by_id(report_id: str) -> dict:
    """
    Retrieve a single report by ID.
    
    Args:
        report_id: Firestore document ID
    
    Returns:
        dict: Report data or None if not found
    """
    db = get_db()
    
    doc_ref = db.collection("reports").document(report_id)
    doc = doc_ref.get()
    
    if not doc.exists:
        return None
    
    data = doc.to_dict()
    data["id"] = doc.id
    return data


async def upgrade_report_confidence(
    report_id: str,
    confidence: str,
    admin_note: str = None
) -> dict:
    """
    Upgrade report confidence to HIGH (admin action).
    
    This is the ONLY way to reach HIGH confidence.
    It requires human judgment and provides transparency.
    
    Flow:
    1. Update confidence to HIGH
    2. Update confidence_reason to explain admin decision
    3. Add admin_note if provided
    4. Record reviewed_at timestamp
    5. Preserve audit trail
    
    Args:
        report_id: Firestore document ID
        confidence: New confidence level (must be "HIGH")
        admin_note: Optional admin explanation
    
    Returns:
        dict: Updated report data
    """
    db = get_db()
    
    doc_ref = db.collection("reports").document(report_id)
    
    # Prepare update data
    update_data = {
        "confidence": confidence,
        "confidence_reason": "Upgraded to HIGH by admin review",
        "reviewed_at": firestore.SERVER_TIMESTAMP
    }
    
    if admin_note:
        update_data["admin_note"] = admin_note
    
    # Update Firestore
    doc_ref.update(update_data)
    
    # Retrieve updated document
    updated_doc = doc_ref.get()
    updated_data = updated_doc.to_dict()
    updated_data["id"] = updated_doc.id
    
    logger.info(f"✅ Admin upgraded report {report_id} to HIGH confidence")
    
    return updated_data


async def update_report_status(
    report_id: str,
    status: str,
    admin_note: str = None
) -> dict:
    """
    Update report status (admin workflow action).
    
    Status values represent workflow states, NOT truth verification:
    - UNDER_OBSERVATION: Default, monitoring for patterns
    - CONFIRMED: Human-reviewed for public awareness
    - RESOLVED: Issue has been addressed
    
    Args:
        report_id: Firestore document ID
        status: New status value
        admin_note: Optional admin explanation
    
    Returns:
        dict: Updated report data
    """
    db = get_db()
    
    doc_ref = db.collection("reports").document(report_id)
    
    # Prepare update data
    update_data = {
        "status": status,
        "reviewed_at": firestore.SERVER_TIMESTAMP
    }
    
    if admin_note:
        update_data["admin_note"] = admin_note
    
    # Update Firestore
    doc_ref.update(update_data)
    
    # Retrieve updated document
    updated_doc = doc_ref.get()
    updated_data = updated_doc.to_dict()
    updated_data["id"] = updated_doc.id
    
    logger.info(f"✅ Admin updated report {report_id} status to {status}")
    
    return updated_data
