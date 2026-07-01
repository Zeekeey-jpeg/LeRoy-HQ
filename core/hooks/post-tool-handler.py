#!/usr/bin/env python3
"""
post-tool-handler.py v2.0 — Tool Telemetry + Interrupt Injection

Upgraded from v1.0 (interrupt-only) to add:
  F4-A: Tool-call logging → session/tool-history.jsonl
  F4-B: Capability gap detection → session/capability-gaps.jsonl
  F4-C: Task completion outcome scoring → session/outcome-history.jsonl

v1.0 interrupt surface remains fully intact and runs last (same behavior,
same exit codes). The F4 telemetry layer runs first, writes silently, and
never blocks — all errors are swallowed so a telemetry bug cannot break
tool execution.

Triggered: PostToolUse — after EVERY tool use (matcher: ".*")
Input: JSON on stdin: {tool_use_id, tool_name, tool_input, tool_response}
Output:
  - exit 0 silent: no interrupts
  - exit 2 + stderr: surface interrupts (non-blocking)

Tool-history format (JSONL, session/tool-history.jsonl, max 10000 lines):
  {"ts", "session_id", "tool_name", "ok", "is_error", "subagent_type", "arg_summary"}

Capability-gap format (session/capability-gaps.jsonl):
  {"ts", "session_id", "tool_name_attempted", "error_snippet", "occurrence_count", "first_seen"}

Outcome-history format (session/outcome-history.jsonl):
  {"ts", "session_id", "agent_type", "tool_name", "signal": +1|-1, "detail"}
"""

import json
import sys
import io
import os
from pathlib import Path
from datetime import datetime, timezone

CLAUDE_ROOT     = Path.home() / ".claude"
SESSION         = CLAUDE_ROOT / "session"
QUEUE_PATH      = SESSION / "interrupts.queue"
TOOL_HISTORY    = SESSION / "tool-history.jsonl"
GAP_HISTORY     = SESSION / "capability-gaps.jsonl"
OUTCOME_HISTORY = SESSION / "outcome-history.jsonl"
STATE_JSON      = SESSION / "state.json"

SURFACE_PRIORITIES = {"MEDIUM", "HIGH", "CRITICAL"}
PRIORITY_RANK      = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}

TOOL_HISTORY_CAP = 10000
TOOL_HISTORY_ROT = 8000   # keep newest ROT lines when CAP is hit

GAP_PATTERNS = [
    "tool not found",
    "unknown tool",
    "no tool named",
    "tool_not_found",
    "inputvalidationerror",
    "tool schema mismatch",
    "capability not available",
    "deferred tool",
]

# Tools that represent a task/delegation completion signal. Extend with your own
# notification/task tools as needed.
TASK_TOOLS = {"Agent", "Task", "TaskCreate", "TaskUpdate"}

# Force UTF-8 on stdin/stderr
if sys.stdin.encoding != "utf-8":
    sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "buffer") and getattr(sys.stderr, "encoding", "").lower() != "utf-8":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


# ── Helpers ────────────────────────────────────────────────────────────────────

def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _session_id() -> str:
    try:
        state = json.loads(STATE_JSON.read_text(encoding="utf-8", errors="ignore"))
        return str(state.get("session_id", ""))[:40] or "unknown"
    except Exception:
        return "unknown"


def _is_error(tool_response: dict) -> bool:
    if tool_response.get("isError"):
        return True
    if tool_response.get("error"):
        return True
    content = tool_response.get("content", [])
    if isinstance(content, list):
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                t = item.get("text", "").lower()
                if "error" in t and len(t) < 500:
                    return True
    return False


def _rotate_if_needed(path: Path):
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        if len(lines) >= TOOL_HISTORY_CAP:
            path.write_text("\n".join(lines[-TOOL_HISTORY_ROT:]) + "\n", encoding="utf-8")
    except Exception:
        pass


# ── F4-A: Tool-call logging ────────────────────────────────────────────────────

def log_tool_call(tool_name: str, tool_input: dict, tool_response: dict,
                  session_id: str):
    try:
        SESSION.mkdir(parents=True, exist_ok=True)
        is_err      = _is_error(tool_response)
        subagent    = (tool_input.get("subagent_type") or
                       tool_input.get("agentType") or "")
        arg_keys    = list(tool_input.keys())[:5] if tool_input else []
        arg_summary = ", ".join(
            f"{k}={str(tool_input.get(k, ''))[:40]!r}" for k in arg_keys
        )
        _rotate_if_needed(TOOL_HISTORY)
        with TOOL_HISTORY.open("a", encoding="utf-8") as f:
            f.write(json.dumps({
                "ts":           _ts(),
                "session_id":   session_id,
                "tool_name":    tool_name,
                "ok":           not is_err,
                "is_error":     is_err,
                "subagent_type": subagent,
                "arg_summary":  arg_summary[:200],
            }) + "\n")
    except Exception:
        pass


# ── F4-B: Capability gap detection ────────────────────────────────────────────

def detect_capability_gap(tool_name: str, tool_response: dict, session_id: str):
    try:
        error_text = ""
        if tool_response.get("error"):
            error_text += str(tool_response["error"]).lower() + " "
        content = tool_response.get("content", [])
        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    error_text += item.get("text", "").lower() + " "

        if not any(p in error_text for p in GAP_PATTERNS):
            return

        SESSION.mkdir(parents=True, exist_ok=True)
        gaps: dict[str, dict] = {}
        if GAP_HISTORY.exists():
            for line in GAP_HISTORY.read_text(encoding="utf-8", errors="ignore").splitlines():
                try:
                    g = json.loads(line)
                    k = g.get("tool_name_attempted", "")
                    if k:
                        gaps[k] = g
                except Exception:
                    pass

        existing = gaps.get(tool_name, {})
        count    = existing.get("occurrence_count", 0) + 1
        gaps[tool_name] = {
            "ts":                  _ts(),
            "session_id":          session_id,
            "tool_name_attempted": tool_name,
            "error_snippet":       error_text[:300].strip(),
            "occurrence_count":    count,
            "first_seen":          existing.get("first_seen", _ts()),
        }
        with GAP_HISTORY.open("w", encoding="utf-8") as f:
            for g in gaps.values():
                f.write(json.dumps(g) + "\n")
    except Exception:
        pass


# ── F4-C: Task completion outcome scoring ─────────────────────────────────────

def score_task_outcome(tool_name: str, tool_input: dict, tool_response: dict,
                       session_id: str):
    try:
        if tool_name not in TASK_TOOLS:
            return
        is_err     = _is_error(tool_response)
        signal     = -1 if is_err else +1
        agent_type = (tool_input.get("subagent_type") or
                      tool_input.get("agentType") or tool_name)
        SESSION.mkdir(parents=True, exist_ok=True)
        with OUTCOME_HISTORY.open("a", encoding="utf-8") as f:
            f.write(json.dumps({
                "ts":         _ts(),
                "session_id": session_id,
                "agent_type": agent_type,
                "tool_name":  tool_name,
                "signal":     signal,
                "detail":     "error" if is_err else "complete",
            }) + "\n")
    except Exception:
        pass


# ── Interrupt queue (v1.0 — unchanged) ────────────────────────────────────────

def read_queue():
    if not QUEUE_PATH.exists():
        return []
    entries = []
    try:
        with open(QUEUE_PATH, "r", encoding="utf-8") as f:
            for i, line in enumerate(f):
                line = line.strip()
                if not line:
                    continue
                try:
                    entries.append((i, json.loads(line)))
                except json.JSONDecodeError:
                    continue
    except OSError:
        return []
    return entries


def write_queue(entries):
    tmp = QUEUE_PATH.with_suffix(".queue.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        for entry in entries:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    os.replace(tmp, QUEUE_PATH)


def handle_interrupts() -> tuple[bool, str]:
    raw_entries = read_queue()
    if not raw_entries:
        return False, ""

    to_surface = []
    for idx, entry in raw_entries:
        if entry.get("acked") or entry.get("surfaced"):
            continue
        priority = (entry.get("priority") or "").upper()
        if priority not in SURFACE_PRIORITIES:
            continue
        to_surface.append((idx, entry))

    if not to_surface:
        return False, ""

    to_surface.sort(key=lambda x: (PRIORITY_RANK.get(x[1].get("priority", "").upper(), 99),
                                   x[1].get("ts", "")))

    lines = []
    has_critical = any(e[1].get("priority", "").upper() == "CRITICAL" for e in to_surface)
    if has_critical:
        lines.append("[SOFT INTERRUPT — CRITICAL] Pause TodoWrite progress before next tool. Surface to user.")
    else:
        lines.append(f"[SOFT INTERRUPT] {len(to_surface)} pending message(s) — acknowledge before continuing.")
    lines.append("")
    for idx, entry in to_surface:
        priority = entry.get("priority", "?").upper()
        source   = entry.get("source", "?")
        payload  = entry.get("payload", "(empty)")
        eid      = entry.get("id", f"line{idx}")
        ts       = entry.get("ts", "")
        ack_note = " [ACK requested]" if entry.get("ack_required") else ""
        lines.append(f"  [{priority}] from={source} id={eid} ts={ts[:19]}{ack_note}")
        lines.append(f"    {payload}")

    surfaced_ids = {(idx, id(entry)) for idx, entry in to_surface}
    surfaced_now = _ts()
    new_entries  = []
    for idx, entry in raw_entries:
        if (idx, id(entry)) in surfaced_ids:
            entry["surfaced"]    = True
            entry["surfaced_at"] = surfaced_now
        new_entries.append(entry)

    try:
        write_queue(new_entries)
    except OSError as e:
        lines.append(f"  [WARN] Could not update queue ({e})")

    return True, "\n".join(lines)


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    tool_name     = ""
    tool_input    = {}
    tool_response = {}
    try:
        raw = sys.stdin.read()
        if raw.strip():
            data          = json.loads(raw)
            tool_name     = data.get("tool_name", "")
            tool_input    = data.get("tool_input") or {}
            tool_response = data.get("tool_response") or {}
    except Exception:
        pass

    # F4 telemetry — always runs, never blocks
    if tool_name:
        sid = _session_id()
        log_tool_call(tool_name, tool_input, tool_response, sid)
        detect_capability_gap(tool_name, tool_response, sid)
        score_task_outcome(tool_name, tool_input, tool_response, sid)

    # v1.0 interrupt surface — unchanged
    should_surface, message = handle_interrupts()
    if should_surface:
        sys.stderr.write(message + "\n")
        sys.exit(2)

    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        sys.stderr.write(f"[post-tool-handler v2.0] error: {e}\n")
        sys.exit(0)
