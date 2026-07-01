---
name: smart-todos
description: Dispatch skill for personal smart-todo system. Handles list/add/done/kill/defer/verdict triggers. Renders top-3 for morning, full list on demand. Reads memory/Projects/Personal/.
context: load-on-trigger
---

# Smart Todos — Dispatch Skill

> Single source of truth for all todo operations. Triggered by quick-trigger keywords in CLAUDE.md.
> Built 2026-04-27 from "Debate by the user" verdict. the user's spec: mixed personal+your org, decay 7/21/30, on-demand only (no Notion mirror).

---

## File Locations (Fixed)

| File | Purpose |
|------|---------|
| `~/.claude\memory\Projects\Personal\smart-todos.md` | Active list |
| `~/.claude\memory\Projects\Personal\archive.md` | Resolved items |
| `~/.claude\memory\Projects\Personal\config.md` | Tunable knobs |
| `~/.claude\memory\Projects\Personal\index.md` | System docs |

---

## Triggers Handled

| User says | Action | Output |
|-----------|--------|--------|
| `todo list`, `smart todos`, `what's on my plate`, `what's on my todo`, `todo` | List action | Render full list, stale flagged |
| `personal todos` | List action (filtered) | Domain=personal only |
| `org todos` | List action (filtered) | Domain=org only |
| `verdict needed`, `stale todos` | List action (filtered) | Status=verdict OR age >30d |
| `add todo {text}` | Add action | Append row, confirm with new ID |
| `add personal todo {text}` | Add action | Append with domain=personal |
| `add org todo {text}` | Add action | Append with domain=org |
| `done {id}` | Resolve action | Move to archive (resolution=done) |
| `kill {id}` | Resolve action | Move to archive (resolution=killed) |
| `defer {id} {date}` | Mutate action | Update due, reset created (freshness reset) |
| `bump {id} {priority}` | Mutate action | Change priority (P0/P1/P2) |
| `today is low energy` / `today is high energy` | Session override | Set morning_energy for this session |

---

## Action 1: LIST

**Steps:**
1. Read `smart-todos.md`
2. Parse the markdown table into rows (skip example rows tagged `example`)
3. For each row, compute `score` per `config.md` formula
4. Compute `age_days = today - created`
5. Auto-flip status to `verdict` if `age_days > 30` AND status in (open, in-progress)
6. Sort by score descending
7. Apply filter (domain, verdict, etc.) if requested
8. Render table with stale-tier annotations

**Score computation:**
```python
priority_w = {"P0": 10, "P1": 5, "P2": 2}[priority]
due_proximity = compute_due_proximity(due, today)  # 15/10/5/3/1
energy_match = 1.5 if energy == morning_energy else (0.7 if energy and morning_energy else 1.0)
freshness = compute_freshness(age_days)  # 1.0/0.8/0.5/0.3
score = priority_w * due_proximity * energy_match * freshness
```

**Render format (full list):**
```
================================================================
SMART TODOS — {N} items ({open}/{in-progress}/{verdict})
================================================================

TOP PRIORITY (score-ranked)
-------------------------------------------------------------
[score] T### | P0 | due Mon Apr 28 | personal | high | open
       Title text here
-------------------------------------------------------------

⚠️  VERDICT NEEDED ({K} items >30d — do/defer/kill required)
-------------------------------------------------------------
[id] T### | created 89 days ago | originally P1
     Title text here
     → Say: done T###  |  kill T###  |  defer T### {date}
-------------------------------------------------------------

AGING (8-21d)
-------------------------------------------------------------
[id] T### | 14d old | P2 | personal
     Title text here
-------------------------------------------------------------

System Status: {fresh}/{aging}/{stale}/{verdict}  |  Last add: {date}  |  Last done: {date}
```

**Render format (morning top-3):**
```
================================================================
SMART TODOS — Top 3 Today
================================================================
1. [score N] T### | P0 due today | high energy
   {Title}
2. [score N] T### | P1 due Friday | med energy
   {Title}
3. [score N] T### | P2 no due | high energy
   {Title}

{IF verdict items > 0}
⚠️  {K} items need verdicts (>30d) — say "verdict needed"
{END IF}

Quick actions:  done T###  |  defer T### {date}  |  add todo {text}
```

---

## Action 2: ADD

**Steps:**
1. Parse `text` for hints:
   - `P0` / `P1` / `P2` → priority
   - `due tomorrow` / `due Friday` / `due 2026-05-04` → due date (resolve via system date)
   - `low energy` / `high energy` / `med energy` → energy
   - `personal` / `org` → domain (or use trigger variant)
2. Read frontmatter `next_id` from `smart-todos.md`
3. Build new row with defaults: P2 / med energy / no due / domain from trigger or `personal`
4. Insert row before example rows OR at table bottom if no examples remain
5. Bump `next_id` in frontmatter
6. Update `last_updated` in frontmatter
7. Confirm to user with new ID

**Confirmation format:**
```
✅ Added T### — "{title}"
   P{N} | {domain} | {energy} energy | due {date or 'whenever'}
   Score: {N} (rank: top {K} of {total})
```

---

## Action 3: DONE / KILL

**Steps:**
1. Read `smart-todos.md`, find row by ID
2. Read `archive.md`, append row with:
   - resolution = `done` or `killed`
   - resolved_date = today
   - notes = optional (if user provided context)
3. Remove row from `smart-todos.md`
4. Update stats snapshot in `archive.md` (totals, kill rate, avg time-to-done)
5. Confirm to user

**Confirmation format:**
```
✅ T### archived — resolution={done|killed}
   Was open {N} days. Archive total: {N} items.
```

---

## Action 4: DEFER

**Steps:**
1. Find row by ID in `smart-todos.md`
2. Update `Due` field to new date
3. Reset `Created` to today (freshness clock resets — this is intentional, deferring buys fresh time)
4. If status was `verdict` or `stale`, reset to `open`
5. Confirm to user

**Confirmation format:**
```
✅ T### deferred to {new_date} — freshness clock reset.
   Score: {old} → {new}
```

If `defer` pushes the date >180 days out: ask user "this is essentially a kill — confirm defer-out?" before moving to archive with resolution=`deferred-out`.

---

## Action 5: BUMP (priority change)

Find row, update Priority field, recompute score, confirm.

---

## Auto-Maintenance (Run On Every LIST Action)

Every time the list is rendered, the dispatch skill performs:

1. **Verdict auto-flip:** Any item with age >30d AND status in (open, in-progress) → status=`verdict`
2. **Anti-zombie sweep:** Any item with status=`verdict` AND time-in-verdict >60d → auto-archive with resolution=`auto-killed`
3. **Dormancy check:** Read `last_updated` from smart-todos.md AND `last_resolved_date` from archive.md. If both >14d ago, set `dormant=true` flag in smart-todos frontmatter — morning will surface dormancy prompt.

---

## Date Parsing (Implementation Notes)

When user says natural-language dates, resolve via PowerShell:

```bash
# "tomorrow" → tomorrow's date
powershell -Command "(Get-Date).AddDays(1).ToString('yyyy-MM-dd')"

# "Friday" → next Friday
powershell -Command "$d=Get-Date; while($d.DayOfWeek -ne 'Friday'){$d=$d.AddDays(1)}; $d.ToString('yyyy-MM-dd')"

# "next week" → 7 days out
powershell -Command "(Get-Date).AddDays(7).ToString('yyyy-MM-dd')"
```

System date today = baseline. NEVER guess — always shell out.

---

## Telegram Parity

All triggers above work identically in Telegram sessions. The dispatch skill is session-agnostic. Telegram users can:

- Add via DM: `add todo pick up dry cleaning P1 due Friday`
- List via DM: `todo list`
- Resolve via DM: `done T042`

Reply via the `mcp__plugin_telegram_telegram__reply` tool with chat_id from the inbound message.

---

## Error Handling

| Issue | Response |
|-------|----------|
| ID not found | "T### not found in active list. Try `todo list` to see current IDs." |
| Smart-todos.md missing | "First-run detected. Initializing from index.md schema..." then re-read |
| Malformed table row | Skip row, log warning, continue with rest |
| Date parse failure | Ask user to clarify with explicit YYYY-MM-DD |
| Frontmatter corruption | Read fallback values: next_id=highest_in_table+1, last_updated=today |

---

## Out Of Scope (Explicitly)

- Notion sync (the user declined — on-demand dispatch only)
- Email integration (todos don't auto-create from inbox — stays manual)
- Calendar push (no auto-create calendar events from due dates — separate decision)
- Recurring todos (use `session/one-off-reminders.json` or `schedule-registry.json` for recurring)
- Subtasks / dependencies (kept flat by design — Skeptic's "no schema fancy")

If you want any of these later, the system is designed to extend without breaking. Add a column, add a trigger, ship.
