#!/usr/bin/env python3
"""
LeRoy — doctor.py
=================
Preflight prerequisite checker for the LeRoy installer and `leroy doctor`.

Checks the four hard prerequisites (Claude Code, Node >= 18, Python >= 3.11, git)
and prints a clean PASS / FAIL list with a concrete "how to fix" line for every
miss. No cryptic failures — every red line tells you exactly what to do next.

Exit code is 0 when every REQUIRED check passes, 1 otherwise, so `setup` can
gate on it.

This file is intentionally dependency-free (stdlib only) so it runs on a fresh
machine before any pip install has happened.
"""

from __future__ import annotations

import platform
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field

# Some Windows consoles are strict cp1252, not UTF-8. The _UTF_OK glyph probe
# below only tests the glyphs it's given — any OTHER non-ASCII character used
# later in the file (e.g. the U+21B3 arrow in a fix hint) can still slip past
# it and crash with UnicodeEncodeError on print(). Reconfiguring stdout/stderr
# to replace-on-error is a whole-class fix: any glyph degrades to '?' instead
# of throwing, for every string, forever — belt-and-suspenders with _UTF_OK
# below (which still picks the nicer ASCII fallback marks when it can).
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(errors="replace")

# --- pretty output ----------------------------------------------------------
# Fall back to ASCII marks if the terminal can't render check/cross glyphs.
_UTF_OK = True
try:
    "✅❌⚠️".encode(sys.stdout.encoding or "utf-8")
except (UnicodeEncodeError, LookupError):
    _UTF_OK = False

OK = "✅" if _UTF_OK else "[ OK ]"
BAD = "❌" if _UTF_OK else "[FAIL]"
WARN = "⚠️ " if _UTF_OK else "[warn]"


@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str = ""          # e.g. the version we found
    fix: str = ""             # how to fix it if it failed
    required: bool = True     # required checks gate the exit code


@dataclass
class DoctorReport:
    results: list[CheckResult] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        """True only if every *required* check passed."""
        return all(r.passed for r in self.results if r.required)


# --- helpers ----------------------------------------------------------------
def _run(cmd: list[str]) -> str | None:
    """Run a command, return stdout (stripped) or None if it can't run."""
    exe = shutil.which(cmd[0])
    if not exe:
        return None
    try:
        out = subprocess.run(
            [exe, *cmd[1:]],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (subprocess.SubprocessError, OSError):
        return None
    # Some tools (node) print version to stdout; others may use stderr.
    return (out.stdout or out.stderr or "").strip()


def _parse_semver(text: str) -> tuple[int, int, int] | None:
    m = re.search(r"(\d+)\.(\d+)(?:\.(\d+))?", text or "")
    if not m:
        return None
    return (int(m.group(1)), int(m.group(2)), int(m.group(3) or 0))


# --- individual checks ------------------------------------------------------
def check_python() -> CheckResult:
    v = sys.version_info
    passed = (v.major, v.minor) >= (3, 11)
    return CheckResult(
        name="Python >= 3.11",
        passed=passed,
        detail=f"found {v.major}.{v.minor}.{v.micro}",
        fix="Install Python 3.11+ from https://www.python.org/downloads/ "
        "(on Windows, check 'Add python.exe to PATH').",
    )


def check_node() -> CheckResult:
    raw = _run(["node", "--version"])
    ver = _parse_semver(raw) if raw else None
    passed = ver is not None and ver[0] >= 18
    detail = f"found {raw}" if raw else "not found on PATH"
    return CheckResult(
        name="Node.js >= 18",
        passed=passed,
        detail=detail,
        fix="Install Node 18 LTS or newer from https://nodejs.org/ "
        "(or `nvm install --lts`). Needed by the desktop app + some MCPs.",
        # Node is only strictly needed for the desktop app / some MCPs, but the
        # spec lists it as a preflight check, so we keep it required.
        required=True,
    )


def check_git() -> CheckResult:
    raw = _run(["git", "--version"])
    passed = raw is not None
    return CheckResult(
        name="git",
        passed=passed,
        detail=(f"found {raw}" if raw else "not found on PATH"),
        fix="Install git from https://git-scm.com/downloads "
        "(needed for `leroy update` and self-heal).",
    )


def check_claude_code() -> CheckResult:
    """
    Claude Code ships as the `claude` CLI. We look for it on PATH first, then
    fall back to a version probe. If it isn't found we FAIL with the installer
    link, because LeRoy is an overlay ON TOP of Claude Code — it can't run
    without it.
    """
    exe = shutil.which("claude")
    raw = _run(["claude", "--version"]) if exe else None
    passed = exe is not None
    if passed:
        detail = f"found {raw}" if raw else f"found at {exe}"
    else:
        detail = "not found on PATH"
    return CheckResult(
        name="Claude Code CLI (`claude`)",
        passed=passed,
        detail=detail,
        fix="Install Claude Code: https://claude.com/claude-code "
        "then re-run. LeRoy layers on top of it.",
    )


def run_all() -> DoctorReport:
    """Run every check and return the collected report."""
    report = DoctorReport()
    report.results.extend(
        [
            check_claude_code(),
            check_node(),
            check_python(),
            check_git(),
        ]
    )
    return report


# --- rendering --------------------------------------------------------------
def print_report(report: DoctorReport) -> None:
    print()
    dash = "—" if _UTF_OK else "-"
    print(f"  LeRoy doctor {dash} prerequisite check")
    print(f"  ({platform.system()} {platform.release()}, {platform.machine()})")
    print("  " + "-" * 46)
    for r in report.results:
        mark = OK if r.passed else BAD
        print(f"  {mark}  {r.name:<26} {r.detail}")
        if not r.passed and r.fix:
            print(f"       ↳ fix: {r.fix}")
    print("  " + "-" * 46)
    if report.ok:
        print(f"  {OK}  All prerequisites satisfied. You're good to go.\n")
    else:
        missing = [r.name for r in report.results if r.required and not r.passed]
        print(f"  {BAD}  Missing: {', '.join(missing)}")
        print("       Fix the items above, then re-run.\n")


def main(argv: list[str] | None = None) -> int:
    import argparse
    from pathlib import Path

    parser = argparse.ArgumentParser(description="LeRoy doctor: prereq check, or --upgrade for an existing-install scan")
    parser.add_argument("--upgrade", action="store_true",
                         help="scan an existing ~/.claude vs the shipped core/ and report what's stale/new (WS3 G4)")
    parser.add_argument("--existing", type=Path, default=None, help="with --upgrade: existing ~/.claude to inventory")
    parser.add_argument("--from-archive", type=Path, default=None,
                         help="with --upgrade: a .zip/.tar(.gz) of an existing install instead of a live dir")
    args = parser.parse_args(argv)

    report = run_all()
    print_report(report)
    rc = 0 if report.ok else 1

    if args.upgrade:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import inventory
        inv_argv = []
        if args.existing:
            inv_argv += ["--existing", str(args.existing)]
        if args.from_archive:
            inv_argv += ["--from-archive", str(args.from_archive)]
        inventory.main(inv_argv)

    return rc


if __name__ == "__main__":
    raise SystemExit(main())
