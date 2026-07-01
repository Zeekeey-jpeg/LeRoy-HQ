# Fixed Path Registry v1.0

**Purpose:** Centralized reference for all critical system paths

**When to Use:** When accessing state, memory, or session files

**Critical Rule:** These paths are FIXED and NEVER change. Do not compute, guess, or modify.

---

## Session State Files

**Base:** `.claude/session/`

| File | Purpose | Updated By | Read By |
|------|---------|------------|---------|
| `state.json` | Session state + enforcement flags | Hook, Claude | Hook, Claude, Skills |
| `enforcement.todo` | Mandatory action queue | Hook | Claude (Position #2) |
| `prompt-history.jsonl` | Full conversation log | Hook | Recovery |
| `growth-output.md` | Current session patterns | @scout | Claude, User |
| `growth-history.md` | Cross-session patterns | @scout | Claude |
| `context-anchor.md` | Session decisions + files | Claude | Recovery |

**Example Access:**
```python
# CORRECT:
state_path = ".claude/session/state.json"

# INCORRECT (DO NOT compute paths):
state_path = f"{config_dir}/session/state.json"
```

---

## Memory System Files

**Base:** `.claude/session/`

| File | Purpose | Size | Performance |
|------|---------|------|-------------|
| `memory-index.json` | Full note index | 947KB | Too large for Read tool |
| `memory-cache.json` | Session cache | <100KB | <5ms reads |
| `memory-cache-lru.json` | Frequently accessed notes | <50KB | <1ms reads |

**Shards (Domain-Specific):**

| File | Project | Notes | Size |
|------|---------|-------|------|
| `shards/meta-shard.json` | meta | 91 | 109KB |
| `shards/your organization-shard.json` | your organization | 467 | 673KB |

**Usage Pattern:**
```python
# Load shard instead of full index:
shard_path = ".claude/session/shards/meta-shard.json"
shard_path = ".claude/session/shards/your organization-shard.json"

# DO NOT load full index (exceeds Read limit):
# ❌ index_path = ".claude/session/memory-index.json"
```

---

## Memory Vault (Obsidian)

**Root:** `~/.claude\memory\`

### Folder Structure

| Folder | Purpose | Note Types |
|--------|---------|------------|
| `Claude/Decisions/` | Architectural decisions | Decision notes |
| `Claude/Patterns/` | System patterns | Pattern documentation |
| `Claude/Preferences/` | User preferences | Preference records |
| `Claude/Skills-Learned/` | Learned capabilities | Skill documentation |
| `Claude/Error-Solutions/` | Problem resolutions | Error fix notes |
| `Claude/Projects/` | Project-specific notes | Project documentation |

**Full Paths (Examples):**
```
~/.claude\memory\Claude\Decisions\Protocol-Enforcement-v5.2.md
~/.claude\memory\Claude\Patterns\Memory-Smart-Filtering.md
~/.claude\memory\Claude\Skills-Learned\TodoWrite-Examples.md
```

---

## Skills System

**Root:** `~/.claude\skills\`

### Skill Folders

| Folder | Purpose | Load When |
|--------|---------|-----------|
| `integrations/` | APIs, MCPs, external systems | API calls needed |
| `workflows/` | Git, planning, delivery | Process-driven tasks |
| `domains/` | your BIM tool, Android | Domain-specific work |
| `stacks/` | Supabase, GAS, MCP builder | Tech stack work |
| `tooling/` | Excel, Word, PDF, reports | Document generation |
| `web-development/` | Frontend, UI/UX, styling | Web development |
| `meta/` | Permissions, pagination, skills | Meta-system tasks |
| `user/` | Credentials, emails, roster | User-specific data |
| `scripts/` | Reusable scripts | Automation |

**Index Files (ALWAYS load first):**
```
skills/integrations/index.md
skills/workflows/index.md
skills/domains/index.md
skills/stacks/index.md
skills/tooling/index.md
skills/web-development/index.md
skills/meta/index.md
skills/user/index.md
skills/scripts/index.md
```

---

## Agents

**Root:** `~/.claude\agents\`

| File | Agent | Use For |
|------|-------|---------|
| `index.md` | Router | Agent selection |
| `conductor.md` | @conductor | Coordination, QC |
| `builder.md` | @builder | Implementation |
| `designer.md` | @designer | UI/UX design |
| `forge.md` | @forge | Large data ops |
| `guardian.md` | @guardian | Pre-commit QC |
| `scout.md` | @scout | Pattern detection |
| `validator.md` | @validator | data validation |

---

## Routines

**Root:** `~/.claude\routines\`

| File | Trigger | Purpose |
|------|---------|---------|
| `index.md` | Router | Routine selection |
| `morning.md` | "morning" | Daily briefing |
| `monday-cleanup.md` | "run cleanup" | Weekly cleanup |
| `monday-leadership-report.md` | "monday report" | Leadership agenda |
| `crm-report.md` | "hs report" | Sales performance |
| `token-burn-report.md` | "weekly report" | Token efficiency |
| `bim-connect.md` | "bim-tool mcp" | your BIM tool connection |

---

## Scripts

**Root:** `~/.claude\scripts\`

| File | Purpose | Usage |
|------|---------|-------|
| `build-memory-index.py` | Build memory index | `python scripts\build-memory-index.py` |

**Full Path:**
```
~/.claude\scripts\build-memory-index.py
```

---

## Hooks

**Root:** `~/.claude\hooks\`

| File | Purpose | Fires When |
|------|---------|------------|
| `gate-enforcer.py` | Prompt capture + enforcement | Every user prompt |

**Full Path:**
```
~/.claude\hooks\gate-enforcer.py
```

---

## Reports Output

**Root:** `~\Projects\your organization\Requested Reports\`

**Pattern:** `{YYYY-MM-DD}\{report-name}.xlsx`

**Examples:**
```
~\Projects\your organization\Requested Reports\2026-01-21\monday-leadership-agenda.xlsx
~\Projects\your organization\Requested Reports\2026-01-21\token-burn-week-over-week.xlsx
```

---

## Project Roots

| Project | Root Path |
|---------|-----------|
| ExampleClient (Parent) | `~\Desktop\Projects\EXAMPLECLIENT\` |
| your product | `~\Desktop\Projects\EXAMPLECLIENT\your product\` |
| your product | `~\Desktop\Projects\EXAMPLECLIENT\your product\` |
| your product R2025 | `~\Desktop\Projects\EXAMPLECLIENT\your product\src\your product.R2025\` |
| your product Memory | `~/.claude\memory\Projects\your product\` |
| your organization | `~\Projects\your organization\` |
| Meta (Claude system) | `~/.claude\` |
| Memory Vault | `~/.claude\memory\` |

---

## Path Validation Checklist

**Before using ANY path:**

1. ✅ Is it in this registry?
2. ✅ Is it an absolute path (not relative)?
3. ✅ Does it use backslashes (Windows)?
4. ✅ Is it exactly as written (no modifications)?

**Common Mistakes:**

| ❌ WRONG | ✅ CORRECT |
|---------|-----------|
| `session/state.json` | `.claude/session/state.json` |
| `~` | `~` |
| `{base_path}/state.json` | `.claude/session/state.json` |
| `memory_index.json` | `.claude/session/memory-index.json` |

---

## When Paths Change

**Trigger:** User moves directories or reorganizes structure

**Action:**
1. User updates CLAUDE.md environment section
2. Update this registry
3. Run validation checks
4. Update all skills referencing changed paths
5. Rebuild memory index if vault moved

**Critical:** Fixed paths are only "fixed" until user changes them. Always use paths from this registry, not hardcoded assumptions.

---

## Reference

**Environment Section:** CLAUDE.md lines 123-150
**Memory System:** CLAUDE.md lines 549-794
**Skills System:** CLAUDE.md lines 195-232

---

**Last Updated:** 2026-01-21
**Version:** 1.0
**Status:** Reference Guide
