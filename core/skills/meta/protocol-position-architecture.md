# Protocol Position Architecture v1.0

**Purpose:** Reference documentation for the 4-position execution flow system

**When to Use:** When understanding or debugging protocol execution order

---

## The 4-Position Flow

Every request flows through 4 distinct positions in strict order:

```
Position #0 → Position #1 → Position #2 → Position #3
  (Silent)     (Gate)       (Enforce)      (Execute)
```

---

## Position #0: Silent Enforcement (PRE-GATE)

**Timing:** BEFORE any output to user (even before [GATE])

**Actions (AUTOMATIC, NO OUTPUT):**
1. Read `session/enforcement.todo` (if exists)
2. Execute priority 0/1/2 actions from queue
3. Load memory from appropriate shard (<200ms)
4. Parse context into working memory

**Critical Rules:**
- Memory loading is INVISIBLE to user
- No [MEMORY] blocks shown
- Citations appear naturally in responses
- Must complete before Position #1

**Performance Target:** <200ms total

**Files Accessed:**
- `.claude/session/enforcement.todo`
- `.claude/session/shards/{project}-shard.json`
- `.claude/session/state.json`

---

## Position #1: Gate Output (MANDATORY)

**Timing:** First 200 characters of every response

**Purpose:** Declare intent before execution

**Output Formats:**

### Full Gate (Substantial Tasks)
```
[GATE] Project: {project} | Background: {active/spawning/none}

┌─ ORIGINAL REQUEST (SACRED) ─────────────────────────────┐
│ "{verbatim prompt - first 100 chars}..."                │
│ Goal: {interpreted goal}                                │
│ Done When: {success criteria}                           │
└─────────────────────────────────────────────────────────┘

┌─ ROUTES LOADED ─────────────────────────────────────────┐
│ • {primary_skill_path}                                  │
│ • {secondary_skills...}                                 │
└─────────────────────────────────────────────────────────┘

┌─ AGENTS ────────────────────────────────────────────────┐
│ Foreground: [N] arch  [N] techy  [N] uiux              │
│ Background: [N] growth                                  │
│ Total: {N} agents | Tier: {1-4} | Capacity: {max}       │
└─────────────────────────────────────────────────────────┘

┌─ PROTOCOL ──────────────────────────────────────────────┐
│ Classification: {substantial/trivial/quick-trigger}     │
│ Justification: {why this classification}                │
│ Plan Required: {YES/NO/SKIPPED}                         │
│ Growth Monitor: {SPAWNED (id)/NOT-NEEDED/MISSING}       │
└─────────────────────────────────────────────────────────┘
```

### Mini-Gate (Trivial/Quick Triggers)
```
[GATE] Project: {project} | Agents: [1] micro | Background: yes | Plan: no
```

**Validation:**
- [GATE] MUST appear in first 200 characters
- Every response requires gate output (zero tolerance)
- Minimum 1 agent always spawned ([1] micro for trivial)

**Post-Gate Actions (Substantial Tasks Only):**

For substantial tasks (full gate output), immediately after gate:

1. **Create/Update Context Anchor** (silent, <10ms):
   ```bash
   python scripts/update-context-anchor.py \
     --prompt "$(jq -r '.current_prompt.text' session/state.json)" \
     --goal "[extracted from gate ORIGINAL REQUEST]" \
     --phase "Planning" \
     --next-action "[first intended action]"
   ```

2. **Purpose:** Preserve task context for post-compaction recovery

3. **File:** `.claude/session/context-anchor.md`

**Why This Matters:**
If compaction occurs mid-task, context-anchor.md allows Claude to resume from exact point of interruption without forgetting original goal or losing track of progress.

---

## Position #2: Enforcement Queue Execution

**Timing:** After gate output, before user request execution

**Purpose:** Execute mandatory actions from hook-generated queue

**Queue File:** `.claude/session/enforcement.todo`

**Execution Rules:**

**Priority 0/1 (Substantial Tasks):**
- Execute ALL actions BEFORE responding
- Actions: CHECKPOINT_NOW, CONSOLIDATE_MEMORY, RECALL_MEMORY, SPAWN_GROWTH_MONITOR
- User waits for completion

**Priority 2 (Trivial Requests):**
- Respond to user FIRST
- Execute actions in background AFTER response

**After Execution:**
1. Update timestamps in state.json:
   - `scout.last_checkpoint`
   - `memory_system.last_recall`
   - `memory_system.last_consolidation`
2. Reset enforcement flags:
   - `enforcement.checkpoint_overdue = false`
   - `enforcement.must_spawn_scout = false`
3. Delete `enforcement.todo`

**Critical:** If queue exists but not executed → enforcement flags stay stale forever

---

## Position #3: User Request Execution

**Timing:** After enforcement queue complete

**Purpose:** Execute actual user request with full context

**Available Context:**
- Memory loaded (from Position #0)
- State recovered (from Position #0)
- Enforcement complete (from Position #2)
- Skills routed (from Position #1)
- Agents spawned (from Position #1)

**Execution:**
- Follow routes declared in Position #1 gate
- Use memory citations naturally (no [MEMORY] blocks)
- Spawn agents as declared in gate
- Update state.json when complete

---

## Flow Examples

### Example 1: Trivial Request (Simple Question)

```
User: "What is the your CRM max page size?"

Position #0:
  - Read enforcement.todo (none exists)
  - Load memory from meta-shard.json (180ms)
  - 5 notes loaded silently

Position #1:
  [GATE] Project: meta | Agents: [1] micro | Background: yes | Plan: no

Position #2:
  - No enforcement queue
  - Skip to Position #3

Position #3:
  - Answer using memory citation
  - "The your CRM max page size is 200 deals per request."
```

### Example 2: Substantial Task (Multi-Step Implementation)

```
User: "Implement the new reporting feature"

Position #0:
  - Read enforcement.todo:
    • SPAWN_GROWTH_MONITOR (Priority 1)
    • RECALL_MEMORY (Priority 0)
  - Load memory from your organization-shard.json (190ms)
  - 5 notes loaded silently

Position #1:
  [GATE] Project: your organization | Background: spawning

  ORIGINAL REQUEST: "Implement the new reporting feature"
  Goal: Add reporting functionality with export to Excel
  Done When: Report generates successfully with all fields

  ROUTES LOADED:
  • skills/workflows/planning/planning-phase.md
  • skills/tooling/reports.md

  AGENTS:
  Foreground: [1] arch  [2] techy
  Background: [1] growth
  Total: 4 agents | Tier: 2 | Capacity: 12

  PROTOCOL:
  Classification: substantial
  Plan Required: YES
  Growth Monitor: SPAWNED (ae63703)

Position #2:
  - Execute SPAWN_GROWTH_MONITOR → Task tool spawned
  - Execute RECALL_MEMORY → already done in Position #0
  - Update state.json timestamps
  - Delete enforcement.todo

Position #3:
  - Load planning-phase.md skill
  - Enter plan mode
  - Design implementation approach
  - Present to user for approval
```

---

## Position Violations (Common Mistakes)

### Violation 1: No Gate Output
**Symptom:** Response starts with tool use or explanation
**Impact:** Protocol validation fails, violation tracked in metrics.json
**Fix:** ALWAYS output [GATE] in first 200 characters

### Violation 2: Memory Output in Position #0
**Symptom:** [MEMORY] blocks shown to user
**Impact:** Poor UX, breaks silent loading paradigm
**Fix:** Memory loads invisibly, citations appear naturally in Position #3

### Violation 3: Skipping Enforcement Queue
**Symptom:** enforcement.todo exists but not executed
**Impact:** Flags stay stale, checkpoints never happen, memory never consolidates
**Fix:** Position #2 MUST read and execute queue when file exists

### Violation 4: Wrong Agent Count
**Symptom:** Gate shows [0] agents or insufficient agents for tier
**Impact:** No agent coverage, pattern detection missed
**Fix:** ALWAYS spawn minimum [1] micro, scale to tier capacity

---

## Position Timing

| Position | Target Time | Blocking? |
|----------|-------------|-----------|
| #0: Silent Enforcement | <200ms | No - runs before response |
| #1: Gate Output | <1ms | No - just text output |
| #2: Enforcement Queue | <1sec | Yes for P0/1, No for P2 |
| #3: User Request | Varies | Yes - actual work |

**Total Overhead (Positions 0-2):** <1.2 seconds for substantial tasks, <200ms for trivial

---

## Reference

**Full Protocol:** CLAUDE.md → Session Gate v3.0
**Position #0 Spec:** CLAUDE.md lines 13-28
**Enforcement Queue:** CLAUDE.md → Protocol Enforcement v5.2
**Hook Architecture:** Memory vault → Patterns/Hook-Architecture.md

---

**Last Updated:** 2026-01-21
**Version:** 1.0
**Status:** Reference Guide
