# The Governor — spend cap + work-mix quota

The Boardroom is **token-heavy**: every scene is a full model call. The Governor
is the module that keeps that spend bounded and the room's output useful instead
of noisy. It enforces two independent things:

1. A **spend cap** — hard ceilings so a runaway loop can't drain your quota.
2. A **work-mix quota** — a floor on auto-ship improvements and a floor on
   approval-required changes, with the remainder as monitoring/QC.

The Governor is **pure policy** — it decides *whether* a scene may run and *what
kind* of topic the next scene should be. It spends nothing itself. Defaults live
in [`config/governor.json`](config/governor.json) and are intentionally
conservative; tune them to your plan.

---

## 1. Spend cap

Every generated scene records its real token usage to a usage ledger. Before any
new scene, the Governor sums recent usage and refuses if a ceiling is hit. All
ceilings are **runaway-loop backstops** — set them high enough that your intended
cadence never trips them, low enough that a bug can't run away.

| Control                  | Meaning                                                       |
|--------------------------|--------------------------------------------------------------|
| `window_token_ceiling`   | Max tokens spent in a rolling window (e.g. 5 hours).         |
| `daily_token_ceiling`    | Max tokens spent per 24 hours.                               |
| `max_scenes_per_window`  | Max scenes per rolling window.                               |
| `max_scenes_per_day`     | Max scenes per 24 hours.                                     |
| `max_conversations`      | Max live conversations retained; oldest beyond it archived.  |

**Kill switch.** If the disable flag exists (created by `leroy disable boardroom`
or the installer's documented path), the preflight refuses unconditionally. This
is the instant "stop everything" lever and takes precedence over all other
config.

**Preflight decision (conceptual):**

```python
def preflight(gov, usage, flags):
    if not gov["enabled"] or flags.kill_switch_present:
        return REFUSE, "disabled / kill switch"
    if inside(gov["quiet_hours_local"]):
        return REFUSE, "quiet hours"
    if window_scenes() >= gov["max_scenes_per_window"]:
        return REFUSE, "window scene cap"
    if window_tokens() >= gov["window_token_ceiling"]:
        return REFUSE, "window token ceiling"
    if day_tokens() >= gov["daily_token_ceiling"]:
        return REFUSE, "daily token ceiling"
    return ALLOW, "ok"
```

**Fail closed.** If the governor state file is missing, unreadable, or malformed,
the preflight **refuses** rather than falling through to permissive defaults.
Never fail open on spend.

### Cadence modes

- **`schedule`** — the room convenes at fixed clock hours. Scheduled scenes are
  *forced*: they bypass the interactive-cadence gates (the schedule *is* the
  cadence) but still respect every token ceiling and the kill switch. Quality
  comes from a curated topic ranker (noise sources excluded), not from
  throttling.
- **`dynamic`** — the room throttles itself: shorter spacing when the human is
  idle (burn surplus), longer spacing when they're active (stay out of the way),
  plus an impact gate that silences low-priority topics.

Pick one via `mode` in the config.

---

## 2. Work-mix quota

Left alone, an autonomous room drifts to one of two failure modes: it drowns you
in approvals, or it does nothing but watch. The work-mix quota prevents both by
setting **floors** on how the room's agenda is distributed across three tiers:

| Tier         | What it is                                            | Default floor |
|--------------|-------------------------------------------------------|---------------|
| `green`      | Auto-merge / auto-ship low-risk improvements.         | ≥ 25%         |
| `approval`   | Approval-required, user-facing / consequential change.| ≥ 10%         |
| `monitoring` | Monitoring + QC only; no change.                      | remainder     |

The floors are minimums; the remainder defaults to monitoring. `green + approval`
floors must sum to ≤ 100%.

### The policy (generalized, no private numbers)

```python
from dataclasses import dataclass
from enum import Enum
import math

class Tier(str, Enum):
    GREEN = "green"          # auto-ship
    APPROVAL = "approval"    # needs a human tap
    MONITORING = "monitoring"

@dataclass(frozen=True)
class WorkMixPolicy:
    min_green: float = 0.25
    min_approval: float = 0.10
    max_conversations: int = 20

    @property
    def monitoring_target(self) -> float:
        return max(0.0, 1.0 - self.min_green - self.min_approval)

def choose_next_tier(recent_tiers, policy=WorkMixPolicy()):
    """Which tier the NEXT scene's topic should be to move toward the quota.
    Greedy: whichever floor has the largest projected shortfall wins;
    green breaks ties; otherwise monitoring."""
    n = len(recent_tiers) + 1
    counts = {t: sum(1 for x in recent_tiers if x == t) for t in Tier}
    green_short    = math.ceil(policy.min_green * n)    - counts[Tier.GREEN]
    approval_short = math.ceil(policy.min_approval * n) - counts[Tier.APPROVAL]
    if green_short > 0 and green_short >= approval_short:
        return Tier.GREEN
    if approval_short > 0:
        return Tier.APPROVAL
    return Tier.MONITORING

def cap_conversations(convos, policy=WorkMixPolicy()):
    """Keep the newest `max_conversations`; return (keep_ids, archive_ids).
    convos: list of (conversation_id, timestamp)."""
    ordered = sorted(enumerate(convos), key=lambda p: (p[1][1], p[0]), reverse=True)
    cap = policy.max_conversations
    keep    = [cid for _, (cid, _) in ordered[:cap]]
    archive = [cid for _, (cid, _) in ordered[cap:]]
    return keep, archive
```

`choose_next_tier` biases the topic ranker so the agenda trends toward the quota
over time — it never forces an unnatural topic, it just breaks ties toward the
underserved tier.

---

## 3. Model tiering (route low-stakes turns to a local model)

The Governor also decides **which model** a scene uses, to keep spend down
without hurting the calls that matter:

- **Decision-stakes scenes** — high-impact topics, forced/injected scenes, or
  anything flagged consequential — use your **strongest model**.
- **Routine low-stakes heartbeats** — the "just watching" scenes — are routed to
  a **smaller or local model if one is configured**, reclaiming quota headroom.

If no local/secondary model is configured, everything falls back to your default
model. Model choice is orthogonal to billing: a flat-rate plan (e.g. Claude Max)
is recommended because the room's usage is continuous.

```python
def resolve_scene_model(topic, cfg):
    stakes = topic.get("impact", 0) >= cfg["decision_stakes_impact"] \
             or topic.get("forced", False)
    if stakes:
        return cfg["primary_model"], "decision-stakes"
    return cfg.get("routine_model") or cfg["primary_model"], "routine"
```

---

## Auditing

Every preflight decision (allowed **and** refused) should append a structured
record to a throttle log: the decision, the reason, tokens/scenes spent in the
window and day, and remaining headroom. This makes every refusal — and every
bypass — auditable without manual math.
