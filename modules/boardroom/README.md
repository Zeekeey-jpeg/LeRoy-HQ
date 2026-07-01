# leroy-boardroom

> A simulated C-suite that **debates your consequential decisions** and **watches
> your system for improvements** — then logs what it decided so you never
> relitigate a settled call.

**Status: DEFAULT OFF. Opt-in. Token-heavy.**
This module spends model tokens on every scene it generates. It ships disabled
and does nothing until you turn it on:

```sh
leroy enable boardroom      # or: leroy add boardroom
```

Recommended on a flat-rate plan (e.g. Claude Max) rather than metered API
billing — see [Cost & the Governor](#cost--the-governor).

---

## What the Boardroom is

Most agent frameworks give you *one* assistant. The Boardroom gives you a **room
of them** — a small standing panel of executives with fixed personalities,
memory, and opinions who convene, argue a topic to a real conclusion, and record
the outcome.

A single **scene** is one complete debate: a topic comes in, the panel talks it
out (claims, challenges, an interruption, a concession), a chair forces a call,
and the result is written to a **decision ledger**. The next scene reads that
ledger, so the room never re-proposes something it already shipped or killed.

Two jobs:

1. **Decide** — when you (or a monitor) surface a consequential choice, the room
   debates it from five different angles and returns a recommendation you can
   approve or deny in one tap.
2. **Watch** — left running on a schedule, the room proactively inspects the
   system (usage, git activity, open threads, external signals) and surfaces
   improvements you didn't ask for, gated so only the worthwhile ones reach you.

Plain-English analogy: it's a **board of directors for your automation** — five
advisors who won't let a big call go through on a single opinion, and who keep
minutes so the same argument never happens twice.

---

## The panel (5 personas + the Inquisitor)

Each persona has a **constant core** (voice, expertise, values — they always
*sound* like themselves) and draws a **per-scene disposition** (their stance/mood
for *this* topic only). That split is why the same advisor can champion an idea
one day and gut it the next — the soul stays fixed, the angle rotates. See
[`skills/personas.md`](skills/personas.md) for the disposition library.

| Persona       | One-line lens                          | Always asks…                              |
|---------------|----------------------------------------|-------------------------------------------|
| **General**   | Act now. Bias to shipping.             | "What do we *do*, and who owns it?"       |
| **Sage**      | The 5-year view. Second-order effects. | "Where does this leave us in a year?"     |
| **Skeptic**   | What breaks. The costed downside.      | "What's the weakest assumption here?"     |
| **Diplomat**  | People & how it lands.                 | "Who's affected, and how do they hear it?"|
| **Architect** | Structure & how it's built.            | "What does this actually look like built?"|

The **Inquisitor** is not a voting seat — it's the mechanism that keeps the room
honest. Every scene, the Inquisitor forces the strongest *costed case against*
the leading proposal onto the record, and the chair (the General, by default)
must explicitly overrule or accept it before the scene can close. A debate with
no dissent is treated as a failed scene, not a clean one. See
[`skills/debate-framework.md`](skills/debate-framework.md).

---

## How a scene runs

```
topic in ──▶ governor preflight ──▶ draw dispositions ──▶ generate scene
                    │                                            │
              (may refuse)                                       ▼
                                              turns → Inquisitor challenge → chair rules
                                                            │
                                                            ▼
                                          outcome + optional proposal ──▶ decision ledger
```

1. **Governor preflight.** Before spending anything, the governor checks the caps
   (see below). If a gate fails, the scene is refused and logged — no tokens
   spent.
2. **Draw dispositions.** Each persona is assigned one stance for this scene,
   weighted by affinity and varied vs. the last scene, with at least one
   dissenting stance guaranteed so the room always has tension.
3. **Generate the scene.** The whole room is produced in a **single model call**
   (one model role-playing every seat). This is deliberate: it collapses cost
   dramatically vs. one-call-per-persona and yields a more coherent conversation.
4. **Inquisitor + chair.** The dissent is forced onto the record; the chair rules.
5. **Outcome.** One of `decision | parked | consensus | exhausted`. If there's a
   concrete recommendation, it's attached as a `proposal` with an **impact score**
   and a tier (auto-ship / needs-approval / rejected).
6. **Ledger.** The scene and its outcome are appended to the decision ledger.
   "No decision warranted" is a **respected** outcome — the room does not
   manufacture a proposal just to have something to show.

### Voting & the ledger

The room doesn't tally raw votes; the chair synthesizes the debate into one
outcome, on the record, after the Inquisitor's dissent is answered. Every scene
becomes one ledger entry (`decisions.json` by default). The ledger is the room's
permanent memory and the single source of truth: future scenes read it and are
forbidden from re-proposing anything already shipped, killed, or in flight.

---

## Running on a schedule + the morning briefing

The Boardroom can run **on demand** (you hand it a topic) or **on a schedule**
(it convenes itself and looks for improvements). A scheduled cadence — e.g. a
few scenes overnight plus a handful through the day — lets it surface proposals
while you're away.

Scheduled scenes feed naturally into a **morning briefing**: the overnight
ledger entries become "here's what the board decided / wants your approval on"
without you attending a single meeting. Wire it via your scheduler of choice
(cron, Task Scheduler, or your harness's routine system) — see
[`skills/debate-framework.md`](skills/debate-framework.md#scheduling).

---

## Cost & the Governor

**This module is token-heavy by design** — every scene is a full model call. The
**Governor** is what keeps that spend bounded and useful. It enforces two things
([`governor.md`](governor.md) has the full spec):

- **A spend cap** — token ceilings per rolling window and per day act as hard
  runaway-loop backstops; the room simply stops convening when a ceiling is hit.
  It also caps how many live conversations are retained (oldest archived).
- **A work-mix quota** — of everything the room takes on, a floor goes to
  low-risk auto-ship improvements and a floor to approval-required changes, with
  the remainder as pure monitoring/QC. This stops the room from drowning you in
  approvals *or* from doing nothing but watch.

**Route low-stakes turns to a local model if one is present.** The Governor
supports tiering: decision-stakes scenes use your strongest model, while routine
low-stakes heartbeats can be routed to a smaller/local model to reclaim
headroom. If no local model is configured, everything uses your default model.

Because usage is continuous, a **flat-rate plan (e.g. Claude Max) is
recommended** over metered per-token API billing.

**Kill switch:** create the disable flag at any time to pause instantly (see
`install` output), or run `leroy disable boardroom`.

---

## Install / enable

```sh
# Unix / macOS
./install.sh

# Windows PowerShell
./install.ps1
```

Both scripts only **register** the module and record it as **disabled**. Nothing
runs until you explicitly enable it:

```sh
leroy enable boardroom      # start convening
leroy disable boardroom     # pause (also: create the kill-switch flag)
```

Enablement state and config live under `~/.claude/` (path is printed by the
installer). No private data, no network calls at install time.

---

## Files

| File                          | What it is                                            |
|-------------------------------|-------------------------------------------------------|
| `README.md`                   | This overview.                                        |
| `skills/personas.md`          | The 5 personas + Inquisitor + disposition library.    |
| `skills/debate-framework.md`  | How a scene is assembled, run, and logged.            |
| `governor.md`                 | Token cap + work-mix quota spec (generalized).        |
| `config/personas.json`        | Machine-readable panel + dispositions.                |
| `config/governor.json`        | Default governor policy (conservative, editable).     |
| `install.sh` / `install.ps1`  | Opt-in registration stubs (default OFF).              |
