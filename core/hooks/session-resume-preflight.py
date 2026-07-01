#!/usr/bin/env python3
"""
session-resume-preflight.py -- UserPromptSubmit hook.

Detects when a session is being RESUMED after a long idle gap (default 3h)
and injects a preflight directive.

WHY: A long-open / resumed session silently degrades -- MCP connections drop,
fallback tools route around the guard hooks, and injected context goes stale.
In one incident a ~24h-resumed session sent an unbranded email (the primary
mail MCP was down -> an unguarded fallback path was used) and answered from a
stale ledger. This preflight forces a re-verify before any outbound action.

This hook does NOT block and cannot itself reach the MCP layer. On a stale
resume it tells Claude to:
  1. Re-verify MCP health (esp. the mail/outbound server) BEFORE any outbound action.
  2. Reload the outbound + memory protocols before acting.
  3. Treat the injected context anchor / recalled status as possibly stale
     and sanity-check status data against live sources.

Within an active session the stamp updates every turn, so the gap is seconds
and this never fires. It only fires on genuine resume.

SAFETY: entire body wrapped in try/except; always exit 0 (never breaks the
pipeline, never blocks a prompt).
"""

import sys
from pathlib import Path
from datetime import datetime, timezone

CLAUDE_ROOT = Path.home() / ".claude"
SESSION_DIR = CLAUDE_ROOT / "session"
STAMP = SESSION_DIR / "last-activity.txt"
THRESHOLD_HOURS = 3.0


def _banner(gap_hours: float) -> str:
    hrs = f"{gap_hours:.1f}h" if gap_hours < 48 else f"{gap_hours/24:.1f}d"
    return (
        "================================================================================\n"
        f"    [STALE-SESSION RESUME] Idle ~{hrs} since last activity -- run PREFLIGHT first\n"
        "================================================================================\n"
        "    A long-open session degrades silently. BEFORE acting on this prompt:\n"
        "    1. VERIFY MCP HEALTH -- esp. your mail/outbound server. If an outbound/\n"
        "       email/calendar/drive action is involved, confirm the server is actually\n"
        "       connected. Do NOT silently fall back to an unguarded tool and call it 'sent'.\n"
        "    2. RELOAD PROTOCOLS before outbound or memory work:\n"
        "       - Outbound email -> your outbound/branding protocol (branded HTML).\n"
        "       - Memory/status   -> sanity-check ledgers/status against live source\n"
        "                          before reporting.\n"
        "    3. The injected context anchor / recalled notes may be STALE -- verify\n"
        "       any file/flag/status they name still reflects reality.\n"
        "================================================================================\n"
    )


def main() -> None:
    try:
        # Drain stdin so the hook never blocks on the payload.
        try:
            sys.stdin.read()
        except Exception:
            pass

        now = datetime.now(timezone.utc)
        gap_hours = None
        try:
            if STAMP.exists():
                prev = datetime.fromisoformat(STAMP.read_text(encoding="utf-8").strip())
                gap_hours = (now - prev).total_seconds() / 3600.0
        except Exception:
            gap_hours = None

        # Always refresh the stamp for the next turn.
        try:
            SESSION_DIR.mkdir(parents=True, exist_ok=True)
            STAMP.write_text(now.isoformat(), encoding="utf-8")
        except Exception:
            pass

        if gap_hours is not None and gap_hours >= THRESHOLD_HOURS:
            sys.stdout.write(_banner(gap_hours))
    except Exception:
        pass
    sys.exit(0)


if __name__ == "__main__":
    main()
