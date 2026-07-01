# Hybrid Recall - Quick Reference

**Version:** 7.1 | **Status:** Active | **Updated:** 2026-02-05

---

## Quick Status Check

```bash
# Verify integration is active
python ~/.claude\scripts\test-gate-hybrid-integration.py
```

**Expected:** 4/4 tests passing

---

## Key Files

| File | Purpose | Status |
|------|---------|--------|
| `.claude/hooks/gate-enforcer.py` | Integration logic | ✅ Active |
| `.claude/scripts/hybrid-recall-v7.py` | 7-layer recall engine | ✅ Active |
| `.claude/session/state.json` | Configuration flag | ✅ Enabled |
| `.claude/scripts/test-gate-hybrid-integration.py` | Test suite | ✅ Passing |

---

## Configuration

### Check Status
```bash
# View current setting
cat .claude/session/state.json | grep -A2 "use_hybrid_recall"
```

### Enable
```json
{
  "memory_system": {
    "use_hybrid_recall": true,
    "hybrid_recall_version": "7.1"
  }
}
```

### Disable (Fallback to Markdown Spec)
```json
{
  "memory_system": {
    "use_hybrid_recall": false
  }
}
```

---

## Trigger Conditions

Memory recall triggers when:
- **30+ minutes** since last user input (session start)
- **OR** manual trigger via quick command

**Automatic:** Gate enforcer detects session start and queues recall

---

## Performance Targets

| Metric | Target | Typical |
|--------|--------|---------|
| Script execution | <350ms | 180-320ms |
| Total overhead | <400ms | 190-330ms |
| Notes returned | 5 | 5 |

---

## Troubleshooting

### Fallback to Markdown Spec
**Symptom:** RECALL_MEMORY instead of RECALL_MEMORY_HYBRID

**Check:**
```bash
# Script exists?
ls .claude/scripts/hybrid-recall-v7.py

# Flag enabled?
cat .claude/session/state.json | grep use_hybrid_recall

# Test script directly
python .claude/scripts/hybrid-recall-v7.py --query "test" --format json
```

### Script Execution Error
**Symptom:** Claude reports error during recall

**Check:**
```bash
# Test script
python .claude/scripts/hybrid-recall-v7.py --query "test" --format memory-block

# Rebuild index
python .claude/scripts/build-memory-index.py

# Rebuild BM25
python .claude/scripts/bm25-indexer.py
```

### Performance Degradation
**Symptom:** Recall takes >500ms

**Check:**
```bash
# Index size (should be <5MB)
ls -lh .claude/session/memory-index.json

# Test with metrics
python .claude/scripts/hybrid-recall-v7.py --query "test" --metrics
```

---

## Manual Testing

### Trigger Recall Now
```bash
# Edit state.json - set old timestamp
"last_recall": "2026-02-05T10:00:00Z"

# Send message to Claude
# Check enforcement.todo
cat .claude/session/enforcement.todo

# Should contain RECALL_MEMORY_HYBRID
```

### View Recall Output
```bash
# Execute script directly
python .claude/scripts/hybrid-recall-v7.py \
  --query "test query" \
  --format memory-block \
  --metrics
```

---

## Integration Points

### Gate Enforcer
**File:** `.claude/hooks/gate-enforcer.py`
**Lines:** 174-190 (flag init), 1159-1191 (recall logic)

### Enforcement Queue
**File:** `.claude/session/enforcement.todo`
**Action:** `RECALL_MEMORY_HYBRID`
**Command:** `python hybrid-recall-v7.py --query "..." --format memory-block --update-state`

### State Updates
**File:** `.claude/session/state.json`
**Keys:** `memory_system.use_hybrid_recall`, `memory_system.last_recall`

---

## Rollback

### Quick Disable
```json
{
  "memory_system": {
    "use_hybrid_recall": false
  }
}
```

### Full Revert
```bash
git checkout HEAD -- .claude/hooks/gate-enforcer.py
git checkout HEAD -- .claude/session/state.json
```

---

## Documentation

**Full Guide:** `.claude/skills/meta/hybrid-recall-integration.md`
**Summary:** `.claude/session/hybrid-recall-integration-summary.md`
**Test Suite:** `.claude/scripts/test-gate-hybrid-integration.py`

---

## Next Phase

**Task #2:** Usage tracking and citation detection
- Track recall success rate
- Monitor note relevance
- Detect if notes are actually used
- Create metrics dashboard

---

**Quick Reference v1.0** | Last Updated: 2026-02-05
