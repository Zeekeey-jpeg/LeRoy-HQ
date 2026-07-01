# Simulation Report Template

**Version:** 1.0
**Type:** Tooling (Report Template)
**Purpose:** Reusable report format for any analysis, simulation, or post-mortem
**Last Updated:** 2026-01-18

---

## Template Overview

This template provides a **universal structure** for simulation reports, analysis reports, post-mortems, and any other analytical output that requires structured findings.

**Key features:**
- 7-section structure (Header → Highlights → Scoring → Gaps → Risks → Execution → Memory)
- Scannable format (executives can read Highlights only, technical can dive deep)
- Actionable recommendations (priority, timeline, owner)
- Quantified metrics (scores, percentages, costs)
- Audit trail (data sources, file locations)

---

## When to Use This Template

**Use for:**
- Simulation studies (Super Power framework)
- Post-mortem analysis (project retrospectives)
- Performance audits (system health checks)
- Compliance reports (protocol validation)
- Enhancement studies (optimization recommendations)

**Don't use for:**
- Simple status updates (use inline text)
- Quick questions/answers (use conversation)
- File listings (use Glob output)

---

## 7-Section Structure

### Section 1: Header (Metadata)
**Purpose:** Context and scope at a glance

**Required fields:**
- Date (ISO timestamp)
- Target (component/feature/topic being studied)
- Scenarios (N executed / Total)
- Success rate (X%)
- Runtime (MM:SS or HH:MM:SS)

**Template:**
```markdown
# {Report Title}

**Date:** {ISO_TIMESTAMP}
**Target:** {component/feature/topic}
**Scenarios:** {N executed} / {Total}
**Success Rate:** {X%}
**Runtime:** {MM:SS}
```

### Section 2: Highlights (Top Findings)
**Purpose:** Executive summary - most impactful findings

**Format:** 3-5 findings, each with:
- **Title** - What was found (action-oriented)
- **Impact** - Quantified consequence (revenue, time, efficiency)
- **Evidence** - Data supporting the finding
- **Recommendation** - Specific action to take
- **Confidence** - High/Medium/Low based on data quality

**Template:**
```markdown
## 1. HIGHLIGHTS (Top {3-5})

### Finding 1: {Action-Oriented Title}
- **Impact:** {Quantified consequence - $, time, efficiency}
- **Evidence:** {Data points, scenario results, statistics}
- **Recommendation:** {Specific action with owner and timeline}
- **Confidence:** {High/Medium/Low}

### Finding 2: {Title}
- **Impact:** {consequence}
- **Evidence:** {data}
- **Recommendation:** {action}
- **Confidence:** {level}
```

**Example:**
```markdown
### Finding 1: Option A (3-way split) shows 18% conversion improvement
- **Impact:** $450K additional annual revenue (estimated)
- **Evidence:** Scenario 2 scored 85 vs baseline 70, conversion rate 38% vs 32%
- **Recommendation:** Implement 3-way split by deal size ($0-50K, $50K-100K, $100K+)
- **Confidence:** High (based on 212 historical deals analyzed)
```

### Section 3: Scoring Breakdown (Metrics)
**Purpose:** Quantitative assessment with pass/fail thresholds

**Components:**
1. **Overall Metrics** - Aggregate scores with thresholds
2. **Per-Scenario Results** - Individual scenario scores
3. **Overall Grade** - Letter grade (A-F) based on weighted formula

**Template:**
```markdown
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
```

**Scoring formula reference:**
```javascript
score = (compliance × 40%) +         // Meets requirements?
        (performance × 30%) +        // Fast/efficient?
        (reliability × 20%) +        // Pass rate?
        (edge_case_handling × 10%)   // Handles edge cases?
```

**Grade thresholds:**
| Score | Grade | Status |
|-------|-------|--------|
| 90-100 | A | Excellent ✅ |
| 80-89 | B | Good ✅ |
| 70-79 | C | Acceptable ⚠️ |
| 60-69 | D | Needs Improvement ⚠️ |
| <60 | F | Failed ❌ |

### Section 4: Gap Analysis (What's Missing)
**Purpose:** Identify deficiencies, root causes, and fix complexity

**Components:**
1. **Gaps Detected** - Count and details
2. **Coverage Gaps** - Scenarios NOT tested

**Template:**
```markdown
## 3. GAP ANALYSIS

### Gaps Detected: {count}

#### Gap 1: {Title of Gap}
- **Severity:** {HIGH/MEDIUM/LOW}
- **Root Cause:** {Why this gap exists}
- **Fix Complexity:** {Simple/Moderate/Complex}
- **Affected Scenarios:** {list of scenario IDs or components}
- **Recommendation:** {How to fix}

### Coverage Gaps

Scenarios NOT tested:
- {Scenario type 1} - Reason: {why skipped}
- {Scenario type 2} - Reason: {why skipped}
```

**Example:**
```markdown
#### Gap 1: No escalation process for stuck deals
- **Severity:** HIGH
- **Root Cause:** No automated alerts when deals remain in Stage 6 >60 days
- **Fix Complexity:** Simple (workflow automation)
- **Affected Scenarios:** Scenario 4
- **Recommendation:** Implement your CRM workflow with 60-day trigger
```

### Section 5: Risks & Rewards (Decision Matrix)
**Purpose:** Likelihood/impact analysis for decision-making

**Components:**
1. **Risks** - What could go wrong (likelihood, impact, mitigation)
2. **Rewards** - What could go right (confidence, impact, evidence)

**Template:**
```markdown
## 4. RISKS & REWARDS

### Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| {Risk description} | {High/Med/Low} | {High/Med/Low} | {How to mitigate} |

### Rewards

| Reward | Confidence | Impact | Evidence |
|--------|-----------|--------|----------|
| {Reward description} | {High/Med/Low} | {Quantified if possible} | {Data source} |
```

### Section 6: Execution Summary (Performance)
**Purpose:** Operational metrics and error patterns

**Components:**
1. **Performance Metrics** - Runtime, pass/fail counts
2. **Agent Execution** - (if agents used) Workload distribution
3. **Error Patterns** - Common failures grouped

**Template:**
```markdown
## 5. EXECUTION SUMMARY

### Performance Metrics

- **Total Scenarios:** {N}
- **Scenarios Executed:** {M}
- **Pass:** {count} ({%})
- **Fail:** {count} ({%})
- **Timeout:** {count} ({%})
- **Average Runtime per Scenario:** {seconds}
- **Total Runtime:** {MM:SS}

### Agent Execution (if applicable)

| Agent ID | Assigned | Completed | Pass | Fail | Timeout |
|----------|----------|-----------|------|------|---------|
| agent_1 | 1000 | 998 | 950 | 40 | 8 |

### Error Patterns

| Error Type | Count | Example Scenario | Root Cause |
|------------|-------|------------------|------------|
| {error_pattern_1} | {count} | Scenario {ID} | {reason} |
```

### Section 7: Memory Impact (Knowledge Graph)
**Purpose:** Track learnings consolidated to memory system

**Components:**
1. **Notes Created** - Count and paths
2. **Knowledge Graph Impact** - Wikilinks, hubs connected

**Template:**
```markdown
## 6. MEMORY IMPACT

### Learnings Consolidated: {count} notes

**Notes created:**
1. **{Type}:** {Title}
   - Path: Claude/{Folder}/{filename}.md
   - Tags: [{tag1}, {tag2}, ...]
   - Wikilinks: {count} created

### Knowledge Graph Impact

- **Wikilinks Created:** {total}
- **Hubs Connected:** {list of hub notes}
- **Domain:** {primary domain tag}
- **Index Updated:** {total notes in vault}
```

---

## Optional Sections

### Appendix (File Locations)
**Use when:** Reports reference external files (manifests, logs, raw data)

**Template:**
```markdown
## APPENDIX

### File Locations

- **Scenarios:** session/super_power/{YYYY-MM-DD}/scenarios.jsonl
- **Results:** session/super_power/{YYYY-MM-DD}/results.jsonl
- **Status:** session/super_power/{YYYY-MM-DD}/status.json
- **Audit Log:** session/super_power/{YYYY-MM-DD}/audit.log
- **This Report:** session/super_power/{YYYY-MM-DD}/report.md

### Data Sources

- **Internal:** {list of internal data sources}
- **External:** {list of WebFetch/WebSearch queries}
- **Generated:** {count of synthetic scenarios}
```

### Safety Validation (Safety-Critical Frameworks)
**Use when:** Framework has safety boundaries (Super Power, Skill Composer)

**Template:**
```markdown
## SAFETY VALIDATION

**Total Operations:** {N}
**Allowed:** {M}
**Blocked:** {violations}
**Violation Rate:** {(violations / N) * 100}%

{if violations > 0:}
### Violation Details

| Timestamp | Tool | Reason |
|-----------|------|--------|
| {timestamp} | {tool_name} | {reason} |

⚠️ **Action Required:** Review audit log for full details
{else:}
✅ **Zero violations** - All operations compliant with safety boundaries
{end if}

**Audit Log:** {path/to/audit.log}
```

### Recommendations Summary
**Use when:** Report has >5 recommendations scattered across sections

**Template:**
```markdown
## RECOMMENDATIONS SUMMARY

1. **{Recommendation 1}** - Priority: {HIGH/MEDIUM/LOW}
   - Rationale: {why}
   - Timeline: {estimated time}
   - Owner: {team/person}

2. **{Recommendation 2}** - Priority: {level}
   - Rationale: {why}
   - Timeline: {time}
   - Owner: {owner}
```

---

## Presentation Variations

### Executive Summary (Non-Technical Audience)
**Include:**
- Header
- Highlights (Top 3 only)
- Scoring Breakdown (Overall Metrics only)
- Recommendations Summary

**Omit:**
- Detailed results
- Execution summary
- Appendix
- Technical error patterns

### Technical Review (Engineers/Architects)
**Include:**
- ALL sections
- Emphasize Gap Analysis
- Include Error Patterns
- Reference audit logs
- Include Appendix with file locations

### Post-Mortem Analysis (Project Retrospective)
**Include:**
- ALL sections
- Add timeline visualization (if applicable)
- Cross-reference with prediction accuracy
- Compare actual vs predicted outcomes
- Include lessons learned in Memory Impact

---

## Examples

### Example 1: Business Enhancement Study
**Use case:** your CRM stage optimization simulation

**File:** `session/super_power/2026-01-18/report.md`

**Highlights:**
```markdown
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
```

**See full example:** `skills/meta/super-power-report-template.md` (lines 346-485)

### Example 2: Post-Mortem Analysis
**Use case:** Project overrun analysis

**Highlights:**
```markdown
## 1. HIGHLIGHTS (Top 5)

### Finding 1: Scope creep drove 47% budget overrun
- **Impact:** $127K over budget ($270K actual vs $143K estimated)
- **Evidence:** 87 change requests, 52 approved without budget adjustment
- **Recommendation:** Implement change request approval workflow with budget impact review
- **Confidence:** High (full ticket audit completed)

### Finding 2: Resource allocation mismatch (senior engineers on junior tasks)
- **Impact:** 235 hours of senior time wasted ($23.5K opportunity cost)
- **Evidence:** Time entry analysis shows senior engineers on documentation, basic installs
- **Recommendation:** Create task complexity matrix, route appropriately
- **Confidence:** High (time tracking data)
```

**See full example:** `skills/workflows/leroy/postmortem-factory.md`

### Example 3: Compliance Report
**Use case:** Protocol validation (pagination protocol check)

**Highlights:**
```markdown
## 1. HIGHLIGHTS (Top 3)

### Finding 1: 73% of MCP calls use default page size (missing data)
- **Impact:** Incomplete datasets in 11 reports, affecting decision quality
- **Evidence:** Code scan found 22 of 30 MCP calls without explicit limit parameter
- **Recommendation:** Update all MCP calls to use max page size (varies per connector, e.g. 200–1000)
- **Confidence:** High (full codebase scan)

### Finding 2: No verification step after pagination
- **Impact:** Silent data loss - reports assume completeness without checking
- **Evidence:** Zero instances of "if result_count === max_page_size" checks
- **Recommendation:** Add COUNT → FETCH → VERIFY pattern to all paginated calls
- **Confidence:** High (pattern absence confirmed)
```

---

## Integration with Other Skills

**Called by:**
- `skills/meta/super-power.md` - Phase 3 (report generation)
- `skills/workflows/leroy/postmortem-factory.md` - Post-mortem output
- `skills/meta/simulation-testing-methodology.md` - Test result reporting

**Calls:**
- `skills/meta/memory-consolidation.md` - Memory Impact section
- `skills/meta/risk-classification-framework.md` - Risks & Rewards severity levels

**See also:**
- `skills/meta/framework-documentation-standard.md` - Documentation structure
- `skills/meta/quantified-performance-targets.md` - Scoring formula design

---

## Customization Guide

### Adding Custom Sections
**Pattern:**
```markdown
## {N}. {SECTION TITLE} ({Purpose})

### {Subsection 1}
{content}

### {Subsection 2}
{content}
```

**Best practices:**
- Keep numbering sequential
- Use ALL CAPS for section titles
- Include purpose in parentheses
- Use tables for structured data

### Adapting Scoring Formula
**Default formula:**
```javascript
score = (compliance × 40%) +
        (performance × 30%) +
        (reliability × 20%) +
        (edge_case_handling × 10%)
```

**Customization:**
- Adjust weights based on domain (security: compliance 60%, performance 20%)
- Add dimensions (usability, maintainability, etc.)
- Keep total weights = 100%

**Example custom formula (security audit):**
```javascript
score = (security_compliance × 60%) +
        (vulnerability_coverage × 20%) +
        (response_time × 10%) +
        (false_positive_rate × 10%)
```

### Adding Industry-Specific Metrics
**Pattern:**
```markdown
### Domain-Specific Metrics

| Metric | Value | Industry Benchmark | Status |
|--------|-------|-------------------|--------|
| {metric_1} | {value} | {benchmark} | {✅/❌} |
```

**Examples:**
- **Sales:** Conversion rate, deal velocity, pipeline coverage
- **Engineering:** Code coverage, deployment frequency, MTTR
- **Security:** Vulnerability density, patch coverage, incident response time

---

## Success Metrics

**How to measure template effectiveness:**

| Metric | Target | Measurement |
|--------|--------|-------------|
| Time to generate report | <10 min | Time from data → final report |
| Executive understanding | >90% | Survey: "Did highlights section answer your questions?" |
| Action item clarity | >95% | % of recommendations with clear owner + timeline |
| Template reuse | 100% | % of analytical reports using this template |

---

## Version History

**v1.0 (2026-01-18):**
- Initial release
- 7-section structure
- Integration with Super Power framework
- Examples from your CRM optimization study

**Future enhancements:**
- Visualization templates (charts, graphs)
- Auto-generation from JSONL results
- Email-friendly variant (plain text)
- Interactive dashboard variant

---

*Simulation Report Template v1.0 | Universal structure | Scannable and actionable*
