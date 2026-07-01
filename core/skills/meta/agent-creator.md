---
name: agent-creator
description: |
  Complete guide for creating new agents following Claude Code standards.

  Use when:
  - Creating a new agent
  - Growth-monitor suggests agent opportunity
  - Defining agent responsibilities and triggers
  - Writing agent system prompts

  Includes: Frontmatter format, description examples, system prompt design, validation, approval workflow.
---

# Agent Creator Guide

Create properly structured agents for autonomous task handling.

---

## Quick Reference

### Minimal Agent Template

```markdown
---
name: agent-identifier
description: |
  Use this agent when [conditions]. Examples:

  <example>
  Context: [Situation]
  user: "[Request]"
  assistant: "[Response using this agent]"
  <commentary>
  [Why this agent triggers]
  </commentary>
  </example>

model: inherit
color: blue
tools: ["Read", "Write", "Grep"]
---

You are [role description].

**Your Core Responsibilities:**
1. [Responsibility 1]
2. [Responsibility 2]

**Process:**
1. [Step 1]
2. [Step 2]

**Output Format:**
[What to return]
```

---

## Hybrid Agent Creation Workflow

**Philosophy:** Fast scaffolding + human approval. The skill generates drafts automatically, presents them for review, and writes files only on explicit approval. This preserves velocity (no manual typing) while preventing junk agents (human QA gate).

### Workflow Overview

```
User describes need
    ↓
Skill performs PRE-SCAN (check existing agents, prevent overlap)
    ↓
Skill generates DRAFTS (name, description with examples, tools, index entry)
    ↓
Skill presents for APPROVAL (all drafts shown for review/modification)
    ↓
User approves or requests changes
    ↓
On approval: Skill writes files (agents/{name}.md + update agents/index.md)
    ↓
Skill validates metadata and confirms creation
```

### Phase 1: Pre-Scan (Automated)

When user describes agent need, skill immediately:

1. **Check existing agents:**
   - Read `agents/index.md` routing table
   - List current agent roster (core + background)
   - Scan role descriptions for overlap
   - Report: "Found 10 existing agents. Role overlap analysis complete."

2. **Prevent duplication:**
   - If similar role exists → Recommend enhancement instead of new agent
   - If exact match → Stop and ask user to clarify difference
   - If clear gap → Proceed to draft generation

3. **Report findings:**
   ```
   PRE-SCAN RESULTS:
   ├─ Existing agents: 10 (architect, techy, uiux, data, sentinel, bim, growth, analyst, validator, janitor)
   ├─ Similar roles: [list any near-matches]
   ├─ Recommendation: PROCEED / MERGE WITH EXISTING / ENHANCE EXISTING
   └─ Rationale: [why recommendation made]
   ```

### Phase 2: Draft Generation (Automated)

Skill generates all required metadata:

1. **Frontmatter:**
   - `name`: Validate format (3-50 chars, lowercase-hyphen, start/end alphanumeric)
   - `description`: Generate 2-4 `<example>` blocks based on use cases
   - `tools`: Suggest minimum set required for role (principle of least privilege)
   - `model`: Recommend based on task complexity (default: inherit)
   - `color`: Assign from available colors (no duplicates within agent roster)

2. **System Prompt:**
   - Role description with specialization
   - Core Responsibilities (numbered, specific)
   - You Do NOT (clear boundaries)
   - Process (step-by-step)
   - Quality Standards
   - Output Format (structured)
   - Handoff Protocol (routing to other agents)

3. **Index Entry:**
   - Keywords for triggering the agent
   - Auto-spawn rule (Via architect / Yes / Via schedule)
   - Add to `agents/index.md` routing table

### Phase 3: Approval Checkpoint (Human)

Skill presents ALL drafts for review:

```
DRAFT: New Agent for Review

┌─ FRONTMATTER DRAFT ──────────────────────┐
│ name: {suggested-name}                   │
│ description: |                           │
│   {first 100 chars...}                   │
│ tools: [list of tools]                   │
│ model: inherit                           │
│ color: {color}                           │
└──────────────────────────────────────────┘

┌─ SYSTEM PROMPT DRAFT ────────────────────┐
│ You are the {name} agent, specializing   │
│ in {domain}...                           │
│                                          │
│ **Your Core Responsibilities:**          │
│ 1. [responsibility 1]                    │
│ 2. [responsibility 2]                    │
│ ...                                      │
└──────────────────────────────────────────┘

┌─ INDEX ENTRY DRAFT ──────────────────────┐
│ | {keywords} | {name} | {auto-spawn} |   │
└──────────────────────────────────────────┘

⚠️  REVIEW REQUIRED:
   [ ] Frontmatter looks correct
   [ ] Description captures use cases
   [ ] Tools list is appropriate
   [ ] System prompt is specific
   [ ] Index entry has right keywords

Options:
  [1] Approve and write files
  [2] Request changes (describe)
  [3] Cancel
```

**User can:**
- Approve all drafts as-is
- Request specific changes to any section
- Cancel if pre-scan revealed overlap user didn't notice

### Phase 4: Final Write (On Approval)

Only after explicit approval, skill:

1. **Create files:**
   - Write `agents/{name}.md` with approved frontmatter + system prompt
   - Validate YAML syntax
   - Confirm file creation

2. **Update index:**
   - Read current `agents/index.md`
   - Find appropriate location in routing table (sorted by keyword)
   - Insert new entry with approved keywords + auto-spawn rule
   - Update agent count in footer
   - Confirm index update

3. **Validate metadata:**
   - Parse created agent file
   - Verify frontmatter all fields present
   - Confirm index entry matches agent name
   - Run validation checklist (see below)

4. **Confirm to user:**
   ```
   ✅ AGENT CREATED SUCCESSFULLY

   File: agents/{name}.md
   Index: agents/index.md (routing table updated)

   Next steps:
   1. Read agents/index.md routing table to verify entry placement
   2. Git add agents/conductor to stage changes
   3. Commit with: "feat: Create {name} agent for {purpose}"
   4. Push to remote
   ```

---

### Phase 5: A2A Integration (MANDATORY for all new agents)

Every new agent MUST be A2A-enabled:

1. **Create Agent Card:** Write `agents/agent-cards/{agent-name}.agent.json` with:
   - capabilities list (what this agent can do)
   - inputSchema / outputSchema (what it accepts and returns)
   - `external_safe: true|false` (can external systems call this agent?)
   - `a2a_callable: true`
   - SLA (timeout, priority, long_running flag)

2. **Add A2A Protocol section** to the agent .md file:
   - "Requesting Peer Help" — which agents it can DELEGATE to and when
   - "Receiving Delegated Tasks" — how to handle [A2A:DELEGATED_TASK] prompts
   - "Shared Cache" — check session/a2a-cache.json before starting work
   - Use the [A2A:DELEGATE] / [A2A:RESULT] block format

3. **Update index references:**
   - Add Agent Card to `agents/agent-cards/README.md` table
   - Update `agents/index.md` file tree with card reference

4. **Verify alignment:** Run alignment-monitor to confirm card ↔ agent mapping is correct

**Template Agent Card:**
```json
{
  "schema_version": "a2a/1.0",
  "name": "{agent-name}",
  "display_name": "your org {Display Name}",
  "version": "1.0",
  "capabilities": ["..."],
  "inputSchema": { },
  "outputSchema": { },
  "authentication": { "type": "internal", "required": false },
  "sla": { "timeout_ms": 30000, "priority": "MEDIUM" },
  "a2a_callable": true,
  "external_safe": false
}
```

**No agent ships without an A2A card and protocol section. This is non-negotiable.**

---

## Agent File Structure

### Location

All agents live in: `agents/` (root-level)

```
agents/
├── index.md                    # Routing table (MANDATORY)
├── conductor.md   # Master coordinator
├── builder.md
├── designer.md
├── forge.md
├── guardian.md
├── professor.md
├── scout.md
├── analyst.md
├── validator.md
├── janitor.md
└── {new-agent-name}.md         # New agents follow this pattern
```

**Rule:** File location is deterministic. No nesting. No aliases. `agents/{name}.md` only.

### Complete Format

```markdown
---
name: agent-identifier
description: |
  Brief summary of agent purpose.

  Use this agent when [triggering conditions]. Examples:

  <example>
  Context: [Detailed situation description]
  user: "[Exact user request]"
  assistant: "[How assistant responds and uses this agent]"
  <commentary>
  [Explanation of why this agent should trigger]
  </commentary>
  </example>

  <example>
  Context: [Different situation]
  user: "[Different request]"
  assistant: "[Different response]"
  <commentary>
  [Why this triggers]
  </commentary>
  </example>

model: inherit
color: blue
tools: ["Read", "Write", "Grep", "Bash"]
---

You are [agent role] specializing in [domain].

**Your Core Responsibilities:**
1. [Primary responsibility]
2. [Secondary responsibility]
3. [Additional responsibilities]

**You Do NOT:**
- [Anti-pattern 1]
- [Anti-pattern 2]

**Process:**
1. [Step one]
2. [Step two]
3. [Step three]

**Quality Standards:**
- [Standard 1]
- [Standard 2]

**Output Format:**
[Structured output specification]

**Handoff Protocol:**
| From | To | When |
|------|----|------|
| This agent | Target agent | Condition |
```

---

## Frontmatter Fields

### name (required)

Agent identifier for namespacing and invocation.

```yaml
Format: lowercase, numbers, hyphens only
Length: 3-50 characters
Pattern: Must start and end with alphanumeric
```

**Good:**
- `code-reviewer`
- `data-validator`
- `api-docs-writer`
- `scout`

**Bad:**
- `helper` (too generic)
- `-agent-` (starts/ends with hyphen)
- `my_agent` (underscores not allowed)
- `ag` (too short)

### description (required) - CRITICAL

This field determines when Claude triggers the agent. **Most important field.**

**Must include:**
1. Triggering conditions ("Use this agent when...")
2. Multiple `<example>` blocks (2-4 recommended)
3. Context, user request, and assistant response in each
4. `<commentary>` explaining why agent triggers

**Format:**
```yaml
description: |
  Brief one-line summary.

  Use this agent when [specific conditions]. Examples:

  <example>
  Context: [Scenario description]
  user: "[What user says]"
  assistant: "[How Claude responds]"
  <commentary>
  [Why this agent is appropriate]
  </commentary>
  </example>

  <example>
  Context: [Different scenario]
  user: "[Different request]"
  assistant: "[Different response]"
  <commentary>
  [Different reasoning]
  </commentary>
  </example>
```

**Best Practices:**
- Include 2-4 concrete examples
- Show proactive AND reactive triggering
- Cover different phrasings of same intent
- Explain reasoning in commentary
- Be specific about when NOT to use

### model (required)

Which model the agent uses.

| Value | Use When |
|-------|----------|
| `inherit` | Default - uses parent model (recommended) |
| `haiku` | Fast, cheap - monitoring, simple tasks |
| `sonnet` | Balanced - most implementation work |
| `opus` | Most capable - complex reasoning, architecture |

**Recommendation:** Use `inherit` unless specific need.

### color (required)

Visual identifier in UI.

| Color | Suggested Use |
|-------|---------------|
| `blue` | Analysis, review, general |
| `cyan` | Information, documentation |
| `green` | Success-oriented, monitoring, validation |
| `yellow` | Caution, warnings, QA |
| `magenta` | Creative, generation |
| `red` | Critical, security, errors |

**Rule:** Each agent in system should have distinct color.

### tools (optional)

Restrict agent to specific tools. Principle of least privilege.

```yaml
tools: ["Read", "Write", "Grep", "Bash"]
```

**If omitted:** Agent has access to all tools.

**Common Tool Sets:**

| Agent Type | Tools |
|------------|-------|
| Read-only analysis | `["Read", "Grep", "Glob"]` |
| Code generation | `["Read", "Write", "Grep", "Edit"]` |
| Testing | `["Read", "Bash", "Grep"]` |
| Monitoring | `["Read", "Grep", "Glob"]` |
| Full implementation | Omit (all tools) |

---

## System Prompt Design

The markdown body after frontmatter becomes the agent's system prompt.

### Structure Template

```markdown
You are [role] specializing in [domain].

**Your Core Responsibilities:**
1. [Primary - most important]
2. [Secondary]
3. [Tertiary]

**You Do NOT:**
- [What this agent explicitly avoids]
- [What gets delegated to other agents]

**Process:**
1. [First step]
2. [Second step]
3. [Third step]
...

**Quality Standards:**
- [Standard 1]
- [Standard 2]

**Output Format:**
[Structured specification of what to return]

**Handoff Protocol:**
| From | To | When |
|------|----|------|
| This | Other | Condition |

**Edge Cases:**
- [Situation 1]: [How to handle]
- [Situation 2]: [How to handle]
```

### Best Practices

**DO:**
- Write in second person ("You are...", "You will...")
- Be specific about responsibilities
- Define clear boundaries (what NOT to do)
- Provide step-by-step process
- Specify output format
- Include handoff protocols
- Address edge cases
- Keep under 10,000 characters

**DON'T:**
- Write in first person ("I am...")
- Be vague or generic
- Omit process steps
- Leave output undefined
- Skip boundary definitions
- Ignore error cases

---

## Creation Workflow (Aligned with 4-Phase Model)

### User Input: Identify Need

Before starting, clarify the agent need:

```yaml
New agent justified when:
  ✓ Distinct role emerges (not covered by existing)
  ✓ Would be spawned by conductor
  ✓ Has clear responsibilities separate from others
  ✓ Would handle specific domain repeatedly
  ✓ Growth-monitor flagged the gap

Do NOT create when:
  ✗ One-time task
  ✗ Variation of existing agent work
  ✗ Simple skill execution suffices
  ✗ Can be handled by enhancing existing agent

When user describes need → Proceed to Phase 1
```

---

### Hybrid Workflow Decision Flow

```
User describes        ┌─────────────────────────────────┐
agent need ──────────→│ PHASE 1: Pre-Scan (Automated)   │
                      │ Read agents/index.md            │
                      │ Check for overlap               │
                      └────────────┬────────────────────┘
                                   │
                   ┌───────────────┴───────────────┐
                   ↓                               ↓
        ┌──────────────────────┐      ┌──────────────────────┐
        │ MERGE Recommendation │      │ ENHANCE Recommendation
        │ (enhance existing)   │      │ (enhance existing)   │
        └──────────────────────┘      └──────────────────────┘
                   │                               │
                   └───────────────┬───────────────┘
                                   ↓
                ┌─────────────────────────────────┐
                │   PROCEED to Phase 2             │
                │   New agent needed               │
                └────────────┬────────────────────┘
                             │
                      ┌──────▼──────────────────────────┐
                      │ PHASE 2: Draft Generation       │
                      │ (Automated)                     │
                      │ • Frontmatter with examples     │
                      │ • System prompt sections        │
                      │ • Index entry with keywords     │
                      └────────────┬───────────────────┘
                                   │
                      ┌────────────▼────────────────────┐
                      │ PHASE 3: Approval Checkpoint    │
                      │ (CRITICAL GATE - Human Review)  │
                      │ Present all drafts              │
                      │ Validation checklist            │
                      └────────────┬────────────────────┘
                                   │
         ┌─────────────────────────┼─────────────────────────┐
         │                         │                         │
         ↓                         ↓                         ↓
    [1] APPROVE          [2] REQUEST CHANGES         [3] CANCEL
    Write files          Ask for revisions           Abort creation
         │                         │                         │
         │                         └────────────┬────────────┘
         │                                      │
         ↓                                      ↓
┌──────────────────────┐         Return to Phase 2 with feedback
│ PHASE 4: Final Write │         (revision loop - no files yet)
│ (Automated)          │
│ • Create files       │
│ • Update index       │
│ • Validate           │
│ • Confirm to user    │
└──────────────────────┘

KEY PRINCIPLE: Files created ONLY after explicit [1] Approve in Phase 3
                This preserves both velocity (fast scaffolding) and
                correctness (human approval before writing)
```

---

### Phase 1: Pre-Scan (Automated)

**When:** User describes agent need
**Who:** Skill (automated)
**Output:** Pre-scan findings or recommendation to PROCEED/MERGE/ENHANCE

**Execute:**

1. **Read agents/index.md**
   - Extract routing table (keywords, agent names, auto-spawn rules)
   - Get current agent roster (10 agents)
   - List role descriptions to check for overlap

2. **Check for overlap**
   - Does similar role already exist? (architect, techy, uiux, data, sentinel, bim, growth, analyst, validator, janitor)
   - Could existing agent handle this work?
   - Is this a boundary clarification issue or truly new role?

3. **Report findings:**
   ```
   ┌─ PRE-SCAN RESULTS ──────────────────────────────┐
   │ Existing agents: 10 (list scan results)         │
   │ Similar roles: [any near-matches]               │
   │ Recommendation: PROCEED / MERGE / ENHANCE       │
   │ Rationale: [reasoning for recommendation]       │
   └─────────────────────────────────────────────────┘
   ```

If recommendation is MERGE or ENHANCE → Stop and explain why. Otherwise proceed to Phase 2.

---

### Phase 2: Draft Generation (Automated)

**When:** Pre-scan recommends PROCEED
**Who:** Skill (automated)
**Output:** Complete drafts for all sections

**Generate all sections:**

1. **Define Boundaries (internally)**
   ```yaml
   Answer these before generating:
     1. What does this agent DO? (responsibilities)
     2. What does this agent NOT do? (boundaries)
     3. Who spawns this agent? (deployment context)
     4. Who does this agent hand off to? (other agents)
     5. What tools does it need? (minimum set)
     6. What model is appropriate? (inherit/haiku/sonnet/opus)
   ```

2. **Generate frontmatter**
   - `name`: Suggest format (3-50 chars, lowercase-hyphen)
   - `description`: Generate with 2-4 `<example>` blocks + `<commentary>`
   - `model`: Recommend based on complexity
   - `color`: Assign from available colors (no duplicates)
   - `tools`: Suggest minimal set required

3. **Generate system prompt**
   - Role description with specialization
   - Core Responsibilities (numbered, specific)
   - You Do NOT (clear boundaries)
   - Process (step-by-step)
   - Quality Standards
   - Output Format (structured)
   - Handoff Protocol

4. **Generate index entry**
   - Keywords for agent triggering
   - Auto-spawn rule (Via architect / Yes / Via schedule)
   - Entry ready to insert into routing table

---

### Phase 3: Approval Checkpoint (Human)

**When:** All drafts generated
**Who:** User (human review)
**Output:** Approval or requests for changes

**Present complete draft for review:**

```
┌─ DRAFT: {Agent Name} ───────────────────────────────┐
│                                                      │
│ ┌─ FRONTMATTER ──────────────────────────────────┐  │
│ │ name: {suggested-name}                         │  │
│ │ description: [first 100 chars...              │  │
│ │ tools: [list]                                  │  │
│ │ model: inherit                                 │  │
│ │ color: {color}                                 │  │
│ └────────────────────────────────────────────────┘  │
│                                                      │
│ ┌─ SYSTEM PROMPT PREVIEW ────────────────────────┐  │
│ │ You are the {name} agent, specializing in...  │  │
│ │                                                 │  │
│ │ **Your Core Responsibilities:**                │  │
│ │ 1. [responsibility 1]                          │  │
│ │ 2. [responsibility 2]                          │  │
│ │ ...                                            │  │
│ └────────────────────────────────────────────────┘  │
│                                                      │
│ ┌─ INDEX ENTRY ──────────────────────────────────┐  │
│ │ | {keywords} | {name} | {auto-spawn} |        │  │
│ └────────────────────────────────────────────────┘  │
│                                                      │
│ VALIDATION CHECKLIST:                              │
│ ☐ Frontmatter looks correct                        │
│ ☐ Description captures use cases                   │
│ ☐ Examples are clear and realistic                 │
│ ☐ Tools list is appropriate (minimal)              │
│ ☐ System prompt is specific and actionable         │
│ ☐ Index entry has right keywords                   │
│ ☐ No role overlap with existing agents             │
│                                                      │
│ OPTIONS:                                            │
│ [1] Approve and write files                         │
│ [2] Request changes (describe)                      │
│ [3] Cancel                                          │
└──────────────────────────────────────────────────────┘
```

**User can:**
- Approve all drafts as-is → Proceed to Phase 4
- Request specific changes → Return to Draft Generation (Phase 2)
- Cancel if pre-scan revealed overlap → Stop

---

### Phase 4: Final Write (On Approval)

**When:** User selects "Approve and write files"
**Who:** Skill (automated)
**Output:** Created files + confirmation

**Execute:**

1. **Create agent file**
   - Write to `agents/{name}.md`
   - Include approved frontmatter + system prompt
   - Validate YAML syntax
   - Confirm: ✅ File created

2. **Update agents/index.md**
   - Read current index
   - Find correct position in routing table (alphabetical by keywords)
   - Insert new entry with approved keywords + auto-spawn rule
   - Update footer agent count
   - Confirm: ✅ Index updated

3. **Validate metadata**
   - Parse created agent file
   - Verify all frontmatter fields present
   - Check name format
   - Confirm index entry matches agent name
   - Run full validation checklist (see below)

4. **Confirm to user**
   ```
   ✅ AGENT CREATED SUCCESSFULLY

   File: agents/{name}.md
   Index: agents/index.md (routing table updated)
   Agent count: Updated to N agents

   Next steps:
   1. Read agents/index.md to verify entry placement
   2. Run `git status` to confirm files staged
   3. Commit with: "feat: Create {name} agent for {purpose}"
   4. Push to remote
   ```

---

## Integration with Growth System

### When Growth-Monitor Suggests Agent

```yaml
Growth-monitor output:
  🤖 Agent Opportunities:
  • {gap description} → agents/{suggested-name}.md

User selects: [1] Review & build

Workflow executes 4-phase hybrid model:
  Phase 1: Pre-Scan (Automated)
    - Check existing agents for overlap
    - Report findings: PROCEED / MERGE / ENHANCE

  Phase 2: Draft Generation (Automated)
    - Generate frontmatter with examples
    - Generate system prompt with responsibilities
    - Generate index entry with keywords

  Phase 3: Approval Checkpoint (Human)
    - Present all drafts for review
    - User can approve as-is or request changes
    - Validate completeness against checklist

  Phase 4: Final Write (On Approval)
    - Create agents/{name}.md
    - Update agents/index.md routing table
    - Validate metadata
    - Confirm creation to user
```

### Approval Workflow Integration

```
CRITICAL: NEVER create agent without explicit user approval.

Complete Flow:
  1. Growth-monitor identifies gap → outputs [GROWTH] block
  2. User selects: [1] Review & build
  3. agent-creator skill loads (this file)
  4. Phase 1: Pre-Scan executes (check for overlap)
  5. Phase 2: Draft Generation executes (scaffold metadata)
  6. Phase 3: Approval Checkpoint executes (present drafts with checklist)
  7. User reviews and selects:
       [1] Approve and write files
       [2] Request changes (describe)
       [3] Cancel
  8. Phase 4: Final Write executes ONLY on explicit approval
     - Creates agent file
     - Updates index
     - Confirms to user

Safeguard: File creation (Phase 4) requires explicit [1] selection in Phase 3.
```

---

## Existing Agent Reference

Current agents in the system (10 total):

### Core Team (6 agents)

| Agent | Role | Color | Model |
|-------|------|-------|-------|
| conductor | Master coordinator, planning, QC, delegation | blue | inherit |
| builder | Code implementation, features, fixes | cyan | inherit |
| designer | UI/UX design, components, styling | magenta | inherit |
| forge | Large data operations (10K+), ETL, batch | yellow | inherit |
| guardian | Commit QA, scope validation, auditing | red | inherit |
| professor | BIM expertise, your BIM tool operations, training | green | inherit |

### Background Agents (4 agents)

| Agent | Role | Color | Model |
|-------|------|-------|-------|
| scout | Silent pattern detection, growth opportunities | pink | haiku |
| analyst | Report specification validation, field verification | orange | haiku |
| validator | data validation and completeness checks | orange | haiku |
| janitor | System cleanup orchestrator, parallel scanning | orange | haiku |

### Role Boundaries

```yaml
conductor:
  DOES: Plan, delegate, QC, coordinate, enforce scope, Git operations
  DOES NOT: Write code, design UI, handle data directly, skip planning

builder:
  DOES: Write code, implement features, create integrations, write tests
  DOES NOT: Make architectural decisions alone, design UI without @uiux, commit without @sentinel

designer:
  DOES: Design UI, create components, style with Tailwind/shadcn, ensure accessibility
  DOES NOT: Write backend code, make architecture decisions, handle data operations

forge:
  DOES: Large data operations (10K+), ETL processes, batch transformations, data analysis
  DOES NOT: Small data tasks (inline), UI work, code architecture

guardian:
  DOES: Validate scope adherence, audit changes, check security, verify quality
  DOES NOT: Write code, make changes, skip any commit

professor:
  DOES: your BIM tool operations via your BIM connector, BIM expertise, family/type management, schedules
  DOES NOT: Non-BIM development, general coding tasks

scout:
  DOES: Monitor conversations silently, track patterns, surface suggestions at checkpoints
  DOES NOT: Interrupt active work, create files directly, surface every observation

analyst:
  DOES: Validate report fields exist in data sources, check your CRM/your CRM properties
  DOES NOT: Create/modify reports, change source data, block report creation (advisory only)

validator:
  DOES: Validate your CRM BOMs, cross-reference your data tool/ticketing catalogs, detect missing accessories
  DOES NOT: Modify opportunities, add items automatically, make pricing decisions

janitor:
  DOES: Scan 11 parallel cleanup categories, identify stale files, orchestrate cleanup
  DOES NOT: Execute cleanup without approval, modify user files, delete without confirmation
```

---

## Example: Complete Agent

```markdown
---
name: api-validator
description: |
  Validates API integrations and endpoint responses.

  Use this agent when testing APIs, validating responses, or debugging integration issues. Examples:

  <example>
  Context: User is building a your CRM integration
  user: "Test if this API call is working correctly"
  assistant: "[Spawns api-validator to test endpoint, validate response schema, check error handling]"
  <commentary>
  API validation requires systematic testing beyond simple calls. This agent handles response validation, schema checking, and error case testing.
  </commentary>
  </example>

  <example>
  Context: Integration returning unexpected data
  user: "The your CRM API is returning weird data"
  assistant: "[Spawns api-validator to analyze response, compare to expected schema, identify discrepancies]"
  <commentary>
  Debugging API issues requires methodical validation. This agent systematically checks response structure and content.
  </commentary>
  </example>

model: inherit
color: yellow
tools: ["Read", "Grep", "Bash"]
---

You are the api-validator agent, specializing in API integration testing and validation.

**Your Core Responsibilities:**
1. Test API endpoints for correct responses
2. Validate response schemas against expectations
3. Check error handling and edge cases
4. Document API behavior discrepancies

**You Do NOT:**
- Implement new API integrations (delegate to @techy)
- Make architectural decisions (delegate to @architect)
- Modify production code without approval

**Process:**
1. Identify the API endpoint to test
2. Execute test call with appropriate parameters
3. Validate response structure
4. Check response data against expected schema
5. Test error cases (invalid params, auth failures)
6. Document findings

**Quality Standards:**
- All responses validated against schema
- Error cases explicitly tested
- Clear documentation of any issues
- Reproducible test scenarios

**Output Format:**
```yaml
API Validation Report:
  endpoint: [URL]
  method: [GET/POST/etc]
  status: PASS/FAIL

  Response Validation:
    schema_match: yes/no
    data_integrity: yes/no

  Issues Found:
    - [Issue 1]
    - [Issue 2]

  Recommendations:
    - [Action 1]
```

**Handoff Protocol:**
| From | To | When |
|------|----|------|
| @api-validator | @techy | Fixes needed |
| @api-validator | @architect | Architecture issues found |
| @architect | @api-validator | Validation requested |
```

---

## Validation Rules Summary

| Element | Rule |
|---------|------|
| name | 3-50 chars, lowercase-hyphen, alphanumeric start/end |
| description | 10-5,000 chars, must have examples |
| model | inherit/haiku/sonnet/opus |
| color | blue/cyan/green/yellow/magenta/red |
| tools | Array of tool names, or omit for all |
| System prompt | 20-10,000 chars, second person |

---

*Agent Creator Guide v1.0 | Claude Code Standards*
