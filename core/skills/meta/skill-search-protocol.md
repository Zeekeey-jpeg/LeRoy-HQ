---
name: skill-search-protocol
description: "COO dynamic routing protocol. Invoked when a prompt doesn't match the hot list in CLAUDE.md. Spawns skill-matcher, interprets confidence bands, dispatches by type (skill/agent/agent+skill), and handles fallback."
---

# Skill Search Protocol

**When to invoke:** Any request that does NOT match the CLAUDE.md hot list.

---

## Step 1: Check Index Freshness

Before spawning the matcher, verify `session/skill-index.json` exists and is not stale:

```python
from pathlib import Path
import json
from datetime import datetime, timezone, timedelta

index_path = Path.home() / ".claude" / "session" / "skill-index.json"
if not index_path.exists():
    # Rebuild now
    run: python ~/.claude\scripts\build-skill-index.py
elif (datetime.now(timezone.utc) - datetime.fromisoformat(
        json.loads(index_path.read_text())["generated"]
      ).replace(tzinfo=timezone.utc)) > timedelta(hours=24):
    # Stale — rebuild silently
    run: python ~/.claude\scripts\build-skill-index.py
```

If rebuild fails, skip to Fallback (Step 4).

---

## Step 2: Spawn skill-matcher

```
Task tool:
  subagent_type: skill-matcher
  run_in_background: false
  prompt: "{verbatim user prompt text}"
```

Wait for result (target: <2s). Parse the returned JSON.

---

## Step 3: Dispatch by Confidence + Type

| Confidence | Type | COO Action |
|-----------|------|-----------|
| ≥ 0.50 | `skill` | Read the `file` path, follow instructions in current context |
| ≥ 0.50 | `agent` | Spawn agent named in `agent` field via Task tool |
| ≥ 0.50 | `agent+skill` | Spawn agent named in `agent` field AND pass `file` path as context |
| < 0.50 | any | → Fallback (Step 4) |
| `no_index` | — | → Rebuild index, then retry once |
| `no_match` | — | → Fallback (Step 4) |

### Dispatching a skill (type = "skill")
```
Read: {file}
Follow the skill's instructions in the current conversation context.
```

### Dispatching an agent (type = "agent")
```
Task tool:
  subagent_type: {agent}
  prompt: "{original user prompt}"
```

### Dispatching agent+skill (type = "agent+skill")
```
Task tool:
  subagent_type: {agent}
  prompt: |
    Skill protocol: {file}
    User request: {original user prompt}
    Load and follow the skill file before executing.
```

---

## Step 4: Fallback Chain

If confidence < 0.50 or skill-matcher is unavailable:

1. **Grep `skills/meta/index.md`** — keyword search against the routing table
2. **Check `agents/index.md`** — scan routing table for keyword match
3. **Present folder menu** — list top-level skill folders + agents/, ask user to select
4. **Never execute without routing** — the Never Nothing Rule always applies

---

## Governance Notes

- This protocol is invoked by `agents/conductor.md` dynamic routing section
- Index is rebuilt by `scripts/build-skill-index.py` — also callable from here
- Usage of each matched skill is automatically logged by the skill-usage-tracker hook
- Hot list candidates surface in `session/skill-promotion-candidates.json` via `skill-usage-tracker.py --report`
