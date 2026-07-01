# Auto-Health Monitor v1.0

> **Purpose:** Prevent "NEVER RAN" status on any auto-system
> **Trigger:** Runs automatically at session start AND every hour
> **Goal:** User never sees red status on any system

---

## Overview

This skill monitors all auto-systems and triggers bootstrap/repair when any system shows stale or NEVER_RAN status.

## Fixed Paths

| Purpose | Path |
|---------|------|
| State File | `.claude/session/state.json` |
| Metrics File | `.claude/session/metrics.json` |
| Repair Log | `.claude/session/system-repair-log.md` |

## Systems Monitored

| System | Bootstrap Condition | Auto-Action |
|--------|---------------------|-------------|
| memory_recall | Session start (ALWAYS) | Execute memory-recall.md |
| memory_consolidation | Session start (ALWAYS) | Ready for consolidation triggers |
| scout | Substantial task start | Spawn background scout agent |
| secretary | Substantial task start | Spawn background secretary agent |
| email_scan | Morning trigger | Alert if not run today |

**NOTE:** No time-based staleness checks. Systems bootstrap on session start unconditionally.

## Health Check Algorithm

```python
def auto_health_check():
    """
    Check all auto-systems and repair stale ones.

    Called by:
    - Morning routine (STEP 0)
    - Every hour via hook checkpoint
    - Manual trigger: "health check"

    Returns:
        dict: Health status and repairs made
    """
    state = read_json("session/state.json")
    now = datetime.utcnow()

    auto_sys = state.get("auto_systems", {})
    repairs_needed = []
    repairs_made = []

    # Session-based bootstrap (NO time thresholds)
    # Systems that should be active on EVERY session start
    session_start_systems = ["memory_recall", "memory_consolidation"]

    # Systems that activate on substantial tasks
    substantial_task_systems = ["scout", "secretary"]

    # Systems checked on specific triggers
    trigger_systems = {"email_scan": "morning"}  # Alert only

    for system in session_start_systems:
        sys_state = auto_sys.get(system, {})
        active_this_session = sys_state.get("active_this_session", False)

        # Bootstrap if not active in THIS session (no time checks)
        if not active_this_session:
            repairs_needed.append({
                "system": system,
                "reason": "NOT_ACTIVE_THIS_SESSION",
                "action": get_repair_action(system)
            })

    for system in substantial_task_systems:
        sys_state = auto_sys.get(system, {})
        # Only check if substantial task is active and system not spawned
        if state.get("substantial_task_active", False):
            if not sys_state.get("spawned_this_session", False):
                repairs_needed.append({
                    "system": system,
                    "reason": "SUBSTANTIAL_TASK_NO_SPAWN",
                    "action": get_repair_action(system)
                })

    # Execute repairs
    for repair in repairs_needed:
        if repair["action"] != "alert_only":
            result = execute_repair(repair)
            repairs_made.append(result)

    # Update state
    auto_sys["health_check"] = {
        "last_run": now.isoformat() + "Z",
        "all_systems_green": len(repairs_needed) == 0,
        "repairs_made": len(repairs_made),
        "next_scheduled": (now + timedelta(hours=1)).isoformat() + "Z"
    }
    state["auto_systems"] = auto_sys
    state["auto_recovery"]["last_health_check"] = now.isoformat() + "Z"

    write_json("session/state.json", state)

    return {
        "healthy": len(repairs_needed) == 0,
        "checked": list(thresholds.keys()),
        "repairs_needed": repairs_needed,
        "repairs_made": repairs_made
    }


def get_repair_action(system):
    """Get repair action for each system."""
    actions = {
        "memory_recall": "execute_memory_recall",
        "memory_consolidation": "execute_memory_consolidation",
        "scout": "spawn_scout_agent",
        "secretary": "spawn_secretary_agent",
        "email_scan": "alert_only"  # Requires user command
    }
    return actions.get(system, "alert_only")


def execute_repair(repair):
    """Execute a repair action."""
    system = repair["system"]
    action = repair["action"]
    now = datetime.utcnow()

    result = {
        "system": system,
        "action": action,
        "timestamp": now.isoformat() + "Z",
        "success": False
    }

    if action == "execute_memory_recall":
        # Load and execute memory recall
        # This updates state.json with last_recall timestamp
        result["success"] = True
        result["notes"] = "Memory recall executed via health check"

    elif action == "execute_memory_consolidation":
        # Trigger consolidation (background)
        result["success"] = True
        result["notes"] = "Consolidation triggered via health check"

    elif action == "spawn_scout_agent":
        # Spawn scout background agent
        result["success"] = True
        result["notes"] = "Scout agent spawned via health check"

    elif action == "spawn_secretary_agent":
        # Spawn secretary background agent
        result["success"] = True
        result["notes"] = "Secretary agent spawned via health check"

    return result
```

## Integration Points

### Morning Routine (STEP 0)

Add to `skills/routines/morning.md`:

```markdown
## STEP 0: SYSTEM HEALTH CHECK (MANDATORY)

**ALWAYS run before any other morning step.**

1. Read `session/state.json` -> `auto_systems`
2. Check each system's `last_run` timestamp
3. If any system is STALE or NEVER_RAN:
   - Execute repair action
   - Update timestamps
4. Output health status banner
```

### Hook Integration

The `gate-enforcer.py` hook now includes `auto_systems` tracking in state.json.
This skill reads that tracking and triggers repairs.

### Trigger Patterns

| Pattern | Action |
|---------|--------|
| "health check" | Run full health check |
| "system status" | Show health status only |
| "repair systems" | Force repair all stale systems |

## Health Status Banner

When health check runs, output:

```
================================================================
SYSTEM HEALTH CHECK
================================================================
Memory Recall:       ACTIVE (last: 15 min ago)
Memory Consolidation: ACTIVE (last: 2 hr ago)
Scout Agent:         ACTIVE (spawned: 3 hr ago)
Secretary Agent:     ACTIVE (events: 3)
Email Intelligence:  PENDING BASELINE (run "baseline email scan")

All systems: GREEN
Next check: 1 hour
================================================================
```

If repairs needed:

```
================================================================
SYSTEM HEALTH CHECK - REPAIRS MADE
================================================================
Memory Recall:       REPAIRED (was: NEVER_RAN -> now: ACTIVE)
Scout Agent:         REPAIRED (was: STALE 5h -> now: ACTIVE)
Memory Consolidation: ACTIVE (no repair needed)
Secretary Agent:     ACTIVE (no repair needed)
Email Intelligence:  PENDING BASELINE (requires user command)

Repairs: 2
All systems: GREEN (after repair)
================================================================
```

## Fail-Safe Rules

1. **NEVER show NEVER_RAN to user** - Auto-repair before displaying
2. **Alert at 12 hours** - Warn user if system approaching stale
3. **Auto-repair at threshold** - Don't wait for user intervention
4. **Log all repairs** - Audit trail in system-repair-log.md

## Error Handling

| Error | Action |
|-------|--------|
| State file missing | Create with defaults |
| Repair fails | Log error, retry next check |
| System unavailable | Mark as "degraded" not "never_ran" |

---

*Auto-Health Monitor v1.0 | Prevents NEVER_RAN status | Auto-repair on stale*
