# Agent Tool Validator

**Version:** 1.0
**Purpose:** Pre-spawn validation and post-execution monitoring to enforce org governance

---

## Pre-Spawn Validation

### Validation Rules

**Before spawning ANY agent via Task tool, validate:**

1. **Tool Access Rules** - Agent has appropriate tools for assigned task
2. **Tier Compliance** - Agent tier matches tool access constraints
3. **Delegation Detection** - If C-suite agent is executing implementation work
4. **Capacity Check** - Agent not over-allocated (>85% utilization)

---

## Validation Matrix

### Tier 1: C-Suite (Coordination Only)

**Agents:** conductor, cto, cfo

**Allowed Tools:**
```yaml
- Bash (status commands only)
- Glob, Grep, Read
- WebFetch, WebSearch
- TodoWrite
- Skill
- ListMcpResourcesTool, ReadMcpResourcesTool
- Task (delegation)
```

**FORBIDDEN:**
```yaml
- Edit
- Write
- NotebookEdit
```

**Validation:**
```javascript
function validateCSuite(agent, task) {
  if (task.includes("implement") || task.includes("write code") || task.includes("build")) {
    return {
      valid: false,
      error: "C-suite cannot implement - must delegate to builder/designer/forge",
      suggestion: "Spawn conductor to coordinate, conductor spawns builder to implement"
    };
  }
  return { valid: true };
}
```

---

### Tier 2: VP Level (Oversight Only)

**Agents:** vp-engineering, vp-product, hr (limited)

**Allowed Tools:**
```yaml
- Bash (test runners, status)
- Glob, Grep, Read
- WebFetch, WebSearch
- TodoWrite
- Skill
- Task (delegation)
```

**Limited Edit/Write:**
- `hr` can Edit/Write agent definition files only (agents/*.md)

**Validation:**
```javascript
function validateVP(agent, task, targetFiles) {
  if (agent === "hr" && targetFiles.some(f => f.startsWith("agents/"))) {
    return { valid: true }; // HR can edit agent files
  }

  if (task.includes("implement") || task.includes("fix code") || task.includes("refactor")) {
    return {
      valid: false,
      error: "VP cannot implement - must delegate to specialists",
      suggestion: "Spawn builder/designer/forge for implementation work"
    };
  }

  return { valid: true };
}
```

---

### Tier 3: Management (Domain-Limited)

**Agents:** chief-of-staff, secretary, scrum-leader

**Domain Restrictions:**
- `chief-of-staff`: Can Edit/Write reports only (Reports/*.md)
- `secretary`: Can Edit/Write timeline only (Projects/*/index.md)
- `scrum-leader`: Can Edit/Write sprint docs only (sprints/*.md)

**Validation:**
```javascript
function validateManagement(agent, targetFiles) {
  const restrictions = {
    "chief-of-staff": file => file.startsWith("Reports/") && file.endsWith(".md"),
    "secretary": file => file.match(/Projects\/.*\/index\.md/),
    "scrum-leader": file => file.startsWith("sprints/") && file.endsWith(".md")
  };

  const allowed = restrictions[agent];
  const unauthorized = targetFiles.filter(f => !allowed(f));

  if (unauthorized.length > 0) {
    return {
      valid: false,
      error: `${agent} can only edit ${Object.keys(restrictions[agent])[0]} files`,
      unauthorized: unauthorized
    };
  }

  return { valid: true };
}
```

---

### Tier 4: Specialists (Full Access)

**Agents:** builder, designer, forge, professor, guardian, legal, janitor, proposal-writer

**Tool Access:** Unrestricted within domain

**Validation:**
```javascript
function validateSpecialist(agent, task) {
  // Specialists can use Edit/Write freely within their domain
  // Only validate they're not stepping outside domain

  const domains = {
    "builder": ["code", "tests", "config"],
    "designer": ["design", "UI", "components"],
    "forge": ["data", "ETL", "pipelines"],
    "professor": ["BIM", "your BIM tool", "education"],
    "guardian": ["QC", "audit", "review"],
    "legal": ["contracts", "agreements"],
    "janitor": ["cleanup", "maintenance"],
    "proposal-writer": ["proposals", "presentations"]
  };

  // For now, no domain validation (trust specialists)
  return { valid: true };
}
```

---

### Tier 5: Support (Read-Only)

**Agents:** scout, planner, analyst, validator, quick, scraper

**FORBIDDEN:**
```yaml
- Edit
- Write
- NotebookEdit
```

**Validation:**
```javascript
function validateSupport(agent, task) {
  if (task.includes("edit") || task.includes("write") || task.includes("create file")) {
    return {
      valid: false,
      error: "Support agents are read-only - cannot modify files",
      suggestion: "Spawn builder/designer for file modifications"
    };
  }
  return { valid: true };
}
```

---

## Post-Execution Monitoring

### Red Flags (Violations)

After agent completes task, check:

1. **Tool Count Exceeded**
   - C-suite used >15 tools → VIOLATION (should have delegated)
   - VP used >12 tools → WARNING (check if over-executing)
   - Management used >15 tools → WARNING

2. **Forbidden Tools Used**
   - C-suite used Edit/Write → CRITICAL VIOLATION
   - VP used Edit/Write (except HR on agent files) → CRITICAL VIOLATION
   - Support used Edit/Write → CRITICAL VIOLATION

3. **Delegation Failure**
   - C-suite spawned 0 agents but used >10 tools → VIOLATION (did work themselves)
   - Task marked "implementation" but no builder/designer/forge spawned → VIOLATION

---

## Validation Output Format

### Pre-Spawn Validation

```
┌─ AGENT VALIDATION ──────────────────────────────────────────┐
│ Agent: conductor (COO, Tier 1)                              │
│ Task: "Implement feature X"                                 │
│ Status: ❌ FAILED                                            │
│                                                              │
│ Error: C-suite cannot implement - must delegate             │
│ Suggestion: Spawn conductor to coordinate, conductor spawns │
│             builder to implement                             │
└──────────────────────────────────────────────────────────────┘
```

### Post-Execution Monitoring

```
┌─ EXECUTION MONITOR ─────────────────────────────────────────┐
│ Agent: conductor (COO, Tier 1)                              │
│ Task: "Design UniSuite pre-build workflow"                  │
│ Tool Count: 44 tools                                         │
│ Status: 🔴 CRITICAL VIOLATION                                │
│                                                              │
│ Issues:                                                      │
│ • Tool count exceeds C-suite limit (44 > 15)                │
│ • Used forbidden tool: Edit (6 times)                       │
│ • Used forbidden tool: Write (8 times)                      │
│ • Zero agents spawned (should have delegated to builder)    │
│                                                              │
│ Recommendation: Remove Edit/Write from conductor.md          │
└──────────────────────────────────────────────────────────────┘
```

---

## Integration with Gate System

### Gate v3.0+ Integration

**Position #1: Pre-Spawn Validation** (before ROUTES LOADED)

```
┌─ AGENT VALIDATION ──────────────────────────────────────────┐
│ Agent: conductor                                             │
│ Tier: 1 (C-Suite)                                            │
│ Tools: ✅ Compliant (coordination only)                      │
│ Task Type: Coordination (appropriate)                        │
└──────────────────────────────────────────────────────────────┘
```

**Position #N: Post-Execution Monitor** (after agents finish)

```
┌─ EXECUTION REPORT ──────────────────────────────────────────┐
│ [1] conductor - 8 tools ✅                                   │
│ [2] builder - 28 tools ✅                                    │
│ [3] guardian - 12 tools ✅                                   │
│                                                              │
│ Status: All agents within expected tool counts              │
└──────────────────────────────────────────────────────────────┘
```

---

## Implementation Checklist

### Phase 1: Pre-Spawn Validation
- [ ] Load agent definition file before spawning
- [ ] Extract agent tier from org-governance.md
- [ ] Check task description for implementation keywords
- [ ] Validate tool access against tier constraints
- [ ] Block spawn if validation fails
- [ ] Suggest correct delegation pattern

### Phase 2: Post-Execution Monitoring
- [ ] Track tool usage per agent (count Edit/Write calls)
- [ ] Check if agent spawned sub-agents when expected
- [ ] Flag violations to metrics.json
- [ ] Display violation report in gate output
- [ ] Log violations to session/violations-log.jsonl

### Phase 3: Metrics Dashboard
- [ ] Weekly agent tool usage report
- [ ] Violation trend analysis
- [ ] Top violators by agent
- [ ] Delegation effectiveness score
- [ ] Include in Monday morning briefing

---

## Testing Validation

### Test Case 1: C-Suite Delegation (Should Pass)

**Request:** "Add logging to auth module"

**Expected Flow:**
```
Main spawns conductor
Conductor investigates (Read 5 tools)
Conductor spawns builder → "Add logging to auth module"
Builder implements (Edit/Write 25 tools)
Conductor spawns guardian → "Review changes"
Guardian reviews (Read 10 tools)
Conductor reports back

Validation: ✅ PASS
- Conductor: 5 tools (within 15 limit)
- Conductor: 0 Edit/Write (compliant)
- Conductor: Spawned 2 agents (proper delegation)
```

---

### Test Case 2: C-Suite Over-Execution (Should Fail)

**Request:** "Add logging to auth module"

**Current Broken Flow:**
```
Main spawns conductor
Conductor implements directly (Edit/Write 44 tools)
Conductor reports back

Validation: ❌ FAIL
- Conductor: 44 tools (exceeds 15 limit) 🔴
- Conductor: Used Edit/Write (forbidden) 🔴
- Conductor: Spawned 0 agents (delegation failure) 🔴
```

---

## Validation CLI Commands

### Check Agent Compliance
```bash
# Check if agent definition is compliant
python .claude/scripts/validate-agent.py conductor

# Output:
# Agent: conductor (Tier 1: C-Suite)
# Tools: ✅ Compliant (coordination only)
# Edit/Write: ❌ Not present
# Status: PASS
```

### Audit All Agents
```bash
# Audit entire agent roster
python .claude/scripts/audit-all-agents.py

# Output:
# 23 agents audited
# ✅ 20 compliant
# ❌ 3 violations (conductor, cto, vp-engineering)
```

### Monitor Session
```bash
# Check for violations in current session
python .claude/scripts/check-violations.py

# Output:
# Session: 2026-02-09-1430
# Violations: 1
# • conductor: Tool count exceeded (44 > 15)
```

---

## Emergency Response

### If C-Suite Violation Detected:

1. **STOP** - Do not proceed with current task
2. **READ** this file (`skills/meta/agent-tool-validator.md`)
3. **VERIFY** agent definition file (agents/conductor.md)
4. **CHECK** if Edit/Write present in tools line
5. **ALERT USER** - Show violation report
6. **RECOMMEND FIX** - Point to org-governance.md
7. **OFFER TO FIX** - "Should I remove Edit/Write from conductor.md?"

---

**Last updated:** 2026-02-09
**Status:** Active - Enforce on all agent spawns
**Priority:** CRITICAL - C-suite violations block scaling
