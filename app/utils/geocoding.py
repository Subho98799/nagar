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


def ensure_city_not_null(
    city: Optional[str],
    locality: Optional[str],
    latitude: Optional[float] = None,
    longitude: Optional[float] = None
) -> str:
    """
    Ensure city field is never null.
    
    Tries multiple strategies:
    1. Use provided city if valid
    2. Derive from locality
    3. Derive from coordinates
    4. Fallback to "UNKNOWN"
    
    Args:
        city: Provided city name (may be None)
        locality: Locality string
        latitude: Optional latitude
        longitude: Optional longitude
    
    Returns:
        Non-null city name
    """
    # Strategy 1: Use provided city if valid
    if city and city.strip() and city.strip().upper() != "UNKNOWN":
        return city.strip()
    
    # Strategy 2: Derive from locality
    if locality:
        derived = derive_city_from_locality(locality)
        if derived != "UNKNOWN":
            return derived
    
    # Strategy 3: Derive from coordinates
    if latitude is not None and longitude is not None:
        derived = derive_city_from_coordinates(latitude, longitude)
        if derived != "UNKNOWN":
            return derived
    
    # Strategy 4: Fallback
    return "UNKNOWN"
