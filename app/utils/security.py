"""
Security utilities for Phase-2: IP hashing and privacy protection.
"""

import hashlib
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def hash_ip_address(ip_address: Optional[str]) -> Optional[str]:
    """
    Hash IP address for privacy protection.
    
    Uses SHA-256 with a salt to prevent rainbow table attacks.
    Stores only first 16 characters (64 bits) for reasonable uniqueness.
    
    Args:
        ip_address: Raw IP address string (IPv4 or IPv6)
    
    Returns:
        Hashed IP address (first 16 chars) or None if input is None/empty
    """
    if not ip_address or not ip_address.strip():
        return None
    
    # Simple salt (in production, use environment variable)
    salt = "nagar_alert_salt_2024"
    
    try:
        # Hash IP with salt
        hashed = hashlib.sha256(f"{salt}{ip_address}".encode()).hexdigest()
        # Return first 16 characters (64 bits of entropy)
        return hashed[:16]
    except Exception as e:
        logger.warning(f"Failed to hash IP address: {e}")
        return None


def mask_ip_address(ip_address: Optional[str]) -> Optional[str]:
    """
    Mask IP address for display (privacy-friendly).
    
    For IPv4: 192.168.1.1 → 192.168.x.x
    For IPv6: 2001:0db8::1 → 2001:0db8::x
    
    Args:
        ip_address: Raw IP address string
    
    Returns:
        Masked IP address or None if input is None/empty
    """
    if not ip_address or not ip_address.strip():
        return None
    
    # IPv4 masking
    if '.' in ip_address:
        parts = ip_address.split('.')
        if len(parts) == 4:
            return f"{parts[0]}.{parts[1]}.x.x"
    
    # IPv6 masking (simplified)
    if ':' in ip_address:
        parts = ip_address.split(':')
        if len(parts) > 2:
            return ':'.join(parts[:2]) + '::x'
    
    return ip_address
