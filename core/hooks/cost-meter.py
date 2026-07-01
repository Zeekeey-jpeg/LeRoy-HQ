#!/usr/bin/env python3
"""
cost-meter.py v1.0 — PostToolUse adaptive cost tracker

Appends one JSONL record per tool call to session/cost-log.jsonl using the
locked schema:
  {ts, session_id, trace_id, agent, skill, tool, model,
   tokens_in, tokens_out, cache_w, cache_r, cost_usd,
   source: "api|estimated|fallback", confidence: 0.0-1.0}

Source priority:
  1. api     — metadata.usage present and populated  (confidence 1.0)
  2. estimated — length-based estimate of tool i/o  (confidence 0.6)
  3. fallback — neither available                   (confidence 0.0)

SAFETY: entire body is wrapped in try/except Exception: pass — NEVER blocks.

NOTE: FALLBACK_PRICING below is illustrative. Point PRICING_JSON
(session/pricing.json) at your own per-model rate table to get accurate costs;
otherwise the fallback rates are used.
"""

import json
import sys
import os
from pathlib import Path
from datetime import datetime, timezone

COST_LOG = Path.home() / ".claude" / "session" / "cost-log.jsonl"
PRICING_JSON = Path.home() / ".claude" / "session" / "pricing.json"
STATE_JSON = Path.home() / ".claude" / "session" / "state.json"
DEFAULT_MODEL = "claude-opus-4-7"

# Illustrative rates (USD per 1M tokens). Override via session/pricing.json.
FALLBACK_PRICING = {
    "claude-opus-4-7":   {"in": 5.00, "out": 25.00, "cache_w": 6.25, "cache_r": 0.50},
    "claude-sonnet-4-6": {"in": 3.00, "out": 15.00, "cache_w": 3.75, "cache_r": 0.30},
    "claude-haiku-4-5":  {"in": 1.00, "out":  5.00, "cache_w": 1.25, "cache_r": 0.10},
}

BYTES_PER_TOKEN_ESTIMATE = 4


def _load_pricing() -> dict:
    try:
        with open(PRICING_JSON, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return FALLBACK_PRICING


def _load_state() -> dict:
    try:
        with open(STATE_JSON, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _compute_cost(tokens_in: int, tokens_out: int, cache_w: int, cache_r: int,
                  model: str, pricing: dict) -> float:
    rates = pricing.get(model, pricing.get(DEFAULT_MODEL, {}))
    if not rates:
        return 0.0
    cost = (
        tokens_in  * rates.get("in",      0.0) / 1_000_000 +
        tokens_out * rates.get("out",     0.0) / 1_000_000 +
        cache_w    * rates.get("cache_w", 0.0) / 1_000_000 +
        cache_r    * rates.get("cache_r", 0.0) / 1_000_000
    )
    return round(cost, 8)


def _estimate_tokens_from_payload(payload: dict) -> tuple[int, int]:
    """Rough length-based estimate: input = serialized tool_input, output = tool_result."""
    tool_input_str = json.dumps(payload.get("tool_input", {}))
    tool_result_str = json.dumps(payload.get("tool_result", {}))
    tokens_in  = max(1, len(tool_input_str.encode("utf-8"))  // BYTES_PER_TOKEN_ESTIMATE)
    tokens_out = max(1, len(tool_result_str.encode("utf-8")) // BYTES_PER_TOKEN_ESTIMATE)
    return tokens_in, tokens_out


def main():
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}

        pricing = _load_pricing()
        state   = _load_state()

        model = (
            os.environ.get("CLAUDE_MODEL", "")
            or os.environ.get("ANTHROPIC_MODEL", "")
            or DEFAULT_MODEL
        )

        agent = None
        skill = None
        try:
            agent = state.get("current_agent") or None
            skill = state.get("current_skill") or None
        except Exception:
            pass

        session_id = state.get("session_id") or os.environ.get("CLAUDE_SESSION_ID") or None
        trace_id   = payload.get("prompt_id") or payload.get("trace_id") or None
        tool_name  = payload.get("tool_name") or payload.get("tool") or "unknown"

        tokens_in  = 0
        tokens_out = 0
        cache_w    = 0
        cache_r    = 0
        source     = "fallback"
        confidence = 0.0

        usage = None
        try:
            usage = payload.get("metadata", {}).get("usage", {})
        except Exception:
            usage = None

        if usage and isinstance(usage, dict) and usage.get("input_tokens") is not None:
            tokens_in  = int(usage.get("input_tokens",  0))
            tokens_out = int(usage.get("output_tokens", 0))
            cache_w    = int(usage.get("cache_creation_input_tokens", 0))
            cache_r    = int(usage.get("cache_read_input_tokens",     0))
            source     = "api"
            confidence = 1.0
        else:
            try:
                tokens_in, tokens_out = _estimate_tokens_from_payload(payload)
                cache_w = 0
                cache_r = 0
                source     = "estimated"
                confidence = 0.6
            except Exception:
                source     = "fallback"
                confidence = 0.0

        cost_usd = _compute_cost(tokens_in, tokens_out, cache_w, cache_r, model, pricing)

        record = {
            "ts":         datetime.now(timezone.utc).isoformat(),
            "session_id": session_id,
            "trace_id":   trace_id,
            "agent":      agent,
            "skill":      skill,
            "tool":       tool_name,
            "model":      model,
            "tokens_in":  tokens_in,
            "tokens_out": tokens_out,
            "cache_w":    cache_w,
            "cache_r":    cache_r,
            "cost_usd":   cost_usd,
            "source":     source,
            "confidence": confidence,
        }

        with open(COST_LOG, "a", buffering=1, encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")

    except Exception:
        pass


if __name__ == "__main__":
    main()
