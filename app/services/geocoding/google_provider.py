import logging
from typing import Dict, Any, Optional

import requests

from app.core.settings import settings
from .base import GeocodingProvider, empty_result

logger = logging.getLogger(__name__)


class GoogleMapsProvider(GeocodingProvider):
    """
    Google Maps reverse-geocoding provider.

    - FUTURE-TOGGLE ONLY: not enabled by default.
    - Used only when GEOCODING_PROVIDER=google AND GOOGLE_MAPS_API_KEY is set.
    - Same output schema as other providers.
    - Fails gracefully and never raises upstream exceptions.
    """

    BASE_URL = "https://maps.googleapis.com/maps/api/geocode/json"

    def __init__(self, api_key: Optional[str]):
        self.api_key = api_key

    def reverse_geocode(self, latitude: float, longitude: float) -> Dict[str, str]:
        if not self.api_key:
            # Key missing – silently skip.
            logger.info("GoogleMapsProvider called without API key; returning empty result.")
            return empty_result("google")

        try:
            params = {
                "latlng": f"{latitude},{longitude}",
                "key": self.api_key,
            }
            resp = requests.get(self.BASE_URL, params=params, timeout=3.0)
            if resp.status_code != 200:
                logger.warning(f"Google Maps reverse-geocode failed with status {resp.status_code}")
                return empty_result("google")

            data: Dict[str, Any] = resp.json()
            results = data.get("results") or []
            if not results:
                return empty_result("google")

            first = results[0]
            formatted_address = first.get("formatted_address")
            components = first.get("address_components") or []

            def _get_component(types):
                for c in components:
                    if any(t in c.get("types", []) for t in types):
                        return c.get("long_name")
                return None

            locality = _get_component(["sublocality", "neighborhood"])
            city = _get_component(["locality", "postal_town"])
            state = _get_component(["administrative_area_level_1"])
            country = _get_component(["country"])

            return {
                "formatted_address": formatted_address,
                "locality": locality,
                "city": city,
                "state": state,
                "country": country,
                "provider": "google",
            }
        except Exception as e:
            logger.warning(f"Google Maps reverse-geocode error: {e}")
            return empty_result("google")

