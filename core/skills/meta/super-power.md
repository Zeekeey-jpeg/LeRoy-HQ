# Super Power - Simulation Framework

**Version:** 1.0
**Type:** Meta Skill (System Enhancement)
**Purpose:** Run infinite loop simulations within controlled safety boundaries
**Architecture:** Four-Phase (Planning → Generation → Execution → Report)
**Last Updated:** 2026-01-18

---

## ⛔ CRITICAL: PLAN FIRST, SIMULATE SECOND

**MANDATORY RULE:** NEVER dive straight into simulation. ALWAYS plan first.

```
+===========================================================================+
|                    SUPER POWER EXECUTION PROTOCOL                         |
+===========================================================================+
|                                                                           |
|  Phase 0: PLANNING (REQUIRED - 2-5 min)                                 |
|  ├── User triggers: "Use your superpower to study X"                    |
|  ├── Enter plan mode AUTOMATICALLY (use EnterPlanMode tool)             |
|  ├── Analyze simulation target                                          |
|  ├── Design scenario matrix (what to test)                              |
|  ├── Identify data sources (internal vs external)                       |
|  ├── Query prediction engine for edge cases                             |
|  ├── Present simulation plan to user                                    |
|  └── Get approval before execution                                      |
|                                                                           |
|  Phase 1: Scenario Generation (5 min)                                   |
|  ├── Parse approved plan                                                |
|  ├── Generate 1000-10K scenarios in parallel                            |
|  ├── Enrich with external data if needed                                |
|  ├── Use prediction engine to add edge cases                            |
|  └── Validate scope within safety limits                                |
|                                                                           |
|  Phase 2: Parallel Execution (45 min)                                   |
|  ├── Spawn 10-20 simulator agents (Tier 4)                              |
|  ├── Each agent executes 500-1K scenarios                               |
|  ├── Results written to manifest.jsonl                                  |
|  └── Timeout handling (5 sec per scenario)                              |
|                                                                           |
|  Phase 3: Aggregation & Report (10 min)                                 |
|  ├── Load manifest and analyze results                                  |
|  ├── Generate structured report (highlights, scoring, gaps, risks)      |
|  ├── Consolidate learnings to memory                                    |
|  └── Present findings to user (NO auto-implementation)                  |
|                                                                           |
+===========================================================================+
```

**Why planning is mandatory:**
1. User sees and approves simulation approach before execution
2. Prevents wasted computation on wrong assumptions
3. Prediction engine integration happens during planning
4. Edge case identification before scenario generation
5. Safety boundary validation before any operations

**If you skip planning:** Simulation will be blocked. This is enforced.

---

## Quick Activation

| Trigger | Action |
|---------|--------|
| "use your superpower to [task]" | Mode selection → Simulation OR Plan Mode |
| "superpower study [topic]" | Same as above |
| "run superpower on [component]" | Same as above |
| "simulate [scenarios]" | Same as above |

**All triggers start with mode selection.**

---

## Phase -1: MODE SELECTION (MANDATORY - FIRST STEP)

**Trigger Detection:**
When user says "use your superpower to [task]", IMMEDIATELY present mode selection.

**Menu Options:**
```
[GATE] Super Power Activated

Which mode would you like to use?

1. **Simulation Mode** (Original)
   - Run thousands of scenarios concurrently
   - Test system components, analyze patterns
   - Generate scored reports with recommendations
   - Best for: Testing, validation, pattern analysis

2. **Plan Mode** (New)
   - Generate multiple implementation approaches in parallel
   - Compare plans head-to-head with scoring
   - Get comparative analysis before committing
   - Best for: Design decisions, architectural choices

Enter 1 or 2 to proceed.
```

**Branching Logic:**

**If user selects Option 1 (Simulation Mode):**
- Continue with Phase 0 (Planning) below
- Load standard super-power workflow
- Proceed through 4 phases: Plan → Generate → Execute → Report

**If user selects Option 2 (Plan Mode):**
- Load `skills/meta/super-power-plan-mode.md`
- Execute plan-mode workflow:
  - Phase 0: Problem Definition
  - Phase 1: Approach Specification
  - Phase 2: Parallel Plan Sessions
  - Phase 3: Comparative Analysis
- Exit this skill (plan-mode variant takes over)

**Default:** If unclear, ask user to clarify.

---

## What is a "Superpower"?

Think: **Neo learning kung fu + Doctor Strange seeing all outcomes**.

This framework allows:
- Simulating thousands of scenarios concurrently (within 1-hour limit)
- Pulling external data via WebFetch/WebSearch
- Testing system components with generated inputs
- Analyzing existing protocols for compliance
- Studying ANY topic (business, science, random curiosity)

**Safety First:** Read-only operations. No production writes. Simulation environment only.

---

## Simulation Types (UNLIMITED SUBJECT MATTER)

**CRITICAL:** This framework is NOT limited to business/technical topics. Can simulate ANYTHING.

### 1. System Enhancement Study
**Use:** "Use your superpower to study whether we should split Stage 6"

**Process:**
1. **PLAN MODE** - Analyze real system data, design scenario matrix
2. Load current configuration (your CRM stages, deal distribution)
3. Model multiple scenarios:
   - Current: Stage 6 as single entity
   - Option A: Split by deal size ($0-50K, $50K-100K, $100K+)
   - Option B: Split by timeline (short-cycle, long-cycle)
   - Option C: Keep as-is
4. Score each scenario (win rate, conversion time, bottleneck analysis)
5. Generate recommendations with confidence levels

**Output:** Structured report with scoring table, gap analysis, risks/rewards

### 2. Component Validation
**Use:** "Superpower test of opportunity pricing logic"

**Process:**
1. **PLAN MODE** - Identify edge cases, design test matrix
2. Generate edge cases (boundary conditions, nulls, extremes)
3. Execute simulated user inputs
4. Report pass/fail + discovered issues

**Output:** Pass/fail report, bug list with severity

### 3. Pattern Analysis (Any Domain)
**Business:** "Run superpower on your CRM ticket trends"
**Random:** "Superpower study: do European swallows migrate patterns match African swallows?"

**Process:**
1. **PLAN MODE** - Determine data sources, design analysis approach
2. Load historical data OR fetch external data
3. Detect patterns, anomalies, correlations
4. Present findings with evidence

**Output:** Pattern report with statistical confidence

### 4. Protocol Compliance
**Use:** "Superpower check: are we following pagination protocol?"

**Process:**
1. **PLAN MODE** - Identify protocol requirements, design validation tests
2. Re-test existing components against requirements
3. Identify compliance gaps
4. Score adherence percentage

**Output:** Compliance report with gap breakdown

### 5. External Data Study (Finance, Science, Sports, etc.)
**Finance:** "Superpower analysis of TSLA stock patterns"
**Science:** "Can a swallow carry a coconut? Superpower physics simulation"
**Sports:** "Superpower study: which NFL team has best 4th quarter comeback rate?"

**Process:**
1. **PLAN MODE** - Identify external data sources, design study approach
2. Fetch external data via WebSearch/WebFetch
3. Run analysis/calculations
4. Present insights with confidence scores

**Output:** Research report with sourced data

### 6. Curiosity-Driven Research
**Use:** "Use your superpower to find optimal pizza topping combinations by region"

**Process:**
1. **PLAN MODE** - Design research approach, identify data sources
2. Pure research questions
3. No business value required
4. Learning-focused simulation

**Output:** Research findings with evidence

---

## Safety Boundaries (ENFORCED)

**Blocklist (Production Protection):**
```python
FORBIDDEN_OPS = [
    r".*_update_.*",     # All MCP update operations
    r".*_create_.*",     # All MCP create operations
    r".*_delete_.*",     # All MCP delete operations
    r"send_.*_message",  # Email sending
    r"git (push|commit)", # Git write operations
    r"Write(?!.*session/super_power)", # File writes outside session/super_power/
    r"Edit"              # All file edits
]
```

**Allowlist (Read-Only):**
- All `_search_*`, `_list_*`, `_get_*` MCP operations
- `WebFetch`, `WebSearch` for external data
- `Read`, `Grep`, `Glob` for code exploration
- `Write` to `session/super_power/` ONLY (simulation outputs)

**Validation:** Every tool call checked against blocklist BEFORE execution. Zero tolerance.

**Safety Validator:** See `skills/meta/super-power-safety.md` for full validation logic.

---

## Phase 0: PLANNING (MANDATORY - ALWAYS FIRST)

**Trigger Detection:**
When user says "use your superpower to [task]", IMMEDIATELY call `EnterPlanMode` tool.

**Planning Activities:**
```
1. ANALYZE TARGET
   - What system/component/topic is being studied?
   - What data sources are available?
   - What constraints exist?

2. DESIGN SCENARIO MATRIX
   - What variables should be tested?
   - What combinations need exploration?
   - What edge cases might exist?

3. QUERY PREDICTION ENGINE
   Request: {
     "context": "{simulation_target}",
     "target": "{specific_component}",
     "user_goal": "{what user wants to learn}"
   }

   Receive: [
     "Test scenario A",
     "Test scenario B",
     "Edge case: X",
     "Edge case: Y"
   ]

4. IDENTIFY DATA SOURCES
   - Internal: your CRM, your catalog service, code files
   - External: WebSearch, WebFetch for market data, benchmarks
   - Generated: Synthetic test cases

5. ESTIMATE SCOPE
   - Number of scenarios: 100-10K
   - Runtime estimate: <60 min
   - Agent count: Tier 1-4 based on scenario count

6. PRESENT PLAN
   Show user:
   - Simulation target
   - Scenario matrix (what will be tested)
   - Data sources
   - Expected runtime
   - Predicted edge cases (from prediction engine)

7. GET APPROVAL
   User must approve before proceeding to Phase 1
```

**Planning Output:**
```markdown
# Simulation Plan: {Target}

## Target
{Component/system/topic being studied}

## Objective
{What we want to learn}

## Scenario Matrix
| Variable | Options |
|----------|---------|
| {var1} | {opt1, opt2, opt3} |
| {var2} | {opt1, opt2} |

**Total Scenarios:** {N} (combinations of all options)

## Data Sources
- Internal: {your CRM projects, your CRM deals, etc.}
- External: {WebSearch for benchmark data}
- Generated: {Edge cases from prediction engine}

## Prediction Engine Insights
Edge cases to include:
1. {edge_case_1}
2. {edge_case_2}
3. {edge_case_3}

## Safety Validation
- All operations: Read-only ✅
- No production writes ✅
- Output location: session/super_power/{YYYY-MM-DD}/ ✅

## Execution Plan
- Phase 1: Generate {N} scenarios (5 min)
- Phase 2: Execute with {M} agents (45 min)
- Phase 3: Aggregate and report (10 min)

**Approve to proceed?**
```

**After Approval:**
Exit plan mode and proceed to Phase 1.

---

## Phase 1: Scenario Generation (5 min)

**Input:** Approved plan from Phase 0

**Process:**
```python
# 1. Parse approved plan
scenario_matrix = extract_scenario_matrix(plan)
data_sources = extract_data_sources(plan)
edge_cases = extract_edge_cases(plan)

# 2. Generate base scenarios from matrix
base_scenarios = []
for combination in product(*scenario_matrix.values()):
    base_scenarios.append({
        'variables': dict(zip(scenario_matrix.keys(), combination)),
        'type': 'base'
    })

# 3. Add prediction engine edge cases
for edge_case in edge_cases:
    base_scenarios.append({
        'description': edge_case,
        'type': 'edge_case'
    })

# 4. Enrich with external data if needed
if data_sources.external:
    external_data = fetch_external_data(data_sources.external)
    scenarios = enrich_scenarios(base_scenarios, external_data)
else:
    scenarios = base_scenarios

# 5. Validate safety boundaries
for scenario in scenarios:
    validate_scenario_operations(scenario)

# 6. Write scenarios to manifest
write_manifest("session/super_power/{date}/scenarios.jsonl", scenarios)
```

**Manifest Format:**
```
SCENARIO|{"id": 1, "type": "base", "variables": {...}, "operations": [...]}
SCENARIO|{"id": 2, "type": "edge_case", "description": "...", "operations": [...]}
```

**Output:**
- `session/super_power/{YYYY-MM-DD}/scenarios.jsonl` - All scenarios to execute
- `session/super_power/{YYYY-MM-DD}/status.json` - Execution state tracker

---

## Phase 2: Parallel Execution (45 min)

**Agent Scaling Tiers:**
| Scenarios | Tier | Max Agents | Agent Workload |
|-----------|------|------------|----------------|
| 1-500 | 1 | 5 | 100 scenarios each |
| 501-5K | 2 | 12 | 500 scenarios each |
| 5K-15K | 3 | 18 | 1K scenarios each |
| 15K+ | 4 | 20+ | 1K scenarios each |

**Execution Protocol:**
```
1. READ scenarios.jsonl
2. CALCULATE agent count based on tier
3. SPLIT scenarios into equal chunks
4. SPAWN agents in parallel (all agents launched together)

   FOR EACH AGENT:
     - Task: Execute scenarios {start_id} to {end_id}
     - Timeout: 5 seconds per scenario
     - Output: Append results to results.jsonl
     - Safety: Validation on EVERY tool call

5. MONITOR progress (TaskOutput polling)
6. HANDLE timeouts (mark scenario as TIMEOUT, continue)
7. AGGREGATE when all agents complete
```

**Results Format:**
```
RESULT|{"scenario_id": 1, "status": "PASS", "score": 85, "findings": [...], "runtime": 2.3}
RESULT|{"scenario_id": 2, "status": "FAIL", "error": "...", "runtime": 0.5}
RESULT|{"scenario_id": 3, "status": "TIMEOUT", "runtime": 5.0}
```

**Status Tracking:**
```json
{
  "phase": "execution",
  "scenarios_total": 10000,
  "scenarios_completed": 7532,
  "agents": {
    "agent_1": {"status": "running", "completed": 892, "assigned": 1000},
    "agent_2": {"status": "complete", "completed": 1000, "assigned": 1000}
  },
  "started_at": "2026-01-18T10:00:00Z",
  "estimated_completion": "2026-01-18T10:42:00Z"
}
```

---

## Phase 3: Aggregation & Report (10 min)

**Process:**
```python
# 1. Load all results
results = read_jsonl("session/super_power/{date}/results.jsonl")

# 2. Calculate metrics
metrics = {
    'total_scenarios': len(results),
    'passed': count_where(results, status='PASS'),
    'failed': count_where(results, status='FAIL'),
    'timeout': count_where(results, status='TIMEOUT'),
    'success_rate': (passed / total) * 100,
    'avg_score': mean([r['score'] for r in results if 'score' in r]),
    'runtime_total': sum([r['runtime'] for r in results])
}

# 3. Detect patterns (top failures, score distribution)
patterns = {
    'top_failures': group_by(results, 'error').most_common(5),
    'score_distribution': histogram([r['score'] for r in results if 'score' in r]),
    'edge_case_results': filter(results, type='edge_case')
}

# 4. Generate insights (using postmortem analyzer scoring)
insights = generate_insights(results, patterns)

# 5. Build recommendations
recommendations = build_recommendations(insights, patterns)

# 6. Create structured report (using template)
report = generate_report(metrics, patterns, insights, recommendations)

# 7. Write report to disk
write_file("session/super_power/{date}/report.md", report)

# 8. Consolidate learnings to memory
consolidate_to_memory(insights, recommendations)
```

**Report Template:** See `skills/meta/super-power-report-template.md`

---

## Scoring Methodology (from Postmortem Analyzer)

**Variance Calculation:**
```javascript
const variance = {
  estimated: baseline_value,
  actual: measured_value,
  variance: actual - estimated,
  variancePercent: ((actual - estimated) / estimated) * 100,
  overrunMultiplier: actual / estimated
};
```

**Weighted Scoring Formula:**
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

---

## Memory Integration (Auto-Consolidation)

**After Phase 3 completes, automatically consolidate learnings:**

**What gets saved:**
1. **Patterns Detected** → `Claude/Patterns/{pattern-name}.md`
   - Recurring failure modes
   - Performance bottlenecks
   - Unexpected behaviors

2. **Decisions Made** → `Claude/Decisions/{decision-name}.md`
   - Architectural choices validated/rejected
   - Configuration changes recommended
   - Protocol improvements

3. **Skills Learned** → `Claude/Skills-Learned/{workflow-name}.md`
   - New simulation techniques discovered
   - Optimization strategies
   - Edge case handling

**Consolidation follows:** `skills/meta/memory-consolidation.md` protocol
- Structured frontmatter with tags
- Wikilink generation (automatic)
- Email notification to you@example.com
- Index update

---

## Prediction Engine Integration

**Location:** `~/.claude\session\prediction-engine.json`

**During Planning Phase (Phase 0):**
```python
# Query prediction engine for scenario suggestions
prediction_request = {
    "context": "your CRM stage optimization study",
    "target": "stage naming conventions",
    "user_goal": "improve pipeline clarity"
}

predictions = query_prediction_engine(prediction_request)
# Returns: [
#   "Test split by deal size",
#   "Test split by timeline",
#   "Check for bottleneck stages",
#   "Edge case: deals stuck >90 days"
# ]

# Use predictions to seed scenario generation
scenarios = generate_scenarios_from_predictions(predictions)
```

**During Scenario Generation (Phase 1):**
```python
# Prediction engine suggests edge cases
edge_cases = prediction_engine.suggest_edge_cases(
    simulation_type="enhancement_study",
    domain="crm_tool"
)

# Add to scenario pool
scenarios.extend(edge_cases)
```

**API Pattern:**
```python
def query_prediction_engine(context_object):
    """
    Consults prediction engine for simulation suggestions.

    Returns:
    - scenario_types: What to test
    - edge_cases: What might break
    - data_sources: Where to get data
    - expected_patterns: What to look for
    """
    engine = read_json("session/prediction-engine.json")
    return engine.predict(context_object)
```

---

## Data Integrity Protocol (from LeRoy Factory)

**THE RULE:**
```
+=========================================================================+
|                    DATA INTEGRITY PROTOCOL                               |
+=========================================================================+
|                                                                          |
|  Phase 1 (Generation):  API calls ALLOWED                               |
|  Phase 2 (Execution):   API calls FORBIDDEN                             |
|  Phase 3 (Report):      API calls FORBIDDEN                             |
|                                                                          |
|  ALL agents MUST use the SAME scenario snapshot.                        |
|  If results show different baseline numbers, DATA INTEGRITY HAS FAILED. |
|                                                                          |
+=========================================================================+
```

**Why this matters:**
- Phase 1: Fetch all external data, generate all scenarios, write to manifest
- Phase 2+: Read from manifest ONLY, no new API calls
- Prevents: Different agents seeing different data mid-simulation

**Validation:**
- Before Phase 2: Verify scenarios.jsonl exists and is complete
- During Phase 2: Block all MCP write operations
- After Phase 2: Verify all agents used same scenario set

---

## MCP Pagination (Complete Dataset Fetching)

**If simulation requires MCP data (your CRM):**

**COUNT → FETCH → VERIFY Pattern:**
```javascript
// 1. COUNT first (if API supports it)
const total = await mcp__ticketing__count_opportunities();

// 2. FETCH with max page size
const opportunities = await mcp__ticketing__list_opportunities({
    pageSize: 1000,  // your CRM max
    page: 1
});

// 3. VERIFY: if count === max_page_size, MORE DATA EXISTS
if (opportunities.length === 1000) {
    // PAGINATE - fetch remaining pages
    let page = 2;
    while (true) {
        const next_page = await fetch_page(page);
        if (next_page.length === 0) break;
        opportunities.push(...next_page);
        page++;
    }
}
```

**Max Page Sizes (MEMORIZE):**
| MCP Server | Max Page Size |
|------------|---------------|
| your CRM | 200 |
| your CRM | 1000 |

**Reference:** `skills/meta/mcp-pagination.md`

---

## Example: Business Enhancement Study

**User Request:** "Use your superpower to study your CRM stage naming"

**Phase 0: PLANNING**
```
[EnterPlanMode tool called automatically]

1. Analyze target: your CRM stage configuration
2. Design scenario matrix:
   - Current: Stage 6 as single entity
   - Option A: Split by deal size ($0-50K, $50K-100K, $100K+)
   - Option B: Split by timeline (short-cycle <30 days, long-cycle >30 days)
   - Option C: Keep as-is
3. Query prediction engine: "What scenarios should I test for stage optimization?"
   - Prediction: Test bottleneck detection, conversion rate impact
4. Present plan to user:

   # Simulation Plan: your CRM Stage Optimization

   ## Scenario Matrix
   | Stage Config | Deal Size Splits | Timeline Splits |
   |--------------|------------------|-----------------|
   | Current (1 stage) | N/A | N/A |
   | Option A | 3 ($0-50K, $50K-100K, $100K+) | N/A |
   | Option B | N/A | 2 (short <30d, long >30d) |

   **Total Scenarios:** 3

   ## Data Sources
   - Internal: your CRM deals (last 12 months, Stage 6)
   - Metrics: Conversion rate, time in stage, bottleneck detection

   ## Edge Cases (from prediction engine)
   - Deals stuck >90 days
   - Deals cycling back to earlier stages

   **Approve to proceed?**

5. User approves
```

**Phase 1: GENERATION**
```
1. Generate 3 base scenarios + 2 edge case scenarios
2. Fetch your CRM Stage 6 deals (pagination enforced)
3. Write scenarios.jsonl:
   SCENARIO|{"id": 1, "config": "current", "data": {...}}
   SCENARIO|{"id": 2, "config": "option_a", "splits": [50000, 100000], "data": {...}}
   SCENARIO|{"id": 3, "config": "option_b", "splits": [30], "data": {...}}
   SCENARIO|{"id": 4, "type": "edge_case", "description": "deals >90 days", "data": {...}}
   SCENARIO|{"id": 5, "type": "edge_case", "description": "cycling deals", "data": {...}}
```

**Phase 2: EXECUTION**
```
1. Spawn 1 agent (Tier 1, only 5 scenarios)
2. Agent executes:
   - Scenario 1: Calculate conversion rate, time in stage (current config)
   - Scenario 2: Calculate same metrics with 3-way split
   - Scenario 3: Calculate same metrics with 2-way split
   - Scenario 4: Identify deals stuck >90 days, analyze causes
   - Scenario 5: Identify cycling patterns
3. Write results.jsonl:
   RESULT|{"scenario_id": 1, "conversion_rate": 32%, "avg_time_in_stage": 45, "score": 70}
   RESULT|{"scenario_id": 2, "conversion_rate": 38%, "avg_time_in_stage": 35, "score": 85}
   RESULT|{"scenario_id": 3, "conversion_rate": 35%, "avg_time_in_stage": 40, "score": 80}
   RESULT|{"scenario_id": 4, "findings": ["12 deals stuck, reasons: ..."], "score": 60}
   RESULT|{"scenario_id": 5, "findings": ["5 cycling deals, pattern: ..."], "score": 65}
```

**Phase 3: REPORT**
```markdown
# Super Power Simulation Report

**Date:** 2026-01-18T10:30:00Z
**Target:** your CRM Stage 6 Optimization
**Scenarios:** 5 executed / 5 total
**Success Rate:** 100%
**Runtime:** 00:03:42

---

## 1. HIGHLIGHTS (Top 3)

1. **Option A (3-way split) shows 18% conversion improvement**
   - Evidence: Scenario 2 scored 85 vs baseline 70
   - Impact: $450K additional annual revenue (estimated)
   - Recommendation: Implement 3-way split by deal size

2. **12 deals stuck >90 days identified**
   - Root cause: Sales rep unresponsiveness (7), customer delays (5)
   - Impact: $380K pipeline at risk
   - Recommendation: Create escalation process at 60-day mark

3. **Cycling pattern detected in 5 deals**
   - Pattern: Move to Stage 6 → back to Stage 5 → repeat
   - Root cause: Premature stage progression
   - Recommendation: Add qualification gate before Stage 6

## 2. SCORING BREAKDOWN

| Scenario | Conversion Rate | Avg Time | Score | Status |
|----------|----------------|----------|-------|--------|
| Current (baseline) | 32% | 45 days | 70 | C ⚠️ |
| Option A (deal size) | 38% | 35 days | 85 | B ✅ |
| Option B (timeline) | 35% | 40 days | 80 | B ✅ |
| Edge: Stuck deals | N/A | N/A | 60 | D ⚠️ |
| Edge: Cycling | N/A | N/A | 65 | D ⚠️ |

**Overall Grade:** B (80/100)

## 3. GAP ANALYSIS

**Gaps Detected:**
1. No escalation process for stuck deals → High priority fix
2. No qualification gate before Stage 6 → Medium priority fix
3. Stage naming doesn't reflect deal complexity → Low priority enhancement

**Coverage Gaps:**
- Did not test 4-way split (too granular for current deal volume)
- Did not test stage renaming impact (requires user feedback data)

## 4. RISKS & REWARDS

### Risks
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Sales team rejects complexity | Medium | High | Train on new stages, gradual rollout |
| CRM confusion during transition | High | Medium | Clear communication, documentation |

### Rewards
| Reward | Confidence | Impact |
|--------|-----------|--------|
| 18% conversion improvement | High | $450K/year |
| Reduce stuck deals by 50% | Medium | $190K recovered |

## 5. EXECUTION SUMMARY

- Scenarios executed: 5
- Runtime: 3m 42s
- Agents spawned: 1
- Safety violations: 0 ✅
- Data sources: your CRM (212 deals analyzed)

## 6. RECOMMENDATIONS

1. **Implement Option A (3-way split by deal size)** - Priority: High
   - Rationale: 18% conversion improvement, clear deal segmentation
   - Timeline: 2 weeks (CRM config + training)
   - Owner: Sales Operations

2. **Create 60-day escalation process** - Priority: High
   - Rationale: Prevent 12+ deals from stalling
   - Timeline: 1 week
   - Owner: Sales Management

3. **Add qualification gate before Stage 6** - Priority: Medium
   - Rationale: Prevent premature progression (cycling pattern)
   - Timeline: 1 week
   - Owner: Sales Process Team

## 7. MEMORY IMPACT

- Learnings consolidated: 2 notes
  - Pattern: your CRM Stage Bottleneck Detection
  - Decision: Stage Optimization via Deal Size Segmentation
- Wikilinks created: 6 connections
- Knowledge graph hubs: Connected to [[HUB - your CRM Integration]]

---

## APPENDIX

- Manifest: session/super_power/2026-01-18/scenarios.jsonl
- Results: session/super_power/2026-01-18/results.jsonl
- Audit trail: 0 safety violations ✅
```

---

## Example: Random Curiosity Simulation

**User Request:** "Can a European swallow carry a coconut? Use your superpower"

**Phase 0: PLANNING**
```
1. Parse target: "bird carrying capacity physics"
2. Design scenario matrix:
   - Species: European swallow, African swallow
   - Coconut weight: 0.5kg, 1kg, 1.5kg
   - Flight conditions: Unladen, gripped, harnessed
3. Query prediction engine: "What scenarios should I test for bird carrying capacity?"
   - Prediction: Test grip strength, aerodynamics, unladen vs laden flight
4. Present plan:

   # Simulation Plan: Swallow Carrying Capacity

   ## Scenario Matrix
   | Species | Coconut Weight | Flight Condition |
   |---------|----------------|------------------|
   | European | 0.5kg, 1kg, 1.5kg | Unladen, Gripped, Harnessed |
   | African | 0.5kg, 1kg, 1.5kg | Unladen, Gripped, Harnessed |

   **Total Scenarios:** 2 species × 3 weights × 3 conditions = 18

   ## Data Sources
   - External: Ornithology databases (WebSearch)
   - External: Physics formulas for lift capacity
   - Generated: Grip strength calculations

   **Approve to proceed?**
```

**Phase 1: GENERATION**
```
1. WebSearch for: "European swallow weight", "coconut weight", "bird carrying capacity"
2. Generate 18 scenarios with physics calculations
3. Add edge cases from prediction engine
```

**Phase 2: EXECUTION**
```
1. Execute physics calculations for each scenario
2. Calculate: lift capacity, grip strength, aerodynamic drag
3. Determine: PASS (can carry) or FAIL (cannot carry)
```

**Phase 3: REPORT**
```markdown
## HIGHLIGHTS

1. **European swallow CANNOT carry a 1kg coconut**
   - Evidence: Grip strength insufficient (max 0.4kg grip)
   - Physics: Unladen swallow weight 20g, max lift capacity ~40% body weight
   - Conclusion: Coconut too heavy

2. **African swallow COULD carry 0.5kg coconut (harnessed)**
   - Evidence: Larger bird (40g), stronger grip (0.6kg)
   - Caveat: Flight speed reduced by 60%

3. **Unladen swallow velocity: 24 mph (European), 31 mph (African)**
   - Source: Ornithology studies (WebSearch)

## RECOMMENDATIONS

- For coconut transport: Use African swallow with harness system
- For European swallow: Maximum cargo 0.3kg
```

---

## Folder Structure

```
session/super_power/{YYYY-MM-DD}/
├── status.json              # Execution state
├── scenarios.jsonl          # Generated scenarios
├── results.jsonl            # Execution results
├── report.md               # Final report
└── audit.log               # Safety violation log (should be empty)
```

---

## Status.json Schema

```json
{
  "run_date": "2026-01-18",
  "target": "your CRM stage optimization",
  "phase": "execution",
  "started_at": "2026-01-18T10:00:00Z",
  "completed_at": null,
  "scenarios": {
    "total": 5,
    "completed": 3,
    "passed": 2,
    "failed": 0,
    "timeout": 0
  },
  "agents": {
    "agent_1": {
      "status": "running",
      "assigned_scenarios": [1, 2, 3],
      "completed": 2
    }
  },
  "safety": {
    "violations": 0,
    "blocked_operations": []
  }
}
```

---

## Error Handling

| Condition | Action |
|-----------|--------|
| Safety violation detected | BLOCK operation, LOG to audit.log, FAIL scenario |
| Scenario timeout (>5 sec) | Mark TIMEOUT, continue to next |
| Agent dies mid-execution | Check for partial results, re-spawn agent |
| External data unavailable | Use cached data OR skip scenario |
| Planning rejected by user | ABORT - do not proceed to execution |

---

## Integration Points

**Called By:**
- User via quick trigger
- `@agent-conductor` for large-scale analysis

**Calls:**
- `EnterPlanMode` tool (MANDATORY Phase 0)
- `ExitPlanMode` tool (after plan approval)
- `Task` tool (spawn simulator agents)
- `skills/meta/super-power-safety.md` (validation on every operation)
- `skills/meta/super-power-report-template.md` (report generation)
- `skills/meta/memory-consolidation.md` (auto-consolidation)
- Prediction engine (`session/prediction-engine.json`)

**Requires:**
- MCP tools (for data fetching, if needed)
- WebFetch/WebSearch (for external data)
- Read/Grep/Glob (for code exploration)

---

## Performance Targets

| Metric | Target | Max |
|--------|--------|-----|
| Scenarios (100) | <5 min | 10 min |
| Scenarios (1K) | <15 min | 30 min |
| Scenarios (10K) | <60 min | 90 min |
| Safety violations | 0 | 0 |
| Planning phase | <5 min | 10 min |

---

## Validation Gates

**Before Phase 1:**
- [ ] Plan approved by user
- [ ] Safety boundaries validated
- [ ] Data sources identified
- [ ] Scenario count within limits (<50K)

**Before Phase 2:**
- [ ] scenarios.jsonl exists and is complete
- [ ] All scenarios have valid operations
- [ ] Agent count calculated correctly
- [ ] Status.json initialized

**Before Phase 3:**
- [ ] All agents completed or timed out
- [ ] results.jsonl exists and is complete
- [ ] No safety violations logged
- [ ] Metrics calculated successfully

**Before User Presentation:**
- [ ] Report follows template structure
- [ ] Highlights section has 3-5 items
- [ ] Scoring table present
- [ ] Recommendations actionable
- [ ] Memory consolidation complete

---

## Future Enhancements (v2.0+)

1. **Multi-User Support** - Share simulation results across team
2. **Simulation Templates** - Pre-built scenario sets for common tasks
3. **Interactive Mode** - User adjusts parameters mid-simulation
4. **Real-Time Dashboards** - Live progress tracking for long runs
5. **Comparison Mode** - A/B test two approaches side-by-side
6. **Chaos Engineering** - Automated fault injection testing
7. **Prediction Feedback Loop** - Simulation results improve prediction accuracy

---

## Testing Checklist

**Phase 1: Core Framework**
- [ ] Trigger detection works
- [ ] Planning phase enforced (cannot skip)
- [ ] Scenario generation completes
- [ ] Safety validation blocks forbidden operations

**Phase 2: Execution**
- [ ] Agents spawn correctly based on tier
- [ ] Results written to manifest
- [ ] Timeouts handled gracefully
- [ ] Status tracking updates correctly

**Phase 3: Reporting**
- [ ] Report follows template
- [ ] Scoring calculations correct
- [ ] Recommendations actionable
- [ ] Memory consolidation runs

**Phase 4: Safety**
- [ ] All write operations blocked (except session/super_power/)
- [ ] Email sending blocked
- [ ] Git operations blocked
- [ ] Audit log shows zero violations

---

## Related Meta-Skills

The following meta-skills document reusable patterns extracted from the Super Power framework:

**Core Patterns:**
- `meta/mandatory-phase-gating.md` - Plan-before-execute pattern (Phase 0 enforcement)
- `meta/dual-list-safety-pattern.md` - Blocklist + allowlist safety validation
- `meta/skill-composition-for-frameworks.md` - Building frameworks from existing skills

**Documentation & Planning:**
- `meta/framework-documentation-standard.md` - 7-part structure for framework docs
- `meta/four-week-framework-rollout-template.md` - Weekly breakdown for implementations
- `workflows/scenario-matrix-design.md` - Systematic scenario generation from variables

**Testing & Analysis:**
- `meta/simulation-testing-methodology.md` - 4-phase testing approach with agent scaling
- `meta/risk-classification-framework.md` - 3-tier risk model (HIGH/MEDIUM/LOW)
- `meta/quantified-performance-targets.md` - Framework for measurable objectives

**Reporting:**
- `tooling/simulation-report-template.md` - Universal 7-section report structure

These skills enable rapid framework development by reusing proven patterns.

---

*Super Power Simulation Framework v1.0 | Think: Neo + Doctor Strange | Always plan first*
