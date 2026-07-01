#!/usr/bin/env python3
"""
leroy-status-line.py — Trace Heartbeat (PostToolUse, near-zero cost).

When a front-end / gateway spawns the agent it can set STATUS_FILE (env var
LEROY_STATUS_FILE) in the child env. Every tool call in that run lands here, and
we overwrite the file with a one-line human status ("Searching memory...",
"Editing App.tsx...") that a UI's thinking indicator can poll. Terminal sessions
have no STATUS_FILE -> instant exit, zero overhead.

Portable: reads one env var, writes one small file. No OS-specific code.
"""
import json
import os
import sys

STATUS_FILE = os.environ.get("LEROY_STATUS_FILE")
if not STATUS_FILE:
    sys.exit(0)

VERBS = {
    "Read": "Reading {target}",
    "Write": "Writing {target}",
    "Edit": "Editing {target}",
    "Bash": "Running a command",
    "PowerShell": "Running a command",
    "Grep": "Searching the codebase",
    "Glob": "Scanning files",
    "WebSearch": "Searching the web",
    "WebFetch": "Fetching a page",
    "Task": "Delegating to an agent",
    "Agent": "Delegating to an agent",
    "Skill": "Loading a skill",
    "TodoWrite": "Organizing the plan",
}


def main():
    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
    except Exception:
        sys.exit(0)

    tool = data.get("tool_name", "")
    tin = data.get("tool_input", {}) or {}

    target = ""
    for key in ("file_path", "path", "pattern", "query", "url"):
        v = tin.get(key)
        if v:
            target = os.path.basename(str(v))[:40]
            break

    if tool.startswith("mcp__"):
        # e.g. mcp__<server>__<action> -> "<server>: <action>"
        parts = tool.split("__")
        line = f"Using {parts[1]}" + (f": {parts[2].replace('_', ' ')}" if len(parts) > 2 else "")
    else:
        tpl = VERBS.get(tool, f"Using {tool}" if tool else "Working")
        line = tpl.format(target=target or "files")

    try:
        os.makedirs(os.path.dirname(STATUS_FILE), exist_ok=True)
        tmp = STATUS_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(line[:80])
        os.replace(tmp, STATUS_FILE)
    except Exception:
        pass
    sys.exit(0)


if __name__ == "__main__":
    main()
