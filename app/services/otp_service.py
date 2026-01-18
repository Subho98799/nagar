"""
OTP Service - Generate, store, and verify OTPs for phone authentication.
"""

from firebase_admin import firestore
from app.config.firebase import get_db
from app.utils.firestore_helpers import where_filter
from datetime import datetime, timedelta
from typing import Optional, Dict
import random
import logging

logger = logging.getLogger(__name__)


class OTPService:
    """
    Service for OTP generation, storage, and verification.
    
    OTPs are stored in Firestore with expiration time.
    OTPs expire after 5 minutes.
    """
    
    OTP_LENGTH = 6
    OTP_EXPIRY_MINUTES = 5
    MAX_OTP_ATTEMPTS = 3  # Max verification attempts per OTP
    
    # Test phone number for development (bypasses OTP verification)
    TEST_PHONE_NUMBER = "916200015545"  # Normalized: +916200015545
    TEST_OTP = "123456"  # Fixed OTP for test number
    
    def __init__(self):
        self.db = get_db()
    
    def generate_otp(self) -> str:
        """
        Generate a random 6-digit OTP.
        
        Returns:
            6-digit OTP string
        """
        return str(random.randint(100000, 999999))
    
    def send_otp(self, phone_number: str) -> Dict:
        """
        Generate and store OTP for phone number.
        
        In production, this would send OTP via SMS service (Twilio, AWS SNS, etc.).
        For now, OTP is stored in Firestore and can be retrieved for testing.
        
        Args:
            phone_number: Phone number to send OTP to
        
        Returns:
            Dict with success status and OTP (for testing - remove in production)
        """
        try:
            # Normalize phone number (remove spaces, dashes)
            normalized_phone = self._normalize_phone(phone_number)
            
            # Check if this is the test phone number
            if normalized_phone == self.TEST_PHONE_NUMBER:
                logger.info(f"Test phone number detected: {normalized_phone}, using fixed OTP: {self.TEST_OTP}")
                otp = self.TEST_OTP
            else:
                # Generate OTP
                otp = self.generate_otp()
            
            # Calculate expiration time
            expires_at = datetime.utcnow() + timedelta(minutes=self.OTP_EXPIRY_MINUTES)
            
            # Store OTP in Firestore
            otp_ref = self.db.collection("otps").document()
            otp_data = {
                "phone_number": normalized_phone,
                "otp": otp,
                "expires_at": expires_at,
                "created_at": firestore.SERVER_TIMESTAMP,
                "verified": False,
                "attempts": 0
            }
            otp_ref.set(otp_data)
            
            # TODO: In production, send OTP via SMS service
            # For now, log it (remove in production)
            logger.info(f"OTP generated for {normalized_phone}: {otp} (expires at {expires_at})")
            
            # In production, remove OTP from response
            return {
                "success": True,
                "message": f"OTP sent to {normalized_phone}",
                "otp": otp,  # Remove this in production - only for testing
                "expires_in_minutes": self.OTP_EXPIRY_MINUTES
            }
        
        except Exception as e:
            logger.error(f"Failed to send OTP: {str(e)}", exc_info=True)
            return {
                "success": False,
                "message": f"Failed to send OTP: {str(e)}"
            }
    
    def verify_otp(self, phone_number: str, otp: str) -> Dict:
        """
        Verify OTP for phone number.
        
        Args:
            phone_number: Phone number
            otp: OTP code to verify
        
        Returns:
            Dict with verification result
        """
        try:
            normalized_phone = self._normalize_phone(phone_number)
            
            # Check if this is the test phone number - bypass verification
            if normalized_phone == self.TEST_PHONE_NUMBER:
                if otp == self.TEST_OTP:
                    logger.info(f"Test phone number OTP verified: {normalized_phone}")
                    return {
                        "success": True,
                        "message": "OTP verified successfully (test mode)",
                        "phone_number": normalized_phone
                    }
                else:
                    return {
                        "success": False,
                        "message": f"Invalid OTP. For test number, use: {self.TEST_OTP}"
                    }
            
            # Find unexpired, unverified OTP for this phone number
            otps_ref = self.db.collection("otps")
            query = where_filter(otps_ref, "phone_number", "==", normalized_phone)
            query = where_filter(query, "verified", "==", False)
            
            otp_found = False
            otp_doc = None
            otp_data = None
            
            for doc in query.stream():
                otp_data = doc.to_dict()
                expires_at = otp_data.get("expires_at")
                
                # Check if expired
                if isinstance(expires_at, datetime):
                    if expires_at < datetime.utcnow():
                        continue  # Skip expired OTPs
                
                # Check if OTP matches
                if otp_data.get("otp") == otp:
                    otp_found = True
                    otp_doc = doc
                    break
            
            if not otp_found:
                return {
                    "success": False,
                    "message": "Invalid or expired OTP"
                }
            
            # Check attempts
            attempts = otp_data.get("attempts", 0)
            if attempts >= self.MAX_OTP_ATTEMPTS:
                return {
                    "success": False,
                    "message": "Maximum verification attempts exceeded. Please request a new OTP."
                }
            
            # Mark OTP as verified
            otp_doc.reference.update({
                "verified": True,
                "verified_at": firestore.SERVER_TIMESTAMP,
                "attempts": attempts + 1
            })
            
            # Invalidate other OTPs for this phone number
            self._invalidate_other_otps(normalized_phone, otp_doc.id)
            
            logger.info(f"OTP verified successfully for {normalized_phone}")
            
            return {
                "success": True,
                "message": "OTP verified successfully",
                "phone_number": normalized_phone
            }
        
        except Exception as e:
            logger.error(f"Failed to verify OTP: {str(e)}", exc_info=True)
            return {
                "success": False,
                "message": f"Failed to verify OTP: {str(e)}"
            }
    
    def _normalize_phone(self, phone_number: str) -> str:
        """Normalize phone number (remove spaces, dashes, etc.)."""
        return phone_number.replace(" ", "").replace("-", "").replace("(", "").replace(")", "").replace("+", "")
    
    def _invalidate_other_otps(self, phone_number: str, current_otp_id: str):
        """Mark all other OTPs for this phone number as invalid."""
        try:
            otps_ref = self.db.collection("otps")
            query = where_filter(otps_ref, "phone_number", "==", phone_number)
            query = where_filter(query, "verified", "==", False)
            
            for doc in query.stream():
                if doc.id != current_otp_id:
                    doc.reference.update({"verified": True, "invalidated_at": firestore.SERVER_TIMESTAMP})
        
        except Exception as e:
            logger.warning(f"Failed to invalidate other OTPs: {e}")


# Global service instance (singleton pattern)
_otp_service = None


def get_otp_service() -> OTPService:
    """
    Get or create OTPService singleton instance.
    
    Returns:
        OTPService: The global OTP service instance
    """
    global _otp_service
    if _otp_service is None:
        _otp_service = OTPService()
    return _otp_service
