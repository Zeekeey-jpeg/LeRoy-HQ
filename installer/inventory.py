#!/usr/bin/env python3
"""
LeRoy — inventory.py  (G4 — WS3.1/3.2: real upgrade-mode doctor)
=====================================================================
`doctor.py` today only answers "are Node/Python/git/Claude Code present" —
useful before a FRESH install, but useless for an EXISTING install asking
"what in my current ~/.claude is stale vs. what LeRoy would ship, and what's
mine that LeRoy doesn't know about?"

This module builds that inventory + diff:
  1. Walk an existing ~/.claude (or a tar/zip extracted to a temp dir — see
     `--from-archive`), collecting a flat map of relative path -> content hash
     for every file under core-managed areas (agents/, skills/, hooks/,
     CLAUDE.md, settings.json) plus a simple count for memory/.
  2. Walk the shipped `core/` tree the same way.
  3. Diff:
       - SAME       : identical content, both sides — nothing to do.
       - STALE      : path exists on both sides, content differs, and the
                       existing file looks unmodified from an older shipped
                       version (best-effort: no local-edit markers) -> safe to
                       update via `leroy update` (merge.py already only adds
                       genuinely NEW files, so STALE items need a manual note
                       since merge.py won't touch existing files).
       - USER-OWNED : path exists only on the user's side -> never touched.
       - NEW-IN-CORE: path exists only in the shipped core/ -> `leroy update`
                       will add this automatically (merge.py logic).
       - MEMORY     : the user's memory/ folder is reported as file-count +
                       size only (never diffed file-by-file — it's personal
                       and RAG-migration, not core-merge, territory; see
                       memory_migrate.py for G5).
  4. settings.json gets its own top-level-key diff (mirrors merge.py's
     merge_settings semantics) so the report says which keys/hooks are new,
     not just "differs".

This is read-only. It never writes to the existing install. `doctor.py --upgrade`
calls this and prints the report; nothing here decides to change anything.

Stdlib only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tarfile
import tempfile
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

# See doctor.py for why this exists: this file prints raw em-dashes in report
# text with no ASCII-fallback guard at all — on a strict cp1252 console that
# throws UnicodeEncodeError instead of printing the report. Reconfiguring
# stdout/stderr to replace-on-error is the whole-class fix.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(errors="replace")

CORE_MANAGED_DIRS = ["agents", "skills", "hooks"]
CORE_MANAGED_FILES = ["CLAUDE.md"]
SETTINGS_FILE = "settings.json"
MEMORY_DIR = "memory"

# Never hash/diff these — build artifacts or clearly personal/runtime state.
IGNORE_PARTS = {"__pycache__", "node_modules", ".git", "worktrees", "sessions_archive"}


@dataclass
class DiffReport:
    same: list[str] = field(default_factory=list)
    stale: list[str] = field(default_factory=list)
    user_owned: list[str] = field(default_factory=list)
    new_in_core: list[str] = field(default_factory=list)
    settings_new_keys: list[str] = field(default_factory=list)
    settings_new_hooks: dict = field(default_factory=dict)
    memory_file_count: int = 0
    memory_size_kb: float = 0.0
    memory_present: bool = False


def _hash_file(path: Path) -> str:
    h = hashlib.sha256()
    try:
        h.update(path.read_bytes())
    except OSError:
        return ""
    return h.hexdigest()


def _walk_managed(root: Path) -> dict[str, str]:
    """rel-path -> sha256, for every file under the core-managed areas."""
    out: dict[str, str] = {}
    if not root.exists():
        return out

    targets = [root / d for d in CORE_MANAGED_DIRS] + [root / f for f in CORE_MANAGED_FILES]
    for base in targets:
        if base.is_file():
            out[base.name] = _hash_file(base)
            continue
        if not base.is_dir():
            continue
        for path in base.rglob("*"):
            if path.is_dir():
                continue
            if IGNORE_PARTS & set(path.parts):
                continue
            rel = path.relative_to(root)
            out[rel.as_posix()] = _hash_file(path)
    return out


def _load_settings(root: Path) -> dict:
    path = root / SETTINGS_FILE
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _memory_stats(root: Path) -> tuple[bool, int, float]:
    mem = root / MEMORY_DIR
    if not mem.exists():
        return False, 0, 0.0
    files = [p for p in mem.rglob("*") if p.is_file()]
    size = sum(p.stat().st_size for p in files)
    return True, len(files), round(size / 1024, 1)


def diff_installs(existing: Path, shipped_core: Path) -> DiffReport:
    report = DiffReport()

    existing_map = _walk_managed(existing)
    core_map = _walk_managed(shipped_core)

    all_paths = set(existing_map) | set(core_map)
    for rel in sorted(all_paths):
        in_existing = rel in existing_map
        in_core = rel in core_map
        if in_existing and in_core:
            if existing_map[rel] == core_map[rel]:
                report.same.append(rel)
            else:
                report.stale.append(rel)
        elif in_existing and not in_core:
            report.user_owned.append(rel)
        else:
            report.new_in_core.append(rel)

    existing_settings = _load_settings(existing)
    core_settings = _load_settings(shipped_core)
    report.settings_new_keys = sorted(k for k in core_settings if k != "hooks" and k not in existing_settings)

    core_hooks = core_settings.get("hooks", {}) if isinstance(core_settings.get("hooks"), dict) else {}
    existing_hooks = existing_settings.get("hooks", {}) if isinstance(existing_settings.get("hooks"), dict) else {}
    for event, entries in core_hooks.items():
        existing_entries = existing_hooks.get(event, [])
        existing_sigs = {json.dumps(e, sort_keys=True) for e in existing_entries}
        missing = [e for e in entries if json.dumps(e, sort_keys=True) not in existing_sigs]
        if missing:
            report.settings_new_hooks[event] = len(missing)

    report.memory_present, report.memory_file_count, report.memory_size_kb = _memory_stats(existing)
    return report


def _extract_archive(archive: Path) -> Path:
    """Extract a .zip or .tar(.gz) existing-install archive to a temp dir, return its root."""
    tmp = Path(tempfile.mkdtemp(prefix="leroy-inventory-"))
    if archive.suffix == ".zip":
        with zipfile.ZipFile(archive) as z:
            z.extractall(tmp)
    elif archive.suffixes and archive.suffixes[-1] in (".tar", ".gz", ".tgz") or ".tar" in archive.suffixes:
        with tarfile.open(archive) as t:
            t.extractall(tmp)  # noqa: S202 — trusted local archive the user pointed us at
    else:
        raise ValueError(f"unrecognized archive format: {archive}")

    # A tar/zip of ~/.claude often has one top-level wrapper dir; unwrap it.
    entries = list(tmp.iterdir())
    if len(entries) == 1 and entries[0].is_dir():
        return entries[0]
    return tmp


def print_report(report: DiffReport) -> None:
    print()
    print("  LeRoy upgrade inventory — what would change")
    print("  " + "-" * 56)
    print(f"  Unchanged (no action)         : {len(report.same)}")
    print(f"  Stale (shipped core changed)  : {len(report.stale)}")
    for rel in report.stale[:20]:
        print(f"      ~ {rel}")
    if len(report.stale) > 20:
        print(f"      ... and {len(report.stale) - 20} more")
    print(f"  Yours only (never touched)    : {len(report.user_owned)}")
    print(f"  New in shipped core           : {len(report.new_in_core)}  (added automatically by 'leroy update')")
    for rel in report.new_in_core[:20]:
        print(f"      + {rel}")
    if len(report.new_in_core) > 20:
        print(f"      ... and {len(report.new_in_core) - 20} more")
    print()
    if report.settings_new_keys:
        print(f"  settings.json — new top-level keys available: {', '.join(report.settings_new_keys)}")
    if report.settings_new_hooks:
        for event, count in report.settings_new_hooks.items():
            print(f"  settings.json — {count} new hook(s) available for '{event}'")
    if not report.settings_new_keys and not report.settings_new_hooks:
        print("  settings.json: no new keys/hooks to add.")
    print()
    if report.memory_present:
        print(f"  memory/: {report.memory_file_count} file(s), ~{report.memory_size_kb} KB "
              f"(run 'leroy update' then the memory->RAG migration to index it — see memory_migrate.py)")
    else:
        print("  memory/: not found (fresh vault will be created on first 'leroy init').")
    print("  " + "-" * 56)
    if report.stale:
        print("  NOTE: 'leroy update' only ADDS new files (never overwrites yours).")
        print("        Stale files above changed upstream but won't auto-update —")
        print("        review them manually if you want the newer version.")
    print()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="LeRoy upgrade inventory: existing install vs shipped core/")
    parser.add_argument("--existing", type=Path, default=None, help="existing ~/.claude to inventory (default: ~/.claude)")
    parser.add_argument("--from-archive", type=Path, default=None, help="a .zip/.tar(.gz) of an existing install instead of a live dir")
    parser.add_argument("--core", type=Path, default=None, help="the shipped core/ dir to diff against (default: repo's own core/)")
    args = parser.parse_args(argv)

    if args.from_archive:
        existing = _extract_archive(args.from_archive)
    else:
        existing = (args.existing or (Path.home() / ".claude")).resolve()

    shipped_core = args.core or (Path(__file__).resolve().parent.parent / "core")

    if not existing.exists():
        print(f"\n  No existing install found at {existing} — nothing to inventory (fresh install path applies).\n")
        return 0

    report = diff_installs(existing, shipped_core)
    print_report(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
