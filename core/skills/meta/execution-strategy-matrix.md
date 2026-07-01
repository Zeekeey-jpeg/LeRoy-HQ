---
name: execution-strategy-matrix
description: >
  The CTO's decision matrix for auto-selecting execution modalities (Plan Mode,
  Workflow, A2A mesh, Debate, parallel agents, worktree, Goal engine) on every
  substantial prompt. Read by the CTO when consuming a PLAN_EXECUTION_STRATEGY
  enforcement action; emits the FLIGHT PLAN box. Paired with
  hooks/orchestration-planner.py and the PLAN_EXECUTION_STRATEGY handler in
  enforcement-queue-handler.md.
disable-model-invocation: true
---

# Execution Strategy Matrix — CTO Orchestration Architect

## Purpose

Eliminate manual modality calls. the user's go-tos — "A2A mesh," "plan mode," "workflow,"
"debate" — are selected **automatically** by the CTO (acting as Orchestration Architect)
on every substantial prompt. The CTO reads this matrix + the hook's pre-computed signals,
picks the modality stack, and emits a FLIGHT PLAN box. Execution then auto-proceeds.

**Division of authority:**
- **CTO picks the HOW** — which execution modalities (this matrix).
- **COO picks the WHO** — crew assignment / agent distribution (`agents/conductor.md`).

The CTO hands the chosen stack to the COO; the COO assigns the agents.

---

## Where this runs in the loop

```
prompt → orchestration-planner.py (UserPromptSubmit)
       → substantial? → appends PLAN_EXECUTION_STRATEGY to enforcement.todo (+ signals)
       → Position #0 reads enforcement.todo
       → spawns CTO (this matrix) → returns Flight Plan
       → FLIGHT PLAN box rendered in gate → auto-proceed
```

The hook pre-computes cheap regex signals so the CTO makes **one fast structured
decision**, not a from-scratch analysis. "Always-spawn" stays lean.

---

## The modality arsenal

| # | Modality | Tool / Skill | Primary use |
|---|----------|--------------|-------------|
| 1 | **Single-agent direct** | (no orchestration) | one file, unambiguous ask |
| 2 | **Plan Mode** | `EnterPlanMode` → `ExitPlanMode` | ambiguous reqs, multiple valid approaches, multi-file feature, architecture |
| 3 | **Workflow** | `Workflow` tool | fan-out / pipeline over a known work-list: audit, "review all," sweep, migrate |
| 4 | **A2A mesh** | delegation cards (`mesh-wrapper`, agent `[A2A:DELEGATE]`) | cross-product, "delegate," specialist routing, multi-department |
| 5 | **Debate-by-the user** | `skills/meta/debate-by-council.md` | consequential option fork: "which / should we / compare," irreversible/architectural |
| 6 | **Parallel agents** | `Agent` ×N in one message | independent streams, fan-out with no file conflict |
| 7 | **Worktree isolation** | `EnterWorktree` / `isolation: worktree` | parallel **file-mutating** agents (conflict risk) |
| 8 | **Goal engine** | `/goal` (`skills/meta/goal-engine.md`) | multi-session, long-horizon, "track over weeks," campaign |

Modalities **compose** — e.g. `Plan Mode → A2A mesh [3] → Guardian`, or `Workflow (verify lane)`.

---

## Core rule: modalities COMBINE — this is not a single-pick

**The CTO selects EVERY modality whose signals genuinely fire and runs them together.**
This is a multi-select, not a winner-take-all. A real task routinely runs, e.g.,
**A2A mesh + Debate + Workflow** at once — mesh delegates the streams, a Workflow pipeline
fans out the audit lane, and a Debate gates the one irreversible call inside it. Picking
only one would throw away coverage the user explicitly wants.

The hook already emits **multiple independent signals per prompt** (it sets `workflow`,
`debate`, `mesh`, `plan`… as separate booleans). The CTO's job is to **honor all of them**
and compose them — concurrently where independent, sequentially where one gates another —
not to collapse them to a single choice.

The only thing that bounds the combination is **scope match**: a genuinely trivial,
one-file ask runs a single modality (or none). Everything else combines as many as apply.

## Signal → modality scoring

The hook passes a `signals` dict. The CTO turns **each fired signal into an included
modality** (not a ranked shortlist). Single-agent is the floor only when nothing else fires.

| Signal token (in prompt) | Pushes toward |
|--------------------------|---------------|
| `audit`, `all`, `every`, `each`, `comprehensive`, `sweep`, `bulk`, `review all`, `migrate`, `across the board` | **Workflow** |
| `compare`, `which`, `should we`, `should I`, `vs`, `decide`, `or should`, `better option`, `trade-off`, `pros and cons` | **Debate** |
| `across products`, `delegate`, `specialist`, `hand off`, `each department`, two+ product names (your product/your BIM connector/QuickQuote/IntegratorOS) | **A2A mesh** |
| `build`, `implement`, `refactor`, `feature`, `design`, `architecture`, `from scratch`, multi-file scope | **Plan Mode** |
| `in parallel`, `at the same time`, `simultaneously`, list of independent items | **Parallel agents** |
| parallel + `edit`/`write`/`refactor` across files | **Worktree** |
| `over weeks`, `multi-session`, `ongoing`, `long-term`, `track`, `campaign`, `roadmap` | **Goal engine** |
| `optimize`, `schedule`, `assignment`, `routing`, `allocate`, `QUBO`, `annealing`, `minimize`/`maximize`, `constraint` | **optimization-solver** *(computational tool — see note)* |
| any one-file/lookup/read-only ask, < ~150 chars | **Single-agent** |

### Stakes families (reused from `debate-auto-invoke.md`)

`architectural` · `irreversible` · `financial` · `legal` · `strategic` · `production`

- **≥1 stakes family + an option fork** → add **Debate** to the stack.
- **≥2 stakes families** → escalate CTO deliberation model to **opus**; otherwise sonnet.

### Computational tools (applied *inside* a modality — NOT a 9th modality)

Some signals select a **tool**, not an orchestration topology. When the `optimization`
signal fires (scheduling / assignment / routing / allocation / QUBO / "optimize"), the CTO
does **not** add a modality — it surfaces **"apply the `optimization-solver` skill"**
(`skills/stacks/optimization-solver.md`, tool `scripts/optimize.py`) *inside* whatever stack
already runs, e.g. `Plan Mode → builder (+ optimization-solver)`. It is quantum-*inspired*,
fully classical, no speedup claims. Note it in the Flight Plan's **Why** line; it does not
change the topology.

---

## Decision procedure (CTO)

1. Read the `signals` dict and the base64 prompt from the PLAN_EXECUTION_STRATEGY action.
2. **Include every modality whose signal fired** — this is the multi-select. Do not narrow.
3. **Compose** them (see Composition below): mark which run concurrently (`∥`) and which
   gate sequentially (`→`). Planning gates first; isolation/verify gates last; Debate gates
   immediately before any irreversible step inside the run.
4. Predict whether **Debate** will auto-fire downstream (option fork + stakes) so the box
   pre-announces it — Debate itself still fires via `debate-auto-invoke.py` on
   `AskUserQuestion`; the matrix only forecasts it.
5. Estimate **scale**: rough work-packet count → Tier (1–4) per `session-gate.md`.
6. Emit the Flight Plan (below) and hand the **full combined stack** to COO for crew assignment.
7. Write `orchestration.last_flight_plan` to `state.json` (store the modality list + topology).

## Composition (how multiple modalities run together)

| Relationship | Notation | Example |
|--------------|----------|---------|
| **Concurrent** — independent, run at once | `A ∥ B` | `A2A mesh ∥ Workflow` — mesh delegates specialists while a Workflow pipeline sweeps the audit lane |
| **Sequential gate** — one must finish/approve before the next | `A → B` | `Plan Mode → builder` — approve the plan, then implement |
| **Embedded gate** — a modality wraps a single decision inside another | `A [Debate] B` | a Workflow that hits one irreversible step pauses for Debate, then continues |

A full Flight Plan mixes all three, e.g.
`Plan Mode → (A2A mesh [3] ∥ Workflow 4-stage) → Guardian`, with Debate forecast to fire
on the irreversible call.

**Scope-match rule (the only limiter):**
- Trivial / one-file → single modality (or none). Otherwise combine all that fire.
- Only drop a fired modality if it adds **pure latency with zero coverage gain** for this
  specific prompt (e.g. worktree when nothing mutates files in parallel). Log the drop.
- When scope genuinely can't carry two (rare), keep the one the user named historically
  (Plan Mode, then mesh) — but default is **run both**, not choose.

---

## Flight Plan output (the box the user sees)

```
┌─ FLIGHT PLAN (CTO · Orchestration Architect) ───────────────┐
│ Running:     {combined topology — e.g.                       │
│              Plan → (A2A mesh [3] ∥ Workflow 4-stage) → Guard}│
│ Why:         {one-line rationale naming each fired signal}   │
│ Concurrent:  {what runs in parallel, or "—"}                 │
│ Debate:      {will trigger on {step} (stakes) | not triggered}│
│ Workflow:    {N-stage pipeline | not triggered}              │
│ Scale:       Tier-{1-4} · ~{N} packets · COO assigns crew    │
│ Proceeding ▸  (say "hold" to adjust)                         │
└──────────────────────────────────────────────────────────────┘
```

The **Running** line shows the *combined* stack (`∥` = concurrent, `→` = sequential gate),
never a single modality unless the task is genuinely trivial. Render **after** the
Position #0 enforcement box, **before** ROUTES LOADED. Then proceed — do not wait for
confirmation (announce-then-go; the user's max-autonomy preference).

---

## Worked examples

| Prompt | Signals (multiple fire) | Combined Flight Plan |
|--------|---------|-------------------|
| "fix the typo in cto.md" | none (trivial) | *(filtered by hook — no box)* |
| "audit all open opportunities for missing accessories" | audit, all | **Workflow** (pipeline per opp) · Tier-2 |
| "should we drop the OBID feature?" | debate, strategic | **Debate** → single-agent exec |
| "refactor auth across your product and your BIM connector" | plan, mesh, architectural | **Plan → A2A mesh [2]** · Tier-2 |
| **"audit every client contract, flag the risky ones, and decide which to renegotiate across your org and your organization"** | workflow, debate, mesh, legal | **A2A mesh [2] ∥ Workflow (per-contract pipeline), Debate gates each renegotiate call** · Tier-3 — *four modalities at once* |
| **"build the your CRM export across both products, migrate the 40 SKUs in parallel, and ship it"** | plan, mesh, workflow, production | **Plan → (A2A mesh [2] ∥ Workflow worktree-per-batch) → Guardian**, Debate forecast on the irreversible migrate · Tier-3 |
| "research 5 competitors in parallel and summarize" | parallel | **Parallel agents [5] → synthesis** · Tier-2 |
| "track the ExampleClient deal over the next month" | goal | **Goal engine** (may spawn Workflows per cycle) |

The bolded rows are the point: **several modalities run together**, composed with `∥` and `→`.

---

## Kill switch & phases

- **Shadow (Phase 0):** hook logs the intended plan but writes **no** enforcement action
  and renders **no** box. Controlled by absence of `session/orchestration-planner.live`.
- **Live (Phase 1):** `touch session/orchestration-planner.live` → box renders, auto-proceed.
- **Disabled:** `touch session/orchestration-planner.disabled` → hook short-circuits.

---

## Related files

- Hook: `hooks/orchestration-planner.py`
- Handler: `skills/meta/enforcement-queue-handler.md` → `PLAN_EXECUTION_STRATEGY`
- CTO spec: `agents/cto.md` → "Orchestration Architect"
- Gate box: `skills/meta/session-gate.md`, `skills/meta/position-zero-enforcement.md`
- Debate forecast source: `skills/meta/debate-auto-invoke.md`
- State: `session/state.json` → `orchestration` block
