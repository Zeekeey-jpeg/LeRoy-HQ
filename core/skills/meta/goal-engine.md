---
name: goal-engine
description: Goal Engine v2.0 — two-tier autonomous goal system. Standard (5-10 steps, <15 min) and High Effort (20-50 steps, 1hr+, overnight capable). Handles /goal create/status/next/block/unblock/done/kill/replan/note/resume/pause/watch. Spawns goal-overseer agent for High Effort execution. Sends Telegram ping on completion.
context: load-on-trigger
tags: [goal, autonomous, planning, multi-day, high-effort]
trigger: "/goal" | "plan goal"
version: "2.0"
supersedes: skills/meta/goap-planner.md
---

# Goal Engine v2.0 — Dispatch Skill

> Stateful multi-day goal tracker with two execution tiers.
> Standard: quick-confirm, COO-driven, <15 min.
> High Effort: manifest-approval, overseer-driven, overnight capable, Telegram ping on done.
> Does NOT merge with Smart Todos — separate systems.

---

## Tier Definitions

| | Standard | High Effort |
|---|---|---|
| Steps | 5–10 | 20–50 |
| Agents | 2–3 | 5–15 (overseer + specialists) |
| Web research | No | Yes |
| Testing / validation | No | Yes (guardian required) |
| Est. runtime | <15 min | 1hr – overnight |
| Approval gate | Quick confirm | Full manifest review |
| Telegram ping | Optional | **Required** |
| Checkpoint saves | Every step | Every step + phase boundary |
| Failure behavior | Report in chat | Pause + Telegram alert |
| Overseer agent | No | Yes (spawned via TaskCreate) |

**Auto-tier rule:** If goal text contains any of: `research`, `web`, `test`, `validate`, `deploy`, `overnight`, `20+ steps`, or domain is `cyber-bounty` → High Effort. Otherwise Standard. User can override with `--standard` or `--high`.

---

## File Locations

| File | Purpose |
|------|---------|
| `session/goals.json` | Working set — fast read on every /goal command |
| `memory/Goals/{G-id}.md` | Durability mirror — survives /reset |
| `memory/Goals/archive/{G-id}-{resolution}-{date}.md` | Archived done/killed |
| `memory/Goals/index.md` | Schema reference, recovery guide |
| `scripts/goal_manager.py` | All state mutations — never call file I/O directly |
| `agents/goal-overseer.md` | High Effort autonomous execution agent |

---

## Trigger Commands

| User says | Action |
|-----------|--------|
| `/goal {text}` or `plan goal {text}` | Detect tier → propose steps → confirm → create |
| `/goal {text} --standard` | Force Standard tier |
| `/goal {text} --high` | Force High Effort tier |
| `/goal status` | List all active/running/paused goals |
| `/goal status G-{id}` | Detail view of one goal |
| `/goal next G-{id}` | Advance current_step (Standard) or confirm overseer step (High Effort) |
| `/goal block G-{id} {reason}` | Add blocker at current step |
| `/goal unblock G-{id}` | Clear all blockers |
| `/goal done G-{id}` | Archive as complete |
| `/goal kill G-{id}` | Archive as killed |
| `/goal replan G-{id}` | Regenerate remaining steps — user confirms |
| `/goal note G-{id} {text}` | Append free-text note |
| `/goal resume G-{id}` | Resume paused goal from last checkpoint |
| `/goal pause G-{id}` | Manually pause a running goal |
| `/goal watch G-{id}` | Show live step progress of running goal |

---

## Action 1: CREATE

### Step 1 — Parse trigger
Extract `title` from everything after `/goal ` (strip `--standard`/`--high` flags).

### Step 2 — Detect tier
Auto-detect (see rules above) unless `--standard` or `--high` given.

### Step 3 — Detect domain
- `bim`, `bim`, `product`, `bim-tool` → `bim`
- `bounty`, `hackerone`, `ctf`, `xss`, `sqli`, `pentest` → `cyber-bounty`
- `cyber`, `security`, `osint`, `recon` → `cyber`
- `alpaca`, `bitcoin`, `trading`, `portfolio` → `trading`
- `email`, `telegram`, `client`, `proposal` → `comms`
- `invoice`, `contract`, `tax`, `quickbooks`, `insurance` → `org-business`
- No match → ask user to choose

### Step 4 — Generate actions

**Standard:** 5–10 concrete, ordered steps. Each completable in one session.

**High Effort:** 20–50 steps organized in named phases:
- Phase 1: Research & recon (5–8 steps)
- Phase 2: Implementation (10–20 steps)
- Phase 3: Testing & validation (5–10 steps)
- Phase 4: Delivery + notification (2–5 steps)
  - Final step MUST be: "Send Telegram completion ping to the user"

### Step 5 — Show to user

**Standard confirmation format:**
```
Goal: "{title}"
Tier: STANDARD | Domain: {domain}
Proposed actions:
  1. {action 1}
  ...
  N. {action N}

confirm | edit N {text} | add {text} | cancel
```

**High Effort manifest format:**
```
GOAL MANIFEST — (pending ID)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Tier:        HIGH EFFORT
Domain:      {domain}
Objective:   {title}
Steps:       {N} total across {P} phases
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Agents:      overseer + {specialists list}
Resources:   {web_search? file_system? MCP tools?}
Est. Runtime: {low}–{high} min (overnight safe)
Cost Est:    ~${low}–${high}

Phase breakdown:
  Phase 1 Research      (steps  1–8)
  Phase 2 Implementation (steps 9–25)
  Phase 3 Testing        (steps 26–32)
  Phase 4 Delivery       (steps 33–35)

Completion ping: Telegram chat_id <YOUR_TELEGRAM_CHAT_ID>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
confirm | review steps | edit N {text} | add {text} | cancel
```

### Step 6 — On confirm
Call `goal_manager.create_goal(title, domain, actions, tier, manifest)`.

For High Effort: spawn goal-overseer immediately via TaskCreate (background), then call `goal_manager.set_overseer(goal_id, task_id)`.

**Confirmation output (Standard):**
```
Goal created: G-A7K2QM
"{title}" | STANDARD | domain: {domain} | {N} steps
Current step: 1/{N} — {first action}

/goal next G-A7K2QM when step 1 is done.
```

**Confirmation output (High Effort):**
```
Goal created: G-A7K2QM
"{title}" | HIGH EFFORT | domain: {domain} | {N} steps
Overseer deployed — running autonomously.

I'll ping you on Telegram when done. Say /goal watch G-A7K2QM to check progress.
You can /goal pause G-A7K2QM to halt at any time.
```

---

## Action 2: STATUS (list all)

Call `goal_manager.list_all_active()` (returns both active + running).

```
================================================================
ACTIVE GOALS — {N} goals
================================================================

G-A7K2QM | HIGH EFFORT | org-business | ● RUNNING step 7/35
  Title: {title}
  Overseer: active | Checkpoint: step 6
  Blockers: none

G-X9Q3LR | STANDARD | bim | step 2/8
  Title: {title}
  Blockers: ⛔ Step 2: waiting on your BIM tool file (since 2026-05-18)

================================================================
Quick: /goal status G-{id} | /goal next G-{id} | /goal pause G-{id}
================================================================
```

If no goals and goals.json missing/empty: auto-invoke `recover_from_memory()` first, then re-list.

---

## Action 3: STATUS (detail one goal)

```
================================================================
GOAL G-A7K2QM | HIGH EFFORT
================================================================
Title: {title}
Domain: {domain} | Status: RUNNING
Progress: step 7 of 35 | Checkpoint: step 6
Overseer: active (task_id: {id})

Phases:
  ✅ Phase 1 Research      (steps 1–8)  ← in progress
  ○  Phase 2 Implementation (steps 9–25)
  ○  Phase 3 Testing        (steps 26–32)
  ○  Phase 4 Delivery       (steps 33–35)

Actions:
  1–6: [x] (completed)
  7. [ ] ** {current action} ** ← current
  8–35: [ ] (pending)

================================================================
/goal watch G-A7K2QM | /goal pause G-A7K2QM | /goal status G-A7K2QM
================================================================
```

---

## Action 4: NEXT (/goal next G-{id})

**Standard only.** For running High Effort goals, say: "Overseer is managing this autonomously. Say /goal watch G-{id} to check progress or /goal pause G-{id} to halt."

Call `goal_manager.advance_step(goal_id)`.

```
G-A7K2QM advanced: step 2 → 3 of 8
Now on: "{next action}"

/goal next G-A7K2QM when step 3 is done.
If all complete: /goal done G-A7K2QM
```

---

## Action 5: RESUME (/goal resume G-{id})

1. Get goal via `goal_manager.get_goal(goal_id)`
2. Verify status is `paused`
3. Show: "Resuming G-{id} from checkpoint step {checkpoint_step}. Restarting overseer from step {checkpoint_step + 1}."
4. Call `goal_manager.resume_goal(goal_id)` → sets status to `running`
5. Spawn goal-overseer via TaskCreate (background), passing `resume_from=checkpoint_step+1`
6. Call `goal_manager.set_overseer(goal_id, new_task_id)`

```
G-A7K2QM resumed.
Overseer restarted from step {checkpoint_step + 1}/{N} — "{action text}"
I'll ping Telegram on completion.
```

---

## Action 6: PAUSE (/goal pause G-{id})

1. Get goal. If not running: "G-{id} is not currently running (status: {status})."
2. Call `goal_manager.pause_goal(goal_id, current_step, "Manual pause by the user")`
3. Note: overseer is a background agent — it will naturally wind down on its next checkpoint. Checkpoint data ensures no step is lost.

```
G-A7K2QM paused at step {current_step}/{N}.
Last checkpoint: step {checkpoint_step}

/goal resume G-A7K2QM to continue from step {checkpoint_step + 1}.
```

---

## Action 7: WATCH (/goal watch G-{id})

Read goal from `goal_manager.get_goal(goal_id)`. Render live snapshot:

```
G-A7K2QM — LIVE SNAPSHOT
━━━━━━━━━━━━━━━━━━━━━━━━━
Status: RUNNING
Progress: step {current}/{total}
Checkpoint: step {checkpoint} (last confirmed complete)
Current: "{action text}"
Runtime so far: ~{elapsed} min

Last updated: {updated_at}
━━━━━━━━━━━━━━━━━━━━━━━━━
/goal pause G-A7K2QM to halt
```

---

## Actions 8–12: BLOCK / UNBLOCK / DONE / KILL / REPLAN / NOTE

Identical to goap-planner.md v1 — unchanged logic. See that file for full detail.

---

## High Effort Overseer Spawn Protocol

When creating or resuming a High Effort goal, spawn the goal-overseer agent:

```
Task tool:
  subagent_type: goal-overseer
  run_in_background: true
  prompt: |
    Execute High Effort goal {goal_id}.
    Title: {title}
    Domain: {domain}
    Total steps: {N}
    Resume from step: {resume_from}  (0 for new goals)
    Manifest: {json.dumps(manifest)}
    Telegram chat_id: <YOUR_TELEGRAM_CHAT_ID>
    
    Read scripts/goal_manager.py for all state mutations.
    Read agents/goal-overseer.md for execution protocol.
```

---

## Domain Tag Enum

| Domain | When to use |
|--------|------------|
| `cyber` | Security research, CTF, OSINT, recon (non-bounty) |
| `cyber-bounty` | Active bug bounty campaigns |
| `bim` | your BIM tool, BIM, your product, your BIM connector |
| `comms` | Client communication, proposals |
| `org-business` | Contracts, invoices, taxes, your org ops |
| `trading` | Alpaca, portfolio management |
| `other` | Everything else |

---

## Blocker Semantics

- Blockers record: `at_step`, `reason`, `since_ts`
- Multiple blockers allowed per `/goal block`
- `/goal unblock` clears ALL blockers
- Blocked High Effort goals: overseer halts at blocker step, sends Telegram alert

---

## Recovery from Session Reset

On `/goal status` if goals.json missing/empty → auto-call `goal_manager.recover_from_memory()`.
Manual: `python scripts/goal_manager.py` or `python -c "import sys; sys.path.insert(0, '~/.claude/scripts'); import goal_manager; goal_manager.recover_from_memory()"`

---

## COO Gate Display (Tier-2+ tasks)

When active/running goals exist on Tier-2+ tasks:
```
Goals: {N} active | G-A7K2QM HIGH EFFORT step 7/35 (running) | G-X9Q3LR STANDARD step 2/8
```

---

## Error Handling

| Issue | Response |
|-------|---------|
| G-{id} not found | "G-{id} not found. Say /goal status to see current IDs." |
| goals.json missing | Auto recover_from_memory() then retry |
| Invalid domain | Ask user to choose from enum |
| Overseer spawn fails | Create goal as active (Standard fallback), warn the user |
| Telegram ping fails | Log to leroy.log, note in goal, do not crash |
