---
name: skill-creator
description: |
  Guide for creating new Claude CLI skills.

  Use when:
  - Creating a new skill file
  - Extending the skills architecture
  - Standardizing skill format

  Includes: Templates, validation rules, best practices.
---

# Skill Creator Guide

Create properly structured skills for the Claude CLI system.

## Skill File Structure

```yaml
---
name: skill-name           # kebab-case, matches filename
description: |
  One-line summary.

  Use when:
  - Trigger condition 1
  - Trigger condition 2

  Includes: What's covered.
---

# Skill Title

[Content organized by complexity: simple → advanced]
```

## Template: Simple Skill

```markdown
---
name: example-skill
description: |
  Brief description of what this skill provides.

  Use when:
  - Working with [specific technology]
  - Need to [accomplish specific task]

  Includes: [Key topics covered].
---

# Skill Title

Brief intro paragraph.

## Quick Reference

Most common patterns/commands first.

## Core Concepts

Essential information.

## Common Patterns

```code
// Example with comments
```

## Best Practices

1. **First practice** - explanation
2. **Second practice** - explanation
```

## Context Budget Classification (REQUIRED)

Every new skill MUST include a context budget classification in frontmatter. This is mandatory — no exceptions.

### Classification Table

| Type | Flag | When to Use | Example |
|------|------|-------------|---------|
| Primary workflow driver | (none) | User triggers this skill by name regularly | morning.md, whitehat-protocol.md |
| Background reference | `user-invocable: false` | Reference docs, notes, pattern libraries | study-resources.md, hacker101-guide.md |
| Manual-only | `disable-model-invocation: true` | Only fires via explicit CLAUDE.md routing | sweep-engine.md, kb-auto-ingestion.md |
| Subagent-spawning | `context: fork` | Skill spawns one or more agents | sweep-engine.md, morning.md |

**Rule:** If you can't articulate how a user would trigger this skill by keyword, it's probably `user-invocable: false`.

### Context Budget Math

Current system state (2026-03-12):
- 371 skill files × avg 200 chars = ~74,000 chars total
- Context budget cap: ~16,000 chars
- Pre-classification: 78% invisible
- Target post-classification: <16K chars (all primary drivers visible)

Every skill you create without `user-invocable: false` adds to the budget pressure. Classify first.

## Updated SKILL.md Frontmatter Template (v3.0)

```yaml
---
name: skill-name                  # kebab-case, matches filename
description: |
  One-line summary.

  Use when:
  - Trigger condition 1
  - Trigger condition 2

  Includes: What's covered.

# Context Budget Classification (REQUIRED — choose one):
# user-invocable: false           # Background reference (exclude from budget)
# disable-model-invocation: true  # Manual-only (exclude from budget)
# (no flag) = Primary workflow driver (included in budget)

# Subagent isolation (add if this skill spawns agents):
# context: fork

# Version tracking (required for primary drivers):
version: "1.0"

# Eval tests (required for primary drivers):
eval-tests:
  - input: "example trigger phrase"
    expected: "what the skill should produce"
    pass-criteria: "contains required output section"
---
```

## Eval Loop (Primary Drivers Only)

Primary workflow drivers require eval tests in frontmatter. Run the eval loop to validate:

### Step 1: Define Test Cases

In frontmatter `eval-tests:`, write 2-3 representative trigger phrases and expected outputs.

### Step 2: Run Eval

Use `/skill-creator eval <skill-name>` to run all test cases.

Output format:
```
[EVAL] skill-name v1.0
Test 1: morning briefing trigger → PASS (3/3 required sections present)
Test 2: wrong trigger phrase → PASS (correctly routes to @quick)
Test 3: edge case → FAIL (missing "DEPLOYMENT MANIFEST")
Score: 2/3 (66%) — threshold: 80%
```

### Step 3: Improve

Fix failing tests. Update `eval-tests:` to cover fixed cases.

### Step 4: Benchmark

Compare version metrics:

| Version | Pass Rate | Avg Tokens | Latency |
|---------|-----------|------------|---------|
| 1.0 | 66% | 4,200 | 8s |
| 1.1 | 100% | 3,800 | 6s |

Goal: >80% pass rate + minimal token cost.

## Scoped Hooks (Advanced)

Skills can define hooks that ONLY fire when that skill runs — not globally.

```yaml
hooks:
  pre-invoke: "scripts/pre-skill.sh"    # Runs before skill loads
  post-invoke: "scripts/post-skill.sh"  # Runs after skill completes
```

Use cases:
- catalog validation: post-invoke saves results to vault
- Sweep engine: pre-invoke checks authorization headers
- Morning routine: post-invoke updates last-run timestamp

**Scoped vs global hooks:** Scoped hooks are defined in the skill frontmatter and only fire for that skill. Global hooks are in gate-enforcer.py and fire for every response.

## Template: Agent Skill

```markdown
---
name: agent-name
description: |
  Agent role summary.

  Triggers:
  - When to deploy this agent

  Capabilities: What this agent does.
---

# Agent Name

## Identity

**Role:** One-line role description
**Deployed by:** Who spawns this agent
**Works with:** Collaborating agents

## Responsibilities

### Primary
- Main responsibility 1
- Main responsibility 2

### Does NOT
- Anti-pattern 1
- Anti-pattern 2

## Workflow

```
[Step-by-step process]
```

## Handoff Protocol

| From | To | When |
|------|----|------|
| This agent | Target | Condition |

## Output Schema

```json
{
  "field": "description"
}
```
```

## Template: Integration Skill

```markdown
---
name: service-api
description: |
  Integration with [Service Name].

  Use when:
  - Connecting to [service]
  - Syncing data with [service]

  Includes: Auth, endpoints, field mappings.
---

# Service Name Integration

## Authentication

```typescript
// Auth pattern
```

## Common Endpoints

### GET /endpoint
```typescript
// Request/response example
```

## Field Mappings

| Our Field | API Field | Notes |
|-----------|-----------|-------|
| id | external_id | Primary key |

## Error Handling

```typescript
// Error handling pattern
```
```

## Validation Rules

### Required Elements

| Element | Purpose |
|---------|---------|
| YAML frontmatter | Skill metadata and triggers |
| `name` field | Skill identification |
| `description` field | When to load skill |
| Main heading | Skill title |
| Quick reference | Most common use cases |

### Naming Conventions

```yaml
Files: kebab-case.md
Names: kebab-case (match filename)
Headings: Title Case
Code: language-appropriate conventions
```

### Size Guidelines

| Skill Type | Target Size | Max Size |
|------------|-------------|----------|
| Simple | 100-200 lines | 300 lines |
| Standard | 200-400 lines | 500 lines |
| Complex | 400-600 lines | 800 lines |
| Agent | 300-500 lines | 700 lines |

### Content Guidelines

```yaml
DO:
  - Start with most common use cases
  - Include working code examples
  - Show both simple and advanced patterns
  - Document error handling
  - Keep examples copy-paste ready

DON'T:
  - Include overly basic concepts
  - Duplicate content from other skills
  - Add theoretical explanations without examples
  - Include deprecated patterns
  - Exceed size guidelines significantly
```

## Skill Categories

| Category | Path | Purpose |
|----------|------|---------|
| agents | skills/agents/ | Agent personas and protocols |
| stacks | skills/stacks/ | Technology stack patterns |
| integrations | skills/integrations/ | Third-party API integrations |
| domains | skills/domains/ | Domain-specific development |
| workflows | skills/workflows/ | Process and workflow patterns |
| tooling | skills/tooling/ | Tool-specific operations |
| design | skills/design/ | UI/UX and design patterns |
| meta | skills/meta/ | Skills about skills |

## Creating a New Skill

### Step 1: Identify Category
```
Is it about a specific agent? → agents/
Is it a tech stack? → stacks/
Is it a third-party API? → integrations/
Is it domain knowledge? → domains/
Is it a process/workflow? → workflows/
Is it a specific tool? → tooling/
Is it design-related? → design/
Is it about the skill system? → meta/
```

### Step 2: Create File
```bash
# Create in appropriate category
touch skills/[category]/skill-name.md
```

### Step 3: Add Frontmatter
```yaml
---
name: skill-name
description: |
  Summary.

  Use when:
  - Trigger 1
  - Trigger 2

  Includes: Topics.
---
```

### Step 4: Add Content
```markdown
# Skill Title

## Quick Reference
[Most common patterns]

## Core Concepts
[Essential knowledge]

## Examples
[Working code]

## Best Practices
[Guidelines]
```

### Step 5: Validate
- [ ] Frontmatter is valid YAML
- [ ] Name matches filename
- [ ] Description includes triggers
- [ ] Content is organized simple → complex
- [ ] Examples are copy-paste ready
- [ ] Size is within guidelines

### Step 6: Hot List Check

Ask: **will this trigger fire >5×/week OR is it safety-critical?**

| Answer | Action |
|--------|--------|
| YES | Add to CLAUDE.md hot list table + bump version + commit |
| NO | Skip CLAUDE.md entirely — skill is auto-discoverable via skill-matcher |

**Hot list criteria (both required to add):**
- Frequency: fires more than 5 times per week based on expected usage, OR
- Safety-critical: skipping would cause data loss, misroute Telegram, or bypass enforcement

Most new skills do NOT meet this bar. Default is auto-discoverable — do not add to CLAUDE.md.

### Step 7: Reindex

Always run after creating or renaming a skill file:

```bash
python ~/.claude\scripts\build-skill-index.py
```

Confirm output shows the new skill in the count. Skill-matcher will find it on the next request with no CLAUDE.md edit required.

## Skill Loading in Router (v5.0 Model)

**Do NOT edit CLAUDE.md unless Step 6 hot list check says YES.**

New skills are automatically discoverable via `session/skill-index.json` — no manual trigger table entry required. The reindex script (Step 7) picks up any new `.md` file in `skills/` or `agents/`.

The only skills that go into CLAUDE.md are those meeting the hot list bar:
- >5×/week frequency, OR
- Safety-critical (enforcement, Telegram, Phase 0 gates)

**Hot list entry format (when criteria met):**
```markdown
| "trigger phrase", "alt phrase" | `skills/category/skill-name.md` |
```

## Example: Complete Skill

```markdown
---
name: csv-processing
description: |
  CSV file manipulation with Python.

  Use when:
  - Reading/writing CSV files
  - Transforming tabular data
  - Data cleaning tasks

  Includes: pandas, csv module, common transformations.
---

# CSV Processing

Python patterns for CSV manipulation.

## Quick Reference

```python
import pandas as pd

# Read
df = pd.read_csv('file.csv')

# Write
df.to_csv('output.csv', index=False)

# Filter
filtered = df[df['column'] > value]
```

## Common Operations

### Read with Options
```python
df = pd.read_csv('file.csv',
    encoding='utf-8',
    dtype={'id': str},
    parse_dates=['date_col']
)
```

### Transform
```python
# Rename columns
df.rename(columns={'old': 'new'}, inplace=True)

# Add computed column
df['total'] = df['price'] * df['quantity']

# Group and aggregate
summary = df.groupby('category').agg({'amount': 'sum'})
```

## Best Practices

1. **Specify dtypes** - Prevent type inference issues
2. **Handle encoding** - Use utf-8 or specify explicitly
3. **Chunk large files** - Use `chunksize` parameter
4. **Validate output** - Check row counts after operations
```

---

### A2A Awareness (for agent-facing skills)

If this skill is used by agents that participate in A2A delegation:

1. Note which agents load this skill in the frontmatter: `agents: [builder, forge]`
2. If the skill changes an agent's capabilities, update the corresponding Agent Card in `agents/agent-cards/{agent}.agent.json`
3. If the skill introduces a new capability that other agents should be able to DELEGATE to, add it to the Agent Card's capabilities list
4. Skills do NOT get their own Agent Cards — only agents do. Skills extend agent capabilities.

---

## Pre-Creation Scan (MANDATORY)

**Before creating ANY new skill file or folder, ALWAYS scan first.**

### Step 0: Scan Target Directory

```yaml
BEFORE any file creation:
  1. List all existing files in target directory
  2. List all subdirectories
  3. Read existing files to understand content scope
  4. Check for naming conflicts
  5. Report findings BEFORE proceeding
```

### Scan Report Format

```markdown
## Pre-Creation Scan Results

**Target:** skills/integrations/servicename/
**Action:** Creating new endpoint documentation

### Existing Files Found
| File | Lines | Purpose |
|------|-------|---------|
| api.md | 1176 | Overview, auth, pagination |
| duplicate-detection.md | 200 | Fuzzy matching |

### Naming Conflicts
- [ ] None found
- [x] CONFLICT: `api.md` exists alongside `api/` folder

### Content Overlap Analysis
| New Content | Existing Content | Verdict |
|-------------|------------------|---------|
| Endpoint schemas | api.md has overview | COMPLEMENTARY |
| Auth patterns | api.md has auth | DUPLICATE - skip |

### Recommendation
- Proceed with: [specific files]
- Skip/merge: [overlapping content]
- Rename: [conflicts]
```

### Why This Matters

```
REAL EXAMPLE: your CRM Documentation (January 2026)

We created 22 endpoint files without reading api.md first.
Result: Missed that api.md had 700+ lines of endpoint listings.

If we had scanned first:
- Would have identified the api.md/api/ naming conflict
- Could have planned proper structure upfront
- Avoided redundancy discussion later
```

---

## Naming Conflict Rules

### File/Folder Same-Name Ban

**NEVER** create a file with the same base name as a sibling folder:

```yaml
FORBIDDEN:
  ❌ api.md + api/           # Same base name
  ❌ config.md + config/     # Same base name
  ❌ data.md + data/         # Same base name

ALLOWED:
  ✅ api/index.md            # File INSIDE folder
  ✅ api-overview.md + api/  # Different base names
  ✅ _api.md + api/          # Different (underscore prefix)
```

### When Topic Needs Overview + Sub-Files

If a topic needs both overview content AND multiple sub-files:

```yaml
Pattern A (Preferred): index.md inside folder
  topic/
  ├── index.md        # Overview content
  ├── subtopic-a.md
  └── subtopic-b.md

Pattern B: Different name
  topic-overview.md   # Overview content
  topic/
  ├── subtopic-a.md
  └── subtopic-b.md
```

### Conflict Resolution

If conflict already exists:

```yaml
1. Read both file and folder contents
2. Determine if file content should:
   a. Move INTO folder as index.md
   b. Stay outside with renamed file
   c. Be merged with existing folder content
3. Execute migration
4. Update any references (CLAUDE.md routing, etc.)
```

---

## Agent Suggestion Protocol

**After completing substantial work, evaluate for new agent opportunities.**

### Post-Work Evaluation Questions

```yaml
Ask after every substantial task:
  1. Did this task reveal a repeatable pattern?
  2. Could an agent have automated part of this?
  3. Is there a monitoring gap an agent could fill?
  4. Would future similar work benefit from dedicated agent?
```

### When to Suggest New Agent

```yaml
Suggest new agent when:
  - Same pattern appears 3+ times
  - Manual monitoring was required that could be automated
  - Cross-cutting concern spans multiple existing agents
  - Specialized domain knowledge was needed repeatedly
```

### Agent Suggestion Format

```yaml
## New Agent Recommendation

Agent Name: structure-sentinel
Purpose: Pre-scan monitoring before file creation

Triggers:
  - Before creating new skill files
  - Before creating new folders
  - During substantial skill work

Responsibilities:
  - Scan target directories
  - Identify naming conflicts
  - Check for content redundancy
  - Report findings before creation

Why Needed:
  - [Specific task that revealed the need]
  - [Pattern that would benefit from automation]

Related Existing Agents:
  - @guardian (similar QA focus, different scope)
```

### Agent Suggestion Tracking

All suggestions go to planning phase output. User decides whether to:
- BUILD immediately
- BACKLOG for later
- SKIP (not needed)

---

## Folder Depth Guidelines

### Maximum Nesting

```yaml
Recommended max depth: 4 levels
  skills/                    # Level 1
  └── integrations/          # Level 2
      └── ticketing/       # Level 3
          └── api/           # Level 4
              └── endpoints/ # Level 5 (MAX - avoid if possible)
```

### When Depth Exceeds 4

```yaml
Consider:
  - Flattening structure
  - Using prefixes instead of folders
  - Creating separate top-level category
```

---

## Files Per Folder Guidelines

```yaml
Optimal: 5-10 files per folder
Warning: >15 files - consider subfolder
Critical: >25 files - must reorganize

When reorganizing:
  1. Group by function/purpose
  2. Create meaningful subfolders
  3. Update all references
  4. Add index.md for navigation
```

---

*Skill Creator Guide v3.0 - Context Budget + Eval Loop + Scoped Hooks (2026-03-12)*
