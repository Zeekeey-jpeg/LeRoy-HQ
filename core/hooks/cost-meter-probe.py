#!/usr/bin/env python3
"""
cost-meter-probe.py v1.0 — PostToolUse diagnostic probe

Dumps a sanitized snapshot of the full stdin payload to session/cost-meter-probe.jsonl
so you can inspect the actual shape of metadata.usage before the adaptive
cost-meter commits to a read strategy.

Run for ~1 day, then remove from settings.json PostToolUse chain.

SAFETY: wraps entire body in try/except — never blocks tool execution.
SANITIZATION: strips any value that looks like a secret (keys with "key", "token",
"secret", "password", "auth", "credential" in the name are replaced with "[REDACTED]").
"""

import json
import sys
import os
from pathlib import Path
from datetime import datetime, timezone

PROBE_LOG = Path.home() / ".claude" / "session" / "cost-meter-probe.jsonl"

SECRET_KEYWORDS = {"key", "token", "secret", "password", "auth", "credential",
                   "api_key", "apikey", "bearer", "private"}


def _sanitize(obj, depth=0):
    """Recursively walk obj, redacting values whose keys suggest secrets."""
    if depth > 10:
        return "[DEPTH_LIMIT]"
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            k_lower = str(k).lower()
            if any(kw in k_lower for kw in SECRET_KEYWORDS):
                out[k] = "[REDACTED]"
            else:
                out[k] = _sanitize(v, depth + 1)
        return out
    if isinstance(obj, list):
        return [_sanitize(item, depth + 1) for item in obj[:20]]
    if isinstance(obj, str) and len(obj) > 500:
        return obj[:200] + "...[TRUNCATED]"
    return obj


def main():
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}

        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "tool_name": payload.get("tool_name", payload.get("tool", "unknown")),
            "has_metadata": "metadata" in payload,
            "has_usage": ("metadata" in payload and "usage" in payload.get("metadata", {})),
            "usage_keys": list(payload.get("metadata", {}).get("usage", {}).keys()),
            "top_level_keys": list(payload.keys()),
            "metadata_keys": list(payload.get("metadata", {}).keys()),
            "sanitized_payload": _sanitize(payload),
        }

        with open(PROBE_LOG, "a", buffering=1, encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

    except Exception:
        pass


if __name__ == "__main__":
    main()
