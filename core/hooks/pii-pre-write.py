#!/usr/bin/env python3
"""
pii-pre-write.py v1.0 — PreToolUse PII guard for Write/Edit on memory paths.

Matcher: Write|Edit

Short-circuits immediately (<1ms) if file_path does NOT match memory/** pattern.
Only scans content on memory path writes.

Spike outcome: AUTO-REDACT is not possible (harness ignores stdout mutation).
All high-confidence detections use decision:"block" + exit 2 in enforce mode.

Action model (same as pii-pre-send.py):
  mode=enforce + conf >= 0.9 + sensitive type -> BLOCK (exit 2)
  mode=enforce + 0.6 <= conf < 0.9 -> BLOCK (exit 2)
  conf < 0.6 -> PASS (log only, exit 0)
  mode=log_only -> always PASS (log only)

Performance budget: <1ms for non-memory paths (early exit), <10ms p99 for memory paths.

DEPENDENCY: expects a detector module at ~/.claude/lib/pii_detector.py exposing
detect(text). If the module is absent the hook GRACEFULLY DEGRADES to allow
(fail open) — it never blocks a write just because the detector is missing.

SAFETY: entire body wrapped in try/except — NEVER blocks on exception.
"""

import json
import sys
import os
import re
import hashlib
from pathlib import Path
from datetime import datetime, timezone

CLAUDE_ROOT = Path.home() / ".claude"
SESSION_DIR = CLAUDE_ROOT / "session"
DETECTIONS_LOG = SESSION_DIR / "pii-detections.jsonl"
MODE_FILE = SESSION_DIR / "pii-mode.json"
LIB_DIR = CLAUDE_ROOT / "lib"

MEMORY_ROOT = str(CLAUDE_ROOT / "memory")

SENSITIVE_TYPES = {"CC", "PRIVATE_KEY", "AWS_KEY"}


def _is_memory_path(file_path: str) -> bool:
    if not file_path:
        return False
    try:
        norm = str(Path(file_path).resolve())
        memory_norm = str(Path(MEMORY_ROOT).resolve())
        return norm.startswith(memory_norm)
    except Exception:
        return "memory" in file_path.replace("\\", "/").lower()


def _load_mode() -> dict:
    default = {"mode": "log_only", "chat_enforce": False}
    try:
        with open(MODE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return {**default, **data}
    except Exception:
        return default


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

        file_path = tool_input.get("file_path", "")

        if not _is_memory_path(file_path):
            print(json.dumps({"decision": "allow"}))
            return

        if tool_name == "Write":
            content = tool_input.get("content", "") or ""
        elif tool_name == "Edit":
            content = tool_input.get("new_string", "") or ""
        else:
            print(json.dumps({"decision": "allow"}))
            return

        if not content:
            print(json.dumps({"decision": "allow"}))
            return

        mode_config = _load_mode()
        mode = mode_config.get("mode", "log_only")

        try:
            detector = _import_detector()
        except Exception:
            # Detector module missing/broken — fail open.
            print(json.dumps({"decision": "allow"}))
            return

        detections = detector.detect(content)

        if not detections:
            print(json.dumps({"decision": "allow"}))
            return

        content_hash_val = _content_hash(content)
        target_label = file_path

        effective_enforce = mode == "enforce"

        blocked_detection = None
        if effective_enforce:
            for det in detections:
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
                content_hash=content_hash_val,
            )

        if effective_enforce and blocked_detection:
            block_msg = (
                f"PII DETECTED: {blocked_detection.type} "
                f"(confidence={blocked_detection.confidence:.2f}) found in memory write "
                f"to '{file_path}'. "
                f"Token: {blocked_detection.redaction_token}. "
                f"Mode=enforce — write blocked. "
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
