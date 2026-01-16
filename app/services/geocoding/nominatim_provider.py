import logging
from typing import Dict, Any

import requests

from .base import GeocodingProvider, empty_result

logger = logging.getLogger(__name__)


class NominatimProvider(GeocodingProvider):
    """
    OpenStreetMap Nominatim reverse-geocoding provider.

    - No API key required.
    - Uses a strict timeout (<= 3 seconds).
    - Includes a User-Agent header as required by Nominatim usage policy.
    - Never raises upstream exceptions; returns empty fields on failure.
    """

    BASE_URL = "https://nominatim.openstreetmap.org/reverse"

    def __init__(self, user_agent: str = "nagar-alert-hub/1.0"):
        self.user_agent = user_agent

    def reverse_geocode(self, latitude: float, longitude: float) -> Dict[str, str]:
        try:
            params = {
                "lat": latitude,
                "lon": longitude,
                "format": "json",
                "addressdetails": 1,
            }
            headers = {
                "User-Agent": self.user_agent,
            }
            resp = requests.get(self.BASE_URL, params=params, headers=headers, timeout=3.0)
            if resp.status_code != 200:
                logger.warning(f"Nominatim reverse-geocode failed with status {resp.status_code}")
                return empty_result("nominatim")

            data: Dict[str, Any] = resp.json()
            address = data.get("address") or {}

            locality = (
                address.get("suburb")
                or address.get("neighbourhood")
                or address.get("quarter")
                or address.get("village")
                or address.get("town")
            )

            city = address.get("city") or address.get("town") or address.get("village")
            state = address.get("state")
            country = address.get("country")

            return {
                "formatted_address": data.get("display_name"),
                "locality": locality,
                "city": city,
                "state": state,
                "country": country,
                "provider": "nominatim",
            }
        except Exception as e:
            # Fail gracefully – never block or crash report creation.
            logger.warning(f"Nominatim reverse-geocode error: {e}")
            return empty_result("nominatim")

