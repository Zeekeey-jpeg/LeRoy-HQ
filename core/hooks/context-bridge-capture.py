#!/usr/bin/env python3
"""
context-bridge-capture.py v1.0 — Cross-channel Context Bridge Capture

PostToolUse hook. Detects hot-button list outputs (numbered, >=3 items,
>200 chars) and writes channels/mobile/context-bridge.json with a 30-min
TTL. The gate/startup hook can pick this up on the next session start and
inject it as recent context (e.g. so a mobile/companion channel can continue
a list the user was just looking at).

Trigger: Bash, WebSearch, or WebFetch output with >=3 numbered items >200 chars.
Never blocks (always exits 0).

REDACTION: this hook mirrors RAW Bash/web output into a file with a 30-minute
TTL. Any echoed token, key, or .env content would sit there in plaintext — a
credential-exfil seam. Key-shaped strings are scrubbed before persisting (same
posture as the identity/PII guards).
"""

import json
import sys
import io
import re
import os
from pathlib import Path
from datetime import datetime, timezone, timedelta

if hasattr(sys.stdin, "buffer"):
    sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding="utf-8", errors="replace")

CLAUDE_DIR = Path(__file__).parent.parent
BRIDGE_FILE = CLAUDE_DIR / "channels" / "mobile" / "context-bridge.json"
BRIDGE_TTL_MINUTES = 30
MIN_OUTPUT_LEN = 200
MIN_LIST_ITEMS = 3
WATCHED_TOOLS = {"Bash", "WebSearch", "WebFetch"}


def has_numbered_list(text: str) -> bool:
    pattern = re.compile(r'(?:^|\n)\s*\d+[\.\)]\s+\S', re.MULTILINE)
    return len(pattern.findall(text)) >= MIN_LIST_ITEMS


def extract_topic(tool_input: dict, tool_name: str) -> str:
    if tool_name == "Bash":
        cmd = tool_input.get("command", "")
        return cmd[:60].strip() or tool_name
    if tool_name in ("WebSearch", "WebFetch"):
        ref = tool_input.get("url", tool_input.get("query", ""))
        return str(ref)[:60].strip() or tool_name
    return tool_name


def extract_output(tool_result) -> str:
    if isinstance(tool_result, dict):
        for key in ("stdout", "output", "content", "text", "result"):
            val = tool_result.get(key)
            if val and isinstance(val, str):
                return val
        return str(tool_result)
    return str(tool_result) if tool_result else ""


# ── Redaction ─────────────────────────────────────────────────────────────────
_KV_SECRET = re.compile(
    r"(?i)([\w-]*(?:api[_-]?key|secret|token|passw(?:or)?d|credential|bearer|auth[_-]?key)[\w-]*)"
    r"(\s*[:=]\s*)(\S{8,})"
)
_KEY_BLOB = re.compile(
    r"\b(sk-[A-Za-z0-9_-]{16,}|AKIA[0-9A-Z]{16}|AIza[0-9A-Za-z_-]{30,}"
    r"|gh[pousr]_[A-Za-z0-9]{30,}"
    r"|eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{5,})\b"
)


def redact(text: str) -> str:
    try:
        text = _KV_SECRET.sub(lambda m: m.group(1) + m.group(2) + "[REDACTED]", text)
        text = _KEY_BLOB.sub("[REDACTED-KEY]", text)
    except Exception:
        pass
    return text


def main():
    try:
        raw = sys.stdin.read()
    except Exception:
        sys.exit(0)

    try:
        data = json.loads(raw) if raw.strip() else {}
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)

    tool_name = data.get("tool_name", "")
    if tool_name not in WATCHED_TOOLS:
        sys.exit(0)

    tool_result = data.get("tool_result") or data.get("tool_response") or {}
    output = extract_output(tool_result)

    if len(output) < MIN_OUTPUT_LEN or not has_numbered_list(output):
        sys.exit(0)

    now = datetime.now(timezone.utc)
    tool_input = data.get("tool_input", {})
    bridge = {
        "written_at": now.isoformat(),
        "expires_at": (now + timedelta(minutes=BRIDGE_TTL_MINUTES)).isoformat(),
        "ttl_minutes": BRIDGE_TTL_MINUTES,
        "source_tool": tool_name,
        "topic": extract_topic(tool_input, tool_name),
        "content": redact(output[:3000]),
    }

    try:
        BRIDGE_FILE.parent.mkdir(parents=True, exist_ok=True)
        tmp = BRIDGE_FILE.with_suffix(".json.tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(bridge, f, indent=2, ensure_ascii=False)
        os.replace(tmp, BRIDGE_FILE)
    except OSError:
        pass

    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        sys.exit(0)
