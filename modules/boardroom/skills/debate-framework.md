# The Debate Framework — how a scene is assembled, run, and logged

This is the operational contract for the Boardroom. It describes how one
**scene** (a single complete debate) goes from a topic to a ledger entry. The
persona cast and disposition library it draws from live in
[`personas.md`](personas.md); the spend rules it obeys live in
[`../governor.md`](../governor.md).

---

## Core design decision: one model call per scene

The whole room is generated in a **single model call** — one model instance
role-playing every seat at once — not one call per persona. Two reasons:

1. **Cost.** N personas × M turns as separate calls is roughly an order of
   magnitude more expensive than one call that writes the whole transcript.
2. **Coherence.** A single writer producing the whole room naturally has each
   persona reference the others by name, interrupt, and build on prior turns —
   the conversation is more alive, not less.

The call returns **strict JSON** matching the scene contract below. A malformed
reply is regenerated (optionally on a fallback model) rather than dropped.

---

## Scene pipeline

```
1. Governor preflight   → refuse early if any spend/cadence gate fails (0 tokens)
2. Load ledger memory   → recent decisions, open threads, ground truth
3. Accept / pick topic  → an explicit topic, an injected message, or a live signal
4. Draw dispositions    → one stance per persona; guarantee ≥1 dissent
5. Assemble the prompt   → ground truth + cast + memory + topic + rules
6. Generate scene        → single model call → strict JSON
7. Inquisitor + chair    → dissent forced on record; chair rules
8. Persist               → append to decision ledger + usage ledger
```

### 1. Governor preflight
Before any spend, the governor is consulted. If a cap is hit, a cadence gate
fails, or the kill-switch flag exists, the scene is **refused and logged** with a
reason and **no tokens are spent**. See [`../governor.md`](../governor.md).

### 2. Load ledger memory (ground truth)
The ledger (`decisions.json` by default) is the room's permanent memory. From it
the framework derives a **GROUND TRUTH** block — the authoritative list of what is
actually shipped, what failed to land, what's in flight, what was declined, and
what's awaiting approval. This block carries an **epistemic law**:

> A scene may state that something is shipped/live/deployed **only** if it appears
> in the confirmed-deployed list. Everything else anyone ever proposed is
> *proposed, not built*. Fabricating completion is the gravest failure a member
> can commit — it corrupts the room's memory.

This is what stops the room from re-proposing or "remembering" work that never
happened.

### 3. Accept or pick a topic
Topic sources, in priority order:
1. **Explicit topic** you hand it (on-demand decision).
2. **Injected message** — you drop a live remark into an ongoing scene and the
   room continues *that exact thread* (acknowledges you by name, picks up where
   it left off) rather than starting over.
3. **Live signal** — when running on a schedule, a topic ranker surfaces the most
   worthwhile thing to discuss (e.g. system usage, version-control activity, open
   threads, curated external signals). Noise sources should be excluded at the
   ranker, not throttled after the fact. An evergreen self-improvement backlog is
   the fallback when nothing real is happening.

### 4. Draw dispositions
Per [`personas.md`](personas.md): one stance per persona, affinity-weighted,
anti-repeat vs. the last scene, with at least one dissenting stance guaranteed.

### 5. Assemble the prompt
The prompt is built from: the GROUND TRUTH block, the cast with each persona's
per-scene frame, the ledger memory, the topic seed, and the scene rules (below).

### 6. Generate the scene
One model call, strict-JSON output. Contract in the next section.

### 7. Inquisitor + chair
The Inquisitor's costed dissent must appear in the turns; the chair (General)
must overrule or accept it before `outcome` is set. No dissent on the record ⇒
regenerate.

### 8. Persist
Append the scene to the decision ledger and the usage ledger (real token counts,
so the governor's windows are accurate). Retain at most the cap's worth of live
conversations; archive the oldest beyond it.

---

## How a scene must *feel*

These rules produce a real debate instead of round-robin status updates:

- A genuine back-and-forth — personas speak **multiple times**, not once each.
- A claim → a challenge → a follow-up question → a concession or a doubling-down.
- **At least one interruption** (a turn flagged `interrupts: true`).
- At least one moment of disagreement **and** one of agreement.
- Each persona argues from **today's disposition** — let frames clash; that *is*
  the drama.
- Emotions are **earned** by topic + stance, never random.
- The chair forces the decision near the end; the Diplomat notes what the human
  needs to see.
- **Tight:** roughly 9–16 turns. No monologues (1–3 sentences per turn).
- **Honor the ledger:** never re-propose anything already built/deployed/declined.
  Build the next phase on top of settled work, or pick a fresh angle.
- **Close the loop:** open with a one-line status confirmation of recently
  shipped / failed-to-land items so nothing silently disappears.
- **Be proactive:** the best scenes surface something *new* — earn the seat by
  inventing, not just reviewing.
- **"No decision warranted" is respected:** conclude cleanly with a consensus
  outcome; do not manufacture a proposal.

---

## The scene JSON contract

The single model call must return exactly this shape (no prose, no code fences):

```json
{
  "label": "<2-3 word noun phrase naming the THING (e.g. 'Session sync hardening')>",
  "topic": "<one-line restatement of what was discussed>",
  "turns": [
    {
      "speaker_id": "<persona id>",
      "speaker": "<persona name>",
      "emotion": "<one emotion>",
      "text": "<1-3 sentences, in voice>",
      "interrupts": false,
      "addressed_to": "<persona id or null>"
    }
  ],
  "outcome": {
    "type": "decision|parked|consensus|exhausted",
    "summary": "<1-2 sentences: what the room concluded>"
  },
  "proposal": null
}
```

When there is a concrete recommendation, `proposal` is an object instead of null:

```json
{
  "title": "<short>",
  "tier": "green|approval|never",
  "impact": "<integer 1-10 — business leverage, NOT effort; see rubric>",
  "impact_rationale": "<one sentence defending the impact score>",
  "what": "<a single YES/NO the human can approve or deny with no extra input, ending in (Approve = … ; Deny = …)>",
  "why": "<one sentence>",
  "plain": "<one jargon-free sentence: what changes and why it matters>",
  "tech": "<one concrete sentence for the engineer: the mechanism/change>",
  "owner": "<persona id>",
  "needs_approval": true
}
```

**Contract guard.** The playback engine, ledger writer, and any downstream
pipeline all depend on this shape. Validate before persisting:
- `turns` non-empty; every turn has a speaker and text.
- `label` and `topic` present.
- `outcome.type` ∈ `{decision, parked, consensus, exhausted}`.
- if `proposal` is non-null: `title`, `tier` ∈ `{green, approval, never}`, and
  `what` present.

A scene failing the guard is regenerated (optionally on a fallback model).

### Tier & impact policy

- **`green`** — internal reliability / monitoring / self-healing / plumbing with
  no new user-facing surface and low blast radius. **Auto-ships**; the human is
  never asked. `needs_approval` = false.
- **`approval`** — a genuinely new user-facing feature or a consequential shift.
  Reserved for things worth a human's explicit tap. `needs_approval` = true.
- **`never`** — noise / redundant / low-leverage. **Kill it.** A scene that kills
  a weak idea is a success. `proposal` null or tier `never`.

Rule of thumb: across many scenes, only a small fraction should be `approval`;
the rest are `green` (auto-ship) or `never` (killed).

**Impact (1-10)** scores *business leverage*, not effort or tier:
- **9-10** — moves the business (revenue, a shippable product, saves a client,
  10x's a core workflow).
- **7-8** — a force-multiplier noticed within a day; kills a real bottleneck.
- **4-6** — a solid internal win (reliability, observability). Useful, not
  exciting.
- **1-3** — housekeeping. If the best idea lands here, prefer a no-decision.

The Inquisitor must challenge the *impact score itself*, not just the idea. If
the room can't honestly defend a 7+, prefer a clean no-decision over a padded 5.

---

## Scheduling

The framework is scheduler-agnostic. Point any of these at the scene runner and
pass a cadence:

- **cron** (Unix/macOS)
- **Task Scheduler** (Windows)
- your harness's own routine/cron system

A typical cadence is a few scenes overnight plus a handful through the day. The
**governor's ceilings are the safety net** — set them so your intended cadence
never trips the runaway backstop. Scheduled scenes may be *forced* (they bypass
the interactive-cadence gates because the schedule itself is the cadence), but
they **still respect the token ceilings and the kill switch**.

Overnight ledger entries feed a **morning briefing**: the human wakes to "here's
what the board decided / wants approval on" instead of attending meetings.
