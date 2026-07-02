#!/usr/bin/env python3
"""
LeRoy — memory_migrate.py  (G5 — WS3.3 / WS2.6: memory -> RAG on upgrade)
=============================================================================
Existing-user upgrades must integrate their current memory/ folder with the
new RAG memory system WITHOUT DATA LOSS. This script is the one piece that
does that: it walks memory/, and for every markdown file, POSTs it to the RAG
sidecar's index endpoint. It never deletes, moves, or rewrites a single file
in memory/ — the vault on disk is the source of truth; RAG is a derived index
built FROM it, so "no data loss" is structural (the migration can be re-run
any number of times, or fail outright, and the vault is untouched either way).

Idempotent: re-running is safe. The RAG sidecar is expected to dedupe/replace
by file path + content hash on its own side (that's the sidecar's contract,
not this script's); this script just walks and posts every .md file it finds,
every time.

Where it plugs in:
  - setup.ps1 step 2 (merge) is for CORE files; this is for the VAULT and only
    makes sense once a sidecar exists and is reachable — so it's invoked
    AFTER merge, as an optional step that degrades gracefully (sidecar down
    -> clear message, vault is untouched, nothing is lost, retry later).
  - `leroy update` can also call this after a successful merge so an
    existing user's newly-added memory notes since last update get indexed.

Uses installer/find_user.py to resolve claude_home + rag_port — no hardcoded
paths or ports.

Stdlib only (urllib, no requests dependency).
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
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
    "✅⚠️".encode(sys.stdout.encoding or "utf-8")
except (UnicodeEncodeError, LookupError):
    _UTF_OK = False

OK = "✅" if _UTF_OK else "[ OK ]"
WARN = "⚠️ " if _UTF_OK else "[warn]"

IGNORE_DIR_NAMES = {"__pycache__", "node_modules", ".git", "Archive"}


def _check_sidecar_alive(rag_port: int, timeout: float = 3.0) -> bool:
    try:
        with urllib.request.urlopen(f"http://localhost:{rag_port}/health", timeout=timeout) as resp:
            return resp.status == 200
    except (urllib.error.URLError, OSError, ValueError):
        return False


def _index_one(rag_port: int, rel_path: str, content: str, timeout: float = 15.0) -> tuple[bool, str]:
    body = json.dumps({"path": rel_path, "content": content}).encode("utf-8")
    req = urllib.request.Request(
        f"http://localhost:{rag_port}/index",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return True, ""
    except (urllib.error.URLError, OSError, ValueError) as e:
        return False, str(e)


def migrate(claude_home: Path, rag_port: int, dry_run: bool) -> int:
    vault = claude_home / "memory"
    if not vault.exists():
        print(f"  No memory/ folder at {vault} — nothing to migrate (fresh vault, nothing lost).")
        return 0

    files = [
        p for p in sorted(vault.rglob("*.md"))
        if not (IGNORE_DIR_NAMES & set(p.relative_to(vault).parts))
    ]
    print(f"  Found {len(files)} markdown file(s) under {vault}.")

    if dry_run:
        print(f"  [dry-run] would index {len(files)} file(s) into the RAG sidecar on port {rag_port}.")
        print("  [dry-run] the vault on disk would NOT be modified in any way (index is derived, read-only source).")
        return 0

    if not files:
        return 0

    if not _check_sidecar_alive(rag_port):
        print(f"  {WARN} RAG sidecar not reachable on port {rag_port}.")
        print("  Your memory vault is completely untouched — nothing was lost. Start the RAG")
        print("  sidecar and re-run this migration (it's safe to re-run any number of times):")
        print(f"      python installer/memory_migrate.py")
        return 1

    ok_count = 0
    fail_count = 0
    for path in files:
        rel = path.relative_to(vault).as_posix()
        try:
            content = path.read_text(encoding="utf-8")
        except OSError as e:
            print(f"  {WARN} could not read {rel}: {e}")
            fail_count += 1
            continue
        ok, err = _index_one(rag_port, rel, content)
        if ok:
            ok_count += 1
        else:
            fail_count += 1
            print(f"  {WARN} failed to index {rel}: {err}")

    print()
    print(f"  {OK} indexed {ok_count}/{len(files)} file(s) into RAG.")
    if fail_count:
        print(f"  {WARN} {fail_count} file(s) failed to index (see above) — vault on disk is untouched;")
        print("        re-run this script any time to retry just the failures (idempotent).")
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Index an existing memory/ vault into the RAG sidecar (no data loss)")
    parser.add_argument("--dry-run", action="store_true", help="show what would be indexed, touch nothing, call nothing")
    parser.add_argument("--claude-home", type=Path, default=None, help="override ~/.claude (testing)")
    parser.add_argument("--rag-port", type=int, default=None, help="override the RAG sidecar port")
    args = parser.parse_args(argv)

    claude_home = (args.claude_home or find_user.find_claude_home()).resolve()
    rag_port = args.rag_port or find_user.find_rag_port(claude_home)

    print()
    print("  LeRoy memory -> RAG migration")
    print(f"  vault: {claude_home / 'memory'}")
    print(f"  rag port: {rag_port}")
    print("  " + "-" * 46)
    rc = migrate(claude_home, rag_port, args.dry_run)
    print()
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
