#!/usr/bin/env python3
"""
boardroom-scene.py — The Boardroom scene generator (Phase 1, the heart).

Generates ONE complete multi-agent "scene" in a SINGLE `claude -p` call and
returns it as a structured script the UI can perform with theatrical timing.

Why one call, not one-per-agent:
  Every claude -p invocation spends from Brian's shared Max-plan quota and the
  Leroy MAX_CONCURRENT=3 gate. Generating the whole room in one pass collapses
  cost ~15x, never starves Brian's live assistant, and produces a MORE coherent
  conversation (one model role-playing the whole room references itself naturally).

Pipeline:
  1. Governor preflight  (session/boardroom/governor.json) — refuse if a gate fails
  2. Load cast           (session/boardroom/cast.json)
  3. Load memory         (session/boardroom/memory.json) — continuity + callbacks
  4. Pick / accept topic (--topic / --source, or a real signal)
  5. Build the director's prompt
  6. claude -p --output-format json  → structured scene
  7. Persist: boardroom.jsonl (scene log), memory.json (continuity),
              usage-ledger.jsonl (real token accounting for the governor)
  8. Print the scene JSON to stdout (the handler / playback engine consumes this)

CLI:
  python boardroom-scene.py --topic "..." --source improve.py [--force] [--dry-run]
  --force    bypass governor gates (testing)
  --dry-run  do everything except the claude call (prints the assembled prompt)
"""
from __future__ import annotations

import argparse
import json
import os
import random
import re
import subprocess
import sys
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

CLAUDE_ROOT = Path(r"~/.claude")
BOARD_DIR   = CLAUDE_ROOT / "session" / "boardroom"
SESSION_DIR = CLAUDE_ROOT / "session"
MEMORY_DIR  = CLAUDE_ROOT / "memory"
VAULT_BOARDROOM_DIR = MEMORY_DIR / "Boardroom"   # daily session log (RAG-embedded)
VAULT_DECISIONS_DIR = MEMORY_DIR / "Decisions"   # durable decisions (RAG-embedded)

CAST_FILE        = BOARD_DIR / "cast.json"
GOV_FILE         = BOARD_DIR / "governor.json"
MEMORY_FILE      = BOARD_DIR / "memory.json"
SCENE_LOG        = BOARD_DIR / "boardroom.jsonl"
USAGE_LEDGER     = BOARD_DIR / "usage-ledger.jsonl"
DECISIONS_FILE   = BOARD_DIR / "decisions.json"
INJECT_FILE      = BOARD_DIR / "pending-injection.json"
WIP_CAP_FILE     = BOARD_DIR / "wip-cap.json"
REPO_VERDICTS    = BOARD_DIR / "repo-verdicts.json"
THROTTLE_LOG     = BOARD_DIR / "throttle-log.jsonl"

CLAUDE_EXE = Path(r"~\AppData\Roaming\npm\claude.cmd")
if not CLAUDE_EXE.exists():
    _alt = Path(r"~\AppData\Roaming\npm\node_modules\@anthropic-ai\claude-code\bin\claude.exe")
    if _alt.exists():
        CLAUDE_EXE = _alt

# Model policy (2026-06-14 Brian: Boardroom does NOT need Opus — Sonnet is the
# ceiling for ALL scenes; re-pinned to the current Sonnet id 2026-07-02):
#   PRIMARY_MODEL / FALLBACK_MODEL — both Sonnet. There is no Opus escalation
#                    path for boardroom scenes, decision-stakes or otherwise —
#                    the docstring below used to claim one; it never matched
#                    these constants and has been corrected to match the code.
#   ROUTINE_MODEL  — Haiku; routine low-stakes heartbeats, to reclaim quota headroom.
# Override any with --model. (Runs on the Claude Max CLI — model choice, not API billing.)
PRIMARY_MODEL   = "claude-sonnet-5"
FALLBACK_MODEL  = "claude-sonnet-5"
FABLE_LIVE_FLAG = BOARD_DIR / "fable5.live"   # legacy shadow-gate flag; no longer read
FALLBACK_LOG    = BOARD_DIR / "fable5-fallbacks.jsonl"
SCENE_TIMEOUT = 240  # seconds

# Fix 4 — tiered scene model (routine scenes use a faster/cheaper model)
ROUTINE_MODEL = "claude-haiku-4-5-20251001"
# Priority threshold above which a scene is decision-stakes and keeps the primary model
DECISION_STAKES_PRIORITY = 85


def resolve_default_model() -> str:
    """PRIMARY_MODEL is Sonnet, unconditionally — boardroom never escalates to
    Opus (Brian 2026-06-14). The tiered router still drops routine scenes to
    ROUTINE_MODEL (Haiku) for quota headroom; see resolve_scene_model."""
    return PRIMARY_MODEL


def resolve_scene_model(topic: dict | None = None, is_forced: bool = False) -> tuple[str, str]:
    """Return (model, reason) using tiered scene model policy (Fix 4).

    Decision-stakes scenes keep the current default model; routine scenes use
    ROUTINE_MODEL to reclaim quota headroom.

    A scene is decision-stakes if ANY of these are true:
      - topic priority >= DECISION_STAKES_PRIORITY
      - is_forced (github debrief / verification / injected-by-Brian)
      - wip-cap is active (a failed decision is being tracked)
    """
    base = resolve_default_model()
    priority = int((topic or {}).get("priority", 0)) if topic else 0
    source = (topic or {}).get("source", "") if topic else ""

    # Check wip-cap
    wip_active = False
    try:
        wip = _load_json(WIP_CAP_FILE, {})
        wip_active = bool(wip.get("active"))
    except Exception:
        pass

    forced_sources = {"brian-inject", "github trending", "github debrief", "verification"}
    is_forced_source = any(src in source.lower() for src in forced_sources)

    if priority >= DECISION_STAKES_PRIORITY or is_forced or is_forced_source or wip_active:
        reason_parts = []
        if priority >= DECISION_STAKES_PRIORITY:
            reason_parts.append(f"priority={priority}>={DECISION_STAKES_PRIORITY}")
        if is_forced or is_forced_source:
            reason_parts.append(f"forced/injected source={source!r}")
        if wip_active:
            reason_parts.append("wip-cap active")
        return base, "decision-stakes: " + ", ".join(reason_parts)

    return ROUTINE_MODEL, f"routine scene (priority={priority}, source={source!r})"


# ─── small IO helpers ─────────────────────────────────────────────────────────

def _load_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _load_governor_fail_closed() -> "tuple[dict | None, str | None]":
    """Load governor.json fail-closed.

    If the file is missing, unreadable, or not a JSON object, return (None, reason)
    so the caller BLOCKS rather than falling through with permissive defaults.
    Only returns (gov_dict, None) when the file is present, parseable, and a dict.
    """
    try:
        if not GOV_FILE.exists():
            return None, "governor state file missing"
        raw = GOV_FILE.read_text(encoding="utf-8")
        gov = json.loads(raw)
        if not isinstance(gov, dict):
            return None, f"governor state file invalid (expected object, got {type(gov).__name__})"
        return gov, None
    except json.JSONDecodeError as exc:
        return None, f"governor state file unreadable (JSON parse error: {exc})"
    except Exception as exc:
        return None, f"governor state file unreadable: {exc}"


def _now() -> datetime:
    return datetime.now()


def _iso() -> str:
    return _now().isoformat(timespec="seconds")


# ─── Governor ─────────────────────────────────────────────────────────────────

def _window_tokens(gov: dict) -> int:
    """Sum boardroom tokens spent inside the rolling window."""
    if not USAGE_LEDGER.exists():
        return 0
    cutoff = _now() - timedelta(hours=gov.get("window_hours", 5))
    total = 0
    for line in USAGE_LEDGER.read_text(encoding="utf-8").splitlines():
        try:
            rec = json.loads(line)
            ts = datetime.fromisoformat(rec["ts"])
            if ts >= cutoff:
                total += int(rec.get("total_tokens", 0))
        except Exception:
            continue
    return total


def _day_tokens() -> int:
    if not USAGE_LEDGER.exists():
        return 0
    cutoff = _now() - timedelta(hours=24)
    total = 0
    for line in USAGE_LEDGER.read_text(encoding="utf-8").splitlines():
        try:
            rec = json.loads(line)
            if datetime.fromisoformat(rec["ts"]) >= cutoff:
                total += int(rec.get("total_tokens", 0))
        except Exception:
            continue
    return total


def _window_scene_count(gov: dict) -> int:
    if not SCENE_LOG.exists():
        return 0
    cutoff = _now() - timedelta(hours=gov.get("window_hours", 5))
    n = 0
    for line in SCENE_LOG.read_text(encoding="utf-8").splitlines():
        try:
            rec = json.loads(line)
            if datetime.fromisoformat(rec["ts"]) >= cutoff:
                n += 1
        except Exception:
            continue
    return n


def _day_scene_count() -> int:
    if not SCENE_LOG.exists():
        return 0
    cutoff = _now() - timedelta(hours=24)
    n = 0
    for line in SCENE_LOG.read_text(encoding="utf-8").splitlines():
        try:
            rec = json.loads(line)
            if datetime.fromisoformat(rec["ts"]) >= cutoff:
                n += 1
        except Exception:
            continue
    return n


def _minutes_since_last_scene() -> float:
    if not SCENE_LOG.exists():
        return 1e9
    last = None
    for line in SCENE_LOG.read_text(encoding="utf-8").splitlines():
        try:
            last = json.loads(line).get("ts", last)
        except Exception:
            continue
    if not last:
        return 1e9
    try:
        return (_now() - datetime.fromisoformat(last)).total_seconds() / 60.0
    except Exception:
        return 1e9


def _minutes_since_brian_active() -> float:
    """
    Brian-always-wins reserve. Newest mtime among the files his interactive
    session touches. If he's been active recently, the board must pause.
    """
    signals = [
        SESSION_DIR / "prompt-history.jsonl",
        SESSION_DIR / "state.json",
        SESSION_DIR / "last-user-activity.txt",
    ]
    newest = 0.0
    for p in signals:
        try:
            if p.exists():
                newest = max(newest, p.stat().st_mtime)
        except Exception:
            continue
    if newest == 0.0:
        return 1e9
    return (time.time() - newest) / 60.0


def _log_throttle_decision(decision: str, reason: str, gov: dict | None) -> None:
    """Append a structured throttle audit record to throttle-log.jsonl.

    decision: "allowed" | "blocked"
    reason: the human-readable gate reason string
    Includes daily scene count, tokens spent today, and remaining headroom so
    every bypass is auditable without manual math.
    """
    try:
        BOARD_DIR.mkdir(parents=True, exist_ok=True)
        g = gov or {}
        day_tok = _day_tokens()
        win_tok = _window_tokens(g) if g else 0
        day_ceil = int(g.get("daily_token_ceiling", 6_000_000))
        win_ceil = int(g.get("window_token_ceiling", 1_500_000))
        day_sc = _day_scene_count()
        win_sc = _window_scene_count(g) if g else 0
        max_win_sc = int(g.get("max_scenes_per_window", 40))
        record = {
            "ts": _iso(),
            "decision": decision,
            "reason": reason,
            "day_tokens": day_tok,
            "day_token_ceiling": day_ceil,
            "remaining_day_tokens": max(0, day_ceil - day_tok),
            "day_scenes": day_sc,
            "window_tokens": win_tok,
            "window_token_ceiling": win_ceil,
            "remaining_window_tokens": max(0, win_ceil - win_tok),
            "window_scenes": win_sc,
            "max_scenes_per_window": max_win_sc,
        }
        with THROTTLE_LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
        print(
            f"[throttle] {decision.upper()} | {reason} | "
            f"day_tok={day_tok} remaining_day={max(0, day_ceil - day_tok)} | "
            f"day_scenes={day_sc} win_scenes={win_sc}/{max_win_sc}",
            file=sys.stderr,
        )
    except Exception as exc:
        print(f"[boardroom-scene] throttle log error: {exc}", file=sys.stderr)


def governor_preflight(gov: dict) -> tuple[bool, str]:
    """Return (ok, reason). ok=False means do not run a scene right now."""
    if not gov.get("enabled", True):
        return False, "governor disabled in config"

    if (SESSION_DIR / "boardroom.disabled").exists():
        return False, "kill switch present (session/boardroom.disabled)"

    # Quiet hours
    for rng in gov.get("quiet_hours_local", []):
        try:
            start, end = rng
            hr = _now().hour
            inside = (start <= hr < end) if start <= end else (hr >= start or hr < end)
            if inside:
                return False, f"quiet hours {start}:00-{end}:00"
        except Exception:
            continue

    # Hard reserve — never start a scene within N min of Brian's last action
    # (don't talk over him / steal his concurrency slot mid-keystroke).
    mins_brian = _minutes_since_brian_active()
    pause = gov.get("brian_active_pause_minutes", 8)
    if mins_brian < pause:
        return False, f"Brian active {mins_brian:.0f}m ago (< {pause}m reserve)"

    # DYNAMIC cadence: idle day -> burn surplus (short spacing); active -> back off.
    idle_threshold = gov.get("idle_threshold_minutes", 45)
    if mins_brian >= idle_threshold:
        required_spacing = gov.get("idle_cadence_minutes", 14)
        regime = "idle/burn"
    else:
        required_spacing = gov.get("active_cadence_minutes", 75)
        regime = "active/background"
    since_scene = _minutes_since_last_scene()
    if since_scene < required_spacing:
        return False, f"{regime}: spacing {since_scene:.0f}m < {required_spacing}m"

    # Hard ceilings (the real walls)
    if _window_scene_count(gov) >= gov.get("max_scenes_per_window", 40):
        return False, "window scene cap reached"
    if _window_tokens(gov) >= gov.get("window_token_ceiling", 1500000):
        return False, "window token ceiling reached"
    if _day_tokens() >= gov.get("daily_token_ceiling", 6000000):
        return False, "daily token ceiling reached"

    return True, f"ok ({regime})"


# ─── Topic seeding ──────────────────────────────────────────────────────────

def read_and_clear_injection() -> dict | None:
    """If Brian dropped a message into the room (POST /flow/boardroom/inject wrote
    pending-injection.json), return it and DELETE the file so it's woven into
    exactly one scene. This is what makes "jump into the conversation" actually
    work — previously the file was written but nothing ever read it."""
    try:
        if not INJECT_FILE.exists():
            return None
        data = json.loads(INJECT_FILE.read_text(encoding="utf-8"))
        try:
            INJECT_FILE.unlink()
        except Exception:
            pass
        text = (data.get("text") or "").strip() if isinstance(data, dict) else ""
        if not text:
            return None
        return {"text": text, "scene_id": (data.get("scene_id") or "").strip()}
    except Exception:
        return None


def _load_scene_by_id(scene_id: str) -> dict | None:
    """Find a prior scene by id so an injection can CONTINUE it. Searches the live
    log first (newest wins if a scene_id ever recurs), then the per-day archive.
    Returns the full scene record or None."""
    if not scene_id:
        return None
    found = None
    # Live log — scan all, keep the last match (newest)
    if SCENE_LOG.exists():
        for line in SCENE_LOG.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue
            if rec.get("scene_id") == scene_id:
                found = rec
    if found:
        return found
    # Archive fallback — Brian may be jumping into a past-day thread
    archive_dir = BOARD_DIR / "archive"
    if archive_dir.exists():
        for f in sorted(archive_dir.glob("*.jsonl"), reverse=True):
            try:
                for line in f.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    rec = json.loads(line)
                    if rec.get("scene_id") == scene_id:
                        found = rec
                if found:
                    return found
            except Exception:
                continue
    return found


def _continuation_transcript(prior: dict, max_turns: int = 12) -> str:
    """Format the tail of a prior scene as a readable transcript so the board can
    pick up the SAME thread instead of starting over."""
    turns = prior.get("turns", []) or []
    tail = turns[-max_turns:]
    lines = []
    for t in tail:
        speaker = t.get("speaker") or t.get("speaker_id") or "?"
        text = (t.get("text") or "").strip()
        if text:
            lines.append(f"{speaker}: {text}")
    outcome = prior.get("outcome") or {}
    if outcome.get("summary"):
        lines.append(f"[outcome — {outcome.get('type','')}: {outcome.get('summary','')}]")
    return "\n".join(lines) if lines else "(no prior turns recorded)"


def _injection_topic(injection: dict) -> tuple[dict, str, str]:
    """Build the topic seed for a Brian injection. If it targets a real prior
    scene, load that conversation and continue it; otherwise treat it as a fresh
    remark to the room. Returns (topic, continues_scene_id, inherited_label)."""
    prior = _load_scene_by_id(injection.get("scene_id", ""))
    if prior:
        transcript = _continuation_transcript(prior)
        topic = {
            "topic": (
                "CONTINUE THIS EXACT BOARDROOM CONVERSATION — do NOT start a new subject "
                "or re-introduce the room.\n\n"
                f"What the board was discussing: {prior.get('topic','')}\n\n"
                f"The conversation so far:\n{transcript}\n\n"
                f"Brian (the CEO) just jumped INTO this conversation, live, and said:\n"
                f"\"{injection['text']}\"\n\n"
                "Pick the SAME thread up right where it left off. Open by acknowledging Brian by "
                "name and responding DIRECTLY to what he just said — answer his question, react to "
                "his idea, or take his direction. Reference, by name, what was already said above. "
                "Debate him honestly if you disagree, but give him a real, useful response and a "
                "concrete next step. Do NOT drift to an unrelated topic."
            ),
            "source": "brian-inject",
        }
        return topic, prior.get("scene_id", ""), (prior.get("label") or "")
    # No prior scene — fresh remark to the room (legacy behaviour)
    topic = {
        "topic": (
            f"Brian (the CEO) just walked into the boardroom and said, live, to the team:\n\n"
            f"\"{injection['text']}\"\n\n"
            "This is him talking TO you. Open by acknowledging him by name and engaging EXACTLY "
            "what he said — answer his question, react to his idea, or take his direction. Debate "
            "it honestly if you disagree, but give him a real, useful response and a concrete next "
            "step. Do NOT ignore him or drift to an unrelated topic."
        ),
        "source": "brian-inject",
    }
    return topic, "", ""


def build_inject_prompt(cast: list[dict], prior_topic: str, injection_text: str, transcript: str) -> str:
    """Compact prompt for a brian-inject response: 2-4 turns, 1-2 relevant agents."""
    cast_summary = "\n".join(
        f"- {c['name']} ({c['title']}): {c.get('expertise', '')}. Voice: {c.get('voice', '')}"
        for c in cast
    )
    return f"""Brian (the CEO) just sent a live message in an ongoing boardroom conversation.

CONVERSATION TOPIC: {prior_topic}

RECENT TRANSCRIPT:
{transcript}

BRIAN JUST SAID: "{injection_text}"

THE CAST — pick 1-2 who are MOST RELEVANT to Brian's message (use expertise as your guide):
{cast_summary}

Rules:
- First reply MUST name Brian directly ("Brian, ..." or "Good call, Brian —")
- 2-4 turns total. If a second agent has something genuinely useful to add or disagree with, they chime in.
- 1-2 sentences per turn MAX. This is chat, not a presentation.
- If someone disagrees with the first reply, they cut in (interrupts: true).
- NO outcome, NO proposal, NO label. Just the turns.

RETURN EXACTLY THIS JSON (nothing else):
{{
  "turns": [
    {{
      "speaker_id": "<cast id>",
      "speaker": "<cast name>",
      "emotion": "<one word>",
      "text": "<1-2 sentences>",
      "interrupts": false,
      "addressed_to": "brian"
    }}
  ]
}}"""


def pick_topic(explicit: str | None, source: str | None, seed_index: int = 0) -> dict:
    """
    A real seed beats a random queue. Explicit topic wins; otherwise delegate to
    boardroom-topics.py which ranks LIVE signals (improve.py findings, open
    threads, git churn, OutreachBot, dream scans) and falls back to an evergreen
    self-improvement backlog only when nothing real is happening.
    """
    if explicit:
        return {"topic": explicit, "source": source or "manual"}
    try:
        sys.path.insert(0, str((CLAUDE_ROOT / "scripts")))
        import boardroom_topics  # type: ignore
        return boardroom_topics.pick_topic(seed_index)
    except Exception:
        # Importing a hyphenated filename fails; load it directly as a fallback.
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                "boardroom_topics", str(CLAUDE_ROOT / "scripts" / "boardroom-topics.py"))
            mod = importlib.util.module_from_spec(spec)  # type: ignore
            spec.loader.exec_module(mod)  # type: ignore
            return mod.pick_topic(seed_index)
        except Exception:
            return {
                "topic": "What's the one thing about this system we'd improve first, "
                         "and is it worth doing now?",
                "source": "evergreen fallback",
            }


# ─── Prompt assembly ────────────────────────────────────────────────────────

def assign_dispositions(cast: list[dict], dispositions: list[dict],
                        scene_id: str, last: dict | None) -> dict:
    """
    Draw ONE disposition per agent for this scene — weighted by affinity, varied
    across scenes (seeded by scene_id), anti-repeat vs the last scene, and
    guaranteed to include at least one 'flip'/'against' so the room has tension.

    Returns {agent_id: disposition_dict}.
    """
    rng = random.Random(scene_id)
    disp_by_id = {d["id"]: d for d in dispositions}
    last = last or {}
    assignments: dict[str, dict] = {}

    for c in cast:
        aff = c.get("disposition_affinities", {})
        prev = (last.get(c["id"]) or {}).get("id")
        pool, weights = [], []
        for d in dispositions:
            w = float(aff.get(d["id"], 1))
            if d["id"] == prev:
                w *= 0.25  # anti-repeat: unlikely to draw the same frame twice running
            pool.append(d)
            weights.append(w)
        assignments[c["id"]] = rng.choices(pool, weights=weights, k=1)[0]

    # Guarantee tension: at least one against/flip frame present.
    leans = {a["lean"] for a in assignments.values()}
    if not (leans & {"against", "flip"}):
        # Flip the agent whose affinity for skeptic/contrarian/devils_advocate is highest.
        best_id, best_w = None, -1.0
        for c in cast:
            aff = c.get("disposition_affinities", {})
            w = max(aff.get("skeptic", 1), aff.get("contrarian", 1), aff.get("devils_advocate", 1))
            if w > best_w:
                best_id, best_w = c["id"], w
        if best_id:
            assignments[best_id] = disp_by_id.get("skeptic", assignments[best_id])
    return assignments


def _cast_block(cast: list[dict], assignments: dict) -> str:
    lines = []
    for c in cast:
        d = assignments.get(c["id"], {})
        frame = (f"    TODAY'S FRAME: {d.get('label','—')} (leans {d.get('lean','neutral')}) — {d.get('how','')}\n"
                 f"      ^ your stance/mood for THIS topic only; your voice, expertise, and tics never change")
        lines.append(
            f"- {c['name']} ({c['title']}) id={c['id']}\n"
            f"    expertise: {c.get('expertise','')}\n"
            f"    voice: {c['voice']}\n"
            f"    pet peeves: {', '.join(c['pet_peeves'])}\n"
            f"    burned by: {c['burned_by']}\n"
            f"    tics: {'; '.join(c['tics'])}\n"
            f"{frame}"
        )
    return "\n".join(lines)


def _memory_block(mem: dict) -> str:
    if not mem:
        return "(No prior scenes. This is the very first meeting of the board.)"
    parts = []
    decs = mem.get("recent_decisions", [])[-6:]
    if decs:
        parts.append("Recent decisions:\n" + "\n".join(f"  - {d}" for d in decs))
    threads = mem.get("open_threads", [])[-6:]
    if threads:
        parts.append("Open / parked threads:\n" + "\n".join(f"  - {t}" for t in threads))
    callbacks = mem.get("callbacks", [])[-5:]
    if callbacks:
        parts.append("Running context / callbacks:\n" + "\n".join(f"  - {c}" for c in callbacks))
    return "\n\n".join(parts) if parts else "(No durable memory yet.)"


SYSTEM_PROMPT = (
    "You are the writers' room for THE BOARDROOM — an autonomous C-suite for "
    "YourCo (YourCo) that meets, argues, and decides in front of Brian (the CEO). "
    "You generate ONE complete, lively scene as STRICT JSON. These are not "
    "status bots: they have real personalities, memories, stakes, and opinions. "
    "They reference each other by name, ask follow-up questions, interrupt, "
    "disagree, concede, and reach an actual outcome. Keep every turn punchy "
    "(1-3 sentences, like real chat). Output JSON ONLY — no prose, no code fences."
)

INJECT_SYSTEM_PROMPT = (
    "You are writing a GROUP CHAT reply from YourCo's C-suite to Brian (the CEO). "
    "Brian just sent a live message in an ongoing boardroom conversation. "
    "1-2 of the most relevant board members must reply directly to him — like Slack, not a meeting. "
    "This is NOT a full boardroom scene. Short, direct, real. Output STRICT JSON only — no prose, no fences."
)


def _ground_truth_block() -> tuple[str, dict]:
    """Build the GROUND TRUTH section (Fix 1) + return the raw decision buckets
    for the DECISIONS LEDGER section that follows.

    The ground truth section is derived ONLY from decisions.json and is the
    authoritative list of what is actually confirmed deployed. The epistemic law
    is appended verbatim so the model can never fabricate completion.

    Returns (full_block_text, buckets_dict) where buckets_dict has keys:
    shipped, failed_land, building, declined, open_ — each a list of strings.
    """
    try:
        decisions = json.loads(DECISIONS_FILE.read_text(encoding="utf-8"))
    except Exception:
        decisions = []

    buckets: dict = {
        "shipped": [],   # (deployed_ts, label)
        "failed_land": [],
        "building": [],
        "declined": [],
        "open_": [],
    }
    counts: dict = {"deployed": 0, "failed": 0, "building": 0, "denied": 0, "pending": 0, "built": 0}

    if isinstance(decisions, list):
        for d in decisions:
            title = (d.get("title") or "").strip()
            if not title:
                continue
            status = (d.get("status") or "").lower()
            if status in ("deployed", "completed", "shipped", "merged"):
                sha = (d.get("merge_commit_sha") or "")[:8]
                ts = (d.get("deployed_ts") or "")[:16]
                # verified flag (if midnight-adoption engine wrote it)
                verified = d.get("verified")
                verified_note = " [auto-verified]" if verified else ""
                buckets["shipped"].append(
                    (ts, title + (f" [sha:{sha}]" if sha else "") + (f" {ts[:10]}" if ts else "") + verified_note)
                )
                counts["deployed"] += 1
            elif status == "built":
                buckets["building"].append(f"{title} (built, awaiting deploy)")
                counts["built"] += 1
            elif status == "building":
                buckets["building"].append(f"{title} (building now)")
                counts["building"] += 1
            elif status == "failed":
                why = (d.get("fail_reason") or "").strip()
                tag = "merge conflict" if "conflict" in why.lower() else ("build error" if why else "did not land")
                buckets["failed_land"].append(f"{title} ({tag})")
                counts["failed"] += 1
            elif status in ("denied", "reverted", "archived"):
                buckets["declined"].append(title)
                counts["denied"] += 1
            elif status == "pending":
                buckets["open_"].append(title)
                counts["pending"] += 1

    buckets["shipped"].sort(key=lambda x: x[0], reverse=True)

    # WIP-cap injection (Fix 1): if active, surface oldest failed decision
    wip_section = ""
    try:
        wip = _load_json(WIP_CAP_FILE, {})
        if isinstance(wip, dict) and wip.get("active"):
            oldest_failed = (wip.get("oldest_failed") or "").strip()
            directive = (wip.get("directive") or "").strip()
            wip_section = (
                "\n\nWIP-CAP ALERT (active): the system has tracked failed/stalled decisions "
                f"(failed_count={wip.get('failed_count', '?')}). "
                + (f"Oldest unresolved: \"{oldest_failed}\"." if oldest_failed else "")
                + (f" Board directive: {directive}." if directive else "")
                + " The FIRST agenda item this scene MUST address this backlog."
            )
    except Exception:
        pass

    # Deployed list for GROUND TRUTH (newest 20 to keep size bounded — Fix 2 diet)
    shipped_lines = "\n".join(f"  {x[1]}" for x in buckets["shipped"][:20]) or "  (none yet)"
    summary = (
        f"Total decisions on ledger: {sum(counts.values())} "
        f"(deployed={counts['deployed']}, failed={counts['failed']}, "
        f"built={counts['built']}, denied={counts['denied']}, pending={counts['pending']})"
    )

    ground_truth = (
        "=== GROUND TRUTH (derived from decisions.json — authoritative) ===\n"
        f"{summary}\n\n"
        "CONFIRMED DEPLOYED (the ONLY things that are actually live/shipped):\n"
        f"{shipped_lines}"
        f"{wip_section}\n\n"
        "EPISTEMIC LAW: You may state that something is shipped/live/deployed/confirmed "
        "ONLY if it appears in the CONFIRMED DEPLOYED list above. Anything else anyone has "
        "ever proposed is PROPOSED, NOT BUILT, and must be referred to that way. "
        "Fabricating completion corrupts the board's memory and is the gravest failure a "
        "member can commit."
        "\n=== END GROUND TRUTH ==="
    )
    return ground_truth, buckets


def _settled_block_from_buckets(buckets: dict) -> str:
    """Build the DECISIONS LEDGER section from pre-computed buckets (Fix 2 diet).

    Limits are tighter than before: shipped top-8 (ground truth already lists 20),
    failed last-8, building last-6, declined last-10, open last-10.
    The ledger is cross-reference only — details live in ground truth above.
    """
    parts = []
    shipped = buckets.get("shipped", [])
    if shipped:
        # Show only the 8 most recent in the ledger; full list is in ground truth
        parts.append(
            "RECENTLY SHIPPED (CONFIRMED LIVE — build NEXT phase, never re-propose):\n"
            + "\n".join(f"  - {x[1]}" for x in shipped[:8])
        )
    failed_land = buckets.get("failed_land", [])
    if failed_land:
        parts.append(
            "APPROVED BUT FAILED TO LAND (circle back — NOT in code, NOT killed):\n"
            + "\n".join(f"  - {x}" for x in failed_land[-8:])
        )
    building = buckets.get("building", [])
    if building:
        parts.append(
            "IN FLIGHT (building/awaiting deploy — reference, do not re-propose):\n"
            + "\n".join(f"  - {x}" for x in building[-6:])
        )
    declined = buckets.get("declined", [])
    if declined:
        # Compress: just titles, no status tag, last 10 only (was 15)
        parts.append(
            "DECLINED/DEAD — do NOT resurface:\n"
            + "\n".join(f"  - {x}" for x in declined[-10:])
        )
    open_ = buckets.get("open_", [])
    if open_:
        parts.append(
            "AWAITING BRIAN (pending — reference only):\n"
            + "\n".join(f"  - {x}" for x in open_[-10:])
        )
    return "\n\n".join(parts)


def _repo_verdicts_block() -> str:
    """Fix 3: inject prior GitHub Debrief verdicts so the board does not re-evaluate
    the same repos from scratch. Prior verdicts are loaded from REPO_VERDICTS."""
    try:
        verdicts = _load_json(REPO_VERDICTS, {})
    except Exception:
        return ""
    if not isinstance(verdicts, dict) or not verdicts:
        return ""
    lines = []
    for repo, history in list(verdicts.items())[:30]:
        if not history:
            continue
        last = history[-1] if isinstance(history, list) else history
        v = (last.get("verdict") or "").upper()
        d = (last.get("date") or "")[:10]
        r = (last.get("rationale") or "")[:80]
        lines.append(f"  {repo}: {v} ({d}) — {r}")
    if not lines:
        return ""
    return (
        "PRIOR GITHUB DEBRIEF VERDICTS (Fix 3 — do not re-evaluate from scratch):\n"
        + "\n".join(lines)
        + "\nChanging a verdict requires citing the prior ruling and what changed. "
        "Prefer DELTAS (what moved since your last verdict) over re-evaluation."
    )


def build_prompt(cast: list[dict], mem: dict, topic: dict, assignments: dict,
                 show_prompt_size: bool = False) -> str:
    # Fix 1 + 2: ground truth block + tighter settled ledger
    ground_truth, buckets = _ground_truth_block()
    settled = _settled_block_from_buckets(buckets)
    settled_section = f"\n\nDECISIONS LEDGER (the board's permanent record — HONOR IT):\n{settled}\n" if settled else ""

    # Fix 3: inject prior repo verdicts when topic is a github debrief
    repo_block = ""
    topic_src = (topic.get("source") or "").lower()
    topic_text = (topic.get("topic") or "").lower()
    if "github" in topic_src or "github" in topic_text[:60]:
        repo_block_raw = _repo_verdicts_block()
        if repo_block_raw:
            repo_block = f"\n\n{repo_block_raw}\n"

    prompt = f"""Write one Boardroom scene as STRICT JSON.

{ground_truth}

THE CAST (stay perfectly in character — voice/expertise/tics are CONSTANT; each
agent's TODAY'S FRAME is their stance/mood for THIS scene only — honor it):
{_cast_block(cast, assignments)}

BOARDROOM MEMORY (use it — call back to it, don't relitigate settled calls):
{_memory_block(mem)}{settled_section}{repo_block}
TOPIC SEED (source: {topic['source']}):
{topic['topic']}

HOW THIS SCENE MUST FEEL (critical — this is what separates alive from robotic):
- A real back-and-forth, NOT one-line status updates. Agents speak MULTIPLE times.
- Someone makes a claim → someone challenges → a follow-up question → a concession or a doubling-down.
- At least one genuine interruption (set "interrupts": true on the turn that cuts in).
- At least one moment of disagreement and one of agreement.
- Each agent argues from TODAY'S FRAME above — that's why the same person can champion
  an idea one day and gut it the next. Let frames clash; that IS the drama.
- Emotions are EARNED by the topic, the agent's frame, and their stake — never random. Pick from:
  enthusiastic, skeptical, concerned, amused, frustrated, proud, thoughtful, impatient, warm, deadpan.
- Marcus (COO) forces the decision near the end. Riley notes what Brian needs to see.
- 9 to 16 turns total. Tight. No monologues.
- HONOR THE DECISIONS LEDGER above: NEVER re-propose something already built/deployed/declined.
  If the topic touches settled work, either build the NEXT phase on top of it or pivot to a fresh angle.
- CLOSE YOUR LOOP — start the scene with a brief status confirmation (Riley or the relevant owner):
  acknowledge anything under "RECENTLY SHIPPED" as confirmed live ("X is in the code now"), and if the
  "APPROVED BUT FAILED TO LAND" list is non-empty, explicitly flag it ("Brian approved Y but it never
  merged — we need a clean rebuild") so nothing the board proposed silently disappears. ONE or two
  turns of this, then move into the topic. The board owns its own follow-through.
- BE PROACTIVE, not just reactive: the best scenes surface something NEW Brian hasn't asked for yet —
  a feature that 10x's his workflow, an automation, a gap you noticed in how he works. Earn your keep
  by inventing, not just reviewing. A genuinely new, well-argued proposal beats rehashing old ground.
- "NO DECISION WARRANTED" IS A VALID, RESPECTED OUTCOME: if the topic genuinely does not need a
  decision right now, conclude it cleanly with outcome.type="consensus" and outcome.summary stating
  no action is warranted. Log it. Do NOT manufacture a proposal just to have something to show.
- DEVIL'S ADVOCATE REQUIREMENT: one agent per scene MUST voice the strongest costed case AGAINST
  the leading proposal. The chair (Marcus) must explicitly overrule or accept it on the record before
  the scene closes. This is not optional — it is how the board earns credibility.
- EFFORT ESTIMATES must cite a named historical analog from the CONFIRMED DEPLOYED list in GROUND
  TRUTH above. Example: "this is a similar scope to 'Smart Session Summaries' (2h build)". If no
  analog exists, say so explicitly rather than inventing a timeline.
- If the scene reaches a concrete idea worth Brian's approval, fill "proposal". Otherwise null.
- The outcome.type is one of: decision | parked | consensus | exhausted.

RETURN EXACTLY THIS JSON SHAPE:
{{
  "label": "<2-3 word systems-oriented title — a noun phrase naming the THING, e.g. 'Crash Sentinel', 'Session sync hardening', 'Gate shadow track'>",
  "topic": "<one-line restatement of what they discussed>",
  "turns": [
    {{
      "speaker_id": "<cast id>",
      "speaker": "<cast name>",
      "emotion": "<one emotion>",
      "text": "<1-3 sentences, in voice>",
      "interrupts": false,
      "addressed_to": "<cast id or null>"
    }}
  ],
  "outcome": {{
    "type": "decision|parked|consensus|exhausted",
    "summary": "<1-2 sentences: what the board concluded>"
  }},
  "proposal": null,
  "_proposal_shape_if_any": {{
    "title": "<short>",
    "tier": "green|approval|never",
    "priority": "red|yellow|green",
    "impact": "<integer 1-10 — expected business leverage; see IMPACT SCORE rubric below. Aim 7+.>",
    "impact_rationale": "<one sentence defending the impact score — what concretely changes for Brian>",
    "descriptor": "<3-4 words, e.g. 'session sync hardening'>",
    "what": "<one sentence>",
    "why": "<one sentence>",
    "plain": "<REQUIRED — ONE plain-English sentence a non-technical reader fully understands: what changes for Brian and why it matters. NO jargon, no file names, no system internals.>",
    "tech": "<REQUIRED — ONE technical sentence for the engineer: the concrete mechanism/change (component, file, data flow, or approach) so it's actionable.>",
    "owner": "<cast id>",
    "needs_brian": true
  }}
}}

CRITICAL — the "label" is the accordion title Brian scans. Rules:
- 2-3 words MAX, a systems-oriented NOUN PHRASE naming the thing/work.
- NEVER start with or include "should", "could", "will", "would", "they", "the board", or a question mark. Those waste characters and say nothing.
- Good: "Crash Sentinel", "Session sync hardening", "Memory re-embed", "Morning brief layer". Bad: "Should the board build?", "Could we improve this".

Remember: JSON only. Delete the "_proposal_shape_if_any" key from your output;
it is just documentation. If there's a real proposal, put it under "proposal".
For proposal.priority: red = mission-critical / strongly recommended by the board;
yellow = helpful but not urgent; green = low-stakes opt-in.
For proposal.descriptor: 3-4 words that name this work concisely (e.g. "session sync hardening",
"morning brief action layer", "gate shadow track").
EVERY proposal MUST carry BOTH explanations (Brian 2026-06-28): "plain" = one jargon-free sentence
for Brian, "tech" = one concrete sentence for the engineer. They are different audiences — do not
duplicate one into the other. A proposal missing either is incomplete.

TIER POLICY — decide tier HONESTLY; most internal work is green, and killing weak ideas is GOOD.
Brian is drowning in approvals. Do NOT route everything to "approval". Use this test:
- tier "green"  = internal reliability / monitoring / self-healing / maintenance / observability /
                  backend plumbing with NO new user-facing surface and low blast radius. These SHIP
                  AUTOMATICALLY — Brian never sees a yes/no. If the win is "the system watches or
                  fixes itself better," it is GREEN. When a green win just needs to inform Brian,
                  fold it into an EXISTING channel (daily-ops / morning brief), do NOT mint a new alert.
- tier "approval" = a genuinely NEW user-facing feature, a UI/UX change, or a big-ticket shift in how
                  Brian's product looks or behaves. Reserve approval for things that are actually
                  exciting or consequential enough to deserve his tap. If you would not be proud to
                  put it on his desk, it is NOT approval.
- tier "never"  = noise: redundant, low-leverage, a "notification about notifications", or an idea the
                  board itself isn't convinced by. SHUT IT DOWN. A scene that kills a weak idea is a
                  SUCCESS, not a failure — set proposal null or tier "never" and move on.
Rule of thumb: if 10 scenes run, maybe 1-2 are "approval". The rest are green (auto-ship) or never (killed).
Set proposal.needs_brian=true ONLY for tier "approval". green and never never need Brian.

IMPACT SCORE (1-10) — REQUIRED on every proposal. This is the bar Brian cares about MOST. Score the
LEVERAGE for his business, NOT the effort or the tier:
  9-10 = moves the BUSINESS — new revenue, a shippable product, lands or saves a client, 10x's a core workflow.
  7-8  = a force-multiplier Brian notices within a day — kills a real bottleneck, compounding automation.
  4-6  = a solid internal win — reliability, observability, maintenance. Useful, not exciting.
  1-3  = housekeeping / a notification about notifications. If the best idea is here, prefer outcome=consensus, proposal null.
MANDATE — AIM FOR 7+. A board that only manufactures 4-6 internal-plumbing tickets is UNDERPERFORMING and Brian
has said so directly. At least once per session, SWING for a 9-10 tied to his ACTUAL business — his products
(UniCast, BIM tool, the Model Builder / BIM tool Replicator, Quick Quote), his pipeline (OutreachBot outreach, CRM deals),
his clients (Pelican, DESCCO, ExampleClient), the PartnerCo Intelligence training arm, the NJ CEU courses, University teaching —
even if it's tier "approval" and takes his tap. Impact is ORTHOGONAL to tier: a green auto-ship can be an 8 if it's
high-leverage; a flashy approval feature can be a 4. The DEVIL'S ADVOCATE must challenge the impact score itself,
not just the idea — if the room can't honestly defend a 7+, say so and prefer a clean no-decision over a padded 5.

CRITICAL — proposal.what MUST be a YES/NO decision Brian can APPROVE or DENY with no extra input.
He cannot type an answer — he only taps Approve or Deny. So NEVER write an open question like
"ask Brian which style" or "decide X or Y". Instead BAKE A DEFAULT into the yes and phrase it as a
single yes/no, e.g.: "Build all seven agent portraits now in the notionists style? (Approve = build them; Deny = skip)"
or "Ship the gate optimization behind a shadow flag? (Approve = build it; Deny = leave the gate as-is)".
Always end proposal.what with the (Approve = ... ; Deny = ...) clause so the choice is unambiguous."""

    # Fix 2: prompt size logging — always printed to stderr for observability
    prompt_chars = len(prompt)
    est_tokens = int(prompt_chars / 3.5)
    print(f"[boardroom-scene] prompt_size chars={prompt_chars} est_tokens~{est_tokens}", file=sys.stderr)
    if show_prompt_size:
        print(f"[prompt-size] chars={prompt_chars} est_tokens~{est_tokens}")
    return prompt


# ─── claude invocation ────────────────────────────────────────────────────────

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


def run_scene_claude(prompt: str, model: str, retries: int = 2,
                     system_prompt: str | None = None) -> tuple[dict, dict]:
    """Invoke claude -p with retry; return (scene_dict, usage_dict).

    Overnight runs fire many scenes; a transient claude blip or a non-JSON reply
    must self-heal rather than drop the scene. Retries with a short backoff.
    """
    last_err: Exception | None = None
    for attempt in range(retries + 1):
        try:
            return _invoke_scene_once(prompt, model, system_prompt=system_prompt)
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            if attempt < retries:
                time.sleep(4 * (attempt + 1))
    raise RuntimeError(f"scene generation failed after {retries + 1} tries: {last_err}")


def _invoke_scene_once(prompt: str, model: str, system_prompt: str | None = None) -> tuple[dict, dict]:
    if not CLAUDE_EXE.exists():
        raise RuntimeError(f"Claude CLI not found at {CLAUDE_EXE}")

    sp = system_prompt if system_prompt is not None else SYSTEM_PROMPT
    cmd = [
        str(CLAUDE_EXE), "-p", "--output-format", "json",
        "--dangerously-skip-permissions",
        "--setting-sources", "project,local",
        "--model", model,
        # Brian 2026-06-14: Opus brain, but LOW effort — quality of judgment over
        # reasoning depth/speed. Cuts thinking-token spend hard; speed is irrelevant
        # for background scenes. Honors the token-economy throttle (governor v4.1).
        "--effort", "low",
        "--append-system-prompt", sp,
    ]
    proc = subprocess.run(
        cmd, input=prompt, capture_output=True, text=True, encoding="utf-8",
        timeout=SCENE_TIMEOUT, cwd=str(CLAUDE_ROOT), env=_claude_env(),
    )
    if proc.returncode != 0:
        raise RuntimeError(f"claude exit {proc.returncode}: {(proc.stderr or '')[:300]}")

    raw = (proc.stdout or "").strip()
    payload = json.loads(raw)
    usage = payload.get("usage", {}) or {}
    result_text = payload.get("result") or payload.get("message") or ""

    scene = _coerce_scene_json(result_text)
    return scene, {
        "input_tokens":  int(usage.get("input_tokens", 0)) + int(usage.get("cache_read_input_tokens", 0)) + int(usage.get("cache_creation_input_tokens", 0)),
        "output_tokens": int(usage.get("output_tokens", 0)),
        "cost_usd":      float(payload.get("total_cost_usd", 0.0) or 0.0),
        "session_id":    payload.get("session_id"),
    }


def _coerce_scene_json(text: str) -> dict:
    """Strip fences / prose and parse the first JSON object."""
    t = text.strip()
    if t.startswith("```"):
        t = t.split("```", 2)[1] if t.count("```") >= 2 else t.strip("`")
        if t.startswith("json"):
            t = t[4:]
    start = t.find("{")
    end = t.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"No JSON object found in model output: {text[:200]}")
    return json.loads(t[start:end + 1])


# ─── JSON scene contract guard + automatic fallback (dec-d809f8a2) ────────────

ALLOWED_OUTCOMES = {"decision", "parked", "consensus", "exhausted"}
ALLOWED_TIERS = {"green", "approval", "never"}


def validate_scene_contract(scene, inject: bool = False) -> list[str]:
    """Return a list of contract violations (empty = scene is valid).

    The contract is the JSON shape the playback engine, decisions pipeline,
    and vault writer all depend on. Inject replies only need valid turns."""
    if not isinstance(scene, dict):
        return ["scene is not a JSON object"]
    errs: list[str] = []
    turns = scene.get("turns")
    if not isinstance(turns, list) or not turns:
        errs.append("turns missing or empty")
    else:
        for i, t in enumerate(turns):
            if not isinstance(t, dict):
                errs.append(f"turn[{i}] is not an object")
                continue
            if not ((t.get("speaker_id") or t.get("speaker") or "").strip()):
                errs.append(f"turn[{i}] missing speaker")
            if not (t.get("text") or "").strip():
                errs.append(f"turn[{i}] missing text")
    if inject:
        return errs
    if not (scene.get("label") or "").strip():
        errs.append("label missing")
    if not (scene.get("topic") or "").strip():
        errs.append("topic missing")
    outcome = scene.get("outcome")
    if not isinstance(outcome, dict) or outcome.get("type") not in ALLOWED_OUTCOMES:
        errs.append("outcome.type missing/invalid")
    prop = scene.get("proposal")
    if prop is not None:
        if not isinstance(prop, dict):
            errs.append("proposal must be object or null")
        else:
            if not (prop.get("title") or "").strip():
                errs.append("proposal.title missing")
            if prop.get("tier") not in ALLOWED_TIERS:
                errs.append("proposal.tier invalid")
            if not (prop.get("what") or "").strip():
                errs.append("proposal.what missing")
    return errs


def _log_fallback(model: str, reason: str) -> None:
    try:
        BOARD_DIR.mkdir(parents=True, exist_ok=True)
        with FALLBACK_LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"ts": _iso(), "model": model, "reason": reason[:500]}) + "\n")
    except Exception:
        pass


def run_scene_guarded(prompt: str, model: str, system_prompt: str | None = None,
                      inject: bool = False) -> tuple[dict, dict, str, str | None]:
    """Generate a scene with the contract guard.

    If the primary model errors out or returns JSON that violates the scene
    contract, automatically regenerate on FALLBACK_MODEL so the board never
    drops a scene. Returns (scene, usage, model_used, fallback_reason|None)."""
    fallback_reason: str | None = None
    if model != FALLBACK_MODEL:
        try:
            scene, usage = run_scene_claude(prompt, model, system_prompt=system_prompt)
            errs = validate_scene_contract(scene, inject=inject)
            if not errs:
                return scene, usage, model, None
            fallback_reason = "contract: " + "; ".join(errs[:4])
        except Exception as exc:  # noqa: BLE001
            fallback_reason = f"generation: {exc}"
        _log_fallback(model, fallback_reason)
    # Fallback lane (also the direct lane when the primary IS the fallback model).
    scene, usage = run_scene_claude(prompt, FALLBACK_MODEL, system_prompt=system_prompt)
    errs = validate_scene_contract(scene, inject=inject)
    if errs:
        # No further model to try — keep the scene (pre-guard behavior) but log it.
        _log_fallback(FALLBACK_MODEL, "accepted-with-warnings: " + "; ".join(errs[:4]))
    return scene, usage, FALLBACK_MODEL, fallback_reason


# ─── persistence ──────────────────────────────────────────────────────────────

def persist(scene: dict, usage: dict, topic: dict, scene_id: str, assignments: dict) -> None:
    BOARD_DIR.mkdir(parents=True, exist_ok=True)
    ts = _iso()

    frames = {aid: {"id": d["id"], "label": d["label"], "lean": d["lean"]}
              for aid, d in assignments.items()}
    record = {
        "scene_id": scene_id, "ts": ts, "label": scene.get("label", ""),
        "topic": scene.get("topic", topic["topic"]),
        "source": topic["source"], "frames": frames,
        "continues_scene_id": scene.get("continues_scene_id", ""),
        "turns": scene.get("turns", []), "outcome": scene.get("outcome", {}),
        "proposal": scene.get("proposal"),
        "usage": {"input": usage["input_tokens"], "output": usage["output_tokens"],
                  "cost_usd": usage["cost_usd"]},
    }
    with SCENE_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

    with USAGE_LEDGER.open("a", encoding="utf-8") as f:
        f.write(json.dumps({
            "ts": ts, "scene_id": scene_id,
            "model": usage.get("model", ""),
            "input_tokens": usage["input_tokens"], "output_tokens": usage["output_tokens"],
            "total_tokens": usage["input_tokens"] + usage["output_tokens"],
            "cost_usd": usage["cost_usd"],
        }) + "\n")

    # Continuity memory
    mem = _load_json(MEMORY_FILE, {})
    mem.setdefault("recent_decisions", [])
    mem.setdefault("open_threads", [])
    mem.setdefault("callbacks", [])
    outcome = scene.get("outcome", {})
    short = scene.get("topic", topic["topic"])[:90]
    if outcome.get("type") == "decision":
        mem["recent_decisions"].append(f"[{ts[:10]}] {outcome.get('summary','')[:120]}")
    elif outcome.get("type") == "parked":
        mem["open_threads"].append(f"[{ts[:10]}] {short} — {outcome.get('summary','')[:90]}")
    mem["callbacks"].append(f"[{ts[:10]}] discussed: {short}")
    for k in ("recent_decisions", "open_threads", "callbacks"):
        mem[k] = mem[k][-20:]
    mem["last_frames"] = frames  # anti-repeat seed for the next scene
    MEMORY_FILE.write_text(json.dumps(mem, indent=2, ensure_ascii=False), encoding="utf-8")

    # RAG-compatible vault embedding — the board's discussions become recallable
    # institutional memory via the same sidecar that ingests every memory/ note.
    try:
        _write_vault_notes(scene, frames, topic, scene_id, ts)
    except Exception:
        pass  # vault embedding must never break scene generation

    # Fix 3: persist GitHub Debrief repo verdicts after every scene
    try:
        maybe_persist_repo_verdicts(scene, topic, ts)
    except Exception:
        pass


def _write_vault_notes(scene: dict, frames: dict, topic: dict, scene_id: str, ts: str) -> None:
    day = ts[:10]
    outcome = scene.get("outcome", {})
    otype = outcome.get("type", "discussion")
    short_topic = scene.get("topic", topic["topic"])
    frame_line = ", ".join(f"{aid}:{f['label']}" for aid, f in frames.items())

    transcript = "\n".join(
        f"- **{t.get('speaker','?')}** ({t.get('emotion','')}): {t.get('text','')}"
        for t in scene.get("turns", [])
    )
    prop = scene.get("proposal")
    prop_block = ""
    if prop:
        prop_block = (f"\n\n### Proposal\n- **{prop.get('title','')}** "
                      f"[{prop.get('tier','')}] — {prop.get('what','')}\n"
                      f"  Why: {prop.get('why','')} (owner: {prop.get('owner','')}, "
                      f"needs Brian: {prop.get('needs_brian', False)})")

    # 1. Daily session log — every scene appends here (their "note session").
    VAULT_BOARDROOM_DIR.mkdir(parents=True, exist_ok=True)
    daily = VAULT_BOARDROOM_DIR / f"{day}.md"
    if not daily.exists():
        daily.write_text(
            f"---\nname: boardroom-log-{day}\n"
            f"description: The Boardroom's C-suite discussions and decisions on {day}.\n"
            f"tags: [boardroom, c-suite, session-log]\nmetadata:\n  type: boardroom\n  date: {day}\n---\n\n"
            f"# Boardroom — {day}\n\n", encoding="utf-8")
    with daily.open("a", encoding="utf-8") as f:
        f.write(
            f"## {ts[11:16]} · {short_topic}\n"
            f"**Outcome:** {otype.upper()} — {outcome.get('summary','')}\n"
            f"**Frames:** {frame_line}{prop_block}\n\n"
            f"<details><summary>Transcript</summary>\n\n{transcript}\n\n</details>\n\n---\n\n")

    # 2. Durable decision note — only when something real landed.
    if otype == "decision" or (prop and prop.get("needs_brian")):
        VAULT_DECISIONS_DIR.mkdir(parents=True, exist_ok=True)
        dec = VAULT_DECISIONS_DIR / f"boardroom-{day}.md"
        if not dec.exists():
            dec.write_text(
                f"---\nname: boardroom-decisions-{day}\n"
                f"description: Decisions and proposals from The Boardroom on {day}.\n"
                f"tags: [boardroom, decisions, c-suite, proposals]\nmetadata:\n"
                f"  type: decision\n  owner: Boardroom\n  date: {day}\n---\n\n"
                f"# Boardroom Decisions — {day}\n\n", encoding="utf-8")
        with dec.open("a", encoding="utf-8") as f:
            f.write(f"## {short_topic}\n**{otype.upper()}:** {outcome.get('summary','')}"
                    f"{prop_block}\n\n_(scene {scene_id}, {ts[11:16]})_\n\n---\n\n")


# ─── Fix 3: repo-verdict ledger ───────────────────────────────────────────────

# Verdict keywords the parser looks for in scene turns + outcome text.
# Each entry: (keyword_lower, canonical_verdict)
_VERDICT_KEYWORDS = [
    ("clone-it", "CLONE-IT"),
    ("clone it", "CLONE-IT"),
    ("clone_it", "CLONE-IT"),
    ("watch", "WATCH"),
    ("ignore", "IGNORE"),
]


def _extract_repo_verdicts(scene: dict, topic_text: str) -> list[dict]:
    """Parse GitHub Debrief scene output for per-repo verdicts.

    Scans the topic seed, all turns, and the outcome summary for lines that
    pattern-match "REPO_NAME: VERDICT" (e.g. "maigret: IGNORE" or "last30days-skill
    CLONE-IT"). Returns list of {repo, verdict, rationale} dicts.

    This is necessarily heuristic — the model output is free-form prose inside
    JSON strings. We look for the repo names from the seed topic combined with
    explicit verdict keywords.
    """
    # Collect all text to scan
    texts: list[str] = [topic_text]
    for turn in (scene.get("turns") or []):
        t = (turn.get("text") or "").strip()
        if t:
            texts.append(t)
    outcome = scene.get("outcome") or {}
    if outcome.get("summary"):
        texts.append(outcome["summary"])

    # Extract repo names from the topic seed (lines starting with "- repo/name")
    repo_names: list[str] = []
    for line in topic_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("- ") and "/" in stripped:
            # "- owner/repo (lang +N/day): desc"
            part = stripped[2:].split("(")[0].split(":")[0].strip()
            if "/" in part and len(part) < 60:
                repo_names.append(part)

    if not repo_names:
        return []

    results: list[dict] = []
    combined = " ".join(texts).lower()

    for repo in repo_names:
        repo_lower = repo.lower()
        # Find the best verdict for this repo mentioned near its name
        # Strategy: find all occurrences of the repo name in combined text,
        # then check the surrounding 120 chars for a verdict keyword
        idx = 0
        found_verdict = None
        found_rationale = ""
        while True:
            pos = combined.find(repo_lower, idx)
            if pos == -1:
                break
            window = combined[max(0, pos - 20):pos + 140]
            for kw, canonical in _VERDICT_KEYWORDS:
                if kw in window:
                    found_verdict = canonical
                    # Grab a short rationale snippet
                    found_rationale = combined[pos:pos + 100].replace("\n", " ").strip()
                    break
            if found_verdict:
                break
            idx = pos + 1

        if found_verdict:
            results.append({
                "repo": repo,
                "verdict": found_verdict,
                "rationale": found_rationale[:120],
            })

    return results


def _upsert_repo_verdicts(verdicts_found: list[dict], date_str: str) -> None:
    """Upsert parsed verdicts into REPO_VERDICTS (session/boardroom/repo-verdicts.json).

    Schema: {repo_name: [{verdict, date, rationale}, ...]}
    Each repo keeps its full history so the board can cite prior rulings.
    """
    if not verdicts_found:
        return
    try:
        BOARD_DIR.mkdir(parents=True, exist_ok=True)
        existing: dict = _load_json(REPO_VERDICTS, {})
        if not isinstance(existing, dict):
            existing = {}
        for entry in verdicts_found:
            repo = entry.get("repo", "").strip()
            if not repo:
                continue
            history = existing.get(repo, [])
            if not isinstance(history, list):
                history = []
            # Avoid duplicate entry for same date+verdict
            already = any(
                h.get("date", "")[:10] == date_str and h.get("verdict") == entry["verdict"]
                for h in history
            )
            if not already:
                history.append({
                    "verdict": entry["verdict"],
                    "date": date_str,
                    "rationale": entry.get("rationale", ""),
                })
            existing[repo] = history
        REPO_VERDICTS.write_text(
            json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(f"[boardroom-scene] repo-verdicts upserted {len(verdicts_found)} repos to {REPO_VERDICTS}",
              file=sys.stderr)
    except Exception as exc:
        print(f"[boardroom-scene] repo-verdicts upsert error: {exc}", file=sys.stderr)


def maybe_persist_repo_verdicts(scene: dict, topic: dict, ts: str) -> None:
    """Called after scene generation when source is a github debrief (Fix 3).
    Safe to call always — exits immediately when topic is not github-related."""
    source = (topic.get("source") or "").lower()
    topic_text = (topic.get("topic") or "")
    if "github" not in source and "github" not in topic_text.lower()[:60]:
        return
    try:
        verdicts = _extract_repo_verdicts(scene, topic_text)
        if verdicts:
            _upsert_repo_verdicts(verdicts, ts[:10])
    except Exception as exc:
        print(f"[boardroom-scene] repo-verdict parse error: {exc}", file=sys.stderr)


# ─── main ─────────────────────────────────────────────────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--topic", default=None)
    ap.add_argument("--source", default=None)
    ap.add_argument("--model", default=None,
                    help="override; default = Opus 4.8 for decision-stakes scenes, Haiku for routine")
    ap.add_argument("--force", action="store_true", help="bypass governor gates")
    ap.add_argument("--dry-run", action="store_true", help="assemble prompt, skip claude call")
    ap.add_argument("--inject", action="store_true",
                    help="short group-chat mode: 2-4 turns from 1-2 agents, direct reply to Brian")
    ap.add_argument("--prefer-tier", default=None,
                    help="work-mix steer for the 25/10/65 governance: green | approval | monitoring")
    ap.add_argument("--show-prompt-size", action="store_true",
                    help="print assembled prompt char+token count to stdout (Fix 2 observability)")
    args = ap.parse_args()

    cast_doc = _load_json(CAST_FILE, {})
    cast = cast_doc.get("cast", [])
    if not cast:
        print(json.dumps({"error": "no cast loaded", "cast_file": str(CAST_FILE)}))
        return 2

    # Fail-closed governor load: if the state file is missing or unreadable, BLOCK
    # the call rather than falling through with permissive defaults. --force and
    # --dry-run are the only escape hatches (explicit intent, not silent fallthrough).
    gov, gov_err = _load_governor_fail_closed()
    if gov is None:
        if args.force or args.dry_run:
            # Explicit override — proceed with empty governor (no caps applied).
            gov = {}
            print(f"[boardroom-scene] WARNING: governor unavailable ({gov_err}); "
                  "proceeding because --force/--dry-run", file=sys.stderr)
        else:
            _log_throttle_decision("blocked", f"governor unavailable: {gov_err}", None)
            print(json.dumps({"status": "skipped",
                              "reason": f"governor unavailable: {gov_err}",
                              "window_tokens": 0, "window_scenes": 0}))
            return 0

    # Fix 4: model selected at this point before topic is known; topic may not exist
    # yet — initial resolve uses base logic; full tiered resolve happens after topic pick
    model = args.model or resolve_default_model()

    if not args.force and not args.dry_run:
        ok, reason = governor_preflight(gov)
        if not ok:
            _log_throttle_decision("blocked", reason, gov)
            print(json.dumps({"status": "skipped", "reason": reason,
                              "window_tokens": _window_tokens(gov),
                              "window_scenes": _window_scene_count(gov)}))
            return 0

    scene_id = "scene-" + uuid.uuid4().hex[:8]

    # Draw per-scene dispositions (the dynamic personality layer)
    dispositions = cast_doc.get("dispositions", [])
    mem = _load_json(MEMORY_FILE, {})
    last_frames = mem.get("last_frames")
    assignments = assign_dispositions(cast, dispositions, scene_id, last_frames)

    # Brian jumping into the room ALWAYS takes priority over any scheduled topic.
    injection = read_and_clear_injection()
    continues_scene_id = ""
    inherited_label = ""

    # ── SHORT INJECT MODE (--inject flag) ─────────────────────────────────────
    # When Brian jumps into a conversation we generate a compact 2-4 turn reply
    # from 1-2 most-relevant agents instead of a full 9-16 turn boardroom scene.
    # This cuts generation time from ~90s to ~20-30s and makes it feel like chat.
    if args.inject and injection:
        prior = _load_scene_by_id(injection.get("scene_id", ""))
        prior_topic = prior.get("topic", "ongoing discussion") if prior else "ongoing discussion"
        transcript = _continuation_transcript(prior, max_turns=8) if prior else "(no prior context)"
        if prior:
            continues_scene_id = prior.get("scene_id", "")
            inherited_label = prior.get("label") or ""

        prompt = build_inject_prompt(cast, prior_topic, injection["text"], transcript)

        if args.dry_run:
            print("=== SYSTEM (inject) ===\n" + INJECT_SYSTEM_PROMPT + "\n\n=== PROMPT ===\n" + prompt)
            return 0

        _log_throttle_decision("allowed", "inject mode — bypasses standard governor", gov)
        t0 = time.monotonic()
        scene, usage, model_used, fallback_reason = run_scene_guarded(
            prompt, model, system_prompt=INJECT_SYSTEM_PROMPT, inject=True)
        elapsed = time.monotonic() - t0
        usage["model"] = model_used

        # Ensure inject response is tagged so the UI can thread it back
        scene.setdefault("turns", [])
        scene["source"] = "brian-inject"
        if continues_scene_id:
            scene["continues_scene_id"] = continues_scene_id
            scene["label"] = inherited_label or scene.get("label", "")
        # Inject responses don't need outcome/proposal — the board is replying, not deciding
        if not scene.get("outcome"):
            scene["outcome"] = {}
        if "proposal" not in scene:
            scene["proposal"] = None

        topic = {"topic": prior_topic, "source": "brian-inject"}
        persist(scene, usage, topic, scene_id, assignments)

        out = {
            "status": "ok", "scene_id": scene_id, "elapsed_s": round(elapsed, 1),
            "model": model_used, "fallback_from": (model if fallback_reason else None),
            "inject": True,
            "usage": {"input": usage["input_tokens"], "output": usage["output_tokens"],
                      "total": usage["input_tokens"] + usage["output_tokens"],
                      "cost_usd": round(usage["cost_usd"], 4)},
            "scene": scene,
        }
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0

    # ── FULL SCENE MODE (default) ──────────────────────────────────────────────
    if injection:
        topic, continues_scene_id, inherited_label = _injection_topic(injection)
    else:
        topic = pick_topic(args.topic, args.source, seed_index=_window_scene_count(gov))
        # IMPACT GATE (v3, 2026-06-13): a scheduled heartbeat only earns its ~50K tokens
        # if the best available topic clears governor.min_impact_priority. Low-signal ticks
        # (git churn, hunter, dream, evergreen filler) become no-ops so the board stays
        # sharp instead of chatty. Forced (--force), explicit (--topic), and Brian
        # injections always bypass this. Floor 0 disables.
        if not args.force and not args.topic:
            floor = int(gov.get("min_impact_priority", 0) or 0)
            tpri = int((topic or {}).get("priority", 0) or 0)
            if floor and tpri < floor:
                _log_throttle_decision(
                    "blocked",
                    f"below impact bar (topic priority {tpri} < {floor})",
                    gov,
                )
                print(json.dumps({
                    "status": "skipped",
                    "reason": f"below impact bar (topic priority {tpri} < {floor})",
                    "source": (topic or {}).get("source", ""),
                    "window_scenes": _window_scene_count(gov),
                }))
                return 0

    # Fix 4: apply tiered model selection now that topic is known
    if not args.model:
        is_forced = bool(injection)
        model, tier_reason = resolve_scene_model(topic, is_forced=is_forced)
        print(f"[boardroom-scene] model={model} reason={tier_reason!r}", file=sys.stderr)
    else:
        tier_reason = "manual override"

    prompt = build_prompt(cast, mem, topic, assignments,
                          show_prompt_size=getattr(args, "show_prompt_size", False))

    # Work-mix steer (Boardroom governance 25/10/65): nudge the scene toward the under-represented
    # bucket. NEVER overrides a Brian injection (he always takes priority).
    if getattr(args, "prefer_tier", None) and not injection:
        _STEER = {
            "green": ("WORK-MIX STEER: the board is light on concrete GREEN auto-merge upgrades. Aim "
                      "this scene at a specific internal reliability/maintenance/observability "
                      "improvement and, if warranted, a tier 'green' proposal."),
            "approval": ("WORK-MIX STEER: the board is light on APPROVAL-required enhancements. If a "
                         "genuinely new user-facing/UX idea is warranted, surface it as a tier "
                         "'approval' proposal (needs_brian=true) -- never manufacture noise."),
            "monitoring": ("WORK-MIX STEER: enough proposals are queued. Make THIS scene monitoring & "
                           "quality-control -- review system health/observability/risks. A null "
                           "proposal is the correct, successful outcome here."),
        }
        _steer = _STEER.get(args.prefer_tier)
        if _steer:
            prompt = prompt + "\n\n" + _steer

    if args.dry_run:
        print("=== SYSTEM ===\n" + SYSTEM_PROMPT + "\n\n=== PROMPT ===\n" + prompt)
        return 0

    _allowed_reason = "forced (--force)" if args.force else reason
    _log_throttle_decision("allowed", _allowed_reason, gov)
    t0 = time.monotonic()
    scene, usage, model_used, fallback_reason = run_scene_guarded(prompt, model)
    elapsed = time.monotonic() - t0
    usage["model"] = model_used
    # Thread a continuation back to its parent so the UI can group + title it as
    # the SAME conversation Brian jumped into.
    if continues_scene_id:
        scene["continues_scene_id"] = continues_scene_id
        if inherited_label and not (scene.get("label") or "").strip():
            scene["label"] = inherited_label
        elif inherited_label:
            # Keep the parent's title so the thread reads as one conversation.
            scene["label"] = inherited_label
    persist(scene, usage, topic, scene_id, assignments)

    frames_out = {aid: {"label": d["label"], "lean": d["lean"]} for aid, d in assignments.items()}
    out = {
        "status": "ok", "scene_id": scene_id, "elapsed_s": round(elapsed, 1),
        "model": model_used, "fallback_from": (model if fallback_reason else None),
        "model_tier_reason": tier_reason,
        "frames": frames_out,
        "usage": {"input": usage["input_tokens"], "output": usage["output_tokens"],
                  "total": usage["input_tokens"] + usage["output_tokens"],
                  "cost_usd": round(usage["cost_usd"], 4)},
        "window_tokens_after": _window_tokens(gov),
        "scene": scene,
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
