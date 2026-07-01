#!/usr/bin/env python3
"""
Memory Live Capture v1.0 — Real-time memory librarian hook.

Fires on:
  - UserPromptSubmit: captures signal-bearing prompts immediately
  - PostToolUse (.*): captures builds (Write/Edit), delegations (Task/Agent),
    key Bash ops — tags each entry with session_id for isolation.

Rules:
  - NEVER delete anything
  - Always exit 0 (never block Claude)
  - Complete in <80ms (appends only, no index rebuild here)
  - Session-tagged: each entry carries session_id so sessions never bleed

Output: memory/Chat/YYYY-MM-DD.md (append-only daily file)

CONFIG: SIGNAL_RE is the set of words that mark a prompt "worth remembering".
The defaults below are generic (decisions, preferences, projects, deadlines,
etc.). Add your own domain keywords to capture more.
"""

import json
import os
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────
CLAUDE_DIR  = Path(__file__).parent.parent
MEMORY_DIR  = CLAUDE_DIR / "memory"
SESSION_DIR = CLAUDE_DIR / "session"
CHAT_DIR    = MEMORY_DIR / "Chat"
STATE_FILE  = SESSION_DIR / "state.json"
DISABLE_FLAG = SESSION_DIR / "memory-live-capture.disabled"

# ── Signal patterns (prompts worth capturing) ─────────────────────────────────
# Generic signal words. Extend with your own project/domain keywords.
SIGNAL_RE = re.compile(
    r'\b(remember|prefer|always|never|decision|pattern|learned|important|'
    r'client|deal|contract|project|schedule|deadline|price|budget|invoice|'
    r'meeting|priority|todo|note|bug|release|deploy)\b',
    re.IGNORECASE,
)

# Tools that always signal something was built/changed
BUILD_TOOLS = {"Write", "Edit", "MultiEdit"}

# Tools that signal delegation
DELEGATE_TOOLS = {"Task", "Agent"}

# Bash patterns worth capturing
BASH_SIGNAL_RE = re.compile(
    r'(python|git\s+(commit|push|add)|npm\s+run|embed|memory|recall)',
    re.IGNORECASE,
)


def now_ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def today_str() -> str:
    return date.today().isoformat()


def get_session_id() -> str:
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        return data.get("session_id") or data.get("id") or "unknown"
    except Exception:
        return "unknown"


def append_to_chat(entry: str, session_id: str) -> None:
    """Append one markdown entry to today's Chat file. Never raises."""
    try:
        CHAT_DIR.mkdir(parents=True, exist_ok=True)
        target = CHAT_DIR / f"{today_str()}.md"
        line = f"- [{now_ts()}] [{session_id[:8]}] {entry}\n"
        with open(target, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass  # Never crash, never block


def handle_user_prompt(payload: dict) -> None:
    """Capture signal-bearing user prompts."""
    prompt = (
        payload.get("prompt")
        or payload.get("user_prompt")
        or payload.get("text")
        or ""
    )
    if isinstance(prompt, list):
        prompt = " ".join(str(p) for p in prompt)
    prompt = str(prompt).strip()

    if len(prompt) < 15:
        return
    if not SIGNAL_RE.search(prompt):
        return

    excerpt = prompt[:300].replace("\n", " ")
    session_id = get_session_id()
    append_to_chat(f"[PROMPT] {excerpt}", session_id)


def handle_post_tool(payload: dict) -> None:
    """Capture build/delegate/bash events from tool use."""
    tool_name = (
        payload.get("tool_name")
        or payload.get("tool")
        or ""
    )
    tool_input = payload.get("tool_input") or {}
    session_id = get_session_id()

    if tool_name in BUILD_TOOLS:
        # Something was written or edited — capture the filepath
        file_path = tool_input.get("file_path") or tool_input.get("path") or ""
        if file_path:
            rel = file_path.replace(str(CLAUDE_DIR), ".claude").replace("\\", "/")
            append_to_chat(f"[{tool_name.upper()}] {rel}", session_id)

    elif tool_name in DELEGATE_TOOLS:
        # Agent/Task spawned — capture description or first 150 chars of prompt
        desc = (
            tool_input.get("description")
            or tool_input.get("task")
            or tool_input.get("prompt", "")[:150]
        )
        if desc:
            desc_short = str(desc).strip()[:150].replace("\n", " ")
            append_to_chat(f"[{tool_name.upper()}] {desc_short}", session_id)

    elif tool_name == "Bash":
        cmd = tool_input.get("command") or ""
        if BASH_SIGNAL_RE.search(str(cmd)):
            cmd_short = str(cmd).strip()[:200].replace("\n", " ")
            append_to_chat(f"[BASH] {cmd_short}", session_id)


def main() -> None:
    if DISABLE_FLAG.exists():
        sys.exit(0)

    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
    except Exception:
        sys.exit(0)

    try:
        # Detect event type: UserPromptSubmit payloads have prompt/user_prompt;
        # PostToolUse payloads have tool_name.
        if payload.get("tool_name") or payload.get("tool"):
            handle_post_tool(payload)
        elif payload.get("prompt") or payload.get("user_prompt") or payload.get("text"):
            handle_user_prompt(payload)
        # If neither, silently skip (unknown event type)
    except Exception:
        pass  # Never crash, never block

    sys.exit(0)


if __name__ == "__main__":
    main()
