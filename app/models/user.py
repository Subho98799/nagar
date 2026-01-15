"""
User models for authentication and user management.
"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class UserCreate(BaseModel):
    """Model for creating a new user."""
    phone_number: str = Field(..., min_length=10, max_length=15, description="Phone number (with country code)")
    name: Optional[str] = Field(None, max_length=100, description="User's name (optional)")


class UserResponse(BaseModel):
    """Model for user responses."""
    id: str = Field(..., description="Firestore document ID")
    phone_number: str = Field(..., description="Phone number")
    name: Optional[str] = Field(None, description="User's name")
    is_verified: bool = Field(default=False, description="Whether phone number is verified")
    created_at: datetime = Field(..., description="When user was created")
    last_login_at: Optional[datetime] = Field(None, description="Last login timestamp")


class OTPRequest(BaseModel):
    """Request to send OTP."""
    phone_number: str = Field(..., min_length=10, max_length=15, description="Phone number to send OTP to")


class OTPVerifyRequest(BaseModel):
    """Request to verify OTP."""
    phone_number: str = Field(..., min_length=10, max_length=15, description="Phone number")
    otp: str = Field(..., min_length=4, max_length=6, description="OTP code")


class AuthResponse(BaseModel):
    """Authentication response."""
    success: bool
    message: str
    user: Optional[UserResponse] = None
    token: Optional[str] = None  # JWT token for session management
