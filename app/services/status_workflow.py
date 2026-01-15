"""
Status Workflow Engine - Phase-2 strict state machine.

DESIGN PRINCIPLES:
- No skipping states
- No backward transitions
- All transitions logged in status_history
- Invalid transitions rejected programmatically
"""

from enum import Enum
from datetime import datetime
from typing import Dict, List, Optional
from firebase_admin import firestore
import logging

logger = logging.getLogger(__name__)


class ReportStatus(str, Enum):
    """
    Strict status lifecycle for Phase-2.
    
    States must be traversed in order:
    UNDER_REVIEW → VERIFIED → ACTION_TAKEN → CLOSED
    """
    UNDER_REVIEW = "UNDER_REVIEW"      # Initial state, awaiting review
    VERIFIED = "VERIFIED"               # Reviewed and validated
    ACTION_TAKEN = "ACTION_TAKEN"       # Action initiated/resolved
    CLOSED = "CLOSED"                   # Final state, issue resolved


class StatusWorkflowEngine:
    """
    Strict state machine for report status transitions.
    
    Rules:
    - No skipping states
    - No backward transitions
    - All transitions logged
    """
    
    # Allowed transitions map: {from_status: [to_status, ...]}
    ALLOWED_TRANSITIONS: Dict[ReportStatus, List[ReportStatus]] = {
        ReportStatus.UNDER_REVIEW: [ReportStatus.VERIFIED],
        ReportStatus.VERIFIED: [ReportStatus.ACTION_TAKEN],
        ReportStatus.ACTION_TAKEN: [ReportStatus.CLOSED],
        ReportStatus.CLOSED: []  # Terminal state, no transitions allowed
    }
    
    @classmethod
    def is_valid_transition(cls, from_status: str, to_status: str) -> bool:
        """
        Check if a status transition is valid.
        
        Args:
            from_status: Current status
            to_status: Desired new status
        
        Returns:
            True if transition is allowed, False otherwise
        """
        try:
            from_enum = ReportStatus(from_status)
            to_enum = ReportStatus(to_status)
        except ValueError:
            # Invalid status values
            return False
        
        # Same status is always valid (no-op)
        if from_enum == to_enum:
            return True
        
        # Check if transition is in allowed list
        allowed = cls.ALLOWED_TRANSITIONS.get(from_enum, [])
        return to_enum in allowed
    
    @classmethod
    def get_allowed_transitions(cls, current_status: str) -> List[str]:
        """
        Get list of allowed next statuses from current status.
        
        Args:
            current_status: Current status string
        
        Returns:
            List of allowed next status strings
        """
        try:
            current_enum = ReportStatus(current_status)
            allowed = cls.ALLOWED_TRANSITIONS.get(current_enum, [])
            return [status.value for status in allowed]
        except ValueError:
            return []
    
    @classmethod
    def create_status_history_entry(
        cls,
        from_status: str,
        to_status: str,
        changed_by: str,
        note: Optional[str] = None
    ) -> Dict:
        """
        Create a status history entry for audit trail.
        
        Args:
            from_status: Previous status
            to_status: New status
            changed_by: User/reviewer identifier
            note: Optional note explaining the change
        
        Returns:
            Status history entry dict
        """
        return {
            "from": from_status,
            "to": to_status,
            "changed_by": changed_by,
            "timestamp": firestore.SERVER_TIMESTAMP,
            "note": note or ""
        }
    
    @classmethod
    def validate_and_transition(
        cls,
        current_status: str,
        new_status: str,
        changed_by: str,
        note: Optional[str] = None
    ) -> Dict:
        """
        Validate transition and create history entry.
        
        Args:
            current_status: Current status
            new_status: Desired new status
            changed_by: User/reviewer identifier
            note: Optional note
        
        Returns:
            Dict with validation result and history entry
        
        Raises:
            ValueError: If transition is invalid
        """
        # Validate transition
        if not cls.is_valid_transition(current_status, new_status):
            allowed = cls.get_allowed_transitions(current_status)
            raise ValueError(
                f"Invalid status transition: {current_status} → {new_status}. "
                f"Allowed transitions from {current_status}: {allowed}"
            )
        
        # Create history entry
        history_entry = cls.create_status_history_entry(
            from_status=current_status,
            to_status=new_status,
            changed_by=changed_by,
            note=note
        )
        
        return {
            "valid": True,
            "from_status": current_status,
            "to_status": new_status,
            "history_entry": history_entry
        }
