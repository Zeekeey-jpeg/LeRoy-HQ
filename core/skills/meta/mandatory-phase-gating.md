# Mandatory Phase Gating Pattern

**Version:** 1.0
**Type:** Meta-Skill (Design Pattern)
**Purpose:** Enforce plan-before-execute workflow for complex frameworks
**Last Updated:** 2026-01-18

---

## Pattern Overview

**The Rule:** Complex frameworks MUST plan first, execute second. No exceptions.

This pattern ensures:
- Users see and approve approach before execution
- Prevents wasted computation on wrong assumptions
- Enables prediction engine integration during planning
- Forces edge case identification upfront
- Validates safety boundaries before any operations

---

## Core Components

### 1. Trigger Detection
**When to apply this pattern:**
- User requests complex operation (multi-step, multi-file, architectural)
- Framework involves >3 distinct phases
- Operation requires external data or expensive operations
- User needs visibility into approach before execution

**Keywords that trigger phase gating:**
- "use your superpower to..."
- "simulate..."
- "analyze..."
- "study..."
- Complex implementation requests

### 2. Mandatory Planning Phase
**What MUST happen:**
```
1. ENTER PLAN MODE
   - Use EnterPlanMode tool automatically
   - Signal to user: "Planning approach first..."

2. ANALYZE TARGET
   - What component/system is being addressed?
   - What data sources are available?
   - What constraints exist?

3. DESIGN APPROACH
   - What steps will be executed?
   - What inputs are required?
   - What outputs will be produced?
   - What risks exist?

4. ESTIMATE SCOPE
   - Timeline estimate
   - Resource requirements
   - Agent count (if applicable)

5. PRESENT PLAN
   - Show structured plan to user
   - Include: approach, steps, timeline, risks
   - Ask for explicit approval

6. GET APPROVAL
   - User MUST approve before proceeding
   - If rejected: adjust plan and re-present
   - If approved: exit plan mode and execute
```

### 3. Execution Gate
**Enforcement:**
- Cannot proceed to execution without plan approval
- Plan approval is BLOCKING (not optional)
- If user skips planning, framework displays error and halts

**Error message when gate violated:**
```
[GATE VIOLATION] Planning phase required

This framework requires planning before execution.

Please approve the simulation plan or provide feedback for adjustments.
```

---

## Implementation Pattern

### Template Code (Python)
```python
class PhaseGatedFramework:
    def __init__(self):
        self.plan_approved = False
        self.plan = None

    def execute(self, user_request):
        # PHASE 0: Planning (MANDATORY)
        if not self.plan_approved:
            self.plan = self.generate_plan(user_request)
            self.present_plan_to_user(self.plan)

            # BLOCKING - wait for approval
            approval = self.wait_for_user_approval()

            if not approval:
                return "Planning phase required. Framework halted."

            self.plan_approved = True

        # PHASE 1+: Execution (only after approval)
        return self.execute_plan(self.plan)

    def generate_plan(self, request):
        """
        Analyze request and generate structured plan.

        Returns:
            {
                "target": "what we're addressing",
                "approach": "how we'll do it",
                "steps": ["step 1", "step 2", ...],
                "timeline": "estimated duration",
                "risks": ["risk 1", "risk 2", ...],
                "resources": {"agents": N, "data_sources": [...]}
            }
        """
        pass

    def present_plan_to_user(self, plan):
        """
        Format and display plan for user review.

        Output format:
            # Framework Plan: {target}

            ## Approach
            {approach_description}

            ## Steps
            1. {step_1}
            2. {step_2}
            ...

            ## Timeline
            {estimated_duration}

            ## Risks
            - {risk_1}
            - {risk_2}

            ## Resources
            - Agents: {count}
            - Data sources: {list}

            **Approve to proceed?**
        """
        pass

    def wait_for_user_approval(self):
        """
        Block until user provides approval or rejection.

        Returns:
            True if approved, False if rejected
        """
        pass

    def execute_plan(self, plan):
        """
        Execute approved plan.

        Only called after plan_approved = True.
        """
        pass
```

### Template Code (Markdown Skill)
```markdown
## Execution Protocol

**MANDATORY RULE:** NEVER skip planning phase.

### Phase 0: PLANNING (REQUIRED)

**Trigger:** User requests framework execution

**Process:**
1. Enter plan mode: `[EnterPlanMode tool called automatically]`
2. Analyze target: {component/system being addressed}
3. Design approach:
   - Step 1: {description}
   - Step 2: {description}
   - ...
4. Estimate scope:
   - Timeline: {duration}
   - Resources: {agents/data}
5. Present plan:
   ```
   # Framework Plan: {Target}

   ## Approach
   {how we'll do it}

   ## Steps
   1. {step}
   2. {step}

   ## Timeline
   {duration}

   **Approve to proceed?**
   ```
6. Wait for approval (BLOCKING)

**If approved:** Exit plan mode, proceed to Phase 1
**If rejected:** Adjust plan, re-present

### Phase 1: EXECUTION

**Precondition:** Plan approved by user

**Process:**
{framework-specific execution steps}
```

---

## Integration with Planning Tool

**Frameworks using this pattern MUST:**
1. Call `EnterPlanMode` tool when triggered
2. Generate plan while in plan mode
3. Present plan to user
4. Wait for approval
5. Call `ExitPlanMode` tool after approval
6. Proceed to execution

**Example integration:**
```markdown
## Super Power Execution Protocol

**Phase 0: PLANNING (MANDATORY)**

**Trigger Detection:**
When user says "use your superpower to [task]", IMMEDIATELY call `EnterPlanMode` tool.

**Planning Activities:**
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

4. PRESENT PLAN
   Show user:
   - Simulation target
   - Scenario matrix
   - Data sources
   - Expected runtime
   - Predicted edge cases

5. GET APPROVAL
   User must approve before proceeding to Phase 1

**After Approval:**
Exit plan mode and proceed to scenario generation.
```

---

## Benefits

### 1. User Visibility
- User sees approach before execution
- Can provide feedback/adjustments
- Builds trust in framework

### 2. Reduced Waste
- Prevents executing wrong approach
- Catches misunderstandings early
- Saves computational resources

### 3. Prediction Engine Integration
- Planning phase is perfect time to query predictions
- Edge cases identified before scenario generation
- Improves simulation coverage

### 4. Safety Validation
- Boundaries validated during planning
- Risky operations caught before execution
- Audit trail starts at planning phase

### 5. Quality Control
- Forces framework designer to think through approach
- Structured plan format ensures completeness
- User approval creates accountability

---

## Anti-Patterns (What NOT to Do)

### ❌ Anti-Pattern 1: Optional Planning
```markdown
## Execution

**Optional:** You can plan first if you want.

**Process:**
1. Execute immediately
2. Hope for the best
```

**Why this fails:** Users skip planning, framework executes wrong approach, wastes time.

### ❌ Anti-Pattern 2: Implicit Approval
```markdown
## Planning Phase

1. Generate plan
2. Assume user approves (no explicit confirmation)
3. Proceed to execution
```

**Why this fails:** User didn't see or approve plan, may disagree with approach.

### ❌ Anti-Pattern 3: Planning After Execution
```markdown
## Execution

1. Execute first
2. Generate plan retroactively
3. Show to user
```

**Why this fails:** Too late to adjust approach, wasted computation, poor UX.

---

## Examples from Super Power Framework

### Example 1: Simulation Study
**User Request:** "Use your superpower to study your CRM stage naming"

**Phase 0 (Planning):**
```
[EnterPlanMode tool called automatically]

1. Analyze target: your CRM stage configuration
2. Design scenario matrix:
   - Current: Stage 6 as single entity
   - Option A: Split by deal size
   - Option B: Split by timeline
   - Option C: Keep as-is
3. Query prediction engine: "What scenarios should I test for stage optimization?"
   - Prediction: Test bottleneck detection, conversion rate impact
4. Present plan to user:

   # Simulation Plan: your CRM Stage Optimization

   ## Scenario Matrix
   | Stage Config | Deal Size Splits | Timeline Splits |
   |--------------|------------------|-----------------|
   | Current | N/A | N/A |
   | Option A | 3 | N/A |
   | Option B | N/A | 2 |

   **Total Scenarios:** 3

   ## Data Sources
   - Internal: your CRM deals (last 12 months, Stage 6)
   - Metrics: Conversion rate, time in stage, bottleneck detection

   ## Edge Cases (from prediction engine)
   - Deals stuck >90 days
   - Deals cycling back to earlier stages

   **Approve to proceed?**

5. User approves
6. Exit plan mode
```

**Phase 1 (Execution):**
Only happens after user approval. Generates scenarios and executes simulation.

---

## Validation Checklist

**Before implementing phase gating in a framework:**

- [ ] Framework has >2 distinct phases (planning + execution + ...)
- [ ] Framework involves expensive operations (API calls, large data processing)
- [ ] User needs visibility into approach before execution
- [ ] Planning phase can identify edge cases or risks
- [ ] Execution can be customized based on plan feedback

**If all checkboxes are TRUE:** Use mandatory phase gating pattern

---

## Related Patterns

**Combines well with:**
- **Prediction Engine Integration** - Query during planning phase
- **Safety Validation** - Validate boundaries during planning
- **Scenario Matrix Design** - Design matrix during planning
- **Risk Classification** - Assess risks during planning
- **Quantified Performance Targets** - Set targets during planning

**See also:**
- `skills/meta/super-power.md` - Full implementation example
- `skills/workflows/planning/planning-phase.md` - General planning patterns
- `skills/meta/simulation-testing-methodology.md` - Testing approach using phase gating

---

## Success Metrics

**How to measure if phase gating is working:**

| Metric | Target | Measurement |
|--------|--------|-------------|
| Plans presented to user | 100% | % of executions with prior plan |
| Plans approved without revision | >80% | % of first-try approvals |
| User satisfaction with approach | >90% | Qualitative feedback |
| Wasted execution (wrong approach) | <5% | % of executions that needed restart |

---

## Migration Guide

**Adding phase gating to existing framework:**

1. **Identify trigger keywords** - What user phrases activate framework?
2. **Create plan generation logic** - Extract from existing execution code
3. **Add EnterPlanMode call** - At framework start
4. **Structure plan output** - Use template format
5. **Add approval gate** - Block execution until approved
6. **Add ExitPlanMode call** - After approval, before execution
7. **Test with user** - Verify UX is clear and non-blocking

---

*Mandatory Phase Gating Pattern v1.0 | Plan first, execute second | Always*
