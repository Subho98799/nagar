"""
City Pulse Service - Aggregates city situation into human-readable summary.

DESIGN PRINCIPLES (CRITICAL):
- City Pulse is NOT alerts
- City Pulse is NOT forecasting
- City Pulse is NOT recommendations
- City Pulse is a CALM, NEUTRAL summary of current situation

WHAT CITY PULSE REPRESENTS:
✅ What is happening (active issues)
✅ Where it is happening (affected localities)
✅ How confident the system is (confidence breakdown)
✅ Whether things are ongoing (status-based filtering)

WHAT CITY PULSE DOES NOT DO:
❌ Predict future events
❌ Trigger actions
❌ Send alerts
❌ Recommend responses
❌ Analyze trends
"""

from firebase_admin import firestore
from app.config.firebase import get_db
from app.utils.firestore_helpers import where_filter
from app.services.ai_interpreter import get_ai_interpreter
from typing import Dict, List, Optional
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


class CityPulseService:
    """
    Aggregates current city situation into a structured, calm summary.
    
    This is a READ-ONLY service. It does not modify any data.
    It provides a snapshot of the current situation, not predictions.
    """
    
    # Statuses that represent "active" situations
    ACTIVE_STATUSES = ["UNDER_OBSERVATION", "CONFIRMED"]
    
    def __init__(self):
        self.db = get_db()
        self.ai_interpreter = get_ai_interpreter()
    
    def get_city_pulse(self, city: str) -> Dict:
        """
        Generate a City Pulse summary for the given city.
        
        This aggregates:
        1. Active issues by type
        2. Confidence breakdown (LOW/MEDIUM/HIGH)
        3. Affected localities
        4. AI-generated calm summary
        
        Args:
            city: City name to aggregate data for
        
        Returns:
            dict: City Pulse summary with structured data
        """
        try:
            # STEP 1: Fetch active reports for the city
            reports = self._fetch_active_reports(city)
            
            if not reports:
                return self._empty_pulse(city)
            
            # STEP 2: Aggregate data
            active_issues = self._count_issues_by_type(reports)
            confidence_breakdown = self._count_by_confidence(reports)
            affected_localities = self._extract_localities(reports)
            
            # STEP 3: Generate AI summary (safe, may fail)
            summary = self._generate_summary(
                city=city,
                active_issues=active_issues,
                confidence_breakdown=confidence_breakdown,
                affected_localities=affected_localities,
                report_count=len(reports)
            )
            
            # STEP 4: Build response
            pulse = {
                "city": city,
                "report_count": len(reports),
                "active_issues": dict(active_issues),
                "confidence_breakdown": dict(confidence_breakdown),
                "affected_localities": affected_localities,
                "summary": summary,
                "pulse_generated_at": firestore.SERVER_TIMESTAMP
            }
            
            logger.info(f"✅ City Pulse generated for {city}: {len(reports)} active reports")
            
            return pulse
        
        except Exception as e:
            logger.error(f"❌ Failed to generate City Pulse for {city}: {str(e)}")
            raise
    
    def _fetch_active_reports(self, city: str) -> List[Dict]:
        """
        Fetch all active reports for a given city.
        
        Active = status is UNDER_OBSERVATION or CONFIRMED
        (RESOLVED reports are excluded - they're no longer active)
        
        Args:
            city: City name to filter by (should be normalized, lowercase)
        
        Returns:
            List of active report dictionaries
        """
        reports = []
        
        try:
            # Query reports for this city with active statuses
            # Firestore limitation: we can only filter by one field with 'in'
            # So we'll filter status in Python for simplicity
            reports_ref = self.db.collection("reports")
            query = where_filter(reports_ref, "city", "==", city)
            
            docs = query.stream()
            
            for doc in docs:
                data = doc.to_dict()
                if data is None:
                    continue
                data["id"] = doc.id
                
                # Filter by active status
                status = data.get("status", "UNDER_OBSERVATION")
                if status in self.ACTIVE_STATUSES:
                    reports.append(data)
        except Exception as e:
            logger.error(f"Error fetching active reports for city '{city}': {e}", exc_info=True)
            # Return empty list on error rather than crashing
            return []
        
        logger.info(f"Found {len(reports)} active reports for {city}")
        
        return reports
    
    def _count_issues_by_type(self, reports: List[Dict]) -> Dict[str, int]:
        """
        Count reports by issue type.
        
        Uses AI-classified category from ai_metadata (preferred for aggregation).
        Falls back to user-selected issue_type, then "Unclassified" if not available.
        
        Args:
            reports: List of report dictionaries
        
        Returns:
            Dict mapping issue type to count
        """
        issue_counts = defaultdict(int)
        
        for report in reports:
            # Get AI-classified category (preferred for aggregation)
            ai_metadata = report.get("ai_metadata", {})
            issue_type = ai_metadata.get("ai_classified_category", "")
            
            # Fallback to user-selected issue_type field
            if not issue_type:
                issue_type = report.get("issue_type", "")
            
            # Default if still empty
            if not issue_type:
                issue_type = "Unclassified"
            
            issue_counts[issue_type] += 1
        
        # Sort by count (descending)
        sorted_issues = dict(sorted(
            issue_counts.items(),
            key=lambda x: x[1],
            reverse=True
        ))
        
        return sorted_issues
    
    def _count_by_confidence(self, reports: List[Dict]) -> Dict[str, int]:
        """
        Count reports by confidence level.
        
        Provides breakdown of LOW/MEDIUM/HIGH confidence reports.
        
        Args:
            reports: List of report dictionaries
        
        Returns:
            Dict mapping confidence level to count
        """
        confidence_counts = {
            "LOW": 0,
            "MEDIUM": 0,
            "HIGH": 0
        }
        
        for report in reports:
            confidence = report.get("confidence", "LOW")
            if confidence in confidence_counts:
                confidence_counts[confidence] += 1
            else:
                confidence_counts["LOW"] += 1  # Default unknown to LOW
        
        return confidence_counts
    
    def _extract_localities(self, reports: List[Dict]) -> List[str]:
        """
        Extract unique affected localities.
        
        Returns list of unique locality names, sorted alphabetically.
        
        Args:
            reports: List of report dictionaries
        
        Returns:
            List of unique locality names
        """
        localities = set()
        
        for report in reports:
            locality = report.get("locality", "").strip()
            if locality:
                localities.add(locality)
        
        # Sort alphabetically for consistency
        return sorted(list(localities))
    
    def _generate_summary(
        self,
        city: str,
        active_issues: Dict[str, int],
        confidence_breakdown: Dict[str, int],
        affected_localities: List[str],
        report_count: int
    ) -> str:
        """
        Generate a calm, human-readable summary of the city situation.
        
        Uses AI for natural language generation, but falls back to
        template-based summary if AI fails.
        
        IMPORTANT: Summary must be:
        - Calm and neutral
        - Non-alarmist
        - Factual (what IS, not what MIGHT BE)
        - No recommendations
        - No predictions
        
        Args:
            city: City name
            active_issues: Issue type counts
            confidence_breakdown: Confidence level counts
            affected_localities: List of affected localities
            report_count: Total active report count
        
        Returns:
            Human-readable summary string
        """
        try:
            # Attempt AI-generated summary
            summary = self._ai_generate_summary(
                city=city,
                active_issues=active_issues,
                confidence_breakdown=confidence_breakdown,
                affected_localities=affected_localities,
                report_count=report_count
            )
            return summary
        
        except Exception as e:
            logger.warning(f"⚠️ AI summary failed, using template: {str(e)}")
            # Fallback to template-based summary
            return self._template_summary(
                city=city,
                active_issues=active_issues,
                confidence_breakdown=confidence_breakdown,
                report_count=report_count
            )
    
    def _ai_generate_summary(
        self,
        city: str,
        active_issues: Dict[str, int],
        confidence_breakdown: Dict[str, int],
        affected_localities: List[str],
        report_count: int
    ) -> str:
        """
        Use AI to generate a natural language summary.
        
        The AI is given structured data and asked to create
        a calm, neutral summary. This is advisory only.
        """
        # Build context for AI
        issue_summary = ", ".join([
            f"{count} {issue_type.lower()} report(s)"
            for issue_type, count in active_issues.items()
        ])
        
        locality_summary = ", ".join(affected_localities[:5])  # Top 5 localities
        if len(affected_localities) > 5:
            locality_summary += f" and {len(affected_localities) - 5} other areas"
        
        high_confidence = confidence_breakdown.get("HIGH", 0)
        medium_confidence = confidence_breakdown.get("MEDIUM", 0)
        low_confidence = confidence_breakdown.get("LOW", 0)
        
        # Create a pseudo-description for the AI interpreter
        context = f"""
        City: {city}
        Total active reports: {report_count}
        Issues: {issue_summary}
        Affected areas: {locality_summary}
        Confidence: {high_confidence} high, {medium_confidence} medium, {low_confidence} low
        """
        
        # Use mock AI summary generation
        # In production, this would call Gemini with a specific prompt
        return self._mock_ai_summary(
            city=city,
            active_issues=active_issues,
            confidence_breakdown=confidence_breakdown,
            affected_localities=affected_localities,
            report_count=report_count
        )
    
    def _mock_ai_summary(
        self,
        city: str,
        active_issues: Dict[str, int],
        confidence_breakdown: Dict[str, int],
        affected_localities: List[str],
        report_count: int
    ) -> str:
        """
        Mock AI summary generation for development.
        
        Produces calm, neutral summaries based on data.
        Will be replaced with Gemini API in production.
        """
        # Determine dominant issue
        if not active_issues:
            return f"No active reports in {city} at this time."
        
        dominant_issue = list(active_issues.keys())[0]
        dominant_count = list(active_issues.values())[0]
        
        # Build summary parts
        parts = []
        
        # Part 1: What's happening
        if len(active_issues) == 1:
            parts.append(f"{dominant_issue} issues are currently reported in {city}")
        else:
            other_issues = list(active_issues.keys())[1:3]  # Up to 2 more
            others_text = " and ".join(other_issues).lower()
            parts.append(f"{dominant_issue} along with {others_text} issues are currently reported in {city}")
        
        # Part 2: Where
        if len(affected_localities) == 1:
            parts.append(f"in {affected_localities[0]}")
        elif len(affected_localities) <= 3:
            parts.append(f"across {', '.join(affected_localities)}")
        else:
            parts.append(f"across {len(affected_localities)} localities")
        
        # Part 3: Confidence context
        high_conf = confidence_breakdown.get("HIGH", 0)
        medium_conf = confidence_breakdown.get("MEDIUM", 0)
        
        if high_conf > 0:
            parts.append(f". {high_conf} report(s) have been reviewed and confirmed")
        elif medium_conf > 0:
            parts.append(f". {medium_conf} report(s) show corroborating patterns")
        else:
            parts.append(". Most reports remain under observation")
        
        # Combine
        summary = " ".join(parts) + "."
        
        # Clean up grammar
        summary = summary.replace(" .", ".").replace("..", ".")
        
        return summary
    
    def _template_summary(
        self,
        city: str,
        active_issues: Dict[str, int],
        confidence_breakdown: Dict[str, int],
        report_count: int
    ) -> str:
        """
        Generate a simple template-based summary.
        
        Used as fallback when AI is unavailable.
        Always produces valid, calm output.
        """
        if report_count == 0:
            return f"No active reports in {city} at this time."
        
        # Get dominant issues
        issue_names = list(active_issues.keys())[:3]
        
        if len(issue_names) == 1:
            issues_text = issue_names[0]
        elif len(issue_names) == 2:
            issues_text = f"{issue_names[0]} and {issue_names[1]}"
        else:
            issues_text = f"{issue_names[0]}, {issue_names[1]}, and others"
        
        # Simple template
        return f"{report_count} active report(s) in {city} related to {issues_text.lower()}. Situation is being monitored."
    
    def _empty_pulse(self, city: str) -> Dict:
        """
        Return an empty City Pulse when no active reports exist.
        """
        return {
            "city": city,
            "report_count": 0,
            "active_issues": {},
            "confidence_breakdown": {
                "LOW": 0,
                "MEDIUM": 0,
                "HIGH": 0
            },
            "affected_localities": [],
            "summary": f"No active reports in {city} at this time."
        }


# Global service instance (singleton pattern)
_city_pulse_service = None


def get_city_pulse_service() -> CityPulseService:
    """
    Get or create CityPulseService singleton instance.
    
    Returns:
        CityPulseService: The global city pulse service instance
    """
    global _city_pulse_service
    if _city_pulse_service is None:
        _city_pulse_service = CityPulseService()
    return _city_pulse_service
