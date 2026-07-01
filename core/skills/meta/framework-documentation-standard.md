# Framework Documentation Standard

**Version:** 1.0
**Type:** Meta-Skill (Documentation Pattern)
**Purpose:** 7-part structure for framework documentation
**Last Updated:** 2026-01-18

---

## Standard Overview

**The Rule:** ALL framework documentation follows this 7-part structure.

This ensures:
- Consistent documentation format across all frameworks
- Easy onboarding for new users
- Complete coverage of framework features
- Searchable patterns (all frameworks have same sections)
- Maintenance clarity (know where to update)

---

## 7-Part Structure

### Part 1: Header (Metadata)
**Purpose:** Context and identification

**Required fields:**
```markdown
# {Framework Name}

**Version:** {X.Y}
**Type:** {Meta Skill / Integration / Workflow / etc.}
**Purpose:** {One-sentence description}
**Architecture:** {High-level pattern - e.g., "Four-Phase (Planning → Generation → Execution → Report)"}
**Last Updated:** {YYYY-MM-DD}
```

**Optional fields:**
- **Trigger keywords:** {keywords that activate this framework}
- **Prerequisites:** {dependencies, required tools, credentials}
- **Status:** {Alpha/Beta/Production/Deprecated}

**Example:**
```markdown
# Super Power - Simulation Framework

**Version:** 1.0
**Type:** Meta Skill (System Enhancement)
**Purpose:** Run infinite loop simulations within controlled safety boundaries
**Architecture:** Four-Phase (Planning → Generation → Execution → Report)
**Last Updated:** 2026-01-18
```

### Part 2: Critical Rules (What MUST Happen)
**Purpose:** Non-negotiable constraints and enforcement

**Format:**
- Large ASCII box for visibility
- ALL CAPS for emphasis
- Bullet points for rules
- Consequences if violated

**Template:**
```markdown
## ⛔ CRITICAL: {RULE TITLE}

**MANDATORY RULE:** {One-sentence rule}

```
+===========================================================================+
|                    {RULE TITLE IN BOX}                                    |
+===========================================================================+
|                                                                           |
|  {Multi-line rule description}                                           |
|  {Enforcement details}                                                   |
|  {Consequences if violated}                                              |
|                                                                           |
+===========================================================================+
```

**Why this matters:**
- {Reason 1}
- {Reason 2}
- {Reason 3}

**If you skip {rule}:** {Consequence - system fails, data lost, etc.}
```

**Example:**
```markdown
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
|  └── Get approval before execution                                      |
|                                                                           |
+===========================================================================+
```

**Why planning is mandatory:**
1. User sees and approves approach before execution
2. Prevents wasted computation on wrong assumptions
3. Edge case identification before scenario generation

**If you skip planning:** Simulation will be blocked. This is enforced.
```

### Part 3: Quick Activation (How to Use)
**Purpose:** Fast reference for common use cases

**Format:**
- Table with triggers and actions
- Code examples for typical invocations
- Links to detailed sections

**Template:**
```markdown
## Quick Activation

| Trigger | Action |
|---------|--------|
| "{trigger phrase 1}" | {What happens} |
| "{trigger phrase 2}" | {What happens} |

**Examples:**
```code
{Code example 1}
```

```code
{Code example 2}
```

**See also:** {Links to detailed sections}
```

**Example:**
```markdown
## Quick Activation

| Trigger | Action |
|---------|--------|
| "use your superpower to [task]" | Full run: Plan → Generate → Execute → Report |
| "simulate [scenarios]" | Same as above |

**All triggers require planning phase first.**
```

### Part 4: What It Is (Conceptual Overview)
**Purpose:** High-level explanation without implementation details

**Format:**
- Analogy or metaphor (helps understanding)
- Capabilities list (what it can do)
- Safety boundaries (what it won't do)
- Use cases (when to use it)

**Template:**
```markdown
## What is {Framework Name}?

Think: **{Analogy}**.

This framework allows:
- {Capability 1}
- {Capability 2}
- {Capability 3}

**Safety First:** {Safety boundaries - read-only, no production writes, etc.}

---

## {Framework} Types (Use Cases)

### 1. {Use Case 1}
**Use:** "{Example trigger phrase}"

**Process:**
1. {Step 1}
2. {Step 2}
3. {Step 3}

**Output:** {What you get}

### 2. {Use Case 2}
**Use:** "{Example trigger phrase}"

**Process:**
{steps}

**Output:** {result}
```

**Example:**
```markdown
## What is a "Superpower"?

Think: **Neo learning kung fu + Doctor Strange seeing all outcomes**.

This framework allows:
- Simulating thousands of scenarios concurrently (within 1-hour limit)
- Pulling external data via WebFetch/WebSearch
- Testing system components with generated inputs

**Safety First:** Read-only operations. No production writes. Simulation environment only.
```

### Part 5: How It Works (Implementation Details)
**Purpose:** Step-by-step execution flow with code

**Format:**
- Phase breakdown (if multi-phase)
- Detailed process for each phase
- Code examples (Python, JavaScript, pseudo-code)
- Data structures (schemas, formats)

**Template:**
```markdown
## Phase {N}: {PHASE NAME} ({Duration estimate})

**Input:** {What this phase receives}

**Process:**
```code
# Step-by-step code or pseudo-code
{implementation}
```

**Output:**
- `{file_path}` - {Description}
- `{file_path}` - {Description}

---

## {Data Structure Name} Schema

```json
{
  "field1": "description",
  "field2": {
    "nested": "structure"
  }
}
```

**Field descriptions:**
- `field1` - {What it stores}
- `field2.nested` - {What it stores}
```

**Example:**
```markdown
## Phase 1: Scenario Generation (5 min)

**Input:** Approved plan from Phase 0

**Process:**
```python
# 1. Parse approved plan
scenario_matrix = extract_scenario_matrix(plan)

# 2. Generate base scenarios from matrix
base_scenarios = []
for combination in product(*scenario_matrix.values()):
    base_scenarios.append({
        'variables': dict(zip(scenario_matrix.keys(), combination)),
        'type': 'base'
    })

# 3. Write scenarios to manifest
write_manifest("session/super_power/{date}/scenarios.jsonl", scenarios)
```

**Output:**
- `session/super_power/{YYYY-MM-DD}/scenarios.jsonl` - All scenarios to execute
```

### Part 6: Integration Points (How It Connects)
**Purpose:** Show how framework fits into larger system

**Format:**
- Called by (what invokes this framework)
- Calls (what this framework invokes)
- Requires (dependencies)
- Outputs (what it produces for other systems)

**Template:**
```markdown
## Integration Points

**Called By:**
- {Skill/agent/user action that triggers this}
- {Another caller}

**Calls:**
- `{skill_path}` - {Why it calls this}
- `{tool_name}` - {Why it uses this tool}

**Requires:**
- {MCP tools needed}
- {Files/data that must exist}
- {Credentials/permissions}

**Outputs:**
- {File produced} - {Who consumes it}
- {Data updated} - {Who reads it}

---

## Related Patterns

**Combines well with:**
- **{Pattern 1}** - {How they work together}
- **{Pattern 2}** - {Integration point}

**See also:**
- `{skill_path}` - {Related skill}
- `{skill_path}` - {Another related skill}
```

**Example:**
```markdown
## Integration Points

**Called By:**
- User via quick trigger
- `@agent-conductor` for large-scale analysis

**Calls:**
- `EnterPlanMode` tool (MANDATORY Phase 0)
- `ExitPlanMode` tool (after plan approval)
- `skills/meta/super-power-safety.md` (validation on every operation)
- `skills/meta/memory-consolidation.md` (auto-consolidation)

**Requires:**
- MCP tools (for data fetching, if needed)
- WebFetch/WebSearch (for external data)
- Read/Grep/Glob (for code exploration)

---

## Related Patterns

**Combines well with:**
- **Mandatory Phase Gating** - Enforces planning before execution
- **Dual-List Safety Pattern** - Validates all tool calls

**See also:**
- `skills/meta/super-power-safety.md` - Safety validator
- `skills/meta/super-power-report-template.md` - Report format
```

### Part 7: Examples & Testing (Proof It Works)
**Purpose:** Real-world examples and validation

**Format:**
- Multiple examples (simple, complex, edge cases)
- Test checklist
- Success metrics
- Known issues (if any)

**Template:**
```markdown
## Examples

### Example 1: {Simple Use Case}
**User Request:** "{Example prompt}"

**Process:**
{Step-by-step walkthrough}

**Output:**
{Result shown to user}

---

### Example 2: {Complex Use Case}
**User Request:** "{Example prompt}"

**Process:**
{Walkthrough}

**Output:**
{Result}

---

## Testing Checklist

**Phase 1: {Phase Name}**
- [ ] {Test case 1}
- [ ] {Test case 2}

**Phase 2: {Phase Name}**
- [ ] {Test case 1}
- [ ] {Test case 2}

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| {metric_1} | {target} | {how to measure} |
| {metric_2} | {target} | {how to measure} |

---

## Known Issues

**Current State:** {Overall status - e.g., "Functional but degraded (Score: 7.4/10)"}

**Critical Issues:**
1. **{Issue title}** - {Description}
   - Cause: {Root cause}
   - Impact: {What breaks}
   - Fix: {How to resolve}

**Resolved:**
- ✅ {Resolved issue} - {Date fixed}
```

**Example:**
```markdown
## Example: Business Enhancement Study

**User Request:** "Use your superpower to study your CRM stage naming"

**Phase 0: PLANNING**
```
[EnterPlanMode tool called automatically]

1. Analyze target: your CRM stage configuration
2. Design scenario matrix:
   - Current: Stage 6 as single entity
   - Option A: Split by deal size
   - Option B: Split by timeline
3. Present plan to user
4. User approves
```

**Phase 1: GENERATION**
{...scenario generation details...}

**Output:**
{Full report with findings, scoring, recommendations}
```

---

## Optional Sections

### Performance Targets
**Use when:** Framework has specific performance requirements

**Template:**
```markdown
## Performance Targets

| Metric | Target | Max |
|--------|--------|-----|
| {operation} | {target time} | {max acceptable} |
| Safety violations | 0 | 0 |
```

### Validation Gates
**Use when:** Framework has checkpoints that must pass

**Template:**
```markdown
## Validation Gates

**Before Phase {N}:**
- [ ] {Prerequisite 1}
- [ ] {Prerequisite 2}

**Before {Action}:**
- [ ] {Check 1}
- [ ] {Check 2}
```

### Error Handling
**Use when:** Framework has specific error recovery patterns

**Template:**
```markdown
## Error Handling

| Condition | Action |
|-----------|--------|
| {error_type} | {recovery_action} |
```

### Future Enhancements
**Use when:** Framework has planned features not yet implemented

**Template:**
```markdown
## Future Enhancements (v{X}.0+)

1. **{Feature 1}** - {Description}
2. **{Feature 2}** - {Description}
```

---

## Anti-Patterns (What NOT to Do)

### ❌ Anti-Pattern 1: Missing Critical Rules Section
**Problem:** Users don't know what's mandatory vs optional

**Impact:** Framework misuse, violations, failures

**Solution:** Always include Part 2 (Critical Rules) with ASCII box

### ❌ Anti-Pattern 2: No Examples
**Problem:** Theory without practice is hard to understand

**Impact:** Users can't get started, abandoned framework

**Solution:** Always include Part 7 (Examples) with real use cases

### ❌ Anti-Pattern 3: Implementation Without Overview
**Problem:** Diving straight into code without explaining "what" and "why"

**Impact:** Users lost, can't adapt framework to their needs

**Solution:** Always include Part 4 (What It Is) before Part 5 (How It Works)

### ❌ Anti-Pattern 4: No Integration Points
**Problem:** Framework exists in isolation, no connections to ecosystem

**Impact:** Can't combine with other patterns, manual workflows

**Solution:** Always include Part 6 (Integration Points)

---

## Migration Guide

**Adding this standard to existing framework documentation:**

1. **Identify existing sections** - Map current content to 7-part structure
2. **Fill gaps** - Add missing parts (often Critical Rules or Integration Points)
3. **Reorganize** - Reorder to match standard structure
4. **Enhance** - Add examples, test checklists, success metrics
5. **Review** - Verify all 7 parts present and complete
6. **Update header** - Add version, last updated date

**Example mapping:**
```
Current structure:
- Introduction → Part 1 (Header) + Part 4 (What It Is)
- How to use → Part 3 (Quick Activation)
- Implementation → Part 5 (How It Works)

Missing:
- Part 2 (Critical Rules)
- Part 6 (Integration Points)
- Part 7 (Examples & Testing)

Action: Add missing parts, reorganize existing content
```

---

## Examples from Existing Frameworks

### Example 1: Super Power Framework
**File:** `skills/meta/super-power.md`

**Structure:**
1. **Header** - Version 1.0, Four-Phase architecture
2. **Critical Rules** - ⛔ CRITICAL: PLAN FIRST, SIMULATE SECOND (large ASCII box)
3. **Quick Activation** - Trigger table, all phrases require planning
4. **What It Is** - Analogy: Neo + Doctor Strange, capabilities, safety boundaries
5. **How It Works** - Phase 0-3 detailed, code examples, schemas
6. **Integration Points** - Called by user/agents, calls EnterPlanMode, requires MCP tools
7. **Examples & Testing** - Business study example, random curiosity example, test checklist

**Completeness:** 100% (all 7 parts present)

### Example 2: Skill Composer
**File:** `skills/meta/skill-composer.md`

**Structure:**
1. **Header** - Version 2.0, 10-step pipeline
2. **Critical Rules** - (Missing - should add mandatory disambiguation)
3. **Quick Activation** - Trigger keywords, when to use
4. **What It Is** - Purpose, when to use, when NOT to use
5. **How It Works** - 10-step generation pipeline, detailed
6. **Integration Points** - Called by user/agents, calls disambiguation, templates
7. **Examples & Testing** - 3 examples (simple, multi-step, conditional), metrics

**Completeness:** 85% (missing Part 2 Critical Rules section)

**Improvement:**
```markdown
## ⛔ CRITICAL: DISAMBIGUATION REQUIRED

**MANDATORY RULE:** NEVER skip disambiguation if request is ambiguous.

```
+===========================================================================+
|                    DISAMBIGUATION ENFORCEMENT                             |
+===========================================================================+
|                                                                           |
|  Step 2 (Disambiguate) BLOCKS execution until user clarifies.           |
|  44% of requests need disambiguation.                                    |
|  Proceeding without clarification leads to wrong skill generation.       |
|                                                                           |
+===========================================================================+
```

**Why this matters:**
- 44% of requests have ambiguous targets, credentials, or parameters
- Generating skill with wrong assumptions wastes time
- User must select specific option before continuing

**If you skip disambiguation:** Skill will be generated for wrong system/account/target.
```

### Example 3: Memory Consolidation
**File:** `skills/meta/memory-consolidation.md`

**Check against standard:**
- ✅ Part 1 (Header) - Present
- ✅ Part 2 (Critical Rules) - TAG RULES v1.0 (HARD CONSTRAINTS)
- ✅ Part 3 (Quick Activation) - Auto-triggered by enforcement
- ✅ Part 4 (What It Is) - Purpose, when to use
- ✅ Part 5 (How It Works) - Write path, tag validation, frontmatter
- ✅ Part 6 (Integration Points) - Called by growth monitor, checkpoints
- ✅ Part 7 (Examples & Testing) - Output examples, validation

**Completeness:** 100%

---

## Checklist for New Frameworks

**Before marking framework documentation "complete":**

- [ ] **Part 1: Header** - Version, type, purpose, architecture, last updated
- [ ] **Part 2: Critical Rules** - At least 1 non-negotiable rule in ASCII box
- [ ] **Part 3: Quick Activation** - Trigger table or code examples
- [ ] **Part 4: What It Is** - Analogy, capabilities, safety boundaries
- [ ] **Part 5: How It Works** - Step-by-step with code/pseudo-code
- [ ] **Part 6: Integration Points** - Called by, calls, requires, outputs
- [ ] **Part 7: Examples & Testing** - At least 2 examples, test checklist

**Optional but recommended:**
- [ ] Performance Targets table
- [ ] Validation Gates checklist
- [ ] Error Handling table
- [ ] Future Enhancements list
- [ ] Known Issues section

---

## Success Metrics

**How to measure documentation quality:**

| Metric | Target | Measurement |
|--------|--------|-------------|
| All 7 parts present | 100% | Checklist above |
| Time to understand framework | <15 min | New user feedback |
| Successful first use | >80% | % of users who execute correctly first try |
| Questions after reading | <10% | Support tickets / Slack questions |

---

## Related Standards

**See also:**
- `skills/tooling/simulation-report-template.md` - Report structure (7 sections)
- `skills/meta/mandatory-phase-gating.md` - Critical Rules example
- `skills/meta/dual-list-safety-pattern.md` - Integration Points example

---

*Framework Documentation Standard v1.0 | 7-part structure | Complete and consistent*
