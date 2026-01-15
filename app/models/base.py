"""
Pydantic base models for request/response validation.
Placeholder for future data models (alerts, reports, etc.)

DESIGN PRINCIPLE:
- Models should reflect data structure, not business logic
- Keep models simple and focused on validation
- No ML/AI decisions embedded in models
"""

from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class BaseResponse(BaseModel):
    """
    Base response model for API responses.
    All API responses can extend this for consistency.
    """
    success: bool = True
    message: Optional[str] = None
    timestamp: datetime = datetime.utcnow()


# Placeholder: Future models will go here
# Examples (DO NOT implement yet):
# - AlertModel
# - ReportModel
# - LocationModel
# etc.
