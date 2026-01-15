"""
AI Provider Base Interface - Phase-3 Part 2.

Defines the contract for AI providers.
All AI providers must implement this interface.
"""

from abc import ABC, abstractmethod
from typing import Dict, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class AIResponse:
    """
    Standardized AI response structure.
    
    All AI providers must return this structure.
    """
    
    def __init__(
        self,
        ai_classified_category: str,
        severity_hint: str,
        keywords: list,
        summary: str,
        model_name: str,
        model_version: str,
        inference_timestamp: datetime,
        ai_confidence_score: Optional[float] = None,
        error: Optional[str] = None
    ):
        self.ai_classified_category = ai_classified_category
        self.severity_hint = severity_hint
        self.keywords = keywords
        self.summary = summary
        self.model_name = model_name
        self.model_version = model_version
        self.inference_timestamp = inference_timestamp
        self.ai_confidence_score = ai_confidence_score  # Optional, 0.0-1.0
        self.error = error  # If AI failed, error message stored here
    
    def to_dict(self) -> Dict:
        """
        Convert to dictionary for storage in ai_metadata.
        
        Includes all Phase-3 Part 2 metadata extensions.
        """
        result = {
            "ai_classified_category": self.ai_classified_category,
            "severity_hint": self.severity_hint,
            "keywords": self.keywords,
            "summary": self.summary,
            "model_name": self.model_name,
            "model_version": self.model_version,
            "inference_timestamp": self.inference_timestamp.isoformat() if isinstance(self.inference_timestamp, datetime) else str(self.inference_timestamp),
        }
        
        # Optional fields (only include if present)
        if self.ai_confidence_score is not None:
            result["ai_confidence_score"] = self.ai_confidence_score
        
        if self.error:
            result["error"] = self.error
            result["ai_failure_reason"] = self.error  # Alias for clarity in Phase-3 Part 2
        
        return result


class AIProvider(ABC):
    """
    Abstract base class for AI providers.
    
    All AI providers must implement this interface.
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
    def interpret_report(
        self,
        description: str,
        city: str = "",
        locality: str = ""
    ) -> AIResponse:
        """
        Interpret a citizen report using AI.
        
        This method MUST:
        - Return a valid AIResponse even on failure
        - Never raise exceptions (catch and return error in response)
        - Respect timeout limits
        - Not block the calling thread indefinitely
        
        Args:
            description: The citizen's observation
            city: City name (provides context)
            locality: Locality name (provides context)
        
        Returns:
            AIResponse: Standardized AI response (may contain error)
        """
        pass
    
    @abstractmethod
    def get_timeout_seconds(self) -> float:
        """
        Get timeout for AI inference (in seconds).
        
        Returns:
            Timeout in seconds (e.g., 5.0 for 5 seconds)
        """
        pass
