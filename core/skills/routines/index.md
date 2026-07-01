# Routine Skills

Quick-trigger routines that bypass project detection for immediate execution of common daily tasks.

**NEW in v3.0:** All quick triggers spawn @quick for 100% agent coverage.

## Keyword Routing
| Keywords | File | Agent |
|----------|------|-------|
| morning, daily briefing, calendar, weather, start day | morning.md | @quick |
| hs report, crm report, sales report, Q1-Q4, monthly report | crm-report.md | @quick |
| bim-tool mcp, mcp bim-tool, connect bim-tool, start bim-tool, your BIM tool control | bim-connect.md | @quick |
| weekly report, token burn report, efficiency report, wow trends | token-burn-report.md | @quick |
| scheduled, recurring, every monday, weekly, monthly, workflow schedule | scheduled-workflows.md | @quick |
| backup, push backup, github backup, doomsday backup | backup-reminder.md | @quick |
| product backup, backup product, push product, product mirror | product-backup.md | @quick |
| browser, playwright, chrome, web automation | → `integrations/playwright/` | @quick → @conductor |
| heartbeat, check in, status check, proactive | heartbeat.md | @quick |
| register payment, record payment, payment received, log payment | register-payment.md | @quick |
| done, start over, clear session, reset chat, new conversation | session-reset.md | @quick |
| friday bundle, weekly bundle, accountant bundle, leroy export | friday-bundle.md | @quick |
| revenue email, CEO report, vault growth, daily revenue | revenue-email-quick-reference.md | @quick |
| token efficiency, weekly efficiency, monday token report | token-efficiency-report.md | @quick |
| registry orchestrator, schedule registry, workflow registry | registry-orchestrator.md | @quick |
| routine builder, create routine, new routine, build routine | routine-builder.md | @quick |
| routine cleanup, clean routines, prune routines | routine-cleanup.md | @quick |
| routine dashboard, routine status, all routines, show routines | routine-dashboard.md | @quick |

## Available Skills
- **morning.md** - Daily briefing routine: 3-day calendar (your organization/your org), email summary, weather, scheduled workflows
- **crm-report.md** - your organization sales performance reports with Q1-Q4, monthly, and date range support
- **bim-connect.md** - your BIM connector MCP connection routine for your BIM tool project control
- **token-burn-report.md** - Weekly efficiency report with WoW trends, YTD analysis, and 52-week projections
- **scheduled-workflows.md** - Framework for recurring workflows with calendar integration
- **backup-reminder.md** - Git backup reminder (Mon/Wed/Fri): .claude->LeRoy, memory->memory
- **product-backup.md** - your product mirror backup: Desktop/Projects/EXAMPLECLIENT/your product->ExampleClient_Product
- **heartbeat.md** - Proactive check-in to surface urgent items
- **register-payment.md** - Register payment with 25% tax withholding and YTD tracking
- **session-reset.md** - Session reset: save memory, clear history, reset context
- **friday-bundle.md** - LEROY weekly export bundle with Excel and summary
- **revenue-email-quick-reference.md** - CEO daily revenue report showing vault growth
- **token-efficiency-report.md** - Weekly token efficiency report (Monday 8am auto-trigger)
- **registry-orchestrator.md** - Registry management for scheduled/recurring workflows
- **routine-builder.md** - Create new routine skills
- **routine-cleanup.md** - Cleanup stale or unused routines
- **routine-dashboard.md** - Dashboard view of all active routines

## Data Files
- **schedule-registry.json** - Registry of all scheduled/recurring workflows with next run dates

<!-- linked by alignment fix 2026-05-30 -->
## Additional Skills (linked 2026-05-30)
- [cost-digest-weekly.md](cost-digest-weekly.md) — Sunday 18:00 ET weekly cost digest
- [leroy-improve.md](leroy-improve.md) — Leroy Improve system-health audit
- [exampleclient-session-open.md](exampleclient-session-open.md) — ExampleClient session open: auto-PDF + recap
- [new-computer-setup.md](new-computer-setup.md) — New computer recovery/setup
