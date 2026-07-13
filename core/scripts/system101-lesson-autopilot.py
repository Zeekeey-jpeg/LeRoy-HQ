"""
System 101 Daily Lesson Autopilot — 9 AM launcher.

Fires the System 101 daily-lesson skill (skills/routines/system-101-daily-lesson.md)
via a fresh headless Claude Code run, so the send always goes through a clean MCP
connection (long-lived sessions can silently drop the google-YourCo Gmail MCP and fall
back to an unguarded MCP path — see memory/Feedback/feedback_stale_session_outbound_enforcement_gap.md).

Run modes:
  python system101-lesson-autopilot.py --check    # dry run: print decision + reason
  python system101-lesson-autopilot.py --run      # execute if guard passes

Kill switch: create  C:/Users/bscot/.claude/session/system101-lesson-autopilot.disabled
to suppress all runs until the file is removed.

Idempotency: if today's date already appears as date_covered on the most recently
covered topic in progress.json, skip — a lesson already went out today.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

CLAUDE_ROOT = Path(os.environ.get("LEROY_CLAUDE_ROOT") or (Path.home() / ".claude"))
SESSION_DIR = CLAUDE_ROOT / "session"
PROGRESS_JSON = CLAUDE_ROOT / "memory" / "Projects" / "System-101-Training" / "progress.json"
KILL_SWITCH_FILE = "system101-lesson-autopilot.disabled"
LOG_FILE = "system101-lesson-autopilot.log"

LESSON_PROMPT = (
    "Run the System 101 daily lesson per "
    "skills/routines/system-101-daily-lesson.md"
)


def _resolve_claude_exe() -> Path:
    env = (os.environ.get("LEROY_CLAUDE_EXE") or "").strip()
    if env:
        return Path(env)
    found = shutil.which("claude") or shutil.which("claude.cmd")
    if found:
        return Path(found)
    # Common npm-global fallback on this machine's profile
    return Path.home() / "AppData" / "Roaming" / "npm" / "claude.cmd"


CLAUDE_EXE = _resolve_claude_exe()


def is_kill_switch_on(session_dir: Path = SESSION_DIR) -> bool:
    return (session_dir / KILL_SWITCH_FILE).exists()


def already_sent_today(progress_path: Path = PROGRESS_JSON) -> bool:
    """True if the most recently covered topic's date_covered is today."""
    try:
        data = json.loads(progress_path.read_text(encoding="utf-8"))
    except Exception:
        return False

    covered = [t for t in data.get("topics", []) if t.get("status") == "covered" and t.get("date_covered")]
    if not covered:
        return False

    latest = max(covered, key=lambda t: t["date_covered"])
    return latest["date_covered"] == date.today().isoformat()


def should_run_autopilot(session_dir: Path = SESSION_DIR) -> tuple[bool, str]:
    if is_kill_switch_on(session_dir):
        kill_path = session_dir / KILL_SWITCH_FILE
        return False, f"kill switch active — remove {kill_path} to re-enable"

    if already_sent_today():
        return False, "already sent today — skipping duplicate run"

    return True, "guard clear — launching System 101 daily lesson"


def _append_log(session_dir: Path, message: str) -> None:
    log_file = session_dir / LOG_FILE
    now = datetime.now().isoformat(timespec="seconds")
    try:
        with log_file.open("a", encoding="utf-8") as fh:
            fh.write(f"{now}  {message}\n")
    except OSError:
        pass


def run_autopilot(
    session_dir: Path = SESSION_DIR,
    claude_root: Path = CLAUDE_ROOT,
    claude_exe: Path = CLAUDE_EXE,
    dry_run: bool = False,
) -> int:
    should_run, reason = should_run_autopilot(session_dir)
    _append_log(session_dir, f"[{'DRY' if dry_run else 'RUN'}] {reason}")

    if not should_run:
        print(f"SKIP: {reason}")
        return 0

    print(f"RUN: {reason}")
    if dry_run:
        print("(dry run — not invoking claude)")
        return 0

    exe = claude_exe if claude_exe.exists() else Path("claude")
    cmd = [str(exe), "-p", LESSON_PROMPT, "--output-format", "text"]
    _append_log(session_dir, f"LAUNCH: {' '.join(cmd)}")

    try:
        result = subprocess.run(
            cmd,
            cwd=str(claude_root),
            capture_output=True,
            text=True,
            timeout=900,
        )
        _append_log(session_dir, f"EXIT {result.returncode}")
        if result.stdout:
            _append_log(session_dir, f"STDOUT: {result.stdout[:500]}")
        if result.returncode != 0:
            _append_log(session_dir, f"STDERR: {result.stderr[:500]}")
        return result.returncode
    except subprocess.TimeoutExpired:
        _append_log(session_dir, "TIMEOUT after 900s")
        return 1
    except Exception as exc:
        _append_log(session_dir, f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="System 101 Daily Lesson Autopilot launcher")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true", help="Dry run — print decision, do not launch")
    group.add_argument("--run", action="store_true", help="Run autopilot if guard passes")
    args = parser.parse_args()
    sys.exit(run_autopilot(dry_run=args.check))
