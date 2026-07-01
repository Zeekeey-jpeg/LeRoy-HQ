---
user-invocable: false
---

# Quick Trigger Maintenance v2.0 (Hybrid Routing Model)

**Purpose:** Governance for the CLAUDE.md hot list and auto-discoverable skill routing.

**When to Use:** When creating new skills, evaluating whether a trigger belongs in the hot list, or auditing routing performance.

---

## How Routing Works (v5.0)

There are two routing layers:

| Layer | What It Is | When It Fires |
|-------|-----------|--------------|
| **Hot List** (CLAUDE.md) | 10-row inline table, instant match | Exact keyword match, <100ms |
| **Skill-Matcher** (dynamic) | Haiku agent + skill-index.json | All other requests, ~2s |

**Most new skills do NOT go into CLAUDE.md.** They are auto-discoverable via the skill-matcher as long as they have a good `name:` and `description:` in frontmatter and the index is fresh.

→ Index rebuilt by: `python ~/.claude\scripts\build-skill-index.py`
→ Protocol: `skills/meta/skill-search-protocol.md`

---

## Hot List: What Belongs Here

**Criteria — BOTH required to add to hot list:**

1. **Frequency:** Fires >5 times per week based on expected usage, AND/OR
2. **Safety-critical:** Skipping would cause data loss, misroute Telegram, bypass enforcement, or block Phase 0 gates

**Current hot list (10 entries):**

| Trigger | Skill |
|---------|-------|
| "Morning" | `skills/routines/morning.md` |
| "backup", "push backup", "doomsday backup", "github backup" | `skills/routines/backup-reminder.md` |
| "telegram", "start telegram", "launch telegram", "mobile session" | `skills/routines/telegram-launch.md` |
| "/reset" (via Telegram) | `skills/routines/telegram-reset.md` |
| "run daily ops", "daily ops" | `skills/routines/daily-ops.md` |
| "run leadgen", "leadgen run", "launch leadgen" | `skills/routines/leadgen.md` |
| "overnight hunt", "200 outreach", "nightly outreach" | `skills/routines/overnight-hunt-protocol.md` |
| "whitehat", "bug bounty", "HackerOne", "whitehat now", "whitehat bounty" | `skills/domains/cyber/whitehat-protocol.md` |
| "/goal", "plan goal" + all /goal subcommands | `skills/meta/goal-engine.md` |
| "done", "i'm done", "start over", "clear session", "reset chat" | `skills/routines/session-reset.md` |

---

## Decision Tree: CLAUDE.md vs Auto-Discoverable

```
New skill created
    │
    ├─ Will this fire >5×/week? ─── YES ──► Hot list candidate
    │                                           │
    │                                           └─ Also safety-critical? YES ──► ADD to CLAUDE.md hot list
    │                                                                    NO ──► Hot list candidate only if >5×/week confirmed
    │
    └─ Safety-critical? ──── YES ──► ADD to CLAUDE.md hot list
                        │
                        └─ NO ──► Auto-discoverable. Run reindex. Done.
```

**Default path for most skills: auto-discoverable.** Only ~10 triggers ever belong in CLAUDE.md.

---

## Adding to the Hot List (When Criteria Met)

### Step 1: Confirm criteria

Check both boxes:
- [ ] Expected usage > 5×/week (or safety-critical)
- [ ] No existing hot list trigger handles this pattern

### Step 2: Edit CLAUDE.md hot list

File: `~/.claude\CLAUDE.md`
Section: `## Hot List (Instant Routing — No Search Required)`

Add row in the hot list table:
```markdown
| "trigger phrase", "alt phrase" | `skills/category/skill-name.md` |
```

For safety-critical triggers, add a parenthetical note:
```markdown
| "trigger" | `skills/path.md` *(⛔ enforcement note)* |
```

### Step 3: Version bump

Update the version line at bottom of CLAUDE.md:
```
*Distribution Hub v5.X | ...*
```

Bump the minor version (v5.0 → v5.1).

### Step 4: Reindex + commit

```bash
python ~/.claude\scripts\build-skill-index.py
git add CLAUDE.md
git commit -m "hot list: add {skill-name} trigger (criteria: {reason})"
```

All CLAUDE.md hot list changes MUST be committed — this is the auditable change log.

---

## Auto-Discoverable Skills (No CLAUDE.md Edit)

For skills that do NOT meet hot list criteria, the only required steps are:

1. Create skill file with good frontmatter `name:` + `description:` fields
2. Run reindex: `python ~/.claude\scripts\build-skill-index.py`
3. Skill is immediately findable via skill-matcher

No CLAUDE.md edit. No trigger table entry. No manual registration.

**Good frontmatter = good discovery:**
```yaml
---
name: my-skill-name
description: |
  What this skill does in one sentence.
  
  Use when:
  - Trigger condition A
  - Trigger condition B
  
  Includes: key topics, keywords, domain.
---
```

The skill-matcher scores against the `description:` field — keyword-rich descriptions improve match confidence.

---

## Modifying Hot List Entries

### Valid reasons to modify
- Skill file moved or renamed
- Trigger phrase conflicts with another entry
- User requests different behavior
- Safety-critical status removed (demote to auto-discoverable)

### Modification process
1. Edit the row in CLAUDE.md hot list table
2. If demoting (removing from hot list): confirm the skill's frontmatter description will surface it via skill-matcher
3. Run reindex if skill path changed
4. Version bump + commit

---

## Removing from the Hot List

A trigger is a removal candidate when:
- 0 hits in the past 30 days (growth-agent weekly audit surfaces these)
- Pattern changed and a different trigger phrase handles it now
- Skill was consolidated into another skill

**Removal = auto-discoverable, not deleted.** The skill file stays; only the CLAUDE.md row is removed. Skill-matcher can still find it.

---

## Naming Conventions

### Trigger phrases
- Natural language (how user actually says it)
- Short: 1-3 words preferred
- Multiple variants in one cell: `"phrase 1", "phrase 2"`
- Case-insensitive (system handles)

**Good:** "morning", "validate catalog", "run cleanup"
**Bad:** "please give me the morning briefing", "report" (too ambiguous)

### Conflict avoidance
- Substring conflicts: use specific phrases, not broad ones
- Overlapping meanings: use distinct phrases ("system check" vs "project status")
- Test against existing hot list before adding

---

## Testing

### Hot list trigger test
```
User: "{exact trigger phrase}"
Expected: [GATE] shows correct skill loaded, <100ms
```

### Auto-discoverable skill test
```
User: "{natural language description of what you want}"
Expected: skill-matcher returns confidence ≥ 0.50, correct file returned
```

### Fallback test
```
User: "xyzzy"
Expected: Folder menu presented (confidence < 0.50)
```

---

## Governance Calendar

| Cadence | What | Who |
|---------|------|-----|
| Every new skill | Hot list check (Step 6 in skill-creator.md) | COO |
| Weekly | Growth agent audits hit counts, surfaces removal/promotion candidates | growth-agent.md |
| Any hot list change | Version bump + git commit | COO |
| Quarterly | Alignment-monitor reviews coverage gaps | alignment-monitor |

---

**Last Updated:** 2026-05-24
**Version:** 2.0 (Hybrid Routing Model)
**Status:** Active
