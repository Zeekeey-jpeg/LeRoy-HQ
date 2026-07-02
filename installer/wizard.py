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

VAULT_FOLDERS = [
    "People", "Projects", "Goals", "Decisions", "Boardroom",
    "Chat", "Feedback", "Patterns", "Reference", "Archive",
]


def today() -> str:
    return _dt.date.today().isoformat()


def slug(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s or "untitled"


# --- prompt helpers ---------------------------------------------------------
def ask(prompt: str, default: str = "") -> str:
    """
    Ask a question. Blank input (or 'skip') returns the default.
    Ctrl-C / EOF is treated as 'skip everything gracefully'.
    """
    hint = "  (Enter to skip)" if not default else f"  [{default}]"
    try:
        raw = input(f"\n  {prompt}{hint}\n  > ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\n  (skipping)")
        return default
    if raw.lower() in {"skip", ""}:
        return default
    return raw


def ask_yes(prompt: str, default: bool = False) -> bool:
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
    print("  Nothing is locked in — press Enter to skip any question, and you")
    print("  can change any of this later. Let's get to know each other.")


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
    A la carte autonomy menu. Each item DEFAULT OFF. We RECORD the user's picks
    to ~/.claude/config/autonomy.json — we do NOT install or schedule anything
    here. Enabled features get wired later via `leroy enable <feature>`.
    """
    print("\n" + "=" * 60)
    print("  Phase 5 — Autonomy menu")
    print("  (Turn on the extras you want. Everything here is OFF unless you")
    print("   say yes — and nothing gets scheduled today. You can flip any of")
    print("   these later with `leroy enable <feature>`.)")
    print("=" * 60)

    on_default = defaults.get("on_by_default", {})
    if on_default:
        print("\n  Already ON for you (free, no timers, no autonomous spend):")
        for key, spec in on_default.items():
            if key.startswith("_") or not isinstance(spec, dict):
                continue
            print(f"    {OK}  {spec.get('label', '?')} — {spec.get('plain', '')}")

    off_items = defaults.get("off_by_default", {})
    picks: dict[str, bool] = {}
    enabled_any = False
    for key, spec in off_items.items():
        if key.startswith("_") or not isinstance(spec, dict):
            continue
        label = spec.get("label", key)
        plain = spec.get("plain", "")
        cost = spec.get("token_cost", "")
        print(f"\n  • {label}")
        print(f"    {plain}")
        if cost:
            print(f"    Token cost: {cost}")
        want = ask_yes(f"Turn on {label}?", default=False)
        picks[key] = want
        if want:
            enabled_any = True

    write_autonomy_config(dest, defaults, picks)

    if enabled_any:
        chosen = ", ".join(off_items[k].get("label", k) for k, v in picks.items() if v)
        print(f"\n    {OK} Recorded: {chosen}.")
        print("    These are saved but NOT scheduled yet — run")
        print("    `leroy enable <feature>` when you're ready to wire them up.")
    else:
        print("\n    (No autonomous features turned on — that's the recommended start.)")
        print("    Add any later with `leroy enable <feature>`.")

    return {"picks": picks, "enabled_any": enabled_any}


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
    return cfg_path


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
    interview ever starts) is now the single, authoritative owner of Desktop
    shortcut creation, producing exactly one pair: "Leroy" (UI) + "Leroy CLI"
    (terminal) — the pair items 12/35 require.

    This phase used to ALSO create its own differently-named pair
    ("LeRoy.lnk" + "LeRoy Folder.lnk") as a WS2.5 nicety. That was removed
    (WS6 stress test, 2026-07-01): Windows filenames are case-insensitive, so
    "LeRoy.lnk" from this phase and "Leroy.lnk" from shortcuts.ps1 are THE
    SAME FILE on disk — running this after shortcuts.ps1 silently overwrote
    the real "Leroy" (UI) shortcut with a plain terminal launcher, leaving the
    user with LeRoy(terminal) + LeRoy Folder(explorer) + Leroy CLI instead of
    the required Leroy(UI) + Leroy CLI pair. Two shortcut-creation code paths
    for the same Desktop is a correctness bug waiting to happen, not a
    feature — so this phase no longer creates anything. It only reports.
    """
    print("\n" + "=" * 60)
    print("  Phase 7 — Desktop shortcuts")
    print("=" * 60)

    desktop = Path(os.path.join(os.path.expanduser("~"), "Desktop"))
    have_ui = (desktop / "Leroy.lnk").exists()
    have_cli = (desktop / "Leroy CLI.lnk").exists()

    if have_ui and have_cli:
        print("    Found 'Leroy' and 'Leroy CLI' on your Desktop (created during install).")
        return

    if sys.platform.startswith("win"):
        print("    Didn't find both Desktop shortcuts (Leroy + Leroy CLI).")
        print("    Re-run installer\\shortcuts.ps1 any time to (re)create them:")
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="LeRoy first-run interview (leroy init)")
    parser.add_argument("--dest", type=Path, default=None, help="override ~/.claude (testing)")
    parser.add_argument("--seed", type=Path, default=None, help="override the memory.seed/ template dir")
    args = parser.parse_args(argv)

    dest = (args.dest or (Path.home() / ".claude")).resolve()
    seed = args.seed or (Path(__file__).resolve().parent.parent / "memory.seed")
    defaults = load_autonomy_defaults()

    greeting()

    vault = ensure_vault(dest, seed)
    print(f"\n  Vault: {vault}")

    ctx = phase1_you(vault)
    phase2_work(vault)
    phase3_tools(vault, dest)
    phase4_feedback(vault)
    autonomy = phase5_autonomy(dest, defaults)
    phase6_subscription(autonomy)
    phase7_shortcut(dest)
    close(ctx.get("name", "there"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
