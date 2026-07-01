# Super Power - Report Template

**Version:** 1.0
**Purpose:** Structured output format for simulation results
**Last Updated:** 2026-01-18

---

## Report Structure

All Super Power simulation reports MUST follow this structure:

1. **Header** - Run metadata (date, target, scenarios, runtime)
2. **Highlights** - Top 3-5 findings (impact + evidence + recommendation)
3. **Scoring Breakdown** - Metric tables with pass/fail indicators
4. **Gap Analysis** - What's missing or broken (root causes + fix complexity)
5. **Risks & Rewards** - Likelihood/impact matrices
6. **Execution Summary** - Performance metrics, error patterns
7. **Detailed Results by Type** - Breakdown by scenario category
8. **Memory Impact** - Learnings consolidated, wikilinks created
9. **Appendix** - Manifest location, audit trail

---

## Template (Copy This)

```markdown
# Super Power Simulation Report

**Date:** {ISO_TIMESTAMP}
**Target:** {component/feature/topic being studied}
**Scenarios:** {N executed} / {Total}
**Success Rate:** {X%}
**Runtime:** {MM:SS}

---

## 1. HIGHLIGHTS (Top 5)

### Finding 1: {Title of finding}
- **Impact:** {What this means - quantified if possible}
- **Evidence:** {Scenario results, data points}
- **Recommendation:** {Specific action to take}
- **Confidence:** {High/Medium/Low}

### Finding 2: {Title}
- **Impact:** {quantified}
- **Evidence:** {results}
- **Recommendation:** {action}
- **Confidence:** {level}

... (repeat for 3-5 findings)

---

## 2. SCORING BREAKDOWN

### Overall Metrics

| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| Total Scenarios | {N} | N/A | - |
| Pass Rate | {X%} | ≥70% | {✅/❌} |
| Average Score | {Y} | ≥75 | {✅/❌} |
| Runtime | {MM:SS} | <60min | {✅/❌} |
| Safety Violations | {count} | 0 | {✅/❌} |

**Overall Grade:** {Letter} ({Score}/100)

### Per-Scenario Results

| Scenario ID | Type | Score | Status | Notes |
|-------------|------|-------|--------|-------|
| 1 | base | 85 | ✅ | Passed all checks |
| 2 | edge_case | 60 | ⚠️ | Timeout on 2 operations |
| 3 | base | 92 | ✅ | Excellent performance |
| 4 | base | 45 | ❌ | Failed validation |

---

## 3. GAP ANALYSIS

### Gaps Detected: {count}

#### Gap 1: {Title of gap}
- **Severity:** {HIGH/MEDIUM/LOW}
- **Root Cause:** {Why this gap exists}
- **Fix Complexity:** {Simple/Moderate/Complex}
- **Affected Scenarios:** {list of scenario IDs}
- **Recommendation:** {How to fix}

#### Gap 2: {Title}
- **Severity:** {level}
- **Root Cause:** {reason}
- **Fix Complexity:** {level}
- **Affected Scenarios:** {IDs}
- **Recommendation:** {fix}

... (repeat for all gaps)

### Coverage Gaps

Scenarios NOT tested:
- {Scenario type 1} - Reason: {why skipped}
- {Scenario type 2} - Reason: {why skipped}

---

## 4. RISKS & REWARDS

### Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| {Risk description} | {High/Med/Low} | {High/Med/Low} | {How to mitigate} |
| {Risk 2} | {level} | {level} | {mitigation} |

### Rewards

| Reward | Confidence | Impact | Evidence |
|--------|-----------|--------|----------|
| {Reward description} | {High/Med/Low} | {quantified if possible} | {Scenario results} |
| {Reward 2} | {level} | {impact} | {evidence} |

---

## 5. EXECUTION SUMMARY

### Performance Metrics

- **Total Scenarios:** {N}
- **Scenarios Executed:** {M}
- **Pass:** {count} ({%})
- **Fail:** {count} ({%})
- **Timeout:** {count} ({%})
- **Average Runtime per Scenario:** {seconds}
- **Total Runtime:** {MM:SS}

### Agent Execution

| Agent ID | Assigned | Completed | Pass | Fail | Timeout |
|----------|----------|-----------|------|------|---------|
| agent_1 | 1000 | 998 | 950 | 40 | 8 |
| agent_2 | 1000 | 1000 | 975 | 25 | 0 |

### Error Patterns

| Error Type | Count | Example Scenario | Root Cause |
|------------|-------|------------------|------------|
| {error_pattern_1} | {count} | Scenario {ID} | {reason} |
| {error_pattern_2} | {count} | Scenario {ID} | {reason} |

---

## 6. DETAILED RESULTS BY TYPE

### Base Scenarios ({count} total)

Summary statistics:
- Pass rate: {X%}
- Average score: {Y}
- Typical runtime: {seconds}

### Edge Case Scenarios ({count} total)

Summary statistics:
- Pass rate: {X%}
- Average score: {Y}
- Typical runtime: {seconds}

Notable edge cases:
1. {Scenario description} - Result: {PASS/FAIL/TIMEOUT}
2. {Scenario 2} - Result: {status}

---

## 7. MEMORY IMPACT

### Learnings Consolidated: {count} notes

**Notes created:**
1. **{Type}:** {Title}
   - Path: Claude/{Folder}/{filename}.md
   - Tags: [{tag1}, {tag2}, ...]
   - Wikilinks: {count} created

2. **{Type}:** {Title}
   - Path: Claude/{Folder}/{filename}.md
   - Tags: [{tags}]
   - Wikilinks: {count}

... (repeat for all notes)

### Knowledge Graph Impact

- **Wikilinks Created:** {total}
- **Hubs Connected:** {list of hub notes}
- **Domain:** {primary domain tag}
- **Index Updated:** {total notes in vault}

---

## 8. SAFETY VALIDATION

**Total Operations:** {N}
**Allowed:** {M}
**Blocked:** {violations}
**Violation Rate:** {(violations / N) * 100}%

{if violations > 0:}
### Violation Details

| Timestamp | Tool | Reason |
|-----------|------|--------|
| {timestamp} | {tool_name} | {reason} |
| {timestamp} | {tool_name} | {reason} |

⚠️ **Action Required:** Review audit log for full details

{else:}
✅ **Zero violations** - All operations compliant with safety boundaries
{end if}

**Audit Log:** session/super_power/{YYYY-MM-DD}/audit.log

---

## APPENDIX

### File Locations

- **Scenarios:** session/super_power/{YYYY-MM-DD}/scenarios.jsonl
- **Results:** session/super_power/{YYYY-MM-DD}/results.jsonl
- **Status:** session/super_power/{YYYY-MM-DD}/status.json
- **Audit Log:** session/super_power/{YYYY-MM-DD}/audit.log
- **This Report:** session/super_power/{YYYY-MM-DD}/report.md

### Execution Timeline

- **Phase 0 (Planning):** {start} - {end} ({duration})
- **Phase 1 (Generation):** {start} - {end} ({duration})
- **Phase 2 (Execution):** {start} - {end} ({duration})
- **Phase 3 (Report):** {start} - {end} ({duration})
- **Total:** {total_duration}

### Data Sources

- **Internal:** {list of internal data sources}
- **External:** {list of WebFetch/WebSearch queries}
- **Generated:** {count of synthetic scenarios}

### Prediction Engine Insights

{if prediction_engine_used:}
**Edge Cases Suggested:** {count}

1. {edge_case_1} - Outcome: {result}
2. {edge_case_2} - Outcome: {result}

**Prediction Accuracy:** {X%} (correct predictions / total predictions)
{else:}
Prediction engine not used for this simulation.
{end if}

---

## RECOMMENDATIONS SUMMARY

1. **{Recommendation 1}** - Priority: {HIGH/MEDIUM/LOW}
   - Rationale: {why}
   - Timeline: {estimated time}
   - Owner: {team/person}

2. **{Recommendation 2}** - Priority: {level}
   - Rationale: {why}
   - Timeline: {time}
   - Owner: {owner}

... (repeat for all recommendations)

---

*Report generated by Super Power Simulation Framework v1.0*
*Session: {session_id}*
*Consolidated to memory: {YES/NO}*
```

---

## Scoring Formula (Reference)

**Weighted Scoring:**
```javascript
score = (compliance × 40%) +         // Does it meet requirements?
        (performance × 30%) +        // How fast/efficient?
        (reliability × 20%) +        // Pass rate across scenarios
        (edge_case_handling × 10%)   // Handles edge cases?
```

**Grade Thresholds:**
| Score | Grade | Status |
|-------|-------|--------|
| 90-100 | A | Excellent ✅ |
| 80-89 | B | Good ✅ |
| 70-79 | C | Acceptable ⚠️ |
| 60-69 | D | Needs Improvement ⚠️ |
| <60 | F | Failed ❌ |

**Variance Calculation (from Postmortem Analyzer):**
```javascript
const variance = {
  estimated: baseline_value,
  actual: measured_value,
  variance: actual - estimated,
  variancePercent: ((actual - estimated) / estimated) * 100,
  overrunMultiplier: actual / estimated
};
```

---

## Presentation Guidelines

**For Executive Summary (Non-Technical):**
- Lead with HIGHLIGHTS (top 3 findings)
- Include SCORING BREAKDOWN table
- Include RECOMMENDATIONS SUMMARY
- Omit: Detailed results, execution summary, appendix

**For Technical Review:**
- Include ALL sections
- Emphasize GAP ANALYSIS
- Include ERROR PATTERNS from execution summary
- Reference audit log for safety validation

**For Post-Mortem Analysis:**
- Include ALL sections
- Add timeline visualization (if applicable)
- Cross-reference with prediction engine accuracy
- Compare actual vs predicted outcomes

---

## Example: Business Use Case

```markdown
# Super Power Simulation Report

**Date:** 2026-01-18T10:30:00Z
**Target:** your CRM Stage 6 Optimization
**Scenarios:** 5 executed / 5 total
**Success Rate:** 100%
**Runtime:** 00:03:42

---

## 1. HIGHLIGHTS (Top 3)

### Finding 1: Option A (3-way split) shows 18% conversion improvement
- **Impact:** $450K additional annual revenue (estimated)
- **Evidence:** Scenario 2 scored 85 vs baseline 70, conversion rate 38% vs 32%
- **Recommendation:** Implement 3-way split by deal size ($0-50K, $50K-100K, $100K+)
- **Confidence:** High (based on 212 historical deals analyzed)

### Finding 2: 12 deals stuck >90 days identified
- **Impact:** $380K pipeline at risk
- **Evidence:** Edge case scenario 4 identified stall patterns
- **Recommendation:** Create escalation process at 60-day mark
- **Confidence:** High (7 due to rep unresponsiveness, 5 due to customer delays)

### Finding 3: Cycling pattern detected in 5 deals
- **Impact:** Sales efficiency degradation (average 15 days wasted per cycle)
- **Evidence:** Edge case scenario 5 found Stage 6 → Stage 5 → repeat pattern
- **Recommendation:** Add qualification gate before Stage 6 entry
- **Confidence:** Medium (small sample size, but clear pattern)

---

## 2. SCORING BREAKDOWN

### Overall Metrics

| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| Total Scenarios | 5 | N/A | - |
| Pass Rate | 100% | ≥70% | ✅ |
| Average Score | 76 | ≥75 | ✅ |
| Runtime | 00:03:42 | <60min | ✅ |
| Safety Violations | 0 | 0 | ✅ |

**Overall Grade:** B (80/100)

### Per-Scenario Results

| Scenario ID | Type | Score | Status | Notes |
|-------------|------|-------|--------|-------|
| 1 | base | 70 | ⚠️ | Current config (baseline) |
| 2 | base | 85 | ✅ | Option A - Best performer |
| 3 | base | 80 | ✅ | Option B - Good alternative |
| 4 | edge_case | 60 | ⚠️ | Stuck deals analysis |
| 5 | edge_case | 65 | ⚠️ | Cycling pattern detection |

---

## 3. GAP ANALYSIS

### Gaps Detected: 3

#### Gap 1: No escalation process for stuck deals
- **Severity:** HIGH
- **Root Cause:** No automated alerts when deals remain in Stage 6 >60 days
- **Fix Complexity:** Simple (workflow automation)
- **Affected Scenarios:** Scenario 4
- **Recommendation:** Implement your CRM workflow with 60-day trigger

#### Gap 2: No qualification gate before Stage 6
- **Severity:** MEDIUM
- **Root Cause:** Sales reps can advance deals without meeting criteria
- **Fix Complexity:** Moderate (process change + training)
- **Affected Scenarios:** Scenario 5
- **Recommendation:** Add checklist requirement before stage progression

#### Gap 3: Stage naming doesn't reflect deal complexity
- **Severity:** LOW
- **Root Cause:** Single "Stage 6" name for all deal sizes
- **Fix Complexity:** Simple (CRM config)
- **Affected Scenarios:** Scenario 1, 2
- **Recommendation:** Rename to "Stage 6A/6B/6C" per deal size

### Coverage Gaps

Scenarios NOT tested:
- 4-way split - Reason: Too granular for current deal volume
- Stage renaming impact - Reason: Requires user feedback data (not available)

---

## 4. RISKS & REWARDS

### Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Sales team rejects complexity | Medium | High | Gradual rollout with training |
| CRM confusion during transition | High | Medium | Clear communication, documentation |
| Stage split creates bottlenecks | Low | Medium | Monitor conversion rates weekly |

### Rewards

| Reward | Confidence | Impact | Evidence |
|--------|-----------|--------|----------|
| 18% conversion improvement | High | $450K/year | Scenario 2 results |
| Reduce stuck deals by 50% | Medium | $190K recovered | Scenario 4 analysis |
| Clearer pipeline visibility | High | Qualitative improvement | Scenarios 2-3 |

---

## 7. MEMORY IMPACT

### Learnings Consolidated: 2 notes

**Notes created:**
1. **Pattern:** your CRM Stage Bottleneck Detection
   - Path: Claude/Patterns/your CRM-Stage-Bottleneck-Detection.md
   - Tags: [patterns, crm]
   - Wikilinks: 4 created ([[HUB - your CRM Integration]], [[Decision - Stage Optimization]], ...)

2. **Decision:** Stage Optimization via Deal Size Segmentation
   - Path: Claude/Decisions/Stage-Optimization-Deal-Size-Segmentation.md
   - Tags: [decisions, crm]
   - Wikilinks: 3 created

### Knowledge Graph Impact

- **Wikilinks Created:** 7 total
- **Hubs Connected:** HUB - your CRM Integration
- **Domain:** crm
- **Index Updated:** 40 total notes

---

*Report generated by Super Power Simulation Framework v1.0*
*Session: protocol-enforcement-v5*
*Consolidated to memory: YES*
```

---

*Super Power Report Template v1.0 | Structured, scannable, actionable*
