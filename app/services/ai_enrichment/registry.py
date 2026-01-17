"""
AI Enrichment Registry - Phase 6

Manages AI enrichment provider selection and fail-safe logic.
Provides the main entry point for issue enrichment.
"""

from app.services.ai_enrichment.base import IssueEnrichmentProvider, IssueEnrichmentResponse
from app.services.ai_enrichment.llm_provider import LLMEnrichmentProvider
from app.core.settings import settings
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class AIEnrichmentRegistry:
    """
    Registry for AI enrichment providers with fail-safe logic.
    
    Selects the best available provider based on configuration.
    Falls back gracefully if provider fails.
    """
    
    def __init__(self):
        self.provider: Optional[IssueEnrichmentProvider] = None
        self._initialize_provider()
    
    def _initialize_provider(self):
        """Initialize AI enrichment provider."""
        # Check if AI is globally enabled
        if not settings.AI_ENABLED:
            logger.info("⚠️ AI enrichment is disabled globally (AI_ENABLED=false)")
            self.provider = None
            return
        
        # Try to initialize LLM provider
        try:
            llm_provider = LLMEnrichmentProvider()
            if llm_provider.is_enabled():
                self.provider = llm_provider
                logger.info("✅ LLM Enrichment Provider registered")
            else:
                logger.info("⚠️ LLM Enrichment Provider not available (no API key)")
                self.provider = None
        except Exception as e:
            logger.warning(f"⚠️ Failed to initialize LLM provider: {e}")
            self.provider = None
    
    def enrich_issue(
        self,
        issue: Dict,
        reports: List[Dict]
    ) -> Dict:
        """
        Enrich an issue using AI.
        
        This is the main entry point for issue enrichment.
        Always returns a dict (may be empty on failure).
        Never raises exceptions.
        
        Args:
            issue: The issue document dict (from Firestore)
            reports: List of report dicts that are linked to this issue
        
        Returns:
            Dict to store in issues.ai_metadata (empty dict if enrichment failed/disabled)
        """
        # If AI is disabled or no provider available, return empty dict
        if not settings.AI_ENABLED or self.provider is None:
            return {}
        
        try:
            # Call provider (with timeout protection)
            response = self.provider.enrich_issue(issue, reports)
            
            # Convert to dict for storage
            result = response.to_dict()
            
            # If there's an error, log it but still return the error dict
            if response.error:
                logger.warning(f"⚠️ AI enrichment failed: {response.error}")
            
            return result
        
        except Exception as e:
            # Fail-safe: log error and return empty dict
            logger.error(f"⚠️ AI enrichment exception: {e}")
            return {}


# Global registry instance (singleton)
_registry: Optional[AIEnrichmentRegistry] = None


def enrich_issue(issue: Dict, reports: List[Dict]) -> Dict:
    """
    Enrich an issue using AI based on clustered reports.
    
    This is the main entry point for issue enrichment.
    Always returns a dict (may be empty on failure).
    Never raises exceptions.
    
    Integration point: Call this AFTER issue creation/update and AFTER confidence recalculation.
    
    Args:
        issue: The issue document dict (from Firestore)
        reports: List of report dicts that are linked to this issue
    
    Returns:
        Dict to store in issues.ai_metadata (empty dict if enrichment failed/disabled)
    
    Example:
        # After creating/updating issue and recalculating confidence:
        ai_metadata = enrich_issue(issue_data, linked_reports)
        if ai_metadata:
            issue_ref.update({"ai_metadata": ai_metadata})
    """
    global _registry
    if _registry is None:
        _registry = AIEnrichmentRegistry()
    
    return _registry.enrich_issue(issue, reports)
