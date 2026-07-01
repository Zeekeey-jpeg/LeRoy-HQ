---
user-invocable: false
---

# Agent Scaling Reference v1.0

**Purpose:** Tier system documentation + scaling decision guidance

**When to Use:** When determining how many agents to spawn for a task

**Critical Rule:** Always spawn to tier CAPACITY, not minimum

---

## The 4-Tier System

| Tier | Task Packets | Max Agents | Typical Distribution |
|------|--------------|------------|---------------------|
| **1** | 1-3 | 5 | [1] arch [2] techy [1] uiux [1] growth |
| **2** | 4-9 | 12 | [2] arch [6] techy [2] uiux [2] growth |
| **3** | 10-15 | 18 | [3] arch [9] techy [3] uiux [3] growth |
| **4** | 16+ | 20+ | [4] arch [12] techy [3] uiux [3] growth |

**Rule:** No single team handles >3 task packets

---

## What is a Task Packet?

**Definition:** An independent, parallelizable unit of work

**Examples:**

**1 Packet (Tier 1):**
- Single file implementation
- Bug fix in one component
- Simple feature addition

**3 Packets (Tier 1):**
- Frontend + Backend + Tests
- API endpoint + UI component + Documentation

**6 Packets (Tier 2):**
- Multi-file refactoring
- Feature with several components
- System integration with multiple touch points

**12 Packets (Tier 3):**
- Large feature implementation
- Architecture redesign
- Multi-system integration

**16+ Packets (Tier 4):**
- Full system overhaul
- Multiple interconnected features
- Complex migration project

---

## Agent Types and Roles

### Foreground Agents (Directly Execute Work)

| Agent | Abbreviation | Typical Work |
|-------|--------------|--------------|
| `@agent-conductor` | arch | Coordination, planning, QC |
| `@agent-builder` | techy | Code implementation |
| `@agent-designer` | uiux | UI design, components |
| `@agent-forge` | data | Large data operations (10K+) |

### Background Agents (Pattern Detection)

| Agent | Abbreviation | Auto-Spawned When |
|-------|--------------|-------------------|
| `@agent-scout` | growth | Substantial tasks (150+ chars + action keywords) |

### Special Purpose Agents

| Agent | When to Spawn |
|-------|---------------|
| `@agent-guardian` | ALWAYS before commits (mandatory) |
| `@agent-validator` | data validation workflows |
| `@agent-professor` | your BIM tool/BIM work |
| `@agent-quick` | Trivial requests (100% coverage) |

---

## Scaling Decision Tree

### Step 1: Count Task Packets

**Method:** Break work into independent, parallelizable units

**Questions:**
- How many files need changes?
- How many systems are involved?
- How many features/components?
- Can work be parallelized?

### Step 2: Determine Tier

```
Packets 1-3  → Tier 1 (5 agents)
Packets 4-9  → Tier 2 (12 agents)
Packets 10-15 → Tier 3 (18 agents)
Packets 16+   → Tier 4 (20+ agents)
```

### Step 3: Distribute to Capacity

**Tier 1 Example (5 agents):**
```
[AGENTS]
Foreground: [1] arch  [2] techy  [1] uiux
Background: [1] growth
Total: 5 agents | Tier: 1 | Capacity: 5
```

**Tier 2 Example (12 agents):**
```
[AGENTS]
Foreground: [2] arch  [6] techy  [2] uiux
Background: [2] growth
Total: 12 agents | Tier: 2 | Capacity: 12
```

**Tier 3 Example (18 agents):**
```
[AGENTS]
Foreground: [3] arch  [9] techy  [3] uiux
Background: [3] growth
Total: 18 agents | Tier: 3 | Capacity: 18
```

### Step 4: Adjust for Special Cases

**No UI work?**
- Redistribute uiux allocation to techy
- Example Tier 2: `[2] arch [8] techy [2] growth`

**Large data operations?**
- Swap techy for data-forge
- Example: `[2] arch [4] techy [2] data [2] growth`

**Commit required?**
- Add sentinel (mandatory)
- Example: `[2] arch [6] techy [2] uiux [1] sentinel [1] growth`

---

## Common Scaling Patterns

### Pattern 1: Single Feature Implementation (Tier 1)

**Work:**
- 1 API endpoint
- 1 UI component
- 1 test file

**Packets:** 3

**Scaling:**
```
[1] arch  → Coordinates + QC
[2] techy → API + tests
[1] uiux  → UI component
[1] growth → Background monitoring
```

### Pattern 2: Multi-Component Feature (Tier 2)

**Work:**
- 3 API endpoints
- 4 UI components
- Integration layer
- Test suites

**Packets:** 8

**Scaling:**
```
[2] arch  → Coordination + integration design
[6] techy → APIs + integration + tests
[2] uiux  → UI components
[2] growth → Background monitoring
```

### Pattern 3: System Redesign (Tier 3)

**Work:**
- Architecture planning
- 10 file refactoring
- 5 new components
- Database migration
- Full test coverage

**Packets:** 15

**Scaling:**
```
[3] arch  → Architecture + migration design + QC
[9] techy → Implementation + migration + tests
[3] uiux  → Component redesign
[3] growth → Background monitoring
```

### Pattern 4: Complex Integration (Tier 4)

**Work:**
- Multi-system integration
- 20+ file changes
- New API layer
- UI overhaul
- Data migration
- End-to-end testing

**Packets:** 20+

**Scaling:**
```
[4] arch  → System design + coordination + QC
[12] techy → Implementation across systems
[3] uiux  → UI overhaul
[3] growth → Background monitoring
```

---

## Scaling Anti-Patterns (AVOID)

### Anti-Pattern 1: Under-Scaling

**Bad:**
```
Task: Implement 8-component feature (Tier 2)
Agents: [1] arch [2] techy (Total: 3)
```

**Why Wrong:** Task requires 12 agents (Tier 2 capacity), not 3

**Fix:** Scale to tier capacity
```
Agents: [2] arch [6] techy [2] uiux [2] growth (Total: 12)
```

### Anti-Pattern 2: [0] Agent Count

**Bad:**
```
[GATE] Project: meta | Agents: [0] | Background: none
```

**Why Wrong:** Violates 100% agent coverage rule

**Fix:** ALWAYS spawn minimum [1] micro for trivial requests
```
[GATE] Project: meta | Agents: [1] micro | Background: yes
```

### Anti-Pattern 3: Single Team Overload

**Bad:**
```
Task: 15 packets (Tier 3)
Distribution: [1] arch [17] techy
```

**Why Wrong:** Techy team has >3 packets per agent

**Fix:** No team >3 packets, redistribute
```
Distribution: [3] arch [9] techy [3] uiux [3] growth
```

---

## Special Cases

### Trivial Requests (Priority 2)

**Pattern:** ALWAYS spawn [1] micro

**Example:**
```
User: "What is the your CRM max page size?"

[GATE] Project: meta | Agents: [1] micro | Background: yes | Plan: no
```

**Why:** 100% agent coverage - every request needs at least one agent

### Commit Workflow

**Pattern:** ALWAYS add sentinel before commits

**Example:**
```
User: "Create commit"

[AGENTS]
Foreground: [1] arch  [2] techy
Mandatory: [1] sentinel
Background: [1] growth
Total: 5 agents
```

**Why:** Sentinel is mandatory for pre-commit QC

### Large Data Operations (10K+ records)

**Pattern:** Use data-forge instead of techy

**Example:**
```
Task: Sync 45,000 tickets from your CRM (Tier 2)

[AGENTS]
Foreground: [2] arch  [4] data
Background: [2] growth
Total: 8 agents
```

**Why:** data-forge specialized for high-volume operations

---

## Agent Spawning Syntax

### Via Task Tool

```python
# Single agent spawn
Task(
    subagent_type="builder",
    prompt="Implement user authentication",
    description="Auth implementation"
)

# Background agent spawn
Task(
    subagent_type="scout",
    prompt="Monitor implementation patterns",
    description="Pattern detection",
    run_in_background=True
)
```

### Parallel Spawning (Preferred)

```python
# Spawn multiple agents in parallel (single message, multiple Task calls)
Task(subagent_type="builder", prompt="Implement API", description="API work")
Task(subagent_type="designer", prompt="Design UI", description="UI work")
Task(subagent_type="scout", prompt="Monitor", description="Pattern tracking", run_in_background=True)
```

---

## Validation Checklist

**Before finalizing agent scaling:**

1. ✅ Counted task packets correctly?
2. ✅ Selected appropriate tier?
3. ✅ Scaled to tier CAPACITY?
4. ✅ No team has >3 packets?
5. ✅ At least [1] agent (micro for trivial)?
6. ✅ Sentinel added if commit required?
7. ✅ Growth monitor spawned for substantial tasks?
8. ✅ Special agents added when needed?

---

## Reference

**Agent Index:** `agents/index.md`
**Session Gate:** CLAUDE.md → Session Gate v3.0
**Tier System:** CLAUDE.md lines 103-112
**Agent Deployment:** CLAUDE.md lines 251-260

---

**Last Updated:** 2026-01-21
**Version:** 1.0
**Status:** Reference Guide
