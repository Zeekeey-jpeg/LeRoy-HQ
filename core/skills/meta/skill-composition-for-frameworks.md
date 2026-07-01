# Skill Composition for Frameworks

**Version:** 1.0
**Type:** Meta-Skill (Architecture Pattern)
**Purpose:** How to combine existing skills into new frameworks
**Last Updated:** 2026-01-18

---

## Pattern Overview

**What is skill composition?**
The practice of building complex frameworks by combining existing, proven skills rather than building from scratch.

**Why compose instead of build new?**
- **Faster development:** Reuse working components (weeks → days)
- **Higher quality:** Tested skills have fewer bugs
- **Consistent patterns:** All frameworks use same building blocks
- **Easier maintenance:** Fix once, all frameworks benefit
- **Better documentation:** Skills already documented

**Key principle:** Frameworks are compositions of skills, not monoliths.

---

## Composition Model

### Building Blocks (Skill Types)

**1. Pattern Skills (How to do X)**
- `mandatory-phase-gating.md` - Plan-first pattern
- `dual-list-safety-pattern.md` - Safety validation
- `scenario-matrix-design.md` - Scenario generation
- `risk-classification-framework.md` - Risk assessment

**2. Template Skills (Reusable structures)**
- `simulation-report-template.md` - Report format
- `framework-documentation-standard.md` - Documentation structure
- `four-week-framework-rollout-template.md` - Implementation timeline

**3. Process Skills (Workflows)**
- `simulation-testing-methodology.md` - Testing process
- `memory-consolidation.md` - Knowledge capture
- `memory-recall.md` - Context loading

**4. Integration Skills (External connections)**
- `mcp-pagination.md` - MCP data fetching
- `request-disambiguation.md` - User input clarification
- Prediction engine integration

**5. Validation Skills (Quality gates)**
- Safety validation
- Performance target tracking
- Test coverage metrics

---

## Composition Patterns

### Pattern 1: Sequential Composition (Pipeline)
**Structure:** Skill A → Skill B → Skill C

**Use when:** Each skill's output feeds next skill's input

**Example: Skill Composer**
```
Parse → Disambiguate → Validate MCP → Generate → Validate Syntax →
Validate Security → Validate Tags → Validate Deps → Sandbox Test → Register
```

**Implementation:**
```python
class SkillComposer:
    def execute(self, user_request):
        # Step 1: Parse
        parsed = parse_skill(user_request)

        # Step 2: Disambiguate (blocks until resolved)
        if is_ambiguous(parsed):
            clarified = disambiguate_skill(parsed)
        else:
            clarified = parsed

        # Step 3: Validate MCP
        validated = validate_mcp_skill(clarified)

        # Step 4: Generate (uses template skill)
        generated = generate_from_template(validated)

        # Step 5-8: Validation pipeline
        syntax_checked = validate_syntax_skill(generated)
        security_checked = validate_security_skill(syntax_checked)
        tags_checked = validate_tags_skill(security_checked)
        deps_checked = validate_deps_skill(tags_checked)

        # Step 9: Test
        tested = sandbox_test_skill(deps_checked)

        # Step 10: Register
        return register_skill(tested)
```

### Pattern 2: Parallel Composition (Fan-Out/Fan-In)
**Structure:** Input → [Skill A, Skill B, Skill C] → Aggregate

**Use when:** Independent operations can run simultaneously

**Example: Super Power Execution Phase**
```
Scenarios → [Agent 1, Agent 2, ..., Agent N] → Aggregate Results
```

**Implementation:**
```python
def parallel_execution(scenarios, agent_count):
    # Split scenarios
    chunks = split(scenarios, agent_count)

    # Spawn agents in parallel (fan-out)
    agents = []
    for i, chunk in enumerate(chunks):
        agent = spawn_simulator_agent(
            agent_id=f"sim_{i}",
            scenarios=chunk
        )
        agents.append(agent)

    # Wait for all to complete
    wait_for_all(agents)

    # Aggregate results (fan-in)
    all_results = []
    for agent in agents:
        results = agent.get_results()
        all_results.extend(results)

    return all_results
```

### Pattern 3: Conditional Composition (Branching)
**Structure:** Input → Decision → [Skill A | Skill B]

**Use when:** Different paths based on input characteristics

**Example: Request Routing**
```python
def route_request(user_request):
    if is_simple_question(user_request):
        # Skip planning, answer directly
        return answer_directly_skill(user_request)

    elif is_simulation_request(user_request):
        # Use Super Power framework
        return super_power_skill(user_request)

    elif is_skill_generation(user_request):
        # Use Skill Composer
        return skill_composer_skill(user_request)

    else:
        # Disambiguate first
        clarified = disambiguate_skill(user_request)
        return route_request(clarified)
```

### Pattern 4: Recursive Composition (Nested)
**Structure:** Framework uses sub-frameworks

**Use when:** Complex frameworks need multiple layers

**Example: Super Power Framework**
```
Super Power
├── Phase 0: Planning
│   ├── Mandatory Phase Gating (pattern skill)
│   ├── Scenario Matrix Design (process skill)
│   └── Prediction Engine Query (integration skill)
│
├── Phase 1: Generation
│   └── Scenario Matrix Generation (pattern skill)
│
├── Phase 2: Execution
│   ├── Parallel Composition (pattern)
│   └── Safety Validation (per operation)
│       └── Dual-List Safety Pattern (pattern skill)
│
└── Phase 3: Report
    ├── Simulation Report Template (template skill)
    └── Memory Consolidation (process skill)
```

**Implementation:**
```python
class SuperPowerFramework:
    def __init__(self):
        # Compose from existing skills
        self.phase_gating = MandatoryPhaseGatingSkill()
        self.matrix_design = ScenarioMatrixDesignSkill()
        self.safety = DualListSafetySkill()
        self.report = SimulationReportTemplateSkill()
        self.memory = MemoryConsolidationSkill()

    def execute(self, user_request):
        # Phase 0: Planning (uses phase gating skill)
        plan = self.phase_gating.plan(
            target=user_request,
            matrix_designer=self.matrix_design
        )

        # Get approval
        if not plan.approved:
            return "Planning required"

        # Phase 1: Generation
        scenarios = self.matrix_design.generate(plan)

        # Phase 2: Execution (uses safety skill)
        results = []
        for scenario in scenarios:
            # Validate each operation
            if self.safety.validate(scenario.operations):
                result = execute(scenario)
                results.append(result)
            else:
                results.append(blocked_result(scenario))

        # Phase 3: Report (uses template skill + memory skill)
        report = self.report.generate(results)
        self.memory.consolidate(report.learnings)

        return report
```

---

## Composition Strategies

### Strategy 1: Identify Reusable Patterns
**Process:**
1. **Analyze existing frameworks** - What do they have in common?
2. **Extract patterns** - Generalize common logic into skills
3. **Document patterns** - Create pattern skills (like this one)
4. **Apply patterns** - Use in new frameworks

**Example:**
```markdown
**Pattern identified:** All frameworks need planning before execution

**Extracted skill:** `mandatory-phase-gating.md`

**Applied to:**
- Super Power framework
- Skill Composer (disambiguation step)
- Any future complex framework
```

### Strategy 2: Template-Based Composition
**Process:**
1. **Create templates** - Define structure with slots
2. **Fill slots** - Plug in framework-specific logic
3. **Validate** - Ensure template constraints met
4. **Extend** - Add custom sections if needed

**Example:**
```markdown
**Template:** `simulation-report-template.md` (7 sections)

**Slot-filling for Super Power:**
- Section 1 (Header): Super Power simulation metadata
- Section 2 (Highlights): Top findings from scenarios
- Section 3 (Scoring): Weighted formula (compliance 40%, performance 30%, ...)
- Section 4 (Gaps): Detected issues
- Section 5 (Risks & Rewards): Decision matrix
- Section 6 (Execution): Agent performance metrics
- Section 7 (Memory): Consolidated notes

**Result:** Structured report in <10 min
```

### Strategy 3: Layered Composition
**Process:**
1. **Layer 1 (Foundation):** Core logic, data structures
2. **Layer 2 (Patterns):** Apply design patterns (safety, gating, etc.)
3. **Layer 3 (Integration):** Connect to external systems (MCP, prediction engine)
4. **Layer 4 (Presentation):** Reports, user feedback

**Example: Skill Composer Layers**
```
Layer 4: Report (success/failure, skill path)
         └─ Layer 3: Integration (MCP registry, templates, git)
            └─ Layer 2: Patterns (disambiguation, safety validation)
               └─ Layer 1: Core (parsing, generation, testing)
```

---

## Examples from Existing Frameworks

### Example 1: Super Power Framework
**Composed from:**
```markdown
**Phase 0: Planning**
- `mandatory-phase-gating.md` - Forces planning before execution
- `scenario-matrix-design.md` - Designs test matrix
- Prediction engine integration - Suggests edge cases

**Phase 1: Generation**
- `scenario-matrix-design.md` - Generates scenarios from matrix

**Phase 2: Execution**
- Parallel composition pattern - Spawns agents
- `dual-list-safety-pattern.md` - Validates every operation
- `mcp-pagination.md` - Fetches complete datasets

**Phase 3: Report**
- `simulation-report-template.md` - Structures output
- `memory-consolidation.md` - Saves learnings
- `risk-classification-framework.md` - Classifies gaps

**Documentation:**
- `framework-documentation-standard.md` - 7-part structure

**Rollout:**
- `four-week-framework-rollout-template.md` - Implementation plan
```

**Result:** 1000+ line framework built from 10 skills

### Example 2: Skill Composer
**Composed from:**
```markdown
**Step 2 (Disambiguate):**
- `request-disambiguation.md` - Clarifies ambiguous requests

**Step 6 (Validate Security):**
- `dual-list-safety-pattern.md` - Blocks credentials, dangerous ops

**Step 7 (Validate Tags):**
- Memory system tag rules - Enforces tag structure

**Step 9 (Sandbox Test):**
- `simulation-testing-methodology.md` - Tests generated skill

**Step 10 (Register):**
- Git workflow patterns - Commits and tracks changes

**Documentation:**
- `framework-documentation-standard.md` - Structures skill doc
```

**Result:** 10-step pipeline built from existing skills + custom logic

### Example 3: LeRoy Report Factory
**Composed from:**
```markdown
**Data Fetching:**
- `mcp-pagination.md` - Gets complete datasets from MCP

**Analysis:**
- Postmortem analyzer - Calculates variance, scores

**Reporting:**
- `simulation-report-template.md` - Formats findings

**Distribution:**
- Email integration - Sends to recipients

**Memory:**
- `memory-consolidation.md` - Captures patterns
```

**Result:** 10-report factory built by composing data + analysis + output skills

---

## Composition Checklist

**When building new framework:**
- [ ] Identify similar existing frameworks (what can be reused?)
- [ ] List required capabilities (planning, execution, reporting, etc.)
- [ ] Map capabilities to existing skills
- [ ] Design composition pattern (sequential, parallel, conditional, nested)
- [ ] Implement composition using patterns
- [ ] Add framework-specific logic (fill gaps)
- [ ] Apply documentation standard
- [ ] Test using simulation methodology
- [ ] Create rollout plan (4-week template)

---

## Anti-Patterns

### ❌ Anti-Pattern 1: Monolithic Framework
**Problem:** Build everything from scratch, ignore existing skills

**Impact:** Slower development, bugs, inconsistent patterns

**Solution:** Always check for reusable skills first

### ❌ Anti-Pattern 2: Over-Composition
**Problem:** Compose so many skills that framework is fragile

**Impact:** Changes to one skill break entire framework

**Solution:** Balance composition (80% reuse) with custom logic (20%)

### ❌ Anti-Pattern 3: No Abstraction
**Problem:** Copy-paste skill code instead of importing/calling

**Impact:** Divergent implementations, maintenance nightmare

**Solution:** Always compose by reference, not duplication

### ❌ Anti-Pattern 4: Wrong Composition Pattern
**Problem:** Use sequential when parallel would work (or vice versa)

**Impact:** Performance issues, unnecessary blocking

**Solution:** Choose pattern based on dependencies (parallel if independent)

---

## Maintenance Benefits

**When fixing a bug in a skill:**
```
Before (monolithic): Fix bug in 5 frameworks separately
After (composition): Fix bug in 1 skill, all frameworks benefit
```

**When improving a pattern:**
```
Before: Rewrite logic in each framework
After: Update pattern skill once, all frameworks improve
```

**When adding new feature:**
```
Before: Implement in each framework manually
After: Add to appropriate skill, compose into frameworks
```

---

## Metrics

**Track composition effectiveness:**

| Metric | Target | Measurement |
|--------|--------|-------------|
| Code reuse | >80% | % of framework from existing skills |
| Development time | <2 weeks | Time to build new framework |
| Bug rate | <5 bugs | Bugs per framework (composed > monolithic) |
| Maintenance time | <1 hour | Time to apply bug fix across frameworks |

---

## Future Vision

**Skill library growth:**
```
2026-01: 10 pattern skills
2026-06: 25 pattern skills
2026-12: 50 pattern skills

Framework development time:
2026-01: 4 weeks (80% custom, 20% reuse)
2026-06: 2 weeks (50% custom, 50% reuse)
2026-12: 1 week (20% custom, 80% reuse)
```

**End goal:** Build any framework in days by composing proven skills.

---

## Related Skills

**Core composition skills:**
- `meta/mandatory-phase-gating.md` - Pattern skill
- `meta/dual-list-safety-pattern.md` - Pattern skill
- `workflows/scenario-matrix-design.md` - Process skill
- `tooling/simulation-report-template.md` - Template skill
- `meta/framework-documentation-standard.md` - Template skill
- `meta/simulation-testing-methodology.md` - Process skill
- `meta/risk-classification-framework.md` - Pattern skill
- `meta/quantified-performance-targets.md` - Pattern skill
- `meta/four-week-framework-rollout-template.md` - Template skill

**Integration skills:**
- `meta/mcp-pagination.md` - Integration pattern
- `meta/request-disambiguation.md` - Process skill
- `meta/memory-consolidation.md` - Process skill
- `meta/memory-recall.md` - Process skill

**Example frameworks using composition:**
- `meta/super-power.md` - Full simulation framework
- `meta/skill-composer.md` - Skill generation pipeline
- `workflows/leroy/factory.md` - Report factory

---

## Quick Start Guide

**Building your first composed framework:**

1. **Define framework goal** - What problem does it solve?
2. **List required capabilities** - Planning, execution, reporting, etc.
3. **Search for skills** - Check `skills/meta/`, `skills/workflows/`, `skills/tooling/`
4. **Map capabilities to skills:**
   ```markdown
   Capability: Planning → Skill: mandatory-phase-gating.md
   Capability: Safety → Skill: dual-list-safety-pattern.md
   Capability: Reporting → Skill: simulation-report-template.md
   ```
5. **Choose composition pattern:**
   - Sequential if skills must run in order
   - Parallel if skills can run simultaneously
   - Conditional if branching logic needed
   - Nested if complex multi-phase framework
6. **Implement composition** - Import/call skills, don't copy-paste
7. **Fill gaps** - Add custom logic for framework-specific needs (20%)
8. **Test** - Use simulation testing methodology
9. **Document** - Follow framework documentation standard (7 parts)
10. **Roll out** - Use 4-week rollout template

---

*Skill Composition for Frameworks v1.0 | Build faster, maintain easier | Compose, don't duplicate*
