---
user-invocable: false
---

# Fork Dispatch Pattern

**Loaded by:** Conductor when `SPAWN_FORK_WORKERS` appears in `enforcement.todo`
**Version:** v1.0 — Auto-dispatch fork fan-out for mesh/hybrid topology

---

## What Fork Is

A fork is a subagent that **inherits the full parent conversation** — history, system prompt, tools, model — byte for byte. It runs in background automatically. Only its final result returns to the parent; its tool calls never pollute the main context.

**Cost advantage:** Each fork after the first costs ~5K tokens (cache hit) vs. ~48K for a fresh named subagent. Spawning 3 forks costs roughly the same as spawning 1 regular subagent.

**Activation:** `CLAUDE_CODE_FORK_SUBAGENT=1` in settings.json (already set). Triggered automatically when `Agent` tool call **omits `subagent_type`**.

---

## When to Fan Out (Gate-Driven)

The gate-enforcer injects `SPAWN_FORK_WORKERS|packet_count={N}|topology={T}` into `enforcement.todo` when:
- Topology = `mesh` or `hybrid`
- Estimated independent packets ≥ 2
- Task is NOT a hierarchy-blocked operation (commit, deploy, send email, contract, sign)

You do NOT decide this — the gate already decided. When you see `SPAWN_FORK_WORKERS` in enforcement.todo, execute this pattern immediately.

---

## Fork Fan-Out Pattern

### Step 1 — Parse the directive
```
SPAWN_FORK_WORKERS|packet_count=3|topology=hybrid
```
Read `packet_count` — that's how many parallel workers to spin up.

### Step 2 — Decompose into independent packets
Break the task into N parallel, non-overlapping work units. Each packet must be:
- **Independent**: no result depends on another packet's output
- **Complete**: self-contained enough that the fork can finish without waiting
- **Bounded**: clear scope, clear deliverable

If packets have hard dependencies, chain them in waves (wave 1 forks complete → wave 2 forks start).

### Step 3 — Spawn forks (subagent_type OMITTED)
```python
# Fork fires when subagent_type is omitted
Agent(
    description="Research packet 1: [specific scope]",
    prompt="[self-contained instructions for this packet — fork inherits full context so no re-briefing needed]",
    run_in_background=True
    # subagent_type intentionally omitted → fork mode
)
```

Spawn ALL independent packets in a **single message** (multiple tool calls) so they run truly in parallel.

### Step 4 — Wait and collect
After all forks complete, collect their results. Do NOT synthesize until all N results are in hand.

### Step 5 — Synthesize
Compose all fork results into the final deliverable. This is the conductor's synthesis step — forks provide raw results, conductor integrates.

### Step 6 — QC Gate (unchanged)
QC Gate runs AFTER synthesis, as normal. Guardian (if needed) spawns WITH explicit `subagent_type="guardian"` — never as a fork.

---

## Hard Rules (Non-Negotiable)

| Rule | Detail |
|------|--------|
| **Max 5 forks per task** | Hard cap — prevents runaway parallelism |
| **Hierarchy = NO forks** | Commits, deploys, email sends, contracts stay sequential |
| **Guardian is never a fork** | Always explicit `subagent_type="guardian"` — runs after merge |
| **Named specialists stay named** | builder, designer, forge, professor — keep explicit type (clean context is correct for them) |
| **No nested forks** | Claude Code natively blocks this (two-layer guard) |

---

## Nesting & Compaction Recovery

**Symptom:** Agent call returns `"Fork is not available inside a forked worker."`

**Why this happens:** After context compaction + resume, if compaction occurred while executing inside a fork worker, the resumed session inherits fork-worker status. Attempting to spawn forks from within that context triggers the nesting block.

**Recovery protocol (immediate fallback):**
1. Detect the error — do NOT retry the same call
2. Fall back to sequential dispatch with explicit `subagent_type="general-purpose"` (or appropriate specialist)
3. Run workers sequentially rather than in parallel for this session
4. Note in the gate manifest: `Fork: DEGRADED (compaction recovery — sequential fallback)`
5. Proceed normally — the work still gets done, just without parallel cache savings

**Example fallback:**
```python
# Primary attempt (fork mode):
Agent(description="...", prompt="...", run_in_background=True)
# ^ Returns "Fork is not available inside a forked worker" → fall back:

Agent(description="...", prompt="...", run_in_background=True,
      subagent_type="general-purpose")
# ^ Explicit subagent_type = named agent, no fork constraint
```

**This is expected behavior** after long compaction-heavy sessions. No fix required — just execute the fallback and move on.

---

## Example: 3-Packet Research Task

the user says: "Research our your CRM pipeline health, check our your CRM ticket backlog, and summarize our open opportunities."

Gate injects: `SPAWN_FORK_WORKERS|packet_count=3|topology=hybrid`

Conductor spawns (in one message, all `run_in_background=True`, `subagent_type` omitted):
```
Fork 1: your CRM pipeline health — pull stage distribution, stale deals, close rate
Fork 2: your CRM ticket backlog — open tickets by priority, overdue SLAs
Fork 3: Open opportunities — value by stage, top 5 by amount
```

All three run simultaneously, sharing the session's cache prefix. Results return. Conductor synthesizes a combined ops summary.

---

## Manifest Display

When fork dispatch is active, display in the gate manifest:
```
Topology: hybrid (auto, rule="default") | Fork: ACTIVE (3 workers)
Forks: 3 parallel | cache-shared | ~130K tokens saved
```

When blocked by hierarchy:
```
Topology: hierarchy (auto, rule="commit") | Fork: BLOCKED
```

When eligible but not triggered (1 packet):
```
Topology: hybrid (auto, rule="default") | Fork: STANDBY (single packet)
```
