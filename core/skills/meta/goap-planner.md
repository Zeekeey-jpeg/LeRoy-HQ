---
name: goap-planner
description: Dispatch skill for the thin GOAP goal-tracking system. Handles /goal create/status/next/block/unblock/done/kill/replan/note triggers. Reads session/goals.json; mirrors to memory/Goals/.
context: load-on-trigger
tags: [goal, goap, planning, multi-day]
trigger: "/goal" | "plan goal"
---

# GOAP Planner — Dispatch Skill

> Single source of truth for all goal operations. Triggered by `/goal` commands.
> Built Sprint 3 (2026-05-03) from Ruflo→LeRoy thin-GOAP verdict. Stateful multi-day goals.
> **Does NOT merge with Smart Todos** — coexists. Smart Todos = flat task list. Goals = multi-step initiatives.

---

## File Locations (Fixed)

| File | Purpose |
|------|---------|
| `session/goals.json` | Working set — fast read on every /goal command |
| `memory/Goals/{G-id}.md` | Durability mirror — survives /reset |
| `memory/Goals/archive/{G-id}-{resolution}-{date}.md` | Archived done/killed goals |
| `memory/Goals/index.md` | Folder docs, schema reference, recovery guide |
| `scripts/goal_manager.py` | Atomic state mutations; never call file I/O directly |

---

## When to Use This vs Smart Todos

| Use Smart Todos | Use GOAP Goals |
|----------------|----------------|
| One-off tasks with no ordered sub-steps | Multi-step initiatives spanning days/weeks |
| "Send quote to Mike" (atomic) | "Ship your product v3 with auth refactor" (5 ordered steps) |
| Short-horizon reminders | Long-arc work that survives session resets |
| Domain doesn't matter | Domain matters (cyber/bim/trading/comms/org-business/cyber-bounty/other) |
| Energy/due-date scoring needed | Step-by-step progression + blocker tracking needed |

Both systems coexist. Do NOT auto-migrate todos to goals or vice versa.

---

## Triggers Handled

| User says | Action |
|-----------|--------|
| `/goal {text}` or `plan goal {text}` | Create new goal — LLM proposes 3-8 actions, user confirms |
| `/goal status` | List all active goals with step progress |
| `/goal status G-{id}` | Detail view of one goal |
| `/goal next G-{id}` | Advance current_step by 1 |
| `/goal block G-{id} {reason}` | Add blocker at current step |
| `/goal unblock G-{id}` | Clear all blockers from goal |
| `/goal done G-{id}` | Archive as done, remove from working set |
| `/goal kill G-{id}` | Archive as killed, remove from working set |
| `/goal replan G-{id}` | LLM regenerates remaining actions, user confirms |
| `/goal note G-{id} {text}` | Append free-text note to goal |

---

## Goal Approval UX

When COO presents a proposed goal for confirmation (during CREATE flow):
- User approves by saying **"yes"**, "go", "do it", or "approved"
- COO advances steps internally — never prompts user to run `/goal next`
- `/goal next`, `/goal status`, etc. are available anytime for user visibility, but are NOT required workflow steps
- COO surfaces goal progress in gate boxes (not as action prompts)

---

## Action 1: CREATE (/goal {text})

### Step-by-Step Hybrid Creation Flow

1. **Parse trigger** — extract `title` from everything after `/goal `
2. **Determine domain** — smart-infer from keywords:
   - `bim`, `bim`, `product`, `bim-tool` → `bim`
   - `bounty`, `hackerone`, `xss`, `sqli`, `pentest`, `ctf` → `cyber-bounty`
   - `cyber`, `security`, `hack`, `osint`, `recon` → `cyber`
   - `alpaca`, `bitcoin`, `btc`, `trading`, `portfolio` → `trading`
   - `email`, `telegram`, `client`, `meeting`, `proposal` → `comms`
   - `invoice`, `contract`, `tax`, `quickbooks`, `insurance` → `org-business`
   - No match → ask user to choose from domain list
3. **LLM generates 3-8 action steps** — ordered, concrete, actionable. Based on title + domain. Each step should be completable in one session.
4. **Show numbered list to user:**

```
Goal: "{title}"
Domain: {domain}
Proposed actions:
  1. {action 1}
  2. {action 2}
  3. {action 3}
  ...

Respond with:
  confirm       — accept all steps
  edit N {text} — replace step N with new text
  add {text}    — append a new step
  cancel        — abort
```

5. **On `confirm`** — call `goal_manager.create_goal(title, domain, actions)`, return G-{id}
6. **On `edit N {text}`** — update step N, re-display, ask again
7. **On `add {text}`** — append step, re-display, ask again
8. **On `cancel`** — abort silently

**Confirmation output:**
```
Goal created: G-A7K2QM
"{title}" | domain: {domain} | {N} steps
Current step: 1/{N} — {first action}

Reply 'yes' to confirm and start — COO will execute autonomously.
```

---

## Action 2: STATUS (list all)

Call `goal_manager.list_goals(status="active")`.

**Render format:**
```
================================================================
ACTIVE GOALS — {N} goals
================================================================

G-A7K2QM | org-business | step 2/5 — {current action}
  Title: Ship your product v3 with auth refactor
  Blockers: ⛔ Step 2: waiting on design spec (since 2026-05-02)

----------------------------------------------------------------
Quick actions:
  /goal next G-{id}        advance to next step
  /goal block G-{id} {why} add a blocker
  /goal status G-{id}      see full detail
================================================================
```

If N=0 AND `session/goals.json` is missing or empty: auto-invoke `recover_from_memory()` first, then re-list. If still 0, say "No active goals. Say /goal {text} to create one."

---

## Action 3: STATUS (detail one goal)

Call `goal_manager.get_goal(goal_id)`.

**Render format:**
```
================================================================
GOAL G-A7K2QM
================================================================
Title: Ship your product v3 with auth refactor
Domain: org-business
Status: active
Progress: step 2 of 5

Actions:
  1. [x] Audit current auth flow and identify tech debt
  2. [ ] ** Design new JWT token schema ** ← current
  3. [ ] Implement auth middleware refactor
  4. [ ] Write integration tests
  5. [ ] Deploy to staging + notify team

Blockers:
  ⛔ Step 2: Waiting on design spec from Mike (since 2026-05-02)

Notes:
  the user: keep backward compat with v2 tokens until Q3 cutover.

================================================================
Quick actions:
  /goal next G-A7K2QM       — mark step 2 done, advance to 3
  /goal unblock G-A7K2QM    — clear blocker
  /goal replan G-A7K2QM     — regenerate remaining steps
  /goal done G-A7K2QM       — archive as complete
================================================================
```

---

## Action 4: NEXT (/goal next G-{id})

Call `goal_manager.advance_step(goal_id)`.

Output:
```
G-A7K2QM advanced: step 2 → 3 of 5
Now on: "Implement auth middleware refactor"

Say /goal next G-A7K2QM when step 3 is done.
If all steps complete: /goal done G-A7K2QM
```

If already at last step: "Already on final step (5/5). Say /goal done G-{id} to archive."

---

## Action 5: BLOCK (/goal block G-{id} {reason})

Call `goal_manager.add_blocker(goal_id, reason)`.

Output:
```
⛔ Blocker added to G-A7K2QM at step 2:
  "{reason}"

Say /goal unblock G-A7K2QM to clear when resolved.
```

---

## Action 6: UNBLOCK (/goal unblock G-{id})

Call `goal_manager.clear_blocker(goal_id)`.

Output:
```
G-A7K2QM unblocked. All blockers cleared.
Current step: 2 — "Design new JWT token schema"
```

---

## Action 7: DONE (/goal done G-{id})

Call `goal_manager.mark_done(goal_id)`.

Output:
```
G-A7K2QM archived as DONE.
Archived to: memory/Goals/archive/G-A7K2QM-done-{date}.md
```

---

## Action 8: KILL (/goal kill G-{id})

Call `goal_manager.mark_killed(goal_id)`.

Output:
```
G-A7K2QM archived as KILLED.
Archived to: memory/Goals/archive/G-A7K2QM-killed-{date}.md
```

---

## Action 9: REPLAN (/goal replan G-{id})

**Manual-only. LLM regenerates remaining actions from current_step onward. User confirms.**

1. Get goal via `goal_manager.get_goal(goal_id)`
2. Show current progress (completed steps) and current_step
3. LLM proposes new actions for remaining steps based on goal title + domain + notes + blockers
4. Show to user in same confirm/edit/add/cancel flow as CREATE
5. On confirm: call `goal_manager.replan(goal_id, new_actions)`

Output:
```
G-A7K2QM replanned. {N} remaining steps replaced.
Current step: {current} — "{new current action}"
```

---

## Action 10: NOTE (/goal note G-{id} {text})

Call `goal_manager.add_note(goal_id, text)`.

Output:
```
Note appended to G-A7K2QM:
  "{text}"
```

---

## Domain Tag Enum

| Domain | When to use |
|--------|------------|
| `cyber` | Security research, CTF, OSINT, recon (non-bounty) |
| `cyber-bounty` | Active bug bounty campaigns, HackerOne/Bugcrowd work |
| `bim` | your BIM tool, BIM, your product, your BIM connector, BIM360 work |
| `comms` | Client communication, email campaigns, meeting prep |
| `org-business` | Contracts, proposals, invoices, taxes, insurance, your org ops |
| `other` | Everything else; can be refined later with /goal replan |

---

## Blocker Semantics

- A blocker records: `at_step` (which step), `reason` (text), `since_ts` (ISO timestamp)
- Multiple blockers are allowed (each `/goal block` appends)
- `/goal unblock` clears ALL blockers — not selective by design (thin form v1)
- A blocked goal still appears in `/goal status` list — the ⛔ icon signals it
- COO surfaces blocked goals in Deployment Manifest when count >0 and task is Tier-2+

---

## Done / Kill Archival Rules

| Action | What happens |
|--------|-------------|
| `/goal done G-{id}` | status → done, archived to `memory/Goals/archive/G-{id}-done-{date}.md`, removed from `session/goals.json` |
| `/goal kill G-{id}` | status → killed, archived to `memory/Goals/archive/G-{id}-killed-{date}.md`, removed from `session/goals.json` |

Archives are permanent. There is no undo. Re-create if accidentally killed.

---

## Replan Flow Detail

```
User: /goal replan G-A7K2QM
COO: Goal G-A7K2QM — "Ship your product v3 with auth refactor"
     Completed steps (1-1):
       1. [x] Audit current auth flow

     Remaining steps to replace (2-5):
       2. Design new JWT token schema
       3. Implement auth middleware refactor
       4. Write integration tests
       5. Deploy to staging

     Proposed replacement for steps 2-5:
       2. Simplify: keep existing JWT structure, add refresh token support only
       3. Implement refresh token endpoint
       4. Update existing tests for new endpoint
       5. Deploy to staging + monitor for 24h

     confirm | edit N {text} | add {text} | cancel
```

Only the remaining steps are replaced. Completed steps are preserved.

---

## Recovery from Session Reset

When `/reset` clears the session, `session/goals.json` may be gone. Recovery is automatic:

1. On the next `/goal status` call, if `goals.json` is missing or `{"goals": []}`, dispatch skill calls `goal_manager.recover_from_memory()` before rendering
2. `recover_from_memory()` scans `memory/Goals/G-*.md` (skipping archive/) and rebuilds `goals.json`
3. Goals with `status: done` or `status: killed` in frontmatter are NOT added back to the working set

Manual recovery:
```python
import sys; sys.path.insert(0, '~/.claude/scripts')
import goal_manager; goal_manager.recover_from_memory()
```

---

## Editing goals.json Safely

If you must manually edit a goal (not via triggers):

1. Open `session/goals.json` in any text editor
2. Find the goal by `id`
3. Update the field (e.g., `current_step`)
4. Also update the matching `memory/Goals/{id}.md` frontmatter — keep both in sync
5. Save both files

If they diverge, `session/goals.json` wins for the current session. On next `/reset`, memory wins.

---

## How COO Uses Goals (Tier-2+ only)

On Tier-2+ tasks (4+ work packets), the COO consults `session/goals.json` and displays:

```
Active Goals: 2 | G-A7K2QM step 2/5 (blocked) | G-X9Q3LR step 1/4
```

In the Deployment Manifest. This is display-only — COO does NOT auto-advance steps. the user uses `/goal next` explicitly.

---

## Disabling

There are no hooks. Just stop using the triggers. `goal_manager.py` is called only on explicit `/goal` invocations — it has no background workers, no PreToolUse hooks, no cron.

To archive all goals at once: iterate via `list_goals()` and call `mark_killed()` on each. The `memory/Goals/archive/` folder will retain the records.

---

## Error Handling

| Issue | Response |
|-------|---------|
| `G-{id}` not found | "G-{id} not found in active goals. Say /goal status to see current IDs." |
| `goals.json` missing | Auto-invoke `recover_from_memory()` then retry |
| Invalid domain on create | Ask user to choose from the 7-value enum |
| No actions provided | "Please provide at least 1 action step." |
| Write failure | Warn: "Could not persist goal — check session/ write permissions." |
