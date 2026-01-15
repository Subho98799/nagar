# Phase-2 Firestore Schema Documentation

## Final Phase-2 Report Document Structure

```json
{
  "id": "abc123",
  "description": "Large pothole on MG Road near school",
  "issue_type": "Other",                    // USER-SELECTED (source of truth)
  "city": "Nashik",                         // NEVER NULL (derived or "UNKNOWN")
  "locality": "College Road",
  "latitude": 19.9975,
  "longitude": 73.7898,
  "reporter_name": "Asha",
  "ip_address_hash": "a1b2c3d4e5f6g7h8",  // HASHED IP (privacy-protected)
  "reporter_context": "Citizen",
  "media_urls": ["https://example.com/image1.jpg"],
  "confidence": "HIGH",                     // LOW | MEDIUM | HIGH
  "confidence_reason": "Report includes media evidence (1 file(s))",
  "status": "VERIFIED",                     // UNDER_REVIEW | VERIFIED | ACTION_TAKEN | CLOSED
  "status_history": [                        // PHASE-2: Audit trail
    {
      "from": "",
      "to": "UNDER_REVIEW",
      "changed_by": "system",
      "timestamp": "2024-01-15T10:30:00Z",
      "note": "Report created"
    },
    {
      "from": "UNDER_REVIEW",
      "to": "VERIFIED",
      "changed_by": "reviewer_123",
      "timestamp": "2024-01-15T11:00:00Z",
      "note": "Reviewed and validated"
    }
  ],
  "reviewer_notes": [                       // PHASE-2: Reviewer notes array
    {
      "note": "Verified location and issue severity",
      "reviewer_id": "reviewer_123",
      "created_at": "2024-01-15T11:00:00Z"
    }
  ],
  "ai_metadata": {
    "ai_classified_category": "Traffic & Roads",  // AI-INFERRED (advisory)
    "severity_hint": "Medium",
    "keywords": ["pothole", "school", "road"],
    "summary": "Large pothole on MG Road near school",
    "override": {                          // PHASE-2: Reviewer override (optional)
      "category": "Infrastructure",
      "reviewer_id": "reviewer_123",
      "note": "Reclassified based on reviewer judgment",
      "overridden_at": "2024-01-15T11:05:00Z"
    }
  },
  "created_at": "2024-01-15T10:30:00Z",
  "reviewed_at": "2024-01-15T11:00:00Z",
  "whatsapp_alert_status": "NOT_SENT",
  "whatsapp_alert_sent_at": null
}
```

## Field Descriptions

### Core Fields
- **`id`**: Firestore document ID (auto-generated)
- **`description`**: User-provided description
- **`issue_type`**: USER-SELECTED category (source of truth)
- **`city`**: City name (NEVER NULL, defaults to "UNKNOWN" if cannot be derived)
- **`locality`**: Neighborhood/locality name
- **`latitude`**, **`longitude`**: Geographic coordinates

### Privacy & Security (Phase-2)
- **`ip_address_hash`**: Hashed IP address (SHA-256, first 16 chars)
  - Never store raw IP addresses
  - Used for duplicate detection and rate limiting
- **`reporter_name`**: Optional reporter name (may be blank)

### Confidence System (Phase-2)
- **`confidence`**: `LOW` | `MEDIUM` | `HIGH`
  - **LOW**: Single report (default)
  - **MEDIUM**: 2-3 reports from same locality within time window
  - **HIGH**: 4+ reports OR media attached
- **`confidence_reason`**: Programmatically generated explanation

### Status Workflow (Phase-2)
- **`status`**: Current workflow state
  - `UNDER_REVIEW` → `VERIFIED` → `ACTION_TAKEN` → `CLOSED`
  - No skipping states, no backward transitions
- **`status_history`**: Array of status transitions (audit trail)
  - Each entry: `{from, to, changed_by, timestamp, note}`

### Reviewer Metadata (Phase-2)
- **`reviewer_notes`**: Array of reviewer notes
  - Each note: `{note, reviewer_id, created_at}`
- **`reviewed_at`**: Timestamp of last review

### AI Metadata
- **`ai_metadata.ai_classified_category`**: AI-inferred category (advisory only)
- **`ai_metadata.override`**: Reviewer override (preserves original AI data)

## Status Transition Rules

### Allowed Transitions
```
UNDER_REVIEW → VERIFIED
VERIFIED → ACTION_TAKEN
ACTION_TAKEN → CLOSED
CLOSED → (terminal, no transitions)
```

### Validation Logic
- Same status transition is allowed (no-op)
- Invalid transitions rejected with clear error message
- All transitions logged in `status_history`

## Confidence Calculation Rules

### Rule 1: LOW (Default)
- **Condition**: Single report
- **Reason**: "Single report, awaiting corroboration"

### Rule 2: MEDIUM
- **Condition**: 2-3 reports matching:
  - Same AI-classified category
  - Same locality (exact match)
  - Within 30 minutes
- **Reason**: "Multiple similar reports detected (N reports in {locality} within 30 minutes)"

### Rule 3: HIGH
- **Condition A**: 4+ reports matching MEDIUM criteria
- **Condition B**: Report has media_urls (images/videos)
- **Reason A**: "Multiple corroborating reports detected (N reports in {locality} within 30 minutes)"
- **Reason B**: "Report includes media evidence (N file(s))"

### Rule 4: Manual Override
- Admin/reviewer can manually set HIGH confidence
- Reason: "Upgraded to HIGH by admin review"

## Data Integrity & Anti-Spam

### Duplicate Detection
- **Criteria**:
  1. Same IP hash (if available)
  2. Same locality
  3. Within 50 meters (if coordinates available)
  4. Within 15 minutes
  5. Similar description (>70% word overlap)
- **Action**: Reject duplicate with reference to existing report

### Rate Limiting
- **Limit**: 5 reports per IP hash per hour
- **Action**: Reject with rate limit message

## Reviewer Operations

### Filter Reports
- By status, confidence, locality, issue_type, city
- Returns sorted list (newest first)

### Update Status
- Validates transition using workflow engine
- Logs transition in status_history
- Returns updated report

### Add Reviewer Note
- Appends note to reviewer_notes array
- Includes reviewer_id and timestamp

### Override AI Classification
- Stores override in ai_metadata.override
- Preserves original AI data
- Includes reviewer_id and timestamp

## Migration Notes

### Existing Reports
- `city` may be null → set to "UNKNOWN" or derive from locality
- `ip_address` may exist → migrate to `ip_address_hash` (hash existing IPs)
- `status_history` may be missing → initialize with current status
- `reviewer_notes` may be missing → initialize as empty array

### Backward Compatibility
- Legacy `admin_note` field preserved (deprecated, use `reviewer_notes`)
- Old status values (`UNDER_OBSERVATION`, `CONFIRMED`, `RESOLVED`) should be migrated to Phase-2 workflow
