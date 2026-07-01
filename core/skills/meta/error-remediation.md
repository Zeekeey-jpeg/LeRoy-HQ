---
name: error-remediation
description: "Error remediation decision tree for Bash failures. Three tiers: auto-fix (pip install), diagnose (Claude-assisted), escalate (human required). Used by error-remediator.py hook and Claude when encountering Bash errors."
version: 1.0
created: 2026-04-11
owner: meta
---

# Error Remediation Framework

## How This Works

The `error-remediator.py` PostToolUse hook runs automatically after every Bash tool call. It:
1. Reads exit_code + stderr from the tool result
2. Pattern matches against the error registry below
3. Auto-fixes safe/deterministic errors, logs others, flags systemic patterns

**Claude's role:** Read the hook output and act on it. If `[AUTO-FIX]` appears → re-run the same command. If `Suggestion:` appears → apply the suggestion before retrying. If `ESCALATE` → ask the user.

---

## Tier 1 — Auto-Fix (Hook handles autonomously)

These errors are fixed automatically by `error-remediator.py` without Claude needing to act:

| Pattern | Error | Auto-Fix |
|---------|-------|----------|
| `ModuleNotFoundError` | Python module not installed | `pip install <module>` — runs immediately |

**When auto-fix fires:** Hook outputs `[AUTO-FIX] Installed missing module: X. Re-run the command.`
→ Claude must re-run the exact same command that failed. The module is now installed.

---

## Tier 2 — Diagnose (Claude diagnoses with hook context)

Hook provides suggestion — Claude interprets and applies:

| Pattern | Error | Hook Suggestion | Claude Action |
|---------|-------|-----------------|---------------|
| `RateLimitError` | HTTP 429 from API | "Wait 60s before retry" | Wait, then retry. Add backoff if recurring. |
| `ConnectionRefused` | Service not running | "Verify target process is up" | Check if service needs to be started. Review port. |
| `JSONDecodeError` | Non-JSON response | "Check response encoding or if endpoint returns HTML" | Inspect response. May be an auth/redirect. |
| `FileNotFound` | Path doesn't exist | "Use Glob to find correct path" | Run Glob with similar pattern to find actual path. |
| `PythonSyntaxError` | Runtime syntax error | "Check the script file" | Read the script, find syntax issue, fix and re-run. |

---

## Tier 3 — Escalate (Requires human input)

Hook flags these but cannot resolve:

| Pattern | Error | Action |
|---------|-------|--------|
| `PermissionDenied` | System-level permission | Stop and ask user. Do NOT chmod system files without explicit request. |
| Logic errors | Wrong output, not an exception | Diagnose root cause. Don't retry blindly. |
| Auth failures | Credentials invalid/expired | Ask user to refresh credentials. Never try to guess. |

---

## Systemic Pattern Detection

`error-remediator.py` tracks errors in `session/error-log.jsonl`. If the same pattern appears 3+ times in 24 hours:
1. Hook writes `ERROR_PATTERN_SYSTEMIC | pattern=X` to `session/enforcement.todo`  
2. `gate-enforcer.py` reads this on next prompt and surfaces it in the [GATE] banner
3. Tells Claude: "This pattern needs a permanent fix, not another retry"

**Example:** `ModuleNotFoundError` appearing 3x → means a dependency isn't in the project's requirements. Permanent fix: add to `requirements.txt` or update project setup.

---

## Error Log Reference

```
session/error-log.jsonl — one JSON entry per line:
{
  "ts": "2026-04-11T14:23:00Z",
  "pattern": "ModuleNotFoundError",
  "stderr_snippet": "No module named 'requests'",
  "auto_fixed": true,
  "suggestion": ""
}
```

To review recent errors:
```bash
tail -20 session/error-log.jsonl | python3 -m json.tool
# Or count by pattern:
python3 -c "
import json
from pathlib import Path
entries = [json.loads(l) for l in Path('session/error-log.jsonl').read_text().splitlines() if l]
patterns = {}
for e in entries:
    patterns[e['pattern']] = patterns.get(e['pattern'], 0) + 1
print(sorted(patterns.items(), key=lambda x: -x[1]))
"
```
