#!/usr/bin/env python3
"""
Agent Spawn Logger v1.0
PreToolUse hook — fires on Task tool calls.

Appends ONE JSON line per spawn to session/agent-spawn-log.jsonl.

CRITICAL DESIGN: fail-open and non-blocking.
  - Everything wrapped in try/except.
  - Always exit 0.
  - Never blocks or delays the spawn, even if logging fails.
  - Does NOT print to stdout (PreToolUse stdout can interfere with the spawn).

Stdin/JSON parsing convention copied from agent-spawn-validator.py:
  hook payload (top-level JSON) -> "tool_name", "tool_input" (dict).
  For a Task call, tool_input holds "subagent_type", "prompt", "description".

CONFIG: derive_project() maps a working-directory / payload substring to a
project label. The PROJECT_MARKERS list below is an example — replace the
(substring, label) pairs with your own project roots.
"""

import json
import sys
import io
import os
from pathlib import Path
from datetime import datetime, timezone

# Force UTF-8 encoding for stdin (matches validator convention)
try:
    if sys.stdin.encoding != 'utf-8':
        sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8', errors='replace')
except Exception:
    pass

# Paths
CLAUDE_ROOT = Path.home() / ".claude"
SESSION_DIR = CLAUDE_ROOT / "session"
SPAWN_LOG = SESSION_DIR / "agent-spawn-log.jsonl"

# Example project markers — (lowercase substring to look for, label to record).
# Longest / most-specific first. Customize for your own projects.
PROJECT_MARKERS = [
    ("project-alpha", "Alpha"),
    ("project-beta", "Beta"),
]


def parse_stdin() -> dict:
    """Read + parse the hook JSON payload from stdin. Never raises."""
    try:
        return json.loads(sys.stdin.read())
    except Exception:
        return {}


def derive_project(hook_data: dict, tool_input: dict) -> str:
    """Best-effort project derivation from cwd / payload state. Never raises."""
    try:
        # Candidate strings to scan for a marker.
        candidates = []
        cwd = hook_data.get("cwd") or tool_input.get("cwd") or os.getcwd()
        if cwd:
            candidates.append(str(cwd))
        # Some payloads carry session/workspace hints.
        for key in ("project", "workspace", "session_id"):
            val = hook_data.get(key)
            if isinstance(val, str):
                candidates.append(val)

        haystack = " ".join(candidates).lower()
        for needle, label in PROJECT_MARKERS:
            if needle in haystack:
                return label
    except Exception:
        pass
    return "unknown"


def main():
    try:
        hook_data = parse_stdin()
        tool_name = hook_data.get("tool_name", "")

        # Only act on Task spawns; everything else is a no-op (still exit 0).
        if tool_name != "Task":
            return

        tool_input = hook_data.get("tool_input", {})
        if not isinstance(tool_input, dict):
            tool_input = {}

        # subagent_type -> 'fork' if omitted (a fork/general spawn).
        subagent_type = tool_input.get("subagent_type") or "fork"

        # spawned_by: best available, else 'main'.
        spawned_by = (
            tool_input.get("spawned_by")
            or hook_data.get("spawned_by")
            or hook_data.get("parent_agent")
            or "main"
        )

        # task_preview: first 80 chars of prompt, falling back to description.
        task_src = tool_input.get("prompt") or tool_input.get("description") or ""
        task_preview = str(task_src)[:80]

        # gate_tier: present in payload else null.
        gate_tier = (
            tool_input.get("gate_tier")
            if tool_input.get("gate_tier") is not None
            else hook_data.get("gate_tier")
        )

        project = derive_project(hook_data, tool_input)

        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "agent": subagent_type,
            "spawned_by": spawned_by,
            "task_preview": task_preview,
            "project": project,
            "gate_tier": gate_tier,
        }

        try:
            SESSION_DIR.mkdir(parents=True, exist_ok=True)
            with SPAWN_LOG.open('a', encoding='utf-8') as fh:
                fh.write(json.dumps(entry) + '\n')
        except Exception:
            # Fail-open: logging failure must never block the spawn.
            pass
    except Exception:
        # Absolute fail-open guard around the entire handler.
        pass


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    # Always exit 0 — never block or delay the spawn.
    sys.exit(0)
