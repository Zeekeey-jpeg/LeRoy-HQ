# Hybrid Recall v7.1 - Gradual Rollout Guide

**Status:** Phase 6 - Gradual Rollout with Monitoring
**Version:** 7.1
**Date:** 2026-02-05
**Author:** @builder

## Overview

This guide documents the gradual rollout process for migrating from markdown-based memory recall specification to the executable hybrid-recall-v7.py script.

**Migration Path:** Markdown Spec (2000+ lines) → Hybrid Recall v7.1 (626 lines Python)

**Performance Target:** <350ms recall time (consistent)

---

## Rollout Phases

### Phase 0: Pre-Rollout (Current State)

**Configuration:**
```json
{
  "use_hybrid_recall": true,
  "hybrid_recall_testing": false,
  "hybrid_recall_confidence": 1.0,
  "rollout_phase": "pre-rollout"
}
```

**Status:** Hybrid recall is active but rollout monitoring not yet enabled.

**Actions:**
- System currently using hybrid recall by default
- No parallel testing or gradual rollout active
- Monitoring infrastructure deployed but dormant

---

### Week 1: Parallel Execution Testing (Days 1-7)

**Goal:** Run both markdown spec AND hybrid script in parallel, compare outputs, establish baseline.

**Configuration:**
```json
{
  "use_hybrid_recall": true,
  "hybrid_recall_testing": true,
  "hybrid_recall_confidence": 0.0,
  "rollout_phase": "week1_parallel",
  "rollout_start_date": "2026-02-06",
  "parallel_execution_log": ".claude/session/parallel-execution-log.jsonl"
}
```

**Behavior:**
- Every memory recall executes BOTH methods
- Results are compared and logged to `parallel-execution-log.jsonl`
- Markdown spec results are used (hybrid is for comparison only)
- No impact on production behavior

**Success Criteria:**
- Average overlap >80%
- Hybrid consistently faster than markdown spec
- No errors in hybrid execution
- At least 20 parallel executions logged

**Monitoring:**
```bash
# Check parallel testing status
python scripts/parallel-execution-logger.py analyze

# View health metrics
python scripts/memory-system-health.py

# Morning routine includes automatic health check
```

**Expected Output:**
```json
{
  "executions": 25,
  "avg_overlap_percentage": 85.2,
  "avg_speedup": 1.3,
  "avg_markdown_time_ms": 320,
  "avg_hybrid_time_ms": 245
}
```

**Transition to Week 2:**
Manual update to state.json after 7 days if success criteria met:

```python
state["memory_system"]["rollout_phase"] = "week2_50pct"
state["memory_system"]["hybrid_recall_testing"] = False
state["memory_system"]["hybrid_recall_confidence"] = 0.5
state["memory_system"]["rollout_start_date"] = "2026-02-13"
```

---

### Week 2: 50% Gradual Rollout (Days 8-14)

**Goal:** Use hybrid recall for 50% of memory recalls, markdown spec for other 50%.

**Configuration:**
```json
{
  "use_hybrid_recall": true,
  "hybrid_recall_testing": false,
  "hybrid_recall_confidence": 0.5,
  "rollout_phase": "week2_50pct",
  "rollout_start_date": "2026-02-13"
}
```

**Behavior:**
- Random selection: 50% chance of hybrid, 50% chance of markdown spec
- Uses Python's `random.random() < 0.5` for selection
- Both methods produce same `[MEMORY]` block format
- User sees no difference

**Success Criteria:**
- Zero errors from hybrid recall executions
- Average recall time <350ms for hybrid
- No user-reported issues
- At least 30 hybrid executions during week

**Monitoring:**
```bash
# Check production metrics
python scripts/memory-system-health.py

# Morning routine shows:
# - Error rate (target: 0%)
# - Avg recall time (target: <350ms)
# - Execution count
```

**Rollback Procedure:**
If errors occur, immediately revert:

```python
state["memory_system"]["rollout_phase"] = "week1_parallel"
state["memory_system"]["hybrid_recall_testing"] = True
state["memory_system"]["hybrid_recall_confidence"] = 0.0
```

**Transition to Week 3:**
Manual update to state.json after 7 days if success criteria met:

```python
state["memory_system"]["rollout_phase"] = "week3_full"
state["memory_system"]["hybrid_recall_confidence"] = 1.0
```

---

### Week 3: 100% Migration (Days 15-21)

**Goal:** Complete migration to hybrid recall, deprecate markdown spec.

**Configuration:**
```json
{
  "use_hybrid_recall": true,
  "hybrid_recall_testing": false,
  "hybrid_recall_confidence": 1.0,
  "rollout_phase": "week3_full",
  "markdown_spec_deprecated": true
}
```

**Behavior:**
- 100% of memory recalls use hybrid script
- Markdown spec remains available for emergency fallback
- Monitoring continues for stability verification

**Success Criteria:**
- Zero errors for 7 consecutive days
- Average recall time consistently <350ms
- At least 50 executions during week
- No user-reported issues

**Monitoring:**
Same as Week 2, with focus on stability and consistency.

**Final Transition:**
After successful Week 3:

```python
state["memory_system"]["rollout_phase"] = "complete"
state["memory_system"]["markdown_spec_deprecated"] = True
```

**Documentation Update:**
Create `memory-recall-v7-migration.md` documenting:
- Migration completion date
- Performance improvements achieved
- Lessons learned
- Rollback procedure (for future reference)

---

## Architecture

### Gate Enforcer Integration

**File:** `hooks/gate-enforcer.py` (lines 1159-1229)

**Logic:**

1. **Week 1 (Parallel Testing):**
   - Detect `hybrid_recall_testing == true`
   - Execute both markdown spec AND hybrid script
   - Compare results and log to `parallel-execution-log.jsonl`
   - Use markdown spec results for actual recall

2. **Week 2-3 (Gradual Rollout):**
   - Use `random.random() < confidence` for selection
   - Execute selected method
   - Log execution for monitoring

3. **Fallback:**
   - If hybrid script missing or disabled: use markdown spec
   - If errors occur: automatic fallback to markdown spec

### Monitoring Scripts

**1. parallel-execution-logger.py**
- Logs comparison data during Week 1
- Analyzes overlap percentage and speedup
- Provides health metrics for morning routine

**2. memory-system-health.py**
- Reads state.json for rollout status
- Calls parallel-execution-logger for Week 1 metrics
- Formats output for morning routine
- Determines health status based on phase

### Morning Routine Integration

**File:** `skills/routines/morning.md`

**Section:** "MEMORY SYSTEM HEALTH (Hybrid Recall v7.1 Rollout Monitoring)"

**Execution:**
```bash
python scripts/memory-system-health.py
```

**Output:** Health status, performance metrics, phase progress, next milestone

---

## Manual Operations

### Start Week 1 Testing

```bash
# Update state.json
python -c "
import json
with open('.claude/session/state.json') as f:
    state = json.load(f)

state['memory_system']['hybrid_recall_testing'] = True
state['memory_system']['rollout_phase'] = 'week1_parallel'
state['memory_system']['rollout_start_date'] = '2026-02-06'

with open('.claude/session/state.json', 'w') as f:
    json.dump(state, f, indent=2)
"

# Verify
python scripts/memory-system-health.py
```

### Advance to Week 2

```bash
# Check Week 1 results first
python scripts/parallel-execution-logger.py analyze

# If success criteria met:
python -c "
import json
with open('.claude/session/state.json') as f:
    state = json.load(f)

state['memory_system']['rollout_phase'] = 'week2_50pct'
state['memory_system']['hybrid_recall_testing'] = False
state['memory_system']['hybrid_recall_confidence'] = 0.5
state['memory_system']['rollout_start_date'] = '2026-02-13'

with open('.claude/session/state.json', 'w') as f:
    json.dump(state, f, indent=2)
"
```

### Advance to Week 3

```bash
# Check Week 2 results first
python scripts/memory-system-health.py --json

# If success criteria met:
python -c "
import json
with open('.claude/session/state.json') as f:
    state = json.load(f)

state['memory_system']['rollout_phase'] = 'week3_full'
state['memory_system']['hybrid_recall_confidence'] = 1.0

with open('.claude/session/state.json', 'w') as f:
    json.dump(state, f, indent=2)
"
```

### Emergency Rollback

```bash
# Immediate rollback to markdown spec
python -c "
import json
with open('.claude/session/state.json') as f:
    state = json.load(f)

state['memory_system']['use_hybrid_recall'] = False
state['memory_system']['rollout_phase'] = 'rollback'

with open('.claude/session/state.json', 'w') as f:
    json.dump(state, f, indent=2)
"

# Verify fallback
# Next memory recall will use markdown spec
```

---

## Testing

### Test Parallel Execution Mode

```bash
# Enable testing mode
python -c "
import json
with open('.claude/session/state.json') as f:
    state = json.load(f)
state['memory_system']['hybrid_recall_testing'] = True
state['memory_system']['rollout_phase'] = 'week1_parallel'
with open('.claude/session/state.json', 'w') as f:
    json.dump(state, f, indent=2)
"

# Trigger a session that invokes memory recall
# (wait for next session start or manual trigger)

# Check log
python scripts/parallel-execution-logger.py analyze
```

### Test Morning Health Check

```bash
# Run health check
python scripts/memory-system-health.py

# Expected output: Phase status, metrics, next milestone

# Run with JSON output
python scripts/memory-system-health.py --json
```

### Test Gate Enforcer Integration

```bash
# Check current recall mode
grep -A 20 "must_recall_memory" hooks/gate-enforcer.py | head -30

# Verify random selection works (Week 2)
python -c "
import json
with open('.claude/session/state.json') as f:
    state = json.load(f)
state['memory_system']['rollout_phase'] = 'week2_50pct'
state['memory_system']['hybrid_recall_confidence'] = 0.5
with open('.claude/session/state.json', 'w') as f:
    json.dump(state, f, indent=2)
"

# Trigger multiple sessions and observe which method is used
```

---

## Success Metrics

### Week 1 Targets
- ✅ Parallel executions: >20
- ✅ Average overlap: >80%
- ✅ Hybrid faster: >1.2x speedup
- ✅ Error rate: 0%

### Week 2 Targets
- ✅ Hybrid executions: >30
- ✅ Error rate: 0%
- ✅ Avg recall time: <350ms
- ✅ Zero user complaints

### Week 3 Targets
- ✅ Total executions: >50
- ✅ Error rate: 0%
- ✅ Avg recall time: <350ms
- ✅ 7 consecutive error-free days

---

## Troubleshooting

### Issue: Low overlap (<70%)

**Diagnosis:**
```bash
python scripts/parallel-execution-logger.py analyze
# Check min_overlap and divergent queries
```

**Actions:**
1. Review queries with low overlap
2. Check if hybrid script filtering differs from markdown spec
3. Investigate BM25 scoring vs manual filtering
4. Consider adjusting scoring weights in hybrid-recall-v7.py

### Issue: High recall time (>500ms)

**Diagnosis:**
```bash
python scripts/memory-system-health.py --json
# Check avg_time_ms and performance_status
```

**Actions:**
1. Check memory index size (session/memory-index.json)
2. Verify embeddings file not corrupted
3. Test with smaller query
4. Check system load (CPU/disk)

### Issue: Errors during execution

**Diagnosis:**
```bash
# Check logs
tail -100 session/parallel-execution-log.jsonl
```

**Actions:**
1. Immediate rollback to markdown spec
2. Check Python dependencies (numpy, etc.)
3. Verify hybrid-recall-v7.py syntax
4. Test script standalone: `python scripts/hybrid-recall-v7.py --query "test"`

---

## Files Modified

### Created
- `.claude/scripts/parallel-execution-logger.py` - Parallel execution tracking
- `.claude/scripts/memory-system-health.py` - Health monitoring for morning routine
- `.claude/skills/meta/hybrid-recall-rollout-guide.md` - This guide

### Modified
- `.claude/session/state.json` - Added rollout tracking fields
- `.claude/hooks/gate-enforcer.py` - Added parallel execution and gradual rollout logic
- `.claude/skills/routines/morning.md` - Added memory system health check section

### Logs Created
- `.claude/session/parallel-execution-log.jsonl` - Week 1 parallel execution comparisons

---

## Next Steps

1. **Start Week 1:** Update state.json to enable parallel testing
2. **Monitor Daily:** Check morning routine health metrics
3. **Week 1 Completion:** Analyze parallel execution log, verify success criteria
4. **Advance to Week 2:** Update confidence to 50% if criteria met
5. **Week 2 Monitoring:** Track error rate and performance
6. **Advance to Week 3:** Update confidence to 100% if criteria met
7. **Week 3 Stability:** Monitor for 7 days
8. **Complete Migration:** Mark rollout complete, deprecate markdown spec

---

## Rollback Plan

**Immediate Rollback (Emergency):**
```python
state["memory_system"]["use_hybrid_recall"] = False
```

**Gradual Rollback (Issues During Week 2-3):**
```python
# Return to previous phase
state["memory_system"]["rollout_phase"] = "week1_parallel"
state["memory_system"]["hybrid_recall_testing"] = True
state["memory_system"]["hybrid_recall_confidence"] = 0.0
```

**Complete Revert:**
```python
# Disable hybrid recall entirely
state["memory_system"]["use_hybrid_recall"] = False
state["memory_system"]["rollout_phase"] = "reverted"
state["memory_system"]["markdown_spec_deprecated"] = False
```

Gate enforcer will automatically use markdown spec fallback.

---

**Status:** Ready for Week 1 activation
**Decision:** Manual activation required - update state.json to begin rollout
