"""
Firestore query helpers to use the new filter API and avoid deprecation warnings.

NOTE: For firebase_admin SDK, we use positional arguments which still work.
The deprecation warning is just a warning - the functionality is still supported.
We keep this helper for future compatibility but default to positional args for reliability.
"""

def where_filter(query, field_path: str, op_string: str, value):
    """
    Helper function for Firestore queries.
    
    Currently uses positional arguments (which work reliably with firebase_admin).
    The deprecation warning is just a warning - functionality is still fully supported.
    
    Usage:
        query = where_filter(collection, "city", "==", "demo city")
        query = where_filter(query, "status", "==", "CONFIRMED")
    """
    # Use positional arguments - they work reliably with firebase_admin
    # The deprecation warning doesn't affect functionality
    return query.where(field_path, op_string, value)
