"""
User Service - Manage users in Firestore.
"""

from firebase_admin import firestore
from app.config.firebase import get_db
from app.models.user import UserCreate, UserResponse
from app.utils.firestore_helpers import where_filter
from datetime import datetime
from typing import Optional, Dict
import logging

logger = logging.getLogger(__name__)


class UserService:
    """
    Service for user management in Firestore.
    """
    
    def __init__(self):
        self.db = get_db()
    
    def get_user_by_phone(self, phone_number: str) -> Optional[Dict]:
        """
        Get user by phone number.
        
        Args:
            phone_number: Normalized phone number
        
        Returns:
            User dict with converted timestamps or None if not found
        """
        try:
            normalized_phone = self._normalize_phone(phone_number)
            users_ref = self.db.collection("users")
            query = where_filter(users_ref, "phone_number", "==", normalized_phone).limit(1)
            
            docs = list(query.stream())
            if docs:
                doc = docs[0]
                user_data = self._convert_timestamps(doc)
                user_data["id"] = doc.id
                return user_data
            
            return None
        
        except Exception as e:
            logger.error(f"Failed to get user by phone: {str(e)}")
            return None
    
    def create_user(self, phone_number: str, name: Optional[str] = None) -> Dict:
        """
        Create a new user or update existing user.
        
        Args:
            phone_number: Phone number
            name: Optional user name
        
        Returns:
            User dictionary with properly converted timestamps
        """
        try:
            normalized_phone = self._normalize_phone(phone_number)
            
            # Check if user already exists
            existing_user = self.get_user_by_phone(normalized_phone)
            
            if existing_user:
                # Update existing user
                user_id = existing_user["id"]
                user_ref = self.db.collection("users").document(user_id)
                
                update_data = {
                    "is_verified": True,
                    "last_login_at": firestore.SERVER_TIMESTAMP
                }
                
                if name:
                    update_data["name"] = name
                
                user_ref.update(update_data)
                
                # Retrieve updated user and convert timestamps
                updated_doc = user_ref.get()
                user_data = self._convert_timestamps(updated_doc)
                user_data["id"] = updated_doc.id
                
                logger.info(f"User updated: {user_id}")
                return user_data
            
            # Create new user
            user_ref = self.db.collection("users").document()
            user_data = {
                "phone_number": normalized_phone,
                "name": name,
                "is_verified": True,
                "created_at": firestore.SERVER_TIMESTAMP,
                "last_login_at": firestore.SERVER_TIMESTAMP
            }
            
            user_ref.set(user_data)
            
            # Retrieve the created document to get actual timestamps
            created_doc = user_ref.get()
            user_data = self._convert_timestamps(created_doc)
            user_data["id"] = created_doc.id
            
            logger.info(f"User created: {created_doc.id}")
            
            return user_data
        
        except Exception as e:
            logger.error(f"Failed to create/update user: {str(e)}", exc_info=True)
            raise
    
    def update_user(self, user_id: str, update_data: Dict) -> Dict:
        """
        Update user data.
        
        Args:
            user_id: Firestore document ID
            update_data: Fields to update
        
        Returns:
            Updated user dictionary with converted timestamps
        """
        try:
            user_ref = self.db.collection("users").document(user_id)
            user_ref.update(update_data)
            
            updated_doc = user_ref.get()
            user_data = self._convert_timestamps(updated_doc)
            user_data["id"] = updated_doc.id
            
            return user_data
        
        except Exception as e:
            logger.error(f"Failed to update user: {str(e)}")
            raise
    
    def _convert_timestamps(self, doc) -> Dict:
        """
        Convert Firestore document to dict with proper timestamp conversion.
        
        Converts Firestore timestamps to Python datetime objects.
        Handles both Timestamp objects and SERVER_TIMESTAMP sentinels.
        """
        user_data = doc.to_dict() if hasattr(doc, 'to_dict') else doc
        
        if not user_data:
            return {}
        
        # Convert Firestore timestamps to datetime
        # Firestore timestamps are google.cloud.firestore.Timestamp objects
        if "created_at" in user_data and user_data["created_at"] is not None:
            try:
                # Check if it's already a datetime
                if isinstance(user_data["created_at"], datetime):
                    pass  # Already a datetime, keep it
                # Check if it has to_datetime method (Firestore Timestamp)
                elif hasattr(user_data["created_at"], "to_datetime"):
                    user_data["created_at"] = user_data["created_at"].to_datetime()
                # Check if it's a Firestore Timestamp by checking for timestamp attribute
                elif hasattr(user_data["created_at"], "timestamp"):
                    # It's a Firestore Timestamp, convert it
                    user_data["created_at"] = user_data["created_at"].to_datetime()
                else:
                    # Handle SERVER_TIMESTAMP sentinel or unknown type - use current time
                    logger.warning(f"Unknown created_at type: {type(user_data['created_at'])}, using current time")
                    user_data["created_at"] = datetime.utcnow()
            except Exception as e:
                logger.warning(f"Failed to convert created_at: {e}, using current time")
                user_data["created_at"] = datetime.utcnow()
        
        if "last_login_at" in user_data and user_data["last_login_at"] is not None:
            try:
                # Check if it's already a datetime
                if isinstance(user_data["last_login_at"], datetime):
                    pass  # Already a datetime, keep it
                # Check if it has to_datetime method (Firestore Timestamp)
                elif hasattr(user_data["last_login_at"], "to_datetime"):
                    user_data["last_login_at"] = user_data["last_login_at"].to_datetime()
                # Check if it's a Firestore Timestamp by checking for timestamp attribute
                elif hasattr(user_data["last_login_at"], "timestamp"):
                    # It's a Firestore Timestamp, convert it
                    user_data["last_login_at"] = user_data["last_login_at"].to_datetime()
                else:
                    # Handle SERVER_TIMESTAMP sentinel or unknown type - use current time
                    logger.warning(f"Unknown last_login_at type: {type(user_data['last_login_at'])}, using current time")
                    user_data["last_login_at"] = datetime.utcnow()
            except Exception as e:
                logger.warning(f"Failed to convert last_login_at: {e}, using current time")
                user_data["last_login_at"] = datetime.utcnow()
        
        return user_data
    
    def _normalize_phone(self, phone_number: str) -> str:
        """Normalize phone number."""
        return phone_number.replace(" ", "").replace("-", "").replace("(", "").replace(")", "").replace("+", "")


# Global service instance (singleton pattern)
_user_service = None


def get_user_service() -> UserService:
    """
    Get or create UserService singleton instance.
    
    Returns:
        UserService: The global user service instance
    """
    global _user_service
    if _user_service is None:
        _user_service = UserService()
    return _user_service
