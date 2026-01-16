"""
Core settings and environment variables for Nagar Alert Hub.
Uses pydantic-settings for type-safe environment variable loading.
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    Create a .env file in the root directory to configure these.
    """
    
    # Application
    APP_NAME: str = "Nagar Alert Hub"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    
    # CORS - Frontend URLs allowed to access this API
    # Include common dev ports (3000, 5173, 5174, 5175). In production set this to your exact origin(s).
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173,http://localhost:5174,http://localhost:5175"
    
    # Firebase/Firestore
    FIREBASE_PROJECT_ID: Optional[str] = None
    FIREBASE_CREDENTIALS_PATH: Optional[str] = None  # Path to service account JSON
    # Mock DB mode for local development without Firebase credentials
    USE_MOCK_DB: bool = False
    MOCK_DB_PATH: str = "./mock_db.json"
    
    # AI Configuration (Phase-3 Part 2)
    AI_ENABLED: bool = True  # Enable/disable AI (if False, uses mock provider only)
    GEMINI_API_KEY: Optional[str] = None  # Google Gemini API key (optional)
    AI_TIMEOUT_SECONDS: float = 10.0  # AI inference timeout

    # Geocoding (Phase-4 address resolution)
    # - GEOCODING_PROVIDER: "nominatim" (default, no API key) or "google"
    # - GOOGLE_MAPS_API_KEY: optional; only used when provider is "google"
    GEOCODING_PROVIDER: str = "nominatim"
    GOOGLE_MAPS_API_KEY: Optional[str] = None
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()
