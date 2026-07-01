#!/usr/bin/env python3
"""
Orchestration Planner Hook v1.0

UserPromptSubmit hook. On every SUBSTANTIAL prompt, pre-computes execution-modality
signals and queues a PLAN_EXECUTION_STRATEGY action in enforcement.todo so the CTO
(Orchestration Architect) can auto-select the modality stack (Plan Mode / Workflow /
A2A mesh / Debate / parallel / worktree / Goal engine) and emit a FLIGHT PLAN box.

This REPLACES the user having to manually say "A2A mesh," "plan mode," "workflow," etc.

Design:
  - UserPromptSubmit (NOT PreToolUse): exit 0 ALWAYS. Never blocks the prompt.
  - Substantial-only: trivial prompts + quick-triggers skip entirely (zero tax).
  - Two phases via marker files (no code edit to flip):
        shadow  (default)  -> log intended plan, write NOTHING, render NO box
        live    (.live)    -> append PLAN_EXECUTION_STRATEGY to enforcement.todo
  - Kill switch: session/orchestration-planner.disabled -> short-circuit.
  - Cooldown: avoid double-fire on rapid edits.
  - Signals are cheap regex; the CTO does the real decision against
    skills/meta/execution-strategy-matrix.md.

Contract:
  - Input: stdin JSON (UserPromptSubmit event with a prompt field)
  - Output: exit 0 (approve). Optional stdout = context note (live mode only).
  - Side effects: append enforcement.todo (live), update state.orchestration,
    append orchestration-planner-log.jsonl on every decision.

Performance budget: <30ms.
"""

import json
import sys
import io
import time
import base64
import re
from pathlib import Path
from datetime import datetime, timezone

# Force UTF-8 on Windows consoles
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
ENFORCEMENT_TODO = SESSION_DIR / "enforcement.todo"
LOG_FILE = SESSION_DIR / "orchestration-planner-log.jsonl"
KILL_SWITCH = SESSION_DIR / "orchestration-planner.disabled"
LIVE_MARKER = SESSION_DIR / "orchestration-planner.live"

COOLDOWN_SECONDS = 5  # avoid double-fire on rapid successive prompts

# Action keywords that mark a prompt "substantial" (mirrors enforcement-queue-handler.md)
ACTION_KEYWORDS = [
    "implement", "build", "create", "refactor", "fix", "update", "analyze",
    "design", "integrate", "migrate", "optimize", "deploy", "configure",
    "setup", "set up", "install", "audit", "review", "plan", "research",
    "generate", "rewrite", "overhaul", "scaffold",
]

# Quick-trigger / denylist starts — if the prompt begins with or is one of these,
# skip orchestration entirely (these have their own dedicated routes).
QUICK_TRIGGER_PREFIXES = [
    "morning", "good morning", "backup", "push backup", "doomsday backup",
    "github backup", "telegram", "start telegram", "launch telegram",
    "mobile session", "/reset", "whitehat", "bug bounty", "/goal",
    "plan goal", "done", "i'm done", "im done", "start over", "clear session",
    "reset chat", "status", "ok", "yes", "no", "thanks", "thank you",
]

# Denylist substrings anywhere in the prompt -> skip (safety-critical / routed flows)
DENYLIST_TOKENS = [
    "/reset", "session reset", "telegram session", "kill bot", "restart bot",
    "close position", "market order", "phase 0", "scope confirm",
]

# --- Signal regexes (cheap, pre-computed for the CTO) ---
SIGNAL_PATTERNS = {
    "workflow": r"\b(audit|all\b|every|each\b|comprehensive|sweep|bulk|review all|migrat\w*|backfill|across the board)\b",
    "debate":   r"\b(compare|which\b|should we|should i|\bvs\b|decide|or should|better option|trade[- ]?off|pros and cons)\b",
    "mesh":     r"\b(across products|delegate|specialist|hand off|each department|cross[- ]product)\b",
    "plan":     r"\b(build|implement|refactor|feature|architecture|from scratch|overhaul|rewrite)\b",
    "parallel": r"\b(in parallel|at the same time|simultaneously|concurrently)\b",
    "goal":     r"\b(over weeks|over the next|multi[- ]session|ongoing|long[- ]term|campaign|roadmap|track the)\b",
    "optimization": r"\b(optimi[sz]e|optimization|qubo|simulated annealing|annealing|or[- ]?tools|minimi[sz]e|maximi[sz]e|knapsack|bin[- ]?packing|allocat\w*|assign\w*|routing|route|scheduling problem|objective function)\b",
}

STAKES_PATTERNS = {
    "architectural": r"\b(architecture|structural|schema|migration|framework|core system)\b",
    "irreversible":  r"\b(delete|drop|remove permanently|wipe|overwrite|cannot be undone|irreversible)\b",
    "financial":     r"\b(budget|cost|price|invoice|payment|trade|money|revenue)\b",
    "legal":         r"\b(contract|liability|compliance|nda|agreement|terms)\b",
    "strategic":     r"\b(roadmap|pivot|direction|strategy|drop the|kill the|sunset)\b",
    "production":    r"\b(deploy|release|ship|live system|production|go live)\b",
}

# Product names -> mesh signal when 2+ appear.
# Customize this list with YOUR product/service names so a prompt spanning
# multiple products auto-selects the A2A mesh modality.
PRODUCT_NAMES = []  # e.g. ["webapp", "mobile", "api", "billing"]


def log_decision(payload: dict) -> None:
    """Append structured decision log. Best effort — never raise."""
    try:
        SESSION_DIR.mkdir(exist_ok=True)
        payload["timestamp"] = datetime.now(timezone.utc).isoformat()
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception:
        pass


def extract_user_prompt(input_data: dict) -> str:
    """Extract the prompt from the hook event. Mirrors gate-enforcer.extract_user_prompt."""
    if not isinstance(input_data, dict):
        return ""
    for field in ("prompt", "message", "content", "user_input", "text", "input", "query", "user_message", "request"):
        if field in input_data:
            val = input_data[field]
            if isinstance(val, str) and val.strip():
                return val
            if isinstance(val, dict):
                for nested in ("content", "text", "message"):
                    if nested in val and isinstance(val[nested], str):
                        return val[nested]
    return ""


def is_substantial(prompt: str) -> bool:
    """Mirror gate-enforcer's substantial test: long OR action keyword present."""
    p = prompt.strip().lower()
    if len(p) > 150:
        return True
    return any(re.search(r"\b" + re.escape(kw) + r"\b", p) for kw in ACTION_KEYWORDS)


def has_strategy_signal(signals: dict) -> bool:
    """A prompt is orchestration-eligible if it carries a modality signal even when
    short and keyword-free — e.g. 'should we drop X?' (debate) or 'compare A vs B'."""
    return any(k in signals for k in ("workflow", "debate", "mesh", "plan", "parallel", "goal", "stakes"))


def is_quick_trigger(prompt: str) -> bool:
    p = prompt.strip().lower()
    for pref in QUICK_TRIGGER_PREFIXES:
        if p == pref or p.startswith(pref + " ") or p.startswith(pref + ",") or p.startswith(pref + "!"):
            return True
    return False


def hits_denylist(prompt: str) -> str:
    p = prompt.lower()
    for tok in DENYLIST_TOKENS:
        if tok in p:
            return tok
    return ""


def compute_signals(prompt: str) -> dict:
    """Cheap regex pre-classification handed to the CTO."""
    p = prompt.lower()
    signals = {}
    for name, pat in SIGNAL_PATTERNS.items():
        if re.search(pat, p):
            signals[name] = True

    stakes = [name for name, pat in STAKES_PATTERNS.items() if re.search(pat, p)]
    if stakes:
        signals["stakes"] = stakes

    products = [n for n in PRODUCT_NAMES if n in p]
    if len(set(products)) >= 2:
        signals["mesh"] = True
        signals["products"] = sorted(set(products))

    # Crude file-count / scope hint
    signals["length"] = len(prompt)
    return signals


def read_state() -> dict:
    try:
        if STATE_FILE.exists():
            with STATE_FILE.open("r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def in_cooldown(state: dict) -> bool:
    orch = state.get("orchestration") or {}
    last = orch.get("last_decision_at")
    if not last:
        return False
    try:
        last_dt = datetime.fromisoformat(last.replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - last_dt).total_seconds() < COOLDOWN_SECONDS
    except Exception:
        return False


def update_state(signals: dict, mode: str) -> None:
    """Record the decision in state.orchestration. Best effort."""
    try:
        state = read_state()
        orch = state.setdefault("orchestration", {
            "enabled": True,
            "in_flight": False,
            "invocations": 0,
            "last_decision_at": None,
            "last_signals": None,
            "last_mode": None,
            "last_flight_plan": None,
        })
        orch["last_decision_at"] = datetime.now(timezone.utc).isoformat()
        orch["last_signals"] = signals
        orch["last_mode"] = mode
        orch["invocations"] = orch.get("invocations", 0) + 1
        if mode == "live":
            orch["in_flight"] = True
        if STATE_FILE.exists():
            with STATE_FILE.open("w", encoding="utf-8") as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


def write_enforcement_action(prompt: str, signals: dict) -> None:
    """Append PLAN_EXECUTION_STRATEGY action to enforcement.todo (live mode)."""
    SESSION_DIR.mkdir(exist_ok=True)
    prompt_b64 = base64.b64encode(prompt.encode("utf-8")).decode("ascii")
    signals_b64 = base64.b64encode(json.dumps(signals).encode("utf-8")).decode("ascii")
    stakes = signals.get("stakes", [])
    stakes_str = ",".join(stakes) if stakes else "none"
    action_block = (
        f"\n## PLAN_EXECUTION_STRATEGY (Priority: 1)\n"
        f"**Reason:** Substantial prompt — auto-select execution modality stack\n"
        f"**Stakes:** {stakes_str}\n"
        f"**Pre-computed signals:** {', '.join(k for k in signals if k not in ('length','stakes','products')) or 'none'}\n\n"
        f"**Commands:**\n"
        f"1. Read skills/meta/execution-strategy-matrix.md (the CTO modality matrix).\n"
        f"2. Spawn CTO (Orchestration Architect) via Task. Model: sonnet "
        f"(escalate to opus if >=2 stakes families). Pass the decoded prompt + signals.\n"
        f"3. CTO returns the modality stack + rationale + tier per the matrix.\n"
        f"4. Render the FLIGHT PLAN box (after the Position #0 box, before ROUTES LOADED).\n"
        f"5. Hand the modality stack to COO (@agent-conductor) for crew assignment.\n"
        f"6. Clear state.orchestration.in_flight = false; write state.orchestration.last_flight_plan.\n"
        f"7. Auto-proceed with the chosen modalities (announce-then-go; do NOT wait).\n\n"
        f"**Prompt (base64):** {prompt_b64}\n"
        f"**Signals (base64 json):** {signals_b64}\n"
        f"\n---\n"
    )
    with ENFORCEMENT_TODO.open("a", encoding="utf-8") as f:
        f.write(action_block)


def main() -> int:
    t0 = time.monotonic()

    # Kill switch
    if KILL_SWITCH.exists():
        log_decision({"decision": "skip", "reason": "kill_switch_active",
                      "elapsed_ms": round((time.monotonic() - t0) * 1000, 2)})
        return 0

    # Read stdin
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            return 0
        event = json.loads(raw)
    except Exception as e:
        log_decision({"decision": "skip", "reason": f"stdin_parse_error: {e}",
                      "elapsed_ms": round((time.monotonic() - t0) * 1000, 2)})
        return 0

    prompt = extract_user_prompt(event)
    if not prompt.strip():
        return 0

    preview = prompt.strip()[:80]

    # Filter 1: quick-triggers / routed flows
    if is_quick_trigger(prompt):
        log_decision({"decision": "skip", "reason": "quick_trigger", "prompt_preview": preview,
                      "elapsed_ms": round((time.monotonic() - t0) * 1000, 2)})
        return 0

    # Filter 2: denylist tokens
    deny = hits_denylist(prompt)
    if deny:
        log_decision({"decision": "skip", "reason": f"denylist_token: {deny}", "prompt_preview": preview,
                      "elapsed_ms": round((time.monotonic() - t0) * 1000, 2)})
        return 0

    # Compute signals up front (cheap) — needed for eligibility AND the CTO brief.
    signals = compute_signals(prompt)

    # Filter 3: eligibility — substantial OR carries a modality signal
    # (short decision prompts like "should we drop X?" have no action keyword
    #  but ARE orchestration-worthy via the debate/stakes signal).
    if not (is_substantial(prompt) or has_strategy_signal(signals)):
        log_decision({"decision": "skip", "reason": "trivial", "prompt_preview": preview,
                      "elapsed_ms": round((time.monotonic() - t0) * 1000, 2)})
        return 0

    # Filter 4: cooldown / recursion
    state = read_state()
    if in_cooldown(state):
        log_decision({"decision": "skip", "reason": "cooldown", "prompt_preview": preview,
                      "elapsed_ms": round((time.monotonic() - t0) * 1000, 2)})
        return 0
    if (state.get("orchestration") or {}).get("in_flight"):
        log_decision({"decision": "skip", "reason": "in_flight_guard", "prompt_preview": preview,
                      "elapsed_ms": round((time.monotonic() - t0) * 1000, 2)})
        return 0

    # ELIGIBLE
    mode = "live" if LIVE_MARKER.exists() else "shadow"
    update_state(signals, mode)

    elapsed = round((time.monotonic() - t0) * 1000, 2)

    if mode == "live":
        write_enforcement_action(prompt, signals)
        log_decision({"decision": "queue", "mode": "live", "prompt_preview": preview,
                      "signals": signals, "elapsed_ms": elapsed})
        # UserPromptSubmit stdout is injected as context — nudge Position #0.
        sys.stdout.write(
            "[ORCHESTRATION] Substantial prompt detected. A PLAN_EXECUTION_STRATEGY "
            "action was queued in enforcement.todo. At Position #0, spawn the CTO "
            "(Orchestration Architect) per skills/meta/execution-strategy-matrix.md, "
            "render the FLIGHT PLAN box, then proceed.\n"
        )
    else:
        # Shadow: log intended plan only, change nothing.
        log_decision({"decision": "shadow", "mode": "shadow", "prompt_preview": preview,
                      "signals": signals, "elapsed_ms": elapsed})

    return 0


if __name__ == "__main__":
    try:
        rc = main()
        sys.exit(rc)
    except SystemExit:
        raise
    except Exception as e:
        # Fail-open: never break prompt flow because of a hook error
        try:
            log_decision({"decision": "skip", "reason": f"hook_exception: {type(e).__name__}: {e}"})
        except Exception:
            pass
        sys.exit(0)
