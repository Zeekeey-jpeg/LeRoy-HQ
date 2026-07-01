---
name: morning-brief
description: |
  Generate a single consolidated morning briefing on the "morning" / "good morning" trigger.
  Pulls background-agent findings, pending actions, calendar/day context, and system health
  into one scannable digest — no ceremony, one message.
triggers:
  - "morning"
  - "good morning"
  - "morning briefing"
  - "morning brief"
---

# Morning Brief

The morning brief is a **single consolidated digest** produced on the "morning" trigger. It
is a read-and-report routine: it never sends anything or mutates state on its own. Think of
it as the front page of the day — the few things worth knowing, assembled from what the
system already tracked overnight, in one scannable message.

## Design principles

1. **One message.** Don't stream multiple blocks. Assemble everything, then post once.
2. **Lead with what changed / what needs a decision.** Status that is "all green" gets one line.
3. **Pull, don't recompute.** Read the artifacts background agents already wrote (secretary
   timeline, scout patterns, planner todos, health checks) rather than re-deriving them.
4. **Degrade gracefully.** Any section whose source is missing is silently omitted — a
   missing calendar connector must never break the brief.
5. **No filler.** No "Good morning! Here's your briefing." Just the briefing.

## Sections (include only those with content)

| Section | Source | Show when |
|---------|--------|-----------|
| Day context | system date/time, calendar connector (if configured) | always (1–2 lines) |
| Needs you today | pending-actions / todo store, flagged replies | any pending items |
| Since yesterday | secretary timeline output, session recap | activity in last ~24h |
| Patterns / suggestions | scout / growth output | any surfaced patterns |
| System health | health-check artifact, MCP/connector status, backup status | anything degraded |
| Scheduled jobs | cron / automation registry | any run overnight or due today |

## Assembly flow

```
1. Read background artifacts under ~/.claude/session/ (secretary, scout, planner, health).
2. Read the pending-actions / todo store.
3. If a calendar connector is configured, fetch today's events; else skip.
4. Check backup status (git ahead/behind) — surface only if action is useful.
5. Compose ONE digest. Omit empty sections. Lead with "Needs you today".
6. Post. Do not auto-execute any surfaced action; each is a suggestion the user can trigger.
```

## Weekly hooks (optional)

Fold recurring weekly checks into the brief by weekday rather than as separate triggers:

- **Backup status** (e.g. Mon/Wed/Fri): show version + ahead/behind; never auto-push
  (see `skills/routines/backup-reminder.md`).
- **Cleanup pass** (e.g. Monday): spawn the janitor in the background; surface results only
  if the cleanup score crosses a threshold.

## What the brief must NOT do

- Send email / messages, post anywhere, or commit — read-and-report only.
- Recompute expensive things the background agents already produced.
- Block on a missing connector, empty section, or offline sidecar.

## Customization

The section list above is a starting point. Add domain sections (your inbox summary, your
pipeline, your build status) by wiring their source artifact into step 1 and adding a row to
the table — keep the "omit when empty" and "no auto-action" rules for every section you add.
