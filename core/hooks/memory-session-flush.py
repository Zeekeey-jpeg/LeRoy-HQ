#!/usr/bin/env python3
"""
Memory Session Flush v1.0 — Stop hook vault flush.

Fires when a session ends (Stop event). Spawns scout-cron.py in a detached
background process so the memory index and Chat files are updated even if the
session lasted only a few minutes.

Rules:
  - Never blocks Claude (always exits 0 in <30ms)
  - Spawns scout-cron.py detached — doesn't wait for it
  - Writes a flush-request sentinel if spawn fails (cron picks it up)

GRACEFUL DEGRADE: if scripts/scout-cron.py is absent (e.g. you don't run the
memory indexer), the hook exits silently — nothing to flush.
"""

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

CLAUDE_DIR   = Path(__file__).parent.parent
SESSION_DIR  = CLAUDE_DIR / "session"
SCRIPTS_DIR  = CLAUDE_DIR / "scripts"
DISABLE_FLAG = SESSION_DIR / "memory-session-flush.disabled"
LOG_FILE     = SESSION_DIR / "session-flush-log.jsonl"


def main() -> None:
    if DISABLE_FLAG.exists():
        sys.exit(0)

    try:
        sys.stdin.read()
    except Exception:
        sys.exit(0)

    scout_cron = SCRIPTS_DIR / "scout-cron.py"
    if not scout_cron.exists():
        sys.exit(0)  # Optional indexer not present — graceful degrade.

    try:
        subprocess.Popen(
            [sys.executable, str(scout_cron)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
            cwd=str(CLAUDE_DIR),
        )
        entry = {"ts": datetime.now(timezone.utc).isoformat(), "event": "flush_spawned"}
    except Exception as e:
        # Write sentinel so next cron run knows a flush was missed
        try:
            sentinel = SESSION_DIR / "flush-missed.txt"
            sentinel.write_text(datetime.now(timezone.utc).isoformat(), encoding="utf-8")
        except Exception:
            pass
        entry = {"ts": datetime.now(timezone.utc).isoformat(), "event": "flush_failed", "err": str(e)[:100]}

    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass

    sys.exit(0)


if __name__ == "__main__":
    main()
