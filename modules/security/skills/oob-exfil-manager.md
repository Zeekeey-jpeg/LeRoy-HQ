---
name: oob-exfil-manager
description: "Out-of-Band Exfiltration Manager — webhook.site token lifecycle, signal interpretation, and admin-bot feedback loop compression for CTF XSS chains. Load when: admin bot XSS challenge, OOB callback needed, exfil payload dispatched, webhook.site signal received. Owner: cyber-operator."
version: 1.0
created: 2026-02-24
owner: cyber-operator
---

# OOB Exfil Manager

Coordinates webhook.site token lifecycle and interprets incoming OOB signals during CTF XSS operations. Compresses the 90-120 second admin bot feedback window into near-instant analysis by pre-staging interpretation logic before the bot fires.

---

## Token Registry Format

Maintain this structure in active session memory throughout the challenge:

```json
{
  "active_tokens": [
    {
      "token_id": "<webhook.site token UUID>",
      "challenge": "<challenge name or URL>",
      "payload_iteration": 1,
      "payload_sent": "<exact payload string>",
      "sink_type": "JS|attr|innerHTML|URL|CSS|JSON",
      "dispatched_at": "<ISO timestamp>",
      "status": "pending|fired|failed|timeout"
    }
  ]
}
```

---

## Session State Commands

| Command | Action |
|---------|--------|
| `new token [challenge] [sink]` | Register new token entry in registry |
| `fired [token_id]` | Process and interpret a received signal |
| `status` | Dump full registry with current statuses |
| `next` | Recommend next payload iteration based on results so far |
| `reset [challenge]` | Clear all tokens for a specific challenge |

---

## Pre-Dispatch Setup (Do This Before Sending Payload)

1. Register a new webhook.site token for this payload variant
2. Log in registry: token_id, payload_sent, sink_type, dispatched_at, status=pending
3. Stage the interpretation template (below) so analysis is instant on signal receipt
4. Note dispatch time — this anchors the delta calculation

**Token assignment rule:** One unique token per payload variant, not per challenge. This enables precise attribution when multiple variants are in flight.

---

## Signal Interpretation Protocol

When a webhook fires, analyze in this order:

### 1. Request Method
- `GET` → JavaScript executed inline (reflected XSS or DOM XSS likely)
- `POST` → Explicit fetch with body (stored XSS or user-initiated flow)

### 2. User-Agent Header
- Chrome/Chromium bot string → admin bot confirmed
- Your own browser UA → self-trigger (reflected, not persisted)

### 3. Referer Header
- Matches challenge URL → confirms page context where XSS fired
- Missing → cross-origin fetch (expected in cookie exfil scenarios)

### 4. Query Parameters

| Param | Maps To |
|-------|--------|
| `?c=` | `document.cookie` |
| `?d=` | DOM dump (base64 decoded) |
| `?l=` | localStorage (base64 decoded) |
| `?t=` | Token / auth cookie |
| `?a=` | Admin page source (base64 decoded) |
| `?f=` | Flag element content (base64 decoded) |

### 5. Timing Delta

| Delta | Verdict |
|-------|--------|
| < 10s | Self-trigger — XSS reflects but not persisted or stored |
| 10-60s | Ambiguous — possible background job or fast bot |
| 90-130s | Admin bot confirmed — XSS stored and executed by bot |
| > 150s | Timeout — admin bot did not execute payload |

---

## Output Format (Per Fired Signal)

```json
{
  "token_id": "<token>",
  "fired_at": "<ISO timestamp>",
  "delta_seconds": 0,
  "trigger_type": "self|admin_bot|unknown",
  "data_exfiltrated": {
    "cookies": "<value or null>",
    "dom_fragment": "<base64-decoded value or null>",
    "localStorage": "<base64-decoded value or null>",
    "admin_page": "<base64-decoded value or null>",
    "flag_text": "<base64-decoded value or null>",
    "custom": "<any other captured data>"
  },
  "verdict": "XSS_CONFIRMED|SELF_TRIGGER|NO_FIRE|PARTIAL|TIMEOUT",
  "next_action": "<specific recommendation>"
}
```

### Verdict Definitions

| Verdict | Meaning | Next Action |
|---------|---------|-------------|
| `XSS_CONFIRMED` | Admin bot fired, data captured | Extract flag, submit, post-flag protocol |
| `SELF_TRIGGER` | Reflected XSS only — not stored | Switch to stored/DOM vector, check ctf-payload-bank |
| `PARTIAL` | Webhook fired but no useful data | Adjust exfil payload — try different param name or encoding |
| `NO_FIRE` | Signal received but uninterpretable | Check token_id match, check payload dispatch confirmation |
| `TIMEOUT` | No signal after 150s | Mark failed, escalate to fallback_1 payload |

---

## Feedback Loop Acceleration

The 90-120s admin bot cycle is not idle time — it is reconnaissance time. While waiting:

1. **Pre-stage interpretation template** before payload dispatch so analysis is instant
2. **Cross-reference immediately** when signal arrives — no manual lookup delay
3. **Auto-classify delta** as soon as timestamp is available
4. **Recommend next action inline** with every interpretation output

This eliminates analysis overhead. Signal arrives → verdict in under 10 seconds.

---

## Multi-Token Strategy

- Assign unique tokens per payload variant (not per challenge)
- When running parallel payload variants, stagger dispatch by 5-10s to avoid signal collision
- Rotate tokens after 10 uses or on any 403/rate-limit from webhook.site
- For parallel testing: token-A = primary payload, token-B = fallback_1, token-C = encoding variant

---

## Auto-Escalation on Timeout

If no signal after 150s and status remains `pending`:
1. Mark token status as `timeout`
2. Auto-recommend fallback_1 payload from ctf-payload-bank session output
3. Stage new token for fallback dispatch
4. Log: `[OOB] Token <id> timed out after 150s. Escalating to fallback_1.`

---

## Integration Points

- **ctf-payload-bank:** Always replace `WEBHOOK` placeholder with active token_id from registry before dispatching exfil payloads
- **browser-session-guardian:** Webhook signal dispatch occurs through the browser — confirm `browser_ready: true` before dispatching payload that triggers OOB
- **cyber-operator parallel enum:** During the 90-120s wait window after dispatch, pivot to parallel enumeration protocol — never sit idle

---

*oob-exfil-manager v1.0 | CTF XSS OOB coordination | Authorized platforms only | 2026-02-24*
