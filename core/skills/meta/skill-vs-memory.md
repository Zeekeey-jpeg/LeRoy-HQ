---
disable-model-invocation: true
---

# Skill vs Memory: Decision Criteria

**Version:** 1.0
**Last Updated:** 2026-01-13
**Purpose:** Define clear boundaries between what belongs in Skills vs LeRoy Memory

---

## Core Definitions

| Aspect | Skills | Memory |
|--------|--------|--------|
| **Nature** | Procedural ("how to do X") | Declarative ("what we know about X") |
| **Stability** | Static, version controlled | Dynamic, frequently updated |
| **Trigger** | Keywords, patterns, explicit invocation | Automatic recall when contextually relevant |
| **Structure** | Step-by-step procedures, templates | Facts, decisions, configurations, learnings |
| **Lifecycle** | Created deliberately, committed to git | Auto-consolidated from session work |
| **Reusability** | Same steps every time | Context-dependent application |

---

## Decision Criteria Table

| What You Have | Store As | Example |
|---------------|----------|---------|
| **Repeatable process** | Skill | "How to generate your CRM report" |
| **System fact** | Memory | "your CRM Stage 6 currently has 212 deals" |
| **Step-by-step workflow** | Skill | "Git commit workflow with Sentinel" |
| **Historical decision** | Memory | "We chose X approach for Y reason on Jan 10" |
| **Reusable template** | Skill | "Report output format structure" |
| **Environment config** | Memory | "your organization uses your CRM board ID 42" |
| **Trigger-action pattern** | Skill | "When user says 'morning', run briefing" |
| **Project-specific context** | Memory | "your product Command Center uses React + Supabase" |
| **Integration procedure** | Skill | "How to connect to your BIM connector MCP" |
| **API quirk/workaround** | Memory | "your CRM max page size is 200, always check pagination" |
| **Routing logic** | Skill | "How to detect project from keywords" |
| **Team roster** | Memory | "Scott O's email is scott@example.com" |

---

## Decision Tree

```
START: I learned/documented something
  │
  ├─> Is it a PROCESS (step 1, 2, 3...)?
  │   ├─> YES → Will these exact steps repeat?
  │   │   ├─> YES → SKILL
  │   │   └─> NO → Is it project-specific workaround?
  │   │       ├─> YES → MEMORY
  │   │       └─> NO → SKILL (generalized)
  │   └─> NO → Continue ↓
  │
  ├─> Is it a FACT about systems/people/config?
  │   └─> YES → MEMORY
  │
  ├─> Is it a DECISION we made?
  │   └─> YES → MEMORY
  │
  ├─> Is it a TEMPLATE/STRUCTURE to reuse?
  │   └─> YES → SKILL
  │
  └─> Is it CONTEXTUAL KNOWLEDGE about a project?
      └─> YES → MEMORY
```

---

## Detailed Examples

### Skill Examples

1. **Morning Briefing Routine**
   - **Why Skill:** Same steps every morning (calendar, tasks, reports)
   - **Location:** `routines/morning.md`

2. **your CRM Report Generation**
   - **Why Skill:** Repeatable process with specific formatting rules
   - **Location:** `routines/crm-report.md`

3. **Git Commit with Sentinel**
   - **Why Skill:** Standard workflow every commit
   - **Location:** `workflows/git/pr-workflow.md`

4. **catalog Validation**
   - **Why Skill:** Repeatable pattern (extract, cross-reference, report)
   - **Location:** `workflows/catalog-validation.md`

5. **Browser Automation Setup**
   - **Why Skill:** Step-by-step integration procedure
   - **Location:** `integrations/playwright/`

### Memory Examples

1. **your CRM Pipeline State**
   - **Why Memory:** Changes frequently, current state knowledge
   - **Content:** "Stage 6 has 212 deals totaling $8.9M as of 2026-01-10"
   - **Location:** `memory/integrations/crm/pipeline-state.md`

2. **Project Architecture Decision**
   - **Why Memory:** Historical context for future reference
   - **Content:** "your product Command Center: Chose Supabase over Firebase because..."
   - **Location:** `memory/projects/product/architecture-decisions.md`

3. **API Pagination Lesson**
   - **Why Memory:** Learned quirk, contextual application
   - **Content:** "your CRM Stage 6 report showed $5.6M with default limits, actual was $8.9M - ALWAYS use limit: 200"
   - **Location:** `memory/integrations/crm/pagination-lessons.md`

4. **Team Roster**
   - **Why Memory:** Changes as people join/leave
   - **Content:** "Scott O - you@example.com - Project Manager"
   - **Location:** `memory/team/roster.md`

5. **your CRM Configuration**
   - **Why Memory:** Environment-specific, may change
   - **Content:** "your organization production uses board ID 42 for service tickets"
   - **Location:** `memory/integrations/ticketing/config.md`

---

## Edge Cases & Resolutions

### Case 1: Integration Workaround
**Scenario:** Discovered your CRM API returns null for custom field X, workaround is to use field Y instead.

**Decision:** **MEMORY**
- **Why:** Specific to your CRM instance configuration
- **Might change:** If they fix the field mapping
- **Not procedural:** Just a fact to remember when writing queries

### Case 2: Report Format Template
**Scenario:** Excel output has specific header structure, font sizes, column widths.

**Decision:** **SKILL**
- **Why:** Reusable template every report
- **Won't change:** Standard format requirement
- **Procedural:** Apply these exact steps to format output

### Case 3: Error Recovery Pattern
**Scenario:** When Supabase RPC fails with "permission denied", retry after refreshing auth token.

**Decision:** **SKILL**
- **Why:** Repeatable recovery procedure
- **Generalizable:** Applies to all Supabase RPCs
- **Procedural:** If X error, then Y steps

### Case 4: Project Tech Stack
**Scenario:** your product uses React 18, Vite, Tailwind, Supabase, deployed on Vercel.

**Decision:** **MEMORY**
- **Why:** Project-specific context
- **May change:** Tech stack could evolve
- **Not procedural:** Just facts to know

### Case 5: Recurring Bug Symptom
**Scenario:** Every few weeks, your CRM API starts returning 429 errors, solution is to throttle requests.

**Decision:** **BOTH**
- **Memory:** "your CRM rate limits trigger around 100 req/min, observed 2025-12-15"
- **Skill:** If considering skill... Is this a one-time pattern or a reusable procedure?
  - If pattern recurs → Add throttling logic to `integrations/ticketing/` skill
  - If one-off → Keep as memory only

---

## Graduation Pathway: Memory → Skill

**When does knowledge become a skill?**

### Graduation Criteria

Promote memory to skill when **ALL** of these are true:

1. **Frequency:** Pattern has appeared **3+ times** in memory
2. **Stability:** Steps are **consistent** across occurrences
3. **Generalizability:** Applies to **multiple** projects/contexts
4. **Triggerable:** Can define **clear trigger** condition
5. **Benefit:** Automation would **save time** vs. manual application

### Graduation Process

1. **Detection (automatic):**
   - Growth monitor flags recurring patterns in `growth-history.md`
   - Memory organizer identifies duplicate procedures in vault

2. **Proposal:**
   - Claude suggests: "This pattern appeared 4 times. Promote to skill?"
   - Shows: frequency, consistency score, proposed trigger

3. **Creation:**
   - Extract procedure from memory examples
   - Generalize to template form
   - Create new skill file in appropriate folder
   - Update index.md routing

4. **Memory Update:**
   - Keep historical examples in memory (context)
   - Add cross-reference: "See `skills/X/Y.md` for procedure"

### Example Graduation

**Memory entries (3 occurrences):**
```
2025-12-01: When your catalog service import fails, check catalog publish status first
2025-12-15: your catalog service error → verified catalog publish status resolved issue
2026-01-05: Reminder: your catalog service imports need published catalog first
```

**Graduated to skill:**
```
Location: skills/integrations/catalog/troubleshooting.md

# your catalog service Import Troubleshooting

## Trigger
- User reports your catalog service import failure
- Error mentions catalog/product data

## Procedure
1. Check catalog publish status
   - `mcp__bom__bom_tool`
2. If unpublished → Publish first
   - `mcp__bom__bom_tool`
3. Retry import after publish completes
...
```

**Memory updated:**
```
Location: memory/integrations/catalog/known-issues.md

# Known Issues
- **Import failures:** Usually due to unpublished catalogs
  - See troubleshooting procedure: `skills/integrations/catalog/troubleshooting.md`
  - Historical occurrences: 2025-12-01, 2025-12-15, 2026-01-05
```

---

## Quick Reference Flowchart

```
┌─────────────────────────────────────────────────────┐
│ I need to save something I learned/documented       │
└───────────────────┬─────────────────────────────────┘
                    │
        ┌───────────┴───────────┐
        ▼                       ▼
   Process with           Fact/Context
   repeating steps?       about systems?
        │                       │
        YES                    YES
        │                       │
        ▼                       ▼
   Will exact steps      ┌──────────┐
   repeat next time?     │  MEMORY  │
        │                └──────────┘
    ┌───┴───┐
   YES     NO
    │       │
    ▼       ▼
┌────────┐ Is it project-specific
│ SKILL  │ or one-time workaround?
└────────┘      │
            ┌───┴───┐
           YES     NO
            │       │
            ▼       ▼
       ┌──────────┐ Generalize
       │  MEMORY  │ and make SKILL
       └──────────┘
```

---

## Integration Points

### 1. Session Consolidation
When consolidating session work to memory:
- **Growth monitor output** → Check for procedural patterns → Flag for skill consideration
- **Decisions made** → Always memory
- **Files created** → Memory (what/why)
- **Procedures repeated** → Flag if already in memory (possible graduation)

### 2. Skill Creation
When creating new skills:
- **Check memory first** → Is there related context?
- **Cross-reference** → Link to relevant memory notes
- **Document triggers** → How will this skill be invoked?

### 3. Memory Recall
When loading memory at session start:
- **Load declarative knowledge** → Facts, configs, decisions
- **Don't load procedures** → Those are in skills (already loaded)
- **Load context** → Historical decisions that explain WHY we do things certain ways

---

## Maintenance Rules

### For Skills
- **Version controlled** → All changes committed to git
- **Require review** → Architectural changes need validation
- **Update routing** → Keep index.md files current
- **Test triggers** → Ensure keywords/patterns still work

### For Memory
- **Auto-cleanup** → Weekly organizer removes stale/duplicate notes
- **Date-stamp important facts** → "As of 2026-01-10..."
- **Cross-reference skills** → When procedure exists, point to it
- **Archive old decisions** → Move to history subfolder after 6 months

---

## Summary

**SKILLS** = Executable procedures you want triggered automatically
**MEMORY** = Contextual knowledge you want recalled when relevant

**When in doubt:** Start with memory. If pattern repeats 3+ times, graduate to skill.

**Anti-pattern:** Putting facts in skills (causes stale data) or procedures in memory (causes inconsistent execution).

---

*Decision criteria established: 2026-01-13*
