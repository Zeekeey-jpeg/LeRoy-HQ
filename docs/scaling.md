# Scaling Protocol

How LeRoy sizes a crew to a task, chooses a communication shape, and keeps parallelism from
running away. This is the mechanism behind "deploy to capacity, not minimum" — the COO reads
the *shape* of the work and scales the team to match.

> **Plain-English version:** think of it like a shop foreman. A one-off fix gets one person.
> A big rebuild gets a whole crew with leads. The foreman never sends one person to do a
> twelve-person job, and never sends twelve to change a lightbulb.

---

## 1. Tiers — how many agents

Work is broken into **task packets** — independent, parallelizable units. Count the packets,
pick the tier, then staff the tier to **capacity** (not the minimum that would technically work).

| Tier | Task packets | Max agents | Typical distribution |
|------|--------------|-----------|----------------------|
| **T1** | 1–3 | 5 | 1 arch · 2 build · 1 design · 1 background |
| **T2** | 4–9 | 12 | 2 arch · 6 build · 2 design · 2 background |
| **T3** | 10–15 | 18 | 3 arch · 9 build · 3 design · 3 background |
| **T4** | 16+ | 20+ | 4 arch · 12 build · 3 design · 3 background |

**The one hard rule:** no single team handles more than **3 task packets**. If a lane would
exceed that, split it and redistribute. A "build" lane with 17 packets is an anti-pattern —
break it across arch/build/design so no lane is overloaded.

### What counts as a packet?
- **1 packet** — a single-file change, one bug fix, one small feature.
- **3 packets** — frontend + backend + tests; or endpoint + component + docs.
- **6 packets** — a multi-file refactor, a feature spanning several components.
- **12 packets** — a large feature, an architecture redesign, a multi-system integration.
- **16+ packets** — a full overhaul, several interlocking features, a complex migration.

### Staffing adjustments
- **No UI work?** Redistribute the design allocation into build.
- **Large data (10k+ records)?** Swap build agents for the batch/ETL specialist.
- **Commit involved?** Add the pre-commit quality gate agent (mandatory — never skipped).
- **Trivial request?** Still spawn at least one lightweight handler — coverage is 100%, never zero.

---

## 2. Topology — how agents talk

Every task has a natural communication shape. LeRoy selects one per task (keyword scan,
first-match-wins; default is `hybrid`). Trivial requests skip topology entirely.

| Topology | Shape | When |
|----------|-------|------|
| `hierarchy` | Router → specialists → gate, strict chain | Commits, releases, contracts, signed outbound, deploys |
| `mesh` | Agents talk laterally, all report up to the router | Debate, research, recon, parallel hunts, brainstorming |
| `hybrid` | Router conducts, but agents may talk laterally for sub-decisions | Most general work (the default) |

Rules live in a hot-reloadable config (`session/topology-rules.json`) — edit the file and the
next turn picks it up, no restart. Topology can also be **declared** to override the auto-pick
when the keywords don't match the real task shape (e.g. "commit this research summary" keys on
*commit* → `hierarchy`, but it's a doc, so override to `mesh`).

> Topology is **descriptive metadata** today — it labels the shape and logs it. Prescriptive
> routing (agents actually behaving differently per topology) is a later, telemetry-gated phase.

---

## 3. A2A mesh — peer-to-peer coordination

For big jobs, agents don't have to funnel everything through the router. The **agent-to-agent
mesh** lets peers coordinate directly with three verbs:

- **DELEGATE** — hand a sub-task to a better-suited peer.
- **SUBSCRIBE / NOTIFY** — watch for an event, get pinged when it happens.
- **CACHE** — share a computed result so peers don't redo it.

This is where the **2–10× speedup on parallel work** comes from. It's kept safe by hard limits:

| Guardrail | Limit |
|-----------|-------|
| DELEGATE chain depth | **Max 3 hops** — a 4th hop trips the circuit breaker |
| Circuit breaker (deadlocks) | Fires at **>3 hops or >5 deadlocks** → escalates to the tech lead |
| Per-hop latency budget | **<100ms** message overhead per hop |
| Conflict resolution | version-vector reconciliation on shared state |

When a chain hits hop 3 and still wants to delegate, the agent absorbs the work itself or
surfaces it up instead of chaining further. No infinite delegation loops.

---

## 4. Forks — cheap parallelism

A **fork** clones the current agent's full context so several copies run in parallel, sharing
the session's cache prefix. Because forks reuse the cache, each one after the first is far
cheaper than spawning a fresh named subagent — spinning up three forks costs roughly what one
regular subagent costs.

| Guardrail | Limit |
|-----------|-------|
| Forks per task | **Max 5** — a hard cap against runaway parallelism |

If the cap is hit, work still completes — it just proceeds without the extra parallel cache
savings.

---

## 5. CTO flight plan — composing modalities

For a substantial prompt, the CTO acts as an **orchestration architect**: it scans which
execution modalities the prompt calls for and composes them into a single plan. This is a
**multi-select, not winner-take-all** — every modality whose signal fired is included, then
composed:

- `∥` — **concurrent**: independent lanes run at once (e.g. `A2A mesh ∥ workflow pipeline`).
- `→` — **sequential gate**: one lane must finish or be approved before the next
  (e.g. `Plan → builder`, or `… → Guardian` as the final gate).

A real plan mixes both. Example:

```
Plan → (A2A mesh [3] ∥ Workflow 4-stage) → Guardian
```

Read: plan first, then run a 3-agent mesh *and* a 4-stage workflow in parallel, then send it
all through the guardian gate before anything ships. Planning gates first; isolation/verify
gates last. The composed stack is what gets handed to the router for crew assignment.

---

## Putting it together

A typical substantial request flows:

1. **Count packets** → pick the **tier** → staff to capacity (no lane >3 packets).
2. **Select topology** for the communication shape (or declare an override).
3. Let peers use the **A2A mesh** (≤3 hops) and **forks** (≤5) to parallelize.
4. The **CTO flight plan** composes the modalities with `∥` / `→` and hands the crew to the router.

Every one of these limits exists to make big jobs fast *and* bounded — parallel where it pays,
capped where it could spiral.
