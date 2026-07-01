#!/usr/bin/env python3
"""
Debate Auto-Invoke Hook v1.0 (Phase 0)

PreToolUse hook on `AskUserQuestion`. Intercepts option presentations and,
when the calling context is debate-eligible and safe, blocks the tool call
so the assistant runs the multi-persona `debate` skill (the router agent
answers the Inquisitor's 3 questions via A2A), then re-asks the original
question post-verdict.

Phase 0 scope (this file):
  - Explicit opt-in path ONLY (via session/debate-pending.flag)
  - Hard denylist (irreversible / time-critical / life-safety flows)
  - Recursion guard (state.debate_auto_invoke.in_flight)
  - Structured decision logging
  - Heuristic keyword path: DISABLED (Phase 1)

Contract:
  - Input: stdin JSON with tool_name, tool_input, session metadata
  - Output: exit 0 = approve, exit 2 = block with stderr reason
  - Side effects: write enforcement.todo on block, update state.json flags,
    append to debate-auto-invoke-log.jsonl on every decision

Performance budget: <30ms (must not bottleneck AskUserQuestion across many skills).

Portable: uses Path.home() only (works on POSIX + Windows).
"""

import json
import sys
import io
import os
import time
import base64
from pathlib import Path
from datetime import datetime, timezone

# Force UTF-8 (Windows consoles default to cp1252)
if sys.stdin.encoding != "utf-8":
    sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding="utf-8", errors="replace")
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr.encoding != "utf-8":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# --- Paths ---
CLAUDE_ROOT = Path.home() / ".claude"
SESSION_DIR = CLAUDE_ROOT / "session"
STATE_FILE = SESSION_DIR / "state.json"
STATE_HOT = SESSION_DIR / "state-hot.json"
ENFORCEMENT_TODO = SESSION_DIR / "enforcement.todo"
DEBATE_FLAG = SESSION_DIR / "debate-pending.flag"
LOG_FILE = SESSION_DIR / "debate-auto-invoke-log.jsonl"
KILL_SWITCH = SESSION_DIR / "debate-auto-invoke.disabled"

# --- Denylist: skills / contexts where debate MUST NOT auto-fire ---
# Generic categories — extend for your own high-stakes / time-critical flows.
DENYLIST_SKILL_PATTERNS = [
    "skills/routines/session-reset",
    "skills/routines/daily-ops",
    "skills/routines/morning",
    "skills/routines/backup-reminder",
    "skills/routines/heartbeat",
]

# Projects where auto-debate is inappropriate (irreversible / financial / safety).
# Populate with your own project prefixes.
DENYLIST_PROJECT_PREFIXES = []

# Hot strings in question text that indicate time-critical / financial /
# life-safety flows where a debate would add unacceptable latency or risk.
DENYLIST_TEXT_TOKENS = [
    "kill process", "restart service", "close position", "sell position",
    "market order", "wire transfer", "delete production", "drop database",
    "session reset", "irreversible",
    "phase 0", "scope confirm",
]

COOLDOWN_SECONDS = 60  # after last debate verdict, no new auto-debate


def log_decision(payload: dict) -> None:
    """Append structured decision log. Best effort — never raise."""
    try:
        SESSION_DIR.mkdir(exist_ok=True)
        payload["timestamp"] = datetime.now(timezone.utc).isoformat()
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception:
        pass


def read_state() -> dict:
    """Merge state-hot + state. Hot wins for shared keys, but debate_auto_invoke
    lives in canonical state.json — explicitly merge both."""
    merged: dict = {}
    for candidate in (STATE_FILE, STATE_HOT):
        try:
            if candidate.exists():
                with candidate.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                # Hot overrides cold for top-level keys it has
                merged.update(data)
                # But preserve debate_auto_invoke from STATE_FILE if STATE_HOT doesn't have it
                if candidate is STATE_HOT and "debate_auto_invoke" not in data and "debate_auto_invoke" in merged:
                    pass  # already preserved from prior iteration
        except Exception:
            continue
    return merged


def update_state_flags(in_flight: bool, pending: dict | None = None, denylist_hit: bool = False) -> None:
    """Update debate_auto_invoke section in state.json. Best effort."""
    try:
        if not STATE_FILE.exists():
            return
        with STATE_FILE.open("r", encoding="utf-8") as f:
            state = json.load(f)
        dai = state.setdefault("debate_auto_invoke", {
            "in_flight": False,
            "pending_question": None,
            "last_verdict": None,
            "denylist_hits": 0,
            "invocations": 0,
            "last_decision_at": None,
        })
        dai["in_flight"] = in_flight
        dai["last_decision_at"] = datetime.now(timezone.utc).isoformat()
        if pending is not None:
            dai["pending_question"] = pending
            dai["invocations"] = dai.get("invocations", 0) + 1
        if denylist_hit:
            dai["denylist_hits"] = dai.get("denylist_hits", 0) + 1
        with STATE_FILE.open("w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


def check_denylist(question_text: str, state: dict) -> tuple[bool, str]:
    """Return (is_denied, reason)."""
    # 1. Current skill context (if tracked in state)
    active = (state.get("active_skill") or state.get("current_skill") or "").replace("\\", "/").lower()
    for pat in DENYLIST_SKILL_PATTERNS:
        if pat.lower() in active:
            return True, f"active_skill matches denylist pattern: {pat}"

    # 2. Project context
    project = (state.get("current_project_path") or state.get("project") or "").replace("\\", "/").lower()
    for pat in DENYLIST_PROJECT_PREFIXES:
        if pat.lower() in project:
            return True, f"current project under denylisted prefix: {pat}"

    # 3. Question text hot strings
    qlow = question_text.lower()
    for tok in DENYLIST_TEXT_TOKENS:
        if tok in qlow:
            return True, f"question text contains denylist token: '{tok}'"

    # 4. Cooldown after last verdict
    dai = state.get("debate_auto_invoke") or {}
    last = dai.get("last_decision_at")
    if last and dai.get("in_flight") is False:
        try:
            last_dt = datetime.fromisoformat(last.replace("Z", "+00:00"))
            age = (datetime.now(timezone.utc) - last_dt).total_seconds()
            if age < COOLDOWN_SECONDS and dai.get("invocations", 0) > 0:
                return True, f"cooldown active ({int(age)}s of {COOLDOWN_SECONDS}s)"
        except Exception:
            pass

    return False, ""


def consume_eligibility_flag() -> dict | None:
    """Read and delete the debate-pending.flag file if present. Returns flag payload or None."""
    if not DEBATE_FLAG.exists():
        return None
    try:
        with DEBATE_FLAG.open("r", encoding="utf-8") as f:
            payload = json.load(f)
        # Consume: delete after read so it's single-shot
        DEBATE_FLAG.unlink(missing_ok=True)
        return payload
    except Exception:
        # Malformed flag — remove it and skip
        try:
            DEBATE_FLAG.unlink(missing_ok=True)
        except Exception:
            pass
        return None


def extract_question_payload(tool_input: dict) -> tuple[str, list, str]:
    """Extract question text, options, header from AskUserQuestion tool_input."""
    questions = tool_input.get("questions") or []
    if not questions:
        return "", [], ""
    q = questions[0]  # first question is the one we evaluate
    text = str(q.get("question") or "")
    header = str(q.get("header") or "")
    options = q.get("options") or []
    opt_labels = [str(o.get("label", "")) for o in options if isinstance(o, dict)]
    return text, opt_labels, header


def write_enforcement_action(question_text: str, options: list, stakes: list, skill: str) -> None:
    """Append DEBATE_AUTO_INVOKE action to enforcement.todo."""
    SESSION_DIR.mkdir(exist_ok=True)
    q_b64 = base64.b64encode(question_text.encode("utf-8")).decode("ascii")
    opts_b64 = base64.b64encode(json.dumps(options).encode("utf-8")).decode("ascii")
    stakes_str = ",".join(stakes) if stakes else "opt-in"
    action_block = (
        f"\n## DEBATE_AUTO_INVOKE (Priority: 0)\n"
        f"**Reason:** Option presentation flagged as debate-eligible\n"
        f"**Stakes:** {stakes_str}\n"
        f"**Calling skill:** {skill or 'unknown'}\n\n"
        f"**Commands:**\n"
        f"1. Run the `debate` skill in auto-invocation mode.\n"
        f"2. Inquisitor Q1-Q3 -> delegate to the router agent via the Task tool.\n"
        f"   Prompt template: skills/meta/debate-auto-invoke.md Section 'Router Inquisitor Template'.\n"
        f"3. Run the multi-persona debate using the router's answers as the brief.\n"
        f"4. Display vote + verdict to the user.\n"
        f"5. Clear state.debate_auto_invoke.in_flight = false.\n"
        f"6. Re-invoke AskUserQuestion with the original payload (now post-debate).\n\n"
        f"**Original question (base64):** {q_b64}\n"
        f"**Original options (base64 json):** {opts_b64}\n"
        f"\n---\n"
    )
    with ENFORCEMENT_TODO.open("a", encoding="utf-8") as f:
        f.write(action_block)


def main() -> int:
    t0 = time.monotonic()

    # Kill switch: if this file exists, hook is disabled entirely
    if KILL_SWITCH.exists():
        log_decision({"decision": "approve", "reason": "kill_switch_active", "elapsed_ms": round((time.monotonic() - t0) * 1000, 2)})
        return 0

    # Read stdin
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            return 0
        event = json.loads(raw)
    except Exception as e:
        log_decision({"decision": "approve", "reason": f"stdin_parse_error: {e}", "elapsed_ms": round((time.monotonic() - t0) * 1000, 2)})
        return 0

    tool_name = event.get("tool_name") or ""
    tool_input = event.get("tool_input") or {}

    # Defensive: only act on AskUserQuestion
    if tool_name != "AskUserQuestion":
        return 0

    question_text, opt_labels, header = extract_question_payload(tool_input)

    state = read_state()
    dai = state.get("debate_auto_invoke") or {}

    # GUARD 1: recursion — if debate already in flight, approve silently
    if dai.get("in_flight"):
        log_decision({"decision": "approve", "reason": "recursion_guard_in_flight", "question_preview": question_text[:80], "elapsed_ms": round((time.monotonic() - t0) * 1000, 2)})
        return 0

    # GUARD 2: denylist
    denied, deny_reason = check_denylist(question_text, state)
    if denied:
        update_state_flags(in_flight=False, denylist_hit=True)
        log_decision({"decision": "approve", "reason": f"denylist: {deny_reason}", "question_preview": question_text[:80], "elapsed_ms": round((time.monotonic() - t0) * 1000, 2)})
        return 0

    # ELIGIBILITY: Phase 0 uses explicit opt-in flag only
    flag_payload = consume_eligibility_flag()
    if flag_payload is None:
        log_decision({"decision": "approve", "reason": "no_eligibility_flag (phase 0 opt-in only)", "question_preview": question_text[:80], "elapsed_ms": round((time.monotonic() - t0) * 1000, 2)})
        return 0

    # ELIGIBLE — trigger debate
    stakes = flag_payload.get("stakes") if isinstance(flag_payload, dict) else []
    if not isinstance(stakes, list):
        stakes = [str(stakes)]
    calling_skill = (flag_payload or {}).get("skill", "") if isinstance(flag_payload, dict) else ""

    # Persist pending question for post-debate re-invocation
    pending = {
        "question": question_text,
        "header": header,
        "options": opt_labels,
        "stakes": stakes,
        "skill": calling_skill,
        "flagged_at": datetime.now(timezone.utc).isoformat(),
    }
    update_state_flags(in_flight=True, pending=pending)
    write_enforcement_action(question_text, opt_labels, stakes, calling_skill)

    elapsed = round((time.monotonic() - t0) * 1000, 2)
    log_decision({
        "decision": "block",
        "reason": "debate_auto_invoke_triggered",
        "question_preview": question_text[:80],
        "stakes": stakes,
        "skill": calling_skill,
        "elapsed_ms": elapsed,
    })

    # Emit block reason to stderr so the assistant sees it and reads enforcement.todo
    sys.stderr.write(
        "[DEBATE-AUTO-INVOKE]\n"
        "This option presentation was flagged as debate-eligible.\n"
        f"Stakes: {', '.join(stakes) if stakes else 'opt-in'}\n"
        "Read ~/.claude/session/enforcement.todo for the DEBATE_AUTO_INVOKE action.\n"
        "Required: run the `debate` skill (auto mode), spawn the router agent to answer the 3 Inquisitor questions,\n"
        "display the multi-persona debate + vote + verdict, clear state.debate_auto_invoke.in_flight = false,\n"
        "then re-invoke AskUserQuestion with the original question payload.\n"
    )
    return 2


if __name__ == "__main__":
    try:
        rc = main()
        sys.exit(rc)
    except SystemExit:
        raise
    except Exception as e:
        # Fail-open: never break tool execution because of a hook error
        try:
            log_decision({"decision": "approve", "reason": f"hook_exception: {type(e).__name__}: {e}"})
        except Exception:
            pass
        sys.exit(0)
