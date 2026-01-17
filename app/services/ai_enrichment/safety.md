# AI Enrichment Safety Guarantees - Phase 6

## Execution Order (CRITICAL)

The AI enrichment layer executes in the following order to ensure safety:

1. **Issue Created/Updated in Firestore** ✅ (MUST succeed)
2. **Reports Linked to Issue** ✅ (MUST succeed)
3. **Confidence Recalculation** ✅ (MUST complete)
4. **AI Enrichment** (OPTIONAL, NON-BLOCKING)
   - Runs AFTER issue is saved
   - Runs AFTER confidence recalculation
   - Runs BEFORE returning to caller
5. **AI Metadata Stored** (if enrichment succeeded)
6. **Return Response**

## Safety Guarantees

### 1. Never Blocks Issue Creation/Update
- Issue is saved to Firestore BEFORE AI runs
- AI failures are caught and logged
- Issue creation/update succeeds even if AI completely fails
- AI timeout limits prevent indefinite blocking (8 seconds max)

### 2. AI Never Changes Core Fields
AI output is stored ONLY in `issues.ai_metadata` and NEVER affects:
- ❌ `confidence` (rule-based, from confidence engine)
- ❌ `confidence_score` (rule-based, from confidence engine)
- ❌ `status` (workflow state)
- ❌ `report_ids` (source of truth)
- ❌ `report_count` (source of truth)
- ❌ `confidence_timeline` (append-only, rule-based)

### 3. AI Can Be Disabled
- Set `AI_ENABLED=false` in config
- System works identically without AI
- No breaking changes
- Returns empty dict `{}` when disabled

### 4. Graceful Failure Handling
- AI failures are logged with full error details
- Failure reason stored in `ai_metadata.error`
- System continues with empty or minimal `ai_metadata`
- No retry loops that block flow
- Never raises exceptions

### 5. Hinglish Support
- Input may be English, Hindi, or Hinglish (Hindi + English mix)
- AI understands Hinglish and preserves meaning
- Output is always calm, neutral English
- Examples: "pani nhi aa rha" → "Water supply not available"

## AI Metadata Structure

### Success Case
```json
{
  "summary": "Multiple reports of water supply issues in the area",
  "keywords": ["water", "supply", "outage"],
  "severity_hint": "Medium",
  "title_suggestion": "Water Supply Issue in Downtown Area",
  "model_name": "gemini-llm-enrichment",
  "model_version": "1.0",
  "inference_timestamp": "2024-01-15T10:30:00Z"
}
```

### Failure Case
```json
{
  "error": "LLM API error: Connection timeout",
  "model_name": "llm-enrichment",
  "model_version": "1.0",
  "inference_timestamp": "2024-01-15T10:30:00Z"
}
```

### Disabled Case
```json
{}  // Empty - AI was disabled
```

## Integration Points

### Issue Creation Flow
```python
# 1. Create/update issue (MUST succeed)
issue_ref.set(issue_data)

# 2. Link reports to issue
for report_id in report_ids:
    reports_ref.document(report_id).update({"issue_id": issue_id})

# 3. Recalculate confidence (MUST complete)
recalculate_issue_confidence(issue_id)

# 4. AI enrichment (OPTIONAL, NON-BLOCKING)
from app.services.ai_enrichment import enrich_issue
ai_metadata = enrich_issue(issue_data, linked_reports)
if ai_metadata:
    issue_ref.update({"ai_metadata": ai_metadata})
```

### Critical: Never During Report Creation
- AI enrichment runs ONLY for ISSUES
- NEVER during report creation
- Reports have their own AI interpretation (separate system)

## Testing Safety

### Test 1: AI Disabled
```bash
AI_ENABLED=false
```
**Expected**: Issues created successfully, `ai_metadata` empty `{}`

### Test 2: AI Enabled but Fails
```bash
AI_ENABLED=true
GEMINI_API_KEY=invalid_key
```
**Expected**: Issues created successfully, `ai_metadata` contains error, system continues

### Test 3: AI Enabled and Works
```bash
AI_ENABLED=true
GEMINI_API_KEY=valid_key
```
**Expected**: Issues created successfully, `ai_metadata` contains full enrichment

### Test 4: AI Timeout
```bash
AI_ENABLED=true
AI_TIMEOUT_SECONDS=0.1  # Very short timeout
```
**Expected**: Issues created successfully, `ai_metadata` contains timeout error

### Test 5: Hinglish Input
```bash
# Reports with descriptions like:
# "pani nhi aa rha"
# "road pe jam hai"
```
**Expected**: AI understands Hinglish, outputs calm English summary

## Verification Checklist

- [x] Issue saved BEFORE AI runs
- [x] Confidence recalculated BEFORE AI runs
- [x] AI failures don't block issue creation/update
- [x] AI never changes core fields
- [x] AI can be disabled via config
- [x] Failure reasons logged and stored
- [x] Hinglish input supported
- [x] No breaking schema changes
- [x] Backward compatible with existing issues
- [x] Timeout protection (8 seconds max)
- [x] Never raises exceptions
