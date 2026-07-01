---
name: leroy-log-schema
description: Schema reference for session/leroy.log — the unified observability stream introduced in Sprint 2 (#8)
tags: [observability, logging, schema, leroy]
trigger: "log schema" | "leroy log" | "leroy.log"
---

# leroy.log — Unified Observability Stream Schema

`session/leroy.log` is the authoritative summary log for all LeRoy agent activity. It is a rotating JSONL file written by `scripts/leroy_log.py`.

---

## Schema Fields

Every line in `leroy.log` is a JSON object with exactly these fields:

| Field | Type | Description |
|---|---|---|
| `ts` | ISO-8601 string (UTC) | Timestamp of the event, e.g. `"2026-05-03T14:22:01.123456+00:00"` |
| `level` | enum string | Severity: `debug`, `info`, `warn`, `error` |
| `trace_id` | string | Correlates all events within one gate-to-stop session. Format: `tr-YYYYMMDDHH-{6char-hex}` |
| `session_id` | string or null | Claude session identifier from `CLAUDE_SESSION_ID` env var |
| `agent` | string or null | Active agent name at write time (e.g. `"builder"`, `"conductor"`) |
| `skill` | string or null | Skill file loaded at write time (e.g. `"skills/meta/topology-selection.md"`) |
| `tool` | string or null | Tool name for `tool_called` / `tool_result` events |
| `event` | enum string | One of the 12 closed event strings (see below) |
| `ref` | string or null | Back-pointer to detail log, format `path#L<line>`, e.g. `"session/cost-log.jsonl#L1042"` |
| `payload` | object | Event-specific data. Max 2KB serialized; truncated if over limit. |

### Payload Conventions

- `tool_result` events: `{tool_input_summary, duration_ms, status}`
- `topology_selected` events: `{auto, rule, prompt_keywords}`
- `gate_emitted` events: `{trivial_or_full, topology}`
- `cost_recorded` events: `{cost_usd, tokens_in, tokens_out, ref}` — `ref` points to cost-log.jsonl
- `pii_detected` events: `{pii_type, action_taken, ref}` — `ref` points to pii-detections.jsonl
- `error_raised` events: `{error_class, message, context}`

---

## Closed Event Enum (13 strings)

Additions require an ADR (Architecture Decision Record). Schema drift is tracked via the closed enum.

| Event | When it fires |
|---|---|
| `gate_emitted` | gate-enforcer.py completes banner output for a prompt |
| `tool_called` | Any tool is about to be called (PreToolUse) |
| `tool_result` | Any tool has returned a result (PostToolUse — via leroy-logger.py tee hook) |
| `agent_spawned` | A sub-agent or Task is created |
| `agent_completed` | A sub-agent or Task returns |
| `skill_loaded` | A `.md` skill file is read by Claude |
| `memory_written` | A note is written to the memory vault |
| `memory_recalled` | Memory recall executes and returns notes |
| `pii_detected` | PII scanner triggers on email/memory write (summary; detail in pii-detections.jsonl) |
| `cost_recorded` | Cost meter records a tool-call cost (summary; detail in cost-log.jsonl) |
| `topology_selected` | Gate selects topology for the current prompt |
| `error_raised` | An error is caught and logged in a hook or script |
| `goal_event` | GOAP planner lifecycle event — goal created, advanced, blocked, etc. (Sprint 3) |

### goal_event — sub_event values

`goal_event` carries a mandatory `sub_event` key in its payload. Valid sub_event values:

| sub_event | When it fires |
|---|---|
| `goal_created` | A new goal is created via `goal_manager.create_goal()` |
| `goal_advanced` | `advance_step()` increments current_step; payload includes `from_step`, `to_step` |
| `goal_blocked` | `add_blocker()` appends a blocker; payload includes `reason` |
| `goal_unblocked` | `clear_blocker()` removes all blockers |
| `goal_done` | `mark_done()` archives the goal as completed |
| `goal_killed` | `mark_killed()` archives the goal as abandoned |
| `goal_replanned` | `replan()` replaces remaining actions; payload includes `new_action_count` |
| `goal_noted` | `add_note()` appends free-text to the goal |

**Example payload:**
```json
{"event": "goal_event", "payload": {"sub_event": "goal_advanced", "goal_id": "G-A7K2QM", "from_step": 1, "to_step": 2}}
```

---

## Trace ID Format and Propagation

**Format:** `tr-YYYYMMDDHH-{6char-hex}`
- Example: `tr-2026050314-a3f9c2`
- Generated: by `_get_or_create_trace_id()` in `hooks/gate-enforcer.py` at gate-emit time
- Persisted: written to `session/state.json:current_trace_id`
- Propagated: passed to spawned sub-agents via `CLAUDE_TRACE_ID` environment variable
- Read by: `scripts/leroy_log.py` (env first, state.json fallback, "tr-unknown" last resort)

---

## Rotation Policy and Archive Naming

| Rule | Value |
|---|---|
| Rotation threshold | 25 MB |
| Archive location | `session/archive/leroy-YYYY-Www.log` |
| Archive naming | ISO calendar week, e.g. `leroy-2026-W18.log` |
| Rotation trigger | Stat check before each write in `leroy_log.py._rotate_if_needed()` |
| If archive exists | Append (not overwrite) — handles week boundary overlap |

---

## How to Read

**Live tail (PowerShell):**
Load skill: `skills/routines/logs-tail.md`
Trigger: `/logs tail` or `logs tail` or `tail logs`

**Trace filter (all events for one trace_id):**
Load skill: `skills/routines/logs-trace.md`
Trigger: `/logs trace {trace_id}` or `logs trace {trace_id}`
Renders ASCII Gantt showing agent timeline for the trace.

**Raw grep (one-liner):**
```
grep "topology_selected" session/leroy.log | tail -20
```

---

## Schema Versioning Policy

- The closed event enum is the schema contract. New events = ADR required.
- Field additions to `payload` are backward-compatible (consumers ignore unknown keys).
- Field removals or type changes to the 9 top-level fields require a schema version bump and migration note here.
- Current version: **1.1** (Sprint 3 2026-05-03 — added `goal_event` + sub_event taxonomy)

---

## Disable Path

To silence all leroy.log writes without removing the hook:

```
touch session/leroy-logger.disabled
```

Remove the file to re-enable. The `leroy_log.py` writer checks this flag before every write.

---

## Relationship to Other Logs

`leroy.log` is the **summary stream**. It does not replace detail logs:

| Log | Purpose | Relationship |
|---|---|---|
| `session/cost-log.jsonl` | Per-tool-call token + cost detail | leroy.log writes 1-line `cost_recorded` summary with `ref` back-pointer |
| `session/pii-detections.jsonl` | Full PII scan results | leroy.log writes 1-line `pii_detected` summary with `ref` back-pointer |
| `session/leroy-radar-log.jsonl` | Radar/watchlist alerts | Independent; leroy.log does not duplicate |
| `session/error-log.jsonl` | gate-enforcer internal errors | leroy.log writes `error_raised` summaries for hook-level errors |
