"""
Report service - Business logic for citizen report handling.

CRITICAL GUARANTEE:
- Firestore write is SYNCHRONOUS
- Firestore write happens FIRST
- No async / background / enrichment during creation
"""

from datetime import datetime
from typing import List

from firebase_admin import firestore

from app.config.firebase import get_db
from app.models.report import ReportCreate, ReportResponse
from app.utils.geocoding import ensure_city_not_null
from app.services.status_workflow import ReportStatus, StatusWorkflowEngine


# ------------------------------------------------------------------
# 🔥 CORE FIX: SYNCHRONOUS FIRESTORE WRITE
# ------------------------------------------------------------------

def create_report_sync(report_data: ReportCreate) -> dict:
    """
    Synchronous Firestore write.
    This function MUST succeed or throw.
    """

    db = get_db()
    if db is None:
        raise RuntimeError("Firestore DB not initialized")

    reports_ref = db.collection("reports")
    doc_ref = reports_ref.document()
    report_id = doc_ref.id

    city = ensure_city_not_null(
        city=report_data.city,
        locality=report_data.locality,
        latitude=report_data.latitude,
        longitude=report_data.longitude,
    )

    workflow = StatusWorkflowEngine()
    initial_status = ReportStatus.UNDER_REVIEW.value

    firestore_payload = {
        "id": report_id,
        "description": report_data.description,
        "issue_type": report_data.issue_type or "",
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
        "status_history": [
            workflow.create_status_history_entry(
                from_status="",
                to_status=initial_status,
                changed_by="system",
                note="Report created",
            )
        ],
        "confidence": "LOW",
        "confidence_reason": "Single report, awaiting corroboration",
        "ai_metadata": {},
        "priority_score": None,
        "priority_reason": None,
        "escalation_flag": False,
        "escalation_reason": None,
        "escalation_history": [],
        "created_at": firestore.SERVER_TIMESTAMP,
    }

    # 🔥 SINGLE SOURCE OF TRUTH WRITE
    doc_ref.set(firestore_payload)

    # 🔥 VERIFY WRITE
    snap = doc_ref.get()
    if not snap.exists:
        raise RuntimeError("Firestore write verification failed")

    return firestore_payload


# ------------------------------------------------------------------
# ASYNC WRAPPER (THIN, SAFE)
# ------------------------------------------------------------------

async def create_report(report_data: ReportCreate) -> ReportResponse:
    """
    Async wrapper required by FastAPI.
    Does NOT perform async Firestore operations.
    """

    data = create_report_sync(report_data)

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

        # 🔥 FIX: NEVER return Firestore timestamp
        created_at=datetime.utcnow(),

        resolved_address=data.get("resolved_address"),
        resolved_locality=None,
        resolved_city=None,
        resolved_state=None,
        resolved_country=None,
        geocoding_provider=None,
        geocoded_at=None,
    )


# ------------------------------------------------------------------
# READ OPERATIONS (UNCHANGED)
# ------------------------------------------------------------------

async def get_all_reports() -> List[ReportResponse]:
    db = get_db()
    docs = (
        db.collection("reports")
        .order_by("created_at", direction=firestore.Query.DESCENDING)
        .stream()
    )

    reports = []
    for doc in docs:
        data = doc.to_dict()
        reports.append(
            ReportResponse(
                id=doc.id,
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
                resolved_locality=data.get("resolved_locality"),
                resolved_city=data.get("resolved_city"),
                resolved_state=data.get("resolved_state"),
                resolved_country=data.get("resolved_country"),
                geocoding_provider=data.get("geocoding_provider"),
                geocoded_at=data.get("geocoded_at"),
            )
        )

    return reports
# =====================================================================
# ADMIN / REVIEWER READ & MUTATION HELPERS
# (Required by app/routes/admin.py)
# =====================================================================

async def get_report_by_id(report_id: str) -> dict | None:
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
    admin_note: str | None = None,
) -> dict:
    db = get_db()
    doc_ref = db.collection("reports").document(report_id)

    update_data = {
        "confidence": confidence,
        "confidence_reason": "Upgraded by admin review",
        "reviewed_at": firestore.SERVER_TIMESTAMP,
    }

    if admin_note:
        update_data["admin_note"] = admin_note

    doc_ref.update(update_data)

    doc = doc_ref.get()
    if not doc.exists:
        raise RuntimeError("Report not found after confidence upgrade")

    data = doc.to_dict()
    data["id"] = doc.id
    return data


async def update_report_status(
    report_id: str,
    status: str,
    admin_note: str | None = None,
) -> dict:
    db = get_db()
    doc_ref = db.collection("reports").document(report_id)

    update_data = {
        "status": status,
        "reviewed_at": firestore.SERVER_TIMESTAMP,
    }

    if admin_note:
        update_data["admin_note"] = admin_note

    doc_ref.update(update_data)

    doc = doc_ref.get()
    if not doc.exists:
        raise RuntimeError("Report not found after status update")

    data = doc.to_dict()
    data["id"] = doc.id
    return data
