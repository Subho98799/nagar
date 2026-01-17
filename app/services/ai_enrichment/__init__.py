"""
AI Enrichment Module - Phase 6

Provides AI enrichment for ISSUES (not reports).
This is a separate layer from the report AI interpretation.

Key principles:
- Runs AFTER issue creation/update
- Runs AFTER confidence recalculation
- Never changes core fields (confidence, status, etc.)
- Fail-safe: returns {} on any error
- Supports Hinglish input
"""

from app.services.ai_enrichment.registry import enrich_issue

__all__ = ["enrich_issue"]
