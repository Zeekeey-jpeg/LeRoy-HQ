#!/usr/bin/env python3
"""
LeRoy — autonomy.py
===================
Backs `leroy enable <feature>`, `leroy disable <feature>`, and the autonomy
section of `leroy doctor`. Reads / writes ~/.claude/config/autonomy.json (the
file the wizard creates at install time).

  enable  <feature>  -> flip enabled=true, then WIRE it (register cron / add module)
  disable <feature>  -> flip enabled=false, then UNWIRE it (unschedule)
  status             -> print which autonomy features are on/off (for `leroy doctor`)

Wiring for the token-burning features currently hands off to other scripts
(cron registration, module merge). Those calls are marked with clear TODOs where
the real integration lands; the config flip + on/off bookkeeping is real today.

Stdlib only, so it runs on a fresh machine.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
from pathlib import Path

_UTF_OK = True
try:
    "✅⚪🔴".encode(sys.stdout.encoding or "utf-8")
except (UnicodeEncodeError, LookupError):
    _UTF_OK = False

ON = "✅" if _UTF_OK else "[on ]"
OFF = "⚪" if _UTF_OK else "[off]"
BAD = "🔴" if _UTF_OK else "[!!]"


def config_path(dest: Path) -> Path:
    return dest / "config" / "autonomy.json"


def load_config(dest: Path) -> dict | None:
    path = config_path(dest)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def save_config(dest: Path, cfg: dict) -> None:
    path = config_path(dest)
    path.parent.mkdir(parents=True, exist_ok=True)
    cfg["updated"] = _dt.date.today().isoformat()
    path.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")


# --- wiring stubs -----------------------------------------------------------
# Enable/disable does two things: (1) flips the config flag [real, done here],
# and (2) wires/unwires the actual feature. The wiring for the autonomous
# features is where LeRoy's cron + module systems get touched — kept as clearly
# labelled stubs so the flip works today and the integration is obvious.

def wire_feature(key: str, dest: Path) -> None:
    """Turn a feature ON in the real system (register cron / add module)."""
    if key == "boardroom":
        # TODO(wiring): register the boardroom scene cron (governor.json driven)
        #   and additive-merge modules/boardroom. e.g. call merge.py --source
        #   ../modules/boardroom, then CronCreate the scene driver.
        print(f"    (stub) would register the boardroom cron + add the boardroom module")
    elif key == "morning_briefing":
        # TODO(wiring): CronCreate a daily morning-briefing job.
        print(f"    (stub) would schedule the daily morning briefing")
    elif key == "email_digests":
        # TODO(wiring): CronCreate the digest/outbound job (outbound stays
        #   draft-gated by the gmail guard).
        print(f"    (stub) would schedule email digests (outbound stays draft-gated)")
    elif key == "scheduled_automations":
        # TODO(wiring): CronCreate the selected background jobs (self-heal timer,
        #   backup, watchdog).
        print(f"    (stub) would register the background crons (self-heal timer, backup, watchdog)")
    else:
        # On-by-default features are already active; nothing to schedule.
        print(f"    (nothing to schedule for '{key}')")


def unwire_feature(key: str, dest: Path) -> None:
    """Turn a feature OFF in the real system (unschedule / remove)."""
    if key in {"boardroom", "morning_briefing", "email_digests", "scheduled_automations"}:
        # TODO(wiring): CronDelete the job(s) registered for this feature.
        print(f"    (stub) would unschedule the cron(s) for '{key}'")
    else:
        print(f"    (nothing scheduled for '{key}')")


# --- commands ---------------------------------------------------------------
def _no_config_msg(dest: Path) -> None:
    print(f"  {BAD} No autonomy config at {config_path(dest)}.")
    print("     Run 'leroy init' first (it creates config/autonomy.json).")


def cmd_enable(dest: Path, feature: str) -> int:
    cfg = load_config(dest)
    if cfg is None:
        _no_config_msg(dest)
        return 1
    feats = cfg.setdefault("features", {})
    if feature not in feats:
        print(f"  {BAD} Unknown feature '{feature}'. Known: {', '.join(sorted(feats)) or '(none)'}")
        return 1
    entry = feats[feature]
    if entry.get("enabled") and entry.get("wired"):
        print(f"  {ON} '{feature}' is already enabled.")
        return 0
    entry["enabled"] = True
    print(f"  Enabling '{entry.get('label', feature)}'...")
    wire_feature(feature, dest)
    entry["wired"] = True
    save_config(dest, cfg)
    print(f"  {ON} '{feature}' is on.")
    return 0


def cmd_disable(dest: Path, feature: str) -> int:
    cfg = load_config(dest)
    if cfg is None:
        _no_config_msg(dest)
        return 1
    feats = cfg.setdefault("features", {})
    if feature not in feats:
        print(f"  {BAD} Unknown feature '{feature}'. Known: {', '.join(sorted(feats)) or '(none)'}")
        return 1
    entry = feats[feature]
    if not entry.get("enabled"):
        print(f"  {OFF} '{feature}' is already off.")
        return 0
    print(f"  Disabling '{entry.get('label', feature)}'...")
    unwire_feature(feature, dest)
    entry["enabled"] = False
    entry["wired"] = False
    save_config(dest, cfg)
    print(f"  {OFF} '{feature}' is off.")
    return 0


def cmd_status(dest: Path) -> int:
    cfg = load_config(dest)
    if cfg is None:
        # Not an error for `leroy doctor` — just report it's not set up.
        print("  Autonomy: not configured yet (run 'leroy init').")
        return 0
    feats = cfg.get("features", {})
    print("  Autonomy features:")
    for key, entry in feats.items():
        mark = ON if entry.get("enabled") else OFF
        label = entry.get("label", key)
        default = entry.get("default", "?")
        tail = "" if entry.get("enabled") else f"  (default {default})"
        print(f"    {mark}  {label:<28} [{key}]{tail}")
    print("  Toggle with: leroy enable <feature> | leroy disable <feature>")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="LeRoy autonomy feature toggles")
    parser.add_argument("action", choices=["enable", "disable", "status"])
    parser.add_argument("feature", nargs="?", default=None)
    parser.add_argument("--dest", type=Path, default=None, help="override ~/.claude (testing)")
    args = parser.parse_args(argv)

    dest = (args.dest or (Path.home() / ".claude")).resolve()

    if args.action == "status":
        return cmd_status(dest)
    if not args.feature:
        print(f"  Usage: leroy {args.action} <feature>")
        return 1
    if args.action == "enable":
        return cmd_enable(dest, args.feature)
    return cmd_disable(dest, args.feature)


if __name__ == "__main__":
    raise SystemExit(main())
