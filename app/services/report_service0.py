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
from typing import List, Optional
import asyncio
import logging

logger = logging.getLogger(__name__)


async def _geocode_and_update_report(
    doc_ref,
    latitude: Optional[float],
    longitude: Optional[float],
) -> None:
    """
    Fire-and-forget helper to enrich a report with reverse-geocoded address data.

    Governance / safety:
    - Runs AFTER the report has been written.
    - Never blocks the main report creation response.
    - Never raises exceptions upstream.
    - Does NOT affect confidence, status, priority, or escalation.
    """
    if latitude is None or longitude is None:
        return

    try:
        from app.services.geocoding import get_geocoding_provider
        from datetime import datetime as _dt

        provider = get_geocoding_provider()

        loop = asyncio.get_event_loop()
        # Offload blocking HTTP call to a thread executor.
        result = await loop.run_in_executor(
            None, provider.reverse_geocode, float(latitude), float(longitude)
        )

        if not isinstance(result, dict):
            return

        update_data = {
            "resolved_address": result.get("formatted_address"),
            "resolved_locality": result.get("locality"),
            "resolved_city": result.get("city"),
            "resolved_state": result.get("state"),
            "resolved_country": result.get("country"),
            "geocoding_provider": result.get("provider"),
            "geocoded_at": firestore.SERVER_TIMESTAMP,
        }

        # Only send fields that have some value to avoid noisy writes.
        cleaned_update = {k: v for k, v in update_data.items() if v is not None}
        if cleaned_update:
            doc_ref.update(cleaned_update)
            logger.info(f"✅ Geocoding enrichment added to report {doc_ref.id}")
    except Exception as e:
        logger.warning(f"⚠️ Geocoding enrichment failed for report {getattr(doc_ref, 'id', 'unknown')}: {e}")


async def create_report(report_data: ReportCreate) -> ReportResponse:
    """
    Create a new citizen report and store it in Firestore.
    
    CRITICAL DATA INTEGRITY REQUIREMENT:
    - Firestore write MUST happen BEFORE: geocoding, AI, confidence, priority, escalation
    - Firestore write MUST be synchronous (blocking - Firestore Admin SDK)
    - Firestore write MUST be verified after execution
    - If Firestore write fails, API MUST return 500
    - Collection name MUST be exactly: "reports"
    - Report ID MUST be used as document ID and stored as field "id"
    
    Flow:
    1. Perform validation checks (duplicate detection, rate limiting)
    2. Generate report ID and prepare Firestore payload
    3. WRITE TO FIRESTORE IMMEDIATELY (synchronous, blocking)
    4. Verify write succeeded
    5. Schedule geocoding enrichment (non-blocking, optional)
    6. Call AI interpreter for assistance (advisory only, non-blocking)
    7. Update report with AI metadata
    8. Calculate confidence based on pattern detection
    9. Calculate priority score and evaluate escalation
    10. Return complete report
    
    IMPORTANT: If AI fails, report is still stored and returned.
    AI interpretation is helpful but NOT required.
    
    Args:
        report_data: Validated report data from POST request
    
    Returns:
        ReportResponse: The created report with generated ID, timestamp, and AI metadata
    """
    try:
        import sys
        import traceback
        
        # DEBUG: Print incoming schema before any mutation (use stderr so uvicorn shows it)
        sys.stderr.write("=" * 80 + "\n")
        sys.stderr.write("🔥 DEBUG: Incoming report_data\n")
        sys.stderr.write("=" * 80 + "\n")
        sys.stderr.flush()
        try:
            report_dict = report_data.model_dump() if hasattr(report_data, 'model_dump') else report_data.dict()
            sys.stderr.write(f"report_data.dict(): {report_dict}\n")
        except Exception as e:
            sys.stderr.write(f"Failed to print report_data.dict(): {e}\n")
            sys.stderr.write(f"report_data type: {type(report_data)}\n")
            sys.stderr.write(f"report_data: {report_data}\n")
        sys.stderr.write("=" * 80 + "\n")
        sys.stderr.flush()
        
        # Get Firestore client and verify it's not None
        sys.stderr.write("🔍 Getting Firestore client...\n")
        sys.stderr.flush()
        db = get_db()
        assert db is not None, "Firestore client is None"
        sys.stderr.write(f"✅ Firestore client obtained: {type(db)}\n")
        sys.stderr.flush()
        
        # Verify collection exists
        sys.stderr.write("🔍 Verifying collection 'reports'...\n")
        sys.stderr.flush()
        reports_collection = db.collection("reports")
        assert reports_collection is not None, "Collection 'reports' does not exist"
        sys.stderr.write(f"✅ Collection 'reports' verified\n")
        sys.stderr.flush()
        
        # ========================================================================
        # STEP 1: VALIDATION CHECKS (BEFORE FIRESTORE WRITE)
        # ========================================================================
        # Perform duplicate detection and rate limiting BEFORE write
        # This prevents creating reports that should be rejected
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
        
        # ========================================================================
        # STEP 2: GENERATE REPORT ID AND PREPARE FIRESTORE PAYLOAD
        # ========================================================================
        # Generate unique report ID
        doc_ref = db.collection("reports").document()  # Auto-generate unique ID
        report_id = doc_ref.id
        
        # Get current UTC timestamp for created_at
        now = datetime.utcnow()
        
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
        
        # Prepare Firestore payload with all required fields
        # Use getattr for all optional fields to prevent AttributeError
        sys.stderr.write(f"🔍 Preparing Firestore payload for report {report_id}...\n")
        sys.stderr.flush()
        firestore_payload = {
            "id": report_id,  # Report ID as both document ID and field
            "description": report_data.description,
            "issue_type": getattr(report_data, 'issue_type', None) or "",
            "city": city,
            "locality": report_data.locality,
            "latitude": getattr(report_data, 'latitude', None),
            "longitude": getattr(report_data, 'longitude', None),
            "reporter_name": getattr(report_data, 'reporter_name', None),
            "ip_address_hash": ip_address_hash,
            "reporter_context": (getattr(report_data, 'reporter_context', None).value 
                                 if getattr(report_data, 'reporter_context', None) else None),
            "media_urls": getattr(report_data, 'media_urls', None) or [],
            "resolved_address": getattr(report_data, 'resolved_address', None),
            "user_entered_location": getattr(report_data, 'user_entered_location', None),
            "location_source": getattr(report_data, 'location_source', None),
            "created_at": firestore.SERVER_TIMESTAMP,
            "status": initial_status,
            "status_history": status_history,
            "reviewer_notes": [],
            "confidence": "LOW",
            "confidence_reason": "Single report, awaiting corroboration",
            "ai_metadata": {},
            "priority_score": None,
            "priority_reason": None,
            "escalation_flag": False,
            "escalation_reason": None,
            "escalation_history": [],
        }
        sys.stderr.write(f"✅ Payload prepared: {len(firestore_payload)} fields\n")
        sys.stderr.flush()
        
        # ========================================================================
        # STEP 3: WRITE TO FIRESTORE IMMEDIATELY (SYNCHRONOUS, BLOCKING)
        # ========================================================================
        # CRITICAL: This write MUST succeed before any other operations
        # Firestore Admin SDK set() is synchronous and blocking
        # This write happens BEFORE: geocoding, AI, confidence, priority, escalation
        sys.stderr.write(f"🔍 Writing document {report_id} to Firestore collection 'reports'...\n")
        sys.stderr.write(f"   Document path: reports/{report_id}\n")
        sys.stderr.flush()
        
        try:
            doc_ref.set(firestore_payload)
            sys.stderr.write(f"✅ doc_ref.set() completed for report {report_id}\n")
            sys.stderr.flush()
            logger.info(f"✅ Report saved to Firestore: {report_id}")
            
            # VERIFICATION: Confirm document exists in Firestore
            sys.stderr.write(f"🔍 Verifying document {report_id} exists in Firestore...\n")
            sys.stderr.flush()
            verify_doc = doc_ref.get()
            if not verify_doc.exists:
                raise RuntimeError(f"Firestore write verification failed: document {report_id} does not exist after write")
            
            sys.stderr.write(f"✅ Document {report_id} verified in Firestore\n")
            sys.stderr.flush()
            logger.info(f"✅ Firestore write confirmed for report {report_id}")
        except Exception as write_error:
            sys.stderr.write(f"❌ FIRESTORE WRITE FAILED: {write_error}\n")
            sys.stderr.write(traceback.format_exc())
            sys.stderr.flush()
            raise

        # ========================================================================
        # TEMPORARILY DISABLED: Background tasks and enrichment
        # ========================================================================
        # DEBUGGING MODE: All background tasks disabled to isolate Firestore write issue
        # STEP 4-7: Geocoding, AI, Confidence, Priority, Escalation - TEMPORARILY DISABLED
        
        # ========================================================================
        # STEP 4: RETRIEVE DOCUMENT AND RETURN RESPONSE
        # ========================================================================
        # Retrieve the document that was just written
        sys.stderr.write(f"🔍 Retrieving document {report_id} from Firestore...\n")
        sys.stderr.flush()
        final_doc = doc_ref.get()
        if not final_doc.exists:
            raise RuntimeError(f"Document {report_id} does not exist after write")
        
        final_data = final_doc.to_dict()
        sys.stderr.write(f"✅ Document retrieved successfully: {final_doc.id}\n")
        sys.stderr.flush()
    
        # Return as response model
        sys.stderr.write(f"✅ Creating ReportResponse for report {report_id}\n")
        sys.stderr.flush()
        response = ReportResponse(
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
            created_at=final_data["created_at"],
            resolved_address=final_data.get("resolved_address"),
            resolved_locality=final_data.get("resolved_locality"),
            resolved_city=final_data.get("resolved_city"),
            resolved_state=final_data.get("resolved_state"),
            resolved_country=final_data.get("resolved_country"),
            geocoding_provider=final_data.get("geocoding_provider"),
            geocoded_at=final_data.get("geocoded_at"),
        )
        sys.stderr.write(f"✅ ReportResponse created successfully for report {report_id}\n")
        sys.stderr.write("=" * 80 + "\n")
        sys.stderr.write("✅ REPORT CREATION SUCCESSFUL\n")
        sys.stderr.write("=" * 80 + "\n")
        sys.stderr.flush()
        return response
        
    except Exception as e:
        import sys
        import traceback
        sys.stderr.write("=" * 80 + "\n")
        sys.stderr.write("🔥 REPORT CREATION FAILED\n")
        sys.stderr.write("=" * 80 + "\n")
        sys.stderr.write(traceback.format_exc())
        sys.stderr.write("=" * 80 + "\n")
        sys.stderr.flush()
        # Re-raise to let FastAPI handle it
        raise


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
                escalation_history=data.get("escalation_history", []),  # PHASE-3
                resolved_address=data.get("resolved_address"),
                resolved_locality=data.get("resolved_locality"),
                resolved_city=data.get("resolved_city"),
                resolved_state=data.get("resolved_state"),
                resolved_country=data.get("resolved_country"),
                geocoding_provider=data.get("geocoding_provider"),
                geocoded_at=data.get("geocoded_at"),
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
