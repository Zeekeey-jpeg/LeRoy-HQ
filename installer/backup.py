#!/usr/bin/env python3
"""
LeRoy — backup.py  (`leroy backup` — G11)
============================================
Generic private-repo backup for the PUBLIC product. This is NOT Brian's
private doomsday-backup skill (that pushes to his own GitHub, hardcodes his
paths, and mirrors his memory vault — none of that ships here). This is the
user's own backup, to a remote THEY configure (via the optional GitHub
walkthrough offered in `leroy init` — G6), or to a local zip if they haven't
set one up yet.

Two things happen when a user runs `leroy backup`:
  1. The backup itself:
       - if the user has a configured git remote (config/backup.json ->
         "remote_url"), commit + push their ~/.claude tree to it.
       - otherwise, fall back to a local timestamped zip snapshot so
         `leroy backup` always does *something* useful, never a hard error.
  2. The maintenance piggyback (mechanism a, item 39): on a SUCCESSFUL backup,
     automatically call core/scripts/maintenance.py --skip-snapshot (it just
     took its own snapshot as step 1, no need to double it). This is
     event-driven off the user's own action, so WS9 does not require a
     separate consent prompt — it's part of the `backup` command they invoked,
     and it's housekeeping-only (no push, no token spend).

Vault-deletion safeguard (reused from the private harness's
backup-reminder.md pattern): before pushing, count how many files under
memory/ would be DELETED by this push (i.e. tracked in the last commit but
missing locally). 1-5 deleted files -> warn and ask to confirm. >5 -> block
outright and tell the user to investigate, so a generic user can't silently
nuke their memory vault with a bad push.

Stdlib only.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import find_user  # noqa: E402

# See doctor.py for why this exists: a glyph-probe fallback alone can miss a
# non-ASCII character that only appears later in the file, crashing print()
# on a strict cp1252 console. Reconfiguring is the whole-class fix.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(errors="replace")

_UTF_OK = True
try:
    "✅⚠️🔴".encode(sys.stdout.encoding or "utf-8")
except (UnicodeEncodeError, LookupError):
    _UTF_OK = False

OK = "✅" if _UTF_OK else "[ OK ]"
WARN = "⚠️ " if _UTF_OK else "[warn]"
BLOCK = "🔴" if _UTF_OK else "[BLOCKED]"

VAULT_WARN_THRESHOLD = 1
VAULT_BLOCK_THRESHOLD = 5


def _backup_config_path(claude_home: Path) -> Path:
    return claude_home / "config" / "backup.json"


def load_backup_config(claude_home: Path) -> dict:
    path = _backup_config_path(claude_home)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _count_vault_deletions(claude_home: Path) -> int:
    """
    How many memory/*.md files does the last commit have that don't exist on
    disk right now? A large number here usually means something clobbered the
    vault (bad merge, accidental rm -rf) rather than genuine intentional
    deletes, so we use it as a safety trip-wire before pushing.
    """
    try:
        result = subprocess.run(
            ["git", "-C", str(claude_home), "ls-tree", "-r", "--name-only", "HEAD", "memory"],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            return 0  # no commits yet / not a repo — nothing to compare against
        tracked = [line for line in result.stdout.splitlines() if line.strip()]
    except (subprocess.SubprocessError, OSError):
        return 0

    missing = sum(1 for rel in tracked if not (claude_home / rel).exists())
    return missing


def _git_push(claude_home: Path, remote_url: str, log) -> bool:
    """Commit + push ~/.claude to the user's configured remote. Returns success."""
    try:
        subprocess.run(["git", "-C", str(claude_home), "add", "-A"],
                        capture_output=True, text=True, timeout=60, check=True)
        stamp = _dt.datetime.now().strftime("%Y-%m-%d %H:%M")
        commit = subprocess.run(
            ["git", "-C", str(claude_home), "commit", "-m", f"LeRoy backup - {stamp}"],
            capture_output=True, text=True, timeout=60,
        )
        if commit.returncode != 0 and "nothing to commit" not in (commit.stdout + commit.stderr).lower():
            log(f"{WARN} commit reported an issue: {commit.stderr.strip()[:200]}")
        push = subprocess.run(
            ["git", "-C", str(claude_home), "push", remote_url, "HEAD"],
            capture_output=True, text=True, timeout=180,
        )
        if push.returncode != 0:
            log(f"{WARN} push failed: {push.stderr.strip()[:300]}")
            return False
        log(f"{OK} pushed to your private backup remote.")
        return True
    except (subprocess.SubprocessError, OSError) as e:
        log(f"{WARN} git backup failed: {e}")
        return False


def _local_zip_fallback(claude_home: Path, backup_dest: Path, log) -> bool:
    """No remote configured yet — zip the vault locally so backup still does something."""
    backup_dest.mkdir(parents=True, exist_ok=True)
    stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    base = str(backup_dest / f"leroy-backup-{stamp}")
    try:
        shutil.make_archive(base, "zip", root_dir=str(claude_home))
        log(f"{OK} No private remote configured yet — saved a local backup instead:")
        log(f"    {base}.zip")
        log("    Run 'leroy init' again (or the wizard's backup walkthrough) to set up a private GitHub remote.")
        return True
    except OSError as e:
        log(f"{WARN} local backup zip failed: {e}")
        return False


def run(dry_run: bool = False) -> int:
    def log(msg: str) -> None:
        print(f"  {msg}")

    paths = find_user.resolve()
    claude_home = paths.claude_home

    if not claude_home.exists():
        log(f"{WARN} No ~/.claude found at {claude_home} — nothing to back up.")
        return 1

    deletions = _count_vault_deletions(claude_home)
    if deletions > VAULT_BLOCK_THRESHOLD:
        log(f"{BLOCK} {deletions} memory files are tracked but missing locally.")
        log("    This looks like vault data loss, not an intentional cleanup.")
        log("    Backup BLOCKED — investigate before pushing (this safeguard protects your vault).")
        return 1
    elif deletions >= VAULT_WARN_THRESHOLD:
        log(f"{WARN} {deletions} memory file(s) are tracked but missing locally.")
        if dry_run:
            log("    [dry-run] would prompt to confirm before proceeding.")
        else:
            confirm = input(f"    Continue the backup anyway? Type 'yes' to proceed: ").strip().lower()
            if confirm != "yes":
                log("Aborted.")
                return 1

    cfg = load_backup_config(claude_home)
    remote_url = cfg.get("remote_url")

    if dry_run:
        if remote_url:
            log(f"[dry-run] would commit + push {claude_home} -> {remote_url}")
        else:
            log(f"[dry-run] would zip {claude_home} -> {paths.backup_dest} (no remote configured)")
        log("[dry-run] would then piggyback: core/scripts/maintenance.py --skip-snapshot")
        return 0

    if remote_url:
        success = _git_push(claude_home, remote_url, log)
    else:
        success = _local_zip_fallback(claude_home, paths.backup_dest, log)

    if not success:
        log(f"{WARN} Backup did not complete — skipping the maintenance piggyback.")
        return 1

    # --- mechanism (a): piggyback maintenance on a SUCCESSFUL backup --------
    log("Backup complete — running housekeeping (log prune, RAG reindex, skill index)...")
    maint_script = None
    if paths.repo_root is not None:
        candidate = paths.repo_root / "core" / "scripts" / "maintenance.py"
        if candidate.exists():
            maint_script = candidate
    if maint_script is None:
        log(f"{WARN} maintenance engine not found (repo checkout not located) — skipping housekeeping this time.")
        return 0

    try:
        result = subprocess.run(
            [sys.executable, str(maint_script), "--skip-snapshot"],
            capture_output=True, text=True, timeout=180,
        )
        for line in (result.stdout or "").splitlines()[-6:]:
            log(line)
        if result.returncode != 0:
            log(f"{WARN} maintenance engine exited non-zero ({result.returncode}) — backup itself still succeeded.")
    except (subprocess.SubprocessError, OSError) as e:
        log(f"{WARN} could not run maintenance engine: {e}")

    log(f"{OK} leroy backup complete.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="LeRoy backup (+ automatic housekeeping piggyback)")
    parser.add_argument("--dry-run", action="store_true", help="show what would happen, touch nothing")
    args = parser.parse_args(argv)
    return run(dry_run=args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
