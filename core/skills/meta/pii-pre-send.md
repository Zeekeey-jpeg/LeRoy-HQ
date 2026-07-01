---
name: pii-pre-send
description: PII detection system — guards outbound Gmail/Telegram sends and memory writes. Regex-v1, Presidio interface ready for Sprint 1.5.
tags: [pii, security, privacy, hooks, gmail, telegram, memory]
trigger: "pii status", "pii detections", "pii mode"
version: 1.0
sprint: 1
created: 2026-05-04
---

# PII Pre-Send Guard — Operator Reference

## Overview + Threat Model

The PII detection system protects against accidental exfiltration of sensitive data through three channels:
- **Gmail sends** (`mcp__email-primary__send_mail`, `mcp__claude_ai_Gmail__create_draft`)
- **Telegram messages** (`mcp__plugin_telegram_telegram__reply`)
- **Memory file writes** (Write/Edit tool calls targeting `memory/**` paths)

Threat model: the user or an agent accidentally includes a client SSN, credit card number, AWS key, or private key in an outbound message or in memory. The hook catches it before send/write.

## Spike Outcome (2026-05-04)

**AUTO-REDACT IS DEAD.** The Claude Code harness does NOT honor stdout payload mutation from PreToolUse hooks. The hook must output `{"decision": "allow"}` or `{"decision": "block", "reason": "..."}`. Rewriting tool_input in stdout has no effect.

**Sprint 1 consequence:** conf >= 0.9 sensitive types fall back to BLOCK instead of auto-redact. the user gets a clear error message naming the type detected, then can remove the PII manually and retry.

## Phase A → B Rollout

### Phase A (first 48h — log_only, active now)
- Everything passes through
- All detections logged to `session/pii-detections.jsonl`
- No false-positive friction on real workflow
- **Review log before promoting to Phase B**

### Phase B (enforce mode — requires deliberate promotion)
1. Review `session/pii-detections.jsonl` for false positives
2. Add legitimate patterns to `session/pii-allowlist.json`
3. Validate allowlist covers EINs, order numbers, known business data
4. Flip mode flag (see below)

## Mode Flags

File: `session/pii-mode.json`

```json
{
  "mode": "log_only",
  "telegram_enforce": false
}
```

### Mode options
| Value | Behavior |
|-------|----------|
| `log_only` | All detections logged, nothing blocked. Phase A default. |
| `enforce` | conf >= 0.9 sensitive types + conf >= 0.6 → BLOCK with error message. |

### Telegram override
`telegram_enforce: false` (default, permanent in v1) — Telegram channel is always log-only regardless of `mode` flag. Telegram is a primary channel; unexpected blocks = friction. This is a deliberate design choice per CTO brief. Do not set `telegram_enforce: true` in v1.

### Flipping to enforce mode
```bash
# Edit session/pii-mode.json:
{
  "mode": "enforce",
  "telegram_enforce": false
}
```
ONLY do this after completing the Phase A → B promotion checklist below.

## Phase A → B Promotion Checklist

Before flipping to `"mode": "enforce"`:

- [ ] Read `session/pii-detections.jsonl` — check all logged entries
- [ ] For each false positive: add pattern to `pii-allowlist.json`
- [ ] Verify EIN pattern is in allowlist: `{"regex": "EIN:\\s*\\d{2}-\\d{7}", "reason": "client EIN"}`
- [ ] Verify known business account numbers are in `values` list
- [ ] Run synthetic test manually: `python lib/pii_detector.py` (or scripts/test-pii.py if still present)
- [ ] Confirm EIN input returns 0 detections (allowlist working)
- [ ] Confirm SSN with cue returns conf >= 0.9
- [ ] Flip mode to `enforce`
- [ ] Send one test email with clean content — verify no false block
- [ ] Update sprint tracker: W1.9 acceptance verified

## Allowlist Usage

File: `session/pii-allowlist.json`

```json
{
  "patterns": [
    {"regex": "EIN:\\s*\\d{2}-\\d{7}", "reason": "client EIN"},
    {"regex": "Order #\\d{13,16}", "reason": "order IDs that look like CC numbers"}
  ],
  "values": [
    "555-12-3456"
  ],
  "recipients": [
    "you@example.com",
    "accountant@firm.com"
  ]
}
```

### Pattern types
| Field | Behavior |
|-------|----------|
| `patterns[].regex` | Regex applied to matched text. If it matches, detection is suppressed. |
| `values[]` | Exact string match against detected text. |
| `recipients[]` | Gmail `to` field exact match. Entire email body scan is skipped for listed recipients. |

## Detection Types + Confidence Model

| Type | Regex trigger | Confidence | Notes |
|------|---------------|-----------|-------|
| SSN | `\d{3}-?\d{2}-?\d{4}` | 0.6 base | Boosts to 0.95 if 5-token window contains "SSN", "social", "Tax ID" etc. |
| CC | 13-19 digit sequence | 0.95 | Requires Luhn checksum pass. Luhn fail → 0.3 (likely order ID, passes through). |
| PRIVATE_KEY | `-----BEGIN ` marker | 1.0 | Always blocks in enforce mode. No exceptions. |
| AWS_KEY | `AKIA[0-9A-Z]{16}` | 0.95 | AWS IAM key format. |
| IBAN | Country prefix + mod-97 checksum | 0.95 | Invalid checksum → not reported. |
| API_KEY | 40+ char base64-ish string | 0.7 | Medium confidence — may FP on long tokens. |
| PHONE | US phone format | 0.5 | Low — too common in signatures. Always passes through in v1. |

### Action model (enforce mode)
| Confidence + Type | Action |
|-------------------|--------|
| >= 0.9 + sensitive type (CC, PRIVATE_KEY, AWS_KEY) | BLOCK |
| >= 0.6 (any type) | BLOCK |
| < 0.6 | LOG only, pass through |

Note: PRIVATE_KEY at conf=1.0 always blocks. PHONE at conf=0.5 always passes through.

## Reading pii-detections.jsonl

```bash
# All detections this session
cat session/pii-detections.jsonl | python -m json.tool

# Count by type
cat session/pii-detections.jsonl | python -c "
import sys, json
from collections import Counter
lines = [json.loads(l) for l in sys.stdin if l.strip()]
c = Counter(l['type'] for l in lines)
print(dict(c))
"

# Show only blocked entries
cat session/pii-detections.jsonl | python -c "
import sys, json
for line in sys.stdin:
    e = json.loads(line.strip())
    if e.get('action') == 'blocked':
        print(json.dumps(e, indent=2))
"
```

### Log schema
```json
{
  "ts": "2026-05-04T00:00:00+00:00",
  "session_id": "...",
  "tool": "mcp__email-primary__send_mail",
  "target": "client@example.com",
  "type": "SSN",
  "confidence": 0.95,
  "action": "blocked|logged",
  "content_hash": "sha256:abcd1234...",
  "match_span": [247, 258],
  "redaction_token": "[REDACTED-SSN]",
  "mode": "log_only|enforce"
}
```

## Files

| File | Purpose |
|------|---------|
| `hooks/pii-pre-send.py` | PreToolUse hook — Gmail + Telegram |
| `hooks/pii-pre-write.py` | PreToolUse hook — Write/Edit on memory paths |
| `lib/pii_detector.py` | Shared detection engine (Presidio-compatible interface) |
| `session/pii-mode.json` | Mode flag (log_only / enforce) |
| `session/pii-allowlist.json` | Allowlisted patterns, values, recipients |
| `session/pii-detections.jsonl` | Detection log (append-only) |

## Upgrading to Presidio (Sprint 1.5)

The `lib/pii_detector.py` exposes:
```python
detect(text: str, context: dict = None) -> list[Detection]
```
Presidio drops in behind this same interface. Both hooks import `pii_detector.detect()` — upgrading the library upgrades both hooks automatically. No hook changes required in Sprint 1.5.

## Disabling

To disable without deleting:
1. Edit `session/pii-mode.json` → `"mode": "log_only"` (already the default — nothing to do)
2. To fully disable, remove the two PreToolUse entries from `settings.json`:
   - Matcher: `mcp__email-primary__send_mail|mcp__claude_ai_Gmail__create_draft|mcp__plugin_telegram_telegram__reply`
   - Matcher: `Write|Edit`

To re-enable: add them back (see settings.json registration section).

## Quick Triggers (CLAUDE.md)

| Trigger | Action |
|---------|--------|
| "pii status" | Load this file — show mode, recent detection count |
| "pii detections" | Load this file — tail `session/pii-detections.jsonl` |
| "pii mode" | Load this file — show current mode flag, explain how to flip |
