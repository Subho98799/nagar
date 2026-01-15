"""
Nagar Alert Hub - FastAPI Application Entry Point

A WhatsApp-first civic alert system for Tier-2 and Tier-3 cities in India.

DESIGN PRINCIPLES:
- AI assists interpretation, does NOT verify truth
- Human-in-the-loop for high-impact alerts only
- No automated authority escalation
- No prediction or forecasting
- Simple, demo-safe, hackathon-feasible
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.settings import settings
from app.config.firebase import initialize_firestore
from app.routes import health


# Initialize FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="A civic alert system for citizen-reported incidents in Indian cities",
    debug=settings.DEBUG
)


# CORS configuration - Allow frontend to access API
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Application lifecycle events
@app.on_event("startup")
async def startup_event():
    """
    Initialize services on application startup.
    Currently: Firestore connection
    """
    print(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    
    # Initialize Firestore
    try:
        initialize_firestore()
    except Exception as e:
        print(f"Warning: Firestore initialization failed: {e}")
        print("   The app will start but database operations may fail.")


@app.on_event("shutdown")
async def shutdown_event():
    """
    Cleanup on application shutdown.
    """
    print(f"Shutting down {settings.APP_NAME}")


# Include routers
app.include_router(health.router)

# Import and include report routes
from app.routes import reports
app.include_router(reports.router)

# Import and include admin routes
from app.routes import admin
app.include_router(admin.router)

# Import and include city pulse routes
from app.routes import city_pulse
app.include_router(city_pulse.router)

# Import and include map routes
from app.routes import map
app.include_router(map.router)

# Import and include auth routes
from app.routes import auth
app.include_router(auth.router)

# Import and include timeline routes
from app.routes import timeline
app.include_router(timeline.router)

# Import and include timeline routes
from app.routes import timeline
app.include_router(timeline.router)


# Root endpoint
@app.get("/")
async def root():
    """
    Root endpoint - API information.
    """
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs",
        "health": "/health",
        "city_pulse": "/city-pulse?city={city_name}"
    }
