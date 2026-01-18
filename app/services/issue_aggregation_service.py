"""
Issue Aggregation Service - Phase 5A

Converts multiple related reports into a single ISSUE document.

KEY PRINCIPLE:
- Reports are raw signals
- Issues are summarized, human-governed intelligence
- Issue MUST NOT be created from a single report

ISSUE CREATION RULE:
Create a new issue ONLY when:
- ≥ 5 reports
- Same issue_type
- Within ~500 meters radius
- Same city
- Time window ≤ 2 hours
- Status of reports: UNDER_REVIEW or VERIFIED
"""

import math
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional, Set
from firebase_admin import firestore

from app.config.firebase import get_db
from app.utils.geocoding import normalize_city_name
from app.utils.firestore_helpers import where_filter


# Constants
MIN_REPORTS_FOR_ISSUE = 5
PROXIMITY_METERS = 500
TIME_WINDOW_HOURS = 2
VALID_STATUSES = {"UNDER_REVIEW", "VERIFIED"}


def _haversine_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two points in meters using Haversine formula."""
    R = 6371000  # Earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


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
    # Try Firestore Timestamp interface
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


def _calculate_centroid(reports: List[Dict[str, Any]]) -> tuple[float, float]:
    """Calculate centroid (average) of report coordinates."""
    if not reports:
        return (0.0, 0.0)
    
    total_lat = sum(r.get("latitude") or 0.0 for r in reports)
    total_lon = sum(r.get("longitude") or 0.0 for r in reports)
    count = len(reports)
    
    return (total_lat / count, total_lon / count)


def _get_dominant_locality(reports: List[Dict[str, Any]]) -> str:
    """Get the most common locality from reports."""
    localities = {}
    for report in reports:
        locality = report.get("locality", "").strip()
        if locality:
            localities[locality] = localities.get(locality, 0) + 1
    
    if not localities:
        return ""
    
    return max(localities.items(), key=lambda x: x[1])[0]


def _cluster_reports(
    reports: List[Dict[str, Any]],
    reference_lat: float,
    reference_lon: float,
    reference_time: datetime
) -> List[Dict[str, Any]]:
    """Group reports that are within proximity and time window."""
    clustered = []
    time_window = timedelta(hours=TIME_WINDOW_HOURS)
    
    for report in reports:
        lat = report.get("latitude")
        lon = report.get("longitude")
        created_at = _parse_timestamp(report.get("created_at"))
        
        if lat is None or lon is None or created_at is None:
            continue
        
        # Check proximity
        distance = _haversine_meters(reference_lat, reference_lon, lat, lon)
        if distance > PROXIMITY_METERS:
            continue
        
        # Check time window
        # BUG FIX: Ensure both datetimes are timezone-aware (UTC) before comparison
        # _parse_timestamp already returns UTC-aware datetime, but ensure reference_time is also UTC-aware
        if reference_time.tzinfo is None:
            reference_time = reference_time.replace(tzinfo=timezone.utc)
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        
        time_diff = abs((created_at - reference_time).total_seconds())
        if time_diff > time_window.total_seconds():
            continue
        
        clustered.append(report)
    
    return clustered


def _find_eligible_clusters(reports: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
    """Find clusters of reports that meet issue creation criteria."""
    clusters = []
    processed_report_ids: Set[str] = set()
    
    # Sort by created_at to process chronologically
    sorted_reports = sorted(
        reports,
        key=lambda r: _parse_timestamp(r.get("created_at")) or datetime.min
    )
    
    for report in sorted_reports:
        report_id = report.get("id")
        if not report_id or report_id in processed_report_ids:
            continue
        
        # Skip if already linked to an issue
        if report.get("issue_id"):
            continue
        
        # Check status
        status = report.get("status", "")
        if status not in VALID_STATUSES:
            continue
        
        # Get report coordinates and time
        lat = report.get("latitude")
        lon = report.get("longitude")
        created_at = _parse_timestamp(report.get("created_at"))
        
        if lat is None or lon is None or created_at is None:
            continue
        
        # Find all reports in this cluster
        cluster = _cluster_reports(sorted_reports, lat, lon, created_at)
        
        # Filter cluster to same issue_type and city
        # CRITICAL: Use normalized city for comparison to handle inconsistent city values
        # (e.g., "India", "Ranchi", "Demo City" should all be normalized consistently)
        issue_type = report.get("issue_type")
        city = normalize_city_name(report.get("city"))
        
        cluster = [
            r for r in cluster
            if r.get("issue_type") == issue_type
            and normalize_city_name(r.get("city")) == city  # Use normalized city for exact match
            and r.get("status", "") in VALID_STATUSES
            and not r.get("issue_id")  # Not already linked
        ]
        
        # Check if cluster meets minimum threshold
        if len(cluster) >= MIN_REPORTS_FOR_ISSUE:
            # Mark all reports in cluster as processed
            for r in cluster:
                r_id = r.get("id")
                if r_id:
                    processed_report_ids.add(r_id)
            
            clusters.append(cluster)
    
    return clusters


def _find_existing_issue(
    db,
    issue_type: str,
    city: str,
    centroid_lat: float,
    centroid_lon: float
) -> Optional[str]:
    """
    Find existing issue that matches the cluster criteria.
    
    CRITICAL: city parameter should already be normalized via normalize_city_name()
    to ensure exact matching with stored issue city values.
    
    Returns:
        issue_id if found, None otherwise
    """
    try:
        issues_ref = db.collection("issues")
        
        # CRITICAL: Query issues by normalized city and issue_type
        # Both reports and issues must use the same normalized city value
        normalized_city = normalize_city_name(city)
        query = where_filter(issues_ref, "city", "==", normalized_city)
        query = where_filter(query, "issue_type", "==", issue_type)
        docs = query.stream()
        
        for doc in docs:
            data = doc.to_dict()
            if data is None:
                continue
            
            # Check if issue is still ACTIVE
            if data.get("status") != "ACTIVE":
                continue
            
            # Check proximity (within 500m)
            issue_lat = data.get("latitude")
            issue_lon = data.get("longitude")
            
            if issue_lat is None or issue_lon is None:
                continue
            
            distance = _haversine_meters(centroid_lat, centroid_lon, issue_lat, issue_lon)
            if distance <= PROXIMITY_METERS:
                return doc.id
        
        return None
    except Exception:
        return None


def create_or_update_issue_from_cluster(cluster: List[Dict[str, Any]]) -> Optional[str]:
    """
    Create a new issue or update existing issue from a cluster of reports.
    
    Returns:
        issue_id if successful, None otherwise
    """
    if len(cluster) < MIN_REPORTS_FOR_ISSUE:
        return None
    
    db = get_db()
    if db is None:
        return None
    
    # Extract common fields
    # CRITICAL: Normalize city to ensure consistent storage in issues
    # This ensures both reports and issues use the SAME normalized city value
    issue_type = cluster[0].get("issue_type", "")
    city = normalize_city_name(cluster[0].get("city", ""))
    
    if not issue_type or not city or city == "UNKNOWN":
        return None
    
    # Calculate centroid
    centroid_lat, centroid_lon = _calculate_centroid(cluster)
    
    # CRITICAL FIX: Ensure coordinates are valid numbers before proceeding
    # Do NOT create/update issue if coordinates are invalid (0.0, 0.0 or NaN)
    if (centroid_lat is None or centroid_lon is None or 
        not isinstance(centroid_lat, (int, float)) or not isinstance(centroid_lon, (int, float)) or
        math.isnan(centroid_lat) or math.isnan(centroid_lon) or
        (centroid_lat == 0.0 and centroid_lon == 0.0)):
        return None
    
    # Get dominant locality
    locality = _get_dominant_locality(cluster)
    
    # Get report IDs
    report_ids = [r.get("id") for r in cluster if r.get("id")]
    
    # Get earliest created_at
    created_times = [
        _parse_timestamp(r.get("created_at"))
        for r in cluster
        if _parse_timestamp(r.get("created_at"))
    ]
    earliest_time = min(created_times) if created_times else datetime.now(timezone.utc)
    
    # Check if issue already exists
    existing_issue_id = _find_existing_issue(db, issue_type, city, centroid_lat, centroid_lon)
    
    if existing_issue_id:
        # Update existing issue
        try:
            issue_ref = db.collection("issues").document(existing_issue_id)
            issue_doc = issue_ref.get()
            
            if not issue_doc.exists:
                # Issue was deleted, create new one
                existing_issue_id = None
            else:
                existing_data = issue_doc.to_dict()
                existing_report_ids = set(existing_data.get("report_ids", []))
                new_report_ids = set(report_ids)
                
                # Merge report IDs (avoid duplicates)
                all_report_ids = list(existing_report_ids | new_report_ids)
                
                # Recalculate centroid with all reports
                all_reports = cluster.copy()
                # Fetch existing reports to recalculate centroid
                reports_ref = db.collection("reports")
                for rid in existing_report_ids:
                    if rid not in report_ids:
                        try:
                            rdoc = reports_ref.document(rid).get()
                            if rdoc.exists:
                                rdata = rdoc.to_dict()
                                if rdata:
                                    rdata["id"] = rid
                                    all_reports.append(rdata)
                        except Exception:
                            pass
                
                new_centroid_lat, new_centroid_lon = _calculate_centroid(all_reports)
                
                # CRITICAL FIX: Ensure coordinates are valid before updating
                if (new_centroid_lat is None or new_centroid_lon is None or 
                    not isinstance(new_centroid_lat, (int, float)) or not isinstance(new_centroid_lon, (int, float)) or
                    math.isnan(new_centroid_lat) or math.isnan(new_centroid_lon) or
                    (new_centroid_lat == 0.0 and new_centroid_lon == 0.0)):
                    # Skip update if coordinates are invalid
                    return existing_issue_id
                
                new_locality = _get_dominant_locality(all_reports)
                
                # Update issue
                issue_ref.update({
                    "report_count": len(all_report_ids),
                    "report_ids": all_report_ids,
                    "latitude": new_centroid_lat,
                    "longitude": new_centroid_lon,
                    "locality": new_locality,
                    "updated_at": datetime.now(timezone.utc),
                })
                
                # Link new reports to issue
                for report_id in new_report_ids - existing_report_ids:
                    try:
                        reports_ref.document(report_id).update({"issue_id": existing_issue_id})
                    except Exception:
                        pass
                
                # Trigger confidence recalculation
                from app.services.issue_confidence_engine import recalculate_issue_confidence
                recalculate_issue_confidence(existing_issue_id)
                
                # AI enrichment: Trigger on issue update (fire-and-forget, non-blocking)
                try:
                    # Get updated issue data and linked reports
                    updated_issue_doc = issue_ref.get()
                    if updated_issue_doc.exists:
                        updated_issue_data = updated_issue_doc.to_dict()
                        if updated_issue_data:
                            # Fetch all linked reports
                            linked_reports = []
                            for rid in all_report_ids:
                                try:
                                    rdoc = reports_ref.document(rid).get()
                                    if rdoc.exists:
                                        rdata = rdoc.to_dict()
                                        if rdata:
                                            linked_reports.append(rdata)
                                except Exception:
                                    pass
                            
                            # Enrich issue with AI (fail-safe)
                            from app.services.ai_issue_enrichment import enrich_issue
                            ai_metadata = enrich_issue(updated_issue_data, linked_reports)
                            if ai_metadata:
                                # Store in ai_metadata, don't overwrite if already present
                                existing_ai_metadata = updated_issue_data.get("ai_metadata", {})
                                if not existing_ai_metadata:
                                    issue_ref.update({"ai_metadata": ai_metadata})
                except Exception:
                    # Fail silently - AI enrichment should never block issue updates
                    pass
                
                return existing_issue_id
        except Exception as e:
            print(f"Error updating existing issue: {e}")
            # Fall through to create new issue
    
    # Create new issue
    if existing_issue_id is None:
        # Generate issue ID using Firestore auto-ID
        issue_ref = db.collection("issues").document()
        issue_id = issue_ref.id
        
        issue_data = {
            "id": issue_id,
            "title": f"{issue_type} issue in {locality or city}",
            "description": f"Multiple reports of {issue_type.lower()} issues in {locality or city}. {len(cluster)} reports received.",
            "issue_type": issue_type,
            "city": city,
            "locality": locality,
            "latitude": centroid_lat,
            "longitude": centroid_lon,
            "report_count": len(cluster),
            "report_ids": report_ids,
            "confidence": "LOW",
            "confidence_score": 0.2,
            "confidence_reason": f"Issue created from {len(cluster)} reports",
            "status": "ACTIVE",
            "severity": "Low",
            "created_at": earliest_time,
            "updated_at": datetime.now(timezone.utc),  # BUG FIX: Use timezone-aware datetime for consistent comparison
            "confidence_timeline": [
                {
                    "timestamp": datetime.now(timezone.utc),
                    "previous_confidence": None,
                    "previous_confidence_score": None,
                    "new_confidence": "LOW",
                    "confidence_score": 0.2,
                    "reason": f"Issue created from {len(cluster)} reports"
                }
            ],
            "timeline": [],
            "operatorNotes": None,
        }
        
        try:
            issue_ref.set(issue_data)
            
            # Link reports to issue
            reports_ref = db.collection("reports")
            for report_id in report_ids:
                try:
                    reports_ref.document(report_id).update({"issue_id": issue_id})
                except Exception as e:
                    print(f"Warning: Failed to update report {report_id} with issue_id: {e}")
            
            # Trigger confidence recalculation
            from app.services.issue_confidence_engine import recalculate_issue_confidence
            recalculate_issue_confidence(issue_id)
            
            # AI enrichment: Trigger on issue creation (fire-and-forget, non-blocking)
            try:
                # Get updated issue data and linked reports
                updated_issue_doc = issue_ref.get()
                if updated_issue_doc.exists:
                    updated_issue_data = updated_issue_doc.to_dict()
                    if updated_issue_data:
                        # Fetch all linked reports
                        linked_reports = []
                        for rid in report_ids:
                            try:
                                rdoc = reports_ref.document(rid).get()
                                if rdoc.exists:
                                    rdata = rdoc.to_dict()
                                    if rdata:
                                        linked_reports.append(rdata)
                            except Exception:
                                pass
                        
                        # Enrich issue with AI (fail-safe)
                        from app.services.ai_issue_enrichment import enrich_issue
                        ai_metadata = enrich_issue(updated_issue_data, linked_reports)
                        if ai_metadata:
                            # Store in ai_metadata, don't overwrite if already present
                            existing_ai_metadata = updated_issue_data.get("ai_metadata", {})
                            if not existing_ai_metadata:
                                issue_ref.update({"ai_metadata": ai_metadata})
            except Exception:
                # Fail silently - AI enrichment should never block issue creation
                pass
            
            return issue_id
        except Exception as e:
            print(f"Error creating issue: {e}")
            return None
    
    return None


def attempt_issue_aggregation(report_id: Optional[str] = None) -> List[str]:
    """
    Attempt to create or update issues from eligible report clusters.
    
    Phase 5B.1: Query recent reports (last 24h) and aggregate into issues.
    Updates existing issues if cluster matches, creates new ones if not.
    
    This function is idempotent - it will not create duplicate issues.
    
    CRITICAL: This function MUST be called after report creation to ensure
    reports are aggregated into issues. Logging proves execution.
    
    Args:
        report_id: Optional report ID to focus aggregation around (for efficiency)
    
    Returns:
        List of created/updated issue IDs
    """
    import logging
    logger = logging.getLogger(__name__)
    
    db = get_db()
    if db is None:
        logger.warning("[AGGREGATION] Database not initialized, skipping aggregation")
        return []
    
    updated_issue_ids = []
    
    try:
        logger.info(f"[AGGREGATION] Starting aggregation (report_id: {report_id})")
        reports_ref = db.collection("reports")
        
        # Query recent reports (last 24 hours) for efficiency
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=24)
        
        # Get eligible reports from last 24h
        all_reports = []
        
        # Query by status if possible (Firestore compound queries)
        # Fallback: stream all and filter
        try:
            # Try to query by status first
            query = where_filter(reports_ref, "status", "in", list(VALID_STATUSES))
            docs = query.stream()
        except Exception:
            # Fallback: stream all
            docs = reports_ref.stream()
        
        for doc in docs:
            data = doc.to_dict()
            if data is None:
                continue
            
            # Skip if already linked to an issue (unless we're checking for updates)
            # Actually, we want to check all reports to see if they should be linked
            
            # Check status
            status = data.get("status", "")
            if status not in VALID_STATUSES:
                continue
            
            # Must have coordinates
            if data.get("latitude") is None or data.get("longitude") is None:
                continue
            
            # Must have issue_type and city (normalized)
            # CRITICAL: Normalize city to ensure consistent matching
            normalized_city = normalize_city_name(data.get("city"))
            if not data.get("issue_type") or not normalized_city or normalized_city == "UNKNOWN":
                continue
            
            # Update data with normalized city for consistent comparison
            data["city"] = normalized_city
            
            # Check if within time window (last 24h)
            created_at = _parse_timestamp(data.get("created_at"))
            if created_at is None or created_at < cutoff_time:
                continue
            
            data["id"] = doc.id
            all_reports.append(data)
        
        # Find eligible clusters
        clusters = _find_eligible_clusters(all_reports)
        
        # Create or update issues from clusters
        logger.info(f"[AGGREGATION] Found {len(clusters)} eligible cluster(s)")
        for cluster in clusters:
            issue_id = create_or_update_issue_from_cluster(cluster)
            if issue_id:
                updated_issue_ids.append(issue_id)
                logger.info(f"[AGGREGATION] Created/updated issue {issue_id} from {len(cluster)} reports")
        
        # Phase 5B.1: Also check individual unlinked reports against existing issues
        # Link reports that match existing issues (even if cluster < 5)
        unlinked_reports = [r for r in all_reports if not r.get("issue_id")]
        
        for report in unlinked_reports:
            try:
                lat = report.get("latitude")
                lon = report.get("longitude")
                issue_type = report.get("issue_type")
                city = normalize_city_name(report.get("city"))  # CRITICAL: Normalize for matching
                
                if not all([lat, lon, issue_type, city]) or city == "UNKNOWN":
                    continue
                
                # Find existing issue that matches (using normalized city)
                existing_issue_id = _find_existing_issue(db, issue_type, city, lat, lon)
                
                if existing_issue_id:
                    # Link report to existing issue
                    reports_ref = db.collection("reports")
                    reports_ref.document(report.get("id")).update({"issue_id": existing_issue_id})
                    
                    # Update issue with new report
                    issue_ref = db.collection("issues").document(existing_issue_id)
                    issue_doc = issue_ref.get()
                    
                    if issue_doc.exists:
                        issue_data = issue_doc.to_dict()
                        existing_report_ids = set(issue_data.get("report_ids", []))
                        existing_report_ids.add(report.get("id"))
                        
                        # Recalculate centroid
                        all_report_ids = list(existing_report_ids)
                        all_reports_for_centroid = [report]
                        reports_ref = db.collection("reports")
                        for rid in all_report_ids:
                            if rid != report.get("id"):
                                try:
                                    rdoc = reports_ref.document(rid).get()
                                    if rdoc.exists:
                                        rdata = rdoc.to_dict()
                                        if rdata:
                                            rdata["id"] = rid
                                            all_reports_for_centroid.append(rdata)
                                except Exception:
                                    pass
                        
                        new_centroid_lat, new_centroid_lon = _calculate_centroid(all_reports_for_centroid)
                        
                        # CRITICAL FIX: Ensure coordinates are valid before updating
                        if (new_centroid_lat is None or new_centroid_lon is None or 
                            not isinstance(new_centroid_lat, (int, float)) or not isinstance(new_centroid_lon, (int, float)) or
                            math.isnan(new_centroid_lat) or math.isnan(new_centroid_lon) or
                            (new_centroid_lat == 0.0 and new_centroid_lon == 0.0)):
                            # Skip update if coordinates are invalid
                            continue
                        
                        new_locality = _get_dominant_locality(all_reports_for_centroid)
                        
                        issue_ref.update({
                            "report_count": len(all_report_ids),
                            "report_ids": all_report_ids,
                            "latitude": new_centroid_lat,
                            "longitude": new_centroid_lon,
                            "locality": new_locality,
                            "updated_at": datetime.now(timezone.utc),
                        })
                        
                        # Recalculate confidence
                        from app.services.issue_confidence_engine import recalculate_issue_confidence
                        recalculate_issue_confidence(existing_issue_id)
                        
                        # AI enrichment: Trigger on issue update (fire-and-forget, non-blocking)
                        try:
                            # Get updated issue data and linked reports
                            updated_issue_doc = issue_ref.get()
                            if updated_issue_doc.exists:
                                updated_issue_data = updated_issue_doc.to_dict()
                                if updated_issue_data:
                                    # Fetch all linked reports
                                    linked_reports = []
                                    for rid in all_report_ids:
                                        try:
                                            rdoc = reports_ref.document(rid).get()
                                            if rdoc.exists:
                                                rdata = rdoc.to_dict()
                                                if rdata:
                                                    linked_reports.append(rdata)
                                        except Exception:
                                            pass
                                    
                                    # Enrich issue with AI (fail-safe)
                                    from app.services.ai_issue_enrichment import enrich_issue
                                    ai_metadata = enrich_issue(updated_issue_data, linked_reports)
                                    if ai_metadata:
                                        # Store in ai_metadata, don't overwrite if already present
                                        existing_ai_metadata = updated_issue_data.get("ai_metadata", {})
                                        if not existing_ai_metadata:
                                            issue_ref.update({"ai_metadata": ai_metadata})
                        except Exception:
                            # Fail silently - AI enrichment should never block issue updates
                            pass
                        
                        if existing_issue_id not in updated_issue_ids:
                            updated_issue_ids.append(existing_issue_id)
            except Exception:
                # Continue processing other reports
                pass
        
        logger.info(f"[AGGREGATION] Aggregation completed: {len(updated_issue_ids)} issue(s) created/updated")
        return updated_issue_ids
    
    except Exception as e:
        logger.error(f"[AGGREGATION] Error in issue aggregation: {e}", exc_info=True)
        return []
