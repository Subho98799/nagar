"""
Authentication endpoints - Phone number + OTP authentication.
"""

from fastapi import APIRouter, HTTPException, status
from app.models.user import OTPRequest, OTPVerifyRequest, AuthResponse, UserResponse
from app.services.otp_service import get_otp_service
from app.services.user_service import get_user_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/send-otp")
async def send_otp(request: OTPRequest):
    """
    Send OTP to phone number.
    
    Generates a 6-digit OTP and stores it in Firestore.
    In production, this would send OTP via SMS service.
    
    Args:
        request: OTP request with phone_number
    
    Returns:
        Success message and OTP (for testing - remove OTP in production)
    """
    try:
        otp_service = get_otp_service()
        result = otp_service.send_otp(request.phone_number)
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("message", "Failed to send OTP")
            )
        
        # In production, remove "otp" from response
        return {
            "success": True,
            "message": result["message"],
            "otp": result.get("otp"),  # Remove this in production
            "expires_in_minutes": result.get("expires_in_minutes", 5)
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to send OTP: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send OTP: {str(e)}"
        )


@router.post("/verify-otp", response_model=AuthResponse)
async def verify_otp(request: OTPVerifyRequest):
    """
    Verify OTP and create/login user.
    
    If OTP is valid:
    - Creates user if doesn't exist
    - Updates last_login_at if user exists
    - Returns user data and session token
    
    Args:
        request: OTP verification request
    
    Returns:
        AuthResponse with user data and token
    """
    try:
        otp_service = get_otp_service()
        user_service = get_user_service()
        
        # Verify OTP
        verify_result = otp_service.verify_otp(request.phone_number, request.otp)
        
        if not verify_result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=verify_result.get("message", "Invalid OTP")
            )
        
        # Create or update user
        user_data = user_service.create_user(
            phone_number=request.phone_number,
            name=None  # Name can be updated later
        )
        
        # Generate simple session token (in production, use JWT)
        # For now, use a simple token based on user ID
        import hashlib
        token = hashlib.sha256(f"{user_data['id']}{user_data['phone_number']}".encode()).hexdigest()[:32]
        
        # Convert to UserResponse
        user_response = UserResponse(
            id=user_data["id"],
            phone_number=user_data["phone_number"],
            name=user_data.get("name"),
            is_verified=user_data.get("is_verified", False),
            created_at=user_data.get("created_at"),
            last_login_at=user_data.get("last_login_at")
        )
        
        logger.info(f"User authenticated: {user_data['id']} ({user_data['phone_number']})")
        
        return AuthResponse(
            success=True,
            message="OTP verified successfully",
            user=user_response,
            token=token
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to verify OTP: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to verify OTP: {str(e)}"
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user(token: str):
    """
    Get current user by session token.
    
    Args:
        token: Session token
    
    Returns:
        UserResponse: Current user data
    """
    try:
        # In production, decode JWT token to get user ID
        # For now, this is a placeholder
        # You would decode the token and get user_id, then fetch user
        
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Token-based user lookup not yet implemented"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get current user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get current user: {str(e)}"
        )
