---
name: debate-auto-invoke
description: >
  Protocol spec for the PreToolUse hook that auto-invokes debate-by-council
  when Claude presents option lists via AskUserQuestion. Covers eligibility
  (explicit opt-in flag), hard denylist, recursion guard, and the COO A2A
  Inquisitor answerer flow. Paired with hooks/debate-auto-invoke.py.
disable-model-invocation: true
---

# Debate Auto-Invoke Protocol

## Purpose

Guarantee that when Claude presents consequential option lists (A/B/C) to the user,
the debate-by-council council runs automatically — no reliance on Claude
remembering to invoke it. Enforced by a hook so it cannot be skipped.

## Architecture Summary

```
Claude → AskUserQuestion(question, options)
   ↓
PreToolUse hook: hooks/debate-auto-invoke.py
   ↓
   [ kill switch? recursion flag? denylist? eligibility flag? ]
   ↓
  approve  ───────────────►  question shown to user normally
  block    ───────────────►  writes enforcement.todo →
                             Claude runs debate-by-council (auto mode) →
                             COO answers Inquisitor Qs via Task →
                             5-persona debate + vote + verdict →
                             clears in_flight → re-invokes AskUserQuestion
```

## Eligibility (Phase 0: Explicit Opt-In Only)

The hook fires a debate **only** when `session/debate-pending.flag` exists and
contains a JSON payload. The hook consumes (deletes) the flag on read, so it's
single-shot.

**Flag file format:** `~/.claude\session\debate-pending.flag`

```json
{
  "eligible": true,
  "stakes": ["architectural", "irreversible"],
  "skill": "skills/workflows/planning/planning-phase.md",
  "set_at": "2026-04-23T15:30:00Z"
}
```

**How to set the flag** (from a skill or agent before calling AskUserQuestion):

```bash
# Bash example — any skill that wants a debate before presenting its option list
cat > .claude/session/debate-pending.flag <<'JSON'
{"eligible": true, "stakes": ["architectural"], "skill": "my-skill.md"}
JSON
```

**Stakes vocabulary (informational only, for logging and Inquisitor briefing):**
- `architectural` — structural system changes
- `irreversible` — cannot be undone without damage
- `financial` — money, trades, budget commitment
- `legal` — contracts, liability, compliance
- `strategic` — roadmap, pivot, direction
- `production` — deploy, release, live systems

Phase 1 will add a keyword-heuristic path that fires without the explicit flag
when question text matches 2+ stakes families. Phase 0 ships opt-in only.

## Hard Denylist (Always Bypasses Debate)

The hook **approves immediately** when any of these are true — no debate fires
regardless of eligibility flag:

**Skill / context denylist:**
- Any `skills/routines/telegram-*`
- `skills/routines/session-reset.md`
- `skills/routines/telegram-reset.md`
- `skills/routines/daily-ops.md`
- `skills/routines/morning.md`
- `skills/routines/backup-reminder.md`
- `skills/routines/heartbeat.md`
- `skills/domains/cyber/bounty-session-enforcer.md` (Phase 0 gate)
- `skills/domains/cyber/whitehat-protocol.md`
- `skills/domains/cyber/given-program-fast-path.md`

**Project path denylist:**
- `memory/Projects/Research/**` (bounty sweeps have their own Phase 0)

**Text-token denylist** (scanned in the question text):
- `"/reset"`, `"session reset"`, `"telegram session"`
- `"phase 0"`, `"scope confirm"`

**Cooldown:** 60 seconds after the last debate's `in_flight` clear. Prevents
back-to-back debates in rapid-fire interactive flows.

## Recursion Guard

`state.debate_auto_invoke.in_flight`:
- Set to `true` when the hook blocks and triggers a debate
- Must be cleared to `false` by Claude after the verdict is delivered AND
  the original AskUserQuestion has been re-invoked
- While `true`, the hook approves ALL AskUserQuestion calls (debate-by-council
  itself uses the tool internally; must not self-trigger)
- Stop-hook safety net: `gate-validator-trigger.py` should clear stale flags
  on session end

## COO Inquisitor Template (A2A)

When Claude handles a `DEBATE_AUTO_INVOKE` enforcement action, spawn
`@agent-conductor` (COO) via the `Task` tool with this prompt:

```
You are COO answering Debate-by-the user Inquisitor questions for an
auto-invoked debate.

Pending decision: {question}
Options: {options}
Stakes detected: {stakes_list}
Calling skill: {skill_name}

Answer these 3 Inquisitor questions. Use your org-wide knowledge of
your org, active projects, agent roster, and memory vault.
3-5 sentences each. Under 400 words total.

Q1 (Constraints & irreversibility): What hard constraints does this
decision face, and which aspects would be hard to undo if wrong?

Q2 (Inverse position): What is the strongest argument for the OPPOSITE
of what seems obvious here?

Q3 (Hidden stakeholders & downside risk): Who else is affected that
hasn't been mentioned, and what's the worst realistic outcome?

Return in this format:
**COO ANSWER Q1:** ...
**COO ANSWER Q2:** ...
**COO ANSWER Q3:** ...
**COO RECOMMENDATION:** (1 paragraph gut read)
```

**Timing target:** <2s median. If >5s, fall back to asking the user directly
(manual Inquisitor mode).

**Why COO, not the user:** the user explicitly requested the COO handle the
Inquisitor phase because "it has a pulse on the entire framework." the user
still sees the full 5-persona debate, the vote, and the verdict — and he
still picks from the final options. The Inquisitor friction (3 Qs) is
absorbed by COO so automation doesn't add user-facing delay.

## Post-Verdict Flow

After the 5-persona debate renders and the verdict is displayed, Claude MUST:

1. Clear the recursion flag:
   ```
   Edit state.json → debate_auto_invoke.in_flight = false
   Set debate_auto_invoke.last_verdict = {result, tally, summary}
   ```
2. Delete the DEBATE_AUTO_INVOKE block from `enforcement.todo` (or the whole
   file if that was the only action)
3. Re-invoke `AskUserQuestion` with the original question payload from
   `state.debate_auto_invoke.pending_question`
4. The hook will approve this re-invocation (cooldown active → denylist path)
5. the user selects an option, debate context informing the choice

## Logging & Observability

Every hook decision is appended to `session/debate-auto-invoke-log.jsonl`:

```json
{"timestamp": "...", "decision": "approve|block", "reason": "...",
 "question_preview": "...", "stakes": [...], "elapsed_ms": 12.4}
```

Review weekly to tune denylist, add keyword families, and measure:
- False positive rate (eligible calls that got approved)
- False negative rate (trivial calls that got blocked)
- p95 latency (target <30ms)

## Kill Switch

To disable the hook entirely without editing settings.json:

```bash
touch .claude/session/debate-auto-invoke.disabled
```

Hook will short-circuit to approve-silently on every call while this file
exists. Delete the file to re-enable.

## Phase Rollout

- **Phase 0 (shipped):** opt-in flag + denylist + recursion guard + kill
  switch. Heuristic path OFF.
- **Phase 1:** add keyword-heuristic eligibility (2+ stakes-family match in
  question text). Monitor log 48h.
- **Phase 2:** tune keyword families from real hit/miss ratio. Consider 6th
  persona (CTO) for critical-stakes debates (5+ families).

## Related Files

- Hook: `hooks/debate-auto-invoke.py`
- Council skill: `skills/meta/debate-by-council.md`
- Settings wire-up: `settings.json` → `hooks.PreToolUse[matcher=AskUserQuestion]`
- COO spec: `agents/conductor.md` (Inquisitor Answerer section)
- State schema: `session/state.json` → `debate_auto_invoke` block
