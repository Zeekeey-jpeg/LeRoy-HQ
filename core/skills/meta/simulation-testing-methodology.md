# Simulation Testing Methodology

**Version:** 1.0
**Type:** Meta-Skill (Testing Pattern)
**Purpose:** Testing approach for complex components using scenario-based simulation
**Last Updated:** 2026-01-18

---

## Methodology Overview

**What is simulation testing?**
A systematic approach to test complex components by generating and executing hundreds/thousands of scenarios in parallel.

**When to use:**
- Component has many variables/configurations
- Need to test edge cases systematically
- Manual testing is too time-consuming
- Want to measure performance at scale
- Need comprehensive coverage metrics

**When NOT to use:**
- Simple components (use unit tests instead)
- One-off validation (use manual testing)
- Time-critical fixes (simulation setup overhead not worth it)

---

## 4-Phase Methodology

### Phase 0: Planning (2-5 min)
**Goal:** Design simulation approach BEFORE generating scenarios

**Activities:**
1. **Identify target:** What are we testing?
2. **Design scenario matrix:** What variables and options?
3. **Set performance targets:** How fast should it run?
4. **Define success criteria:** What does "pass" mean?
5. **Query prediction engine:** What edge cases might exist?

**Deliverable:** Simulation plan (approved by user or team)

**Example:**
```markdown
# Simulation Plan: Pagination Protocol Compliance

## Target
All MCP paginated calls in codebase

## Scenario Matrix
| Variable | Options |
|----------|---------|
| MCP Tool | crm_tool, ticketing_tool, ... (10 tools) |
| Result Count | <max_page_size, =max_page_size, >max_page_size |

Total scenarios: 30

## Performance Targets
- Execution time: <10 min (30 scenarios, Tier 1)
- Success rate: >95%

## Success Criteria
- Pass: Uses max page size AND verifies result count
- Fail: Uses default page size OR no verification

## Edge Cases (from prediction engine)
- Empty result set (0 records)
- Exactly 1 record
```

### Phase 1: Scenario Generation (5 min)
**Goal:** Generate all test scenarios from matrix + edge cases

**Process:**
```python
# 1. Generate base scenarios from matrix
import itertools

variables = {
    "tool": ["crm_tool", "ticketing_tool", ...],
    "result_count": ["<max", "=max", ">max"]
}

base_scenarios = []
for combination in itertools.product(*variables.values()):
    scenario = {
        "id": len(base_scenarios) + 1,
        "type": "base",
        "variables": dict(zip(variables.keys(), combination))
    }
    base_scenarios.append(scenario)

# 2. Add edge cases
edge_cases = [
    {"id": 31, "type": "edge_case", "description": "Empty result set"},
    {"id": 32, "type": "edge_case", "description": "Exactly 1 record"}
]

# 3. Combine
all_scenarios = base_scenarios + edge_cases

# 4. Write to manifest
write_jsonl("session/simulation/{date}/scenarios.jsonl", all_scenarios)
```

**Output:** `session/simulation/{YYYY-MM-DD}/scenarios.jsonl`

**Validation:**
- All matrix combinations present
- Edge cases added
- Scenario IDs unique
- Total count matches plan

### Phase 2: Parallel Execution (45 min max)
**Goal:** Execute all scenarios in parallel with agent scaling

**Agent scaling:**
| Scenarios | Tier | Agents | Workload per Agent |
|-----------|------|--------|-------------------|
| 1-100 | 1 | 5 | 20 scenarios |
| 101-1K | 2 | 12 | ~85 scenarios |
| 1K-10K | 3 | 18 | ~555 scenarios |
| >10K | 4 | 20+ | ~500-1K scenarios |

**Execution pattern:**
```python
# Read scenarios
scenarios = read_jsonl("session/simulation/{date}/scenarios.jsonl")
scenario_count = len(scenarios)

# Calculate agent count
if scenario_count <= 100:
    agents = 5
elif scenario_count <= 1000:
    agents = 12
elif scenario_count <= 10000:
    agents = 18
else:
    agents = 20

# Split scenarios into chunks
chunk_size = scenario_count // agents
scenario_chunks = [scenarios[i:i+chunk_size] for i in range(0, len(scenarios), chunk_size)]

# Spawn agents in parallel
for i, chunk in enumerate(scenario_chunks):
    spawn_agent(
        agent_id=f"simulator_{i}",
        task=f"Execute scenarios {chunk[0]['id']} to {chunk[-1]['id']}",
        scenarios=chunk,
        timeout=3600  # 1 hour max
    )

# Monitor completion (polling)
while not all_agents_complete():
    check_status()
    time.sleep(5)
```

**Per-scenario execution:**
```python
def execute_scenario(scenario):
    start_time = time.time()

    try:
        # Execute test based on scenario variables
        result = run_test(scenario)

        # Determine pass/fail
        status = "PASS" if result.meets_criteria() else "FAIL"

        # Calculate score (if applicable)
        score = calculate_score(result)

    except TimeoutError:
        status = "TIMEOUT"
        result = None
        score = 0
    except Exception as e:
        status = "ERROR"
        result = None
        score = 0

    runtime = time.time() - start_time

    # Write result
    return {
        "scenario_id": scenario["id"],
        "status": status,
        "score": score,
        "findings": result.findings if result else [],
        "runtime": runtime
    }
```

**Output:** `session/simulation/{YYYY-MM-DD}/results.jsonl`

### Phase 3: Aggregation & Report (10 min)
**Goal:** Analyze results, generate structured report

**Process:**
```python
# Load results
results = read_jsonl("session/simulation/{date}/results.jsonl")

# Calculate metrics
metrics = {
    "total": len(results),
    "passed": count(results, status="PASS"),
    "failed": count(results, status="FAIL"),
    "timeout": count(results, status="TIMEOUT"),
    "error": count(results, status="ERROR"),
    "success_rate": (passed / total) * 100,
    "avg_score": mean([r["score"] for r in results if r["score"]]),
    "total_runtime": sum([r["runtime"] for r in results])
}

# Detect patterns
patterns = {
    "top_failures": group_by(results, "error").most_common(5),
    "score_distribution": histogram([r["score"] for r in results]),
    "edge_case_results": filter(results, type="edge_case")
}

# Generate insights
insights = generate_insights(results, patterns)

# Build recommendations
recommendations = build_recommendations(insights, patterns)

# Create report using template
report = generate_report_from_template(
    metrics=metrics,
    patterns=patterns,
    insights=insights,
    recommendations=recommendations
)

# Write report
write_file("session/simulation/{date}/report.md", report)
```

**Report structure:** (See `skills/tooling/simulation-report-template.md`)

---

## Testing Patterns

### Pattern 1: Compliance Testing
**Use when:** Validating adherence to protocols/standards

**Example:** Pagination protocol compliance

**Success criteria:**
- Tool uses max page size: Required
- Verifies result count = max_page_size: Required
- Paginates if needed: Required

**Scoring:**
```python
score = (uses_max_page_size × 40%) +
        (verifies_count × 40%) +
        (paginates_correctly × 20%)
```

### Pattern 2: Performance Testing
**Use when:** Measuring speed/throughput at scale

**Example:** Database query optimization

**Success criteria:**
- Query completes in <100ms: Required
- Uses index (no full table scan): Required
- Memory usage <50MB: Required

**Scoring:**
```python
score = (speed_score × 50%) +
        (efficiency_score × 30%) +
        (resource_score × 20%)
```

### Pattern 3: Edge Case Validation
**Use when:** Testing unusual or extreme scenarios

**Example:** Error handling validation

**Success criteria:**
- Catches exception: Required
- Logs error: Required
- Returns user-friendly message: Required
- System recovers gracefully: Required

**Scoring:**
```python
score = (catches_exception × 40%) +
        (logs_error × 20%) +
        (user_friendly_msg × 20%) +
        (graceful_recovery × 20%)
```

### Pattern 4: System Enhancement Study
**Use when:** Comparing alternatives (A/B testing)

**Example:** your CRM stage split analysis

**Success criteria:**
- Improved conversion rate: Desired
- Reduced time in stage: Desired
- No regression in other metrics: Required

**Scoring:**
```python
score = (conversion_improvement × 40%) +
        (time_reduction × 30%) +
        (no_regression × 30%)
```

---

## Safety Integration

**ALL simulation testing uses dual-list safety pattern:**

```python
# Before executing scenario
is_allowed, reason = validate_operation(
    tool_name=scenario.tool,
    params=scenario.params,
    audit_log_path="session/simulation/{date}/audit.log"
)

if not is_allowed:
    # Fail scenario immediately
    return {
        "scenario_id": scenario.id,
        "status": "BLOCKED",
        "reason": reason,
        "runtime": 0
    }

# Execute only if allowed
result = execute_test(scenario)
```

**Safety report included:**
```markdown
## SAFETY VALIDATION

- Total Operations: {N}
- Allowed: {M}
- Blocked: {violations}
- Violation Rate: {X%}

{if violations > 0:}
⚠️ **Violations detected** - Review audit log
{else:}
✅ **Zero violations**
{end if}

Audit Log: session/simulation/{date}/audit.log
```

---

## Integration with Frameworks

### Super Power Framework
**File:** `skills/meta/super-power.md`

**Integration points:**
- Phase 0: Uses this methodology for planning
- Phase 1: Uses scenario matrix design
- Phase 2: Uses parallel execution pattern
- Phase 3: Uses report template

**Cross-reference:**
```markdown
**See:** `skills/meta/simulation-testing-methodology.md` for detailed testing approach
```

### Skill Composer
**File:** `skills/meta/skill-composer.md`

**Integration points:**
- Step 9: Sandbox testing uses this methodology
- Generates test scenarios for each skill
- Validates skill behavior before registration

**Cross-reference:**
```markdown
**Testing approach:** See `skills/meta/simulation-testing-methodology.md`
```

---

## Examples

### Example 1: Pagination Protocol Compliance
**Goal:** Verify all MCP calls follow pagination protocol

**Phase 0 (Planning):**
```markdown
Variables:
- MCP tool: [crm_tool, ticketing_tool, ...] (10 tools)
- Result count: [<max, =max, >max]

Total scenarios: 30

Success criteria:
- Uses max page size: Required
- Verifies count = max: Required
- Paginates if needed: Required
```

**Phase 1 (Generation):**
30 scenarios generated (10 tools × 3 result count options)

**Phase 2 (Execution):**
- Agents: 5 (Tier 1)
- Workload: 6 scenarios per agent
- Runtime: 4.2 min

**Phase 3 (Report):**
```markdown
## HIGHLIGHTS

### Finding 1: 73% of MCP calls fail pagination protocol
- Impact: Incomplete datasets in 11 reports
- Evidence: 22 of 30 scenarios failed (uses default page size)
- Recommendation: Update all calls to use max page size
- Confidence: High

## SCORING BREAKDOWN

- Pass rate: 27% (8/30)
- Average score: 32/100
- Overall grade: F

## RECOMMENDATIONS

1. Update all MCP calls to use max page size (HIGH priority)
2. Add COUNT → FETCH → VERIFY pattern (HIGH priority)
3. Add linter rule to catch default page sizes (MEDIUM priority)
```

### Example 2: catalog Accessory Detection
**Goal:** Test accessory detection logic with various product types

**Phase 0 (Planning):**
```markdown
Variables:
- Product category: [Cameras, Panels, Cables, Speakers, Misc]
- Accessory type: [Mounts, Power, Connectors, None]
- Quantity: [1, 5, 100]

Total scenarios: 60

Success criteria:
- Detects required accessories: Required
- Suggests appropriate quantities: Desired
- Handles missing SKUs: Required
```

**Phase 1 (Generation):**
60 base scenarios + 3 edge cases = 63 total

**Phase 2 (Execution):**
- Agents: 5 (Tier 1)
- Workload: 12-13 scenarios per agent
- Runtime: 8.1 min

**Phase 3 (Report):**
```markdown
## HIGHLIGHTS

### Finding 1: 95% accuracy on accessory detection
- Impact: High confidence in recommendations
- Evidence: 60/63 scenarios passed
- Recommendation: Deploy to production
- Confidence: High

### Finding 2: Missing SKU handling needs improvement
- Impact: 3 scenarios failed (crashes on missing SKU)
- Evidence: Edge case scenarios 61-63
- Recommendation: Add null check + fallback logic
- Confidence: High
```

---

## Metrics & KPIs

**Track these metrics for simulation quality:**

| Metric | Target | Measurement |
|--------|--------|-------------|
| Scenario coverage | 100% of matrix | % of combinations tested |
| Edge case coverage | >90% | % of prediction engine suggestions included |
| Execution time | <60 min | Total runtime for all scenarios |
| Success rate | >70% | % of scenarios passing |
| Safety violations | 0 | Count from audit log |

---

## Common Pitfalls

### ❌ Pitfall 1: Skipping Planning Phase
**Problem:** Jump straight to scenario generation

**Impact:** Wrong scenarios tested, wasted compute

**Solution:** Always start with Phase 0 (mandatory phase gating)

### ❌ Pitfall 2: Not Using Prediction Engine
**Problem:** Manual edge case identification

**Impact:** Miss critical edge cases

**Solution:** Query prediction engine in Phase 0

### ❌ Pitfall 3: Sequential Execution
**Problem:** Execute scenarios one-by-one

**Impact:** 10K scenarios take days instead of hours

**Solution:** Always use parallel execution (Phase 2 pattern)

### ❌ Pitfall 4: No Safety Validation
**Problem:** Simulation makes production changes

**Impact:** Data corruption, system downtime

**Solution:** Use dual-list safety pattern on every operation

---

## Checklist

**Before running simulation:**
- [ ] Planning phase complete (Phase 0)
- [ ] Scenario matrix designed
- [ ] Performance targets set
- [ ] Success criteria defined
- [ ] Prediction engine consulted
- [ ] Safety boundaries validated
- [ ] User/team approval obtained

**During execution:**
- [ ] Scenarios generated from matrix
- [ ] Edge cases added
- [ ] Agents spawned in parallel
- [ ] Safety validation on every operation
- [ ] Progress monitored
- [ ] Results written to manifest

**After completion:**
- [ ] Results aggregated
- [ ] Report generated (template used)
- [ ] Safety audit passed (0 violations)
- [ ] Recommendations actionable
- [ ] Learnings consolidated to memory

---

## Related Patterns

**See also:**
- `skills/meta/super-power.md` - Full simulation framework using this methodology
- `skills/workflows/scenario-matrix-design.md` - Matrix design (Phase 0)
- `skills/tooling/simulation-report-template.md` - Report format (Phase 3)
- `skills/meta/dual-list-safety-pattern.md` - Safety validation
- `skills/meta/mandatory-phase-gating.md` - Planning enforcement
- `skills/meta/quantified-performance-targets.md` - Performance metrics

---

*Simulation Testing Methodology v1.0 | Systematic validation | Scale with confidence*
