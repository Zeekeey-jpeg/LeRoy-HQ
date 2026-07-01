# Agents/ — Per-Agent Journals (Cross-Agent Memory)

> This folder is the persistent, per-agent memory layer. It ships **empty** and grows as you
> work. Nothing here is pre-seeded with anyone's history — every entry is written by your own
> system over time.

## What lives here

Each agent keeps its own journal at:

```
memory/Agents/{agent-name}/journal.md
```

A journal is **append-only**, **not session-scoped**, and tied to the agent's *identity* rather
than to any single run. When a fresh instance of an agent is spawned, the conductor reads that
agent's last few journal entries and injects them into the spawn prompt — so the new instance
inherits what prior instances of the same role already learned, instead of relearning it every
session.

The conductor also keeps one special file:

```
memory/Agents/conductor/impact-ledger.md
```

This is the COO's own full, chronological record of every cross-agent impact it has ever
processed — its org-wide "connect-the-dots" memory.

## How entries get written (the IMPACT protocol)

Agents don't write to each other's journals directly. Instead:

1. An agent notices it changed something another agent's domain depends on (a shared mapping
   file, a contract scope, an architecture decision, a retired agent, a budget change, …).
2. It fires an `[A2A:IMPACT]` signal to the conductor. It does **not** persist anything itself.
3. The **conductor is the only writer.** On receipt it:
   - appends the impact to `conductor/impact-ledger.md`, and
   - appends a dated entry to `journal.md` for each agent named as likely-affected,
   - first grepping existing journals so it can note connections to prior entries instead of
     filing in isolation.
4. If the journal for a named agent doesn't exist yet, the conductor **auto-creates it on
   demand** from the template below. This is why the folder can ship empty — journals appear the
   first time an agent is named in an impact, and accumulate from there.

A universal check at QC-gate time (`agents/conductor.md` Step 6g) runs the
**Cross-Agent Domain Ownership Map** (`agents/mesh-wrapper.md`) against every delegated agent's
output, so impacts get logged even for agents that never self-report — the map is the floor,
per-agent emission hooks are an optimization on top of it.

## Conventions

- **Append-only.** Never overwrite or delete existing entries.
- **Dated.** Every entry starts with an ISO date.
- **Valid vault path.** Journals live under the `Agents/` prefix (see the path validator in
  `skills/meta/memory-consolidation.md`).
- **One journal per agent**, named exactly for the agent (`builder/journal.md`,
  `guardian/journal.md`, …).

See `_template/journal.md` for the starting shape of a new journal.
