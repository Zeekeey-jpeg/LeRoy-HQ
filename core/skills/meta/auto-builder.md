# Auto Builder

> **Trigger keywords:** auto build, auto skill, context high, pattern detected, reusable pattern, skill fork, 10 to 11, folder growth, split skills

---

## Purpose

Build skills and agents from detected patterns. Works with the growth system:

| Component | Role |
|-----------|------|
| **scout** (agent) | Silent background observation, surfaces opportunities at breakpoints |
| **auto-builder** (this skill) | Manual execution when user approves building |

**Flow:** scout detects → user approves → auto-builder executes

See `agents/scout.md` for background monitoring rules.
See `meta/sub-agent-spawning.md` for background agent infrastructure.

---

## Context Monitoring Rules

### 80% Context Threshold

**When context usage approaches 80%:**

1. **Detect** - Monitor conversation length and complexity
2. **Extract** - Identify reusable patterns from current session
3. **Generate** - Create skill file from extracted patterns
4. **Spawn** - Launch sub-agent to complete skill creation
5. **Handoff** - Continue conversation in new context

### Context Handoff Protocol

```yaml
Trigger: Context at ~80% capacity

Actions:
  1. Summarize current work state
  2. Identify any reusable patterns discovered
  3. If patterns found:
     - Generate skill file draft
     - Save to appropriate skills/ folder
     - Update CLAUDE.md routing table
  4. Spawn fresh sub-agent with:
     - Work summary
     - Pending tasks
     - New skill reference (if created)
```

---

## Pattern Detection

### What Qualifies as a Reusable Pattern

| Pattern Type | Indicator | Auto-Build? |
|--------------|-----------|-------------|
| API call sequence | Same 3+ calls repeated | Yes |
| Data transformation | Same logic on different data | Yes |
| Workflow steps | Same process executed twice | Yes |
| Error handling | Same recovery pattern | Yes |
| Single-use code | One-time script | No |
| Project-specific | Won't transfer to other projects | No |

### Detection Triggers

```yaml
Auto-Build Triggers:
  - "I've done this before" in conversation
  - Same MCP tool sequence 2+ times
  - User says "save this", "remember this", "make a skill"
  - Complex multi-step process completed successfully
  - Code pattern that could help future sessions

Skip Auto-Build:
  - Debugging/troubleshooting (too specific)
  - One-time data fixes
  - Project-specific configurations
  - Incomplete or failed attempts
```

---

## Auto-Build Process

### Step 1: Pattern Recognition

```yaml
Analyze current session for:
  - Repeated tool call sequences
  - Multi-step workflows that succeeded
  - Code snippets written more than once
  - User corrections that indicate best practice
  - Integration patterns (API → transform → output)
```

### Step 2: Classification

```yaml
Determine skill type:
  agents/       → New agent role identified
  integrations/ → New API or service pattern
  workflows/    → New process flow
  tooling/      → New tool usage pattern
  stacks/       → New tech stack pattern
  domains/      → New domain knowledge
  routines/     → New quick trigger
```

### Step 3: Generation

Use `skill-creator.md` templates to generate:

```markdown
---
name: [auto-detected-name]
description: |
  [Extracted from conversation context]

  Use when:
  - [Trigger derived from when pattern was used]

  Includes: [Key elements detected]
---

# [Title]

## Quick Reference

[Most common usage from session]

## Pattern

[Extracted code/steps]

## Notes

Auto-generated from session on [date].
Review and refine as needed.
```

### Step 4: Validation

Before saving, verify:

```yaml
Checklist:
  - [ ] Pattern is genuinely reusable (not project-specific)
  - [ ] Doesn't duplicate existing skill
  - [ ] Has enough content to be useful
  - [ ] Follows skill-creator.md guidelines
  - [ ] Placed in correct category folder
```

### Step 5: Registration

After saving skill file:

1. Update category's `index.md` if exists
2. Add routing entry to CLAUDE.md skill table
3. Notify user: "Created new skill: [path]"

### Step 6: Recurring Workflow Prompt (For Workflows)

**If skill was saved to `workflows/` folder, prompt for scheduling:**

```
[AUTO-BUILD] Created: workflows/{name}.md

Is this workflow recurring?
[1] No - one-time only
[2] Yes - set schedule

→ If user selects [2]:

How often should this run?
[1] Daily
[2] Weekly - Every Monday
[3] Weekly - Every Friday
[4] Monthly - 1st of month
[5] Monthly - 15th of month
[6] Monthly - Specific weekday (e.g., 3rd Monday)
[7] Custom - describe your schedule

→ Based on selection, add to schedule-registry.json:

{
  "id": "{auto-generated-slug}",
  "name": "{Workflow Name}",
  "skill_path": "workflows/{name}.md",
  "recurrence": "{selected_pattern}",
  "next_run": "{calculated_date}",
  "last_run": null,
  "enabled": true
}

→ Confirm:

✅ Scheduled: {Workflow Name}
   Pattern: {recurrence description}
   Next run: {date} ({X} days)
   Will appear in morning briefing.
```

### Step 7: Post-Completion Scheduling

**After ANY workflow execution, offer scheduling:**

```
User completes a multi-step workflow (not yet a skill)

[WORKFLOW COMPLETE] {Summary of what was done}

Would you like to:
[1] Save as skill (one-time)
[2] Save as skill + schedule recurring
[3] Don't save

→ If [2], follow Step 6 prompts
```

---

## Agent Auto-Creation

> **Full guide:** See `meta/agent-creator.md` for complete agent creation process.

### When to Create New Agent

```yaml
New Agent Justified When:
  - Distinct persona/role emerges (not covered by existing)
  - Would be spawned by Architect-Orchestrator
  - Has clear responsibilities separate from Techy/UIUX/Sentinel
  - Would handle specific domain repeatedly
  - scout flagged the gap

Do NOT Create Agent For:
  - One-time tasks
  - Variations of existing agent work
  - Simple skill execution
```

### Agent Creation Process

1. **Pre-scan** - Check `agents/index.md` for overlap
2. **Identify role gap** - What's not covered by current agents?
3. **Define boundaries** - What does it do / NOT do?
4. **Establish handoffs** - Who spawns it? Who does it hand off to?
5. **Create file** - Use Claude Code format from `meta/agent-creator.md`
6. **Get approval** - Present draft before saving
7. **Update agents/index.md** - Add to roster and routing table

---

## Sub-Agent Spawning for Skill Creation

> **Full infrastructure:** See `meta/sub-agent-spawning.md` for complete patterns.

### When to Spawn

```yaml
Spawn Sub-Agent When:
  - Context exceeds 80%
  - Complex skill needs dedicated attention
  - Current task would benefit from fresh context
  - Multiple skills need creation simultaneously
```

### Spawn Command

```yaml
Task tool with:
  subagent_type: "general-purpose"
  run_in_background: true  # For non-blocking creation
  prompt: |
    Create new skill file based on this pattern:
    [Pattern summary]

    Save to: skills/[category]/[name].md
    Follow: skills/meta/skill-creator.md template

    After creation:
    1. Update category index.md
    2. Report back with file path
```

---

## Skill Fork Monitoring (10→11 Rule)

### The Threshold

**When any skill folder reaches 11 files (from 10), trigger a fork notification.**

This is the signal that a category has grown enough to warrant subfolder organization.

### Detection

```yaml
On skill creation, check target folder:
  count = number of .md files in folder
  if count >= 10:
    trigger_fork_notification(folder)
```

### Fork Notification Format

```
[SKILL-FORK] Category growth detected

Folder: skills/integrations/
Current count: 11 files
Threshold: 10

Recommended action: Review for subfolder organization

Suggested splits:
  integrations/
  ├── crm/           (crm, ticketing contacts)
  ├── psa/           (ticketing tickets, agreements)
  ├── cloud/         (google, supabase)
  └── automation/    (n8n, webhooks)

Options:
[1] Create subfolders now
[2] Ignore (folder is fine as-is)
[3] Remind me at 15 files
```

### Fork Process

When user approves fork:

1. **Analyze skills** - Group by logical domain
2. **Create subfolders** - mkdir for each group
3. **Move files** - Relocate skills to new subfolders
4. **Create index.md** - Add routing index to each subfolder
5. **Update parent index** - Point to subfolders
6. **Update CLAUDE.md** - Adjust routing paths

### Subfolder Structure After Fork

```
Before (flat):
  integrations/
  ├── ticketing-api.md
  ├── ticketing-duplicate-detection.md
  ├── crm-api.md
  ├── catalog-tool.md
  ├── google-workspace.md
  ├── n8n-workflows.md
  ├── n8n-workflow-builder.md
  ├── bim-tool.md
  ├── bim-architecture-plan.md
  ├── bim-type-intelligence.md
  └── bim-phase2-type-api.md    ← 11th file triggers notification

After (organized):
  integrations/
  ├── index.md                   ← Routes to subfolders
  ├── crm/
  │   ├── index.md
  │   ├── crm-api.md
  │   └── ticketing-*.md
  ├── bim-tool/
  │   ├── index.md
  │   └── bim-tool-*.md
  └── automation/
      ├── index.md
      └── n8n-*.md
```

### Thresholds Reference

| Folder Count | Action |
|--------------|--------|
| 1-7 | No action needed |
| 8-9 | Pre-warning: "Approaching limit" |
| 10 | At threshold, monitor closely |
| 11+ | **Fork notification triggered** |
| 15+ | Strong recommendation to split |

### Skip Fork For

```yaml
Do NOT suggest fork when:
  - Folder is already a subfolder (L2/L3)
  - Files are tightly coupled (must stay together)
  - User previously dismissed at higher count
  - Category is inherently broad (e.g., "meta")
```

---

## Examples

### Example: Auto-Detected API Pattern

During session, user repeatedly:
1. Calls your CRM search
2. Filters results
3. Exports to Excel

**Auto-generates:** `workflows/cw-search-export.md`

### Example: Context Threshold Reached

At 80% context:
1. Summarize: "Working on your CRM report generation"
2. Detect pattern: Report generation workflow
3. Generate: `routines/crm-custom-report.md`
4. Spawn sub-agent with summary
5. Continue in fresh context

### Example: New Agent Detected

User consistently needs your BIM tool schedule automation that Techy doesn't handle well.

**Auto-generates:** `agents/bim-scheduler.md` with:
- Clear boundaries from professor
- Specific schedule/quantity takeoff focus
- Handoff protocols

### Example: Skill Fork Triggered

Creating `integrations/bim-phase2-type-api.md` (11th file in integrations/):

```
[SKILL-FORK] Category growth detected

Folder: skills/integrations/
Current count: 11 files
Threshold: 10

Files detected:
  - ticketing-api.md
  - ticketing-duplicate-detection.md
  - catalog-tool.md
  - google-workspace.md
  - crm-api.md
  - n8n-workflows.md
  - n8n-workflow-builder.md
  - bim-tool.md
  - bim-architecture-plan.md
  - bim-type-intelligence.md
  - bim-phase2-type-api.md  ← NEW

Suggested reorganization:
  integrations/
  ├── ticketing/    (2 files)
  ├── bim-tool/           (4 files)
  ├── n8n/            (2 files)
  └── [remaining]     (3 files: catalog-tool, google, crm)

[1] Create subfolders now
[2] Keep flat structure
[3] Remind at 15 files
```

---

## Integration with CLAUDE.md

After any auto-build, update CLAUDE.md:

```markdown
| [new-keywords] | [new-skill-path] |
```

And notify user:

```
[AUTO-BUILD] Created: skills/[category]/[name].md
Keywords: [routing keywords]
Review recommended: [yes/no based on complexity]
```

---

*Auto-builder v2.0 | Integrated with scout system*
