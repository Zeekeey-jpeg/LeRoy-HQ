#!/usr/bin/env python3
"""
LeRoy — wizard.py
=================
The `leroy init` first-run interview: "let's get to know each other."

Opens with a warm, non-technical greeting, then runs the phases from
onboarding-and-install.md. This is the point — EVERY answer writes a real file
into the memory vault, so the user watches their second brain get built in front
of them. Every step is skippable; pressing Enter (or typing "skip") takes a
sensible default and moves on.

  Greeting              -> reassures a total beginner; the CLI is home now
  Phase 1 — You         -> writes USER.md, tunes SOUL.md
  Phase 2 — Your work   -> seeds Goals/, Projects/, People/
  Phase 3 — Your tools  -> optional MCP setup, writes Reference/ + .env stubs
  Phase 4 — How you like things done -> seeds Feedback/
  Phase 5 — Autonomy menu -> a la carte, DEFAULT OFF, writes config/autonomy.json
  Phase 6 — Subscription  -> plain-English guidance (Pro vs Max; no local model needed)
  Phase 7 — Shortcuts     -> status check only; installer\shortcuts.ps1 (run
                             earlier by setup.ps1) is the sole creator of the
                             "Leroy" + "Leroy CLI" Desktop shortcut pair

Autonomy philosophy: ship the working car. Good non-burning features are ON by
default; token-burning / autonomous features are OFF by default and offered one
at a time. Nothing autonomous is installed or scheduled here — we only RECORD the
user's picks to ~/.claude/config/autonomy.json; `leroy enable <feature>` wires
each one later.

--json mode: for the LeRoy UI onboarding screen. Every phase function is
unchanged — the ONLY thing that changes is how ask()/ask_yes() get their
answer: instead of a terminal input(), each question is emitted as one JSON
line on stdout ({"type": "question", ...}) and the answer is read as one JSON
line on stdin ({"answer": ...}). Every write_file() call still fires the
moment its phase runs, exactly as in the terminal path, so a UI-driven
interview persists progress immediately and produces byte-identical output to
the CLI path — there is no second implementation of the vault file formats.

The vault lives at ~/.claude/memory/ (never hardcoded). If a
memory.seed/ template tree exists in the repo it is used to pre-create the
folder skeleton; otherwise we create the folders ourselves.

Stdlib only. All prompts are plain input() so this works in any terminal.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import sys
from pathlib import Path

# See installer/doctor.py for why this exists: a glyph-probe fallback alone
# can miss a non-ASCII character (bullets, em-dashes, etc.) that only appears
# later in the file, crashing print() on a strict cp1252 console. Reconfiguring
# is the whole-class fix.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(errors="replace")

_UTF_OK = True
try:
    "✅✍️".encode(sys.stdout.encoding or "utf-8")
except (UnicodeEncodeError, LookupError):
    _UTF_OK = False

WROTE = "✍️ " if _UTF_OK else "[wrote]"
OK = "✅" if _UTF_OK else "[ OK ]"

# Set from --json in main(). The sole I/O boundary this flips is ask()/ask_yes()
# below — every phase function's logic (including write_file() calls) is
# identical in both modes.
JSON_MODE = False

VAULT_FOLDERS = [
    "People", "Projects", "Goals", "Decisions", "Boardroom",
    "Chat", "Feedback", "Patterns", "Reference", "Archive",
]


def today() -> str:
    return _dt.date.today().isoformat()


def slug(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s or "untitled"


def _desktop_dir() -> Path:
    """The real per-user Desktop. On Windows this is read from the shell-folders
    registry, so it's correct whether the Desktop is the plain ~/Desktop or has
    been redirected (e.g. by OneDrive) - no OneDrive-specific guessing. Falls
    back to ~/Desktop everywhere else."""
    if sys.platform.startswith("win"):
        try:
            import winreg
            sub = r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, sub) as k:
                val, _ = winreg.QueryValueEx(k, "Desktop")
            return Path(os.path.expandvars(val))
        except Exception:
            pass
    return Path(os.path.expanduser("~")) / "Desktop"


# --- prompt helpers ---------------------------------------------------------
def _emit_question(prompt: str, default, kind: str) -> None:
    print(json.dumps({"type": "question", "kind": kind, "prompt": prompt, "default": default}), flush=True)


def _read_json_answer():
    """Read one JSON line from stdin: {"answer": ...}. Returns None on EOF or
    a malformed line, which callers treat the same as Ctrl-C/EOF in the
    terminal path — fall back to the question's default."""
    line = sys.stdin.readline()
    if not line:
        return None
    try:
        payload = json.loads(line)
    except ValueError:
        return None
    return payload.get("answer")


def ask(prompt: str, default: str = "") -> str:
    """
    Ask a question. Blank input (or 'skip') returns the default.
    Ctrl-C / EOF is treated as 'skip everything gracefully'.
    In --json mode the question/answer round-trip is one JSON line each way
    on stdout/stdin instead of input() — see the --json note in the module
    docstring.
    """
    if JSON_MODE:
        _emit_question(prompt, default, "text")
        answer = _read_json_answer()
        if answer is None:
            return default
        raw = str(answer).strip()
        if raw.lower() in {"skip", ""}:
            return default
        return raw

    hint = "  (press Enter to continue)" if not default else f"  [{default}]"
    try:
        raw = input(f"\n  {prompt}{hint}\n  > ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\n  (skipping)")
        return default
    if raw.lower() in {"skip", ""}:
        return default
    return raw


def ask_yes(prompt: str, default: bool = False) -> bool:
    if JSON_MODE:
        _emit_question(prompt, default, "yesno")
        answer = _read_json_answer()
        if answer is None:
            return default
        if isinstance(answer, bool):
            return answer
        return str(answer).strip().lower() in {"y", "yes", "true"}

    d = "Y/n" if default else "y/N"
    try:
        raw = input(f"\n  {prompt}  ({d})\n  > ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        return default
    if not raw:
        return default
    return raw in {"y", "yes"}


def write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")
    # Show a repo-relative-ish path so it's readable.
    print(f"    {WROTE} {path}")


# --- vault bootstrap --------------------------------------------------------
def ensure_vault(dest: Path, seed: Path | None) -> Path:
    vault = dest / "memory"
    vault.mkdir(parents=True, exist_ok=True)
    for folder in VAULT_FOLDERS:
        (vault / folder).mkdir(exist_ok=True)
    # If a seed template exists, copy any templated root files that are missing.
    if seed and seed.exists():
        for tmpl in seed.glob("*.template"):
            target = vault / tmpl.name.replace(".template", "")
            if not target.exists():
                target.write_text(tmpl.read_text(encoding="utf-8"), encoding="utf-8")
    return vault


# --- autonomy defaults ------------------------------------------------------
def load_autonomy_defaults() -> dict:
    """
    Read installer/autonomy.defaults.json (documents ON- vs OFF-by-default).
    If it's missing or unreadable we fall back to a built-in copy so the wizard
    never dead-ends on a broken checkout.
    """
    defaults_path = Path(__file__).resolve().parent / "autonomy.defaults.json"
    try:
        return json.loads(defaults_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {
            "version": 1,
            "on_by_default": {},
            "off_by_default": {
                "boardroom": {
                    "label": "Boardroom",
                    "plain": "A simulated C-suite that debates your decisions and watches the system for improvements.",
                    "token_cost": "token-heavy; recommended only on Claude Max",
                    "recommends_max": True,
                },
                "morning_briefing": {
                    "label": "Morning briefing",
                    "plain": "A short daily digest each morning; can fold in boardroom findings.",
                    "token_cost": "light-to-moderate daily",
                },
                "email_digests": {
                    "label": "Email digests / outbound",
                    "plain": "I can send you digests or draft outbound email on a schedule.",
                    "token_cost": "moderate; scales with volume",
                },
                "scheduled_automations": {
                    "label": "Scheduled automations / crons",
                    "plain": "Timed background jobs: self-heal on a timer, backups, watchdogs.",
                    "token_cost": "varies by job; can add up",
                },
            },
        }


# --- the greeting -----------------------------------------------------------
def greeting() -> None:
    """
    Warm, non-technical welcome. Reassures a total beginner that the command
    line is home now and that LeRoy will guide them.
    """
    print("\n" + "=" * 60)
    print("  Hi — welcome to LeRoy")
    print("  (Learning Engine for Real-time Optimization & Yield)")
    print("=" * 60)
    print()
    print("  I'm here to learn how you work and get better every day.")
    print("  The command line is home now — don't worry, I'll guide you.")
    print()
    print("  We'll do a handful of quick questions in a few short phases.")
    print("  Every answer builds a real file in your memory vault, so you'll")
    print("  watch your second brain get built in front of you.")
    print()
    print("  Nothing is locked in - answer what you like, press Enter to move")
    print("  to the next question, and you can change any of this later.")
    print("  Let's get to know each other.")


# --- the phases -------------------------------------------------------------
def phase1_you(vault: Path) -> dict:
    print("\n" + "=" * 60)
    print("  Phase 1 — You")
    print("  (Builds USER.md and tunes how I talk to you.)")
    print("=" * 60)

    name = ask("First — who am I working for? Your name?", default="")
    role = ask("What do you do, and what's your role?", default="")
    technical = ask(
        "How technical are you? (so I know how much to explain) "
        "e.g. 'non-technical', 'some', 'engineer'",
        default="some",
    )
    comms = ask(
        "How do you like me to talk to you — 'brief and direct' or 'thorough'?",
        default="brief and direct",
    )

    display_name = name or "there"
    user_md = f"""# USER.md — who I'm working for

- **Name:** {name or "(not set)"}
- **Role / what you do:** {role or "(not set)"}
- **Technical level:** {technical}
- **Comms preference:** {comms}

_Established during `leroy init` on {today()}. I'll refine this as we work together._
"""
    write_file(vault / "USER.md", user_md)

    # Tune SOUL.md — behavior contract. Preserve any existing template body,
    # then append the personalization block.
    soul_path = vault / "SOUL.md"
    base = soul_path.read_text(encoding="utf-8") if soul_path.exists() else "# SOUL.md — how LeRoy behaves\n"
    tuning = f"""

## Personalization (set {today()})
- Address the user as **{display_name}**.
- Default communication style: **{comms}**.
- Assume technical level: **{technical}** — calibrate explanation depth to match.
"""
    if "## Personalization" not in base:
        write_file(soul_path, base + tuning)
    else:
        print(f"    (SOUL.md already personalized — left as-is)")

    return {"name": display_name, "technical": technical, "comms": comms}


def phase2_work(vault: Path) -> None:
    print("\n" + "=" * 60)
    print("  Phase 2 — Your work")
    print("  (Seeds Goals/, Projects/, People/ so recall isn't empty on day one.)")
    print("=" * 60)

    goals = ask(
        "What are you trying to get done this month? (1-3 things, comma-separated)",
        default="",
    )
    for g in [x.strip() for x in goals.split(",") if x.strip()]:
        write_file(
            vault / "Goals" / f"{slug(g)}.md",
            f"""---
type: goal
status: active
created: {today()}
---

# Goal: {g}

**Target:** this month.

_Seeded during onboarding. Add milestones as they firm up._
""",
        )

    projects = ask(
        "What are you working on right now that I should track? (comma-separated)",
        default="",
    )
    for p in [x.strip() for x in projects.split(",") if x.strip()]:
        write_file(
            vault / "Projects" / slug(p) / "index.md",
            f"""---
type: project
status: active
created: {today()}
---

# {p}

_Active project. I'll distill context here as we work on it._

## Timeline
- {today()} — project registered during onboarding.
""",
        )

    people = ask(
        "Who do you work with most? (names, comma-separated — I'll start contact files)",
        default="",
    )
    for person in [x.strip() for x in people.split(",") if x.strip()]:
        write_file(
            vault / "People" / f"{slug(person)}.md",
            f"""---
type: person
created: {today()}
---

# {person}

- **Relationship:** (to fill in)
- **Last contact:** —

_Contact stub seeded during onboarding._
""",
        )


def phase3_tools(vault: Path, dest: Path) -> None:
    print("\n" + "=" * 60)
    print("  Phase 3 — Your tools")
    print("  (Optional. Each tool you connect gets a Reference/ note + local .env stub.)")
    print("  Everything here is skippable — no dead-ends if you say 'not now'.")
    print("=" * 60)

    # Keys never go in the vault; .env lives at the config root, git-ignored.
    env_path = dest / ".env"
    env_lines: list[str] = []

    def offer(tool_name: str, question: str, env_keys: list[str]) -> None:
        if not ask_yes(question, default=False):
            return
        write_file(
            vault / "Reference" / f"{slug(tool_name)}.md",
            f"""---
type: reference
tool: {tool_name}
connected: {today()}
---

# {tool_name} (connected)

Wired during onboarding. Credentials live in `~/.claude/.env` (local, git-ignored).
Required keys: {", ".join(env_keys) or "none"}.

Run `leroy mcp add` to (re)configure or `leroy doctor` to verify the connection.
""",
        )
        for k in env_keys:
            env_lines.append(f"# {tool_name}\n{k}=")
        print(f"    {OK} noted {tool_name}. I'll help you fill the keys next time via `leroy mcp add`.")

    offer("CRM", "Do you use a CRM you'd like me to connect?", ["CRM_API_KEY"])
    offer("Gmail / Google Workspace", "Connect Gmail / Google Workspace?", ["GOOGLE_OAUTH_CLIENT_ID", "GOOGLE_OAUTH_CLIENT_SECRET"])

    other = ask("Any other system I should talk to? (name it, or skip)", default="")
    if other:
        offer(other, f"Set up a connector stub for '{other}' now?", [f"{slug(other).upper().replace('-', '_')}_API_KEY"])

    if env_lines:
        # Append to .env additively — never clobber existing keys.
        existing = env_path.read_text(encoding="utf-8") if env_path.exists() else ""
        header = "" if existing.endswith("\n") or not existing else "\n"
        env_path.write_text(existing + header + "\n".join(env_lines) + "\n", encoding="utf-8")
        print(f"    {WROTE} {env_path}  (fill in the values, keys stay local)")
    else:
        print("    (no tools connected — you can always run `leroy mcp add` later)")


def phase4_feedback(vault: Path) -> None:
    print("\n" + "=" * 60)
    print("  Phase 4 — How you like things done")
    print("  (Seeds Feedback/ — the corrections layer that makes me feel like your team.)")
    print("=" * 60)

    rules = ask(
        "Any hard rules or pet peeves? "
        "(e.g. 'never send email without showing me first')",
        default="",
    )
    if rules:
        write_file(
            vault / "Feedback" / "hard-rules.md",
            f"""---
type: feedback
created: {today()}
---

# Hard rules & pet peeves

{rules}

**Why:** stated directly by the user during onboarding.
**How to apply:** treat these as non-negotiable defaults in every session.
""",
        )

    good_day = ask("What does a good day of help from me look like?", default="")
    if good_day:
        write_file(
            vault / "Feedback" / "what-good-looks-like.md",
            f"""---
type: feedback
created: {today()}
---

# What a good day of help looks like

{good_day}

**Why:** the user's own definition of success.
**How to apply:** optimize toward this outcome when choosing how to help.
""",
        )


def phase5_autonomy(dest: Path, defaults: dict) -> dict:
    """
    No questions asked here anymore (2026-07-20 — interview was running long,
    mostly on capability opt-ins better discovered as UI shortcuts than forced
    yes/no's mid-interview). Every off-by-default feature starts OFF; the user
    turns any of them on later — from the app's own shortcuts/panels (Boardroom
    already has its in-panel toggle) or `leroy enable <feature>` — at their own
    pace, once they've actually seen what's there. This still writes
    ~/.claude/config/autonomy.json (other code, e.g. brain_interview_done
    detection, depends on that file existing) — it just no longer interrupts
    onboarding to ask about it.
    """
    off_items = defaults.get("off_by_default", {})
    picks = {
        key: False
        for key, spec in off_items.items()
        if not key.startswith("_") and isinstance(spec, dict)
    }
    write_autonomy_config(dest, defaults, picks)
    print("\n  (Extras like morning briefings and scheduled automations are off by")
    print("   default — turn any on later from the app whenever you want them.)")
    return {"picks": picks, "enabled_any": False}


def write_autonomy_config(dest: Path, defaults: dict, picks: dict) -> Path:
    """
    Persist the user's choices to ~/.claude/config/autonomy.json. ON-by-default
    features are recorded as enabled; OFF-by-default features carry the user's
    yes/no. `wired` stays False for everything until `leroy enable` acts on it.
    """
    cfg_dir = dest / "config"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    cfg_path = cfg_dir / "autonomy.json"

    features: dict[str, dict] = {}
    for key, spec in defaults.get("on_by_default", {}).items():
        if key.startswith("_"):
            continue
        features[key] = {
            "label": spec.get("label", key),
            "default": "on",
            "enabled": True,
            "wired": True,  # on-by-default features are active out of the box
            "autonomous": bool(spec.get("autonomous", False)),
        }
    for key, spec in defaults.get("off_by_default", {}).items():
        if key.startswith("_"):
            continue
        want = bool(picks.get(key, False))
        features[key] = {
            "label": spec.get("label", key),
            "default": "off",
            "enabled": want,
            "wired": False,  # never wired at install time; `leroy enable` does that
            "autonomous": bool(spec.get("autonomous", True)),
        }

    payload = {
        "version": defaults.get("version", 1),
        "updated": today(),
        "note": "User autonomy choices. OFF-by-default features are recorded here "
                "but only wired when `leroy enable <feature>` runs.",
        "features": features,
    }
    cfg_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"    {WROTE} {cfg_path}")

    write_pending_setup(dest, features)
    return cfg_path


def write_pending_setup(dest: Path, features: dict) -> None:
    """
    If the user enabled anything that isn't wired yet, drop a small marker file
    listing exactly what's pending. core/CLAUDE.md's Position Zero checks for
    this file at the start of every session and walks the user through wiring
    each item one at a time via `leroy enable <feature>` — this is what makes
    saying "yes" during onboarding actually lead somewhere, instead of silently
    recording a pick nobody ever acts on. `leroy enable`/`autonomy.py` deletes
    this file once every pending item is resolved, so the guidance in CLAUDE.md
    never resurfaces after the user is done — no CLAUDE.md edits needed per
    user, just this ephemeral file coming and going.
    """
    pending = [
        {"key": key, "label": spec.get("label", key)}
        for key, spec in features.items()
        if spec.get("enabled") and not spec.get("wired")
    ]
    pending_path = dest / "config" / "pending-autonomy-setup.json"
    if not pending:
        # Nothing pending (common case: user opted into nothing, or everything
        # they picked is already wired) - make sure a stale marker from a
        # previous run doesn't linger and trigger guidance for nothing.
        pending_path.unlink(missing_ok=True)
        return
    pending_path.parent.mkdir(parents=True, exist_ok=True)
    pending_path.write_text(
        json.dumps({"created": today(), "pending": pending}, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"    {WROTE} {pending_path}")


def phase6_subscription(autonomy: dict) -> None:
    """
    Plain-English guidance on what LeRoy runs on. Everything runs on a Claude
    subscription. Interactive use is fine on Pro; recommend Max if they enabled
    autonomous features (especially the boardroom). No local model is required.
    """
    print("\n" + "=" * 60)
    print("  Phase 6 — What LeRoy runs on")
    print("=" * 60)
    print()
    print("  LeRoy runs entirely on your Claude subscription — no separate API")
    print("  bill, no metering. Just talking to me day to day works great on")
    print("  Claude Pro.")

    picks = autonomy.get("picks", {})
    if autonomy.get("enabled_any"):
        boardroom_on = picks.get("boardroom", False)
        print()
        if boardroom_on:
            print("  You turned on the Boardroom, which is token-heavy. For that I")
            print("  recommend Claude Max ($100/mo) so background debates don't eat")
            print("  into your day-to-day usage.")
        else:
            print("  You turned on some autonomous features. If they start crowding")
            print("  your usage, Claude Max ($100/mo) gives you a lot more room.")
    else:
        print()
        print("  You didn't turn on any autonomous features, so Pro is plenty.")
        print("  If you enable the Boardroom later, consider Claude Max ($100/mo).")

    print()
    print("  No local model needed — everything runs on Claude. A local model")
    print("  (e.g. Ollama) is optional, and only then does it offload cheap work")
    print("  to save tokens. Skip it entirely if you're not sure.")


def phase7_shortcut(dest: Path) -> None:
    """
    Desktop shortcut status check — NOT creation.

    installer\\shortcuts.ps1 (called from setup.ps1 step 5, BEFORE this
    interview ever starts) is the single, authoritative owner of the "Leroy CLI"
    Desktop shortcut (a terminal that opens in ~/.claude and starts Claude Code
    there). The LeRoy UI desktop app installs its own "LeRoy UI" shortcut
    separately. This phase only reports whether the CLI shortcut is present — it
    never creates anything (a second creation path for the same Desktop is a
    correctness bug waiting to happen).
    """
    print("\n" + "=" * 60)
    print("  Phase 7 — Desktop shortcuts")
    print("=" * 60)

    have_cli = (_desktop_dir() / "Leroy CLI.lnk").exists()

    if have_cli:
        print("    Found your 'Leroy CLI' shortcut on the Desktop (created during install).")
        return

    if sys.platform.startswith("win"):
        print("    Didn't find the 'Leroy CLI' Desktop shortcut.")
        print("    Re-run installer\\shortcuts.ps1 any time to (re)create it:")
        print(f"      powershell -File shortcuts.ps1 -ClaudeHome \"{dest}\"")
    else:
        print("    Double-click shortcuts are Windows-only in this build.")
        print("    On macOS/Linux, add a shell alias instead, e.g.:")
        print("      echo 'alias leroy=\"cd ~/.claude && leroy\"' >> ~/.zshrc")


def close(name: str) -> None:
    print("\n" + "=" * 60)
    print(f"  {OK}  You're live, {name}.")
    print("  Everything you turned on is ready; anything else you can enable")
    print("  later with `leroy enable <feature>`.")
    print()
    print("  I'll learn the rest by working with you — every conversation makes me sharper.")
    print()
    print("  Type  `leroy`         to begin a session.")
    print("  Type  `leroy doctor`  to see what's on/off.")
    print("  Type  `leroy memory`  to watch your vault grow.")
    print("=" * 60 + "\n")


def mark_interview_complete(dest: Path) -> Path:
    """Write the authoritative onboarding-completion marker.

    Distinct from config/autonomy.json (written mid-interview by phase5): the
    backend's brain_interview_done detection reads THIS file, so completion is
    only ever signalled after the full interview runs to the end."""
    cfg_dir = dest / "config"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    marker = cfg_dir / "onboarding_complete.json"
    marker.write_text(
        json.dumps({
            "completed": True,
            "completed_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
            "wizard_version": 1,
        }),
        encoding="utf-8",
    )
    return marker


def main(argv: list[str] | None = None) -> int:
    global JSON_MODE

    parser = argparse.ArgumentParser(description="LeRoy first-run interview (leroy init)")
    parser.add_argument("--dest", type=Path, default=None, help="override ~/.claude (testing)")
    parser.add_argument("--seed", type=Path, default=None, help="override the memory.seed/ template dir")
    parser.add_argument(
        "--json", action="store_true",
        help="drive the interview over JSON lines on stdin/stdout (used by the LeRoy UI onboarding screen)",
    )
    args = parser.parse_args(argv)

    JSON_MODE = args.json

    dest = (args.dest or (Path.home() / ".claude")).resolve()
    seed = args.seed or (Path(__file__).resolve().parent.parent / "memory.seed")
    defaults = load_autonomy_defaults()

    if not JSON_MODE:
        greeting()

    vault = ensure_vault(dest, seed)
    print(f"\n  Vault: {vault}")

    ctx = phase1_you(vault)
    phase2_work(vault)
    # phase3_tools (connect CRM/Gmail/other) is intentionally not called during
    # the interview anymore (2026-07-20) — connecting a tool is a "when I need
    # it" action, not a get-to-know-you question. Still available any time via
    # `leroy mcp add`.
    phase4_feedback(vault)
    autonomy = phase5_autonomy(dest, defaults)
    phase6_subscription(autonomy)
    phase7_shortcut(dest)

    name = ctx.get("name", "there")
    # Authoritative "interview finished" signal. MUST be written only here, after
    # every phase has run — NOT at phase5 (config/autonomy.json). brain_interview_done
    # detection keys off this marker so an interview interrupted after phase5 (with
    # autonomy.json already on disk) is not mistaken for complete on the next launch,
    # and the UI reveals only once the whole interview has actually finished.
    mark_interview_complete(dest)
    if JSON_MODE:
        print(json.dumps({"type": "done", "name": name}), flush=True)
    else:
        close(name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
