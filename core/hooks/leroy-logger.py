#!/usr/bin/env python3
"""
leroy-logger.py — PostToolUse `.*` tee hook.

Registered LAST in the PostToolUse chain (after cost-meter, pii-pre-write).
Writes ONE tool_result record to session/agent.log per tool invocation.

Safety rules:
  - try/except wrap -> exit 0 always, never blocks tool execution
  - Honors session/leroy-logger.disabled flag (returns immediately if present)
  - Delegates all writes to scripts/agent_log.py (shared writer)

GRACEFUL DEGRADE: if scripts/agent_log.py is not present, the hook exits
silently — logging is optional and must never break the tool chain.
"""

import json
import os
import sys
import time
from pathlib import Path

CLAUDE_DIR = Path(__file__).parent.parent
SCRIPTS_DIR = CLAUDE_DIR / "scripts"
DISABLE_FLAG = CLAUDE_DIR / "session" / "leroy-logger.disabled"

sys.path.insert(0, str(SCRIPTS_DIR))


def _summarise_input(tool_input, max_chars: int = 200) -> str:
    """Return a short string summary of tool_input for the payload."""
    try:
        if isinstance(tool_input, dict):
            raw = json.dumps(tool_input, default=str)
        else:
            raw = str(tool_input)
        if len(raw) > max_chars:
            return raw[:max_chars] + "..."
        return raw
    except Exception:
        return "(unserializable)"


def _infer_level(tool_response) -> str:
    """Return warn/error/info based on response content."""
    try:
        if isinstance(tool_response, dict):
            if tool_response.get("error") or tool_response.get("exception"):
                return "error"
            status = str(tool_response.get("status", "")).lower()
            if status in ("error", "failed", "failure"):
                return "warn"
        if isinstance(tool_response, str):
            lower = tool_response.lower()
            if "error" in lower or "exception" in lower or "traceback" in lower:
                return "warn"
    except Exception:
        pass
    return "info"


def main() -> None:
    if DISABLE_FLAG.exists():
        return

    try:
        # Shared writer is optional — import inside try so its absence is a
        # silent no-op rather than a crash.
        from agent_log import write_event

        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}

        tool_name = (
            payload.get("tool_name")
            or payload.get("tool")
            or "unknown"
        )
        tool_input = payload.get("tool_input", {})
        tool_response = payload.get("tool_response") or payload.get("tool_result", {})

        # duration_ms: not provided by harness for PostToolUse; use 0 as placeholder
        duration_ms = int(payload.get("duration_ms", 0))

        level = _infer_level(tool_response)

        event_payload = {
            "tool_input_summary": _summarise_input(tool_input),
            "duration_ms": duration_ms,
            "status": "error" if level in ("warn", "error") else "ok",
        }

        write_event(
            event="tool_result",
            payload=event_payload,
            level=level,
            tool=tool_name,
        )

    except Exception:
        pass  # Never block the tool chain


if __name__ == "__main__":
    main()
