---
name: cost-tracker
description: Read the cost log, invoke the aggregator, produce weekly spend summary
created: 2026-05-03
modified: 2026-05-03
tags: [cost, tracking, observability]
trigger: "cost report" | "cost" | "tokens this week"
---

# Cost Tracker

Surfaces token spend by agent, skill, and tool from `session/cost-log.jsonl`.

## Quick Invocation

```bash
python ~/.claude/scripts/cost-aggregator.py
```

Output goes to stdout (Telegram-shaped) and also writes:
- `session/cost-weekly-{YYYY-WW}.md` — full breakdown
- `session/cost-history.jsonl` — one appended line per run (week-over-week diff)

## Schema Reference

Each record in `session/cost-log.jsonl`:

| Field | Type | Notes |
|-------|------|-------|
| `ts` | ISO-8601 string | UTC timestamp of tool call |
| `session_id` | string \| null | From state.json or env |
| `trace_id` | string \| null | prompt_id if available |
| `agent` | string \| null | `state.json["current_agent"]` |
| `skill` | string \| null | `state.json["current_skill"]` |
| `tool` | string | Tool name (Read, Write, Bash, etc.) |
| `model` | string | e.g. `claude-sonnet-4-6` |
| `tokens_in` | int | Input token count |
| `tokens_out` | int | Output token count |
| `cache_w` | int | Cache write tokens |
| `cache_r` | int | Cache read tokens |
| `cost_usd` | float | Computed cost in USD |
| `source` | "api"\|"estimated"\|"fallback" | How tokens were measured |
| `confidence` | 0.0–1.0 | 1.0=API, 0.6=estimated, 0.0=fallback |

## Source Hierarchy

1. **api** (confidence 1.0) — `metadata.usage.input_tokens` populated by harness
2. **estimated** (confidence 0.6) — length of serialized tool input/output ÷ 4 bytes/token
3. **fallback** (confidence 0.0) — all zero; metadata unavailable

Confidence banner fires when <70% of total cost is `source="api"`:
`⚠️ NUMBERS PARTIAL — X% measured, Y% estimated`

## Pricing Config

`session/pricing.json` — rates per million tokens:

| Model | In | Out | Cache Write | Cache Read |
|-------|----|-----|-------------|------------|
| claude-opus-4-7 | $5.00 | $25.00 | $6.25 | $0.50 |
| claude-sonnet-4-6 | $3.00 | $15.00 | $3.75 | $0.30 |
| claude-haiku-4-5 | $1.00 | $5.00 | $1.25 | $0.10 |

## Hooks

Both hooks fire on every PostToolUse call (matcher `.*`):

| Hook | File | Purpose |
|------|------|---------|
| Probe | `hooks/cost-meter-probe.py` | Diagnostic — dumps sanitized payload shape to `session/cost-meter-probe.jsonl`. Disable after ~1 day by removing from `settings.json`. |
| Meter | `hooks/cost-meter.py` | Production — writes cost record to `session/cost-log.jsonl`. Keep permanently. |

## Disabling

To disable the probe (after ~1 day of data collection):
1. Open `~/.claude/settings.json`
2. Remove the `cost-meter-probe.py` entry from the `PostToolUse` hook chain
3. Leave `cost-meter.py` in place permanently

To disable the meter entirely (emergency only):
- Remove both hooks from `settings.json` PostToolUse chain
- Existing log data is preserved in `session/cost-log.jsonl`

## Gate Footer Integration

Sprint 0 Day 5 work (W0.6) will hook `gate-enforcer.py` to read `cost-log.jsonl`
and prepend live attribution to the gate footer. This skill is the data source.

## Sunday Digest

Sprint 0 Day 6 work (W0.7) will set up a cron that pipes `cost-aggregator.py`
stdout to the Telegram bot on Sunday evenings.
