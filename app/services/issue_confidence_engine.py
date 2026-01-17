"""
Issue Confidence Evolution Engine - Phase 5B

Automatically evolves ISSUE confidence over time as more reports arrive.

IMPORTANT:
- Confidence applies to ISSUES, not REPORTS
- Never depends solely on AI
- Uses Firestore as source of truth
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, List, Set
from firebase_admin import firestore

from app.config.firebase import get_db

# Import minimum reports constant
MIN_REPORTS_FOR_ISSUE = 5

# Confidence scoring rules
SCORE_INCREMENT_ADDITIONAL_REPORTS = 0.2  # 3+ additional reports
SCORE_INCREMENT_UNIQUE_REPORTERS = 0.15   # Different reporters (unique IP hash)
SCORE_INCREMENT_TIME_PERSISTENCE = 0.15   # Time persistence > 2 hours
SCORE_INCREMENT_MEDIA_PRESENT = 0.10     # Any media present

INITIAL_CONFIDENCE_SCORE = 0.2
MAX_CONFIDENCE_SCORE = 1.0

# Confidence mapping
CONFIDENCE_LOW_THRESHOLD = 0.4
CONFIDENCE_MEDIUM_THRESHOLD = 0.7


def _parse_timestamp(value) -> Optional[datetime]:
    """Parse various timestamp formats to timezone-aware datetime (UTC)."""
    if value is None:
        return None
    if isinstance(value, datetime):
        # Ensure timezone-aware (UTC)
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
    if isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except Exception:
            try:
                dt = datetime.fromisoformat(value)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except Exception:
                return None
    try:
        if hasattr(value, 'timestamp'):
            dt = datetime.fromtimestamp(value.timestamp(), tz=timezone.utc)
            return dt
        if hasattr(value, 'ToDatetime'):
            dt = value.ToDatetime()
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        if hasattr(value, 'to_datetime'):
            dt = value.to_datetime()
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
    except Exception:
        pass
    return None


def _score_to_confidence_label(score: float) -> str:
    """Map confidence score to label."""
    if score < CONFIDENCE_LOW_THRESHOLD:
        return "LOW"
    elif score < CONFIDENCE_MEDIUM_THRESHOLD:
        return "MEDIUM"
    else:
        return "HIGH"


def _calculate_confidence_score(issue_data: Dict[str, Any], reports: List[Dict[str, Any]]) -> tuple[float, str]:
    """
    Calculate confidence score and reason based on issue and linked reports.
    
    Returns:
        (score, reason) tuple
    """
    base_score = INITIAL_CONFIDENCE_SCORE
    reasons = []
    
    # Get initial report count (when issue was created)
    initial_report_count = issue_data.get("report_count", MIN_REPORTS_FOR_ISSUE)
    current_report_count = len(reports)
    
    # Check: 3+ additional reports beyond initial
    additional_reports = current_report_count - initial_report_count
    if additional_reports >= 3:
        base_score += SCORE_INCREMENT_ADDITIONAL_REPORTS
        reasons.append(f"{additional_reports} additional reports received")
    
    # Check: Unique reporters (by IP hash)
    unique_ips: Set[str] = set()
    for report in reports:
        ip_hash = report.get("ip_address_hash") or report.get("ip_address")
        if ip_hash:
            unique_ips.add(str(ip_hash))
    
    if len(unique_ips) > 1:
        base_score += SCORE_INCREMENT_UNIQUE_REPORTERS
        reasons.append(f"{len(unique_ips)} unique reporters")
    
    # Check: Time persistence > 2 hours
    created_at = _parse_timestamp(issue_data.get("created_at"))
    if created_at:
        time_persisted = datetime.now(timezone.utc) - created_at
        if time_persisted > timedelta(hours=2):
            base_score += SCORE_INCREMENT_TIME_PERSISTENCE
            hours = int(time_persisted.total_seconds() / 3600)
            reasons.append(f"Persisted for {hours} hours")
    
    # Check: Any media present
    has_media = any(
        report.get("media_urls") and len(report.get("media_urls", [])) > 0
        for report in reports
    )
    if has_media:
        base_score += SCORE_INCREMENT_MEDIA_PRESENT
        reasons.append("Media evidence present")
    
    # Cap at maximum
    final_score = min(base_score, MAX_CONFIDENCE_SCORE)
    
    # Generate reason string
    if reasons:
        reason = "; ".join(reasons)
    else:
        reason = f"Issue created from {current_report_count} reports"
    
    return (final_score, reason)


def recalculate_issue_confidence(issue_id: str) -> Optional[Dict[str, Any]]:
    """
    Recalculate confidence for an issue based on current linked reports.
    
    This is deterministic and idempotent.
    
    Args:
        issue_id: The issue document ID
    
    Returns:
        Updated issue data dict, or None if issue not found
    """
    db = get_db()
    if db is None:
        return None
    
    try:
        # Get issue document
        issue_ref = db.collection("issues").document(issue_id)
        issue_doc = issue_ref.get()
        
        if not issue_doc.exists:
            return None
        
        issue_data = issue_doc.to_dict()
        if issue_data is None:
            return None
        
        # Get all linked reports
        report_ids = issue_data.get("report_ids", [])
        if not report_ids:
            return issue_data
        
        reports_ref = db.collection("reports")
        reports = []
        
        for report_id in report_ids:
            try:
                report_doc = reports_ref.document(report_id).get()
                if report_doc.exists:
                    report_data = report_doc.to_dict()
                    if report_data:
                        report_data["id"] = report_id
                        reports.append(report_data)
            except Exception:
                # Skip missing reports
                continue
        
        # Get previous confidence
        previous_score = issue_data.get("confidence_score", INITIAL_CONFIDENCE_SCORE)
        previous_confidence = issue_data.get("confidence", "LOW")
        
        # Calculate new confidence
        new_score, reason = _calculate_confidence_score(issue_data, reports)
        new_confidence = _score_to_confidence_label(new_score)
        
        # Get existing confidence_timeline
        confidence_timeline = issue_data.get("confidence_timeline", [])
        if not isinstance(confidence_timeline, list):
            confidence_timeline = []
        
        # Track if confidence changed
        confidence_changed = new_score != previous_score or new_confidence != previous_confidence
        
        # Add new entry to timeline (only if changed)
        if confidence_changed:
            timeline_entry = {
                "timestamp": datetime.now(timezone.utc),
                "previous_confidence": previous_confidence,
                "previous_confidence_score": previous_score,
                "new_confidence": new_confidence,
                "confidence_score": new_score,
                "reason": reason
            }
            confidence_timeline.append(timeline_entry)
        
        # Update issue document
        update_data = {
            "confidence": new_confidence,
            "confidence_score": new_score,
            "confidence_reason": reason,
            "confidence_timeline": confidence_timeline,
            "updated_at": datetime.now(timezone.utc),
            "report_count": len(reports),  # Update count in case reports were deleted
        }
        
        issue_ref.update(update_data)
        
        # AI enrichment: Trigger on confidence change (fire-and-forget, non-blocking)
        if confidence_changed:
            try:
                # Get updated issue data and linked reports
                updated_issue_doc = issue_ref.get()
                if updated_issue_doc.exists:
                    updated_issue_data = updated_issue_doc.to_dict()
                    if updated_issue_data:
                        # Fetch all linked reports
                        linked_reports = []
                        for report_id in report_ids:
                            try:
                                report_doc = reports_ref.document(report_id).get()
                                if report_doc.exists:
                                    report_data = report_doc.to_dict()
                                    if report_data:
                                        linked_reports.append(report_data)
                            except Exception:
                                continue
                        
                        # Enrich issue with AI (fail-safe, non-blocking)
                        # CRITICAL: AI enrichment NEVER affects control flow, confidence, status, or escalation
                        from app.services.ai_enrichment.registry import enrich_issue
                        ai_metadata = enrich_issue(updated_issue_data, linked_reports)
                        if ai_metadata:
                            # Store in ai_metadata, don't overwrite if already present
                            existing_ai_metadata = updated_issue_data.get("ai_metadata", {})
                            if not existing_ai_metadata:
                                issue_ref.update({"ai_metadata": ai_metadata})
            except Exception:
                # Fail silently - AI enrichment should never block confidence updates
                pass
        
        # Return updated data
        issue_data.update(update_data)
        return issue_data
    
    except Exception as e:
        print(f"Error recalculating confidence for issue {issue_id}: {e}")
        return None


def recalculate_all_issues_confidence() -> Dict[str, Any]:
    """
    Recalculate confidence for all issues in the system.
    
    Returns:
        Dict with summary of results
    """
    db = get_db()
    if db is None:
        return {"success": False, "error": "Database not initialized"}
    
    try:
        issues_ref = db.collection("issues")
        docs = issues_ref.stream()
        
        updated = 0
        failed = 0
        errors = []
        
        for doc in docs:
            issue_id = doc.id
            result = recalculate_issue_confidence(issue_id)
            if result:
                updated += 1
            else:
                failed += 1
                errors.append(issue_id)
        
        return {
            "success": True,
            "updated": updated,
            "failed": failed,
            "errors": errors
        }
    
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
