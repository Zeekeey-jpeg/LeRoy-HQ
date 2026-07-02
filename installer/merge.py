#!/usr/bin/env python3
"""
LeRoy — merge.py
================
Safe, backup-first, ADDITIVE merge of the LeRoy overlay (`core/`) into the
user's Claude Code config directory (`~/.claude`).

Two ironclad rules:
  1. NEVER overwrite the user's own settings. We back the whole `~/.claude`
     tree up first, then only copy files that DON'T already exist. The one
     exception is `settings.json`, which we MERGE key-by-key (and hooks are
     appended, never replaced).
  2. Everything is reversible. The backup lives at
     `~/.claude.backup-<YYYY-MM-DD-HHMMSS>/` and `leroy reset` restores it.

Usage:
    python installer/merge.py                 # do the merge
    python installer/merge.py --dry-run       # show what WOULD happen, touch nothing
    python installer/merge.py --source PATH   # override the core/ source dir
    python installer/merge.py --dest PATH     # override ~/.claude (testing)

The dry-run prints a plan: which files are new (copied), which already exist
(skipped), and how settings.json would be merged — without writing anything.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import shutil
import sys
from pathlib import Path

# See installer/doctor.py for why this exists: a glyph-probe fallback alone
# can miss a non-ASCII character that only appears later in the file,
# crashing print() on a strict cp1252 console. Reconfiguring is the
# whole-class fix.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(errors="replace")

# --- pretty marks (ASCII fallback) ------------------------------------------
_UTF_OK = True
try:
    "✅＋≈↷".encode(sys.stdout.encoding or "utf-8")
except (UnicodeEncodeError, LookupError):
    _UTF_OK = False

NEW = "＋" if _UTF_OK else "[new] "
SKIP = "·" if _UTF_OK else "[skip]"
MERGE = "≈" if _UTF_OK else "[merge]"
OK = "✅" if _UTF_OK else "[ OK ]"


def default_source() -> Path:
    """core/ sits next to installer/ in the repo."""
    return (Path(__file__).resolve().parent.parent / "core").resolve()


def default_dest() -> Path:
    """The live Claude Code config dir — always derived from HOME, never hardcoded."""
    return (Path.home() / ".claude").resolve()


# --- settings.json merge ----------------------------------------------------
def merge_settings(user: dict, overlay: dict) -> dict:
    """
    Additive deep merge that NEVER clobbers a user value.

    - Scalars/lists the user already set win (overlay is ignored for them).
    - Keys the user doesn't have are taken from the overlay.
    - `hooks` is special: it's a dict of event -> list; we append overlay hook
      entries that the user doesn't already have (dedup by JSON identity).
    - Nested dicts recurse with the same rules.
    """
    result = dict(user)  # start from the user's settings — they always win
    for key, ov_val in overlay.items():
        if key == "hooks" and isinstance(ov_val, dict):
            result["hooks"] = _merge_hooks(user.get("hooks", {}), ov_val)
        elif key not in result:
            result[key] = ov_val
        elif isinstance(result[key], dict) and isinstance(ov_val, dict):
            result[key] = merge_settings(result[key], ov_val)
        # else: user already has a non-dict value here -> keep it, drop overlay
    return result


def _merge_hooks(user_hooks: dict, overlay_hooks: dict) -> dict:
    """Append overlay hooks additively, deduping by serialized identity."""
    merged = {k: list(v) for k, v in user_hooks.items()}
    for event, entries in overlay_hooks.items():
        existing = merged.setdefault(event, [])
        seen = {json.dumps(e, sort_keys=True) for e in existing}
        for entry in entries:
            sig = json.dumps(entry, sort_keys=True)
            if sig not in seen:
                existing.append(entry)
                seen.add(sig)
    return merged


# --- the merge engine -------------------------------------------------------
class MergePlan:
    def __init__(self) -> None:
        self.new_files: list[Path] = []      # relative paths to be copied
        self.skipped: list[Path] = []        # already exist, left untouched
        self.settings_merge: str | None = None  # human summary of settings action


def build_plan(source: Path, dest: Path) -> MergePlan:
    plan = MergePlan()
    if not source.exists():
        raise FileNotFoundError(f"source overlay not found: {source}")

    for path in sorted(source.rglob("*")):
        if path.is_dir():
            continue
        rel = path.relative_to(source)
        # Skip Python bytecode caches — build artifacts, never part of the overlay.
        if "__pycache__" in rel.parts or rel.suffix == ".pyc":
            continue
        # settings.json is handled by the merger, not the copier.
        if rel.name == "settings.json" and rel.parent == Path("."):
            continue
        target = dest / rel
        if target.exists():
            plan.skipped.append(rel)
        else:
            plan.new_files.append(rel)

    # Plan the settings.json action.
    src_settings = source / "settings.json"
    dst_settings = dest / "settings.json"
    if src_settings.exists():
        if dst_settings.exists():
            plan.settings_merge = "deep-merge into existing settings.json (user values win, hooks appended)"
        else:
            plan.settings_merge = "create settings.json from overlay (no existing file)"
    return plan


def backup(dest: Path, dry_run: bool) -> Path | None:
    """Back up the entire existing ~/.claude before touching it."""
    if not dest.exists():
        return None  # nothing to back up (fresh install)
    stamp = _dt.datetime.now().strftime("%Y-%m-%d-%H%M%S")
    backup_dir = dest.parent / f"{dest.name}.backup-{stamp}"
    if dry_run:
        return backup_dir
    shutil.copytree(dest, backup_dir, dirs_exist_ok=False)
    return backup_dir


def apply_plan(source: Path, dest: Path, plan: MergePlan) -> None:
    """Execute the merge for real (caller must have backed up first)."""
    dest.mkdir(parents=True, exist_ok=True)
    for rel in plan.new_files:
        src = source / rel
        tgt = dest / rel
        tgt.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, tgt)

    # settings.json — merge or create.
    src_settings = source / "settings.json"
    if src_settings.exists():
        overlay = _load_json(src_settings)
        dst_settings = dest / "settings.json"
        if dst_settings.exists():
            user = _load_json(dst_settings)
            merged = merge_settings(user, overlay)
        else:
            merged = overlay
        dst_settings.write_text(
            json.dumps(merged, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )


def _load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        raise SystemExit(f"  {'!'}  could not read {path}: {e}")


# --- rendering --------------------------------------------------------------
def print_plan(plan: MergePlan, source: Path, dest: Path, dry_run: bool, backup_dir: Path | None) -> None:
    print()
    dash = "—" if _UTF_OK else "-"
    mode = f"DRY RUN {dash} nothing will be written" if dry_run else "APPLYING merge"
    print(f"  LeRoy merge {dash} {mode}")
    print(f"  source: {source}")
    print(f"  dest:   {dest}")
    print("  " + "-" * 60)
    if backup_dir:
        verb = "would back up" if dry_run else "backed up"
        print(f"  {'↷'if _UTF_OK else '[bak]'}  {verb} existing config -> {backup_dir}")
    else:
        print(f"  (fresh install — no existing {dest.name} to back up)")
    print()
    print(f"  {NEW} {len(plan.new_files)} new file(s) to add:")
    for rel in plan.new_files[:40]:
        print(f"      {NEW} {rel.as_posix()}")
    if len(plan.new_files) > 40:
        print(f"      ... and {len(plan.new_files) - 40} more")
    print()
    print(f"  {SKIP} {len(plan.skipped)} file(s) already present (left untouched):")
    for rel in plan.skipped[:15]:
        print(f"      {SKIP} {rel.as_posix()}")
    if len(plan.skipped) > 15:
        print(f"      ... and {len(plan.skipped) - 15} more")
    print()
    if plan.settings_merge:
        print(f"  {MERGE} settings.json: {plan.settings_merge}")
    else:
        print("  (no settings.json in overlay)")
    print("  " + "-" * 60)
    if dry_run:
        print("  Dry run complete. Re-run without --dry-run to apply.\n")
    else:
        print(f"  {OK}  Merge complete.\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Safe additive merge of LeRoy core/ into ~/.claude")
    parser.add_argument("--dry-run", action="store_true", help="show the plan, write nothing")
    parser.add_argument("--source", type=Path, default=None, help="override the core/ source dir")
    parser.add_argument("--dest", type=Path, default=None, help="override the ~/.claude target dir")
    args = parser.parse_args(argv)

    source = (args.source or default_source()).resolve()
    dest = (args.dest or default_dest()).resolve()

    try:
        plan = build_plan(source, dest)
    except FileNotFoundError as e:
        print(f"\n  merge aborted: {e}\n")
        return 1

    backup_dir = backup(dest, dry_run=args.dry_run)
    if not args.dry_run:
        apply_plan(source, dest, plan)
    print_plan(plan, source, dest, args.dry_run, backup_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
