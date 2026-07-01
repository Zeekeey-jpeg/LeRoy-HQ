#!/usr/bin/env python3
"""
Error Remediator Hook v1.0 — PostToolUse on Bash
Reads Bash tool exit code + stderr, pattern matches against error registry.

AUTO-FIX (safe, deterministic):
  - ModuleNotFoundError → pip install <module>

LOG + SUGGEST (Claude diagnoses):
  - 429 Too Many Requests → retry-queue entry with backoff
  - Connection refused → check service running
  - JSONDecodeError → encoding check
  - File not found → path suggestion

ESCALATE (systemic detection):
  - Same pattern 3+ times in 24h → ERROR_PATTERN_SYSTEMIC in enforcement queue

Usage: Called by settings.json PostToolUse hook with matcher "Bash"
Input (stdin): Claude Code hook JSON with tool_result containing exit_code + stderr
"""
import json
import sys
import os
import subprocess
import time
import re
import io
from datetime import datetime, timezone
from pathlib import Path

# Windows UTF-8 compat
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
if sys.stdin.encoding != 'utf-8':
    sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8', errors='replace')

CLAUDE_DIR = Path(__file__).parent.parent
ERROR_LOG = CLAUDE_DIR / "session" / "error-log.jsonl"
ENFORCEMENT_TODO = CLAUDE_DIR / "session" / "enforcement.todo"

# Use the interpreter running this hook — portable across OSes and installs.
PYTHON_EXE = sys.executable

def read_input() -> dict:
    try:
        raw = sys.stdin.read()
        return json.loads(raw) if raw.strip() else {}
    except Exception:
        return {}

def get_error_info(data: dict) -> tuple[int, str]:
    """Extract exit_code and stderr from hook payload."""
    # Claude Code sends tool_result for PostToolUse
    tool_result = data.get("tool_result") or data.get("tool_response") or {}
    if isinstance(tool_result, str):
        try:
            tool_result = json.loads(tool_result)
        except Exception:
            pass

    exit_code = (
        tool_result.get("exit_code")
        or tool_result.get("exitCode")
        or data.get("exit_code")
        or 0
    )
    stderr = (
        tool_result.get("stderr")
        or tool_result.get("error")
        or data.get("stderr")
        or ""
    )
    # Also check stdout for error patterns
    stdout = tool_result.get("stdout") or tool_result.get("output") or ""
    combined_output = f"{stderr}\n{stdout}"

    return int(exit_code), combined_output

def log_error(pattern: str, stderr: str, auto_fixed: bool, suggestion: str) -> None:
    """Append error to JSONL log."""
    try:
        ERROR_LOG.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "pattern": pattern,
            "stderr_snippet": stderr[:200],
            "auto_fixed": auto_fixed,
            "suggestion": suggestion
        }
        with open(ERROR_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass

def count_recent_pattern(pattern: str, hours: int = 24) -> int:
    """Count occurrences of error pattern in last N hours."""
    if not ERROR_LOG.exists():
        return 0
    cutoff = time.time() - (hours * 3600)
    count = 0
    try:
        with open(ERROR_LOG, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    entry_ts = datetime.fromisoformat(entry.get("ts", "")).timestamp()
                    if entry_ts >= cutoff and entry.get("pattern") == pattern:
                        count += 1
                except Exception:
                    continue
    except Exception:
        pass
    return count

def flag_systemic_pattern(pattern: str) -> None:
    """Add systemic error flag to enforcement queue."""
    try:
        ENFORCEMENT_TODO.parent.mkdir(parents=True, exist_ok=True)
        with open(ENFORCEMENT_TODO, "a", encoding="utf-8") as f:
            f.write(f"\nERROR_PATTERN_SYSTEMIC | pattern={pattern} | Priority: 1\n")
    except Exception:
        pass

def try_auto_fix_pip(module_name: str) -> bool:
    """Attempt to auto-install a missing Python module."""
    if not module_name or not re.match(r'^[a-zA-Z0-9_\-\.]+$', module_name):
        return False  # Safety: only alphanumeric module names
    try:
        result = subprocess.run(
            [PYTHON_EXE, "-m", "pip", "install", module_name],
            capture_output=True, text=True, timeout=60
        )
        return result.returncode == 0
    except Exception:
        return False


def main():
    data = read_input()
    exit_code, stderr = get_error_info(data)

    # No error — nothing to do
    if exit_code == 0 or not stderr.strip():
        sys.exit(0)

    # Pattern registry — ordered by specificity
    pattern = None
    auto_fixed = False
    suggestion = ""
    auto_fix_message = ""

    # ── Pattern 1: Missing Python module ──────────────────────────────────
    m = re.search(r"ModuleNotFoundError: No module named '([a-zA-Z0-9_\-\.]+)'", stderr)
    if m:
        pattern = "ModuleNotFoundError"
        module = m.group(1)
        fixed = try_auto_fix_pip(module)
        if fixed:
            auto_fixed = True
            auto_fix_message = f"\n[AUTO-FIX] Installed missing module: {module}. Re-run the command."
            print(auto_fix_message)
        else:
            suggestion = f"pip install {module}"

    # ── Pattern 2: Rate limit 429 ──────────────────────────────────────────
    elif re.search(r"429|Too Many Requests|rate.?limit", stderr, re.IGNORECASE):
        pattern = "RateLimitError"
        suggestion = "Rate limited. Wait 60s before retry. Consider adding backoff."

    # ── Pattern 3: Connection refused ─────────────────────────────────────
    elif re.search(r"Connection refused|ECONNREFUSED|connect.*refused", stderr, re.IGNORECASE):
        pattern = "ConnectionRefused"
        suggestion = "Service not running or wrong port. Verify target process is up."

    # ── Pattern 4: JSON parse error ──────────────────────────────────────
    elif re.search(r"JSONDecodeError|json.decoder|Expecting value:", stderr, re.IGNORECASE):
        pattern = "JSONDecodeError"
        suggestion = "Response is not valid JSON. Check response encoding or if endpoint returns HTML error page."

    # ── Pattern 5: File not found ─────────────────────────────────────────
    elif re.search(r"No such file or directory|FileNotFoundError|cannot find the path", stderr, re.IGNORECASE):
        pattern = "FileNotFound"
        m2 = re.search(r"'([^']+)'", stderr)
        missing_path = m2.group(1) if m2 else "unknown path"
        suggestion = f"Path not found: {missing_path}. Use Glob to find correct path."

    # ── Pattern 6: Permission denied ─────────────────────────────────────
    elif re.search(r"Permission denied|Access is denied|PermissionError", stderr, re.IGNORECASE):
        pattern = "PermissionDenied"
        suggestion = "ESCALATE: Permission denied — check file/directory ownership or run as appropriate user."

    # ── Pattern 7: Syntax error (non-.py files or runtime) ───────────────
    elif re.search(r"SyntaxError:|IndentationError:", stderr):
        pattern = "PythonSyntaxError"
        suggestion = "Python syntax error in executed script. Check the script file."

    else:
        # Unknown error — just log it
        pattern = "UnknownError"
        suggestion = ""

    # Log the error
    log_error(pattern, stderr, auto_fixed, suggestion)

    # Check for systemic pattern (3+ occurrences in 24h)
    occurrences = count_recent_pattern(pattern)
    if occurrences >= 3:
        flag_systemic_pattern(pattern)
        print(f"\n[ERROR-REMEDIATOR] Systemic pattern detected: {pattern} ({occurrences}x in 24h) — flagged in enforcement queue")

    # Output suggestion to Claude (if not auto-fixed)
    if not auto_fixed and suggestion:
        print(f"\n[ERROR-REMEDIATOR] Pattern: {pattern} | Suggestion: {suggestion}")

    sys.exit(0)  # Never block — always pass through (remediator is advisory)


if __name__ == "__main__":
    main()
