#!/usr/bin/env python3
"""
cron-creation-guard.py -- PreToolUse hard block on autonomous scheduled-task /
background-script / session-cron creation.

Incident-born governance: unmanaged autonomous automation once sprawled -- a
self-scheduling loop registered OS scheduled tasks with no registry and no
approval, and later a session cron got registered ON TOP of an existing OS task
(double-fire). This guard makes autonomous task/cron creation an approval-gated
action, and closes the dual-scheduler gap.

Matcher (settings.json): Bash|PowerShell|CronCreate

Two governed surfaces
---------------------
1) Bash / PowerShell that CREATES or CHANGES an OS scheduled task:
     Windows-first patterns (schtasks /create|/change, Register/Set-ScheduledTask).
     POSIX equivalent: guard `crontab`, `systemctl ... --user enable`, and
     `at`/`launchctl load` similarly by adding patterns to CREATE_PATTERNS.
   -> RED-tier: requires session/cron-approved.flag (single-use) unless it is one
   of the sanctioned management scripts (ALLOWLIST).

2) The CronCreate tool (session crons). Cross-checks the routine against
   session/active-crons.json `owner` ledger:
     - owner == "cron" (genuine session-cron-owned, no OS task) -> ALLOW
       (idempotent re-registration of an already-approved cron).
     - owner in ("task-scheduler", "monitor-daemon") or suppressed:true -> BLOCK
       (the OS task / daemon is the real owner; a cron would double-fire).
     - routine not in the ledger (novel) -> RED-tier: requires the approval flag.

Override (deliberate, human): create the approval flag with a one-line reason
        echo "why this task is needed" > session/cron-approved.flag
  The flag is single-use -- consumed on the next allowed creation.

SAFETY: whole body try/except -> NEVER blocks on parse error (fail open).
Log: session/cron-creation-guard.log
"""
import json
import re
import sys
from pathlib import Path
from datetime import datetime, timezone

CLAUDE_ROOT = Path.home() / ".claude"
SESSION_DIR = CLAUDE_ROOT / "session"
LOG_FILE = SESSION_DIR / "cron-creation-guard.log"
APPROVE_FLAG = SESSION_DIR / "cron-approved.flag"
ACTIVE_CRONS = SESSION_DIR / "active-crons.json"

# Patterns that CREATE or MODIFY a scheduled task (not query/run/delete).
# Windows-first; add POSIX patterns (crontab, systemctl --user enable, at,
# launchctl load) here to guard those schedulers too.
CREATE_PATTERNS = [
    re.compile(r"schtasks\b.*?/create", re.IGNORECASE | re.DOTALL),
    re.compile(r"schtasks\b.*?/change", re.IGNORECASE | re.DOTALL),
    re.compile(r"\bRegister-ScheduledTask\b", re.IGNORECASE),
    re.compile(r"\bSet-ScheduledTask\b", re.IGNORECASE),
]

# Sanctioned management scripts -- allowed without a flag. Replace with your own.
ALLOWLIST = [
    # e.g. "your-scheduler-audit.py", "your-cutover-script.ps1",
]

_STOP = {"the", "a", "an", "for", "to", "of", "and", "or", "in", "on", "at",
         "is", "this", "that", "via", "run", "now", "first", "if", "then",
         "task", "scheduler", "cron", "daily", "weekly", "session"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _log(line: str) -> None:
    try:
        SESSION_DIR.mkdir(parents=True, exist_ok=True)
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(f"{_now()}  {line}\n")
    except Exception:
        pass


def _tokens(text: str) -> set:
    toks = re.findall(r"[a-z0-9]+", (text or "").lower())
    return {t for t in toks if t not in _STOP and len(t) > 1}


def _best_match(prompt: str) -> tuple:
    """Return (key, entry, score) of the closest active-crons routine, or (None, None, 0)."""
    try:
        crons = json.loads(ACTIVE_CRONS.read_text(encoding="utf-8"))
    except Exception:
        return (None, None, 0.0)
    pt = _tokens(prompt)
    if not pt:
        return (None, None, 0.0)
    best = (None, None, 0.0)
    for key, entry in crons.items():
        if key.startswith("_") or not isinstance(entry, dict):
            continue
        et = _tokens(entry.get("prompt", "")) | _tokens(key)
        if not et:
            continue
        inter = len(pt & et)
        union = len(pt | et) or 1
        jacc = inter / union
        # subset bonus: one prompt fully contained in the other counts as a match
        subset = pt <= et or et <= pt
        score = max(jacc, 0.6 if (subset and inter >= 1) else 0.0)
        if score > best[2]:
            best = (key, entry, score)
    return best


def _block_taskmod(cmd: str) -> None:
    _log(f"BLOCK taskmod cmd={cmd[:200]!r}")
    sys.stderr.write(
        "[CRON-CREATION-GUARD] BLOCKED\n"
        "This command creates or modifies an OS scheduled task.\n\n"
        "Autonomous task/script creation is RED-tier: it must be registered in\n"
        "session/automation-registry.json AND explicitly approved.\n\n"
        "If this is a deliberate, approved task:\n"
        "  1. Add an entry to session/automation-registry.json\n"
        "  2. echo \"why this task is needed\" > session/cron-approved.flag\n"
        "  3. Re-run. The flag is single-use.\n"
    )
    sys.exit(2)


def _block_dual(prompt: str, key: str, entry: dict) -> None:
    owner = entry.get("owner", "?")
    task = entry.get("task", "(an OS task)")
    _log(f"BLOCK dual-scheduler prompt={prompt[:120]!r} matched={key!r} owner={owner} task={task!r}")
    sys.stderr.write(
        "[CRON-CREATION-GUARD] BLOCKED -- dual-scheduler\n"
        f"This CronCreate would register a session cron for routine '{key}',\n"
        f"but that routine is already owned by {owner}: {task}.\n"
        "A session cron on top of the OS task / daemon = double-fire (the exact\n"
        "duplicate-automation problem this guard exists to prevent).\n\n"
        "Do NOT register this cron. The OS task / monitor daemon already runs it.\n"
        "If you genuinely want the session cron to OWN it instead, first disable the\n"
        "OS task and flip its active-crons.json owner to 'cron'.\n"
    )
    sys.exit(2)


def _block_novel_cron(prompt: str) -> None:
    _log(f"BLOCK novel-cron prompt={prompt[:160]!r}")
    sys.stderr.write(
        "[CRON-CREATION-GUARD] BLOCKED -- unregistered cron\n"
        "This CronCreate is for a routine not in session/active-crons.json.\n"
        "Autonomous cron creation is RED-tier (unmanaged automation can sprawl).\n\n"
        "If this is a deliberate, approved cron:\n"
        "  1. Add it to session/active-crons.json with \"owner\": \"cron\"\n"
        "  2. echo \"why this cron is needed\" > session/cron-approved.flag\n"
        "  3. Re-run. The flag is single-use.\n"
    )
    sys.exit(2)


def _consume_flag_and_allow(context: str) -> None:
    try:
        reason = APPROVE_FLAG.read_text(encoding="utf-8").strip()
        _log(f"ALLOW approved {context} reason={reason!r} (consuming flag)")
        APPROVE_FLAG.unlink()
    except Exception:
        pass
    sys.exit(0)


def main() -> None:
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            sys.exit(0)
        payload = json.loads(raw)
    except Exception:
        sys.exit(0)  # fail open

    try:
        tool = payload.get("tool_name", "") or ""
        ti = payload.get("tool_input", {}) or {}
        if not isinstance(ti, dict):
            sys.exit(0)

        # ---- Surface 2: the CronCreate tool ----
        if tool == "CronCreate":
            prompt = ti.get("prompt", "") or ti.get("command", "") or ""
            key, entry, score = _best_match(prompt)
            if entry and score >= 0.5:
                owner = entry.get("owner", "cron")
                suppressed = bool(entry.get("suppressed"))
                if owner == "cron" and not suppressed:
                    _log(f"ALLOW cron-owned re-register key={key!r} score={score:.2f}")
                    sys.exit(0)
                # owned by an OS task / daemon -> dual-scheduler block
                _block_dual(prompt, key, entry)
            # Novel cron: RED-tier, needs the flag.
            if APPROVE_FLAG.exists():
                _consume_flag_and_allow("novel-cron")
            _block_novel_cron(prompt)

        # ---- Surface 1: Bash/PowerShell task create/change ----
        cmd = ti.get("command", "") or ti.get("script", "") or ""
        if not isinstance(cmd, str) or not cmd:
            sys.exit(0)
        if not any(p.search(cmd) for p in CREATE_PATTERNS):
            sys.exit(0)
        if any(name in cmd for name in ALLOWLIST):
            _log(f"ALLOW management-script cmd={cmd[:120]!r}")
            sys.exit(0)
        if APPROVE_FLAG.exists():
            _consume_flag_and_allow("taskmod")
        _block_taskmod(cmd)

    except SystemExit:
        raise
    except Exception as e:
        _log(f"ERROR (failing open) {type(e).__name__}: {e}")
        sys.exit(0)


if __name__ == "__main__":
    main()
