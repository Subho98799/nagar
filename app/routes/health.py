"""
Health check endpoints.
Used for monitoring, deployment readiness checks, and basic connectivity tests.
"""

from fastapi import APIRouter, HTTPException
from app.config.firebase import get_db
from app.core.settings import settings
from datetime import datetime


router = APIRouter(prefix="/health", tags=["Health"])


@router.get("")
async def health_check():
    """
    Basic health check endpoint.
    Returns 200 if service is running.
    """
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/db")
async def database_health():
    """
    Database connectivity check.
    Attempts to connect to Firestore and perform a simple operation.
    """
    try:
        db = get_db()
        
        # Perform a lightweight operation to verify connectivity
        # We'll just check if we can access collections (doesn't need to exist)
        collections = list(db.collections())
        
        return {
            "status": "healthy",
            "database": "firestore",
            "connected": True,
            "collections_count": len(collections),
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Database connection failed: {str(e)}"
        )
