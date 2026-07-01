---
name: cost-digest-weekly
description: Sunday 18:00 ET — run cost-aggregator and push weekly cost summary to Telegram
created: 2026-05-03
modified: 2026-05-03
tags: [routines, cost, telegram, digest, cron]
trigger:
  manual: ["weekly cost digest", "cost digest"]
  cron: "0 18 * * 0"
---

# Weekly Cost Digest

## Limitation — Session-Only Cron

This skill is registered via `CronCreate` which is **session-only**: the cron job auto-expires when the Claude Code session ends or after 7 days, whichever comes first. The Sunday 18:00 firing is NOT durable across Claude restarts.

**For permanent scheduling**, register a Windows Task Scheduler entry similar to `Claude-DailyOps` (see `skills/routines/daily-ops.md` for the pattern). Until then, this cron must be re-registered each new Claude session — consider adding the registration to morning routine or telegram-launch startup.

**Workaround for now:** Run `python ~/.claude/scripts/cost-aggregator.py --capture-output` manually any Sunday and forward to Telegram chat <YOUR_TELEGRAM_CHAT_ID> if the cron didn't fire.

---

## Purpose

Runs every Sunday at 18:00 local time. Executes `scripts/cost-aggregator.py --capture-output`
to produce a clean Telegram-ready cost summary and pushes it to the user's Telegram chat.

Heartbeat dedup prevents duplicate sends if the cron fires more than once on the same day
(e.g., session restart or manual trigger).

---

## Heartbeat Dedup

Before executing, read `~/.claude\session\cost-digest-heartbeat.txt`.

- If the file contains today's date (format `YYYY-MM-DD`) → **skip entirely, do nothing.**
- If the file is missing or contains a past date → **proceed with execution.**

```python
from pathlib import Path
from datetime import date

heartbeat = Path("~/.claude/session/cost-digest-heartbeat.txt")
today = date.today().isoformat()

if heartbeat.exists() and heartbeat.read_text().strip() == today:
    # Already sent today — skip silently
    exit(0)
```

---

## Execution Sequence

### Step 1 — Run aggregator with --capture-output flag

```bash
python ~/.claude/scripts/cost-aggregator.py --capture-output
```

Capture stdout into a variable. The flag suppresses file-path footer lines and emits only
the Telegram-ready summary string.

### Step 2 — Check for no-data condition

If the captured output starts with `no data` (case-insensitive) → **skip Telegram send.**
Write today's date to heartbeat file and exit. No error, no alert.

```python
if output.lower().startswith("no data"):
    heartbeat.write_text(today)
    exit(0)
```

### Step 3 — Send to Telegram

Call `mcp__plugin_telegram_telegram__reply` with:

- `chat_id`: `<YOUR_TELEGRAM_CHAT_ID>`
- `text`: the captured stdout string

```python
# MCP call — not Python; pseudocode for reference
mcp__plugin_telegram_telegram__reply(
    chat_id="<YOUR_TELEGRAM_CHAT_ID>",
    text=output
)
```

### Step 4 — Write heartbeat

Write today's date to `~/.claude\session\cost-digest-heartbeat.txt`:

```python
heartbeat.write_text(today)
```

---

## Error Handling

If the Telegram send fails (MCP error, network timeout, etc.):

1. **Do NOT retry immediately.** The cron will fire again next Sunday.
2. Log the error to `~/.claude\session\cost-digest-errors.jsonl`:

```python
import json
from datetime import datetime, timezone

error_log = Path("~/.claude/session/cost-digest-errors.jsonl")
entry = {
    "ts": datetime.now(timezone.utc).isoformat(),
    "error": str(exception),
    "week": week_label,   # e.g. "2026-W18"
    "output_preview": output[:200]
}
with open(error_log, "a", encoding="utf-8") as f:
    f.write(json.dumps(entry) + "\n")
```

3. Do **not** write the heartbeat file on Telegram failure — this allows a manual retry
   by saying "weekly cost digest" in a new session before next Sunday.

---

## Telegram Target

- **chat_id:** `<YOUR_TELEGRAM_CHAT_ID>`
- **tool:** `mcp__plugin_telegram_telegram__reply`
- **format:** plain text (no MarkdownV2)

---

## Related Files

| File | Role |
|------|------|
| `scripts/cost-aggregator.py` | Produces the digest string; writes `session/cost-weekly-{YYYY-WW}.md` and appends to `session/cost-history.jsonl` |
| `session/cost-digest-heartbeat.txt` | Dedup guard — contains last-sent date |
| `session/cost-digest-errors.jsonl` | Error log for failed Telegram sends |
| `session/cost-log.jsonl` | Source data read by the aggregator |
