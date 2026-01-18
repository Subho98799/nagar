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

import sys
import traceback
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
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


# Global exception handler to catch ALL exceptions
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch all unhandled exceptions and log them with full traceback."""
    sys.stderr.write("=" * 80 + "\n")
    sys.stderr.write("🔥 GLOBAL EXCEPTION HANDLER CAUGHT EXCEPTION\n")
    sys.stderr.write(f"Path: {request.url.path}\n")
    sys.stderr.write(f"Method: {request.method}\n")
    sys.stderr.write("=" * 80 + "\n")
    sys.stderr.write(traceback.format_exc())
    sys.stderr.write("=" * 80 + "\n")
    sys.stderr.flush()
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": f"Internal server error: {str(exc)}"}
    )


# Pydantic validation error handler
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Catch Pydantic validation errors and log them."""
    sys.stderr.write("=" * 80 + "\n")
    sys.stderr.write("🔥 VALIDATION ERROR HANDLER\n")
    sys.stderr.write(f"Path: {request.url.path}\n")
    sys.stderr.write(f"Method: {request.method}\n")
    sys.stderr.write(f"Errors: {exc.errors()}\n")
    sys.stderr.write("=" * 80 + "\n")
    sys.stderr.flush()
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors(), "body": exc.body}
    )


# CORS configuration - allow only local dev frontends to call the API.
# Governance note:
# - This is intentionally narrow (no wildcard origins) to keep the backend
#   locked to local development hosts. For production, configure allowed
#   origins explicitly via settings, not "*".
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
    ],
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
        return
    
    # MOCK ISSUE SAFETY NET: Insert demo issue if collection is empty
    # This ensures the demo always has at least one issue to display
    # Run sync operations in executor to avoid blocking startup
    import asyncio
    
    def init_mock_issue_sync():
        try:
            from app.config.firebase import get_db
            from app.utils.geocoding import normalize_city_name
            from datetime import datetime, timezone
            
            db = get_db()
            if db is None:
                print("Warning: Firestore DB is None, skipping mock issue initialization")
                return
            
            # Check if issues collection is empty for Demo City
            normalized_city = normalize_city_name("Demo City")
            issues_ref = db.collection("issues")
            
            # Count existing issues for Demo City (with timeout protection)
            existing_count = 0
            try:
                # Use limit(1) to avoid loading all documents
                from app.utils.firestore_helpers import where_filter
                query = where_filter(issues_ref, "city", "==", normalized_city).limit(1)
                docs = list(query.stream())
                existing_count = len(docs)
            except Exception as e:
                print(f"[STARTUP] Query check failed: {e}, assuming empty")
                # Fallback: check all issues (with limit)
                try:
                    all_docs = list(issues_ref.limit(1).stream())
                    existing_count = len(all_docs)
                except Exception:
                    pass
            
            # If no issues exist, create a demo issue
            if existing_count == 0:
                print(f"[STARTUP] No issues found for '{normalized_city}', creating demo issue...")
                demo_issue = {
                    "title": "Traffic slowdown at Main Chowk",
                    "description": "Clustered reports indicate slow-moving traffic near Main Chowk.",
                    "issue_type": "Traffic & Roads",
                    "severity": "MEDIUM",
                    "confidence": "HIGH",
                    "latitude": 12.9718,
                    "longitude": 77.5940,
                    "city": normalized_city,  # Use normalized city
                    "locality": "Main Chowk, Station Road",
                    "report_count": 12,
                    "report_ids": [],
                    "created_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc),
                    "status": "CONFIRMED",
                    "operatorNotes": None,
                    "timeline": [
                        {
                            "id": "t1",
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "time": datetime.now(timezone.utc).strftime("%I:%M %p"),
                            "confidence": "High",
                            "description": "First reports received"
                        }
                    ]
                }
                
                # Create the issue document
                issue_ref = issues_ref.document()
                issue_ref.set(demo_issue)
                print(f"[STARTUP] Created demo issue with ID: {issue_ref.id}")
            else:
                print(f"[STARTUP] Found {existing_count} existing issue(s) for '{normalized_city}', skipping demo issue creation")
        except Exception as e:
            # Fail gracefully - don't block startup
            print(f"Warning: Failed to initialize mock issue: {e}")
            import traceback
            traceback.print_exc()
    
    # Run mock issue init in executor (non-blocking)
    loop = asyncio.get_event_loop()
    loop.run_in_executor(None, init_mock_issue_sync)


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
