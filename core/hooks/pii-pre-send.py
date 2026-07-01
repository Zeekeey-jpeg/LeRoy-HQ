#!/usr/bin/env python3
"""
pii-pre-send.py v1.0 — PreToolUse PII guard for email + chat send channels.

Matcher (settings.json): configure it to fire on your outbound send/draft tools,
e.g. an email send tool and a chat/reply tool. The generic detection below keys
off tool-NAME shape (any tool whose name contains 'send'/'draft'/'reply') plus an
explicit allow-set, so it is not bound to any one vendor's MCP.

Spike outcome: this harness does NOT honor stdout payload mutation. AUTO-REDACT
is not possible; all high-confidence blocks use decision:"block" + exit 2.

Action model:
  conf >= 0.9 + sensitive type (CC w/ Luhn, PRIVATE_KEY, AWS_KEY) -> BLOCK (exit 2)
  0.6 <= conf < 0.9 -> BLOCK (exit 2)
  conf < 0.6 -> PASS (log only, exit 0)

Chat/reply channel: ALWAYS log_only unless chat_enforce is set.
Mode: controlled by session/pii-mode.json {"mode": "log_only|enforce"}

DEPENDENCY: expects a detector module at ~/.claude/lib/pii_detector.py exposing
detect(text) -> list of detections (each with .type, .confidence, .span,
.redaction_token). If the module is absent the hook GRACEFULLY DEGRADES to allow
(fail open) — it never blocks a send just because the detector is missing.

SAFETY: entire body wrapped in try/except — NEVER blocks on exception.
"""

import json
import sys
import os
import hashlib
from pathlib import Path
from datetime import datetime, timezone

CLAUDE_ROOT = Path.home() / ".claude"
SESSION_DIR = CLAUDE_ROOT / "session"
DETECTIONS_LOG = SESSION_DIR / "pii-detections.jsonl"
MODE_FILE = SESSION_DIR / "pii-mode.json"
ALLOWLIST_FILE = SESSION_DIR / "pii-allowlist.json"

LIB_DIR = CLAUDE_ROOT / "lib"

SENSITIVE_TYPES = {"CC", "PRIVATE_KEY", "AWS_KEY"}

# Tool-name substrings that mark a CHAT/reply channel (vs. an email channel).
# Chat channels stay log-only unless chat_enforce is explicitly turned on.
CHAT_TOOL_HINTS = ("reply", "chat", "message_send", "sendmessage")

# Tool-name substrings that mark an outbound send/draft action of ANY channel.
SEND_TOOL_HINTS = ("send", "draft", "reply")


def _is_send_tool(tool_name: str) -> bool:
    lowered = (tool_name or "").lower()
    return any(h in lowered for h in SEND_TOOL_HINTS)


def _is_chat_tool(tool_name: str) -> bool:
    lowered = (tool_name or "").lower()
    return any(h in lowered for h in CHAT_TOOL_HINTS)


def _load_mode() -> dict:
    default = {"mode": "log_only", "chat_enforce": False}
    try:
        with open(MODE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return {**default, **data}
    except Exception:
        return default


def _load_allowlist() -> dict:
    try:
        with open(ALLOWLIST_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"patterns": [], "values": [], "recipients": []}


def _recipient_allowlisted(recipient: str, allowlist: dict) -> bool:
    if not recipient:
        return False
    recipients = allowlist.get("recipients", [])
    recipient_lower = recipient.lower().strip()
    for r in recipients:
        if isinstance(r, str) and r.lower().strip() == recipient_lower:
            return True
    return False


def _content_hash(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()[:16]


def _log_detection(tool_name: str, det_type: str, confidence: float,
                   action: str, span: tuple, redaction_token: str,
                   mode: str, target: str, content_hash: str) -> None:
    try:
        SESSION_DIR.mkdir(parents=True, exist_ok=True)
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "session_id": os.environ.get("CLAUDE_SESSION_ID"),
            "tool": tool_name,
            "target": target,
            "type": det_type,
            "confidence": confidence,
            "action": action,
            "content_hash": content_hash,
            "match_span": list(span),
            "redaction_token": redaction_token,
            "mode": mode,
        }
        with open(DETECTIONS_LOG, "a", buffering=1, encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass


def _import_detector():
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "pii_detector", str(LIB_DIR / "pii_detector.py")
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}

        tool_name = payload.get("tool_name", "")
        tool_input = payload.get("tool_input", {})

        mode_config = _load_mode()
        mode = mode_config.get("mode", "log_only")
        chat_enforce = mode_config.get("chat_enforce", False)

        # Only inspect outbound send/draft/reply tools.
        if not _is_send_tool(tool_name):
            print(json.dumps({"decision": "allow"}))
            return

        is_chat = _is_chat_tool(tool_name)

        # Best-effort extraction of body + recipient across tool shapes.
        body_text = (
            tool_input.get("body")
            or tool_input.get("message_body")
            or tool_input.get("text")
            or tool_input.get("content")
            or ""
        )
        recipient = tool_input.get("to", "") or tool_input.get("recipient", "") or ""
        target_label = recipient or ("chat" if is_chat else "email")

        if not body_text:
            print(json.dumps({"decision": "allow"}))
            return

        allowlist = _load_allowlist()

        if not is_chat and _recipient_allowlisted(recipient, allowlist):
            print(json.dumps({"decision": "allow"}))
            return

        try:
            detector = _import_detector()
        except Exception:
            # Detector module missing/broken — fail open.
            print(json.dumps({"decision": "allow"}))
            return

        detections = detector.detect(body_text)

        if not detections:
            print(json.dumps({"decision": "allow"}))
            return

        body_hash = _content_hash(body_text)

        effective_enforce = (mode == "enforce") and (not is_chat or chat_enforce)

        blocked_detection = None
        for det in detections:
            if effective_enforce:
                if det.confidence >= 0.9 and det.type in SENSITIVE_TYPES:
                    blocked_detection = det
                    break
                elif det.confidence >= 0.6:
                    blocked_detection = det
                    break

        for det in detections:
            if effective_enforce and det == blocked_detection:
                action = "blocked"
            else:
                action = "logged"
            _log_detection(
                tool_name=tool_name,
                det_type=det.type,
                confidence=det.confidence,
                action=action,
                span=det.span,
                redaction_token=det.redaction_token,
                mode=mode,
                target=target_label,
                content_hash=body_hash,
            )

        if effective_enforce and blocked_detection:
            block_msg = (
                f"PII DETECTED: {blocked_detection.type} "
                f"(confidence={blocked_detection.confidence:.2f}) found in outbound "
                f"{'chat message' if is_chat else 'email'}. "
                f"Token: {blocked_detection.redaction_token}. "
                f"Mode=enforce — send blocked. "
                f"Remove PII or add to session/pii-allowlist.json to proceed."
            )
            print(json.dumps({"decision": "block", "reason": block_msg}))
            sys.exit(2)

        print(json.dumps({"decision": "allow"}))

    except Exception:
        print(json.dumps({"decision": "allow"}))
        sys.exit(0)


if __name__ == "__main__":
    main()
