#!/usr/bin/env python3
"""
gmail-sender-guard.py v1.0 -- PreToolUse hard block on wrong-identity Gmail sends.

Triggered: 2026-05-06 after 5 client emails leaked from personal@example.com
(personal Gmail) instead of you@example.com (YourCo business).

Matcher (configured in settings.json):
  mcp__google-personal__.*|mcp__google-twg__.*|mcp__google-hmb__gmail_send|mcp__google-hmb__gmail_createDraft

Block rules (any match = exit 2):
  1. Tool prefix is mcp__google-personal__ AND tool name contains 'send' or 'draft'
     -> HARD BLOCK unless session/personal-gmail-allow.flag exists with reason.
  2. Tool prefix is mcp__google-twg__ AND tool name contains 'send' or 'draft'
     -> HARD BLOCK unless session/PartnerCo-gmail-allow.flag exists with reason.
  3. Any send/draft (any MCP) where args.from / args.sender contains 'bdscott0988'
     -> HARD BLOCK -- belt and suspenders.

Override path (rare, deliberate):
    Brian must say in current message: "send from my personal" / "use bdscott"
    AND someone must create the allow flag file with a one-line reason:
        echo "Sending personal RSVP to non-client" > session/personal-gmail-allow.flag
    Flag is auto-deleted by this hook AFTER the send (single-use).

SAFETY: entire body wrapped in try/except. NEVER blocks on parse error
(returns 0) so a buggy hook can't break the whole pipeline.

Log: session/gmail-sender-guard.log -- every block AND every allowed send.
"""

import json
import sys
import os
from pathlib import Path
from datetime import datetime, timezone

CLAUDE_ROOT = Path.home() / ".claude"
SESSION_DIR = CLAUDE_ROOT / "session"
LOG_FILE = SESSION_DIR / "gmail-sender-guard.log"
PERSONAL_FLAG = SESSION_DIR / "personal-gmail-allow.flag"
TWG_FLAG = SESSION_DIR / "PartnerCo-gmail-allow.flag"

PERSONAL_PREFIX = "mcp__google-personal__"
TWG_PREFIX = "mcp__google-twg__"
HMB_PREFIX = "mcp__google-hmb__"
CLAUDE_AI_GMAIL_PREFIX = "mcp__claude_ai_Gmail__"
# Live YourCo send/draft tool names have changed over time
# (gmail_send -> send_gmail_message). Detection is name-agnostic via
# _is_send_or_draft(); this set is kept only for explicit allow-logging.
HMB_SEND_TOOLS = {
    "mcp__google-hmb__gmail_send", "mcp__google-hmb__gmail_createDraft",
    "mcp__google-hmb__send_gmail_message", "mcp__google-hmb__draft_gmail_message",
}

SUSPECT_FROM_FIELDS = ["from", "From", "sender", "fromAddress", "from_email", "fromEmail"]
FORBIDDEN_FROM_SUBSTRINGS = ["bdscott0988", "personal@example.com"]

# --- Branding enforcement (added 2026-06-29 after unbranded ExampleClient send) ---
# A substantive outbound email sent as PLAIN text only (no HTML alternative,
# no isHtml flag) is unbranded and must be blocked. Short confirmations exempt.
BRANDING_PLAIN_EXEMPT_LEN = 140
BODY_FIELDS = ["body", "text", "plain_body", "message", "content", "bodyText"]
HTML_FIELDS = ["htmlBody", "html", "html_body", "htmlContent", "bodyHtml"]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _log(line: str) -> None:
    try:
        SESSION_DIR.mkdir(parents=True, exist_ok=True)
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(f"{_now()}  {line}\n")
    except Exception:
        pass


def _block(reason: str, tool: str) -> None:
    _log(f"BLOCK tool={tool} reason={reason}")
    sys.stderr.write(
        "[GMAIL-SENDER-GUARD] BLOCKED\n"
        f"Tool: {tool}\n"
        f"Reason: {reason}\n\n"
        "YourCo (you@example.com) is the ONLY sanctioned outbound on this machine.\n"
        "If this is intentional, Brian must say so explicitly AND someone must create:\n"
        "    session/personal-gmail-allow.flag   (for bdscott0988)\n"
        "    session/PartnerCo-gmail-allow.flag        (for team@example.com)\n"
        "with a one-line written reason inside.\n"
    )
    sys.exit(2)


def _is_send_or_draft(tool_name: str) -> bool:
    lowered = tool_name.lower()
    return ("send" in lowered) or ("draft" in lowered) or ("createdraft" in lowered)


def _check_personal(tool: str) -> None:
    if not tool.startswith(PERSONAL_PREFIX):
        return
    if not _is_send_or_draft(tool):
        return  # read/search tools are fine
    if PERSONAL_FLAG.exists():
        try:
            reason = PERSONAL_FLAG.read_text(encoding="utf-8").strip()
            _log(f"ALLOW personal-send tool={tool} reason={reason!r} (consuming flag)")
            PERSONAL_FLAG.unlink()  # single-use flag
            return
        except Exception:
            pass
    _block(
        "Refusing to send/draft from personal@example.com (personal). "
        "Five client emails leaked from this address on 2026-05-06; protocol is now hard-locked.",
        tool,
    )


def _check_twg(tool: str) -> None:
    if not tool.startswith(TWG_PREFIX):
        return
    if not _is_send_or_draft(tool):
        return
    if TWG_FLAG.exists():
        try:
            reason = TWG_FLAG.read_text(encoding="utf-8").strip()
            _log(f"ALLOW PartnerCo-send tool={tool} reason={reason!r} (consuming flag)")
            TWG_FLAG.unlink()
            return
        except Exception:
            pass
    _block(
        "Refusing to send/draft from team@example.com (PartnerCo). "
        "PartnerCo outbound requires explicit user instruction + allow flag on this machine.",
        tool,
    )


def _check_from_field(tool: str, args: dict) -> None:
    if not isinstance(args, dict):
        return
    for field in SUSPECT_FROM_FIELDS:
        val = args.get(field)
        if not isinstance(val, str):
            continue
        v = val.lower()
        for needle in FORBIDDEN_FROM_SUBSTRINGS:
            if needle in v:
                _block(
                    f"Outbound message has forbidden sender in {field}={val!r}. "
                    "YourCo is the only valid identity on this machine.",
                    tool,
                )


def _block_branding(tool: str, plain_len: int) -> None:
    _log(f"BLOCK-BRANDING tool={tool} plain_len={plain_len}")
    sys.stderr.write(
        "[GMAIL-SENDER-GUARD] BLOCKED -- unbranded outbound email\n"
        f"Tool: {tool}\n"
        f"A substantive plain-text email ({plain_len} chars) with no HTML branding "
        "was about to be sent.\n\n"
        "YourCo protocol: ALL substantive emails use a branded HTML template.\n\n"
        "Training/session recap or client status emails -> use the NAVY/BLUE table\n"
        "template at skills/user/YourCo-email-recap-template.html (confirmed canonical\n"
        "2026-07-08 against actual Sent mail). Invoices/reports only -> "
        "skills/user/YourCo-brand-assets.md.\n\n"
        "FIX: load skills/integrations/gmail-send-protocol.md, pick the correct\n"
        "template for the email type above, and resend with a branded htmlBody.\n"
        "Only single-line confirmations ('ok thanks') may go plain text.\n"
    )
    sys.exit(2)


def _first_str(args: dict, fields) -> str:
    for f in fields:
        v = args.get(f)
        if isinstance(v, str) and v.strip():
            return v
    return ""


def _check_branding(tool: str, args: dict) -> None:
    """Block substantive PLAIN-only outbound emails (no HTML, no isHtml).

    Conservative by design: only blocks when we are confident the email is
    unbranded -- a substantive plain `body` with NO html alternative and NO
    isHtml flag. Any html field or isHtml=true is assumed to be the branded
    composer path and passes. This precisely catches the 2026-06-29 failure
    (plain-text ExampleClient cancellation) without risking the real branded paths.
    """
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
        return  # has an HTML alternative -> assume branded composer path
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

        # Order: personal first (most likely leak), then PartnerCo, then content scan.
        _check_personal(tool)
        _check_twg(tool)
        _check_from_field(tool, args)

        # Branding enforcement (all matched gmail send/draft tools).
        _check_branding(tool, args)

        # claude.ai Gmail is a FALLBACK path (used when google-YourCo MCP is down,
        # as on 2026-06-29). Identity cannot be verified from args; log loudly.
        if tool.startswith(CLAUDE_AI_GMAIL_PREFIX) and _is_send_or_draft(tool):
            _log(f"ALLOW-FALLBACK claude-ai-gmail tool={tool} (verify account is YourCo)")
        elif tool in HMB_SEND_TOOLS or (tool.startswith(HMB_PREFIX) and _is_send_or_draft(tool)):
            _log(f"ALLOW YourCo-send tool={tool}")
        sys.exit(0)
    except SystemExit:
        raise
    except Exception as e:
        _log(f"ERROR (failing open) {type(e).__name__}: {e}")
        sys.exit(0)


if __name__ == "__main__":
    main()
