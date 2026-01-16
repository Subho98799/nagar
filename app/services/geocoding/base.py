from abc import ABC, abstractmethod
from typing import Dict
import logging

logger = logging.getLogger(__name__)


class GeocodingProvider(ABC):
    """
    Abstract reverse-geocoding provider.

    Contract:
    - Input: latitude, longitude (floats)
    - Output: dict with well-known keys:
      {
        "formatted_address": str | None,
        "locality": str | None,
        "city": str | None,
        "state": str | None,
        "country": str | None,
        "provider": str
      }
    - MUST NEVER raise upstream exceptions.
    - MUST return empty fields on failure.
    - Implementations should enforce a network timeout <= 3 seconds.
    """

    @abstractmethod
    def reverse_geocode(self, latitude: float, longitude: float) -> Dict[str, str]:
        raise NotImplementedError


def empty_result(provider: str) -> Dict[str, str]:
    return {
        "formatted_address": None,
        "locality": None,
        "city": None,
        "state": None,
        "country": None,
        "provider": provider,
    }

