"""
City Normalization Utility - Production-Grade City Resolution

Provides robust city normalization for reports and issues to ensure
dashboard queries work reliably across all city name variations.

CRITICAL: This is a deterministic function - same input always produces
same output. Used for both aggregation clustering and dashboard queries.
"""

import logging
import re
from typing import Dict, List, Optional

from app.utils.geocoding import normalize_city_name, derive_city_from_locality

logger = logging.getLogger(__name__)


def extract_city_from_address(address: Optional[str]) -> Optional[str]:
    """
    Extract city name from a resolved address string.
    
    Handles common address formats:
    - "Street, City, State, Country"
    - "Area, City"
    - "City, State"
    
    Args:
        address: Full address string (may be None)
    
    Returns:
        Extracted city name or None if cannot extract
    """
    if not address or not isinstance(address, str):
        return None
    
    address = address.strip()
    if not address:
        return None
    
    # Common Indian address patterns
    # Format: "Street, Area, City, State, PIN, Country"
    # Try to extract city (usually 2nd or 3rd from end)
    parts = [p.strip() for p in address.split(',')]
    
    # Known city names to look for
    known_cities = [
        "pune", "mumbai", "nashik", "nagpur", "aurangabad",
        "delhi", "bangalore", "hyderabad", "chennai", "kolkata",
        "ahmedabad", "surat", "jaipur", "lucknow", "kanpur",
        "ranchi", "patna", "bhopal", "indore", "raipur",
        "jamshedpur", "dhanbad", "bokaro", "gaya", "muzaffarpur"
    ]
    
    # Check each part for known city
    for part in parts:
        part_lower = part.lower()
        for city in known_cities:
            if city in part_lower:
                # Return the part with proper capitalization
                return part.strip()
    
    # If no known city found, try heuristic:
    # City is usually 2nd or 3rd from end (before state/country)
    if len(parts) >= 2:
        # Try 2nd from end (before state)
        potential_city = parts[-2].strip()
        if len(potential_city) > 2 and potential_city.lower() not in ["india", "state"]:
            return potential_city
    
    if len(parts) >= 3:
        # Try 3rd from end
        potential_city = parts[-3].strip()
        if len(potential_city) > 2 and potential_city.lower() not in ["india", "state"]:
            return potential_city
    
    return None


def generate_city_variants(canonical_city: str) -> List[str]:
    """
    Generate common variants of a city name for flexible querying.
    
    Examples:
    - "Ranchi" → ["Ranchi", "Ranchi, Jharkhand", "Jharkhand"]
    - "Pune" → ["Pune", "Pune, Maharashtra", "Maharashtra"]
    
    Args:
        canonical_city: The canonical city name
    
    Returns:
        List of city variants (always includes canonical_city)
    """
    if not canonical_city or canonical_city == "UNKNOWN":
        return ["UNKNOWN"]
    
    variants = [canonical_city]  # Always include canonical
    
    # Common state mappings for major Indian cities
    city_state_map = {
        "ranchi": "Jharkhand",
        "pune": "Maharashtra",
        "mumbai": "Maharashtra",
        "nashik": "Maharashtra",
        "nagpur": "Maharashtra",
        "aurangabad": "Maharashtra",
        "delhi": "Delhi",
        "bangalore": "Karnataka",
        "hyderabad": "Telangana",
        "chennai": "Tamil Nadu",
        "kolkata": "West Bengal",
        "ahmedabad": "Gujarat",
        "surat": "Gujarat",
        "jaipur": "Rajasthan",
        "lucknow": "Uttar Pradesh",
        "kanpur": "Uttar Pradesh",
        "patna": "Bihar",
        "bhopal": "Madhya Pradesh",
        "indore": "Madhya Pradesh",
        "raipur": "Chhattisgarh",
    }
    
    city_lower = canonical_city.lower()
    if city_lower in city_state_map:
        state = city_state_map[city_lower]
        variants.append(f"{canonical_city}, {state}")
        variants.append(state)
    
    # Add common variations
    variants.append("India")  # Fallback for country-level queries
    
    # Remove duplicates while preserving order
    seen = set()
    unique_variants = []
    for variant in variants:
        variant_lower = variant.lower()
        if variant_lower not in seen:
            seen.add(variant_lower)
            unique_variants.append(variant)
    
    return unique_variants


def normalize_city(report: Dict) -> Dict:
    """
    Normalize city from a report with priority-based resolution.
    
    PRODUCTION-GRADE: Handles all city name variations and edge cases.
    
    Priority order:
    1. resolved_city (from geocoding - highest priority)
    2. city field from report
    3. Extract city from resolved_address
    4. Derive from locality
    5. Fallback → "UNKNOWN"
    
    Args:
        report: Report dictionary with city-related fields
    
    Returns:
        Dict with:
        {
            "canonical_city": str,  # Normalized, title-case city name
            "variants": List[str]    # Array of city name variants for flexible querying
        }
    
    Example:
        normalize_city({
            "city": "ranchi",
            "resolved_city": "Ranchi, Jharkhand",
            "resolved_address": "Main Road, Ranchi, Jharkhand, India"
        })
        → {
            "canonical_city": "Ranchi",
            "variants": ["Ranchi", "Ranchi, Jharkhand", "Jharkhand", "India"]
        }
    """
    # Priority 1: resolved_city (from geocoding - most accurate)
    resolved_city = report.get("resolved_city")
    if resolved_city and isinstance(resolved_city, str) and resolved_city.strip():
        normalized = normalize_city_name(resolved_city.strip())
        if normalized != "UNKNOWN":
            variants = generate_city_variants(normalized)
            return {
                "canonical_city": normalized,
                "variants": variants
            }
    
    # Priority 2: city field from report
    city = report.get("city")
    if city and isinstance(city, str) and city.strip():
        normalized = normalize_city_name(city.strip())
        if normalized != "UNKNOWN":
            variants = generate_city_variants(normalized)
            return {
                "canonical_city": normalized,
                "variants": variants
            }
    
    # Priority 3: Extract city from resolved_address
    resolved_address = report.get("resolved_address")
    if resolved_address:
        extracted_city = extract_city_from_address(resolved_address)
        if extracted_city:
            normalized = normalize_city_name(extracted_city)
            if normalized != "UNKNOWN":
                variants = generate_city_variants(normalized)
                return {
                    "canonical_city": normalized,
                    "variants": variants
                }
    
    # Priority 4: Derive from locality
    locality = report.get("locality")
    if locality:
        from app.utils.geocoding import derive_city_from_locality
        derived = derive_city_from_locality(locality)
        if derived != "UNKNOWN":
            normalized = normalize_city_name(derived)
            variants = generate_city_variants(normalized)
            return {
                "canonical_city": normalized,
                "variants": variants
            }
    
    # Priority 5: Fallback to UNKNOWN
    return {
        "canonical_city": "UNKNOWN",
        "variants": ["UNKNOWN"]
    }
