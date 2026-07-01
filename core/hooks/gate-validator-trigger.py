#!/usr/bin/env python3
"""
Gate Validator Trigger v2.0
Stop hook: spawns response-monitor.py + auto-dispatches Priority-2 enforcement queue.

Performance: <100ms (non-blocking spawns)
Triggered: On agent Stop event
v2.0: Added auto_dispatch_background_queue() for P2 enforcement items

GRACEFUL DEGRADE: every helper script it spawns (response-monitor.py,
consolidate_memory.py, agent-feedback-collector.py) is optional — if the script
is absent the corresponding step is skipped silently. The hook never blocks.
"""

import json
import sys
import io
import subprocess
from pathlib import Path
import datetime

# Force UTF-8 encoding for stdin (Unicode encoding fix v1.1)
if sys.stdin.encoding != 'utf-8':
    sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8', errors='replace')


def parse_input() -> dict:
    """Parse JSON input from stdin."""
    try:
        input_data = sys.stdin.read()
        return json.loads(input_data)
    except json.JSONDecodeError:
        return {}


def get_transcript_path(hook_data: dict) -> str:
    """
    Extract transcript path from Stop hook data.

    Stop hook provides:
    {
      "transcript_path": "/path/to/conversation.jsonl",
      "agent_id": "...",
      ...
    }
    """
    return hook_data.get("transcript_path", "")


def spawn_validator(transcript_path: str) -> bool:
    """
    Spawn response-monitor.py in background (non-blocking).

    Uses Popen with detachment to avoid blocking hook execution.
    Returns immediately (<50ms).

    Returns:
        True if spawned successfully, False otherwise
    """
    # Derive paths
    claude_root = Path.home() / ".claude"
    monitor_script = claude_root / "scripts" / "response-monitor.py"

    if not monitor_script.exists():
        # Optional helper not present — skip silently (graceful degrade).
        return False

    if not transcript_path or not Path(transcript_path).exists():
        return False

    try:
        # Spawn detached background process
        # - start_new_session=True detaches from hook process
        # - stdout/stderr to DEVNULL prevents pipe blocking
        # - Returns immediately (<10ms)
        subprocess.Popen(
            [sys.executable, str(monitor_script), transcript_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,  # Detach from parent
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
        )

        return True

    except Exception as e:
        print(f"[ERROR] Failed to spawn validator: {e}", file=sys.stderr)
        return False


def auto_dispatch_background_queue():
    """
    Auto-dispatch Priority-2 enforcement queue items on session stop.
    Only dispatches safe, background-only items (P0/P1 remain manual).

    Actions handled:
    - CONSOLIDATE_MEMORY: runs consolidate_memory.py as subprocess
    - SEND_MEMORY_NOTIFICATION_EMAIL: writes deferred-email-trigger.json for next session
    """
    claude_root = Path.home() / ".claude"
    enforcement_todo = claude_root / "session" / "enforcement.todo"

    if not enforcement_todo.exists():
        return  # No queue — nothing to dispatch

    try:
        content = enforcement_todo.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return

    # Only process Priority-2 (background) items — never auto-fire P0/P1
    if "Priority: 2" not in content:
        return

    dispatched = []

    # Action 1: CONSOLIDATE_MEMORY — safe to run as subprocess at session end
    if "CONSOLIDATE_MEMORY" in content:
        consolidate_script = claude_root / "scripts" / "consolidate_memory.py"
        if consolidate_script.exists():
            try:
                subprocess.Popen(
                    [sys.executable, str(consolidate_script)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
                )
                dispatched.append("CONSOLIDATE_MEMORY")
            except Exception:
                pass

    # Action 2: SEND_MEMORY_NOTIFICATION_EMAIL — write deferred trigger for next session
    if "SEND_MEMORY_NOTIFICATION_EMAIL" in content:
        pending_email = claude_root / "session" / "pending-email-request.json"
        if pending_email.exists():
            deferred_trigger = claude_root / "session" / "deferred-email-trigger.json"
            try:
                # Move pending email to deferred — gate-enforcer picks it up next session
                import shutil
                shutil.copy2(str(pending_email), str(deferred_trigger))
                pending_email.unlink()  # Remove original to prevent re-queue
                dispatched.append("SEND_MEMORY_NOTIFICATION_EMAIL")
            except Exception:
                pass

    # Log dispatch activity
    if dispatched:
        log_entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "event": "auto_dispatch_background_queue",
            "dispatched": dispatched,
            "component": "gate-validator-trigger"
        }
        log_file = claude_root / "session" / "dispatch-log.jsonl"
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry) + "\n")
        except Exception:
            pass


def collect_agent_feedback() -> None:
    """
    Call agent-feedback-collector.py to validate agent output quality.
    Runs synchronously with a 5s timeout — lightweight validation only.
    Writes quality signals to session/agent-feedback.jsonl.
    Optional helper — skipped silently if not present.
    """
    claude_root = Path.home() / ".claude"
    collector_script = claude_root / "scripts" / "agent-feedback-collector.py"

    if not collector_script.exists():
        return  # Script not deployed — skip silently

    try:
        subprocess.run(
            [sys.executable, str(collector_script)],
            capture_output=True,
            text=True,
            timeout=5
        )
    except Exception:
        pass  # Never block Stop hook on collector failure


def main():
    """
    Stop hook entry point.

    Critical requirement: Complete in <100ms to avoid UX degradation.
    """
    # Parse input (~2ms)
    hook_data = parse_input()

    # Extract transcript path (<1ms)
    transcript_path = get_transcript_path(hook_data)

    if not transcript_path:
        # No transcript path = not an agent stop we care about
        # Still run background queue dispatch (enforcement.todo may exist)
        auto_dispatch_background_queue()
        collect_agent_feedback()
        sys.exit(0)

    # Spawn validator in background (~10ms)
    spawn_validator(transcript_path)

    # Auto-dispatch Priority-2 enforcement queue items (~15ms)
    auto_dispatch_background_queue()

    # Validate agent output quality (~5ms, synchronous with timeout)
    collect_agent_feedback()

    # Hook completes here (<100ms total)
    sys.exit(0)  # Always exit 0 (don't block on errors)


if __name__ == "__main__":
    main()
