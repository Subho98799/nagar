# Phase-3 Part 1 Implementation: System Intelligence & Escalation

## Overview

Phase-3 Part 1 adds system-level intelligence and escalation capabilities on top of Phase-1 and Phase-2, without breaking existing functionality. All additions are optional, additive, and backward-compatible.

## Components Implemented

### 1. Priority Scoring Service ✅

**File**: `app/services/priority_scoring.py`

**Purpose**: Calculate system-derived priority score (0-100) for reports.

**Factors Considered**:
1. **Confidence Level**: HIGH (+30), MEDIUM (+15), LOW (+5)
2. **Issue Type**: Safety-critical (+30), Traffic (+20), Power/Water (+15), Infrastructure (+10), Other (+5)
3. **Status**: VERIFIED (+20), UNDER_REVIEW (+15), ACTION_TAKEN (+10), CLOSED (+0)
4. **Media Presence**: +10 points if media attached
5. **Time Persistence**: +5 points per day beyond 24 hours (capped at +20)
6. **Locality Repetition**: +5 points per additional report in same locality (capped at +15)

**Key Methods**:
- `calculate_priority()`: Calculate priority for a report
- `recalculate_priority()`: Recalculate and update priority in Firestore

**Design Principles**:
- Priority is SYSTEM-DERIVED, NOT user-editable
- Priority is ADVISORY for escalation ordering
- Priority does NOT override human review
- Priority is recalculable

### 2. Escalation Engine ✅

**File**: `app/services/escalation_engine.py`

**Purpose**: Rule-based escalation system that marks reports as ESCALATION_CANDIDATE.

**Escalation Triggers**:
1. **High Priority Score**: Priority >= 70
2. **HIGH Confidence + Locality Repetition**: HIGH confidence + 5+ reports in same locality
3. **VERIFIED + Time Persistence**: VERIFIED status + open >48 hours
4. **Safety-Critical Issue Types**: Safety, Safety Concern, Public Safety

**Key Methods**:
- `evaluate_escalation()`: Evaluate if report should be escalated
- `update_escalation_flag()`: Update escalation flag and log change
- `get_escalation_candidates()`: Get all escalated reports

**Design Principles**:
- Escalation is ADVISORY, NOT authoritative
- Escalation does NOT auto-notify authorities
- Escalation only marks reports as "ESCALATION_CANDIDATE"
- Escalation is a PARALLEL signal to status workflow
- All escalation changes are logged for auditability

### 3. Schema Extensions ✅

**File**: `app/models/report.py`

**New Fields Added** (all optional, backward-compatible):
- `priority_score`: int (0-100) - System-derived priority score
- `priority_reason`: str - Explainable reason for priority
- `escalation_flag`: bool - Whether report is flagged for escalation
- `escalation_reason`: str - Reason for escalation flag
- `escalation_history`: List[Dict] - Escalation flag change history

**Backward Compatibility**:
- All new fields are optional (default to None/False/[])
- Existing reports continue to work without these fields
- No breaking changes to existing schemas

### 4. Integration with Report Service ✅

**File**: `app/services/report_service.py`

**Changes**:
- Priority scoring calculated after confidence calculation
- Escalation evaluation after priority calculation
- Both integrated into report creation flow
- Failures are logged but don't block report creation

### 5. Reviewer Endpoints ✅

**File**: `app/routes/admin.py`

**New Endpoints**:
- `POST /admin/reports/{id}/recalculate-priority`: Recalculate priority score
- `POST /admin/reports/{id}/escalate`: Approve escalation (manual)
- `POST /admin/reports/{id}/dismiss-escalation`: Dismiss escalation
- `GET /admin/escalation-candidates`: Get all escalated reports

## Priority Score Calculation Example

### Example 1: High Priority Report
```json
{
  "confidence": "HIGH",
  "issue_type": "Safety",
  "status": "VERIFIED",
  "media_urls": ["photo.jpg"],
  "priority_score": 90,
  "priority_reason": "Confidence: HIGH (+30) | Issue type: Safety (+30) | Status: VERIFIED (+20) | Media attached (+10)"
}
```

### Example 2: Medium Priority Report
```json
{
  "confidence": "MEDIUM",
  "issue_type": "Traffic",
  "status": "UNDER_REVIEW",
  "priority_score": 50,
  "priority_reason": "Confidence: MEDIUM (+15) | Issue type: Traffic (+20) | Status: UNDER_REVIEW (+15)"
}
```

### Example 3: Low Priority Report
```json
{
  "confidence": "LOW",
  "issue_type": "Other",
  "status": "UNDER_REVIEW",
  "priority_score": 25,
  "priority_reason": "Confidence: LOW (+5) | Issue type: Other (+5) | Status: UNDER_REVIEW (+15)"
}
```

## Escalation Rules Examples

### Rule 1: High Priority Score
```json
{
  "priority_score": 75,
  "escalation_flag": true,
  "escalation_reason": "High priority score (75 >= 70)"
}
```

### Rule 2: HIGH Confidence + Locality Repetition
```json
{
  "confidence": "HIGH",
  "locality": "Kothrud",
  "escalation_flag": true,
  "escalation_reason": "HIGH confidence + 6 reports in Kothrud"
}
```

### Rule 3: VERIFIED + Time Persistence
```json
{
  "status": "VERIFIED",
  "created_at": "2024-01-13T10:00:00Z",
  "escalation_flag": true,
  "escalation_reason": "VERIFIED issue persisting for 50.5 hours"
}
```

### Rule 4: Safety-Critical Issue
```json
{
  "issue_type": "Safety",
  "escalation_flag": true,
  "escalation_reason": "Safety-critical issue type: Safety"
}
```

## Escalation History Example

```json
{
  "escalation_history": [
    {
      "from_flag": false,
      "to_flag": true,
      "changed_by": "system",
      "timestamp": "2024-01-15T10:30:00Z",
      "reason": "High priority score (75 >= 70)"
    },
    {
      "from_flag": true,
      "to_flag": false,
      "changed_by": "reviewer_123",
      "timestamp": "2024-01-15T11:00:00Z",
      "reason": "Escalation dismissed by reviewer"
    }
  ]
}
```

## API Examples

### 1. Recalculate Priority
```bash
POST /admin/reports/{id}/recalculate-priority

# Response:
{
  "success": true,
  "priority_score": 75,
  "priority_reason": "Confidence: HIGH (+30) | Issue type: Safety (+30) | Status: VERIFIED (+20) | Media attached (+10)"
}
```

### 2. Approve Escalation
```bash
POST /admin/reports/{id}/escalate?reviewer_id=reviewer_123&note=Urgent safety concern

# Response:
{
  "success": true,
  "message": "Report escalated",
  "report": { ... }
}
```

### 3. Dismiss Escalation
```bash
POST /admin/reports/{id}/dismiss-escalation?reviewer_id=reviewer_123&note=Issue resolved

# Response:
{
  "success": true,
  "message": "Escalation dismissed",
  "report": { ... }
}
```

### 4. Get Escalation Candidates
```bash
GET /admin/escalation-candidates?limit=50

# Response:
{
  "success": true,
  "count": 12,
  "candidates": [
    {
      "id": "abc123",
      "priority_score": 90,
      "escalation_flag": true,
      "escalation_reason": "High priority score (90 >= 70)",
      ...
    },
    ...
  ]
}
```

## Integration Flow

### Report Creation Flow (with Phase-3)
1. Create report (Phase-1)
2. AI interpretation (Phase-1)
3. Confidence calculation (Phase-2)
4. **Priority scoring (Phase-3)** ← NEW
5. **Escalation evaluation (Phase-3)** ← NEW
6. Return complete report

### Escalation Evaluation Flow
1. Calculate priority score
2. Evaluate escalation rules
3. Update escalation_flag if triggered
4. Log change in escalation_history

## Safety & Auditability

### Escalation Logging
- All escalation flag changes logged in `escalation_history`
- Includes: from_flag, to_flag, changed_by, timestamp, reason
- Complete audit trail for compliance

### Reviewer Control
- Reviewers can approve escalation (manual override)
- Reviewers can dismiss escalation
- All reviewer actions logged with reviewer_id

### No Automatic Actions
- Escalation does NOT trigger external notifications
- Escalation does NOT change report status
- Escalation is purely advisory

## Backward Compatibility

### Existing Reports
- Reports without Phase-3 fields continue to work
- Priority defaults to None (not calculated)
- Escalation defaults to False
- No migration required

### Existing Endpoints
- All Phase-1 and Phase-2 endpoints unchanged
- New endpoints are additive only
- No breaking changes

## Configuration

### Priority Scoring Weights
- Configurable in `PriorityScoringService` class
- Easy to adjust based on production data
- Issue type weights can be customized

### Escalation Thresholds
- Configurable in `EscalationEngine` class
- Priority threshold: 70 (adjustable)
- Persistence threshold: 48 hours (adjustable)
- Locality count threshold: 5 reports (adjustable)

## Files Created/Modified

### New Files
- `app/services/priority_scoring.py` - Priority scoring service
- `app/services/escalation_engine.py` - Escalation engine
- `PHASE3_PART1_IMPLEMENTATION.md` - This documentation

### Modified Files
- `app/models/report.py` - Added Phase-3 fields (additive)
- `app/services/report_service.py` - Integrated priority/escalation
- `app/routes/admin.py` - Added escalation endpoints

## Testing Checklist

- [x] Priority scoring calculates correctly
- [x] Escalation rules trigger correctly
- [x] Escalation history logs changes
- [x] Reviewer can approve/dismiss escalation
- [x] Backward compatibility maintained
- [x] No breaking changes to existing endpoints
- [x] Failures don't block report creation

## Next Steps (Future Enhancements)

1. **Priority Score Dashboard**: Visualize priority distribution
2. **Escalation Notifications**: Optional email/SMS to reviewers
3. **Priority Score Analytics**: Track priority trends over time
4. **Custom Escalation Rules**: Allow reviewers to define custom rules
5. **Bulk Escalation Actions**: Process multiple escalations at once
