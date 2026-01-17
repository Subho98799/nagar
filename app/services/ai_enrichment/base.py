"""
AI Enrichment Base Interface - Phase 6

Defines the contract for AI issue enrichment providers.
All enrichment providers must implement this interface.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class IssueEnrichmentResponse:
    """
    Standardized AI enrichment response structure for issues.
    
    All AI providers must return this structure.
    """
    
    def __init__(
        self,
        summary: str = "",
        keywords: List[str] = None,
        severity_hint: str = "",
        title_suggestion: str = "",
        summary_hinglish: str = "",
        language_detected: str = "English",
        model_name: str = "",
        model_version: str = "",
        inference_timestamp: Optional[datetime] = None,
        error: Optional[str] = None
    ):
        self.summary = summary
        self.keywords = keywords or []
        self.severity_hint = severity_hint
        self.title_suggestion = title_suggestion
        self.summary_hinglish = summary_hinglish  # Hinglish summary if available
        self.language_detected = language_detected  # Detected language from reports
        self.model_name = model_name
        self.model_version = model_version
        self.inference_timestamp = inference_timestamp or datetime.utcnow()
        self.error = error
    
    def to_dict(self) -> Dict:
        """
        Convert to dictionary for storage in issues.ai_metadata.
        
        Returns empty dict if error occurred (fail-safe).
        """
        if self.error:
            return {
                "error": self.error,
                "model_name": self.model_name,
                "model_version": self.model_version,
                "inference_timestamp": self.inference_timestamp.isoformat() if isinstance(self.inference_timestamp, datetime) else str(self.inference_timestamp)
            }
        
        result = {
            "summary": self.summary,
            "keywords": self.keywords,
            "severity_hint": self.severity_hint,
            "title_suggestion": self.title_suggestion,
            "summary_hinglish": self.summary_hinglish,
            "language_detected": self.language_detected,
            "model_name": self.model_name,
            "model_version": self.model_version,
            "inference_timestamp": self.inference_timestamp.isoformat() if isinstance(self.inference_timestamp, datetime) else str(self.inference_timestamp)
        }
        
        # Remove empty fields (but keep required fields even if empty)
        # Required fields: summary, keywords, severity_hint, language_detected
        filtered = {}
        for k, v in result.items():
            if k in ["summary", "keywords", "severity_hint", "language_detected"]:
                # Always include required fields
                filtered[k] = v
            elif v:  # Only include non-empty optional fields
                filtered[k] = v
        
        return filtered


class IssueEnrichmentProvider(ABC):
    """
    Abstract base class for AI issue enrichment providers.
    
    All enrichment providers must implement this interface.
    This ensures consistent behavior and graceful failure handling.
    """
    
    @abstractmethod
    def is_enabled(self) -> bool:
        """
        Check if this AI provider is enabled.
        
        Returns:
            True if provider is enabled and ready, False otherwise
        """
        pass
    
    @abstractmethod
    def get_model_info(self) -> Dict[str, str]:
        """
        Get model information (name, version).
        
        Returns:
            Dict with 'name' and 'version' keys
        """
        pass
    
    @abstractmethod
    def enrich_issue(
        self,
        issue: Dict,
        reports: List[Dict]
    ) -> IssueEnrichmentResponse:
        """
        Enrich an issue using AI based on clustered reports.
        
        This method MUST:
        - Return a valid IssueEnrichmentResponse even on failure
        - Never raise exceptions (catch and return error in response)
        - Respect timeout limits
        - Not block the calling thread indefinitely
        - Support Hinglish (Hindi + English mix) input
        - Output calm, neutral English
        
        Args:
            issue: The issue document dict (from Firestore)
            reports: List of report dicts that are linked to this issue
        
        Returns:
            IssueEnrichmentResponse: Standardized enrichment response (may contain error)
        """
        pass
    
    @abstractmethod
    def get_timeout_seconds(self) -> float:
        """
        Get timeout for AI inference (in seconds).
        
        Returns:
            Timeout in seconds (e.g., 8.0 for 8 seconds)
        """
        pass
