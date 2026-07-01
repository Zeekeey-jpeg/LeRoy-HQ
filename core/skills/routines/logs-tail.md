---
name: logs-tail
description: Live tail of session/leroy.log — the unified observability stream
tags: [observability, logs, debugging, leroy]
trigger: "/logs tail" | "logs tail" | "tail logs"
---

# /logs tail — Live Observability Stream

Stream the last 50 lines of `session/leroy.log` and follow new writes in real time.

## PowerShell (tail -f equivalent)

```powershell
Get-Content -Path "~/.claude\session\leroy.log" -Wait -Tail 50
```

Press `Ctrl+C` to stop following.

## One-shot snapshot (last 50 lines, no follow)

```powershell
Get-Content -Path "~/.claude\session\leroy.log" -Tail 50
```

## Filter by event type (example: topology_selected)

```powershell
Get-Content "~/.claude\session\leroy.log" | Where-Object { $_ -match "topology_selected" } | Select-Object -Last 20
```

## Filter by agent

```powershell
Get-Content "~/.claude\session\leroy.log" | Where-Object { $_ -match '"agent":"builder"' } | Select-Object -Last 20
```

## Notes

- Log rotates at 25 MB. Archives land in `session/archive/leroy-YYYY-Www.log`
- Schema reference: `skills/meta/leroy-log-schema.md`
- To trace a full multi-agent run: use `/logs trace {trace_id}` → `skills/routines/logs-trace.md`
- Disable writes: `touch session/leroy-logger.disabled` / re-enable: delete the file
