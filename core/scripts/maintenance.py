#!/usr/bin/env python3
"""
LeRoy — maintenance.py  (the ONE generalized self-maintenance engine)
=======================================================================
Ported + generalized from the private harness's scripts/nightly-maintenance.ps1
(item 39 / G7 / G12). That script was trimmed to housekeeping-only on 2026-07-01
and hardcoded five values to one machine:
    C:\\Users\\bscot\\.claude
    C:\\Users\\bscot\\.claude\\memory\\Projects\\leroy-pwa-app
    C:\\Users\\bscot\\Backups\\leroy
    RAG port 7742
    scripts\\build-skill-index.py

This file removes every one of those hardcodes by resolving all five through
installer/find_user.py (the WS4.1 shared user-finding protocol), so it runs
correctly on ANY user's machine.

What it does (identical to the source script, just generalized):
  1. State snapshot: zip a read-only copy of session/boardroom-ish state +
     uncommitted-work patches into backup_dest. No git push, no git commit.
  2. Janitor: prune snapshots older than 14 days, prune backend log litter
     older than 7 days, cap this script's own log at ~1MB.
  3. RAG sidecar reindex: POST /reindex on the resolved rag_port (best-effort;
     a down sidecar is a WARN, not a failure).
  4. Skill-index rebuild: run the resolved skill_index_script, if one exists.

What it NEVER does (the guarantee this script inherits and must keep):
  No `git push`, no `git commit`, no publish/whitehat scan, no PR. This is
  housekeeping only. If you're tempted to add a push step here — don't; put it
  in a separate, explicitly-invoked, explicitly-consented flow instead.

Two invocation mechanisms call this same engine (item 39 rev):
  (a) `leroy backup` piggybacks a call to this script after a successful
      backup — event-driven off a user action, no extra consent needed (WS9).
  (b) An opt-in Task Scheduler entry (Windows) registered only when the user
      says yes during `leroy init`'s autonomy menu — see register_task.py.

Stdlib only. PowerShell 5.1 environments can still shell out to `python
core/scripts/maintenance.py` — no dependency on this being run from a
Python-aware terminal.

Usage:
    python core/scripts/maintenance.py                 # run for real
    python core/scripts/maintenance.py --dry-run        # touch nothing, print the plan
    python core/scripts/maintenance.py --skip-snapshot   # e.g. called right after `leroy backup` already snapshotted
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "installer"))
import find_user  # noqa: E402  (path bootstrap must precede this import)

# See installer/doctor.py for why this exists: a glyph-probe fallback alone
# can miss a non-ASCII character that only appears later in the file,
# crashing print()/log() on a strict cp1252 console. Reconfiguring is the
# whole-class fix — this script's log output is user-facing on every backup.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(errors="replace")

_UTF_OK = True
try:
    "✅⚠️".encode(sys.stdout.encoding or "utf-8")
except (UnicodeEncodeError, LookupError):
    _UTF_OK = False

OK = "✅" if _UTF_OK else "[ OK ]"
WARN = "⚠️ " if _UTF_OK else "[warn]"


class Logger:
    """Mirrors the source script's Log() helper: timestamped, tees to a file."""

    def __init__(self, log_file: Path, dry_run: bool):
        self.log_file = log_file
        self.dry_run = dry_run
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

    def __call__(self, msg: str) -> None:
        line = f"{_dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} {msg}"
        print(line)
        if not self.dry_run:
            with self.log_file.open("a", encoding="utf-8") as f:
                f.write(line + "\n")


# --- 1. state snapshot -------------------------------------------------------
def snapshot(paths: find_user.UserPaths, log: Logger, dry_run: bool) -> None:
    stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M")
    claude = paths.claude_home
    pwa = paths.app_dir  # the packaged app, if any, replaces the hardcoded pwa path

    # Same target set as the source script, generalized: any target that
    # doesn't exist on this user's machine is a soft WARN, not a failure —
    # not every install has an app dir or a boardroom session folder.
    targets = [
        ("backend-data", (pwa / "backend" / "data") if pwa else None),
        ("boardroom", claude / "session" / "boardroom"),
        ("session-state", claude / "session" / "state.json"),
        ("auth-config", (pwa / "backend" / "auth_config.json") if pwa else None),
    ]

    if dry_run:
        for name, src in targets:
            if src is None:
                log(f"[dry-run] skip {name} (no packaged app dir found)")
            elif src.exists():
                log(f"[dry-run] would snapshot: {name} <- {src}")
            else:
                log(f"WARN: missing target {src}")
        log(f"[dry-run] would write zip to: {paths.backup_dest / f'leroy-state-{stamp}.zip'}")
        return

    staging = Path.home() / ".leroy-maint-staging" / f"leroy-maint-{stamp}"
    staging.mkdir(parents=True, exist_ok=True)
    try:
        for name, src in targets:
            if src is None:
                continue
            if not src.exists():
                log(f"WARN: missing target {src}")
                continue
            dest = staging / name
            if src.is_dir():
                shutil.copytree(
                    src,
                    dest,
                    ignore=shutil.ignore_patterns(
                        "worktrees", "portraits", "_scratch-merge-test", "node_modules", "__pycache__"
                    ),
                    dirs_exist_ok=True,
                )
            else:
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dest.with_suffix(src.suffix))

        # Uncommitted work captured as read-only patches — never pushed.
        if paths.repo_root is not None:
            _write_git_snapshot(paths.repo_root, staging, "claude")
        if pwa is not None:
            _write_git_snapshot(pwa, staging, "pwa")

        find_user.ensure_backup_dest(paths)
        zip_path = paths.backup_dest / f"leroy-state-{stamp}.zip"
        base = str(zip_path.with_suffix(""))
        shutil.make_archive(base, "zip", root_dir=staging)
        size_mb = round(zip_path.stat().st_size / (1024 * 1024), 1)
        log(f"snapshot OK: {zip_path} ({size_mb}MB)")
    except OSError as e:
        log(f"ERROR: snapshot failed: {e}")
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def _write_git_snapshot(repo: Path, staging: Path, label: str) -> None:
    """git diff/log captured read-only — mirrors the source script exactly."""
    try:
        diff = subprocess.run(
            ["git", "-C", str(repo), "diff", "HEAD"],
            capture_output=True, text=True, timeout=30,
        ).stdout
        (staging / f"{label}-dirty.patch").write_text(diff, encoding="utf-8")
        head = subprocess.run(
            ["git", "-C", str(repo), "log", "--oneline", "-5"],
            capture_output=True, text=True, timeout=15,
        ).stdout
        (staging / f"{label}-head.txt").write_text(head, encoding="utf-8")
    except (subprocess.SubprocessError, OSError):
        pass  # best-effort, matches source script's `2>$null` swallow


# --- 2. janitor ---------------------------------------------------------------
def janitor(paths: find_user.UserPaths, log: Logger, dry_run: bool) -> None:
    now = _dt.datetime.now()

    # Prune snapshots older than 14 days.
    if paths.backup_dest.exists():
        for f in paths.backup_dest.glob("leroy-state-*.zip"):
            age_days = (now - _dt.datetime.fromtimestamp(f.stat().st_mtime)).days
            if age_days > 14:
                log(f"{'[dry-run] would prune' if dry_run else 'prune snapshot:'} {f.name}")
                if not dry_run:
                    f.unlink(missing_ok=True)

    # Prune backend log litter older than 7 days (be-*.log / uvicorn-*.log).
    if paths.app_dir is not None:
        backend = paths.app_dir / "backend"
        if backend.exists():
            for f in list(backend.glob("be-*.log")) + list(backend.glob("uvicorn-*.log")):
                age_days = (now - _dt.datetime.fromtimestamp(f.stat().st_mtime)).days
                if age_days > 7:
                    log(f"{'[dry-run] would prune log:' if dry_run else 'prune log:'} {f.name}")
                    if not dry_run:
                        f.unlink(missing_ok=True)

    # Cap our own log at ~1MB (tail 500 lines) — skip during dry-run.
    log_file = paths.backup_dest / "nightly-maintenance.log"
    if not dry_run and log_file.exists() and log_file.stat().st_size > 1_000_000:
        lines = log_file.read_text(encoding="utf-8", errors="replace").splitlines()[-500:]
        log_file.write_text("\n".join(lines) + "\n", encoding="utf-8")


# --- 3. RAG sidecar reindex ---------------------------------------------------
def rag_reindex(paths: find_user.UserPaths, log: Logger, dry_run: bool) -> None:
    if dry_run:
        log(f"[dry-run] would: POST http://localhost:{paths.rag_port}/reindex {{full:false}}")
        return
    url = f"http://localhost:{paths.rag_port}/reindex"
    body = json.dumps({"full": False}).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            log(f"rag reindex: {data.get('status', 'ok')}")
    except (urllib.error.URLError, OSError, ValueError) as e:
        log(f"WARN: rag reindex failed (sidecar down on port {paths.rag_port}?): {e}")


# --- 4. skill-index rebuild ---------------------------------------------------
def skill_index(paths: find_user.UserPaths, log: Logger, dry_run: bool) -> None:
    if paths.skill_index_script is None:
        log("WARN: no skill-index script found — skipping (not fatal)")
        return
    if dry_run:
        log(f"[dry-run] would run: python {paths.skill_index_script}")
        return
    try:
        result = subprocess.run(
            [sys.executable, str(paths.skill_index_script)],
            capture_output=True, text=True, timeout=120,
        )
        last_line = (result.stdout or result.stderr or "").strip().splitlines()
        log(f"skill-index: {last_line[-1] if last_line else '(no output)'}")
    except (subprocess.SubprocessError, OSError) as e:
        log(f"WARN: skill-index rebuild failed: {e}")


# --- orchestration -------------------------------------------------------------
def run(dry_run: bool, skip_snapshot: bool) -> int:
    paths = find_user.resolve()
    log_file = paths.backup_dest / "nightly-maintenance.log"
    log = Logger(log_file, dry_run)

    log("=== leroy maintenance start ===")
    log(f"resolved paths: claude_home={paths.claude_home} repo_root={paths.repo_root} "
        f"app_dir={paths.app_dir} backup_dest={paths.backup_dest} rag_port={paths.rag_port}")

    if skip_snapshot:
        log("snapshot: skipped (--skip-snapshot — caller already took one, e.g. `leroy backup`)")
    else:
        snapshot(paths, log, dry_run)

    janitor(paths, log, dry_run)
    rag_reindex(paths, log, dry_run)
    skill_index(paths, log, dry_run)

    log("=== leroy maintenance done ===")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="LeRoy generalized self-maintenance engine")
    parser.add_argument("--dry-run", action="store_true", help="print the plan, write/call nothing")
    parser.add_argument("--skip-snapshot", action="store_true",
                         help="skip the state-snapshot step (used when a caller like `leroy backup` already took one)")
    args = parser.parse_args(argv)
    return run(dry_run=args.dry_run, skip_snapshot=args.skip_snapshot)


if __name__ == "__main__":
    raise SystemExit(main())
