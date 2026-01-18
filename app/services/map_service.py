"""
Map service - aggregate reports into map issues for frontend

Implements deterministic clustering based on:
- same issue_type
- within 500 meters
- within 30 minutes

Returns a flat list of issue objects matching the exact schema required by frontend.
"""

from typing import List, Dict, Any, Optional
from app.config.firebase import get_db
from datetime import datetime, timedelta
from app.utils.geocoding import normalize_city_name
from app.utils.firestore_helpers import where_filter
import math


def _parse_timestamp(value) -> Optional[datetime]:
    """
    Parse various timestamp formats to timezone-aware datetime (UTC).
    
    CRITICAL: All datetimes must be timezone-aware to prevent comparison bugs.
    """
    from datetime import timezone
    
    if value is None:
        return None
    if isinstance(value, datetime):
        # Ensure timezone-aware (UTC)
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    if isinstance(value, str):
        try:
            # Handle ISO format with Z
            dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except Exception:
            try:
                # Try without Z
                dt = datetime.fromisoformat(value)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.astimezone(timezone.utc)
            except Exception:
                return None
    # Try common firestore Timestamp interface
    try:
        if hasattr(value, 'timestamp'):
            return datetime.fromtimestamp(value.timestamp(), tz=timezone.utc)
        if hasattr(value, 'ToDatetime'):
            dt = value.ToDatetime()
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        if hasattr(value, 'to_datetime'):
            dt = value.to_datetime()
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
    except Exception:
        pass
    return None


def _haversine_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371000
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def _severity_from_confidence(confidence: str) -> str:
    if confidence == "HIGH":
        return "High"
    if confidence == "MEDIUM":
        return "Medium"
    return "Low"


def _choose_cluster_confidence(confidences: List[str]) -> str:
    # Choose highest: HIGH > MEDIUM > LOW
    if any(c == "HIGH" for c in confidences):
        return "HIGH"
    if any(c == "MEDIUM" for c in confidences):
        return "MEDIUM"
    return "LOW"


def get_city_issues(city: str) -> List[Dict[str, Any]]:
    """
    Get all issues for a given city.
    
    Phase 5B: Dashboard reads ONLY from issues collection (not reports).
    City name is normalized to match the normalized city values stored in issues.
    
    Args:
        city: City name (normalized, lowercase) or empty string for all issues
    """
    db = get_db()
    if db is None:
        return []

    # Fetch pre-aggregated issues from the issues collection (Firestore already has clustering done)
    issues_ref = db.collection("issues")
    docs = []
    
    try:
        # If city is provided and not empty, filter by city
        # CRITICAL: City must be normalized (lowercase) to match stored values
        if city and city != "UNKNOWN":
            query = where_filter(issues_ref, "city", "==", city).limit(100)
            docs = list(query.stream())
        else:
            # No city filter - return all issues (with limit for performance)
            docs = list(issues_ref.limit(100).stream())
    except Exception as e:
        # Fallback: iterate all and filter by normalized city (with limit)
        try:
            docs = list(issues_ref.limit(100).stream())
            # If city filter was requested, filter in memory
            if city and city != "UNKNOWN":
                from app.utils.geocoding import normalize_city_name
                docs = [
                    doc for doc in docs
                    if normalize_city_name(doc.to_dict().get("city", "")) == city
                ]
        except Exception:
            # Return empty list if all queries fail
            return []

    issues: List[Dict[str, Any]] = []
    for doc in docs:
        data = doc.to_dict()
        
        # Filter by normalized city if city filter was provided
        if city and city != "UNKNOWN":
            issue_city = normalize_city_name(data.get("city", ""))
            if issue_city != city:
                continue
        
        # Ensure required fields exist
        created_at = _parse_timestamp(data.get("created_at"))
        updated_at = _parse_timestamp(data.get("updated_at"))
        
        lat = data.get("latitude")
        lon = data.get("longitude")
        if lat is None or lon is None:
            continue
        
        # Normalize severity: map uppercase variants to title case
        severity_raw = data.get("severity", "Low")
        if severity_raw.upper() == "HIGH":
            severity_mapped = "High"
        elif severity_raw.upper() == "MEDIUM":
            severity_mapped = "Medium"
        else:
            severity_mapped = "Low"
        
        # Map Firestore issue doc to frontend schema
        # Normalize status: ACTIVE -> CONFIRMED, RESOLVED -> RESOLVED, etc.
        status_raw = data.get("status", "UNDER_OBSERVATION")
        status_mapped = "CONFIRMED" if status_raw == "ACTIVE" else status_raw
        
        # Normalize confidence: uppercase to match frontend expectations
        confidence_raw = data.get("confidence", "LOW")
        confidence_mapped = confidence_raw if confidence_raw.isupper() else confidence_raw.upper()
        
        # Map timeline if present
        timeline = []
        raw_timeline = data.get("timeline", [])
        if isinstance(raw_timeline, list):
            for ev in raw_timeline:
                timeline.append({
                    "id": ev.get("id") or f"{doc.id}-t",
                    "timestamp": ev.get("timestamp") or "",
                    "time": ev.get("time") or ev.get("timestamp") or "",
                    "confidence": ev.get("confidence", "Low"),
                    "description": ev.get("description", ""),
                })
        
        issue_obj: Dict[str, Any] = {
            "id": doc.id,
            "title": data.get("title", ""),
            "description": data.get("description", ""),
            "issue_type": data.get("issue_type", ""),
            "severity": severity_mapped,
            "confidence": confidence_mapped,
            "status": status_mapped,
            "latitude": float(lat),
            "longitude": float(lon),
            "locality": data.get("locality", ""),
            "city": data.get("city", city),
            "report_count": int(data.get("report_count", 1)),
            "created_at": created_at.isoformat() if created_at else "",
            "updated_at": updated_at.isoformat() if updated_at else "",
            "timeline": timeline,
            "operatorNotes": data.get("operatorNotes") or None,
            # Phase-4: Pass through resolved address fields if available (read-only display)
            "resolved_address": data.get("resolved_address") or None,
            "resolved_locality": data.get("resolved_locality") or None,
            "resolved_city": data.get("resolved_city") or None,
        }
        
        issues.append(issue_obj)

    # Sort: HIGH first, then MEDIUM, then LOW
    order_map = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    issues.sort(key=lambda x: (order_map.get(x.get("confidence", "LOW"), 2), x.get("created_at")),)

    return issues
