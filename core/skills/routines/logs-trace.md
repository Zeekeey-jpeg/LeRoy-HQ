---
name: logs-trace
description: Render ASCII Gantt timeline for a leroy.log trace_id — shows all events grouped by agent across a multi-agent run
tags: [observability, logs, debugging, leroy, trace]
trigger: "/logs trace" | "trace logs" | "logs trace"
---

# /logs trace — Multi-Agent Timeline Gantt

Filters `session/leroy.log` by `trace_id` and renders an ASCII Gantt showing all agent activity bands.

## Usage

```powershell
python ~/.claude\scripts\logs-trace.py <trace_id>
```

Replace `<trace_id>` with the actual trace ID, e.g.:

```powershell
python ~/.claude\scripts\logs-trace.py tr-2026050314-a3f9c2
```

## Output Example

```
trace tr-2026050314-a3f9c2 — duration 8.3s, 24 events, 3 agents

system          |████                    | 14:22:01 → 14:22:03 (4 events: gate_emitted(1), topology_selected(1), tool_result(2))
builder         |     ████████████       | 14:22:03 → 14:22:09 (15 events: tool_result(12), skill_loaded(2), memory_written(1))
guardian        |                   ████ | 14:22:09 → 14:22:10 (5 events: tool_result(4), agent_completed(1))
```

## Finding Your Trace ID

The current session trace ID is in `session/state.json:current_trace_id`.

```powershell
python -c "import json; s=json.load(open('~/.claude/session/state.json')); print(s.get('current_trace_id','not set'))"
```

Or look at the TOPOLOGY banner line in the gate output — it shows the auto-selected topology, and the trace ID is embedded in recent log entries.

## Notes

- Archives: if the trace spans a rotation boundary, also check `session/archive/leroy-YYYY-Www.log`
- Schema reference: `skills/meta/leroy-log-schema.md`
- For live watching: use `/logs tail` → `skills/routines/logs-tail.md`
