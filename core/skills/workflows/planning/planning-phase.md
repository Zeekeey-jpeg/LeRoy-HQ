# Planning Phase Workflow

**Purpose:** Ensure substantial tasks are planned before implementation to prevent wasted effort and scope creep.

---

## When to Use This Skill

Load this skill when:
- Task involves building new features
- Task modifies multiple files (3+)
- Task requires architectural decisions
- Task involves refactoring or restructuring
- User asks to "build", "create", "implement", "add feature"

---

## Quick Reference: Plan or Execute?

```
┌─────────────────────────────────────────────────────────────────┐
│                     TASK CLASSIFICATION                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  EXECUTE IMMEDIATELY (No Planning)                              │
│  ├── Quick triggers (morning, hs report, bim-tool connect)          │
│  ├── Single-file changes                                        │
│  ├── Read-only queries and lookups                              │
│  ├── Obvious bug fixes (single line)                            │
│  ├── User says "just do it" / "skip planning"                   │
│  └── User provides complete spec (no decisions needed)          │
│                                                                 │
│  PLAN FIRST (Substantial Tasks)                                 │
│  ├── New features / components                                  │
│  ├── Multi-file modifications (3+)                              │
│  ├── API integrations                                           │
│  ├── Database schema changes                                    │
│  ├── Refactoring / restructuring                                │
│  ├── UI/UX changes                                              │
│  └── Anything with multiple valid approaches                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Planning Process

### Step 1: Acknowledge

When substantial task detected, immediately signal:

```
This requires planning. Let me explore the codebase and outline an approach.
```

### Step 2: Explore

Before creating plan, gather context:

```yaml
Exploration Checklist:
  - [ ] Read existing related files
  - [ ] Understand current patterns/conventions
  - [ ] Identify dependencies
  - [ ] Note any constraints (APIs, schemas, etc.)
  - [ ] Check for similar implementations to follow
```

### Step 3: Present Plan

Use this **MANDATORY** template. All sections required:

```markdown
## Plan: [Feature/Task Name]

---

### Skills Loaded

| Skill | Path | Purpose |
|-------|------|---------|
| [skill-name] | `category/skill.md` | Why needed |
| [skill-name] | `category/skill.md` | Why needed |

---

### Agent Team

**Resource Summary:**
```
Foreground: [N] arch  [N] techy  [N] uiux  [N] other
Background: [N] growth
Total: {N} agents | Tier: {1-4} | Capacity: {max}
```

**Assignments:**
| Agent | Count | Responsibility | Packets |
|-------|-------|----------------|---------|
| arch | [1] | Overseer, coordination | All |
| techy | [N] | Implementation | 1-3, 4-6... |
| uiux | [N] | Design/styling | UI packets |
| sentinel | [1] | Commit QA | Final |
| growth | [1] | Pattern detection | Background |

**Sub-Architects (Tier 2+):**
- Sub-Arch 1: [techy, uiux] → packets 1-3
- Sub-Arch 2: [techy, data] → packets 4-6

---

### Pre-Scan Results (MANDATORY for file creation)

```yaml
Target Directory: [path]
Existing Files: [count] files found
Naming Conflicts: [none/list]
Content Overlap: [none/list]
Recommendation: [PROCEED/RENAME/MERGE]
```

---

### Goal
[One sentence: what are we building and why]

### Scope
**In Scope:**
- Item 1
- Item 2

**Out of Scope:**
- What we're NOT touching
- Future work deferred

### Approach
[Brief description of how we'll implement this]

**Key Decisions:**
- Decision 1: [choice] because [reason]
- Decision 2: [choice] because [reason]

### Files to Modify/Create

| File | Action | Purpose |
|------|--------|---------|
| `path/to/file.ts` | Modify | Add new function |
| `path/to/new.ts` | Create | New component |

### Implementation Steps

1. **[Step Title]**
   - Deliverable: [what gets created/changed]
   - Agent: @agent-[assigned]
   - Dependencies: [what must exist first]

2. **[Step Title]**
   - Deliverable: [what gets created/changed]
   - Agent: @agent-[assigned]
   - Dependencies: [step 1]

3. ...

### Testing Strategy
- How we'll verify the implementation works

### Risks / Considerations
- Any gotchas, edge cases, or dependencies to watch

---

### New Agent Suggestions

Based on this work, consider creating:

| Agent | Purpose | Evidence |
|-------|---------|----------|
| @agent-[name] | [role] | [pattern observed] |

*(If no suggestions, write: "None identified")*

---

### Ready to proceed?
[1] Yes, execute this plan
[2] Modify - [tell me what to change]
[3] Cancel
```

### Template Field Reference

| Field | Required | Notes |
|-------|----------|-------|
| Skills Loaded | YES | Every skill being used |
| Agent Team | YES | At minimum: Overseer + 1 helper |
| Pre-Scan Results | YES (for file creation) | Skip for non-file tasks |
| Goal | YES | One sentence |
| Scope | YES | In/out clearly defined |
| Files | YES | Every file touched |
| Steps | YES | Each with agent assignment |
| Agent Suggestions | YES | Minimum: "None identified" |

### Step 4: Wait for Approval

**CRITICAL:** Do NOT start implementation until user responds with approval.

Valid approvals:
- `1`, `yes`, `proceed`, `go`, `do it`, `approved`
- Any affirmative response

### Step 5: Execute with Tracking

Once approved:

1. Create TodoWrite items for each step
2. Work through steps sequentially
3. Mark todos complete as you go
4. Report progress at each milestone

---

## Plan Variants

### Quick Plan (Lightweight)

For smaller substantial tasks, use condensed format:

```markdown
**Plan:** [One-line description]

**Changes:** file1.ts, file2.ts, file3.ts

**Steps:**
1. [Step] → [deliverable]
2. [Step] → [deliverable]
3. [Step] → [deliverable]

Proceed? [y/n]
```

Trigger with: `[quick plan]` in request

### Detailed Plan (Complex Features)

For large features, add:
- Sequence diagrams (mermaid)
- API contract definitions
- Database schema changes
- Migration strategy
- Rollback plan

---

## Planning Anti-Patterns

**AVOID:**

| Anti-Pattern | Instead |
|--------------|---------|
| Planning simple tasks | Just execute |
| Over-planning | Keep plans actionable, not exhaustive |
| Planning without reading code | Explore first |
| Vague steps ("implement feature") | Specific deliverables |
| Starting before approval | Always wait |
| Ignoring plan during execution | Follow or re-plan |

---

## Integration with Agent Framework

### Mandatory Agent Team Structure

**RULE: Overseer ALWAYS needs at least one helper agent.**

There is NO minimum task count required. Every substantial task gets:

```yaml
ALWAYS Required:
  Overseer: @agent-conductor
  Helper: At least 1 specialist agent

Common Combinations:
  Code work: Architect + Techy
  UI work: Architect + UIUX + Techy
  Data work: Architect + DataForge
  Commit: Architect + Sentinel (MANDATORY)
  BIM work: Architect + your BIM tool-BIM-Instructor

Scaling (>3 task packets):
  Tier-2 structure with sub-architects
  Each sub-architect gets max 3 packets
```

### Workflow

1. **Architect** creates the plan (with skills, agents, pre-scan)
2. **User** approves the plan
3. **Architect** delegates to specialists (Techy, UIUX, etc.)
4. **Sentinel** validates scope adherence (ALWAYS before commit)
5. **Architect** suggests new agents if patterns emerge

The plan becomes the source of truth for scope validation.

---

## Examples

### Example 1: New API Endpoint

```
User: "Add an endpoint to fetch user analytics"

Claude: This requires planning. Let me explore the API structure...

[Reads existing routes, services, types]

## Plan: User Analytics Endpoint

### Goal
Add GET /api/users/:id/analytics endpoint returning usage metrics.

### Scope
**In Scope:** API route, service method, response typing
**Out of Scope:** Frontend display, caching, real-time updates

### Approach
Follow existing endpoint patterns in `/api/users/`. Use existing analytics service.

### Files to Modify/Create
| File | Action | Purpose |
|------|--------|---------|
| `src/routes/users.ts` | Modify | Add route handler |
| `src/services/analytics.ts` | Modify | Add getUserAnalytics() |
| `src/types/analytics.ts` | Create | Response types |

### Steps
1. Define response types in analytics.ts
2. Add service method with database query
3. Add route handler with validation
4. Add tests

Proceed? [1] Yes [2] Modify [3] Cancel
```

### Example 2: Skip Planning

```
User: "Fix the typo in the header component"

Claude: [Directly fixes typo - no planning needed for single-line change]
```

---

## Checklist Before Starting Implementation

- [ ] Plan presented to user
- [ ] User explicitly approved (1/yes/proceed)
- [ ] TodoWrite items created for steps
- [ ] First step marked as in_progress
- [ ] Relevant files read and understood

---

## A2A Mesh (v3.0)

Planning is the first broadcast point. When Step 3 (Plan Presentation) completes and user approves:

1. Conductor writes the approved plan to cache so all assigned agents have shared context without a conductor round-trip:

```
[A2A:BROADCAST]
key: planning.{task_slug}.approved_plan
data: { "packets": [...], "agent_assignments": {...}, "files_to_modify": [...] }
ttl: session
[/A2A:BROADCAST]
```

2. Each specialist agent (builder, designer, forge) SUBSCRIBES to that key on spawn instead of waiting for conductor to relay the brief.

3. When a specialist completes a packet, it writes its output to cache:
```
[A2A:BROADCAST]
key: planning.{task_slug}.packet_{n}.complete
data: { "files_modified": [...], "decisions": [...], "notes": "..." }
[/A2A:BROADCAST]
```

4. Guardian SUBSCRIBES to all `planning.{task_slug}.packet_*.complete` keys before starting its audit — no conductor handoff required.

**DELEGATE example (conductor → builder for code packet):**
```
[A2A:DELEGATE]
target: builder
capability: code-implementation
input: { "packet": 1, "spec": "...", "cache_key": "planning.{task_slug}.approved_plan" }
priority: HIGH
reason: Approved plan packet assignment — builder reads full context from cache
[/A2A:DELEGATE]
```

---

*Planning Workflow v2.1.0 | Mandatory Skills/Agents/Pre-Scan Format | Protocol Block Integration*
