#!/usr/bin/env python3
"""
LeRoy — find_user.py
=====================
WS4.1 shared user-finding protocol: locates a user's LeRoy install pieces
generically, with zero hardcoded paths (no `C:\\Users\\<you>`, no personal
machine assumptions). Every installer/maintenance script that needs "where is
this user's stuff" should import this module instead of re-deriving paths.

Resolves, in order of reliability:
  - claude_home     : ~/.claude  (or $LEROY_CLAUDE_HOME override)
  - repo_root       : the LeRoy git checkout (walks up from this file; falls
                       back to $LEROY_REPO_ROOT, then a few common install dirs)
  - app_dir         : the packaged desktop app, if one exists under repo/app
  - backup_dest     : where `leroy backup` / maintenance snapshots should land
                       (default: ~/LeRoy-Backups; override via config or env)
  - rag_port        : the RAG sidecar's port (default 7742; override via
                       config/rag.json or $LEROY_RAG_PORT)
  - skill_index_script : path to the skill-index rebuild script, if present

All resolution is read-only (no writes) except `ensure_backup_dest`, which
only creates the destination directory when explicitly asked.

Stdlib only.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path

# print_report() below uses a raw em-dash with no ASCII fallback — on a strict
# cp1252 console (common on plain Windows terminals) that crashes with
# UnicodeEncodeError instead of printing the report. Reconfiguring stdout to
# replace-on-error is a whole-class fix (see installer/doctor.py for the fuller
# rationale): any non-ASCII glyph degrades to '?' instead of throwing.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(errors="replace")


@dataclass
class UserPaths:
    claude_home: Path
    repo_root: Path | None
    app_dir: Path | None
    backup_dest: Path
    rag_port: int
    skill_index_script: Path | None


def find_claude_home() -> Path:
    """~/.claude, or $LEROY_CLAUDE_HOME if the user relocated it."""
    override = os.environ.get("LEROY_CLAUDE_HOME")
    if override:
        return Path(override).expanduser().resolve()
    return (Path.home() / ".claude").resolve()


def find_repo_root() -> Path | None:
    """
    The LeRoy git checkout. Preference order:
      1. $LEROY_REPO_ROOT env override.
      2. Walk up from this file (installer/find_user.py -> repo root is parent).
      3. A `leroy_repo` pointer file inside claude_home/config/, if one exists
         (written by setup.ps1 at install time — see write_repo_pointer()).
      4. Common default install dirs (~/LeRoy-HQ), if they look like a checkout.
    Returns None if nothing plausible is found (caller decides how to degrade).
    """
    override = os.environ.get("LEROY_REPO_ROOT")
    if override:
        p = Path(override).expanduser().resolve()
        if p.exists():
            return p

    here = Path(__file__).resolve().parent.parent  # installer/ -> repo root
    if (here / "bin").exists() and (here / "core").exists():
        return here

    claude_home = find_claude_home()
    pointer = claude_home / "config" / "leroy_repo.json"
    if pointer.exists():
        try:
            data = json.loads(pointer.read_text(encoding="utf-8"))
            candidate = Path(data.get("repo_root", "")).expanduser()
            if candidate.exists():
                return candidate.resolve()
        except (OSError, ValueError):
            pass

    fallback = Path.home() / "LeRoy-HQ"
    if (fallback / "bin").exists():
        return fallback.resolve()

    return None


def write_repo_pointer(claude_home: Path, repo_root: Path) -> None:
    """
    Record where the repo checkout lives so future lookups (from a different
    cwd, e.g. a scheduled task) don't have to guess. Called once by setup.ps1
    after a successful install/merge. Never overwrites a user-edited pointer
    with a worse guess — always safe to call again after `leroy update`.
    """
    cfg_dir = claude_home / "config"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    pointer = cfg_dir / "leroy_repo.json"
    pointer.write_text(
        json.dumps({"repo_root": str(repo_root.resolve())}, indent=2) + "\n",
        encoding="utf-8",
    )


def find_app_dir(repo_root: Path | None) -> Path | None:
    """The packaged desktop app (WS4.8), if this checkout has one."""
    if repo_root is None:
        return None
    app = repo_root / "app"
    return app if app.exists() else None


def _maintenance_config_path(claude_home: Path) -> Path:
    return claude_home / "config" / "maintenance.json"


def find_backup_dest(claude_home: Path) -> Path:
    """
    Where snapshots/backups land. Preference order:
      1. $LEROY_BACKUP_DEST env override.
      2. config/maintenance.json ("backup_dest"), if the user or wizard set one.
      3. Default: ~/LeRoy-Backups (NOT inside ~/.claude, so a `leroy reset`
         restoring ~/.claude never touches backups).
    """
    override = os.environ.get("LEROY_BACKUP_DEST")
    if override:
        return Path(override).expanduser().resolve()

    cfg_path = _maintenance_config_path(claude_home)
    if cfg_path.exists():
        try:
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
            dest = cfg.get("backup_dest")
            if dest:
                return Path(dest).expanduser().resolve()
        except (OSError, ValueError):
            pass

    return (Path.home() / "LeRoy-Backups").resolve()


def find_rag_port(claude_home: Path) -> int:
    """RAG sidecar port. Default 7742 (matches the private harness convention)."""
    override = os.environ.get("LEROY_RAG_PORT")
    if override and override.isdigit():
        return int(override)

    cfg_path = _maintenance_config_path(claude_home)
    if cfg_path.exists():
        try:
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
            port = cfg.get("rag_port")
            if isinstance(port, int):
                return port
        except (OSError, ValueError):
            pass

    return 7742


def find_skill_index_script(repo_root: Path | None, claude_home: Path) -> Path | None:
    """
    The skill-index rebuild script. Checked in order: the repo checkout's
    core/scripts/, then a user-added ~/.claude/scripts/ (private-harness style
    installs may add their own). Returns None if neither exists — callers must
    treat a missing skill-index step as a soft skip, not a hard failure.
    """
    candidates = []
    if repo_root is not None:
        candidates.append(repo_root / "core" / "scripts" / "build-skill-index.py")
        candidates.append(repo_root / "core" / "scripts" / "build_skill_index.py")
    candidates.append(claude_home / "scripts" / "build-skill-index.py")
    candidates.append(claude_home / "scripts" / "build_skill_index.py")
    for c in candidates:
        if c.exists():
            return c
    return None


def resolve() -> UserPaths:
    """One call that resolves everything a maintenance/backup script needs."""
    claude_home = find_claude_home()
    repo_root = find_repo_root()
    return UserPaths(
        claude_home=claude_home,
        repo_root=repo_root,
        app_dir=find_app_dir(repo_root),
        backup_dest=find_backup_dest(claude_home),
        rag_port=find_rag_port(claude_home),
        skill_index_script=find_skill_index_script(repo_root, claude_home),
    )


def ensure_backup_dest(paths: UserPaths) -> Path:
    """Create backup_dest if missing and return it. The only writing helper here."""
    paths.backup_dest.mkdir(parents=True, exist_ok=True)
    return paths.backup_dest


def print_report(paths: UserPaths) -> None:
    print("  LeRoy user-finding report")
    print("  " + "-" * 46)
    print(f"  claude_home         : {paths.claude_home}"
          f"{'  (missing!)' if not paths.claude_home.exists() else ''}")
    print(f"  repo_root           : {paths.repo_root or '(not found)'}")
    print(f"  app_dir             : {paths.app_dir or '(not packaged in this checkout)'}")
    print(f"  backup_dest         : {paths.backup_dest}")
    print(f"  rag_port            : {paths.rag_port}")
    print(f"  skill_index_script  : {paths.skill_index_script or '(not found — will be skipped)'}")
    print("  " + "-" * 46)


def main() -> int:
    print_report(resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
