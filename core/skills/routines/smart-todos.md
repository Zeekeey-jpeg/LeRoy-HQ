---
name: smart-todos
description: Dispatch skill for personal smart-todo system. Handles list/add/done/kill/defer/bump/backstory/verdict triggers. Renders top-3 for morning, full board after every write, full list on demand. Reads memory/Projects/Personal/.
context: load-on-trigger
---

# Smart Todos — Dispatch Skill

> Single source of truth for all todo operations. Triggered by quick-trigger keywords in CLAUDE.md.
> Built 2026-04-27 from "Debate by you" verdict. your spec: mixed personal+YourCo, decay 7/21/30, on-demand only (no Notion mirror).
>
> **v2.0 (2026-07-15):** Added Layer B backstory paper-trail + RAG push (from "To-Do System with
> Backstory + RAG" spec, email 2026-07-15). See Action 6 below and `memory/Projects/Personal/backstory/README.md`.
> Write confirmations now render the full board (Action 1 LIST logic, reused) instead of a single row —
> this does NOT change the morning kindness rule (top-3 only), which is a separate trigger untouched by this update.

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
| `YourCo todos` | List action (filtered) | Domain=YourCo only |
| `verdict needed`, `stale todos` | List action (filtered) | Status=verdict OR age >30d |
| `add todo {text}` | Add action | Append row, confirm with new ID |
| `add personal todo {text}` | Add action | Append with domain=personal |
| `add YourCo todo {text}` | Add action | Append with domain=YourCo |
| `done {id}` | Resolve action | Move to archive (resolution=done) |
| `kill {id}` | Resolve action | Move to archive (resolution=killed) |
| `defer {id} {date}` | Mutate action | Update due, reset created (freshness reset) |
| `bump {id} {priority}` | Mutate action | Change priority (P0/P1/P2) |
| `today is low energy` / `today is high energy` | Session override | Set morning_energy for this session |
| `backstory {id}`, `tell me about {id}`, `what's the story on {id}` | Backstory read action | Narrate paper-trail from `backstory/T{id}.md` + recall cross-check |
| `backstory {id} {pasted text}`, or pasted correspondence alongside `add todo` | Backstory write action | Extract task row AND backstory file from the same text, same response |

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
   - `personal` / `YourCo` → domain (or use trigger variant)
   - Requestor name mentioned explicitly (e.g. "Jim asked me to...") → `Who Asked`; otherwise `Self`.
     If genuinely ambiguous whether it's your own item or someone else's ask, do NOT guess — set
     `Who Asked: ⚠️ unclear` and say so in the confirmation.
2. Read frontmatter `next_id` from `smart-todos.md`
3. Build new row with defaults: P2 / med energy / no due / domain from trigger or `personal` / `Who Asked: Self` / `Backstory: No`
4. Insert row before example rows OR at table bottom if no examples remain
5. Bump `next_id` in frontmatter
6. Update `last_updated` in frontmatter
7. **Conversation-extraction rule:** if the user pasted raw correspondence (email thread, Slack/Teams
   copy-paste, meeting notes) alongside the add request, do NOT just extract a one-line title — also
   create the backstory file in the same response (see Action 6 WRITE flow). Never ask the user to
   split this into two separate requests. This is still a manual, user-triggered action (pasting text
   into chat) — it does not conflict with the "no auto-create from inbox" scope boundary below.
8. Confirm to user with new ID, then render the full current board (reuse Action 1 LIST logic, all
   domains, no filter) per the v2.0 show-after-write rule.

**Confirmation format:**
```
✅ Added T### — "{title}"
   P{N} | {domain} | {energy} energy | due {date or 'whenever'} | Who Asked: {name or Self}
   Score: {N} (rank: top {K} of {total})
   {IF backstory created}Backstory: [[T###]] created — {N} correspondence entries captured{END IF}

{full board render — same format as `todo list`}
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
   {IF had backstory}Backstory file kept at backstory/T###.md (not deleted — archival record){END IF}

{full board render — same format as `todo list`}
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

{full board render — same format as `todo list`}
```

If `defer` pushes the date >180 days out: ask user "this is essentially a kill — confirm defer-out?" before moving to archive with resolution=`deferred-out`.

---

## Action 5: BUMP (priority change)

Find row, update Priority field, recompute score, confirm, then render the full board (same v2.0 rule as ADD/DONE/KILL/DEFER).

---

## Action 6: BACKSTORY (v2.0, 2026-07-15)

Full spec: `memory/Projects/Personal/backstory/README.md`. Two sub-actions:

### READ — `backstory {id}` / `tell me about {id}` / `what's the story on {id}`

1. Find the row by ID in `smart-todos.md`. If `Backstory: No`, tell the user none exists and offer
   to start one (`backstory {id} {text}`) — do not fabricate history.
2. If `Backstory: Yes → [[T{id}]]`, read `backstory/T{id}.md`.
3. Cross-check with `mcp__hmb-memory__recall(query="{task title keywords}", limit=3)` — surface if
   the vault file and the recall entry disagree (recall entry stale, or vice versa).
4. **Narrate in plain language** — who asked, what's the current state, key decisions, what's left.
   Never dump the raw markdown file at the user.

**Narration format:**
```
📋 T{id} — {title}
   Who: {who_asked} | Status: {status} | Opened: {created}

{2-4 sentence plain-language summary: snapshot + why it exists + latest correspondence}

What's left:
- {unchecked items from "What's needed to complete"}

Full file: backstory/T{id}.md
```

### WRITE — `backstory {id} {text}`, or pasted correspondence during `add todo`

1. If no backstory file exists yet, create one from the template in `backstory/README.md`.
   If one exists, **append** a new dated row to "Correspondence & History" — never overwrite the file.
2. Extract from the pasted text: date/channel/who/summary (Correspondence & History row), any new
   decisions, people, or systems mentioned, and any completed/remaining steps.
3. Update `smart-todos.md`: set `Backstory: Yes → [[T{id}]]` on the row if this is the first backstory write.
4. **RAG push (mandatory):**
   ```python
   mcp__hmb-memory__remember(
       content=f"Task {id}: {title}. Latest: {latest_status_line}. Who: {who_asked}. Systems: {systems_in_play}.",
       type="context",
       tags=f"todo,{domain},{topic_tags}",
       importance=6
   )
   ```
5. **Verify — don't assume the push landed:**
   ```python
   mcp__hmb-memory__recall(query="{title keywords}", limit=3)
   ```
   If the new/updated entry isn't in the top 3, retry once with a more specific query. If it still
   doesn't surface, log a one-line warning in the confirmation (`⚠️ RAG push unverified — retry recall
   manually`) but do NOT block the todo write on this — the vault file is still the source of truth.
6. Confirm to user, then render the full board (v2.0 rule).

**Confirmation format:**
```
✅ Backstory {created|updated}: T### — "{title}"
   {N} correspondence entries | Who: {who_asked}
   RAG: pushed + verified ✅ (or ⚠️ unverified — see above)

{full board render}
```

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
| `Who Asked` ambiguous | Never guess — set `⚠️ unclear`, surface it in the confirmation, resolve on next edit |
| `backstory {id}` with no backstory file | Tell user none exists, offer to start one — don't fabricate history |
| RAG push succeeds but recall doesn't surface it | Retry once with a narrower query; if still absent, warn (not block) and keep the vault file as source of truth |

---

## Out Of Scope (Explicitly)

- Notion sync (you declined — on-demand dispatch only)
- Email integration — **still stays manual.** The v2.0 conversation-extraction rule (Action 2 step 7,
  Action 6 WRITE) only fires when you pastes text into a chat turn himself; nothing auto-scans the
  inbox or auto-creates todos/backstories from it.
- Calendar push (no auto-create calendar events from due dates — separate decision)
- Recurring todos (use `session/one-off-reminders.json` or `schedule-registry.json` for recurring)
- Subtasks / dependencies (Layer A stays flat by design — Skeptic's "no schema fancy"; the backstory
  layer's own checklist ("What's needed to complete") is the closest thing to sub-steps, and it lives
  in Layer B, not as new Layer A schema)
- Auto-completion detection from email/calendar evidence (this exists as a design in the archived-adjacent
  `smart-todo-tracking.md` — deliberately not folded in here; noted as a possible future radar item, not built)

If you want any of these later, the system is designed to extend without breaking. Add a column, add a trigger, ship.
