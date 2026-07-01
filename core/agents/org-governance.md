# Organizational Governance & Tool Access Matrix

**Version:** 1.0
**Purpose:** Define organizational hierarchy, tool access by role level, and enforcement rules

---

## Organizational Hierarchy

```
                              CEO (the user)
                                    │
                 ┌──────────┬───────┼───────┬──────────┐
                 │          │       │       │          │
                CTO    COO (Conductor)    CFO        CKO
                 │          │                         │
         ┌───────┴──────┐   │                  Alignment Monitor
         │              │   │
   VP Engineering  VP Product
         │              │   │
   ┌─────┴────┐         │   │
   │          │         │   │
Tech Lead  Scrum Lead   │   │
   │          │         │   │
┌──┴───┐  ┌──┴──┐      │   │
Builder Designer Team   │   │
Forge  Professor        │   │
Guardian Janitor        │   │
                        │   │
                  Chief of Staff
                        │
                  ┌─────┴─────┐
              Secretary    HR
```

**CRITICAL SCALING PRINCIPLE:**

Each position (builder, designer, forge, etc.) can have **MULTIPLE WORKERS** deployed simultaneously. The COO is authorized and ENCOURAGED to deploy large teams:

- **5 builders** working in parallel on different modules
- **3 designers** handling different UI areas concurrently
- **2 forges** processing separate datasets simultaneously
- **Manager oversight**: Deploy VP Engineering or Tech Lead to coordinate large teams

**Example Large Deployment:**
```
conductor (COO)
├─ vp-engineering (Team Manager)
│  ├─ builder-1 (Auth module)
│  ├─ builder-2 (API endpoints)
│  ├─ builder-3 (Database layer)
│  ├─ builder-4 (Tests)
│  └─ builder-5 (Documentation)
├─ designer-1 (Login UI)
├─ designer-2 (Dashboard)
└─ guardian (Pre-commit QC for all)
```

This is how you leverage a multi-position org chart properly.

---

## Role Tiers & Tool Access

### Tier 1: C-Suite (Strategy & Coordination)

**Principle:** They delegate, they don't execute.

| Role | Tools | Can Edit/Write? |
|------|-------|----------------|
| **CTO** | Read, Glob, Grep, Bash (status), Task, WebFetch, WebSearch, TodoWrite, Skill | ❌ NO |
| **COO (Conductor)** | Read, Glob, Grep, Bash (status), Task, WebFetch, WebSearch, TodoWrite, Skill, MCP | ❌ NO |
| **CFO** | Read, Glob, Grep, Bash (status), Task, WebFetch, WebSearch, TodoWrite | ❌ NO |

**Key restriction:** No Edit, Write, or NotebookEdit. Period.

---

### Tier 2: VP Level (Department Leadership)

**Principle:** They monitor, coach, and escalate. Light delegation for department-specific tasks.

| Role | Tools | Can Edit/Write? |
|------|-------|----------------|
| **VP Engineering** | Read, Glob, Grep, Bash (test runners), Task, WebFetch, WebSearch, TodoWrite, Skill | ❌ NO |
| **VP Product** | Read, Glob, Grep, Task, WebFetch, WebSearch, TodoWrite, Skill | ❌ NO |
| **VP HR** | Read, Glob, Grep, Edit (agent files only), Write (agent files only), Task, WebFetch, WebSearch, TodoWrite, Skill | ⚠️ LIMITED (agent management) |

**Key restriction:** No production code changes. VP HR exception: can edit agent definition files only.

---

### Tier 3: Management (Leads & Coordinators)

**Principle:** They organize work and report status. Some can write non-code artifacts.

| Role | Tools | Can Edit/Write? |
|------|-------|----------------|
| **Chief of Staff** | Read, Glob, Grep, Bash (status), Task, WebFetch, TodoWrite, Edit (reports only), Write (reports only) | ⚠️ LIMITED (reports/docs) |
| **Scrum Leader** | Read, Glob, Grep, Edit (sprint docs), Write (sprint docs), Task, TodoWrite, Skill | ⚠️ LIMITED (sprint artifacts) |
| **Tech Lead** | Read, Glob, Grep, Bash (build/test), Task, TodoWrite, Skill | ❌ NO |
| **Secretary** | Read, Write (timeline only), Edit (timeline only), Glob, Grep, TodoWrite, MCP | ⚠️ LIMITED (timeline tracking) |

**Key restriction:** No production code. Can write documentation/tracking artifacts only.

---

### Tier 4: Specialists (Implementation & Execution)

**Principle:** They do the hands-on work. Full tool access within their domain.

| Role | Tools | Can Edit/Write? | Domain |
|------|-------|----------------|--------|
| **Builder** | ALL TOOLS | ✅ YES | Production code, tests, config |
| **Designer** | Read, Edit, Write, Glob, Grep, WebFetch, TodoWrite, Skill, MCP (Excalidraw) | ✅ YES | Design systems, UI components, diagrams |
| **Forge** | ALL TOOLS | ✅ YES | Data operations, ETL, large-scale |
| **Professor** | ALL TOOLS | ✅ YES | Educational content, domain instruction |
| **Guardian** | ALL TOOLS | ✅ YES | QC audits, pre-commit validation |
| **Legal** | Read, Write, Edit, Glob, Grep, TodoWrite, MCP (Drive) | ✅ YES | Contracts, legal docs |
| **Janitor** | Edit, Write, NotebookEdit, Bash, Skill | ✅ YES | Cleanup, maintenance |
| **Proposal Writer** | ALL TOOLS | ✅ YES | Sales proposals, presentations |

---

### Tier 5: Support & Background (Monitoring & Research)

**Principle:** They observe, track, and report. No direct changes.

| Role | Tools | Can Edit/Write? | Notes |
|------|-------|----------------|-------|
| **Scout** | Read, Glob, Grep, WebFetch, TodoWrite, WebSearch, MCP | ❌ NO | Pattern detection (background) |
| **Planner** | Read, Glob, Grep, WebFetch, TodoWrite, WebSearch | ❌ NO | Task tracking (background) |
| **Quick** | Read, Bash, Glob, Grep, TodoWrite | ❌ NO | Trivial queries |
| **Scraper** | Read, WebFetch, WebSearch, TodoWrite, MCP (scraping backend) | ❌ NO | Web extraction |
| **Alignment Monitor** | Read, Glob, Grep, Bash (read-only), TodoWrite | ❌ NO | Skill routing audits |

---

## Tool Definitions

### Coordination Tools (Safe for Leadership)
- **Read:** Read files (investigation)
- **Glob:** Find files by pattern
- **Grep:** Search file contents
- **Bash:** Run commands (status/diagnostic only for leadership)
- **Task:** Spawn workers (delegation)
- **TodoWrite:** Track tasks
- **WebFetch/WebSearch:** Research
- **Skill:** Invoke workflows
- **ListMcpResourcesTool/ReadMcpResourceTool:** MCP coordination

### Implementation Tools (Restricted)
- **Edit:** Modify existing files
- **Write:** Create new files
- **NotebookEdit:** Modify Jupyter notebooks
- **Bash (full):** Run any command including destructive operations

---

## Validation Rules

### Rule 1: Tool Access Validation
Before spawning an agent, verify tool access matches role tier:
```
if agent.tier <= 2 and ("Edit" in tools or "Write" in tools):
    VIOLATION - C-suite/VP cannot have Edit/Write
```

### Rule 2: Delegation Enforcement
If C-suite agent uses >15 tools on a task:
```
VIOLATION - C-suite should delegate, not execute
```

### Rule 3: Scope Validation
If agent modifies files outside their domain:
```
if agent == "Secretary" and file != "timeline.md":
    VIOLATION - Secretary can only write timeline
```

---

## Enforcement Checklist

When creating or modifying an agent:

- [ ] **Tier classified correctly** (C-suite vs VP vs Management vs Specialist vs Support)
- [ ] **Tools match tier** (no Edit/Write for Tier 1-2)
- [ ] **Domain restrictions defined** (if limited Edit/Write access)
- [ ] **Delegation pattern documented** (who does this agent spawn?)
- [ ] **Tool count expectations set** (C-suite: <15 tools per task)

---

## New Agent Template

When creating a new agent, use this template:

```markdown
# Agent: [Name]

**Tier:** [1-5] [C-Suite/VP/Management/Specialist/Support]
**Title:** [Organizational title]
**Reports to:** [Manager]
**Manages:** [Direct reports, if any]

## Role & Responsibility

[Clear description of what this agent coordinates/implements/monitors]

## Tool Access

**Allowed:**
- [List of allowed tools]

**Forbidden:**
- [Explicitly list forbidden tools if any]

## Delegation Pattern

When this agent receives a task:
1. [Step 1 - typically Read/investigate]
2. [Step 2 - typically spawn workers OR implement directly]
3. [Step 3 - typically monitor OR return results]

## Domain Restrictions

[If Edit/Write access is limited, specify exactly what files/folders]

## Tool Count Expectations

**Typical task:** [X] tools
**Red flag threshold:** [Y] tools (indicates over-execution)

## Examples

[Show 2-3 example task flows]
```

---

## Agents with Correct Access (Reference)

| Agent | Tier | Tool Access | Status |
|-------|------|-------------|--------|
| builder | Specialist | ALL TOOLS | ✅ Correct |
| designer | Specialist | Edit/Write | ✅ Correct |
| forge | Specialist | ALL TOOLS | ✅ Correct |
| professor | Specialist | ALL TOOLS | ✅ Correct |
| guardian | Specialist | ALL TOOLS | ✅ Correct |
| legal | Specialist | Edit/Write | ✅ Correct |
| janitor | Specialist | Edit/Write | ✅ Correct |
| proposal-writer | Specialist | ALL TOOLS | ✅ Correct |
| scout | Support | Read-only | ✅ Correct |
| planner | Support | Read-only | ✅ Correct |
| quick | Support | Limited | ✅ Correct |
| alignment-monitor | Support | Read-only | ✅ Correct |

---

## A2A Lateral Spawning Rules (v3.0)

### What Changed

Previously, **only conductor could spawn agents**. With A2A v3.0, specialist agents can directly delegate work to peers via DELEGATE messages — without a conductor round-trip.

### Lateral Spawning Governance

| Spawning Agent Tier | May Delegate To | Cannot Delegate To |
|--------------------|----------------|--------------------|
| Tier-4 Specialist | Other Tier-4 specialists, Tier-5 support | Tier-1, 2, 3 (upward) |
| Tier-5 Support | Other Tier-5 support only | Tier-4 specialists or above |
| Tier-3 Management | Tier-4 and Tier-5 | Tier-1 or 2 (upward) |

### Lateral Delegation Rules

1. **Same-tier-or-below only.** No agent can delegate upward.
2. **Max 3 DELEGATE hops.** A → B → C is allowed; A → B → C → D triggers conductor notification.
3. **Conductor observes, not mediates.** Conductor monitors `mesh-messages.jsonl` but does not intercept A2A calls unless circuit breaker fires.
4. **Circuit breaker:** If any agent sends >3 DELEGATE messages in a session, conductor auto-receives a HIGH priority UPDATE and evaluates capacity.
5. **Failure escalation:** If a delegated agent fails (no ACK in timeout), caller escalates to conductor — does not retry blindly.
6. **Audit trail:** All DELEGATE messages written to `session/agent-spawn-log.jsonl` by the `hooks/agent-spawn-validator.py` hook.

### A2A Message Type Permissions by Tier

| Tier | DELEGATE | SUBSCRIBE | NOTIFY | CACHE | UPDATE/QUERY/ACK |
|------|----------|-----------|--------|-------|------------------|
| Tier-1 C-Suite | ❌ | ✅ | ✅ | ❌ | ✅ |
| Tier-2 VP | ❌ | ✅ | ✅ | ❌ | ✅ |
| Tier-3 Management | ⚠️ (downward only) | ✅ | ✅ | ❌ | ✅ |
| Tier-4 Specialist | ✅ (downward/same) | ✅ | ✅ | ✅ | ✅ |
| Tier-5 Support | ⚠️ (Tier-5 only) | ✅ | ✅ | ✅ | ✅ |

### Conductor Role After A2A

Conductor transitions from **sole orchestrator** to **meta-orchestrator + circuit breaker**:

```
OLD role:
  conductor → spawns builder → builder reports → conductor spawns guardian
                                                  → guardian reports → conductor

NEW role (A2A):
  conductor → spawns builder
               └─ builder DELEGATE→ guardian (direct, no conductor round-trip)
                            └─ guardian NOTIFY→ builder (result delivered directly)
  conductor OBSERVES via mesh-messages.jsonl (does not block or intercept)
  conductor INTERVENES only if: deadlocks >5, spawns >3 hops, or circuit breaker fires
```

### External A2A Agent Registry

For external callers (other vendors, partner systems), the org can expose a service directory:

```
GET /.well-known/agents.json   → list all external_safe agents + their card URLs
GET /agent-cards/{name}        → full Agent Card JSON for discovery
POST /tasks                    → submit A2A task
GET /tasks/{id}                → poll task status
GET /tasks/{id}/stream         → SSE stream for long-running tasks
```

**External-safe agents:** proposal-writer, professor, scraper
**Internal only:** builder, forge, legal (write access or confidential data)

---

## Governance Going Forward

### New Agent Checklist
1. Classify tier (1-5)
2. Define reporting structure
3. Assign tools based on tier
4. Document delegation pattern
5. Create Agent Card in `agent-cards/{name}.agent.json` (set `external_safe` carefully)
6. Add to org chart
7. Update CLAUDE.md and `agents/index.md`

### Quarterly Review
- Audit tool usage per agent
- Identify delegation violations (check `session/agent-spawn-log.jsonl`)
- Review A2A message traffic patterns
- Review org structure effectiveness
- Update tier classifications if needed

---

**Owner:** the user
**Status:** MANDATORY - Zero tolerance for violations | A2A v3.0 lateral spawning active
