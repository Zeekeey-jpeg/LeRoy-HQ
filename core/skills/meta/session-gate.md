---
name: session-gate
description: |
  Mandatory gate protocol v2.0 that enforces routing, agent deployment, and growth monitoring.

  Use when:
  - Starting ANY new session (automatic)
  - First response to any user request
  - Ensuring compliance with skills architecture

  Includes: Multi-resource gate, agent scaling tiers, protocol block, growth enforcement.
---

# Session Gate Protocol v2.0

**MANDATORY:** Every session response begins with the gate. No exceptions.

---

## The Gate (Full Format)

For substantial tasks, output the complete gate:

```
[GATE] Project: {project} | Background: {active/spawning/none}

┌─ ROUTES LOADED ─────────────────────────────────────────┐
│ • {primary_skill_path}                                  │
│ • {secondary_skill_path}                                │
│ • {additional_skills...}                                │
└─────────────────────────────────────────────────────────┘

┌─ AGENTS ────────────────────────────────────────────────┐
│ [N] {agent} - {org-title} ({task-description})         │
│ [N] {agent} - {org-title} ({task-description})         │
│ Background: [N] {agent} - {org-title}                   │
│ Total: {N} agents | Tier: {1-4} | Capacity: {max}       │
└─────────────────────────────────────────────────────────┘

┌─ PROTOCOL ──────────────────────────────────────────────┐
│ Classification: {trivial/substantial/quick-trigger}     │
│ Justification: {why this classification}                │
│ Plan Required: {YES-presenting/NO-trivial/SKIPPED}      │
│ Growth Monitor: {SPAWNED (id)/NOT-NEEDED/MISSING}       │
└─────────────────────────────────────────────────────────┘
```

## FLIGHT PLAN Box (Orchestration Architect)

On substantial prompts, the CTO auto-selects the execution modality stack (replacing
manual "A2A mesh / plan mode / workflow / debate" calls). When a `PLAN_EXECUTION_STRATEGY`
action is present in `enforcement.todo`, render this box **after the Position #0
enforcement box and before ROUTES LOADED**:

```
┌─ FLIGHT PLAN (CTO · Orchestration Architect) ───────────────┐
│ Running:     Plan → (A2A mesh [3] ∥ Workflow 4-stage) → Guard │
│ Why:         {rationale naming each fired signal}            │
│ Concurrent:  {what runs in parallel, or "—"}                 │
│ Debate:      {will trigger on {step} (stakes) | not triggered}│
│ Workflow:    {N-stage pipeline | not triggered}              │
│ Scale:       Tier-{1-4} · ~{N} packets · COO assigns crew    │
│ Proceeding ▸  (say "hold" to adjust)                         │
└──────────────────────────────────────────────────────────────┘
```

The CTO runs **all** modalities that fire — multiple combine (`∥` concurrent, `→` gated),
not a single pick. Then **auto-proceed** (announce-then-go). Full selection logic:
`skills/meta/execution-strategy-matrix.md`. Hook: `hooks/orchestration-planner.py`.
Absent in shadow mode or when `session/orchestration-planner.disabled` exists.

## The Gate (Compact Format)

For trivial tasks and quick triggers:

```
[GATE] Project: {project} | Route: direct | Agents: [0] | Background: none | Plan: no
```

---

## Gate Fields Reference

### Header Line

| Field | Required | Values | Purpose |
|-------|----------|--------|---------|
| Project | Yes | your org, your organization, an LMS, Meta/Skills, TBD | Working context |
| Background | Yes | active, spawning, none | Growth monitor status |

### Routes Loaded Block

| Field | Required | Notes |
|-------|----------|-------|
| Primary skill | Yes | Main skill being executed |
| Secondary skills | If applicable | Supporting skills loaded |
| Maximum | 5-7 | Don't overload - focus |

### Agents Block

| Field | Format | Example |
|-------|--------|---------|
| Agent display | `[N] name - Title (task)` | `[1] conductor - COO (coordination)` |
| Foreground | Active workers | Agents doing main work |
| Background | Silent workers | growth, data-forge batches |
| Total | Sum | Total agent instances |
| Tier | 1-4 | Scaling tier (see below) |
| Capacity | Max for tier | Maximum agents allowed |

**Title Mapping:** See `skills/meta/agent-org-titles.md` for complete agent → organizational title mapping.

### Protocol Block

| Field | Values | Meaning |
|-------|--------|---------|
| Classification | trivial, substantial, quick-trigger | Task complexity |
| Justification | Free text | WHY this classification |
| Plan Required | YES-presenting, NO-trivial, SKIPPED | Planning status |
| Growth Monitor | SPAWNED (id), NOT-NEEDED, MISSING | Monitoring status |

**WARNING SYMBOLS:**
- `SKIPPED` = Protocol violation (plan was required but skipped)
- `MISSING` = Protocol violation (growth monitor should be active)

---

## Growth Monitor State (BULLETPROOF v2.0)

**Survives compaction via persistent file.**

### State File Location
```
.claude/session/state.json
```

### Before EVERY Gate Output
1. **READ** `session/state.json`
2. Use `scout.active` to populate Growth Monitor field
3. If substantial task AND `active=false`:
   - Spawn growth monitor
   - Update state.json with task_id

### Growth Monitor Field Values
| Value | Meaning | Action |
|-------|---------|--------|
| `SPAWNED (task_id)` | Active and tracking | Read state.json for task_id |
| `NOT-NEEDED` | Trivial task | No growth monitor required |
| `MISSING` | **VIOLATION** | Should be active but isn't |
| `RECOVERING` | Post-compaction | Re-read state.json, continue monitoring |

### Recovery Protocol
After compaction, the hook banner shows state.json status:
1. Banner shows: `Growth Monitor: ACTIVE (task_id: xxx)`
2. Read state.json to recover full context
3. Continue monitoring without data loss

---

## Agent Scaling Tiers

### Tier Definitions

| Tier | Work Packets | Structure | Max Agents |
|------|--------------|-----------|------------|
| **Tier-1** | 1-3 | 1 arch + helpers | 5 |
| **Tier-2** | 4-9 | 1 arch + 2-3 sub-arch + helpers | 12 |
| **Tier-3** | 10-15 | 1 arch + 5 sub-arch + helpers | 18 |
| **Tier-4** | 16+ | 1 arch + ceil(packets/3) sub-arch + helpers | 20+ |

### Maximize Rule

```yaml
ALWAYS spawn to tier capacity, not minimum.

Example - Tier 2 task with 6 work packets:
  WRONG: [1] arch [1] techy (minimum)
  RIGHT: [1] arch [2] sub-arch [6] techy [1] sentinel (maximize)

Rationale: Parallel execution, faster completion, better quality
```

### Agent Count Notation

```yaml
Format: [N] type

Types:
  arch     = conductor
  techy    = builder
  uiux     = designer
  data     = forge
  sentinel = guardian
  bim    = professor
  growth   = scout

Examples:
  [1] arch [3] techy [1] sentinel
  [1] arch [2] sub-arch [5] techy [1] uiux
  [0] (trivial task, no agents)
```

### Sub-Architect Rules

```yaml
When to spawn sub-architects:
  - Tier-2 or higher
  - 4+ work packets
  - Need parallel streams

Sub-architect responsibilities:
  - Each handles max 3 work packets
  - Reports to main architect
  - Has own helper agents

Hierarchy:
  Main Architect
  ├── Sub-Arch 1 → [techy, uiux] → packets 1-3
  ├── Sub-Arch 2 → [techy, data] → packets 4-6
  └── Sub-Arch 3 → [techy, sentinel] → packets 7-9
```

---

## Enforcement Rules

### Rule 1: Gate First, Always

```yaml
BEFORE any tool call or response:
  1. Output [GATE] header
  2. Output ROUTES LOADED block (if substantial)
  3. Output AGENTS block (if substantial)
  4. Output PROTOCOL block (if substantial)
  5. THEN make first tool call

VIOLATION: Any tool call before gate = protocol breach
```

### Rule 2: First Tool Must Match Primary Route

```yaml
If Primary Route = "workflows/planning/planning-phase.md"
  → First Read tool: that file

If Primary Route = "integrations/crm-api.md"
  → First Read tool: that file

If Route = "direct"
  → May proceed with action
```

### Rule 3: Agent Count Accuracy

```yaml
SUBSTANTIAL TASK (3+ steps, multi-file):
  → Agents block REQUIRED
  → Minimum: [1] arch
  → Growth Monitor: MUST be SPAWNED
  → Plan: MUST be YES

QUICK TRIGGER:
  → Compact gate OK
  → Agents: [0] acceptable
  → Growth Monitor: NOT-NEEDED

TRIVIAL:
  → Compact gate OK
  → Agents: [0] acceptable
  → Plan: NO
```

### Rule 4: Growth Monitor Enforcement

```yaml
MANDATORY on substantial tasks:
  1. Spawn scout in background
  2. Show task_id in PROTOCOL block
  3. Check output at:
     - Task completion
     - Before any commit
     - Session end
     - User request ("growth report")
  4. ALWAYS surface [GROWTH] block (even if empty)

VIOLATION: Substantial task without growth monitor = MISSING status
```

---

## Classification Criteria

### Quick Triggers (Bypass Full Gate)

| Trigger | Route | Full Gate? |
|---------|-------|------------|
| "Morning" | routines/morning.md | No - compact |
| "hs report" | routines/crm-report.md | No - compact |
| "bim-tool connect" | routines/bim-connect.md | No - compact |

### Trivial Tasks (Compact Gate)

| Criteria | Example |
|----------|---------|
| Single question | "What time is my meeting?" |
| One-liner fix | "Fix that typo" |
| Direct file read | "Show me config.json" |
| Simple lookup | "Find company ID for Acme" |

### Substantial Tasks (Full Gate Required)

| Criteria | Must Have |
|----------|-----------|
| 3+ steps | Full gate + plan |
| Multi-file changes | Full gate + plan |
| New feature | Full gate + plan |
| Refactoring | Full gate + plan |
| Integration work | Full gate + agents |
| Architectural decisions | Full gate + plan |

---

## Project Detection

| Keywords | Project |
|----------|---------|
| your product, Command Center, precast, ExampleClient | your org |
| your product, QQ, Android | your organization |
| your CRM, ticketing, your CRM, your catalog service, CRM | your organization |
| a course, a course, LMS, quiz | an LMS |
| skills, agents, CLAUDE.md, meta, growth | Meta/Skills |

```yaml
No keywords detected:
  Project: TBD
  Action: Present numbered menu
  Rule: NO file operations until confirmed
```

---

## Growth Monitor Protocol

### Spawn Command

```yaml
Task tool:
  subagent_type: "general-purpose"
  run_in_background: true
  model: "haiku"
  description: "Growth monitor - background"
  prompt: |
    You are scout. Execute per agents/scout.md

    Monitor for:
    - Tool sequences (3+ same tools)
    - Clarification gaps (repeated questions)
    - Workflow patterns
    - Agent role gaps

    LOWERED THRESHOLD: Surface at 1+ patterns (not 3+)

    Track: {brief session context}
    Output: [GROWTH] format only when queried or session end
```

### Mandatory Checkpoints

| Checkpoint | Action |
|------------|--------|
| Task completion | Read growth monitor output, surface [GROWTH] |
| Before commit | Read growth monitor, surface before sentinel |
| User says "done" | Surface [GROWTH] block |
| Session ending | Final growth report |
| User requests | Immediate [GROWTH] output |

### Fresh Instance Protocol

```yaml
EVERY fresh Claude instance MUST:
  1. On first substantial task: spawn growth monitor
  2. Track patterns from conversation start
  3. Lower suggestion threshold (1+ not 3+)
  4. Surface suggestions aggressively
  5. Propose skills/agents when patterns detected

GOAL: Every session should identify growth opportunities
```

---

## Self-Correction

```yaml
If violation detected mid-session:
  1. STOP current action
  2. Output: "[GATE CORRECTION] Protocol violation detected. Resetting..."
  3. Output proper full gate
  4. Load proper routes
  5. Spawn growth monitor if missing
  6. Continue correctly
```

---

## Complete Workflow

```
USER INPUT RECEIVED

Step 1: Detect Project
  → Scan keywords
  → If unclear: TBD + menu

Step 2: Classify Task
  → Quick trigger? → Compact gate
  → Trivial? → Compact gate
  → Substantial? → Full gate

Step 3: Determine Resources
  → Count work packets
  → Select tier (1-4)
  → Assign agent counts
  → List skills to load

Step 4: Output Gate
  → Header line
  → ROUTES LOADED block (if substantial)
  → AGENTS block (if substantial)
  → PROTOCOL block (if substantial)

Step 5: Spawn Growth Monitor
  → If substantial: spawn immediately
  → Record task_id in PROTOCOL block

Step 6: Execute Primary Route
  → Read primary skill file
  → Follow skill instructions

Step 7: Track Progress
  → TodoWrite for task list
  → Update as completed

Step 8: Checkpoints
  → Surface [GROWTH] at completion
  → Check before commits
  → Final report at session end
```

---

## Examples

### Example 1: Substantial Task (Full Gate)

```
User: "Build a new your CRM ticket export feature"

[GATE] Project: your organization | Background: spawning

┌─ ROUTES LOADED ─────────────────────────────────────────┐
│ • workflows/planning/planning-phase.md                  │
│ • integrations/ticketing/tickets.md                   │
│ • tooling/reports.md                                    │
└─────────────────────────────────────────────────────────┘

┌─ AGENTS ────────────────────────────────────────────────┐
│ [1] conductor - COO (coordination & planning)           │
│ [2] builder - VP Delivery (feature implementation)      │
│ [1] guardian - Quality Sentinel (pre-commit review)     │
│ Background: [1] scout - VP Research                     │
│ Total: 5 agents | Tier: 1 | Capacity: 5                 │
└─────────────────────────────────────────────────────────┘

┌─ PROTOCOL ──────────────────────────────────────────────┐
│ Classification: substantial (new feature, 5 steps)      │
│ Justification: Multi-file, integration, needs design    │
│ Plan Required: YES - presenting below                   │
│ Growth Monitor: SPAWNED (task_id: abc123)               │
└─────────────────────────────────────────────────────────┘

[Proceeds with planning phase...]
```

### Example 2: Quick Trigger (Compact Gate)

```
User: "Morning"

[GATE] Project: your organization | Route: routines/morning.md | Agents: [0] | Background: none | Plan: no

[Reads morning.md, executes routine...]
```

### Example 3: Trivial Request (Compact Gate)

```
User: "What meetings do I have today?"

[GATE] Project: your organization | Route: direct | Agents: [0] | Background: none | Plan: no

[Calls calendar tool directly...]
```

### Example 4: Multi-Agent Tier-2 Task

```
User: "Refactor the entire authentication system"

[GATE] Project: your organization | Background: spawning

┌─ ROUTES LOADED ─────────────────────────────────────────┐
│ • workflows/planning/planning-phase.md                  │
│ • stacks/supabase/auth.md                               │
│ • web-development/frontend/architecture.md              │
└─────────────────────────────────────────────────────────┘

┌─ AGENTS ────────────────────────────────────────────────┐
│ [1] conductor - COO (orchestration)                     │
│ [2] conductor - Sub-Architect (stream coordination)     │
│ [4] builder - VP Delivery (implementation)              │
│ [1] designer - Design Lead (UI/UX)                      │
│ Background: [1] scout - VP Research                     │
│ Total: 9 agents | Tier: 2 | Capacity: 12                │
└─────────────────────────────────────────────────────────┘

┌─ PROTOCOL ──────────────────────────────────────────────┐
│ Classification: substantial (refactor, 8 work packets)  │
│ Justification: Multi-file, architectural, security      │
│ Plan Required: YES - presenting below                   │
│ Growth Monitor: SPAWNED (task_id: def456)               │
└─────────────────────────────────────────────────────────┘
```

---

## Pre-Action Checklist

```yaml
Before ANY tool call:
  - [ ] [GATE] header output
  - [ ] Classification justified
  - [ ] Appropriate gate format (full vs compact)
  - [ ] Agent counts match tier
  - [ ] Growth monitor status shown
  - [ ] Plan status accurate
  - [ ] First tool matches primary route
```

---

## Violation Reference

| Violation | Status Shows | Fix |
|-----------|--------------|-----|
| No gate before tools | - | GATE CORRECTION |
| Substantial without plan | SKIPPED | Present plan |
| No growth monitor | MISSING | Spawn immediately |
| Wrong tier | Undercapacity | Scale up agents |
| Route mismatch | - | GATE CORRECTION |

---

*Session Gate Protocol v2.0 | Multi-resource visibility, agent scaling, growth enforcement*
