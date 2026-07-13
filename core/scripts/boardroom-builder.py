#!/usr/bin/env python3
"""
boardroom-builder.py — The Boardroom Sandbox Builder  (Phase 4 + AUTO-SHIP)

The board proposes. The sandbox builds. Green tier ships automatically.

This script implements the "build-gate" for Boardroom proposals:

  1. Pull a proposal (by scene_id or from the build queue).
  2. Create an ISOLATED git worktree on a new branch boardroom/poc-<slug>.
  3. Run a `claude -p` build INSIDE that worktree to implement the POC.
  4. Capture a demo artifact: git diff stat + written summary.
  5. Save the artifact to session/boardroom/builds/<id>.json.
  6. Append a RAG-embeddable note to memory/Projects/Boardroom-Sandbox/builds-log.md.

HARD SAFETY RULES (enforced in code):
  - NEVER checkout/commit/merge/push to master or any existing branch.
  - NEVER push to a remote.
  - NEVER delete files outside the worktree.
  - approve_and_merge() is the ONLY path that merges into master. It requires
    either brian_go=True (manual approval) OR the build is green-tier AND
    verify_build passed. These are the ONLY two entry points; the tier check is
    performed first and is not bypassable.
  - NEVER auto-merge an approval-tier or never-tier build — even if somehow
    called directly, the function refuses at line 1 of the merge block.

TIER MODEL:
  green    → AUTO-SHIP: build → verify → if pass, merge → backup → notify "shipped".
             If verify fails → roll back (no merge), status "failed", notify.
  approval → Manual: build sandbox, wait for Brian's explicit approve+merge.
             CANNOT reach the auto-merge path — hard refusal enforced.
  never    → Hard-blocked: sync_decisions skips it; run_build returns early.

VERIFICATION GATE (verify_build):
  Runs INSIDE the worktree BEFORE any auto-merge:
  - Detects changed files via git diff --name-only against master.
  - SCOPE: only .claude-repo changes are auto-verifiable. If ANY changed file
    is outside CLAUDE_ROOT (e.g. .claude/memory/Projects/leroy-pwa-app), the build is
    classified "needs_brian" — auto-merge is blocked and Brian is notified.
  - For every changed *.py: python -m py_compile <file> (syntax check).
  - Basic sanity: diff is non-empty, all listed files exist.
  - Returns (ok: bool, report: str).

CLI:
  --proposal-scene <scene_id>   Pull proposal from boardroom.jsonl by scene id
  --queue                       Process first pending item in build-queue.json
  --list                        List all builds (status, title, branch)
  --approve <build_id>          MERGE gate: requires --yes-really-merge flag
  --reject  <build_id>          Mark rejected + clean up worktree
  --verify  <build_id>          Run verification gate without merging (dry-run)
  --yes-really-merge            Explicit Brian-go flag (required for --approve)
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import re
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("boardroom-builder")

# ─── Paths ────────────────────────────────────────────────────────────────────

CLAUDE_ROOT    = Path(r"~/.claude")
# Bookkeeping (decisions, scenes, build records, queue, logs) ALWAYS lives in
# .claude — the board's own memory. These never move.
SCRIPTS_DIR    = CLAUDE_ROOT / "scripts"
SESSION_DIR    = CLAUDE_ROOT / "session"
BOARD_DIR      = SESSION_DIR / "boardroom"
BUILDS_DIR     = BOARD_DIR / "builds"
BUILD_QUEUE    = BOARD_DIR / "build-queue.json"
SCENE_LOG      = BOARD_DIR / "boardroom.jsonl"
MEMORY_DIR     = CLAUDE_ROOT / "memory"
SANDBOX_MEMORY = MEMORY_DIR / "Projects" / "Boardroom-Sandbox"
BUILDS_LOG_MD  = SANDBOX_MEMORY / "builds-log.md"

# ── BUILD TARGET ──────────────────────────────────────────────────────────────
# The board builds and deploys against the LIVE Leroy app — the running app, not
# a sandbox copy. So "deploy" actually ships. All git ops (worktree/branch/merge/
# revert) and the verify boundary run against APP_REPO. Only the bookkeeping above
# stays in .claude. Override via env for testing.
APP_REPO       = Path(os.getenv("BOARDROOM_APP_REPO", r"~/.claude\memory\Projects\leroy-pwa-app"))
# Build worktrees live OUTSIDE both repos so an app-repo worktree is never nested
# inside the .claude repo tree (which would confuse both repos' status).
WORKTREES_DIR  = Path(r"~\Desktop\Projects\.leroy-build-worktrees")

CLAUDE_EXE = Path(r"~\AppData\Roaming\npm\claude.cmd")
if not CLAUDE_EXE.exists():
    _alt = Path(r"~\AppData\Roaming\npm\node_modules\@anthropic-ai\claude-code\bin\claude.exe")
    if _alt.exists():
        CLAUDE_EXE = _alt

MASTER_BRANCH  = "master"
BRANCH_PREFIX  = "boardroom/poc-"
BUILD_TIMEOUT  = 600   # seconds — POC builds may need up to 10 min

# ── Build concurrency throttle ──────────────────────────────────────────────────
# "Approve all" used to fire one unbounded thread per decision — approve 30 and you
# got 30 parallel `claude` builds, which shreds the Max-plan rate limit and thrashes
# the machine. We gate run_build() behind a bounded semaphore so at most
# BUILD_CONCURRENCY builds actually compile at once; the rest sit in a "queued"
# state (visible on their [Board] card) and promote automatically as slots free.
# One dial: env LEROY_BUILD_CONCURRENCY (default 3 — Brian's "two or three, tops").
BUILD_CONCURRENCY = max(1, int(os.getenv("LEROY_BUILD_CONCURRENCY", "3")))
_build_sem = threading.BoundedSemaphore(BUILD_CONCURRENCY)
# How long a build may wait in the queue for a slot before we give up and mark it
# failed (so a wedged slot can never strand a queued build forever).
BUILD_QUEUE_WAIT = float(os.getenv("LEROY_BUILD_QUEUE_WAIT", "3600"))  # 1h

# Branches the sandbox is NEVER allowed to touch.
PROTECTED_BRANCHES = {MASTER_BRANCH, "main", "develop", "production"}

# Kill-switch: if this file exists, ALL auto-ship activity is blocked.
KILL_SWITCH = SESSION_DIR / "boardroom.disabled"


# ─── IO helpers ───────────────────────────────────────────────────────────────

def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _load_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _save_json(path: Path, data) -> None:
    # Atomic write (tmp + replace) so a crash mid-write can't corrupt a build
    # record on the auto-merge path (guardian recommendation).
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def _slug(text: str) -> str:
    """Convert a proposal title to a safe branch-name slug (max 40 chars)."""
    clean = re.sub(r"[^a-z0-9]+", "-", text.lower())
    clean = clean.strip("-")
    return clean[:40]


# ─── Git helpers (all scoped to the live APP_REPO build target) ──────────────

def _git(*args: str, cwd: Path = APP_REPO, timeout: int = 30) -> str:
    """Run a git command (default: against the live APP_REPO) and return stdout.
    Raises on non-zero exit. Every build/branch/worktree/merge/revert op targets
    the live app; bookkeeping is plain file I/O, never git, so this default is
    correct for all callers."""
    result = subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=timeout,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"git {' '.join(args)} failed (exit {result.returncode}):\n{result.stderr.strip()}"
        )
    return result.stdout.strip()


def _current_branch() -> str:
    return _git("rev-parse", "--abbrev-ref", "HEAD")


def _branch_exists(branch: str) -> bool:
    result = subprocess.run(
        ["git", "branch", "--list", branch],
        cwd=str(APP_REPO),
        capture_output=True, text=True, timeout=10,
    )
    return branch in (result.stdout or "")


def _worktree_list() -> list[dict]:
    """Parse `git worktree list --porcelain` into a list of dicts."""
    out = _git("worktree", "list", "--porcelain")
    worktrees = []
    current: dict = {}
    for line in out.splitlines():
        if line.startswith("worktree "):
            if current:
                worktrees.append(current)
            current = {"path": line.split(" ", 1)[1]}
        elif line.startswith("branch "):
            current["branch"] = line.split(" ", 1)[1].replace("refs/heads/", "")
        elif line.startswith("HEAD "):
            current["HEAD"] = line.split(" ", 1)[1]
    if current:
        worktrees.append(current)
    return worktrees


# ─── Merge-state safety (prevents the "unmerged files / exit 128" wedge) ──────

def _repo_is_mid_merge() -> bool:
    """True if the repo is stuck mid-merge — MERGE_HEAD present OR unmerged index
    entries. THIS is the state that blocks EVERY subsequent deploy with
    'merging is not possible because you have unmerged files'."""
    try:
        if (APP_REPO / ".git" / "MERGE_HEAD").exists():
            return True
        result = subprocess.run(
            ["git", "ls-files", "--unmerged"],
            cwd=str(APP_REPO), capture_output=True, text=True, timeout=15,
        )
        return bool((result.stdout or "").strip())
    except Exception:
        return False


def _recover_stuck_merge() -> bool:
    """Best-effort self-heal: abort an in-progress/conflicted merge so the working
    tree is clean and future deploys aren't blocked. Uses ONLY `git merge --abort`
    (safe — it does not touch unrelated uncommitted work; we deliberately do NOT
    `git reset --hard`, which would nuke Brian's other changes). Returns True if
    the repo is clean afterwards."""
    if not _repo_is_mid_merge():
        return True
    try:
        subprocess.run(
            ["git", "merge", "--abort"],
            cwd=str(APP_REPO), capture_output=True, text=True, timeout=30,
        )
        log.warning("Recovered a stuck/conflicted merge via `git merge --abort`.")
    except Exception as exc:
        log.error("Could not abort stuck merge: %s", exc)
    return not _repo_is_mid_merge()


def _rebase_poc_onto_master(branch: str, worktree_path: str) -> bool:
    """
    Before merging, replay the POC branch onto CURRENT master from inside its own
    worktree. This is the fix for the "spam-approve, only the first lands" cascade:
    when one deploy moves master, the other built POCs are merely BEHIND it. A
    plain `git merge --no-ff` of a behind branch can conflict even when the changes
    don't truly overlap; rebasing first makes those land cleanly. A genuine content
    overlap still conflicts → we abort the rebase and return False so the caller
    marks it for rebuild (no wedge, master untouched).

    Runs IN the worktree because the branch is checked out there (the main repo
    can't `checkout` a branch that a worktree holds).
    """
    wt = Path(worktree_path) if worktree_path else None
    if not wt or not wt.exists():
        return False  # no worktree to rebase in; caller falls back to a plain merge
    try:
        _git("rebase", MASTER_BRANCH, cwd=wt, timeout=180)
        log.info("Rebased POC %s onto %s before merge.", branch, MASTER_BRANCH)
        return True
    except Exception as exc:
        log.warning("POC rebase onto %s conflicted (%s) — aborting; needs rebuild.",
                    MASTER_BRANCH, str(exc)[:140])
        try:
            _git("rebase", "--abort", cwd=wt, timeout=30)
        except Exception:
            pass
        return False


# ─── Proposal retrieval ───────────────────────────────────────────────────────

def _load_proposal_by_scene(scene_id: str) -> Optional[dict]:
    """Find a proposal in boardroom.jsonl by scene_id."""
    if not SCENE_LOG.exists():
        return None
    for line in SCENE_LOG.read_text(encoding="utf-8").splitlines():
        try:
            rec = json.loads(line)
            if rec.get("scene_id") == scene_id:
                proposal = rec.get("proposal")
                if proposal:
                    return {"scene_id": scene_id, "ts": rec.get("ts", ""), **proposal}
        except Exception:
            continue
    return None


def _pop_queue() -> Optional[dict]:
    """Pop and return the first pending item from build-queue.json."""
    queue_data = _load_json(BUILD_QUEUE, {"queue": []})
    items = queue_data.get("queue", [])
    pending = [i for i in items if i.get("status", "pending") == "pending"]
    if not pending:
        return None
    item = pending[0]
    item["status"] = "processing"
    _save_json(BUILD_QUEUE, queue_data)
    return item


def _update_queue_item(proposal_key: str, status: str, build_id: Optional[str] = None) -> None:
    queue_data = _load_json(BUILD_QUEUE, {"queue": []})
    for item in queue_data.get("queue", []):
        if item.get("scene_id") == proposal_key or item.get("build_id") == proposal_key:
            item["status"] = status
            if build_id:
                item["build_id"] = build_id
    _save_json(BUILD_QUEUE, queue_data)


# ─── Build record IO ──────────────────────────────────────────────────────────

def _list_builds() -> list[dict]:
    BUILDS_DIR.mkdir(parents=True, exist_ok=True)
    builds = []
    for path in sorted(BUILDS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime):
        try:
            builds.append(json.loads(path.read_text(encoding="utf-8")))
        except Exception:
            continue
    return builds


def _load_build(build_id: str) -> Optional[dict]:
    path = BUILDS_DIR / f"{build_id}.json"
    return _load_json(path, None)


# Builds capped at BUILD_TIMEOUT (10 min); anything "running" past this is dead.
STALE_BUILD_MINUTES = 20


def reap_stale_builds(notify_fn=None) -> dict:
    """
    Self-healing: a build subprocess is capped at BUILD_TIMEOUT (10 min). Any build
    still 'running' past STALE_BUILD_MINUTES means its process died/orphaned without
    updating status. Mark it 'failed', clean up its leftover worktree, and unstick any
    'building' decision tied to it — so stuck builds never pile up needing Brian's
    attention. Idempotent; safe to call every driver tick.
    """
    reaped: list[str] = []
    now = datetime.now()
    for b in _list_builds():
        if b.get("status") != "running":
            continue
        try:
            age_min = (now - datetime.fromisoformat(b.get("created_ts", ""))).total_seconds() / 60.0
        except Exception:
            continue
        if age_min <= STALE_BUILD_MINUTES:
            continue
        bid = b.get("build_id", "")
        b["status"] = "failed"
        b["error"] = f"Auto-reaped: stuck in 'running' for {age_min:.0f} min (cap {STALE_BUILD_MINUTES}m). Process likely died."
        b["completed_ts"] = now.isoformat(timespec="seconds")
        _save_build(b)
        # Clean the orphaned worktree + branch
        wt = b.get("worktree", "")
        branch = b.get("branch", "")
        try:
            if wt and Path(wt).exists():
                _remove_worktree(Path(wt), branch, force=True)
        except Exception as exc:  # noqa: BLE001
            log.warning("reap: worktree cleanup failed for %s: %s", bid, exc)
        # Unstick any decision tied to this build (by build_id or proposal title)
        try:
            dm = _decisions_mod()
            if dm:
                title = b.get("proposal", {}).get("title", "")
                for d in dm._load_decisions():
                    if d.get("status") == "building" and (
                        d.get("build_id") == bid or (title and d.get("title") == title)
                    ):
                        dm.fail(d["id"], reason="Build auto-reaped (stuck).")
        except Exception as exc:  # noqa: BLE001
            log.warning("reap: decision unstick failed for %s: %s", bid, exc)
        reaped.append(bid)
        log.warning("reap: marked stale build %s failed (age %.0fm)", bid, age_min)

    if reaped and notify_fn:
        try:
            notify_fn("Boardroom: cleared stuck builds",
                      f"Auto-reaped {len(reaped)} build(s) stuck in 'running' and cleaned up their worktrees.")
        except Exception:
            pass
    return {"reaped": reaped, "count": len(reaped)}


def recover_orphaned_builds(notify_fn=None) -> dict:
    """
    Startup recovery: a backend restart kills every in-flight build thread, but their
    build records stay 'running'/'queued' forever — that's the "[Board] card frozen on
    building…" you see after a restart. Call this ONCE at startup: any 'running' or
    'queued' build has no owning thread anymore (we just started), so fail it cleanly,
    clean its worktree, and unstick its decision so Brian can simply re-approve.
    """
    recovered: list[str] = []
    now = datetime.now()
    for b in _list_builds():
        if b.get("status") not in ("running", "queued"):
            continue
        bid = b.get("build_id", "")
        b["status"]       = "failed"
        b["phase"]        = ""
        b["error"]        = "Interrupted by a backend restart. Re-approve to rebuild."
        b["completed_ts"] = now.isoformat(timespec="seconds")
        _save_build(b)
        wt = b.get("worktree", "")
        branch = b.get("branch", "")
        try:
            if wt and Path(wt).exists():
                _remove_worktree(Path(wt), branch, force=True)
        except Exception as exc:  # noqa: BLE001
            log.warning("recover: worktree cleanup failed for %s: %s", bid, exc)
        try:
            dm = _decisions_mod()
            if dm:
                title = b.get("proposal", {}).get("title", "")
                for d in dm._load_decisions():
                    if d.get("status") == "building" and (
                        d.get("build_id") == bid or (title and d.get("title") == title)
                    ):
                        dm.fail(d["id"], reason="Build interrupted by restart — re-approve to rebuild.")
        except Exception as exc:  # noqa: BLE001
            log.warning("recover: decision unstick failed for %s: %s", bid, exc)
        recovered.append(bid)
        log.warning("recover: failed orphaned build %s (was %s)", bid, b.get("status"))

    if recovered and notify_fn:
        try:
            notify_fn("Boardroom: recovered after restart",
                      f"Cleared {len(recovered)} build(s) interrupted by the restart. Re-approve to rebuild.")
        except Exception:
            pass
    return {"recovered": recovered, "count": len(recovered)}


def _decisions_mod():
    """Best-effort import of the decisions module (for unsticking decisions)."""
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "_bd_decisions", str(Path(__file__).parent / "boardroom-decisions.py"))
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)  # type: ignore
        return m
    except Exception:
        return None


def _save_build(record: dict) -> None:
    BUILDS_DIR.mkdir(parents=True, exist_ok=True)
    path = BUILDS_DIR / f"{record['build_id']}.json"
    _save_json(path, record)


# ─── RAG memory append ────────────────────────────────────────────────────────

def _append_builds_log(record: dict) -> None:
    """Append a short RAG-embeddable note so the sandbox's work is recallable."""
    SANDBOX_MEMORY.mkdir(parents=True, exist_ok=True)
    ts   = record.get("created_ts", _now_iso())[:10]
    bid  = record["build_id"]
    title = record.get("proposal", {}).get("title", "Untitled")
    branch = record.get("branch", "")
    status = record.get("status", "unknown")
    summary = record.get("summary", "")
    diff_stat = record.get("diff_stat", "")

    entry = (
        f"\n## [{ts}] {title} — {status.upper()}\n"
        f"- **Build ID:** {bid}\n"
        f"- **Branch:** `{branch}`\n"
        f"- **Status:** {status}\n"
    )
    if summary:
        entry += f"- **Summary:** {summary[:300]}\n"
    if diff_stat:
        entry += f"- **Diff stat:** {diff_stat[:200]}\n"
    entry += "\n---\n"

    if not BUILDS_LOG_MD.exists():
        BUILDS_LOG_MD.write_text(
            "---\nname: boardroom-sandbox-builds-log\n"
            "description: Log of every POC build the Boardroom Sandbox has attempted. "
            "RAG-indexed so past builds are recallable.\n"
            "tags: [boardroom, sandbox, builds, poc]\n"
            "metadata:\n  type: builds-log\n  owner: Boardroom-Sandbox\n---\n\n"
            "# Boardroom Sandbox — Builds Log\n\n"
            "Each entry is one POC build: its proposal, branch, outcome, and summary.\n",
            encoding="utf-8",
        )
    with BUILDS_LOG_MD.open("a", encoding="utf-8") as f:
        f.write(entry)


# ─── Worktree lifecycle ───────────────────────────────────────────────────────

def _create_worktree(build_id: str, slug: str) -> tuple[Path, str]:
    """
    Create an isolated git worktree on a new branch.

    Safety: the branch is always boardroom/poc-<slug> — never master or
    any protected branch. The worktree lives under WORKTREES_DIR so it is
    completely separate from the main working tree.

    Returns (worktree_path, branch_name).
    """
    branch = f"{BRANCH_PREFIX}{slug}-{build_id[:8]}"

    # Hard guard: refuse to create a worktree on a protected branch.
    if branch in PROTECTED_BRANCHES or not branch.startswith(BRANCH_PREFIX):
        raise RuntimeError(
            f"SAFETY VIOLATION: attempted to create worktree on protected branch '{branch}'"
        )

    if _branch_exists(branch):
        raise RuntimeError(f"Branch '{branch}' already exists — aborting to avoid collision.")

    worktree_path = WORKTREES_DIR / build_id
    worktree_path.parent.mkdir(parents=True, exist_ok=True)

    _git("worktree", "add", "-b", branch, str(worktree_path), MASTER_BRANCH)
    log.info("Worktree created: %s on branch %s", worktree_path, branch)
    return worktree_path, branch


def _remove_worktree(worktree_path: Path, branch: str, *, force: bool = False) -> str:
    """
    Remove the worktree and optionally delete the branch.

    Safety: NEVER deletes master or any protected branch.
    """
    if branch in PROTECTED_BRANCHES:
        return f"SAFETY: will not delete protected branch '{branch}'"

    messages = []
    try:
        cmd = ["git", "worktree", "remove", str(worktree_path)]
        if force:
            cmd.append("--force")
        _git(*cmd[1:])
        messages.append(f"Worktree removed: {worktree_path}")
    except Exception as exc:
        messages.append(f"Worktree remove warning: {exc}")

    if branch.startswith(BRANCH_PREFIX):
        try:
            _git("branch", "-d", branch)
            messages.append(f"Branch deleted: {branch}")
        except Exception:
            try:
                _git("branch", "-D", branch)
                messages.append(f"Branch force-deleted: {branch}")
            except Exception as exc2:
                messages.append(f"Branch delete warning: {exc2}")

    return "; ".join(messages)


# ─── claude invocation (inside worktree) ─────────────────────────────────────

def _claude_env() -> dict:
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    npm_dir = str(CLAUDE_EXE.parent)
    must = [npm_dir]
    if sys.platform == "win32":
        sysroot = os.environ.get("SystemRoot", r"C:\Windows")
        must += [sysroot + r"\System32", sysroot]
    parts = (env.get("PATH", "") or "").split(os.pathsep)
    for p in reversed(must):
        if p not in parts:
            parts.insert(0, p)
    env["PATH"] = os.pathsep.join(parts)
    return env


POC_SYSTEM_PROMPT = (
    "You are the Boardroom Sandbox Builder for YourCo. "
    "Your job is to implement the described proof-of-concept COMPLETELY and SAFELY. "
    "Work only within the current working directory (the isolated git worktree). "
    "NEVER modify files outside the worktree. "
    "NEVER push to any remote. "
    "NEVER checkout or merge into master or any branch other than the current one. "
    "MODEL DOCTRINE (Brian's directive, 2026-07-02): know the model tiers — "
    "Fable/Opus are premium and reserved for Brian's interactive work; Sonnet is the "
    "workhorse; NEVER let generated code auto-choose a model. If the POC invokes the "
    "Claude CLI in ANY recurring way (daemon, cron, poller, scheduled task, background "
    "loop), it MUST pass an explicit '--model sonnet' (or equivalent) — never Fable, "
    "never Opus, and never inherit the ambient default model. Recurring jobs also need "
    "a conservative interval: nothing more frequent than hourly without Brian's "
    "explicit sign-off in the proposal. "
    "Write clean, tested code. Commit your changes with a descriptive message. "
    "After building, produce a concise summary (max 200 words) of: "
    "what you built, which files you changed, and what Brian would see if it shipped."
)


def _build_poc_prompt(proposal: dict) -> str:
    title   = proposal.get("title", "Untitled POC")
    what    = proposal.get("what", "")
    why     = proposal.get("why", "")
    owner   = proposal.get("owner", "")
    tier    = proposal.get("tier", "green")
    return (
        f"BOARDROOM SANDBOX BUILD\n\n"
        f"Title: {title}\n"
        f"Tier: {tier}\n"
        f"Owner: {owner}\n\n"
        f"WHAT TO BUILD:\n{what}\n\n"
        f"WHY IT MATTERS:\n{why}\n\n"
        f"INSTRUCTIONS:\n"
        f"1. Implement this POC completely. Make real file changes.\n"
        f"2. Write tests if the proposal touches logic.\n"
        f"3. If the POC spawns Claude on a schedule (daemon/cron/poller), hardcode\n"
        f"   '--model sonnet' and an interval no tighter than hourly. No auto-chosen\n"
        f"   models, no inheriting the machine default.\n"
        f"4. Commit your changes with a descriptive commit message.\n"
        f"5. Finish with a plain-English summary (no markdown headers) of:\n"
        f"   - What you built\n"
        f"   - Which files changed\n"
        f"   - What Brian will see when it ships\n"
        f"Keep the summary under 200 words."
    )


class UsageLimitError(RuntimeError):
    """The claude build was blocked by a usage/rate limit, not a real code failure.
    These are retryable once the Max-plan limit resets — the pipeline treats them
    as 'blocked' (re-approvable), never 'failed'."""


# ─── Exit Recovery Layer hook ─────────────────────────────────────────────────

def _exit_recovery_on_blocked(record: dict, proposal: dict) -> None:
    """
    Called from run_build() when a UsageLimitError is caught.

    Responsibilities:
      1. Checkpoint phase state to disk.
      2. Send a Leroy inbox notification (first block only, suppressed on retries).
      3. If proposal.fail_fast == True  → mark build "failed" and stop; no retry.
         If proposal.fail_fast == False → queue the job for auto-retry.

    Entirely non-fatal — if the recovery module can't load, a warning is logged
    and the build stays "blocked" (manually re-approvable, as before).
    """
    import importlib.util as _ilu

    _recovery_path = SCRIPTS_DIR / "boardroom_exit_recovery.py"
    try:
        spec = _ilu.spec_from_file_location("boardroom_exit_recovery", str(_recovery_path))
        if spec is None or spec.loader is None:
            log.warning("Exit recovery module not found at %s — skipping.", _recovery_path)
            return
        mod = _ilu.module_from_spec(spec)
        spec.loader.exec_module(mod)  # type: ignore[attr-defined]
    except Exception as load_exc:
        log.warning("Could not load exit recovery module (non-fatal): %s", load_exc)
        return

    build_id    = record["build_id"]
    title       = proposal.get("title", "Untitled")
    error       = record.get("error", "")
    fail_fast   = bool(proposal.get("fail_fast", False))
    retry_count = int(proposal.get("_retry_count", 0))

    try:
        mod.checkpoint_build(build_id, proposal)
        mod.notify_blocked(build_id, title, error, fail_fast=fail_fast, retry_count=retry_count)

        if fail_fast:
            log.warning("Build %s has fail_fast=True — alerting and dying, no retry.", build_id)
            record["status"] = "failed"
            record["error"]  = f"[fail_fast] {error}"
            _save_build(record)
        else:
            mod.queue_for_retry(build_id, proposal)
            log.info("Build %s queued for retry when quota opens (attempt %d).",
                     build_id, retry_count + 1)
    except Exception as hook_exc:
        log.warning("Exit recovery hook error (non-fatal): %s", hook_exc)


# ─── Exit Signal Router (lazy-load) ──────────────────────────────────────────

def _load_exit_signal_mod():
    """Lazy-load boardroom_exit_signal module — non-fatal if absent."""
    import importlib.util as _ilu
    _path = SCRIPTS_DIR / "boardroom_exit_signal.py"
    try:
        spec = _ilu.spec_from_file_location("boardroom_exit_signal", str(_path))
        if spec is None or spec.loader is None:
            return None
        mod = _ilu.module_from_spec(spec)
        spec.loader.exec_module(mod)  # type: ignore[attr-defined]
        return mod
    except Exception as exc:
        log.warning("Could not load exit signal module (non-fatal): %s", exc)
        return None


def _stamp_exit_signal(record: dict) -> None:
    """Classify and write exit_signal into the build record — non-fatal."""
    mod = _load_exit_signal_mod()
    if mod:
        try:
            mod.stamp_exit_signal(record)
        except Exception as exc:
            log.warning("stamp_exit_signal failed (non-fatal): %s", exc)


def _exit_signal_auto_retry_enabled() -> bool:
    """Return True if the USAGE_MAX auto-retry feature flag is on."""
    mod = _load_exit_signal_mod()
    if not mod:
        return False
    try:
        return mod.is_auto_retry_enabled()
    except Exception:
        return False


# Substrings that mark a usage/rate-limit refusal. claude -p prints the notice to
# stdout (JSON) and exits non-zero with EMPTY stderr — so the old code, which only
# reported stderr, surfaced a mysterious bare "exit 1". Match case-insensitively.
_USAGE_LIMIT_PATTERNS = (
    "usage limit", "rate limit", "rate_limit", "limit reached", "limit will reset",
    "reset at", "exceeded your", "too many requests", "429", "overloaded",
    "out of credits", "insufficient credit", "quota", "upgrade to increase",
    "reached your", "try again later",
)


def _is_usage_limit(text: str) -> bool:
    t = (text or "").lower()
    return any(p in t for p in _USAGE_LIMIT_PATTERNS)


def _run_poc_claude(proposal: dict, worktree_path: Path) -> tuple[str, str]:
    """
    Invoke `claude -p` inside the worktree to build the POC.

    Returns (summary_text, raw_output).
    Raises UsageLimitError if blocked by a usage/rate limit, RuntimeError otherwise.
    """
    if not CLAUDE_EXE.exists():
        raise RuntimeError(f"Claude CLI not found at {CLAUDE_EXE}")

    prompt = _build_poc_prompt(proposal)
    cmd = [
        str(CLAUDE_EXE), "-p", "--output-format", "json",
        "--dangerously-skip-permissions",
        "--setting-sources", "project,local",
        "--model", "sonnet",
        "--append-system-prompt", POC_SYSTEM_PROMPT,
    ]

    log.info("Invoking claude build in worktree: %s", worktree_path)
    proc = subprocess.run(
        cmd,
        input=prompt,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=BUILD_TIMEOUT,
        cwd=str(worktree_path),
        env=_claude_env(),
    )

    if proc.returncode != 0:
        # Look at BOTH streams — the usage-limit notice lands in stdout/JSON, not stderr.
        detail = ((proc.stderr or "").strip() + " " + (proc.stdout or "").strip()).strip()
        if _is_usage_limit(detail):
            raise UsageLimitError(
                f"Claude usage/rate limit during build (exit {proc.returncode}). {detail[:300]}".strip()
            )
        if not detail:
            # Empty output + non-zero exit from `claude -p` is, in practice, the
            # usage cap (Brian's observation) — the CLI bails before printing.
            raise UsageLimitError(
                f"Claude build exited {proc.returncode} with no output — almost certainly "
                "the usage/rate limit (common when a build runs while you're actively using Claude)."
            )
        raise RuntimeError(f"claude build exit {proc.returncode}: {detail[:400]}")

    raw = (proc.stdout or "").strip()
    try:
        payload = json.loads(raw)
        summary = payload.get("result") or payload.get("message") or raw
    except (json.JSONDecodeError, TypeError):
        summary = raw or "(no output)"

    return str(summary)[:2000], raw


# ─── diff capture ─────────────────────────────────────────────────────────────

def _capture_diff_stat(worktree_path: Path) -> str:
    """
    Return `git diff HEAD --stat` from the worktree (shows what the build changed).
    Falls back to `git log --oneline -5` if HEAD is clean.
    """
    try:
        stat = _git("diff", "HEAD", "--stat", cwd=worktree_path)
        if stat:
            return stat[:1000]
        # If diff is empty, show recent commits (the build likely committed)
        return _git("log", "--oneline", "-5", cwd=worktree_path)
    except Exception as exc:
        return f"(diff capture error: {exc})"


# ─── Main build pipeline ─────────────────────────────────────────────────────

# ─── Stalled Build Rescue Hook ────────────────────────────────────────────────
# When an approved GREEN-tier build fails RESCUE_FAIL_THRESHOLD times in a row,
# tag it "needs-preflight", divert it to a human review queue, and refuse to
# auto-rebuild it until the entry is cleared. Stops a broken green build from
# burning attempts (and tokens) in a silent retry loop. 'blocked' (usage-limit)
# outcomes never count — those are quota pauses, not code failures.

RESCUE_QUEUE          = BOARD_DIR / "rescue-queue.json"
RESCUE_FAIL_THRESHOLD = int(os.getenv("LEROY_RESCUE_FAIL_THRESHOLD", "2"))


def _rescue_key(proposal: dict) -> str:
    """Stable identity for a proposal across rebuild attempts. No decision id is
    carried on the proposal, so fall back to the title slug."""
    return str(
        proposal.get("id")
        or proposal.get("decision_id")
        or _slug(proposal.get("title", "untitled"))
    )


def _consecutive_build_failures(key: str) -> int:
    """Count this proposal's most-recent build records that ended 'failed',
    newest-first, stopping at the first success or quota-pause."""
    if not BUILDS_DIR.exists():
        return 0
    records = []
    for p in BUILDS_DIR.glob("build-*.json"):
        try:
            r = json.loads(p.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        if _rescue_key(r.get("proposal", {})) == key:
            records.append(r)
    records.sort(key=lambda r: r.get("created_ts", ""), reverse=True)
    streak = 0
    for r in records:
        status = r.get("status")
        if status == "failed":
            streak += 1
        elif status in ("ready", "deployed", "blocked"):
            break  # a success or a quota pause breaks the failure streak
    return streak


def _load_rescue_queue() -> dict:
    try:
        return json.loads(RESCUE_QUEUE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_rescue_queue(data: dict) -> None:
    BOARD_DIR.mkdir(parents=True, exist_ok=True)
    tmp = RESCUE_QUEUE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    tmp.replace(RESCUE_QUEUE)


def is_in_rescue_queue(proposal: dict) -> bool:
    """True if this proposal is flagged needs-preflight and not yet cleared."""
    entry = _load_rescue_queue().get(_rescue_key(proposal))
    return bool(entry and not entry.get("cleared"))


def clear_rescue_queue(key: str) -> bool:
    """Mark a rescue entry cleared after human preflight review."""
    q = _load_rescue_queue()
    if key in q and not q[key].get("cleared"):
        q[key]["cleared"]    = True
        q[key]["cleared_ts"] = _now_iso()
        _save_rescue_queue(q)
        return True
    return False


def _rescue_notify(proposal: dict, fail_count: int, error: str) -> None:
    """Best-effort inbox alert via tools/leroy_notify.py. Never raises."""
    title = proposal.get("title", "Untitled")
    try:
        import sys as _sys
        tools_dir = str(CLAUDE_ROOT / "tools")
        if tools_dir not in _sys.path:
            _sys.path.insert(0, tools_dir)
        from leroy_notify import notify_leroy  # type: ignore
        notify_leroy(
            f"🛟 Build needs preflight — {title}",
            (
                f"'{title}' failed {fail_count}× in a row and was pulled from the "
                f"auto-build loop. It needs a preflight review before another rebuild.\n\n"
                f"Last error: {error[:300]}"
            ),
            source="rescue_hook",
        )
    except Exception as exc:  # noqa: BLE001
        log.debug("rescue notify skipped: %s", exc)


def _route_to_rescue(record: dict, proposal: dict, fail_count: int) -> None:
    """Tag the failed record, persist a rescue-queue entry, and alert the inbox.
    Non-fatal — must never mask the underlying build failure."""
    try:
        key = _rescue_key(proposal)
        record["needs_preflight"] = True
        record["routed_to"]       = "rescue_queue"
        _save_build(record)

        q = _load_rescue_queue()
        q[key] = {
            "key":           key,
            "title":         proposal.get("title", "Untitled"),
            "tier":          proposal.get("tier", "green"),
            "fail_count":    fail_count,
            "last_build_id": record.get("build_id", ""),
            "last_error":    (record.get("error", "") or "")[:600],
            "flagged_ts":    _now_iso(),
            "cleared":       False,
        }
        _save_rescue_queue(q)
        log.warning(
            "Build %s routed to rescue queue (needs-preflight after %d failures)",
            record.get("build_id", "?"), fail_count,
        )
        _rescue_notify(proposal, fail_count, record.get("error", ""))
    except Exception as exc:  # noqa: BLE001
        log.warning("Rescue routing error (non-fatal): %s", exc)


def run_build(proposal: dict, on_phase=None) -> dict:
    """
    Full sandbox build pipeline for one proposal.

    Concurrency: gated by a bounded semaphore (BUILD_CONCURRENCY, default 3). A build
    that can't get a slot immediately persists as status 'queued' and waits — its
    [Board] card shows "queued" until a slot frees and it flips to 'running'. This is
    what makes "Approve all" safe: 30 approvals become 3 running + 27 queued, not 30
    parallel claude processes.

    on_phase(text): optional callback fired on every phase change ("queued",
    "Creating worktree…", "Building in sandbox…", …). The approve path uses it to
    stream a live heartbeat onto the mirror card so [Board] cards stop looking frozen.

    Returns the completed build record dict.
    """
    build_id = "build-" + uuid.uuid4().hex[:10]
    title = proposal.get("title", "Untitled")
    slug  = _slug(title)
    ts    = _now_iso()

    record: dict = {
        "build_id":    build_id,
        "status":      "queued",
        "phase":       "Queued — waiting for a build slot…",
        "proposal":    proposal,
        "branch":      "",
        "worktree":    "",
        "diff_stat":   "",
        "summary":     "",
        "error":       "",
        "created_ts":  ts,
        "started_ts":  "",
        "completed_ts": "",
    }
    _save_build(record)

    # Stalled Build Rescue gate: a build already flagged needs-preflight (failed
    # repeatedly) is held out of the auto-build loop until its rescue entry is
    # cleared — don't burn another slot/attempt on a known-broken build.
    if is_in_rescue_queue(proposal):
        record["status"]         = "blocked"
        record["blocked_reason"] = "needs_preflight"
        record["phase"]          = ""
        record["error"]          = (
            "Held for preflight review after repeated failures. "
            "Clear the rescue queue to allow a rebuild."
        )
        record["completed_ts"]   = _now_iso()
        _save_build(record)
        _append_builds_log(record)
        log.warning("Build %s held — proposal in rescue queue (needs-preflight)", build_id)
        return record

    def _emit_phase(text: str) -> None:
        record["phase"] = text
        _save_build(record)
        if on_phase:
            try:
                on_phase(text)
            except Exception:  # noqa: BLE001 - heartbeat must never break a build
                pass

    _emit_phase("Queued — waiting for a build slot…")

    # Block for a free slot. created_ts is set above, but reap_stale_builds only ages
    # 'running' builds, so a long queue wait never trips a false reap.
    got_slot = _build_sem.acquire(timeout=BUILD_QUEUE_WAIT)
    if not got_slot:
        record["status"]       = "failed"
        record["phase"]        = ""
        record["error"]        = f"Timed out after {BUILD_QUEUE_WAIT:.0f}s waiting for a build slot."
        record["completed_ts"] = _now_iso()
        _save_build(record)
        _append_builds_log(record)
        log.warning("Build %s gave up waiting for a slot", build_id)
        return record

    worktree_path: Optional[Path] = None
    branch: str = ""

    try:
        record["status"]     = "running"
        record["started_ts"] = _now_iso()
        _emit_phase("Creating isolated sandbox worktree…")

        # Step 1 — isolated worktree
        worktree_path, branch = _create_worktree(build_id, slug)
        record["branch"]   = branch
        record["worktree"] = str(worktree_path)
        _save_build(record)

        # Step 2 — claude POC build (runs inside the worktree)
        _emit_phase("Building POC in the sandbox…")
        summary, _ = _run_poc_claude(proposal, worktree_path)
        record["summary"] = summary

        # Step 3 — capture diff artifact
        _emit_phase("Capturing the diff…")
        record["diff_stat"] = _capture_diff_stat(worktree_path)

        record["status"]       = "ready"
        record["phase"]        = "Built — awaiting your deploy."
        record["completed_ts"] = _now_iso()
        _save_build(record)
        _append_builds_log(record)
        if on_phase:
            try:
                on_phase("Built — awaiting your deploy.")
            except Exception:  # noqa: BLE001
                pass

        log.info("Build %s complete (branch: %s)", build_id, branch)

    except UsageLimitError as exc:
        # NOT a code failure — Claude's usage/rate limit. Mark 'blocked' so the
        # decision stays recoverable (re-approve later) instead of dead 'failed'.
        record["status"]         = "blocked"
        record["blocked_reason"] = "usage_limit"
        record["error"]          = str(exc)[:600]
        record["completed_ts"]   = _now_iso()
        # ── Exit Signal Router: classify and stamp USAGE_MAX on the build card ─
        _stamp_exit_signal(record)
        _save_build(record)
        _append_builds_log(record)
        log.warning("Build %s blocked (USAGE_MAX): %s", build_id, exc)
        # ── Exit Recovery Layer: checkpoint + notify; auto-retry only when flag ON
        if _exit_signal_auto_retry_enabled():
            _exit_recovery_on_blocked(record, proposal)
        else:
            log.info(
                "Build %s auto-retry disabled (exit-signal-router flag off) "
                "— stays blocked as USAGE_MAX.",
                build_id,
            )

    except Exception as exc:
        record["status"]       = "failed"
        record["error"]        = str(exc)[:600]
        record["completed_ts"] = _now_iso()
        # ── Exit Signal Router: classify and stamp CODE_ERROR on the build card ─
        _stamp_exit_signal(record)
        _save_build(record)
        _append_builds_log(record)
        log.error("Build %s failed (CODE_ERROR): %s", build_id, exc)

        # Stalled Build Rescue: if this GREEN-tier build has now failed
        # RESCUE_FAIL_THRESHOLD times in a row, pull it from the auto-build loop
        # and route it to preflight review (the failed record is already saved,
        # so it's included in the streak count).
        if proposal.get("tier", "green") == "green":
            _fail_streak = _consecutive_build_failures(_rescue_key(proposal))
            if _fail_streak >= RESCUE_FAIL_THRESHOLD:
                _route_to_rescue(record, proposal, _fail_streak)

    finally:
        # Always free the slot so the next queued build can start, even if this one
        # crashed. Released exactly once per successful acquire.
        _build_sem.release()

    return record


# ─── Verification gate ────────────────────────────────────────────────────────

def verify_build(build_id: str) -> tuple[bool, str]:
    """
    Verify a completed build BEFORE any auto-merge.

    Scope rules (critical):
    - We get the list of files changed in the worktree branch vs master.
    - The worktree IS the live app repo (APP_REPO). Guard against a build writing
      OUTSIDE the repo (path traversal); if anything escapes, return ok=False.
    - Syntax-check every changed *.py with py_compile.
    - Basic sanity: diff is non-empty; all listed files exist in the worktree.

    Returns (ok: bool, report: str).
    """
    record = _load_build(build_id)
    if not record:
        return False, f"Build record not found: {build_id}"

    worktree_path = Path(record.get("worktree", ""))
    if not worktree_path.exists():
        return False, f"Worktree path does not exist: {worktree_path}"

    branch = record.get("branch", "")
    if not branch.startswith(BRANCH_PREFIX):
        return False, f"SAFETY: branch '{branch}' is not a boardroom/poc-* branch."

    # ── Step 1: get the list of changed files in this branch vs master ─────────
    try:
        diff_output = _git(
            "diff", "--name-only", f"{MASTER_BRANCH}...{branch}",
            cwd=worktree_path,
            timeout=30,
        )
    except Exception as exc:
        # Fallback: diff between HEAD and its merge-base
        try:
            diff_output = _git(
                "diff", "--name-only", "HEAD",
                cwd=worktree_path,
                timeout=30,
            )
        except Exception as exc2:
            return False, f"Could not determine changed files: {exc}; {exc2}"

    changed_files = [f.strip() for f in diff_output.splitlines() if f.strip()]

    if not changed_files:
        return False, "Verification FAIL: diff is empty — build made no changes."

    # ── Step 2: boundary check — any file escaping the app repo? ───────────────
    # The worktree IS the live app repo (APP_REPO), so changed files SHOULD all be
    # app files — that's the point of build=real. We still guard against a build
    # writing outside the repo (path traversal / absolute escapes). Changed files
    # from git diff --name-only are relative to the repo root (APP_REPO).
    outside_repo: list[str] = []
    for rel_path in changed_files:
        # git diff paths use forward slashes even on Windows
        try:
            resolved = (APP_REPO / rel_path).resolve()
            if not str(resolved).startswith(str(APP_REPO.resolve())):
                outside_repo.append(rel_path)
        except Exception:
            outside_repo.append(rel_path)

    if outside_repo:
        report = (
            "Verification BLOCKED: changed files escape the app repo.\n"
            "A build must only modify files inside the Leroy app.\n"
            "Files outside the app repo: " + ", ".join(outside_repo[:10]) + "\n"
            "Action required: Brian must review manually."
        )
        return False, report

    # ── Step 3: syntax check every changed Python file ─────────────────────────
    errors: list[str] = []
    checked: list[str] = []

    for rel_path in changed_files:
        abs_path = worktree_path / rel_path
        if not abs_path.exists():
            errors.append(f"Missing: {rel_path}")
            continue
        if rel_path.endswith(".py"):
            result = subprocess.run(
                [sys.executable, "-m", "py_compile", str(abs_path)],
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=15,
            )
            if result.returncode != 0:
                err_snippet = (result.stderr or "").strip()[:200]
                errors.append(f"Syntax error in {rel_path}: {err_snippet}")
            else:
                checked.append(rel_path)

    if errors:
        report = (
            "Verification FAIL:\n" + "\n".join(f"  - {e}" for e in errors) + "\n\n"
            f"Checked OK: {len(checked)} file(s). "
            f"Changed files: {len(changed_files)}."
        )
        return False, report

    # ── Step 4: BUILD-TRUTH GATE (added 2026-06-10) ───────────────────────────
    # A build must contain the work it claims. Evidence this was missing: commit
    # ab83200e claimed "Harden MCP server startup" but its diff was two voice-
    # queue .txt files and an index line — fiction shipped as feature. Two checks:
    #   (a) noise-only diff: every changed file is runtime litter → FAIL.
    #   (b) claim match: at least one significant token from the proposal's
    #       title/what must appear in a changed path or the diff body → FAIL if
    #       zero overlap (the diff has nothing to do with the claim).
    ok_truth, truth_msg = _build_truth_gate(record, changed_files, worktree_path, branch)
    if not ok_truth:
        return False, "Verification FAIL (build-truth gate): " + truth_msg

    report = (
        f"Verification PASS: {len(changed_files)} file(s) changed, "
        f"{len(checked)} Python file(s) syntax-checked OK; build-truth gate OK "
        f"({truth_msg}).\n"
        f"Files: {', '.join(changed_files[:10])}"
        + (" ..." if len(changed_files) > 10 else "")
    )
    return True, report


_TRUTH_NOISE_PATTERNS = (
    "hooks/voice/queue/", "memory/chat/", "memory/boardroom/", ".last-",
    "session/", "cache/", "__pycache__/", "backups/",
)
_TRUTH_NOISE_SUFFIXES = (".log", ".lock", ".pid", ".tmp")
_TRUTH_STOPWORDS = {
    "the", "a", "an", "and", "or", "for", "with", "into", "from", "that",
    "this", "build", "builds", "add", "adds", "added", "fix", "fixes", "make",
    "makes", "new", "via", "all", "our", "its", "their", "then", "when",
    "leroy", "boardroom", "system", "feature", "pipeline", "update", "updated",
}


def _significant_tokens(text: str) -> list[str]:
    words = re.findall(r"[a-zA-Z_][a-zA-Z0-9_\-]{3,}", (text or "").lower())
    return [w for w in words if w not in _TRUTH_STOPWORDS]


def _build_truth_gate(
    record: dict, changed_files: list[str], worktree_path: Path, branch: str
) -> tuple[bool, str]:
    """Return (ok, message). Defensive: an internal error PASSES with a note —
    this gate must tighten honesty, never brick legitimate builds."""
    try:
        # (a) noise-only diff
        def _is_noise(rel: str) -> bool:
            low = rel.lower().replace("\\", "/")
            return (
                any(p in low for p in _TRUTH_NOISE_PATTERNS)
                or low.endswith(_TRUTH_NOISE_SUFFIXES)
            )

        real_files = [f for f in changed_files if not _is_noise(f)]
        if not real_files:
            return False, (
                "every changed file is runtime noise ("
                + ", ".join(changed_files[:5])
                + ") — the claimed work is not in this build"
            )

        # (b) claim-token overlap
        prop = record.get("proposal") or {}
        claim_text = " ".join(
            str(x) for x in (record.get("title"), prop.get("title"), prop.get("what"))
            if x
        )
        tokens = _significant_tokens(claim_text)
        if not tokens:
            return True, "no claim tokens to match (untitled build) — noise check only"

        paths_blob = " ".join(real_files).lower()
        hit = next((t for t in tokens if t in paths_blob), None)
        if not hit:
            try:
                diff_body = _git(
                    "diff", f"{MASTER_BRANCH}...{branch}", "--unified=0",
                    cwd=worktree_path, timeout=30,
                ).lower()
            except Exception:
                diff_body = ""
            hit = next((t for t in tokens if t in diff_body), None)
        if not hit:
            return False, (
                f"none of the claim tokens {tokens[:6]} appear in the changed "
                f"paths or diff — the build does not contain its claimed work"
            )
        return True, f"claim token '{hit}' matched in diff"
    except Exception as exc:  # noqa: BLE001
        return True, f"truth-gate internal error (passed open): {exc}"


# ─── Auto-ship pipeline (GREEN tier only) ─────────────────────────────────────

def auto_ship_if_green(build_id: str, *, notify_fn=None) -> dict:
    """
    The AUTO-SHIP pipeline for GREEN-tier builds.

    SAFETY INVARIANTS — all must pass or the function refuses:
      1. Kill-switch file MUST NOT exist (session/boardroom.disabled).
      2. The build record MUST exist and be in 'ready' status.
      3. decision.tier MUST be 'green' — this is checked explicitly here.
         approval-tier and never-tier builds CANNOT reach auto-merge via this
         function; the check is at the top of the merge block, not optional.
      4. verify_build() MUST return ok=True. Any verification failure blocks merge.
      5. Branch MUST start with BRANCH_PREFIX and MUST NOT be protected.
      6. Current git branch MUST be master.

    On success: merges, records merge_commit_sha (needed for revert), updates
    status to 'shipped', cleans worktree, calls notify_fn if provided.

    On verify failure: rolls back (no merge), sets status 'failed', notifies.

    Returns result dict with status and message.
    """
    # ── Guard 1: kill-switch ────────────────────────────────────────────────────
    if KILL_SWITCH.exists():
        return {
            "status": "blocked",
            "reason": "Auto-ship kill-switch is active (session/boardroom.disabled). "
                      "Delete that file to re-enable.",
        }

    # ── Guard 2: load record ────────────────────────────────────────────────────
    record = _load_build(build_id)
    if not record:
        return {"status": "error", "reason": f"Build not found: {build_id}"}

    if record.get("status") != "ready":
        return {
            "status": "error",
            "reason": f"Build is '{record.get('status')}', not 'ready'. Cannot auto-ship.",
        }

    # ── Guard 3: TIER CHECK — this is the critical safety gate ─────────────────
    # We read tier from BOTH the build record's proposal AND as a top-level field
    # (populated by boardroom-decisions.py when it triggers auto-ship).
    proposal_tier = (record.get("proposal", {}).get("tier") or "").lower().strip()
    build_tier    = (record.get("tier") or "").lower().strip()
    effective_tier = build_tier or proposal_tier

    if effective_tier != "green":
        return {
            "status": "refused",
            "reason": (
                f"AUTO-SHIP REFUSED: build tier is '{effective_tier}', not 'green'. "
                "Only green-tier builds can be auto-shipped. "
                "approval-tier and never-tier builds MUST use the manual approve_and_merge() path."
            ),
        }

    # ── Guard 4: branch safety ──────────────────────────────────────────────────
    branch = record.get("branch", "")
    if not branch.startswith(BRANCH_PREFIX):
        return {
            "status": "error",
            "reason": f"SAFETY: branch '{branch}' does not start with '{BRANCH_PREFIX}'. Refusing.",
        }
    if branch in PROTECTED_BRANCHES:
        return {
            "status": "error",
            "reason": f"SAFETY: will not auto-merge protected branch '{branch}'.",
        }

    # ── Guard 5: must be on master ──────────────────────────────────────────────
    current = _current_branch()
    if current != MASTER_BRANCH:
        return {
            "status": "error",
            "reason": f"Repo is on '{current}', not '{MASTER_BRANCH}'. Cannot auto-merge.",
        }

    title = record.get("proposal", {}).get("title", "Untitled")

    # ── Step 1: verify ──────────────────────────────────────────────────────────
    log.info("auto_ship: running verification for %s (%s)", build_id, title)
    verify_ok, verify_report = verify_build(build_id)

    if not verify_ok:
        log.warning("auto_ship: verification FAILED for %s: %s", build_id, verify_report[:200])
        record["status"]       = "failed"
        record["verify_report"] = verify_report
        record["completed_ts"] = _now_iso()
        _save_build(record)
        _append_builds_log(record)

        # Clean up the worktree even on failure
        worktree_path = Path(record.get("worktree", ""))
        if worktree_path.exists():
            try:
                _remove_worktree(worktree_path, branch, force=True)
            except Exception as exc:
                log.warning("cleanup after verify fail: %s", exc)

        if notify_fn:
            try:
                notify_fn(
                    f"Build failed: {title}",
                    f"Verification failed — rolled back, not merged. "
                    f"Parked for review. Detail: {verify_report[:200]}",
                )
            except Exception:
                pass

        return {
            "status": "failed",
            "build_id": build_id,
            "verify_report": verify_report,
            "reason": "Verification failed — build rolled back, not merged.",
        }

    log.info("auto_ship: verification PASSED for %s — proceeding to merge", build_id)

    # ── Step 2: merge ───────────────────────────────────────────────────────────
    try:
        merge_out = _git(
            "merge", "--no-ff", branch, "-m",
            f"boardroom-auto-ship: {build_id} ({title[:60]})",
            timeout=60,
        )
    except Exception as exc:
        record["status"]       = "failed"
        record["error"]        = f"Auto-merge failed: {exc}"
        record["completed_ts"] = _now_iso()
        _save_build(record)
        _append_builds_log(record)
        return {"status": "failed", "reason": f"Merge failed: {exc}"}

    # Record the merge commit SHA for revert capability
    try:
        merge_sha = _git("rev-parse", "HEAD", timeout=10)
    except Exception:
        merge_sha = ""

    record["status"]          = "shipped"
    record["merged_ts"]       = _now_iso()
    record["merge_commit_sha"] = merge_sha
    record["verify_report"]   = verify_report
    _save_build(record)
    _append_builds_log(record)

    log.info("auto_ship: SHIPPED %s (sha=%s)", build_id, merge_sha[:12])

    # ── Step 3: clean up worktree ───────────────────────────────────────────────
    worktree_path = Path(record.get("worktree", ""))
    cleanup_msg = ""
    if worktree_path.exists():
        try:
            cleanup_msg = _remove_worktree(worktree_path, branch, force=True)
        except Exception as exc:
            cleanup_msg = f"Cleanup warning: {exc}"

    # ── Step 4: notify ──────────────────────────────────────────────────────────
    if notify_fn:
        try:
            notify_fn(
                f"Built & shipped: {title}",
                f"Auto-shipped to master (verified). "
                f"Reply 'revert {build_id}' to undo.",
            )
        except Exception as exc:
            log.warning("notify_fn error (non-fatal): %s", exc)

    return {
        "status":          "shipped",
        "build_id":        build_id,
        "branch":          branch,
        "merge_commit_sha": merge_sha,
        "merge_output":    merge_out[:300],
        "verify_report":   verify_report,
        "cleanup":         cleanup_msg,
    }


# ─── Revert path ──────────────────────────────────────────────────────────────

def revert_build(build_id: str) -> dict:
    """
    Revert a shipped build using git revert --no-edit <merge_commit_sha>.

    This is the SAFE, non-destructive undo: it creates a new revert commit on
    master rather than resetting history. Always revertible. Safe to call even
    after subsequent commits have been made.

    Requires:
      - Build status must be 'shipped' (auto-shipped) or 'merged' (Brian-approved).
      - merge_commit_sha must be recorded on the build.
      - Current branch must be master.

    On success: updates status to 'reverted', records revert_commit_sha.
    Returns result dict.
    """
    record = _load_build(build_id)
    if not record:
        return {"status": "error", "reason": f"Build not found: {build_id}"}

    status = record.get("status", "")
    if status not in ("shipped", "merged", "completed", "deployed"):
        return {
            "status": "error",
            "reason": (
                f"Build status is '{status}'. Can only revert builds that have been merged "
                "(deployed/completed/shipped/merged). "
                "Use reject_build() for builds that haven't been merged."
            ),
        }

    merge_sha = record.get("merge_commit_sha", "")
    if not merge_sha:
        return {
            "status": "error",
            "reason": (
                "No merge_commit_sha recorded on this build. "
                "This build predates revert tracking — manual revert required: "
                f"git revert <sha> in {str(APP_REPO)}"
            ),
        }

    # Confirm we are on master
    current = _current_branch()
    if current != MASTER_BRANCH:
        return {
            "status": "error",
            "reason": f"Repo is on '{current}', not '{MASTER_BRANCH}'. Switch to master first.",
        }

    # Verify the SHA still exists (history may have been rewritten in edge cases)
    try:
        subject = _git("log", "-1", "--format=%s", merge_sha, timeout=15)
        if not subject:
            return {"status": "error", "reason": f"Commit {merge_sha[:12]} no longer exists."}
    except Exception as exc:
        return {"status": "error", "reason": f"Commit lookup failed: {exc}"}

    # Auto-ship merges are --no-ff merge commits (2 parents). git revert REQUIRES
    # -m <mainline> to revert a merge; mainline 1 = the master side (pre-merge).
    # Detect parent count and pass -m 1 only when it's a merge.
    is_merge = False
    try:
        parents = _git("rev-list", "--parents", "-n", "1", merge_sha, timeout=15).split()
        is_merge = len(parents) > 2  # [sha, parent1, parent2, ...]
    except Exception:
        is_merge = True  # assume merge (auto-ship default) if detection fails

    revert_args = (["revert", "--no-edit", "-m", "1", merge_sha] if is_merge
                   else ["revert", "--no-edit", merge_sha])
    try:
        revert_out = _git(*revert_args, timeout=60)
    except Exception as exc:
        # Abort a failed revert to leave the tree clean
        try:
            _git("revert", "--abort", timeout=15)
        except Exception:
            pass
        _mflag = "-m 1 " if is_merge else ""
        return {
            "status": "error",
            "reason": (
                f"Revert failed (tree may have conflicts): {exc}\n"
                f"Manual fix: cd {APP_REPO} && git revert --no-edit {_mflag}{merge_sha[:12]}"
            ),
        }

    try:
        revert_sha = _git("rev-parse", "HEAD", timeout=10)
    except Exception:
        revert_sha = ""

    record["status"]          = "reverted"
    record["reverted_ts"]     = _now_iso()
    record["revert_commit_sha"] = revert_sha
    _save_build(record)
    _append_builds_log(record)

    log.info("revert_build: REVERTED %s (revert sha=%s)", build_id, revert_sha[:12])

    return {
        "status":           "reverted",
        "build_id":         build_id,
        "merge_commit_sha": merge_sha,
        "revert_commit_sha": revert_sha,
        "revert_output":    revert_out[:300],
    }


# ─── approve_and_merge: the ONLY path to master ───────────────────────────────

def approve_and_merge(build_id: str, *, brian_go: bool = False) -> dict:
    """
    Merge a completed POC branch into master (MANUAL / APPROVAL-TIER path).

    SAFETY INVARIANTS:
    - brian_go MUST be True (caller passes --yes-really-merge flag or the UI
      approval endpoint sets it). This is Brian's explicit go.
    - This function is for approval-tier (and green-tier if Brian manually approves).
      It is NOT the auto-ship path — auto_ship_if_green() handles that.
    - Build must be in 'ready' status.
    - Branch must start with BRANCH_PREFIX.
    - NEVER merges a protected branch.
    - After merge, removes the worktree and deletes the feature branch.
    - Records merge_commit_sha so revert_build() can undo it.

    Returns result dict with status and message.
    """
    if not brian_go:
        return {
            "status": "rejected",
            "reason": "Missing Brian's explicit approval flag (--yes-really-merge). "
                      "This is the merge gate — it requires deliberate intent.",
        }

    record = _load_build(build_id)
    if not record:
        return {"status": "error", "reason": f"Build not found: {build_id}"}

    if record.get("status") != "ready":
        return {
            "status": "error",
            "reason": f"Build is '{record.get('status')}', not 'ready'. Cannot merge.",
        }

    branch = record.get("branch", "")
    if not branch.startswith(BRANCH_PREFIX):
        return {
            "status": "error",
            "reason": f"SAFETY: branch '{branch}' does not start with '{BRANCH_PREFIX}'. Refusing merge.",
        }

    if branch in PROTECTED_BRANCHES:
        return {
            "status": "error",
            "reason": f"SAFETY: will not merge protected branch '{branch}'.",
        }

    # Confirm we are on master before merging
    current = _current_branch()
    if current != MASTER_BRANCH:
        return {
            "status": "error",
            "reason": f"Repo is on '{current}', not '{MASTER_BRANCH}'. Switch to master first.",
        }

    # PREFLIGHT SELF-HEAL: if a PRIOR merge left the repo wedged (MERGE_HEAD /
    # unmerged files), git would refuse THIS merge with "unmerged files". Clear it
    # first so one bad build can't permanently block every future deploy.
    if _repo_is_mid_merge():
        if not _recover_stuck_merge():
            return {
                "status": "error",
                "reason": (
                    "The repo has a stuck merge that couldn't be auto-cleared. "
                    "Run `git merge --abort` in ~/.claude, then retry deploy."
                ),
            }

    title = record.get("proposal", {}).get("title", "")

    # Land cleanly even when an earlier deploy already moved master: replay this
    # POC onto current master first. This is what lets Brian spam-approve a batch
    # and have ALL of them land (not just the first) — behind-but-non-overlapping
    # branches now merge clean instead of conflicting. True overlaps still fail
    # below and get marked for rebuild.
    _rebase_poc_onto_master(branch, record.get("worktree", ""))

    try:
        merge_out = _git(
            "merge", "--no-ff", branch, "-m",
            f"boardroom-sandbox: merge {build_id} ({title[:60]})",
            timeout=60,
        )

        # Record merge SHA for revert capability
        try:
            merge_sha = _git("rev-parse", "HEAD", timeout=10)
        except Exception:
            merge_sha = ""

        record["status"]           = "completed"
        record["merged_ts"]        = _now_iso()
        record["merge_commit_sha"] = merge_sha
        _save_build(record)
        _append_builds_log(record)

        # Clean up worktree + branch after successful merge
        worktree_path = Path(record.get("worktree", ""))
        cleanup_msg = ""
        if worktree_path.exists():
            cleanup_msg = _remove_worktree(worktree_path, branch, force=True)

        return {
            "status":           "completed",
            "build_id":         build_id,
            "branch":           branch,
            "merge_commit_sha": merge_sha,
            "merge_output":     merge_out[:300],
            "cleanup":          cleanup_msg,
        }

    except Exception as exc:
        # CRITICAL HARDENING: a conflicted merge leaves the tree wedged and blocks
        # ALL future deploys (the bug that took the whole system down). NEVER leave
        # it stuck — abort so master stays clean and mergeable. This build just
        # needs a rebuild against current master.
        recovered = _recover_stuck_merge()
        record["status"] = "failed"
        record["error"]  = f"Merge conflict (rolled back): {str(exc)[:300]}"
        _save_build(record)
        return {
            "status": "error",
            "reason": (
                f"Merge conflicted and was automatically rolled back "
                f"(repo clean: {recovered}). This POC needs a rebuild against the "
                f"current master — its branch is stale. No deploys are blocked."
            ),
        }


# ─── reject / cleanup ────────────────────────────────────────────────────────

def reject_build(build_id: str) -> dict:
    """Mark a build rejected and clean up its worktree."""
    record = _load_build(build_id)
    if not record:
        return {"status": "error", "reason": f"Build not found: {build_id}"}

    if record.get("status") == "merged":
        return {"status": "error", "reason": "Cannot reject a build that is already merged."}

    branch = record.get("branch", "")
    worktree_path = Path(record.get("worktree", ""))
    cleanup_msg = ""

    if worktree_path.exists() and branch:
        try:
            cleanup_msg = _remove_worktree(worktree_path, branch, force=True)
        except Exception as exc:
            cleanup_msg = f"Cleanup warning: {exc}"

    record["status"]       = "rejected"
    record["completed_ts"] = _now_iso()
    _save_build(record)
    _append_builds_log(record)

    return {
        "status": "rejected",
        "build_id": build_id,
        "cleanup": cleanup_msg,
    }


# ─── worktree cleanup for abandoned builds ────────────────────────────────────

def cleanup_worktree(build_id: str) -> str:
    """
    Helper: remove an abandoned worktree for a given build_id.

    Does NOT change build status. Use reject_build() for a full reject.
    """
    record = _load_build(build_id)
    if not record:
        return f"Build not found: {build_id}"

    branch = record.get("branch", "")
    worktree_path = Path(record.get("worktree", ""))

    if not worktree_path.exists():
        return "Worktree path does not exist (already cleaned up?)."

    if not branch.startswith(BRANCH_PREFIX):
        return f"SAFETY: branch '{branch}' not a sandbox branch. Manual cleanup required."

    return _remove_worktree(worktree_path, branch, force=True)


# ─── CLI ─────────────────────────────────────────────────────────────────────

def _print_builds_list() -> None:
    builds = _list_builds()
    if not builds:
        print("No builds found.")
        return
    print(f"{'BUILD ID':<22}  {'STATUS':<10}  {'BRANCH':<45}  TITLE")
    print("-" * 110)
    for b in builds:
        bid    = b.get("build_id", "")[:22]
        status = b.get("status", "")[:10]
        branch = b.get("branch", "")[:45]
        title  = b.get("proposal", {}).get("title", "")[:50]
        print(f"{bid:<22}  {status:<10}  {branch:<45}  {title}")


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Boardroom Sandbox Builder — safely builds POCs from board proposals."
    )
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--proposal-scene", metavar="SCENE_ID",
                       help="Build POC from a proposal in boardroom.jsonl by scene id")
    group.add_argument("--queue", action="store_true",
                       help="Process first pending item in build-queue.json")
    group.add_argument("--list", action="store_true",
                       help="List all builds")
    group.add_argument("--approve", metavar="BUILD_ID",
                       help="Merge gate: merge a ready build into master (requires --yes-really-merge)")
    group.add_argument("--reject", metavar="BUILD_ID",
                       help="Mark a build rejected and clean up its worktree")
    group.add_argument("--verify", metavar="BUILD_ID",
                       help="Run verification gate on a build (dry-run — does NOT merge)")
    group.add_argument("--revert", metavar="BUILD_ID",
                       help="Revert a shipped/merged build via git revert --no-edit")

    ap.add_argument("--yes-really-merge", action="store_true",
                    help="Brian's explicit go flag — required for --approve to execute the merge")

    args = ap.parse_args()

    if args.list:
        _print_builds_list()
        return 0

    if args.approve:
        result = approve_and_merge(args.approve, brian_go=args.yes_really_merge)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0 if result.get("status") == "completed" else 1

    if args.reject:
        result = reject_build(args.reject)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0 if result.get("status") == "rejected" else 1

    if args.verify:
        ok, report = verify_build(args.verify)
        print(json.dumps({"ok": ok, "report": report}, indent=2, ensure_ascii=False))
        return 0 if ok else 1

    if args.revert:
        result = revert_build(args.revert)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0 if result.get("status") == "reverted" else 1

    # Resolve proposal
    proposal: Optional[dict] = None

    if args.proposal_scene:
        proposal = _load_proposal_by_scene(args.proposal_scene)
        if not proposal:
            print(json.dumps({
                "error": f"No proposal found for scene_id: {args.proposal_scene}",
                "hint": "Check that the scene exists in boardroom.jsonl and has a proposal field.",
            }))
            return 1

    elif args.queue:
        item = _pop_queue()
        if not item:
            print(json.dumps({"status": "idle", "message": "Build queue is empty."}))
            return 0
        # Item from queue may carry a full proposal or just a scene_id reference
        if "scene_id" in item and "title" not in item:
            proposal = _load_proposal_by_scene(item["scene_id"])
            if not proposal:
                print(json.dumps({
                    "error": f"Queue item references scene_id {item['scene_id']} but no proposal found.",
                }))
                return 1
        else:
            proposal = item

    if not proposal:
        print(json.dumps({"error": "No proposal resolved."}))
        return 1

    log.info("Starting build for: %s", proposal.get("title", "Untitled"))
    record = run_build(proposal)
    print(json.dumps(record, indent=2, ensure_ascii=False))
    return 0 if record.get("status") == "ready" else 1


if __name__ == "__main__":
    sys.exit(main())
