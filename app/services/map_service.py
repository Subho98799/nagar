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
import math


def _parse_timestamp(value) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except Exception:
            try:
                # Strip Z if present
                if value.endswith('Z'):
                    return datetime.fromisoformat(value[:-1])
            except Exception:
                return None
    # Try common firestore Timestamp interface
    try:
        if hasattr(value, 'ToDatetime'):
            return value.ToDatetime()
        if hasattr(value, 'to_datetime'):
            return value.to_datetime()
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
    
    PRODUCTION-GRADE: Handles city name variations and special cases.
    
    Phase 5B: Dashboard reads ONLY from issues collection (not reports).
    
    Query Logic:
    - If city == "Demo City": Return ALL ACTIVE issues (demo mode)
    - If city is missing/empty: Return ALL ACTIVE issues
    - Otherwise: Query by city OR city_variants array contains city
    
    Args:
        city: City name to filter by (may be "Demo City" for demo mode)
    
    Returns:
        List of issue dictionaries matching the city filter
    """
    db = get_db()
    issues_ref = db.collection("issues")
    
    # SPECIAL CASE: Demo City returns ALL active issues (intentional demo mode behavior)
    if not city or city.strip() == "" or city.strip().lower() == "demo city":
        # Return all active issues for demo mode
        try:
            docs = list(issues_ref.where("status", "==", "ACTIVE").stream())
        except Exception:
            # Fallback: iterate all and filter by status
            docs = list(issues_ref.stream())
    else:
        # Normalize city name for querying
        normalized_city = normalize_city_name(city.strip())
        
        # Query by city OR city_variants array contains city
        # Firestore doesn't support OR queries directly, so we need to:
        # 1. Try query by city field
        # 2. Fallback to iterate all and filter by city or city_variants
        try:
            # Try query by exact city match first
            docs = list(issues_ref.where("city", "==", normalized_city).stream())
        except Exception:
            # Fallback: iterate all and filter
            docs = list(issues_ref.stream())

    issues: List[Dict[str, Any]] = []
    for doc in docs:
        data = doc.to_dict()
        
        # Skip non-active issues (unless demo mode)
        status = data.get("status", "")
        if status != "ACTIVE":
            continue
        
        # Filter by city if not demo mode
        if city and city.strip() and city.strip().lower() != "demo city":
            normalized_city = normalize_city_name(city.strip())
            issue_city = normalize_city_name(data.get("city", ""))
            city_variants = data.get("city_variants", [])
            
            # Match if: city matches OR city is in variants array
            city_matches = (issue_city == normalized_city)
            variant_matches = (normalized_city in [normalize_city_name(v) for v in city_variants])
            
            if not (city_matches or variant_matches):
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
