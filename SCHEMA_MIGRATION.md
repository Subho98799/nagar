# Firestore Schema Migration: issue_type Field Separation

## Problem Statement

Previously, `issue_type` existed in two places:
- **Root-level `issue_type`**: User-selected value from form (e.g., "Other", "Traffic", "Water")
- **AI `issue_type` inside `ai_metadata`**: AI-inferred classification (e.g., "Traffic & Roads", "Water & Sanitation")

This created ambiguity about which field is the source of truth and caused confusion in:
- Pattern matching (confidence engine)
- Aggregation (city pulse)
- Alert generation (WhatsApp service)

## Solution

Renamed AI-inferred field to `ai_classified_category` to clearly distinguish it from user-selected `issue_type`.

### Field Naming Convention

| Field | Location | Source | Purpose |
|-------|----------|--------|---------|
| `issue_type` | Root level | User selection | User's chosen category from form dropdown |
| `ai_classified_category` | `ai_metadata` object | AI inference | AI's interpretation of the report content |

### Source of Truth Rules

1. **Root-level `issue_type`** is the PRIMARY source of truth for:
   - Displaying user's selection
   - Filtering/searching by user intent
   - Reporting what the user chose

2. **`ai_classified_category`** is ADVISORY and used for:
   - Pattern detection (confidence engine clustering)
   - Aggregation and analytics (city pulse)
   - Cross-referencing similar reports

3. **Fallback logic**: If `ai_classified_category` is missing, systems fall back to root-level `issue_type`.

## Updated Schema

### Report Document Structure

```json
{
  "id": "abc123",
  "description": "Large pothole on MG Road near school",
  "issue_type": "Other",  // ← User-selected (source of truth)
  "city": "Nashik",
  "locality": "College Road",
  "latitude": 19.9975,
  "longitude": 73.7898,
  "confidence": "MEDIUM",
  "status": "UNDER_REVIEW",
  "created_at": "2024-01-15T10:30:00Z",
  "ai_metadata": {
    "ai_classified_category": "Traffic & Roads",  // ← AI-inferred (advisory)
    "severity_hint": "Medium",
    "keywords": ["pothole", "school", "road"],
    "summary": "Large pothole on MG Road near school"
  }
}
```

## Migration Strategy

### For Existing Documents

If you have existing reports with `ai_metadata.issue_type`, you need to migrate them.

#### Option 1: One-Time Migration Script (Recommended)

Run this script once to update all existing documents:

```python
"""
Migration script to rename ai_metadata.issue_type to ai_classified_category
Run this once after deploying the code changes.
"""

from app.config.firebase import get_db
import logging

logger = logging.getLogger(__name__)

def migrate_ai_issue_type():
    """
    Migrate existing reports: rename ai_metadata.issue_type to ai_classified_category
    """
    db = get_db()
    reports_ref = db.collection("reports")
    
    migrated_count = 0
    skipped_count = 0
    
    for doc in reports_ref.stream():
        data = doc.to_dict()
        ai_metadata = data.get("ai_metadata", {})
        
        # Check if old field exists
        if "issue_type" in ai_metadata and "ai_classified_category" not in ai_metadata:
            # Migrate: copy issue_type to ai_classified_category
            ai_metadata["ai_classified_category"] = ai_metadata.pop("issue_type")
            
            # Update document
            doc_ref = reports_ref.document(doc.id)
            doc_ref.update({"ai_metadata": ai_metadata})
            
            migrated_count += 1
            logger.info(f"Migrated report {doc.id}")
        else:
            skipped_count += 1
    
    logger.info(f"Migration complete: {migrated_count} migrated, {skipped_count} skipped")
    return migrated_count, skipped_count

if __name__ == "__main__":
    migrate_ai_issue_type()
```

#### Option 2: Backward-Compatible Code (Temporary)

If you can't run migration immediately, add temporary backward compatibility:

```python
# In confidence_engine.py, city_pulse_service.py, whatsapp_service.py
# Add fallback logic:

ai_category = ai_metadata.get("ai_classified_category") or ai_metadata.get("issue_type", "")
```

**Note**: This is a temporary measure. Remove after migration is complete.

### For New Documents

New reports will automatically use `ai_classified_category`. No action needed.

## Files Changed

1. **`app/services/ai_interpreter.py`**
   - Changed return value from `issue_type` to `ai_classified_category`
   - Updated all mock logic and documentation

2. **`app/services/confidence_engine.py`**
   - Updated pattern matching to use `ai_classified_category`
   - Updated method signatures and documentation

3. **`app/services/city_pulse_service.py`**
   - Updated aggregation to use `ai_classified_category` (with fallback)

4. **`app/services/whatsapp_service.py`**
   - Updated alert generation to use `ai_classified_category` (with fallback)

5. **`app/models/report.py`**
   - Updated example schema to show new field name

## Testing Checklist

- [ ] New reports store `ai_classified_category` correctly
- [ ] Confidence engine clusters reports using `ai_classified_category`
- [ ] City pulse aggregates by `ai_classified_category` (with fallback)
- [ ] WhatsApp alerts use `ai_classified_category` (with fallback)
- [ ] Existing reports work with backward compatibility (if implemented)
- [ ] Migration script runs successfully (if used)

## Rollback Plan

If issues occur:

1. **Immediate**: Revert code changes (git revert)
2. **Data**: If migration ran, you can reverse it:
   ```python
   # Reverse migration: copy ai_classified_category back to issue_type
   ai_metadata["issue_type"] = ai_metadata.get("ai_classified_category", "")
   ```

## Future Considerations

- Consider adding validation to ensure `ai_classified_category` is always set when AI succeeds
- Consider adding a field to track which AI model/version generated the classification
- Consider adding confidence score for AI classification (separate from report confidence)
