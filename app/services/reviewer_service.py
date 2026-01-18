"""
Reviewer Service - Phase-2 backend logic for reviewer operations.

DESIGN PRINCIPLES:
- Filter reports by status, confidence, locality, issue_type
- Update status with strict workflow validation
- Add reviewer notes
- Override AI classification (preserve original)
"""

from firebase_admin import firestore
from app.config.firebase import get_db
from app.utils.firestore_helpers import where_filter
from app.services.status_workflow import StatusWorkflowEngine, ReportStatus
from typing import List, Dict, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ReviewerService:
    """
    Service for reviewer operations on reports.
    """
    
    def __init__(self):
        self.db = get_db()
        self.workflow = StatusWorkflowEngine()
    
    def get_reports(
        self,
        status: Optional[str] = None,
        confidence: Optional[str] = None,
        locality: Optional[str] = None,
        issue_type: Optional[str] = None,
        city: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        Fetch reports with filtering options.
        
        Args:
            status: Filter by status (e.g., "UNDER_REVIEW")
            confidence: Filter by confidence (e.g., "HIGH")
            locality: Filter by locality name
            issue_type: Filter by user-selected issue_type
            city: Filter by city name
            limit: Maximum number of reports to return
        
        Returns:
            List of report dictionaries matching filters
        """
        reports_ref = self.db.collection("reports")
        
        # Build query (Firestore allows one range filter, so we'll filter in Python)
        query = reports_ref
        
        # Apply filters that Firestore supports efficiently
        if city:
            query = where_filter(query, "city", "==", city)
        
        if status:
            query = where_filter(query, "status", "==", status)
        
        if confidence:
            query = where_filter(query, "confidence", "==", confidence)
        
        # Execute query
        docs = query.limit(limit).stream()
        
        reports = []
        for doc in docs:
            data = doc.to_dict()
            data["id"] = doc.id
            
            # Apply Python-side filters
            if locality and data.get("locality") != locality:
                continue
            
            if issue_type and data.get("issue_type") != issue_type:
                continue
            
            reports.append(data)
        
        # Sort by created_at descending (newest first)
        reports.sort(key=lambda x: x.get("created_at", datetime.min), reverse=True)
        
        logger.info(f"Retrieved {len(reports)} reports with filters: status={status}, confidence={confidence}, locality={locality}, issue_type={issue_type}, city={city}")
        
        return reports
    
    def update_status(
        self,
        report_id: str,
        new_status: str,
        reviewer_id: str,
        note: Optional[str] = None
    ) -> Dict:
        """
        Update report status with strict workflow validation.
        
        Args:
            report_id: Firestore document ID
            new_status: New status value
            reviewer_id: Reviewer identifier
            note: Optional note explaining the change
        
        Returns:
            Updated report dictionary
        
        Raises:
            ValueError: If transition is invalid
        """
        doc_ref = self.db.collection("reports").document(report_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            raise ValueError(f"Report {report_id} not found")
        
        current_data = doc.to_dict()
        current_status = current_data.get("status", "UNDER_REVIEW")
        
        # Validate transition
        transition_result = self.workflow.validate_and_transition(
            current_status=current_status,
            new_status=new_status,
            changed_by=reviewer_id,
            note=note
        )
        
        # Get existing status_history
        status_history = current_data.get("status_history", [])
        if not isinstance(status_history, list):
            status_history = []
        
        # Append new history entry
        status_history.append(transition_result["history_entry"])
        
        # Update document
        update_data = {
            "status": new_status,
            "status_history": status_history,
            "reviewed_at": firestore.SERVER_TIMESTAMP
        }
        
        doc_ref.update(update_data)
        
        # Retrieve updated document
        updated_doc = doc_ref.get()
        updated_data = updated_doc.to_dict()
        updated_data["id"] = updated_doc.id
        
        logger.info(f"✅ Reviewer {reviewer_id} updated report {report_id}: {current_status} → {new_status}")
        
        return updated_data
    
    def add_reviewer_note(
        self,
        report_id: str,
        note: str,
        reviewer_id: str
    ) -> Dict:
        """
        Add a reviewer note to a report.
        
        Args:
            report_id: Firestore document ID
            note: Note text
            reviewer_id: Reviewer identifier
        
        Returns:
            Updated report dictionary
        """
        doc_ref = self.db.collection("reports").document(report_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            raise ValueError(f"Report {report_id} not found")
        
        current_data = doc.to_dict()
        
        # Get existing reviewer_notes
        reviewer_notes = current_data.get("reviewer_notes", [])
        if not isinstance(reviewer_notes, list):
            reviewer_notes = []
        
        # Create new note entry
        new_note = {
            "note": note,
            "reviewer_id": reviewer_id,
            "created_at": firestore.SERVER_TIMESTAMP
        }
        
        reviewer_notes.append(new_note)
        
        # Update document
        doc_ref.update({"reviewer_notes": reviewer_notes})
        
        # Retrieve updated document
        updated_doc = doc_ref.get()
        updated_data = updated_doc.to_dict()
        updated_data["id"] = updated_doc.id
        
        logger.info(f"✅ Reviewer {reviewer_id} added note to report {report_id}")
        
        return updated_data
    
    def override_ai_classification(
        self,
        report_id: str,
        reviewer_id: str,
        override_category: str,
        note: Optional[str] = None
    ) -> Dict:
        """
        Override AI classification without deleting original AI data.
        
        Stores override in ai_metadata.override field, preserving original.
        
        Args:
            report_id: Firestore document ID
            reviewer_id: Reviewer identifier
            override_category: New category to use instead of AI classification
            note: Optional note explaining the override
        
        Returns:
            Updated report dictionary
        """
        doc_ref = self.db.collection("reports").document(report_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            raise ValueError(f"Report {report_id} not found")
        
        current_data = doc.to_dict()
        ai_metadata = current_data.get("ai_metadata", {})
        
        # Store override (preserve original)
        ai_metadata["override"] = {
            "category": override_category,
            "reviewer_id": reviewer_id,
            "note": note or "",
            "overridden_at": firestore.SERVER_TIMESTAMP
        }
        
        # Update document
        doc_ref.update({"ai_metadata": ai_metadata})
        
        # Retrieve updated document
        updated_doc = doc_ref.get()
        updated_data = updated_doc.to_dict()
        updated_data["id"] = updated_doc.id
        
        logger.info(f"✅ Reviewer {reviewer_id} overrode AI classification for report {report_id}: {override_category}")
        
        return updated_data


# Global service instance (singleton pattern)
_reviewer_service = None


def get_reviewer_service() -> ReviewerService:
    """
    Get or create ReviewerService singleton instance.
    
    Returns:
        ReviewerService: The global reviewer service instance
    """
    global _reviewer_service
    if _reviewer_service is None:
        _reviewer_service = ReviewerService()
    return _reviewer_service
