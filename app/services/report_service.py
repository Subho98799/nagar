"""
Report service - Business logic for citizen report handling.

CRITICAL GUARANTEE:
- Firestore write is SYNCHRONOUS
- Firestore write happens FIRST
- No async / enrichment during creation
"""

from datetime import datetime, timezone
from typing import List, Optional

from firebase_admin import firestore

from app.config.firebase import get_db
from app.models.report import ReportCreate, ReportResponse
from app.utils.geocoding import ensure_city_not_null, normalize_city_name
from app.services.status_workflow import ReportStatus, StatusWorkflowEngine


# ------------------------------------------------------------------
# CORE CREATE
# ------------------------------------------------------------------

def create_report_sync(report_data: ReportCreate) -> dict:
    db = get_db()
    if db is None:
        raise RuntimeError("Firestore DB not initialized")

    doc_ref = db.collection("reports").document()
    report_id = doc_ref.id

    # CRITICAL: Use canonical city normalization to ensure consistent city values
    # This ensures aggregation can match reports by city using exact comparison
    city = ensure_city_not_null(
        city=report_data.city,
        locality=report_data.locality,
        latitude=report_data.latitude,
        longitude=report_data.longitude,
        resolved_city=getattr(report_data, 'resolved_city', None),
    )

    workflow = StatusWorkflowEngine()
    initial_status = ReportStatus.UNDER_REVIEW.value
    created_at = datetime.now(timezone.utc)

    # Create status_history entry with datetime (not SERVER_TIMESTAMP) for JSON serialization
    # Since we're creating synchronously, we can use the exact creation time
    status_history_entry = {
        "from": "",
        "to": initial_status,
        "changed_by": "system",
        "timestamp": created_at,
        "note": "Report created"
    }

    payload = {
        "id": report_id,
        "description": report_data.description,
        "issue_type": report_data.issue_type,
        "city": city,
        "locality": report_data.locality,
        "latitude": report_data.latitude,
        "longitude": report_data.longitude,
        "reporter_name": report_data.reporter_name,
        "media_urls": report_data.media_urls or [],
        "resolved_address": report_data.resolved_address,
        "user_entered_location": report_data.user_entered_location,
        "location_source": report_data.location_source,
        "status": initial_status,
        "status_history": [status_history_entry],
        "confidence": "LOW",
        "confidence_reason": "Single report, awaiting corroboration",
        "ai_metadata": {},
        "priority_score": None,
        "priority_reason": None,
        "escalation_flag": False,
        "escalation_reason": None,
        "escalation_history": [],
        "created_at": created_at,
    }

    doc_ref.set(payload)

    if not doc_ref.get().exists:
        raise RuntimeError("Firestore write verification failed")

    return payload


async def create_report(report_data: ReportCreate) -> ReportResponse:
    data = create_report_sync(report_data)

    # Phase 5B: Attempt issue aggregation (non-blocking, fails gracefully)
    # This will:
    # 1. Query recent reports (last 24h)
    # 2. Find clusters matching criteria
    # 3. Create new issues or update existing ones
    # 4. Automatically recalculate confidence (handled in aggregation service)
    # 
    # CRITICAL: Aggregation MUST run after report creation to ensure reports
    # are grouped into issues. Logging proves execution.
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        from app.services.issue_aggregation_service import attempt_issue_aggregation
        logger.info(f"[AGGREGATION] Triggering aggregation for report {data['id']} (city: {data.get('city', 'N/A')})")
        # Trigger aggregation (fire-and-forget, non-blocking)
        # Confidence recalculation is handled inside create_or_update_issue_from_cluster
        issue_ids = attempt_issue_aggregation(report_id=data["id"])
        if issue_ids:
            logger.info(f"[AGGREGATION] Successfully created/updated {len(issue_ids)} issue(s): {issue_ids}")
        else:
            logger.info(f"[AGGREGATION] No issues created/updated for report {data['id']} (cluster criteria not met)")
    except Exception as e:
        # Fail gracefully - report creation should never fail due to aggregation
        # But log the error so we know aggregation was attempted
        logger.error(f"[AGGREGATION] Failed to run aggregation for report {data['id']}: {e}", exc_info=True)

    return ReportResponse(
        id=data["id"],
        description=data["description"],
        issue_type=data.get("issue_type"),
        city=data["city"],
        locality=data["locality"],
        latitude=data["latitude"],
        longitude=data["longitude"],
        reporter_name=data.get("reporter_name"),
        media_urls=data.get("media_urls", []),
        confidence=data["confidence"],
        confidence_reason=data["confidence_reason"],
        status=data["status"],
        ai_metadata=data.get("ai_metadata"),
        status_history=data.get("status_history", []),
        created_at=data["created_at"],
        resolved_address=data.get("resolved_address"),
        resolved_locality=None,
        resolved_city=None,
        resolved_state=None,
        resolved_country=None,
        geocoding_provider=None,
        geocoded_at=None,
    )


# ------------------------------------------------------------------
# READ
# ------------------------------------------------------------------

async def get_all_reports() -> List[ReportResponse]:
    db = get_db()
    docs = (
        db.collection("reports")
        .order_by("created_at", direction=firestore.Query.DESCENDING)
        .stream()
    )

    results = []
    for doc in docs:
        d = doc.to_dict()
        results.append(
            ReportResponse(
                id=doc.id,
                description=d["description"],
                issue_type=d.get("issue_type"),
                city=d["city"],
                locality=d["locality"],
                latitude=d["latitude"],
                longitude=d["longitude"],
                reporter_name=d.get("reporter_name"),
                media_urls=d.get("media_urls", []),
                confidence=d["confidence"],
                confidence_reason=d["confidence_reason"],
                status=d["status"],
                ai_metadata=d.get("ai_metadata"),
                status_history=d.get("status_history", []),
                created_at=d["created_at"],
                resolved_address=d.get("resolved_address"),
                resolved_locality=d.get("resolved_locality"),
                resolved_city=d.get("resolved_city"),
                resolved_state=d.get("resolved_state"),
                resolved_country=d.get("resolved_country"),
                geocoding_provider=d.get("geocoding_provider"),
                geocoded_at=d.get("geocoded_at"),
            )
        )
    return results


# ------------------------------------------------------------------
# ADMIN REQUIRED FUNCTIONS (DO NOT REMOVE)
# ------------------------------------------------------------------

async def get_report_by_id(report_id: str) -> Optional[dict]:
    db = get_db()
    doc = db.collection("reports").document(report_id).get()
    if not doc.exists:
        return None
    data = doc.to_dict()
    data["id"] = doc.id
    return data


async def upgrade_report_confidence(
    report_id: str,
    confidence: str,
    admin_note: Optional[str] = None,
) -> dict:
    db = get_db()
    ref = db.collection("reports").document(report_id)

    ref.update({
        "confidence": confidence,
        "confidence_reason": "Upgraded by admin review",
        "reviewed_at": firestore.SERVER_TIMESTAMP,
        **({"admin_note": admin_note} if admin_note else {}),
    })

    doc = ref.get()
    data = doc.to_dict()
    data["id"] = doc.id
    return data


async def update_report_status(
    report_id: str,
    status: str,
    admin_note: Optional[str] = None,
) -> dict:
    db = get_db()
    ref = db.collection("reports").document(report_id)

    ref.update({
        "status": status,
        "reviewed_at": firestore.SERVER_TIMESTAMP,
        **({"admin_note": admin_note} if admin_note else {}),
    })

    doc = ref.get()
    data = doc.to_dict()
    data["id"] = doc.id
    return data
