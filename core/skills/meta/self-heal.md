---
name: self-heal
description: Autonomous audit → fix → verify → rollback loop that keeps LeRoy healthy without you babysitting it.
tags: [meta, self-improvement, reliability]
---

# Self-Healing

LeRoy audits itself on a schedule (and on error spikes) and can **repair** problems on its own —
closing the loop from "detect" to "fixed and verified," not just "reported."

## The loop

```
audit → classify → fix → VERIFY → auto-rollback if worse → notify
```

## Tiers (what it's allowed to do unattended)

| Tier | Examples | Autonomy |
|---|---|---|
| GREEN | restart a dead sidecar, rebuild the skill index, fix a missing dependency | auto-apply |
| YELLOW | bulk edits across files, config changes | build it, then ask you to approve |
| RED | anything destructive or irreversible | never automatic — always your call |

## Guardrails (each born from a real incident)

- **Protected-path wall** — the fixer is physically blocked from editing the files that *are* the
  workflow (the gate, hooks, `CLAUDE.md`, and the fixer itself).
- **Git checkpoint per fix** — every change is committed first, so any fix is one `reset` away from
  undone; a whole-run anchor tag enables a full rollback.
- **Syntax gate** — every changed file is compiled/validated before the run continues.
- **Smoke-regression rollback** — it diffs the pass/fail map before vs. after and rolls back if it
  introduced a *new* failure.
- **Blast-radius cap** — at most a few fixes per run; overflow escalates to approval instead of
  charging ahead.
- **Loud-notify receipt** — a heartbeat + failure log so a swallowed notification can never hide a
  silent failure.

## How it runs

A daily health audit scores the core subsystems (agents, memory/RAG, connectors, builds). GREEN
findings are auto-fixed and verified; YELLOW/RED are surfaced for you. It's the difference between a
system that *reports* it's broken and one that *quietly keeps itself working.*

> Related: the deterministic pre-flight gate, the `janitor` agent (scheduled cleanup), and the
> automation registry (LeRoy won't create a background job without an approved entry).
