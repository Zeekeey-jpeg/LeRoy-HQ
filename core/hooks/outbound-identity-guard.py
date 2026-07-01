#!/usr/bin/env python3
"""
outbound-identity-guard.py v1.0 -- PreToolUse hard block on wrong-identity sends.

Incident-born: N client emails once leaked from a personal account instead of
the sanctioned business identity. This guard makes the sanctioned outbound
identity the ONLY one allowed to send/draft from this machine, config-driven so
it works for any tenant.

WHAT IT GUARDS
--------------
Any outbound send/draft tool (email, and by extension chat) whose name matches
the configured MCP prefixes and looks like a send/draft/reply action. Detection
is name-agnostic (contains 'send'/'draft'/'createdraft'/'reply'), so it survives
tool renames.

CONFIG (session/outbound-identity.json), all optional:
  {
    "sanctioned_identity": "you@example.com",   // the ONLY allowed from/sender
    "send_mcp_prefixes": ["mcp__"],             // which MCP namespaces to guard
    "block_unsanctioned_prefixes": [],          // MCP prefixes to HARD block on
                                                //   any send (e.g. a personal
                                                //   account's namespace)
    "forbidden_from_substrings": [],            // never allow these in from/sender
    "branding_enforce": true                    // block substantive plain-text
  }
If the file is absent, sensible fail-open defaults apply (identity check only
runs when a sanctioned_identity is configured; branding enforcement on).

Block rules (any match = decision:block, exit 2):
  1. Tool is under a `block_unsanctioned_prefixes` namespace AND is a send/draft
     -> HARD BLOCK unless the single-use allow flag exists.
  2. Any send/draft whose args.from / args.sender is NOT the sanctioned identity
     (or contains a forbidden substring) -> HARD BLOCK.
  3. Branding: a substantive PLAIN-text send with no HTML/branded alternative
     -> BLOCK (short confirmations exempt).

OVERRIDE (rare, deliberate) — single-use allow flag:
    echo "why this one send is allowed" > session/outbound-identity-allow.flag
  The flag is consumed (deleted) on the next allowed send.

SAFETY: entire body wrapped in try/except. NEVER blocks on parse error
(returns 0) so a buggy hook can't break the whole pipeline.

Log: session/outbound-identity-guard.log -- every block AND every allowed send.
"""

import json
import sys
import os
from pathlib import Path
from datetime import datetime, timezone

CLAUDE_ROOT = Path.home() / ".claude"
SESSION_DIR = CLAUDE_ROOT / "session"
LOG_FILE = SESSION_DIR / "outbound-identity-guard.log"
ALLOW_FLAG = SESSION_DIR / "outbound-identity-allow.flag"
CONFIG_FILE = SESSION_DIR / "outbound-identity.json"

SUSPECT_FROM_FIELDS = ["from", "From", "sender", "fromAddress", "from_email", "fromEmail"]

# --- Branding enforcement ---
# A substantive outbound email sent as PLAIN text only (no HTML alternative,
# no isHtml flag) is unbranded and may be blocked. Short confirmations exempt.
BRANDING_PLAIN_EXEMPT_LEN = 140
BODY_FIELDS = ["body", "text", "plain_body", "message", "content", "bodyText"]
HTML_FIELDS = ["htmlBody", "html", "html_body", "htmlContent", "bodyHtml"]

DEFAULT_CONFIG = {
    "sanctioned_identity": "",          # empty -> identity check is skipped
    "send_mcp_prefixes": ["mcp__"],     # guard all MCP tools by default
    "block_unsanctioned_prefixes": [],  # e.g. ["mcp__email-personal__"]
    "forbidden_from_substrings": [],
    "branding_enforce": True,
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _log(line: str) -> None:
    try:
        SESSION_DIR.mkdir(parents=True, exist_ok=True)
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(f"{_now()}  {line}\n")
    except Exception:
        pass


def _load_config() -> dict:
    cfg = dict(DEFAULT_CONFIG)
    # Env override for the sanctioned identity (handy in CI / headless).
    env_identity = os.environ.get("OUTBOUND_SANCTIONED_IDENTITY", "").strip()
    try:
        if CONFIG_FILE.exists():
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                cfg.update(data)
    except Exception:
        pass
    if env_identity:
        cfg["sanctioned_identity"] = env_identity
    return cfg


def _consume_flag_and_allow(context: str, tool: str) -> None:
    try:
        reason = ALLOW_FLAG.read_text(encoding="utf-8").strip()
        _log(f"ALLOW {context} tool={tool} reason={reason!r} (consuming flag)")
        ALLOW_FLAG.unlink()  # single-use flag
    except Exception:
        pass
    sys.exit(0)


def _block(reason: str, tool: str, sanctioned: str) -> None:
    _log(f"BLOCK tool={tool} reason={reason}")
    ident = sanctioned or "the sanctioned identity"
    sys.stderr.write(
        "[OUTBOUND-IDENTITY-GUARD] BLOCKED\n"
        f"Tool: {tool}\n"
        f"Reason: {reason}\n\n"
        f"{ident} is the ONLY sanctioned outbound identity on this machine.\n"
        "If this send is intentional, create a single-use allow flag with a reason:\n"
        "    echo \"why this one send is allowed\" > session/outbound-identity-allow.flag\n"
    )
    sys.exit(2)


def _is_send_or_draft(tool_name: str) -> bool:
    lowered = (tool_name or "").lower()
    return ("send" in lowered) or ("draft" in lowered) or \
           ("createdraft" in lowered) or ("reply" in lowered)


def _in_guarded_namespace(tool: str, prefixes) -> bool:
    if not prefixes:
        return True  # default: guard everything
    return any(tool.startswith(p) for p in prefixes)


def _check_blocked_prefix(tool: str, cfg: dict) -> None:
    for pref in cfg.get("block_unsanctioned_prefixes", []) or []:
        if tool.startswith(pref) and _is_send_or_draft(tool):
            if ALLOW_FLAG.exists():
                _consume_flag_and_allow("blocked-prefix-override", tool)
            _block(
                f"Refusing to send/draft from a non-sanctioned namespace ('{pref}'). "
                "Sends from this account are hard-locked; use the sanctioned identity.",
                tool,
                cfg.get("sanctioned_identity", ""),
            )


def _check_from_field(tool: str, args: dict, cfg: dict) -> None:
    if not isinstance(args, dict):
        return
    sanctioned = (cfg.get("sanctioned_identity") or "").strip().lower()
    forbidden = [s.lower() for s in (cfg.get("forbidden_from_substrings") or []) if s]

    for field in SUSPECT_FROM_FIELDS:
        val = args.get(field)
        if not isinstance(val, str) or not val.strip():
            continue
        v = val.lower()
        # 1) explicit forbidden substrings always block
        for needle in forbidden:
            if needle in v:
                if ALLOW_FLAG.exists():
                    _consume_flag_and_allow("forbidden-from-override", tool)
                _block(
                    f"Outbound message has a forbidden sender in {field}={val!r}.",
                    tool, cfg.get("sanctioned_identity", ""),
                )
        # 2) if a sanctioned identity is configured, the from MUST be it
        if sanctioned and sanctioned not in v:
            if ALLOW_FLAG.exists():
                _consume_flag_and_allow("wrong-identity-override", tool)
            _block(
                f"Outbound {field}={val!r} is not the sanctioned identity "
                f"({cfg.get('sanctioned_identity')}).",
                tool, cfg.get("sanctioned_identity", ""),
            )


def _first_str(args: dict, fields) -> str:
    for f in fields:
        v = args.get(f)
        if isinstance(v, str) and v.strip():
            return v
    return ""


def _block_branding(tool: str, plain_len: int) -> None:
    _log(f"BLOCK-BRANDING tool={tool} plain_len={plain_len}")
    sys.stderr.write(
        "[OUTBOUND-IDENTITY-GUARD] BLOCKED -- unbranded outbound email\n"
        f"Tool: {tool}\n"
        f"A substantive plain-text email ({plain_len} chars) with no HTML branding "
        "was about to be sent.\n\n"
        "Policy: substantive emails should use your branded template (an HTML body).\n"
        "FIX: compose the message with your branded template and resend with an\n"
        "htmlBody. Only single-line confirmations may go as plain text.\n"
        "To bypass once:\n"
        "    echo \"why plain text is fine here\" > session/outbound-identity-allow.flag\n"
    )
    sys.exit(2)


def _check_branding(tool: str, args: dict, cfg: dict) -> None:
    """Block substantive PLAIN-only outbound emails (no HTML, no isHtml).

    Conservative by design: only blocks when we are confident the email is
    unbranded -- a substantive plain `body` with NO html alternative and NO
    isHtml flag. Any html field or isHtml=true is assumed to be the branded
    path and passes.
    """
    if not cfg.get("branding_enforce", True):
        return
    if not isinstance(args, dict):
        return
    if not _is_send_or_draft(tool):
        return
    body = _first_str(args, BODY_FIELDS)
    html = _first_str(args, HTML_FIELDS)
    is_html_flag = args.get("isHtml") is True or args.get("is_html") is True
    plain_len = len(body.strip())
    if plain_len <= BRANDING_PLAIN_EXEMPT_LEN:
        return  # short confirmation / not substantive
    if html or is_html_flag:
        return  # has an HTML alternative -> assume branded path
    if ALLOW_FLAG.exists():
        _consume_flag_and_allow("branding-override", tool)
    _block_branding(tool, plain_len)


def main() -> None:
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            sys.exit(0)
        payload = json.loads(raw)
    except Exception:
        # Fail open on parse error -- never break the pipeline.
        sys.exit(0)

    try:
        tool = payload.get("tool_name", "") or ""
        args = payload.get("tool_input", {}) or {}
        cfg = _load_config()

        # Only inspect send/draft tools within the guarded namespace.
        if not _is_send_or_draft(tool):
            sys.exit(0)
        if not _in_guarded_namespace(tool, cfg.get("send_mcp_prefixes")):
            sys.exit(0)

        # Order: blocked-namespace first, then identity, then branding.
        _check_blocked_prefix(tool, cfg)
        _check_from_field(tool, args, cfg)
        _check_branding(tool, args, cfg)

        _log(f"ALLOW send tool={tool}")
        sys.exit(0)
    except SystemExit:
        raise
    except Exception as e:
        _log(f"ERROR (failing open) {type(e).__name__}: {e}")
        sys.exit(0)


if __name__ == "__main__":
    main()
