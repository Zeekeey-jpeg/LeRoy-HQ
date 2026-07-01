---
name: harness-radar
description: Bi-weekly competitive radar — scrape the agent-harness field, diff vs Leroy's capability manifest, and report new features Leroy lacks as a To-Do + email. Keeps the user ahead of the space.
triggers: ["harness radar", "competitive radar", "scan the field", "what's new in agent frameworks", "run harness radar"]
owner: HR/Scout
schedule: every 14 days (off-peak) via cron/register-harness-radar.ps1
---

# Harness Radar — keep Leroy ahead of the field

**Purpose:** the user didn't know Leroy's top upgrades (Kanban triage, etc.) already existed in the field.
This radar runs autonomously every 2 weeks, finds what's NEW that Leroy lacks, and surfaces it as a
To-Do + an email so he keeps up with the space.

## Inputs
- **Capability manifest (ground-truth):** `~/.claude/memory/Projects/leroy-pwa-app/backend/leroy_core/capabilities/capabilities.yaml`
  — read it first. It lists what Leroy HAS (`capabilities`), what's already planned (`known_gaps` — DO
  NOT re-report these), and the `watch_list` of frameworks to scan.
- **Run history:** `~/.claude/memory/Projects/leroy-pwa-app/backend/leroy_core/radar/runs/` — read the
  most recent prior run so you don't repeat last cycle's findings.

## Procedure
1. **Load** `capabilities.yaml`. Build the set of: present/partial capabilities, `known_gaps`, and the
   `watch_list`.
2. **Scan** each watch_list framework with WebSearch + WebFetch — target their CHANGELOG / releases / docs
   "what's new" from the **last ~14 days** (and anything notable since the last run). Focus on
   *capabilities/architecture*, not version-number noise.
3. **Diff:** a finding qualifies ONLY if it is a real capability that is (a) ABSENT or PARTIAL in
   `capabilities`, AND (b) NOT already in `known_gaps`, AND (c) not reported in the previous run. Be
   strict — no re-reporting, no vague "they shipped a release."
4. **Score** each finding: `value_to_leroy` (high/med/low), `effort` (S/M/L), `portable?` (does it fit our
   markdown-brain + claude-max + FastAPI/PWA architecture — remember: NO API/SDK-metered paths).
5. **Write the artifact FIRST (cap-safe):** save `runs/radar-YYYY-MM-DD.md` with the full findings table
   BEFORE any network email — so a usage-cap mid-run never loses the work.
6. **Emit a To-Do:** append the single highest-value finding to
   `~/.claude/memory/Projects/Personal/smart-todos.md` in the standard row format
   (`| T-{HHMMSS} | Radar: <finding> | your org | P2 | medium | - | {date} | open | |`) so it shows in the
   Leroy inbox.
7. **Email the user** (you@example.com via email-primary send_mail): subject `Harness Radar — N new
   things Leroy could adopt (YYYY-MM-DD)`, body = the findings table + your top recommendation. Keep it
   skimmable. **The body is HTML, so you MUST pass `isHtml: true` to send_mail** — otherwise Gmail
   escapes the markup and the recipient sees raw `<div>…` source instead of a rendered table. Never send
   an HTML body without that flag.
8. **Update the manifest if warranted:** if a finding reveals a capability we actually already have, fix
   its status in `capabilities.yaml` (keep ground-truth honest).

## Output contract
- One artifact file in `runs/`, one To-Do row, one email. If ZERO qualifying findings: still write the
  artifact ("no new gaps this cycle") and send a 1-line email; do NOT spam a todo.

## Guardrails
- Cap-safe: disk artifact before email/todo.
- No re-reporting `known_gaps` or prior-run findings.
- Respect billing law: never recommend a path that requires moving off Claude Max to API/metered.
- Single pass; off-peak.
