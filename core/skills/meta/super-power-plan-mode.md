# Super Power - Plan Mode Variant

**Version:** 1.0
**Type:** Meta Skill (System Enhancement)
**Purpose:** Generate and compare multiple implementation approaches in parallel
**Architecture:** Four-Phase (Problem → Approaches → Plans → Analysis)
**Parent:** `super-power.md` (loaded via Phase -1 mode selection)
**Last Updated:** 2026-01-23

---

## ⛔ CRITICAL: WHAT THIS MODE DOES

**Plan Mode generates MULTIPLE implementation plans for the SAME problem, then compares them.**

```
+===========================================================================+
|                    PLAN MODE EXECUTION PROTOCOL                           |
+===========================================================================+
|                                                                           |
|  User: "Use your superpower to plan [feature/refactor/integration]"     |
|                                                                           |
|  Phase 0: Problem Definition (5 min)                                    |
|  ├── Enter plan mode (use EnterPlanMode tool)                           |
|  ├── Analyze problem space                                              |
|  ├── Identify constraints (time, resources, tech stack)                 |
|  ├── Define success criteria                                            |
|  ├── Brainstorm 3-5 distinct approaches                                 |
|  └── Write approaches to approaches.jsonl                               |
|                                                                           |
|  Phase 1: Approach Specification (2 min)                                |
|  ├── Read approaches.jsonl                                              |
|  ├── Validate each approach is distinct (no duplicates)                 |
|  ├── Assign approach IDs (1, 2, 3, ...)                                 |
|  └── Initialize status.json                                             |
|                                                                           |
|  Phase 2: Parallel Plan Sessions (30 min)                               |
|  ├── Spawn 1 planner agent per approach (3-5 agents)                    |
|  ├── Each agent generates FULL implementation plan                      |
|  ├── Plans include: steps, risks, timeline, resources                   |
|  ├── Plans written to plan-{approach_id}.md                             |
|  └── All agents run in parallel (not sequential)                        |
|                                                                           |
|  Phase 3: Comparative Analysis (10 min)                                 |
|  ├── Load all plans from disk                                           |
|  ├── Score each plan (complexity, risk, timeline, resources)            |
|  ├── Generate head-to-head comparison table                             |
|  ├── Identify recommended approach with rationale                       |
|  ├── Consolidate learnings to memory                                    |
|  └── Present findings to user (NO auto-implementation)                  |
|                                                                           |
+===========================================================================+
```

**Why Plan Mode is valuable:**
1. See all viable approaches BEFORE committing to one
2. Compare trade-offs side-by-side (time vs complexity vs risk)
3. Catch hidden risks early (each planner agent surfaces different concerns)
4. User makes informed decision with full context
5. Faster iteration (parallel planning vs sequential trial-and-error)

**When to use Plan Mode vs Simulation Mode:**
- **Plan Mode:** Design decisions, architectural choices, feature implementation strategies
- **Simulation Mode:** Testing, validation, pattern analysis, system enhancement studies

---

## Phase 0: Problem Definition (5 min)

**Input:** User request: "Use your superpower to plan [feature/refactor/integration]"

**Process:**
```
1. ENTER PLAN MODE
   - Call EnterPlanMode tool
   - Confirm mode active

2. ANALYZE PROBLEM SPACE
   - What is the user trying to accomplish?
   - What constraints exist? (time, budget, tech stack, team capacity)
   - What are the success criteria?
   - What are the failure modes?

3. IDENTIFY EXISTING CONTEXT
   - Read relevant code files
   - Check existing architecture patterns
   - Review dependencies and integrations
   - Consult memory for past decisions

4. BRAINSTORM APPROACHES
   Generate 3-5 DISTINCT approaches. Each approach must be:
   - Viable (can actually solve the problem)
   - Distinct (not just minor variations)
   - Trade-off different (optimize for different priorities)

   Example approaches for "Add real-time notifications":
   - Approach A: WebSockets with Socket.io (real-time, complex)
   - Approach B: Server-Sent Events (real-time, simpler)
   - Approach C: Polling with optimistic updates (simpler, less real-time)
   - Approach D: Push notifications only (simplest, mobile-friendly)
   - Approach E: Hybrid SSE + polling fallback (most compatible)

5. VALIDATE DISTINCTNESS
   Each approach should optimize for different priority:
   - Speed of implementation
   - Runtime performance
   - Maintainability
   - Cost efficiency
   - User experience
   - Future extensibility

6. WRITE APPROACHES TO DISK
   Write to: session/super_power/{YYYY-MM-DD}/approaches.jsonl

   Format:
   APPROACH|{"id": 1, "name": "WebSockets with Socket.io", "priority": "real-time performance", "complexity": "high", "description": "..."}
   APPROACH|{"id": 2, "name": "Server-Sent Events", "priority": "simplicity", "complexity": "medium", "description": "..."}
   ...

7. PRESENT TO USER
   Show the user:
   - Problem statement (interpreted)
   - Success criteria
   - Constraints identified
   - List of approaches (names + priorities)
   - Estimated planning time (Phase 2)

8. GET APPROVAL
   User must approve approach list before Phase 2
   User can request adjustments (add/remove approaches)
```

**Output:**
```markdown
# Plan Mode: Problem Definition

## Problem
{User's original request, interpreted}

## Success Criteria
- [ ] {Criterion 1}
- [ ] {Criterion 2}
- [ ] {Criterion 3}

## Constraints
- Time: {e.g., "2 weeks"}
- Resources: {e.g., "1 developer"}
- Tech Stack: {e.g., "React, Node.js, Supabase"}
- Existing Systems: {e.g., "Must integrate with your CRM"}

## Approaches Identified

### Approach 1: {Name}
- **Priority:** {What this optimizes for}
- **Complexity:** {Low/Medium/High}
- **Description:** {1-2 sentence summary}

### Approach 2: {Name}
- **Priority:** {What this optimizes for}
- **Complexity:** {Low/Medium/High}
- **Description:** {1-2 sentence summary}

### Approach 3: {Name}
- **Priority:** {What this optimizes for}
- **Complexity:** {Low/Medium/High}
- **Description:** {1-2 sentence summary}

*(Repeat for 3-5 approaches)*

## Execution Plan
- Phase 2: Spawn {N} planner agents (1 per approach)
- Phase 2 Runtime: ~30 minutes (parallel execution)
- Phase 3: Comparative analysis (~10 minutes)

**Approve to proceed?**
```

---

## Phase 1: Approach Specification (2 min)

**Input:** Approved approaches.jsonl from Phase 0

**Process:**
```python
# 1. Read approaches.jsonl
approaches = read_jsonl("session/super_power/{date}/approaches.jsonl")

# 2. Validate distinctness
for i, approach_i in enumerate(approaches):
    for j, approach_j in enumerate(approaches):
        if i != j:
            similarity = calculate_similarity(approach_i, approach_j)
            if similarity > 0.8:
                raise ValueError(f"Approaches {i+1} and {j+1} are too similar")

# 3. Assign IDs (already done in Phase 0)
# Each approach has unique ID: 1, 2, 3, ...

# 4. Initialize status.json
status = {
    "run_date": date,
    "mode": "plan",
    "problem": user_request,
    "phase": "approach_specification",
    "approaches": {
        str(approach["id"]): {
            "name": approach["name"],
            "priority": approach["priority"],
            "status": "pending",
            "plan_file": f"plan-{approach['id']}.md"
        }
        for approach in approaches
    },
    "started_at": now(),
    "completed_at": None
}

write_json("session/super_power/{date}/status.json", status)

# 5. Validate count (3-5 approaches)
if len(approaches) < 3:
    raise ValueError("Need at least 3 approaches")
if len(approaches) > 5:
    raise ValueError("Maximum 5 approaches (agent limit)")
```

**Output:**
- `status.json` initialized
- Approach IDs validated
- Ready for Phase 2 (agent spawning)

---

## Phase 2: Parallel Plan Sessions (30 min)

**Agent Spawning:**
```
FOR EACH approach in approaches.jsonl:
    SPAWN planner agent with task:
    {
        "role": "Implementation Planner",
        "approach": {approach object},
        "constraints": {from Phase 0},
        "success_criteria": {from Phase 0},
        "output_file": "session/super_power/{date}/plan-{approach_id}.md",
        "instructions": "Generate FULL implementation plan following template"
    }

ALL AGENTS RUN IN PARALLEL (not sequential)
```

**Planner Agent Task:**

Each planner agent receives:
- Problem statement
- Success criteria
- Constraints (time, resources, tech stack)
- Assigned approach (name, priority, description)
- Template to follow

Each planner agent generates:
```markdown
# Implementation Plan: {Approach Name}

## Approach Summary
{2-3 sentence description of this approach}

**Priority:** {What this optimizes for}
**Complexity:** {Low/Medium/High}
**Estimated Timeline:** {e.g., "2 weeks"}

---

## Phase Breakdown

### Phase 1: {Phase Name} ({Duration})
**Objective:** {What gets accomplished}

**Tasks:**
1. {Task description}
   - File(s): {files to create/modify}
   - Dependencies: {packages to install}
   - Risks: {potential issues}
2. {Task description}
   ...

**Deliverables:**
- {Deliverable 1}
- {Deliverable 2}

**Dependencies:** {What must complete before this phase}

---

### Phase 2: {Phase Name} ({Duration})
*(Repeat structure)*

---

*(Repeat for all phases)*

---

## Total Timeline
- Phase 1: {Duration}
- Phase 2: {Duration}
- Phase 3: {Duration}
- **Total:** {Sum}

---

## Resource Requirements

### Team
- {Role 1}: {Availability needed} (e.g., "1 developer, full-time for 2 weeks")
- {Role 2}: {Availability needed}

### Infrastructure
- {Service 1}: {Requirement} (e.g., "Supabase Pro tier for real-time subscriptions")
- {Service 2}: {Requirement}

### Dependencies
| Package | Version | Purpose |
|---------|---------|---------|
| {pkg1} | {ver} | {why} |
| {pkg2} | {ver} | {why} |

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| {Risk 1} | High/Med/Low | High/Med/Low | {How to address} |
| {Risk 2} | High/Med/Low | High/Med/Low | {How to address} |

**Overall Risk Level:** {Low/Medium/High}

---

## Trade-offs

### Advantages
- {Pro 1}
- {Pro 2}
- {Pro 3}

### Disadvantages
- {Con 1}
- {Con 2}
- {Con 3}

### Compared to Other Approaches
- **vs Approach X:** {This approach is better at Y but worse at Z}
- **vs Approach Y:** {This approach is better at Z but worse at Y}

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| {Metric 1} | {Value} | {How to measure} |
| {Metric 2} | {Value} | {How to measure} |

---

## Testing Strategy

### Unit Tests
- {What to test}
- {What to test}

### Integration Tests
- {What to test}
- {What to test}

### E2E Tests
- {What to test}
- {What to test}

**Test Coverage Target:** {e.g., "80%"}

---

## Rollback Plan

If implementation fails:
1. {Rollback step 1}
2. {Rollback step 2}
3. {Rollback step 3}

**Rollback Time:** {Duration}

---

## Future Extensibility

This approach enables:
- {Future enhancement 1}
- {Future enhancement 2}
- {Future enhancement 3}

This approach blocks/complicates:
- {Future limitation 1}
- {Future limitation 2}

---

## Recommendation Confidence

**Confidence Level:** {Low/Medium/High}

**Rationale:**
{Why this confidence level? What unknowns exist?}

---

## Next Steps

If this approach is selected:
1. {First action}
2. {Second action}
3. {Third action}
```

**Status Tracking:**
```json
{
  "phase": "parallel_planning",
  "approaches": {
    "1": {"status": "in_progress", "agent_id": "planner_1"},
    "2": {"status": "complete", "plan_file": "plan-2.md"},
    "3": {"status": "in_progress", "agent_id": "planner_3"}
  },
  "started_at": "2026-01-23T10:00:00Z",
  "estimated_completion": "2026-01-23T10:30:00Z"
}
```

---

## Phase 3: Comparative Analysis (10 min)

**Input:** All plans from Phase 2 (plan-1.md, plan-2.md, ...)

**Process:**
```python
# 1. Load all plans
plans = []
for approach_id in [1, 2, 3, 4, 5]:
    plan_file = f"session/super_power/{date}/plan-{approach_id}.md"
    if file_exists(plan_file):
        plans.append({
            'id': approach_id,
            'content': read_file(plan_file),
            'parsed': parse_plan(plan_file)
        })

# 2. Extract metrics from each plan
metrics = []
for plan in plans:
    metrics.append({
        'id': plan['id'],
        'name': plan['parsed']['approach_name'],
        'timeline': parse_duration(plan['parsed']['total_timeline']),
        'complexity': plan['parsed']['complexity'],  # Low/Med/High → 1/2/3
        'risk': plan['parsed']['overall_risk_level'],  # Low/Med/High → 1/2/3
        'resource_count': count_resources(plan['parsed']['resource_requirements']),
        'test_coverage': plan['parsed']['test_coverage_target'],
        'extensibility_score': score_extensibility(plan['parsed']['future_extensibility'])
    })

# 3. Score each plan (weighted formula)
for metric in metrics:
    score = (
        (100 / metric['timeline']) * 0.25 +        # Faster = better (25%)
        (4 - metric['complexity']) * 10 * 0.20 +   # Simpler = better (20%)
        (4 - metric['risk']) * 10 * 0.30 +         # Lower risk = better (30%)
        (100 / metric['resource_count']) * 0.15 +  # Fewer resources = better (15%)
        metric['extensibility_score'] * 0.10       # More extensible = better (10%)
    )
    metric['total_score'] = round(score, 1)

# 4. Rank plans by score
ranked = sorted(metrics, key=lambda x: x['total_score'], reverse=True)

# 5. Generate head-to-head comparison table
comparison_table = generate_comparison_table(ranked)

# 6. Identify recommended approach
recommended = ranked[0]
runner_up = ranked[1] if len(ranked) > 1 else None

# 7. Generate insights
insights = {
    'recommended': {
        'id': recommended['id'],
        'name': recommended['name'],
        'score': recommended['total_score'],
        'rationale': generate_rationale(recommended, runner_up)
    },
    'runner_up': {
        'id': runner_up['id'],
        'name': runner_up['name'],
        'score': runner_up['total_score'],
        'when_to_use': generate_when_to_use(runner_up, recommended)
    } if runner_up else None,
    'key_differences': identify_key_differences(ranked),
    'risk_summary': summarize_risks(plans)
}

# 8. Build comparative report (using template)
report = generate_report(metrics, comparison_table, insights, plans)

# 9. Write report to disk
write_file(f"session/super_power/{date}/plan-comparison.md", report)

# 10. Consolidate learnings to memory
consolidate_to_memory(insights, plans)
```

**Scoring Formula:**
```javascript
score = (timeline_score × 25%) +      // Faster = better
        (simplicity_score × 20%) +    // Simpler = better
        (risk_score × 30%) +          // Lower risk = better
        (resource_score × 15%) +      // Fewer resources = better
        (extensibility_score × 10%)   // More extensible = better

// Grade thresholds
90-100 = A (Excellent - highly recommended)
80-89  = B (Good - solid choice)
70-79  = C (Acceptable - consider trade-offs)
60-69  = D (Risky - needs careful evaluation)
<60    = F (Not recommended)
```

**Output:**
- `plan-comparison.md` (full comparative report)
- Recommended approach identified
- Trade-offs clearly documented
- User can make informed decision

**Report Template:** See `skills/meta/super-power-plan-mode-report-template.md`

---

## Safety Boundaries (INHERITED FROM PARENT)

**Plan Mode uses SAME safety boundaries as Simulation Mode.**

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
- `WebFetch`, `WebSearch` for external research
- `Read`, `Grep`, `Glob` for code exploration
- `Write` to `session/super_power/` ONLY (plan outputs)

**Validation:** Every tool call checked against blocklist BEFORE execution. Zero tolerance.

**Plan Mode does NOT implement plans automatically.**
- Generates plan documents only
- User decides which plan to implement
- Implementation happens in separate session (after review)

---

## Data Integrity Protocol (INHERITED FROM PARENT)

**Plan Mode follows SAME data integrity rules as Simulation Mode.**

```
+=========================================================================+
|                    DATA INTEGRITY PROTOCOL                               |
+=========================================================================+
|                                                                          |
|  Phase 0 (Problem):     API calls ALLOWED (research phase)              |
|  Phase 1 (Approaches):  API calls ALLOWED (validation)                  |
|  Phase 2 (Planning):    API calls ALLOWED (each agent researches)       |
|  Phase 3 (Analysis):    API calls FORBIDDEN (use cached plans)          |
|                                                                          |
|  Each planner agent MAY call APIs during planning.                      |
|  Analysis phase uses ONLY the plan documents generated.                 |
|                                                                          |
+=========================================================================+
```

**Why this matters:**
- Phase 2: Each planner agent can research independently (parallel execution)
- Phase 3: Analysis uses ONLY the plan documents (no new data fetching)
- Prevents: Inconsistent analysis due to changing external data

---

## Folder Structure

```
session/super_power/{YYYY-MM-DD}/
├── status.json              # Execution state
├── approaches.jsonl         # Approach specifications (Phase 0)
├── plan-1.md               # Implementation plan (Approach 1)
├── plan-2.md               # Implementation plan (Approach 2)
├── plan-3.md               # Implementation plan (Approach 3)
├── plan-4.md               # Implementation plan (Approach 4, optional)
├── plan-5.md               # Implementation plan (Approach 5, optional)
├── plan-comparison.md      # Final comparative report
└── audit.log               # Safety violation log (should be empty)
```

---

## Example: Real-Time Notifications Feature

**User Request:** "Use your superpower to plan adding real-time notifications to your product"

**Phase 0: Problem Definition**
```markdown
# Problem
Add real-time notifications to your product Android app so users are notified instantly when:
- A quote is approved
- A project status changes
- A message is received from sales team

## Success Criteria
- [ ] Notifications arrive within 5 seconds of event
- [ ] Notifications work when app is in background
- [ ] User can dismiss/snooze notifications
- [ ] Notifications include deep links to relevant screen

## Constraints
- Time: 3 weeks
- Resources: 1 Android developer (full-time)
- Tech Stack: Android/Kotlin, Supabase backend, Firebase (available)
- Existing Systems: your product app (300+ screens), Supabase PostgreSQL

## Approaches Identified

### Approach 1: Firebase Cloud Messaging (FCM)
- **Priority:** Simplicity & reliability
- **Complexity:** Low
- **Description:** Use Firebase's push notification service. Well-documented, battle-tested.

### Approach 2: Supabase Realtime + Local Notifications
- **Priority:** Cost efficiency (no Firebase)
- **Complexity:** Medium
- **Description:** Subscribe to Supabase Realtime channels, trigger local notifications.

### Approach 3: WebSockets + WorkManager
- **Priority:** Maximum control
- **Complexity:** High
- **Description:** Custom WebSocket connection, WorkManager for background tasks.

### Approach 4: Hybrid FCM + Supabase Triggers
- **Priority:** Best UX (instant + persistent)
- **Complexity:** Medium
- **Description:** FCM for push, Supabase triggers for event detection.

**Approve to proceed?**
```

**Phase 2: Parallel Planning**
```
4 planner agents spawn simultaneously:
- Agent 1: Planning FCM approach
- Agent 2: Planning Supabase Realtime approach
- Agent 3: Planning WebSockets approach
- Agent 4: Planning Hybrid approach

Each agent generates full implementation plan (~30 min).
```

**Phase 3: Comparative Analysis**
```markdown
# Plan Mode Comparison Report

## RECOMMENDED APPROACH

**Approach 4: Hybrid FCM + Supabase Triggers**
- **Score:** 87/100 (Grade: B)
- **Timeline:** 2.5 weeks
- **Complexity:** Medium
- **Risk:** Low

**Why this approach wins:**
1. Best UX (instant notifications + reliable delivery)
2. Leverages existing Firebase setup (already in project)
3. Moderate complexity (not over-engineered)
4. Low risk (both technologies proven in production)
5. Future-proof (easy to extend with rich notifications)

**Runner-Up:** Approach 1 (FCM standalone) scored 82/100
- Use if timeline is tight (2 weeks instead of 2.5)
- Slightly simpler but less integrated with Supabase

---

## HEAD-TO-HEAD COMPARISON

| Approach | Timeline | Complexity | Risk | Resources | Score | Grade |
|----------|----------|------------|------|-----------|-------|-------|
| **4. Hybrid FCM + Supabase** | 2.5 wks | Medium | Low | 1 dev | **87** | B ✅ |
| 1. FCM Standalone | 2 wks | Low | Low | 1 dev | 82 | B ✅ |
| 2. Supabase Realtime | 2.5 wks | Medium | Medium | 1 dev | 75 | C ⚠️ |
| 3. WebSockets | 4 wks | High | High | 1 dev | 58 | F ❌ |

---

## KEY DIFFERENCES

### Approach 4 vs Approach 1 (Top 2)
- **Approach 4 advantage:** Tighter Supabase integration, easier to add app-side filtering
- **Approach 1 advantage:** Simpler setup, 3 days faster
- **Decision point:** Choose 4 if Supabase integration matters; choose 1 if speed is critical

### Approach 4 vs Approach 2
- **Approach 4 advantage:** Works when app is closed (FCM push)
- **Approach 2 limitation:** Only works when app is open/background (not closed)
- **Decision point:** Approach 2 saves Firebase costs but sacrifices UX

### Why Approach 3 Failed
- 4-week timeline (2x longer than winner)
- High complexity (custom WebSocket handling, reconnection logic)
- High risk (many edge cases: network changes, battery optimization)
- Low score: 58/100 (Grade: F)

---

## RISKS & MITIGATION

### All Approaches (Shared Risks)
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Firebase API changes | Low | High | Pin Firebase version, monitor release notes |
| Notification permissions denied | High | High | Onboarding flow explains value, graceful degradation |

### Approach 4 Specific Risks
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Supabase trigger latency | Medium | Medium | Add timeout fallback to polling |
| Firebase quota exceeded | Low | High | Monitor usage, implement rate limiting |

---

## DETAILED BREAKDOWN

### Approach 4: Hybrid FCM + Supabase Triggers

**Phase 1: Firebase Setup (3 days)**
- Configure Firebase project
- Add FCM dependencies to app
- Implement token registration
- Test push delivery

**Phase 2: Supabase Triggers (4 days)**
- Create PostgreSQL triggers for events (quote approval, status change)
- Implement Cloud Function to send FCM messages
- Add notification payload formatting
- Test end-to-end flow

**Phase 3: Android UI (3 days)**
- Build notification UI (icons, layouts)
- Implement deep linking
- Add notification preferences screen
- Handle notification tap actions

**Phase 4: Testing & Polish (3 days)**
- E2E testing (all event types)
- Background/foreground testing
- Battery optimization testing
- User acceptance testing

**Total:** 13 days (2.5 weeks)

**Resource Requirements:**
- 1 Android developer (full-time)
- Firebase Cloud Messaging (free tier sufficient)
- Supabase Functions (existing plan)

**Testing Strategy:**
- Unit: 15 tests (token handling, payload parsing)
- Integration: 8 tests (FCM → app flow)
- E2E: 5 scenarios (all event types)
- Coverage: 80%

**Rollback Plan:**
1. Disable Supabase triggers
2. Remove FCM message sending logic
3. Revert Android app changes
4. Rollback time: 2 hours

---

## MEMORY IMPACT

- Learnings consolidated: 1 note
  - Decision: Real-Time Notifications - Hybrid FCM + Supabase Approach
- Wikilinks created: 4 connections
- Knowledge graph hubs: Connected to [[your product]], [[Supabase]], [[Firebase]]

---

## NEXT STEPS

If Approach 4 is selected:
1. Create Firebase project and configure FCM
2. Implement Phase 1 (Firebase setup) first
3. Schedule user testing after Phase 3
4. Plan rollout: beta group → full release

If timeline is critical (need 2 weeks):
- **Switch to Approach 1** (FCM standalone)
- Accept slightly less Supabase integration
- Still delivers core notification functionality
```

---

## Integration Points

**Called By:**
- `super-power.md` Phase -1 (Mode Selection)

**Calls:**
- `EnterPlanMode` tool (MANDATORY Phase 0)
- `ExitPlanMode` tool (after Phase 3)
- `Task` tool (spawn planner agents)
- `skills/meta/super-power-safety.md` (validation on every operation)
- `skills/meta/super-power-plan-mode-report-template.md` (report generation)
- `skills/meta/memory-consolidation.md` (auto-consolidation)

**Requires:**
- MCP tools (for research, if needed)
- WebFetch/WebSearch (for external research)
- Read/Grep/Glob (for code exploration)

---

## Performance Targets

| Metric | Target | Max |
|--------|--------|-----|
| Problem definition (Phase 0) | <5 min | 10 min |
| Approach specification (Phase 1) | <2 min | 5 min |
| Parallel planning (Phase 2) | <30 min | 45 min |
| Comparative analysis (Phase 3) | <10 min | 15 min |
| Safety violations | 0 | 0 |

---

## Validation Gates

**Before Phase 1:**
- [ ] Problem statement clear
- [ ] Success criteria defined
- [ ] Constraints identified
- [ ] 3-5 distinct approaches specified
- [ ] User approved approach list

**Before Phase 2:**
- [ ] approaches.jsonl exists and is valid
- [ ] All approaches are distinct (not duplicates)
- [ ] status.json initialized
- [ ] Agent count matches approach count

**Before Phase 3:**
- [ ] All planner agents completed
- [ ] All plan files exist (plan-1.md, plan-2.md, ...)
- [ ] No safety violations logged
- [ ] All plans follow template structure

**Before User Presentation:**
- [ ] Comparison table complete
- [ ] Recommended approach identified with rationale
- [ ] Runner-up documented (if exists)
- [ ] Risk summary present
- [ ] Memory consolidation complete

---

## Related Skills

**Parent:**
- `meta/super-power.md` - Main superpower framework (mode selection)

**Templates:**
- `meta/super-power-plan-mode-report-template.md` - Report structure

**Safety:**
- `meta/super-power-safety.md` - Validation logic (shared with simulation mode)

**Memory:**
- `meta/memory-consolidation.md` - Auto-consolidation protocol

---

*Plan Mode v1.0 | Generate → Compare → Decide | Always present options, never auto-implement*
