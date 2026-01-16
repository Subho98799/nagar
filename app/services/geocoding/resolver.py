import logging
from typing import Optional

from app.core.settings import settings
from .base import GeocodingProvider
from .nominatim_provider import NominatimProvider
from .google_provider import GoogleMapsProvider

logger = logging.getLogger(__name__)

_provider_instance: Optional[GeocodingProvider] = None


def get_geocoding_provider() -> GeocodingProvider:
    """
    Resolve the active geocoding provider based on settings.

    Rules:
    - Default: Nominatim (no API key required).
    - If GEOCODING_PROVIDER='google' AND GOOGLE_MAPS_API_KEY is set:
      - Try Google; if anything fails, fall back to Nominatim.
    - Never raises upstream exceptions.
    """
    global _provider_instance
    if _provider_instance is not None:
        return _provider_instance

    provider_name = (getattr(settings, "GEOCODING_PROVIDER", "nominatim") or "nominatim").lower()

    if provider_name == "google":
        api_key = getattr(settings, "GOOGLE_MAPS_API_KEY", None)
        if api_key:
            try:
                _provider_instance = GoogleMapsProvider(api_key=api_key)
                logger.info("Geocoding provider initialized: google")
                return _provider_instance
            except Exception as e:
                logger.warning(f"Failed to initialize GoogleMapsProvider: {e}. Falling back to Nominatim.")

    # Default / fallback: Nominatim
    try:
        _provider_instance = NominatimProvider()
        logger.info("Geocoding provider initialized: nominatim")
    except Exception as e:
        # In the unlikely event that even Nominatim init fails, log and still provide a no-op provider.
        logger.error(f"Failed to initialize NominatimProvider: {e}. Using no-op provider.")
        from .base import empty_result

        class NoOpProvider(GeocodingProvider):
            def reverse_geocode(self, latitude: float, longitude: float):
                return empty_result("noop")

        _provider_instance = NoOpProvider()

    return _provider_instance

