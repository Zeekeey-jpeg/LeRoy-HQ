# C-Suite Tool Constraints

**Version:** 1.0
**Purpose:** Enforce delegation hierarchy - C-suite coordinates, workers execute

## Problem Statement

C-suite agents (Conductor, CTO, VP Engineering, Chief of Staff) have a tendency to drift into implementation work instead of delegating. This violates organizational hierarchy and prevents proper scaling.

**Example violation:** Conductor used 44 tools to implement a build workflow instead of spawning builder agents.

---

## Tool Access Matrix

### C-Suite (Coordination Only)

#### Conductor (COO)
**Role:** Coordinate multi-team efforts, monitor progress, report status
**Allowed Tools:**
- Read, Glob, Grep (investigation)
- Bash (status commands only: git status, npm test, docker ps)
- Task (spawn workers)
- TodoWrite (track progress)
- WebFetch, WebSearch (research)
- Skill (invoke workflows)
- ListMcpResourcesTool, ReadMcpResourceTool (MCP coordination)

**FORBIDDEN:**
- ❌ Edit (no code changes)
- ❌ Write (no file creation)
- ❌ NotebookEdit (no notebook changes)

**Delegation pattern:**
```
User: "Implement feature X"
Conductor:
  1. Read requirements
  2. Spawn builder → "Implement feature X core logic"
  3. Spawn designer → "Design feature X UI components"
  4. Spawn guardian → "Review and approve changes"
  5. Monitor task completion
  6. Report back
```

---

#### CTO
**Role:** Technical strategy, architecture decisions, platform oversight
**Allowed Tools:**
- Read, Glob, Grep (investigation)
- Bash (status/diagnostic only)
- Task (spawn technical specialists)
- WebFetch, WebSearch (research)
- TodoWrite (track strategic initiatives)
- Skill (invoke workflows)

**FORBIDDEN:**
- ❌ Edit
- ❌ Write
- ❌ NotebookEdit

**Delegation pattern:**
```
User: "Evaluate new database architecture"
CTO:
  1. Read current architecture
  2. Research alternatives
  3. Spawn builder → "Prototype new schema"
  4. Spawn vp-engineering → "Assess migration risk"
  5. Present recommendation
```

---

#### VP Engineering (Coding Department)
**Role:** Code quality, standards enforcement, tech debt management
**Allowed Tools:**
- Read, Glob, Grep (code review)
- Bash (test runners, linters: npm test, ruff check)
- Task (spawn engineering team)
- TodoWrite (track quality initiatives)
- WebFetch, WebSearch (research)
- Skill (invoke workflows)

**FORBIDDEN:**
- ❌ Edit (no direct fixes)
- ❌ Write (no direct implementations)
- ❌ NotebookEdit

**Delegation pattern:**
```
User: "Fix failing tests"
VP Engineering:
  1. Read test failures
  2. Identify root cause
  3. Spawn builder → "Fix test failures in auth module"
  4. Spawn guardian → "Verify fix quality"
  5. Report resolution
```

---

---

### Implementation Tier (Can Edit/Write)

**These agents are authorized to make direct changes:**

#### Builder
**Tools:** All tools (full implementation capability)
**Scope:** Production code, tests, configuration

#### Designer
**Tools:** Read, Edit, Write, Glob, Grep, WebFetch, TodoWrite, Skill
**Scope:** Design systems, component specs, UI implementations

#### Forge
**Tools:** All tools (data operations)
**Scope:** Data processing, ETL, large-scale operations

#### Professor
**Tools:** All tools (educational content)
**Scope:** Domain instruction, tutoring, course materials

#### Legal
**Tools:** Read, Write, Edit, Glob, Grep, TodoWrite, MCP (Drive)
**Scope:** Contract drafting, legal documentation

#### Guardian
**Tools:** All tools (QC enforcement)
**Scope:** Pre-commit audits, quality gates, scope validation

#### Janitor
**Tools:** Edit, Write, NotebookEdit, Bash, Skill
**Scope:** Cleanup operations, maintenance, optimization

#### Scrum Leader
**Tools:** Read, Edit, Write, Glob, Grep, TodoWrite, Skill
**Scope:** Sprint planning, backlog management, velocity tracking

---

## Enforcement

**How to enforce:**

1. **Agent definition files** - Update tool lists in `agents/*.md` to remove Edit/Write from C-suite
2. **Task tool validation** - Main agent MUST verify spawned agent has correct tools for task
3. **Metrics tracking** - Monitor tool usage per agent to detect violations

**Red flags (violations):**
- C-suite agent uses >20 tools on a single task
- C-suite agent uses Edit/Write/NotebookEdit
- Implementation work not delegated to builder/designer/forge

---

## Test Case

**Request:** "Add error logging to the authentication module"

**Expected flow:**
```
Main
├─ Conductor (COO) - Coordinate implementation
   ├─ Builder - Implement error logging
   ├─ Builder - Add tests for error cases
   └─ Guardian - Review and approve
```

**Tool usage expectations:**
- Conductor: ~8 tools (mostly Task spawns, Read for context)
- Builder: ~30 tools (Edit/Write for implementation)
- Guardian: ~15 tools (Read for review, Write for report)

**VIOLATION if:**
- Conductor uses >20 tools
- Conductor uses Edit/Write
- No builder spawned

---

**Owner:** the user
**Enforcement:** MANDATORY for all C-suite agents
