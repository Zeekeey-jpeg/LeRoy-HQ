---
name: optimization-solver
description: |
  Quantum-INSPIRED classical optimization toolkit (QUBO + simulated annealing, with
  optional OR-Tools / dwave-neal upgrade). Use when a task is secretly a combinatorial
  optimization problem - scheduling, assignment, routing, allocation, shift/timetable
  planning, bin-packing, or selection-under-a-budget. Runs on a normal CPU; no quantum
  hardware. Decides between annealing, OR-Tools CP-SAT, and plain logic. Tool:
  scripts/optimize.py. Owned by the CTO.
---

# Optimization Solver (QUBO / Simulated Annealing)

Quantum-inspired, fully classical. The "quantum" is only the inspiration: **annealing**
borrows from metallurgy/physics, and **QUBO** is mathematically the Ising model. It all
runs on a normal CPU. There is **no exponential speedup** here - parallelism/optimization
is classical. The value is solving messy combinatorial problems *well* and *fast*.

## Step 1 - Is this even an optimization problem? (the seating-chart test)

A prompt is secretly a QUBO when it has all three:
1. **Discrete choices** - things get assigned to buckets (lead -> time slot, tech -> job,
   item -> box, guest -> table).
2. **Pairwise interactions** - the quality of one choice depends on others (two leads can't
   share a slot; friends should share a table).
3. **A "best" to find** - you want to minimize cost / maximize value subject to rules.

If yes, it's "a wedding seating chart wearing a different outfit." Scheduling, routing,
assignment, allocation, timetabling, packing all qualify. If it's a one-file edit, a lookup,
or has no combinatorial structure - it is NOT this; do not reach for the solver.

## Step 2 - Plain English: QUBO + annealing

**QUBO** = Quadratic Unconstrained Binary Optimization.
- **Binary** - every decision is a yes/no switch (1/0): "lead #47 in the 9:03 slot?"
- **Quadratic** - the score depends on how switches interact *in pairs*.
- **Unconstrained** - rules become **penalties** ("if they share a slot, add a huge cost"),
  not hard prohibitions. The optimizer avoids violations because they're expensive.
- **Optimization** - find the switch combo with the lowest total cost.

**Annealing** solves it. Like cooling metal slowly: start with a rough answer, make random
tweaks, sometimes accept a *worse* one (often when "hot," rarely when "cool") to escape dead
ends a greedy approach gets stuck in, then cool and lock in.

## Step 3 - Technical layer

Minimize `x^T Q x` over `x in {0,1}^n`. `Q` diagonal = per-switch cost; off-diagonal =
pairwise cost. Constraints become penalty terms, e.g. "each item in exactly one slot" ->
`A*(sum_s x[i,s] - 1)^2`, which expands to linear `-A` per `x[i,s]` and quadratic `+2A` per
same-item pair. Equivalent to the Ising model.

## Step 4 - Pick the right hammer (decision tree)

| Situation | Use | Why |
|-----------|-----|-----|
| Big, messy, **soft/competing** goals; "great fast" beats "perfect" | **Simulated annealing** (this tool, default) | Heuristic, scales, no deps |
| Tight, **hard** constraints; need provable optimality / feasibility | **OR-Tools CP-SAT** (auto-used if installed) | Exact, handles "must never" rules cleanly |
| Small (<~10 items) or no real pairwise structure | **Plain logic / sort** | Don't over-engineer |
| Pure 1:1 matching (N items <-> N slots) | annealing in **permutation mode** | Avoids O(n^2) QUBO blowup |

Hybrid posture: the tool is zero-dependency by default and **auto-upgrades** if `ortools`
or `neal`/`dimod` are present. Nothing is forced on a machine (matters for client portability).

## Step 5 - Use the tool: `scripts/optimize.py`

```
python scripts/optimize.py --demo                      # wedding-seating self-test
python scripts/optimize.py --solve spec.json           # your QUBO or assignment spec
python scripts/optimize.py --benchmark overnight-hunt  # annealing vs greedy, 200 leads
```

**QUBO spec** (`{"type":"qubo","linear":{...},"quadratic":{"x0,x1":2.0}}`) minimizes
`sum linear[i]*x_i + sum quadratic[i,j]*x_i*x_j`.

**Assignment spec** (`{"type":"assignment","items":[...],"slots":[...],"value":{"a,s0":5.0},
"forbidden":["b,s1"]}`) maximizes total value over a 1:1 item->slot matching; `forbidden`
encodes hard exclusions.

Output reports the **solver used**, the assignment, the score/energy, and constraint
violations.

## Worked example - the Overnight Hunt (the proving ground)

200 leads, 200 one-minute slots. Each lead has a **priority** (1-3) and a **send-window**
(latest acceptable slot). Formulate as a 1:1 assignment:
- **value(lead, slot)** = `priority * (1 + earliness)` if `slot <= window_end`, else a heavy
  penalty (`-1000`). Earliness = `(N - slot)/N` so hot leads land early.
- 1:1 matching (each lead one slot, each slot one lead) is enforced by the permutation encoding.

`--benchmark overnight-hunt` builds a synthetic instance and runs **annealing vs the current
greedy 1/min baseline**. Typical result: window violations drop sharply (e.g. 71 -> 11) and
score improves ~85%, in ~100 ms. The live protocol is NOT modified - this is a proof. If it
wins, integration is a separate, approved step.

## Honesty rules (enforce)

- Never claim exponential or quantum speedup. It's classical and linear.
- Prefer OR-Tools for hard-constrained feasibility problems; prefer plain logic for tiny ones.
- Annealing gives *very good*, not *provably optimal*. Report residual violations honestly.

## Related

- Tool: `scripts/optimize.py`
- Radar: `memory/Decisions/Technology-Radar.md` (QUBO/annealing = Adopt)
- Owner: `agents/cto.md` (CTO surfaces this when the `optimization` signal fires)
- Matrix: `skills/meta/execution-strategy-matrix.md`
