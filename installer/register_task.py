#!/usr/bin/env python3
"""
LeRoy — register_task.py  (mechanism b: opt-in nightly housekeeping)
=======================================================================
Registers/unregisters a Windows Task Scheduler entry that runs
core/scripts/maintenance.py on a nightly schedule. This is mechanism (b) from
item 39 rev — OPT-IN ONLY per WS9. Nothing calls this file automatically;
it is only invoked from `leroy enable scheduled_automations` (via
autonomy.py's wire_feature stub) after the user has explicitly said yes during
`leroy init`'s autonomy menu.

Reversible: `leroy disable scheduled_automations` calls unregister(), which
deletes the task. No orphaned scheduled tasks after disable.

Windows-only (schtasks.exe). On non-Windows this reports "not supported yet"
rather than silently no-op'ing, so `leroy enable` gives honest feedback.

Stdlib only.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import find_user  # noqa: E402

# See installer/doctor.py for why this exists: em-dashes in this file's
# messages (printed here and by autonomy.py's enable/disable wiring) can crash
# print() with UnicodeEncodeError on a strict cp1252 console. Reconfiguring is
# the whole-class fix.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(errors="replace")

TASK_NAME = "LeRoy-Nightly-Maintenance"
DEFAULT_TIME = "02:30"


def register(time_of_day: str = DEFAULT_TIME) -> tuple[bool, str]:
    """Create/replace the nightly Task Scheduler entry. Returns (ok, message)."""
    if not sys.platform.startswith("win"):
        return False, "Scheduled nightly housekeeping isn't wired for this OS yet (Windows-only in this build)."

    paths = find_user.resolve()
    if paths.repo_root is None:
        return False, "Could not locate the LeRoy repo checkout — run this from inside your LeRoy install."

    maint_script = paths.repo_root / "core" / "scripts" / "maintenance.py"
    if not maint_script.exists():
        return False, f"maintenance engine not found at {maint_script}."

    python = sys.executable
    # schtasks needs the full command quoted as one TR argument.
    tr = f'"{python}" "{maint_script}"'
    cmd = [
        "schtasks", "/Create", "/F",
        "/SC", "DAILY",
        "/ST", time_of_day,
        "/TN", TASK_NAME,
        "/TR", tr,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    except (subprocess.SubprocessError, OSError) as e:
        return False, f"schtasks failed to run: {e}"

    if result.returncode != 0:
        return False, f"schtasks reported an error: {result.stderr.strip() or result.stdout.strip()}"
    return True, f"Registered '{TASK_NAME}' to run daily at {time_of_day} (housekeeping only — no push, no tokens)."


def unregister() -> tuple[bool, str]:
    """Delete the scheduled task, if present. Safe to call when it doesn't exist."""
    if not sys.platform.startswith("win"):
        return True, "Nothing to unregister on this OS."

    try:
        result = subprocess.run(
            ["schtasks", "/Delete", "/TN", TASK_NAME, "/F"],
            capture_output=True, text=True, timeout=30,
        )
    except (subprocess.SubprocessError, OSError) as e:
        return False, f"schtasks failed to run: {e}"

    combined = (result.stdout + result.stderr).lower()
    if result.returncode != 0 and "cannot find" not in combined and "does not exist" not in combined:
        return False, f"schtasks reported an error: {result.stderr.strip() or result.stdout.strip()}"
    return True, f"'{TASK_NAME}' is unregistered (or was never registered)."


def is_registered() -> bool:
    if not sys.platform.startswith("win"):
        return False
    try:
        result = subprocess.run(
            ["schtasks", "/Query", "/TN", TASK_NAME],
            capture_output=True, text=True, timeout=15,
        )
        return result.returncode == 0
    except (subprocess.SubprocessError, OSError):
        return False


def main(argv: list[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Register/unregister LeRoy's opt-in nightly housekeeping task")
    parser.add_argument("action", choices=["register", "unregister", "status"])
    parser.add_argument("--time", default=DEFAULT_TIME, help="HH:MM daily run time (default 02:30)")
    args = parser.parse_args(argv)

    if args.action == "status":
        print(f"  {'registered' if is_registered() else 'not registered'}")
        return 0

    ok, msg = register(args.time) if args.action == "register" else unregister()
    print(f"  {msg}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
