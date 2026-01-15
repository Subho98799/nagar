"""
Firebase Firestore initialization.
Handles connection setup and provides db instance for the application.
"""

from firebase_admin import credentials, firestore, initialize_app
from app.core.settings import settings
import firebase_admin
from typing import Optional


# Global Firestore client instance
db: Optional[firestore.Client] = None


def initialize_firestore() -> firestore.Client:
    """
    Initialize Firebase Admin SDK and return Firestore client.
    
    This function:
    1. Initializes Firebase Admin SDK (only once)
    2. Returns Firestore client for database operations
    
    Returns:
        firestore.Client: Firestore database client
    """
    global db
    
    if db is not None:
        return db
    
    try:
        # If mock DB mode is enabled, use the JSON-backed mock implementation
        if getattr(settings, "USE_MOCK_DB", False):
            from app.config.mock_firestore import get_mock_db

            db = get_mock_db(getattr(settings, "MOCK_DB_PATH", "./mock_db.json"))
            print(f"Using Mock Firestore DB at: {getattr(settings, 'MOCK_DB_PATH', './mock_db.json')}")
            return db

        # Check if Firebase is already initialized
        if not firebase_admin._apps:
            if settings.FIREBASE_CREDENTIALS_PATH:
                # Production: Use service account credentials
                cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
                initialize_app(cred)
            else:
                # Development: Use application default credentials (if available)
                # Or initialize without credentials for emulator
                initialize_app()

        # Get Firestore client
        db = firestore.client()
        print(f"Firestore initialized successfully for project: {settings.FIREBASE_PROJECT_ID or 'default'}")
        return db

    except Exception as e:
        print(f"Failed to initialize Firestore: {str(e)}")
        raise


def get_db() -> firestore.Client:
    """
    Dependency function to get Firestore client.
    Can be used with FastAPI's Depends() for route injection.
    
    Returns:
        firestore.Client: Firestore database client
    """
    global db
    if db is not None:
        return db

    try:
        # Try to initialize the configured DB (mock or real)
        return initialize_firestore()
    except Exception as e:
        # If initialization fails, fall back to mock DB silently (demo-safe)
        print(f"Falling back to Mock Firestore due to init error: {e}")
        try:
            from app.config.mock_firestore import get_mock_db
            db = get_mock_db(getattr(settings, "MOCK_DB_PATH", "./mock_db.json"))
            return db
        except Exception as ex:
            # As last resort, raise the original error (should be rare)
            print(f"Mock DB fallback failed: {ex}")
            raise
