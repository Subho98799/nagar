"""
Geocoding utilities for Phase-2: City derivation from coordinates or locality.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def derive_city_from_locality(locality: Optional[str]) -> str:
    """
    Derive city name from locality string (best-effort).
    
    This is a simple heuristic. In production, use a geocoding API
    or maintain a locality-to-city mapping database.
    
    Args:
        locality: Locality string (e.g., "Kothrud, Pune" or "MG Road, Nashik")
    
    Returns:
        City name or "UNKNOWN" if cannot be derived
    """
    if not locality or not locality.strip():
        return "UNKNOWN"
    
    # Common Indian city patterns in locality strings
    # Format: "Area, City" or "City Area"
    locality_lower = locality.lower()
    
    # Known city names (extend this list)
    known_cities = [
        "pune", "mumbai", "nashik", "nagpur", "aurangabad",
        "delhi", "bangalore", "hyderabad", "chennai", "kolkata",
        "ahmedabad", "surat", "jaipur", "lucknow", "kanpur"
    ]
    
    # Check if city name appears in locality
    for city in known_cities:
        if city in locality_lower:
            return city.capitalize()
    
    # Try to extract from comma-separated format: "Area, City"
    if ',' in locality:
        parts = [p.strip() for p in locality.split(',')]
        if len(parts) >= 2:
            # Last part might be city
            potential_city = parts[-1]
            if len(potential_city) > 2:
                return potential_city
    
    logger.warning(f"Could not derive city from locality: {locality}")
    return "UNKNOWN"


def derive_city_from_coordinates(latitude: Optional[float], longitude: Optional[float]) -> str:
    """
    Derive city name from coordinates (best-effort).
    
    In production, use reverse geocoding API (Google Maps, OpenStreetMap).
    For now, returns "UNKNOWN" as we don't have geocoding API integrated.
    
    Args:
        latitude: Latitude coordinate
        longitude: Longitude coordinate
    
    Returns:
        City name or "UNKNOWN" if coordinates are invalid
    """
    if latitude is None or longitude is None:
        return "UNKNOWN"
    
    # TODO: Integrate reverse geocoding API
    # For now, return UNKNOWN (will fallback to locality-based derivation)
    logger.info(f"Geocoding not implemented, using UNKNOWN for ({latitude}, {longitude})")
    return "UNKNOWN"


def normalize_city_name(city: Optional[str]) -> str:
    """
    Canonical city normalization function.
    
    Normalizes city names to a consistent format:
    - Trims whitespace
    - Converts to lowercase for consistent matching
    - Returns "UNKNOWN" for invalid values
    
    CRITICAL: This function ensures BOTH reports and issues use the SAME normalized city value
    for aggregation matching. Lowercase ensures "Demo City" and "demo city" match.
    
    Args:
        city: City name (may be None, empty, or invalid)
    
    Returns:
        Normalized city name (lowercase) or "UNKNOWN"
    """
    if not city or not isinstance(city, str):
        return "UNKNOWN"
    
    normalized = city.strip()
    if not normalized or normalized.upper() == "UNKNOWN":
        return "UNKNOWN"
    
    # Normalize common variations (e.g., "India" should not be a city)
    # Filter out country names and invalid values
    # NOTE: "Demo City" is a valid demo city name, do NOT filter it
    invalid_cities = {"india", "test city", ""}
    normalized_lower = normalized.lower()
    if normalized_lower in invalid_cities:
        return "UNKNOWN"
    
    # CRITICAL: Return lowercase for consistent matching
    # This ensures "Demo City" and "demo city" are treated as the same
    return normalized_lower


def ensure_city_not_null(
    city: Optional[str],
    locality: Optional[str],
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    resolved_city: Optional[str] = None
) -> str:
    """
    Ensure city field is never null using canonical normalization.
    
    Tries multiple strategies in order:
    1. Use resolved_city (from geocoding) if valid
    2. Use provided city if valid
    3. Derive from locality
    4. Derive from coordinates
    5. Fallback to "UNKNOWN"
    
    CRITICAL: This function uses normalize_city_name() to ensure consistent
    city values for aggregation matching.
    
    Args:
        city: Provided city name (may be None)
        locality: Locality string
        latitude: Optional latitude
        longitude: Optional longitude
        resolved_city: Optional resolved city from geocoding (highest priority)
    
    Returns:
        Non-null normalized city name
    """
    # Strategy 1: Use resolved_city (from geocoding) - highest priority
    if resolved_city:
        normalized = normalize_city_name(resolved_city)
        if normalized != "UNKNOWN":
            return normalized
    
    # Strategy 2: Use provided city if valid
    if city:
        normalized = normalize_city_name(city)
        if normalized != "UNKNOWN":
            return normalized
    
    # Strategy 3: Derive from locality
    if locality:
        derived = derive_city_from_locality(locality)
        if derived != "UNKNOWN":
            return normalize_city_name(derived)
    
    # Strategy 4: Derive from coordinates
    if latitude is not None and longitude is not None:
        derived = derive_city_from_coordinates(latitude, longitude)
        if derived != "UNKNOWN":
            return normalize_city_name(derived)
    
    # Strategy 5: Fallback
    return "UNKNOWN"
