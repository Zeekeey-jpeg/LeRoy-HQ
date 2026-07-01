---
context: fork
---

# Morning Briefing Skill

## Trigger
This skill activates when user says: **"Morning"**, **"Good morning"**, or **"morning briefing"** (all case-insensitive)

---

## Purpose
Provide a system-focused morning briefing with date, weather, calendar/email status, scheduled workflows, daily cleanup scan, and Monday compliance reminders.

---

## STEP 0: MEMORY RECALL (v2.0 AUTO - ALREADY DONE)

**v2.0 UPDATE:** Memory recall happens automatically on session start via hook.

**By the time you see this:**
- Hook already detected session start (30+ min gap)
- Top 5 relevant notes already loaded
- Last recall timestamp already updated
- No manual action needed

**Loaded automatically:**
- Yesterday's incomplete tasks
- Project-specific learnings
- Recurring patterns (e.g., "Friday reports")
- Recent decisions and preferences

**Check loaded context:**
If [MEMORY] block appeared above, memory was recalled. Otherwise, first session of the day.

**Output (already displayed by hook):**
```
[MEMORY] Loaded 5 relevant notes (187ms):
1. **{title}** ({type}, {date}) - {summary}
...
```

**If no relevant memories:** Silent (no output)

---

## STEP 0.5: CRON REGISTRATION (Dedup-Safe — Every Morning)

Register recurring routines via `CronCreate` so they fire autonomously. Dedup check prevents double-registration on session restart.

**Active-crons registry:** `session/active-crons.json` — read before any `CronCreate` call.

```python
from pathlib import Path
import json

active_crons_path = Path("~/.claude/session/active-crons.json")

# Load existing registrations
try:
    active_crons = json.loads(active_crons_path.read_text())
except Exception:
    active_crons = {}

# Cron definitions — key = dedup ID, value = (schedule, prompt)
CRON_DEFINITIONS = {
    "morning-briefing":  ("57 8 * * 1-5",  "/morning"),
    # monday-cleanup REMOVED 2026-05-30 — superseded by the daily janitor scan below
    #   (see "DAILY CLEANUP" section, ~line 1483) which runs every morning and already
    #   covers Monday-only items. The standalone 9am cron never reliably fired (session-
    #   dependent) and only existed as audit-flagged metadata. Do NOT re-add.
    # EOD review handled separately in CLAUDE.md Position #0 (eod-review-heartbeat.txt)
}

for cron_id, (schedule, prompt) in CRON_DEFINITIONS.items():
    if cron_id not in active_crons:
        # Register via CronCreate
        # CronCreate(schedule=schedule, prompt=prompt, recurring=True)
        active_crons[cron_id] = {
            "schedule": schedule,
            "prompt": prompt,
            "registered_at": datetime.now().isoformat()
        }

# Persist registry
active_crons_path.parent.mkdir(parents=True, exist_ok=True)
active_crons_path.write_text(json.dumps(active_crons, indent=2))
```

**Important:**
- Only register when `cron_id NOT in active_crons` — never double-register on repeated morning calls
- EOD review (`2 16 * * 1-5`) is managed by CLAUDE.md Position #0 (eod-review-heartbeat.txt) — do NOT add it here
- If `CronCreate` returns an error (e.g., cron already exists in engine), log and continue — don't fail briefing

---

## STEP 1: GET SYSTEM DATE

**ALWAYS get the current date from the local system.** Do NOT calculate or assume the day of week.

```bash
powershell -Command "Get-Date -Format 'dddd, MMMM d, yyyy'"
```

**Example output:** `Monday, January 5, 2026`

Use this output directly in the briefing header.

---

## STEP 1.5: CRM SYNC (Phase 3 - Background)

> **LEROY Phase 3:** Run your CRM sync as part of morning routine.

**UPDATED APPROACH:** your CRM sync loads via skill trigger, NOT inline here.

**Implementation:**

```python
# your CRM sync is now handled separately:
# 1. If user says "sync crm" or "crm sync" -> Load skill
# 2. Morning briefing only checks last sync status from state.json

# Read last sync status
with open('~/.claude\\session\\state.json', 'r') as f:
    state = json.load(f)

last_crm_tool = state.get('last_crm_tool', {})
sync_summary = {
    'last_run': last_crm_tool.get('timestamp', 'Never'),
    'deals_total': last_crm_tool.get('deals_total', 0),
    'status': last_crm_tool.get('status', 'Not run'),
    'show_reminder': True  # ALWAYS show status on morning trigger - no time checks
}

# If >24h since last sync, include reminder in output
```

**Note:** Sync is manual trigger to avoid blocking morning briefing. Use "sync crm" command when needed.

---

## STEP 2: GATHER DATA (Single Phase Collection)

**CRITICAL:** Execute ALL of these in parallel (single message, multiple tool calls). Do NOT use placeholders - actually call the MCP tools.

**Implementation:**

```python
# Calculate timestamps for calendar queries
from datetime import datetime, timedelta

today = datetime.now()
today_start = today.replace(hour=0, minute=0, second=0, microsecond=0)
today_end = today.replace(hour=23, minute=59, second=59, microsecond=999999)

# Week range (Monday to Sunday)
week_start = today - timedelta(days=today.weekday())
week_end = week_start + timedelta(days=6)

today_start_iso = today_start.strftime('%Y-%m-%dT%H:%M:%SZ')
today_end_iso = today_end.strftime('%Y-%m-%dT%H:%M:%SZ')
week_start_iso = week_start.strftime('%Y-%m-%dT%H:%M:%SZ')
week_end_iso = week_end.strftime('%Y-%m-%dT%H:%M:%SZ')
```

**Execute in parallel (single response, multiple tools):**

1. System date: `Bash(command="powershell -Command \"Get-Date -Format 'dddd, MMMM d, yyyy'\"", description="Get current date")`
2. Weather: `WebFetch(url="https://wttr.in/?format=j1", prompt="Extract: today condition/high/low, tomorrow condition/high/low")`
3. Calendar today: `ToolSearch(query="select:mcp__email-primary__list_events")` then call with timeMin=today_start_iso, timeMax=today_end_iso
4. Calendar week: `ToolSearch(query="select:mcp__email-primary__list_events")` then call with timeMin=week_start_iso, timeMax=week_end_iso
5. Gmail unread: `ToolSearch(query="select:mcp__email-primary__search_mail")` then call with query="is:unread", maxResults=100
6. your CRM deals: `ToolSearch(query="select:mcp__crm__list_deals")` then call with limit=100

**Error Handling:**

```python
# For each data source:
try:
    result = execute_tool()
except Exception as e:
    # Log error but continue
    error_log[source_name] = str(e)
    result = None

# Continue processing other data sources even if one fails
```

**Post-Collection Processing:**

```python
# After parallel collection, process results:
data_collected = {
    'system_date': bash_result or "Date unavailable",
    'weather': weather_result or "Weather unavailable",
    'calendar_today': calendar_today_result or [],
    'calendar_week': calendar_week_result or [],
    'gmail_unread': gmail_result.get('resultSizeEstimate', 'Unknown') if gmail_result else 'Unavailable',
    'crm_tool': crm_tool or []
}

# Store any errors for display in output
data_errors = {k: v for k, v in error_log.items() if v}
```

---

## STEP 2.5: CALENDAR SUMMARY (Phase 4 - LEROY Integration)

> **LEROY Phase 4:** Run calendar summary and reminder scan as part of morning routine.

**SIMPLIFIED APPROACH:** Process calendar data already fetched in Step 2.

**Implementation:**

```python
# Use calendar data from Step 2 (already fetched)
calendar_today = data_collected['calendar_today']  # From Step 2
calendar_week = data_collected['calendar_week']    # From Step 2

# Process events for display
today_events_list = []
if calendar_today and 'items' in calendar_today:
    for event in calendar_today['items']:
        today_events_list.append({
            'time': event.get('start', {}).get('dateTime', 'All day'),
            'title': event.get('summary', 'Untitled'),
            'attendees': event.get('attendees', [])
        })

# Count week statistics
week_stats = {
    'total_events': len(calendar_week.get('items', [])) if calendar_week else 0,
    'meetings': 0,
    'reminders': 0,
    'deadlines': 0
}

if calendar_week and 'items' in calendar_week:
    for event in calendar_week['items']:
        attendee_count = len(event.get('attendees', []))
        if attendee_count > 1:
            week_stats['meetings'] += 1
        elif 'reminder' in event.get('summary', '').lower():
            week_stats['reminders'] += 1
        elif 'due' in event.get('summary', '').lower() or 'deadline' in event.get('summary', '').lower():
            week_stats['deadlines'] += 1

# Store processed calendar data
calendar_data = {
    'today_events': today_events_list,
    'week_stats': week_stats,
    'missing_invites': [],  # Feature not yet implemented
    'reminders_created': 0,  # Feature not yet implemented
    'overdue_alerts': []     # Feature not yet implemented
}
```

**Error Handling:** If calendar API failed in Step 2, calendar_data will show empty lists/zeros.

---

## STEP 1.6: EMAIL INTELLIGENCE SCAN (Secretary Memory Enhancement)

> **Purpose:** Scan last 24 hours of emails and update conversation tracking.
> **Duration:** <30 seconds
> **Skill:** `skills/integrations/email-intelligence.md`

**UPDATED APPROACH:** Email intelligence is now a separate manual trigger ("scan emails").

**Implementation:**

```python
# Check if email intelligence scan has been run recently
with open('~/.claude\\session\\state.json', 'r') as f:
    state = json.load(f)

last_email_scan = state.get('last_email_scan', {})
email_intel_data = {
    'last_run': last_email_scan.get('timestamp', 'Never'),
    'emails_processed': last_email_scan.get('emails_processed', 0),
    'clients_updated': last_email_scan.get('clients_updated', 0),
    'status': last_email_scan.get('status', 'Not run'),
    'show_reminder': True  # ALWAYS show status on morning trigger - no time checks
}

# If >24h since last scan, show reminder in output
```

**Note:** Email intelligence is a separate trigger to avoid blocking. Use "scan emails" command for daily scan.

---

## STEP 2.6: TAX STATUS CHECK (Phase 5 - Quarterly Only)

> **LEROY Phase 5:** Check quarterly tax deadline proximity and include status in briefing.

**SIMPLIFIED APPROACH:** Check state.json for tax deadline alerts set by tax intelligence system.

**Implementation:**

```python
# Read tax status from state.json
with open('~/.claude\\session\\state.json', 'r') as f:
    state = json.load(f)

tax_status = state.get('tax_status', {})
tax_data = {
    'include_in_briefing': tax_status.get('alert_active', False),
    'quarter': tax_status.get('quarter', 'Q1'),
    'deadline': tax_status.get('deadline', ''),
    'days_until': tax_status.get('days_until', 0),
    'amount_due': tax_status.get('amount_due', 0)
}

# Only show if alert is active (within 30 days of deadline)
```

**Note:** Tax deadlines are set manually in state.json or via "tax status" command. This just displays existing alerts.

---

## STEP 2.7: YEAR-OVER-YEAR SUMMARY (Phase 5 - Mondays Only)

> **LEROY Phase 5:** Generate YoY comparison summary on Monday mornings.

**SIMPLIFIED APPROACH:** YoY analysis is now a separate manual trigger.

**Implementation:**

```python
# YoY analysis is manual trigger to avoid blocking briefing
# On Mondays, show reminder instead of auto-running

if "Monday" in system_date:
    yoy_data = {
        'include_in_briefing': True,
        'show_reminder': True  # Show reminder to run "YoY" command
    }
else:
    yoy_data = {'include_in_briefing': False}
```

**Output (Mondays only):**

```
================================================================
YOY SNAPSHOT (Reminder)
================================================================

Monday YoY analysis available.

Say "YoY" to generate full year-over-year comparison.
```

---

## STEP 2.8: CYBER GROWTH ENGINE (M/W/F — Day-Dependent)

> **Whitehating v2.0:** Growth sweep runs Monday background. W/F shows delta since Monday.
> Surfaces in your org office updates automatically — the user never has to ask.

```python
# Determine day
if "Monday" in system_date:
    # MONDAY: Spawn growth sweep in background (if not already running)
    # Check overlap lock first
    lock_path = "~/.claude\\session\\growth-sweep-lock.json"

    if os.path.exists(lock_path):
        with open(lock_path) as f:
            lock = json.load(f)
        # If lock older than 4 hours, consider stale and clear
        if (datetime.now() - datetime.fromisoformat(lock['started_at'])).total_seconds() > 14400:
            os.remove(lock_path)
            run_sweep = True
        else:
            run_sweep = False  # Already running — skip
    else:
        run_sweep = True

    if run_sweep:
        # Write lock file
        with open(lock_path, 'w') as f:
            json.dump({'started_at': datetime.now().isoformat(), 'trigger': 'monday_morning'}, f)
        # Spawn background: load growth-engine.md → Trigger B (weekly sweep)
        # Lock file cleared by growth engine when sweep completes
        growth_status = "SPAWNED (background)"
    else:
        growth_status = "ALREADY RUNNING (skipped to avoid overlap)"

elif "Wednesday" in system_date or "Friday" in system_date:
    # W/F: Read growth-log.md and show delta since Monday
    growth_log_path = "~/.claude\\memory\\Projects\\Cyber\\growth-log.md"
    # Read last entry from growth-log.md and extract this week's additions
    growth_status = "READ_LOG"  # Signal to output formatter: read and include
else:
    growth_status = "SKIP"  # Tue/Thu/Sat/Sun: silent
```

**Monday output:**
```
🔬 CYBER GROWTH SWEEP — Launched (background)
   Scanning: H1 Hacktivity, PortSwigger, CVE feed, YouTube
   Results will appear in Wednesday briefing.
```

**Wednesday / Friday output (if growth-log.md has entries this week):**
```
🔬 CYBER VAULT UPDATE
   [N] new techniques added this week
   [M] existing techniques updated
   [K] dead ends confirmed
   Vault size: [before] → [after] files
   [IF new discovery]: ⚡ NEW: [technique name] — $[payout range] [source]
```

**If no new entries since Monday:** Silent (don't show section at all).

---

## STEP 2.85: GITHUB TRENDING + WATCHLIST SCAN (Silent-Default LeRoy Radar)

> **Purpose:** Detect needle-moving open-source primitives that could enhance LeRoy
> (recall, voice, agents, MCP servers, eval, memory, graph). NOT a feature feed.
> **Council verdict (2026-04-30):** PROCEED WITH CONDITIONS — silent default, tiered surfacing, manual ingest only.
> **Calibration (2026-04-30):** the user flagged ≥7 as too tight. Two-tier surfacing now: FLAGGED at ≥6, WATCH at 4-5. Plus Monday best-of-week guarantee.
> **Watchlist file:** `session/leroy-radar-watchlist.json`
> **Output file:** `session/leroy-radar-output.md`
> **Kill switch:** If the user hasn't said "ingest repo X" or read the section in 30 days, disable in `session/leroy-radar-config.json`.

### Two-Source Feed

**Source A — github.com/trending Top 10** (daily): Fetch HTML, extract repo cards.
**Source B — Named watchlist** (10 maintainers): Read `session/leroy-radar-watchlist.json`, hit each repo's `/releases/latest` and `/commits/main` for new activity.

```python
# Fetch trending
trending = WebFetch(
    url="https://github.com/trending",
    prompt="Extract top 10 repos: full_name, description, language, stars_today, total_stars, primary_language. Return JSON array."
)

# Read watchlist
import json
watchlist = json.loads(Read("~/.claude\\session\\leroy-radar-watchlist.json"))

# For each watchlist entry, fetch latest release + last commit
watchlist_hits = []
for repo in watchlist["repos"]:
    rel = WebFetch(
        url=f"https://github.com/{repo['full_name']}/releases.atom",
        prompt="Return the most recent release date and tag name. JSON only."
    )
    if rel.get("date") > repo.get("last_seen_date"):
        watchlist_hits.append({**repo, **rel})

candidates = trending + watchlist_hits
```

### Hard Filter (Cuts ~70% of trending noise)

A candidate must pass ALL of these or it's dropped silently:

| Filter | Rule |
|--------|------|
| Language | In {Python, TypeScript, Rust, Go} OR {Shell, Markdown} when topic includes `skill`, `claude`, `agent-framework`, `prompt-library` (drop pure JS UI libs, Solidity, etc.) |
| README/topic match | Contains ≥1 of: `LLM`, `agent`, `MCP`, `RAG`, `memory`, `vector`, `voice`, `graph`, `embedding`, `eval`, `prompt`, `tool-use`, `skill`, `claude code` |
| License | MIT / Apache-2.0 / BSD (drop AGPL, custom commercial-restrict) |
| Activity | Last commit ≤30 days |
| Not duplicate | Repo not already in `memory/Projects/LeRoy/ingested-repos.md` |

### Score Gate (5 axes, 0-2 each, max 10)

Two tiers — daily briefing surfaces both, but at different visual weight:

| Tier | Score Range | Treatment |
|------|-------------|-----------|
| **FLAGGED** | ≥6 | Full block: table + per-repo detail + ingest prompt |
| **WATCH** | 4-5 | One-line mention only: `WATCH: owner/name (5/10) — {gap or reason}` |
| **DROP** | ≤3 | Silent — never surfaced |

Compute per candidate:

| Axis | 0 | 1 | 2 |
|------|---|---|---|
| **Gap-match** | No LeRoy gap addressed | Adjacent to a known gap | Directly fixes gap from `memory/Projects/LeRoy/known-gaps.md` |
| **Momentum** | <50 stars total or <5 stars/day | 50-1000 stars, 5-50/day | >1000 stars OR >50 stars/day OR named maintainer hit |
| **License** | Restrictive/unclear | Permissive but copyleft-adjacent | MIT / Apache-2.0 outright |
| **Integration cost** | Rewrite required | Wrapper or MCP shim | Drop-in lib or existing MCP |
| **Regression risk** | Touches recall/consolidation/voice core | Touches output formatter or smart-todos | Pure additive — new MCP tool, new skill |

**Known gaps file** (`memory/Projects/LeRoy/known-gaps.md`) — maintained list of what LeRoy currently can't do well. Examples today: consolidation decay metadata writing, voice tone-match across formality bands, edge-walk 2-hop traversal, multi-agent eval harness, Telegram mid-session interrupt injection. Update when new gaps surface.

### Monday Best-of-Week Guarantee

If a Monday briefing fires AND no repo scored ≥6 in the past 7 days, force-surface the highest-scoring candidate from the past 7 days (read `session/leroy-radar-log.jsonl`) regardless of score — even if it's a 4 or 5. Tag it `BEST OF WEEK (low confidence)`. Ensures the user never goes a full week with zero signal.

### Output

**If 0 candidates score ≥4 AND it's not a forced Monday:** Section omitted entirely. Briefing length unchanged.

**Output template (Tier 1 — FLAGGED, score ≥6):**

> **MANDATORY:** Every repo MUST include a clickable GitHub URL using markdown link syntax `[owner/name](https://github.com/owner/name)`. the user needs one-click access to view source himself. Bullet-point format only — no walls of text.

```
================================================================
LEROY RADAR — {N} FLAGGED  ·  {M} watching            Score ≥6/10
================================================================

| # | Repo | Score | Gap Addressed | Integration |
|---|------|-------|---------------|-------------|
| 1 | [owner/name](https://github.com/owner/name) | 8/10 | G-XXX | MCP shim (~0.5 day) |

[1] [owner/name](https://github.com/owner/name) — {one-line what it does}
  · Why LeRoy gains: {1 sentence — concrete capability}
  · Closes gap: G-XXX ({short gap name})
  · Stars: {N} ({M}/day) | Lang: {L} | License: {X}
  · Last activity: {date} ({N}d ago)
  · Integration: {drop-in / wrapper / MCP shim} (~{N} day)
  · Risk: {1 sentence regression note}
  · Links: [README](https://github.com/owner/name#readme) · [Releases](https://github.com/owner/name/releases) · [Recent commits](https://github.com/owner/name/commits/main)
  · Action: Say `ingest repo owner/name` to deep-dive.

(Repeat for each FLAGGED repo, max 3.)

WATCH (4-5/10):
  · [owner/name1](https://github.com/owner/name1) (5/10) — adjacent to G-003 voice tone-match
  · [owner/name2](https://github.com/owner/name2) (4/10) — graph lib, no direct gap match
```

**Tier 2 only (no FLAGGED, only WATCH):**

```
LEROY RADAR — Watching {N} (no flags today)
  · [owner/name](https://github.com/owner/name) (5/10) — {one-line reason}
```

**Bullet-point rule:** Every repo's "why" details use `· ` bullets, never paragraphs. Max 7 bullets per repo. If something needs more than one line, break into a sub-bullet.

**Link types every repo gets:**
1. Repo name itself → `https://github.com/{full_name}`
2. README link → `https://github.com/{full_name}#readme`
3. Releases link → `https://github.com/{full_name}/releases`
4. Recent commits → `https://github.com/{full_name}/commits/main`

### Manual Ingest Trigger (Never Autonomous)

When the user says **"ingest repo {owner/name}"**:
1. Spawn `@agent-builder` to fetch README + key source files
2. Generate integration plan: which LeRoy gap, what scaffold, what test
3. Write plan to `plans/leroy-radar-{repo-name}-{date}.md`
4. NO code merge until the user approves the plan

### Logging & Kill Switch

After every morning scan, append to `session/leroy-radar-log.jsonl`:
```json
{"date": "2026-04-30", "candidates_total": 18, "passed_filter": 4, "flagged_geq_6": 1, "watch_4_to_5": 2, "top_score": 7, "top_repo": "owner/name", "surfaced": true, "brian_ingested": null}
```

`top_score` and `top_repo` enable the Monday best-of-week guarantee — Monday briefing reads the last 7 entries and force-surfaces the highest `top_score` if no FLAGGED hits occurred.

**Auto-disable rule:** Read last 30 entries. If `flagged_geq_6` count is 0 across all 30 days AND `brian_ingested` is null in all 30, write `session/leroy-radar-config.json` → `{"disabled": true, "reason": "30 days low signal — even with ≥6 gate"}` and skip section. Re-enable manually with "enable leroy radar".

**Self-tuning hint:** If after 14 days `passed_filter` is consistently 0-1, the hard filter is too strict — relax language list or topic keywords. If `passed_filter` averages >5 but `flagged_geq_6` is still 0, the score axes need re-calibration (likely gap-match too strict — open new gaps in known-gaps.md).

### Failure Modes

| Issue | Response |
|-------|----------|
| github.com/trending fetch fails | Skip Source A, run Source B only |
| Watchlist file missing | Generate seed file from template (see watchlist template below) |
| WebFetch rate-limited | Cache last successful scan, show "(stale, {N}h old)" tag |
| Score gate produces no FLAGGED (≥6) hits 30 days | Auto-disable; log to scheduler-log.jsonl. the user re-enables via "enable leroy radar". |
| WATCH tier (4-5) producing zero hits too | Filter is overshooting — relax language whitelist or topic keywords |

### Watchlist Seed (one-time setup)

If `session/leroy-radar-watchlist.json` doesn't exist, create with:
```json
{
  "repos": [
    {"full_name": "anthropics/anthropic-cookbook", "reason": "tool-use + MCP patterns"},
    {"full_name": "modelcontextprotocol/servers", "reason": "reference MCP servers"},
    {"full_name": "mem0ai/mem0", "reason": "memory layer for AI agents"},
    {"full_name": "cline/cline", "reason": "VSCode agent — UX patterns"},
    {"full_name": "Aider-AI/aider", "reason": "voice + edit-loop reference"},
    {"full_name": "microsoft/graphrag", "reason": "edge-walk / graph recall"},
    {"full_name": "BerriAI/litellm", "reason": "model router patterns"},
    {"full_name": "openai/swarm", "reason": "multi-agent orchestration"},
    {"full_name": "stanford-oval/storm", "reason": "structured knowledge synthesis"},
    {"full_name": "evalplus/evalplus", "reason": "eval harness — LeRoy lacks one"}
  ],
  "last_updated": "2026-04-30"
}
```

---

## STEP 2.9: SECURITY SCAN (Every Morning — Mandatory)

> **Defensive Security:** 6-layer host + network scan. No AV needed.
> **Duration:** ~20-30 seconds
> **Skill:** `skills/routines/morning-security.md`

**Run every morning — no exceptions:**

```bash
cd ~/.claude
python tools/morning-security-scan.py
```

**Then read output file and display:**
```python
Read("~/.claude\\tools\\security-brief.md")
```

**If baseline doesn't exist yet (first run):**
```bash
python tools/baseline-builder.py
```
Then re-run the scan.

**Display in briefing:**

```
================================================================
SECURITY BRIEF                              Score: {N}/100 {icon}
================================================================
{contents of security-brief.md verbatim}
================================================================
```

**If score ≥ 40 (ELEVATED or CRITICAL):** Flag prominently at the TOP of the morning briefing before anything else. the user needs to see it immediately.

**If score < 20:** Show at normal position (after calendar, before sales).

---

## STEP 2.95: POST-DEPLOY SECURITY

> **Purpose:** Surface any security regressions and unverified-fixed sinks from the
> latest post-deploy diff, so the briefing always reflects the current security posture
> after a deploy rather than relying on a stale baseline.
> **Duration:** ~2-3 seconds (pure file read — no network, no scan)

**Run every morning — never block the briefing if this fails:**

```bash
cd ~/.claude
python tools/post-deploy-verifier/render_brief_section.py
```

**Then read the rendered output:**
```python
Read("~/.claude\\tools\\post-deploy-verifier\\results\\post-deploy-brief.md")
```

This output is embedded verbatim in the **Infrastructure Department > POST-DEPLOY SECURITY** block (see output template below). If the script errors for any reason, skip silently — never block the briefing.

---

## GROWTH AGENT STATUS (Auto-check)

Read `session/growth-agent-output.json` if it exists.

**If file exists AND `run_timestamp` is within last 48 hours:**
Show 3-line summary in briefing:
```
Growth Agent: {mode} run on {date} — {duration}s
  Vault: {total_notes} notes, {orphans_found} orphans, {index_coverage_pct}% indexed
  Skills: {N} generated ({N} approved, {N} quarantined) | Pending: {N} items
```

**If file exists BUT `run_timestamp` is more than 5 days old:**
```
Growth Agent: STALE (last run {date} — {days} days ago)
  Check Windows Task Scheduler > Claude-GrowthAgent
```

**If file doesn't exist:**
Skip silently (growth agent not yet set up).

**If `pending_review` array is non-empty:**
Add to briefing action items:
```
ACTION: Growth agent has {N} items pending your review. Say "growth agent status" for details.
```

---

## STEP 3: CONTEXT CHECK (Clawdbot Sessions)

**Check if chat context should be cleared before continuing.**

**Ask yourself:**
- Is this a fresh day with new priorities?
- Is the previous session context irrelevant?
- Has it been 24+ hours since last session?

**If yes to any:**
```
/new
```

Wait for fresh session confirmation, then restart morning routine.

**If continuing existing work:** Skip, proceed to next step.

---

## STEP 4: READ SCHEDULE REGISTRY

```python
# Read the schedule registry for recurring workflows
Read("~/.claude\\skills\\routines\\schedule-registry.json")

# Parse JSON and calculate days until each next_run
for workflow in registry["workflows"]:
    if workflow["enabled"]:
        days_until = calculate_days_until(workflow["next_run"])
        if days_until <= 7:
            scheduled_items.append({
                "name": workflow["name"],
                "days": days_until,
                "next_run": workflow["next_run"],
                "recurrence": workflow["recurrence"],
                "last_run": workflow["last_run"],
                "skill_path": workflow["skill_path"]
            })

# Sort by days ascending
scheduled_items.sort(key=lambda x: x["days"])

# Items with days=0 are "TODAY" and prompt for execution
```

---

## STEP 4.5: READ ONE-OFF REMINDERS

**One-off reminders are non-recurring tasks that need attention.**

```python
# Read the one-off reminders file
Read("~/.claude\\session\\one-off-reminders.json")

# Filter for active (not completed) reminders
active_reminders = []
for reminder in reminders_data["reminders"]:
    if not reminder["completed"]:
        active_reminders.append({
            "id": reminder["id"],
            "task": reminder["task"],
            "priority": reminder["priority"],
            "due_date": reminder["due_date"],
            "context": reminder["context"],
            "created": reminder["created"]
        })

# Sort by priority (high first) and due_date
active_reminders.sort(key=lambda x: (
    0 if x["priority"] == "high" else 1,
    x["due_date"] or "9999-99-99"
))
```

**How one-off tracking works:**

1. **Storage**: `session/one-off-reminders.json` - persistent across sessions
2. **Display**: Shown in morning briefing before scheduled workflows
3. **Management**:
   - Add: Edit JSON directly or use "add reminder" command
   - Complete: Mark `"completed": true` and set `"completed_at": "{timestamp}"`
   - Remove: Delete entry or keep for history
4. **Scope**: Personal tasks, follow-ups, meeting prep, one-time actions

**Unlike scheduled workflows:**
- One-offs don't recur (no next_run date)
- One-offs can be simple todos without skill paths
- One-offs are manually managed (no auto-scheduling)

---

## STEP 4.7: SMART TODOS — PERSONAL ACCOUNTABILITY (Top-3 Surfacing)

**Personal smart-todo system (mixed personal + your org). Built 2026-04-27.**

Load skill: `skills/routines/smart-todos.md` (dispatch skill — full schema, scoring, triggers)
Read data: `memory/Projects/Personal/smart-todos.md`

**Steps for morning render:**
1. Read `memory/Projects/Personal/smart-todos.md`
2. Parse table, skip rows tagged `example`
3. For each row, compute score per `memory/Projects/Personal/config.md` formula
4. Auto-flip status to `verdict` if age >30d AND status in (open, in-progress)
5. Take top 3 by score → render in Operations Department block
6. Count items with status=`verdict` → render verdict-needed line if >0
7. Check dormancy: if `last_updated` >14d AND no recent archive entries, render dormancy prompt

**Output goes in:** Operations Department section as "SMART TODOS (Personal)" block — see OUTPUT FORMAT below.

**Kindness rule (Diplomat's mandate):** ONLY top 3 surface in morning. Full list = on-demand only via "todo list" trigger. No wall of shame.

---

## STEP 4.8: GROWTH AGENT STATUS (Auto-Surface Pending Suggestions)

**Surface what the overnight dream scan + growth agent found. Fires every morning if non-empty.**

**Steps:**
1. Read `session/dream-pending-approvals.json` — count pending suggestions + top item
2. Read `session/growth-output.md` — check `Last updated:` timestamp; if >48h old, flag as stale
3. Read `session/growth-agent-output.json` — check `run_timestamp` (null = broken)

**Output conditions:**
- **Pending suggestions (>0):** Show count + top suggestion name + `say "register growth skills" to review`
- **Growth agent never ran / stale >48h:** Show `⚠️ Growth agent stale — no new patterns since {date}`
- **Zero pending + fresh:** Silent (no output — don't clutter briefing)

**Example output (non-empty case only):**
```
GROWTH ENGINE
  3 skill suggestions pending review
  Top: "ExampleClient Post-Session Auto-Recap" (S1, 2026-05-06)
  Say "register growth skills" to review and approve
```

**Placement:** Operations Department block (same section as smart todos).

---

## STEP 4.6: SMART TODO CHECK (Auto Cross-Reference)

**Automatically detect completed todos and suggest new ones.**

Load skill: `skills/meta/smart-todo-tracking.md`

```python
# Check for completion evidence across multiple sources
smart_check_results = {
    'completions': [],
    'suggestions': []
}

# For each active todo, check completion evidence
for todo in active_reminders:
    # 1. EMAIL EVIDENCE - Check if email was sent
    if todo.get('email'):
        sent_emails = mcp__email-primary__search_mail(
            query=f"in:sent to:{todo['email']} after:{todo['created'][:10]}",
            maxResults=50
        )
        if sent_emails['resultSizeEstimate'] > 0:
            smart_check_results['completions'].append({
                'todo': todo,
                'evidence': 'Email sent',
                'confidence': 'high',
                'details': f"Found {sent_emails['resultSizeEstimate']} sent email(s)"
            })

    # 2. CALENDAR EVIDENCE - Check if meeting occurred
    if todo.get('context') and 'meeting' in todo['context'].lower():
        # Check if calendar event with matching attendee occurred
        events_today = calendar_events  # From STEP 2
        for event in events_today:
            if todo.get('email') in str(event.get('attendees', [])):
                if event['start'] < now:
                    smart_check_results['completions'].append({
                        'todo': todo,
                        'evidence': 'Meeting occurred',
                        'confidence': 'high',
                        'details': f"Event: {event['summary']}"
                    })

# 3. SUGGEST NEW TODOS from unread emails with action items
unread_emails = gmail_unread_data  # From STEP 2
if unread_emails['resultSizeEstimate'] > 10:
    smart_check_results['suggestions'].append({
        'task': 'Review and triage {count} unread emails',
        'priority': 'medium',
        'context': f"{unread_emails['resultSizeEstimate']} unread in inbox",
        'source': 'gmail'
    })

# 4. SUGGEST NEW TODOS from upcoming calendar events
for event in calendar_events:
    if event['start'] > now and event['start'] < (now + 2_days):
        # Check if prep work needed
        if len(event.get('attendees', [])) > 3:
            smart_check_results['suggestions'].append({
                'task': f"Prepare for {event['summary']}",
                'priority': 'high',
                'due_date': event['start'][:10],
                'context': f"Meeting on {event['start'][:10]} with {len(event['attendees'])} attendees",
                'source': 'calendar'
            })

# Store results for output section
```

**Performance:** <5 seconds for all checks (run in parallel where possible)

---

## STEP 4.9: BACKGROUND AGENT OUTPUT CHECK

Before generating the morning brief, check if background agents wrote findings during the prior session. This surfaces system alerts and growth findings that would otherwise sit unread in output files.

```powershell
# Check system health alerts (from janitor Category 14)
$alertsPath = "~/.claude\session\system-health-alerts.md"
$systemAlerts = @()
if (Test-Path $alertsPath) {
  $systemAlerts = Get-Content $alertsPath
}

# Check scout/growth output
$growthPath = "~/.claude\session\growth-output.md"
$growthBlocks = @()
if (Test-Path $growthPath) {
  $raw = Get-Content $growthPath -Raw
  if ($raw -match '\[GROWTH\]') {
    $growthBlocks = ($raw -split '\n') | Where-Object { $_ -match '\[GROWTH\]' }
  }
}

# Check cleanup output for high-score alerts
$cleanupPath = "~/.claude\session\cleanup-output.md"
$cleanupAlert = $null
if (Test-Path $cleanupPath) {
  $cleanupContent = Get-Content $cleanupPath -Raw
  if ($cleanupContent -match 'Score:\s*(\d+)') {
    $score = [int]$Matches[1]
    if ($score -ge 10) { $cleanupAlert = "Cleanup score $score — action needed" }
  }
}
```

**Surface format in morning brief** (only shown when non-empty):

```
================================================================
SYSTEM ALERTS (N)
================================================================
[content from session/system-health-alerts.md — ALL alerts shown]

================================================================
SCOUT FINDINGS
================================================================
[GROWTH blocks from session/growth-output.md]
```

**Rules:**
- System alerts section is ALWAYS shown when `system-health-alerts.md` is non-empty — never suppressed
- Growth findings only shown if `[GROWTH]` blocks are present
- After surfacing, do NOT delete the alerts file — janitor/the user clears it manually
- Cleanup alert (if score ≥ 10) folds into the DAILY MAINTENANCE section

---

## OUTPUT FORMAT (v5.0 - Department-Based, Chief of Staff Coordination)

> **v5.0 CHANGE:** Morning briefing is now formatted as an your org Office daily ops report,
> organized by department instead of system-by-system. Data gathering steps (1-4.6) remain
> unchanged. Only the output formatting changes. Chief of Staff agent owns this format.
>
> **Reference:** `agents/chief-of-staff.md` for department mapping and escalation rules.
> **Reference:** `skills/meta/mcp-health-monitor.md` for MCP tracking and diagnostics.

### MCP Health Tracking (Integrated into Data Gathering)

During Phase 1 parallel data gathering, track success/failure of each MCP tool call:

```python
mcp_health_results = {}

# For each MCP tool call, wrap with health tracking:
try:
    calendar_result = mcp__email-primary__list_events(...)
    mcp_health_results["email-primary/list_events"] = {
        "status": "ok", "response_time_ms": elapsed_ms
    }
except Exception as e:
    calendar_result = None
    mcp_health_results["email-primary/list_events"] = {
        "status": "failed", "error": str(e)
    }

# After all calls: update state.json chief_of_staff.mcp_health
# Apply escalation rules from mcp-health-monitor.md
```

### Department Output Template

```
================================================================
     your org OFFICE - DAILY OPS REPORT
     {Day of Week}, {Month} {Date}, {Year}
================================================================

WEATHER - Coopersburg, PA
-------------------------
Today:    {Condition} | High: {X}F | Low: {Y}F
Tomorrow: {Condition} | High: {X}F | Low: {Y}F

================================================================
EXECUTIVE SUMMARY (COO)
================================================================

{IF critical_items > 0}
CRITICAL ITEMS REQUIRING ATTENTION:
{for each critical_item}
[!!] {department}: {description}
{end for}

{END IF}
Secretary Status (Last 24h):
  Events Tracked: {count} | Emails: {email_count} | Meetings: {meeting_count}
  {IF legal_coordination}
  Legal: {legal_summary}
  {END IF}

Today's Calendar (you@example.com):
{IF events exist}
{for each event}
  {time}: {event title}
{end for}
{ELSE}
  No events scheduled today.
{END IF}

This Week: {total_events} events | {meeting_count} meetings | {deadline_count} deadlines

{IF tax_data['include_in_briefing']}
TAX ALERT (Q{quarter} due in {days_until} days):
  Estimated quarterly payment: ${amount_due:,.2f}
  Due: {deadline}
  Say "tax status" for full breakdown.
{END IF}

================================================================
REVENUE GENERATION DEPARTMENT
================================================================

PIPELINE STATUS (your CRM)
{IF crm_tool}
  Active Deals: {total} | Value: ${total_value}
  {IF stage_changes}
  Stage Changes (Last 24h):
  {for each change}
  - {dealname}: "{old_stage}" -> "{new_stage}"
  {end for}
  {END IF}
  {IF new_deals}
  New Deals:
  {for each new_deal}
  + {company} - ${amount} ({stage})
  {end for}
  {END IF}
{ELSE}
  [!!] your CRM API unavailable - see Infrastructure
{END IF}

CLIENT COMMUNICATIONS
  Unread Emails: {count}
  {IF email_intel_available}
  {IF urgent_items}
  URGENT:
  {for each urgent_item}
  [!!] {client}/{contact}: {item}
  {end for}
  {END IF}
  {IF outstanding_items}
  Outstanding Items:
  {for each item}
  [ ] {client}: {item}
  {end for}
  {END IF}
  Say "email intel [client]" for full context.
  {END IF}

ACTIVE CLIENT WORK (Secretary Tracking)
{IF secretary_client_activity}
  | Client | Events | Last Activity |
  |--------|--------|---------------|
  {for each client in active_clients}
  | {client_name} | {event_count} | {last_activity_time} |
  {end for}
{ELSE}
  No tracked client activity in last 24h.
{END IF}

================================================================
OPERATIONS DEPARTMENT
================================================================

LEGAL COORDINATION
{IF legal_events}
{for each legal_event}
  - {client}: {action_description}
{end for}
{ELSE}
  No legal activity in last 24h.
{END IF}

ONE-OFF REMINDERS ({active_count} pending)
{IF active_reminders > 0}
{for each reminder sorted by priority/due_date}
  [{priority}] {task}
  {IF due_date} Due: {due_date} {END IF}
  {IF context} -> {context} {END IF}
{end for}
{ELSE}
  No pending reminders.
{END IF}

SMART TODO CHECK
{IF completions_detected > 0}
  Completions Detected: {count}
  {for each completion}
  [done?] {task} - Evidence: {evidence}
  {end for}
{END IF}
{IF new_suggestions > 0}
  New Suggestions: {count}
  {for each suggestion}
  [ ] {task} (Source: {source})
  {end for}
{END IF}

SMART TODOS (Personal Accountability) — Top 3 Today
{IF top_3_count > 0}
{for each item in top_3 sorted by score desc}
  [{score}] {id} | {priority} {due_label} | {energy} energy | {domain}
        {title}
{end for}
{ELSE}
  No active items. (Add: "add todo {text}")
{END IF}
{IF verdict_needed_count > 0}
  ⚠️  {verdict_needed_count} item(s) need verdicts (>30d) — say "verdict needed"
{END IF}
{IF dormant}
  💤 System dormant ({dormant_days}d no activity). Archive? Say "archive smart todos" to retire.
{END IF}
  Quick: done {id} | defer {id} {date} | add todo {text} | full list: "todo list"

================================================================
INFRASTRUCTURE DEPARTMENT
================================================================

MCP HEALTH STATUS
{for each mcp_tool in registry}
  {server}/{tool}: {status_icon} {status_text} {IF ok}({response_time}ms){END IF}
  {IF failed}
    Error: {error_description}
    Consecutive Failures: {count}
    {IF count >= 3}[!!] CRITICAL - Manual intervention needed{END IF}
  {END IF}
{end for}
  Summary: {healthy}/{total} healthy | {failed} failed | {skipped} not checked

A2A MESH STATUS
  Agent Cards: {count}/13 loaded | Orphaned: {count}
  Protocol: v3.0 (mesh-wrapper.md)
  Last delegation: {timestamp from a2a-delegation-log.jsonl}
  Cache entries: {count from a2a-cache.json selectors+schemas+validations}
  Issues: {any stale cards, missing cards, or unresolved delegations}

**How to check:**
1. Count files in `agents/agent-cards/*.agent.json`
2. Read last line of `session/a2a-delegation-log.jsonl` (if exists) for latest timestamp
3. Read `session/a2a-cache.json` and count non-empty keys
4. Cross-reference card count vs agents with `## A2A Inter-Agent Protocol` section

AUTO-SYSTEMS HEALTH
  Overall: {overall_health_icon} {overall_health_text}
  | System                  | Last Run                                         | Status  |
  |-------------------------|--------------------------------------------------|---------|
  | Daily Scheduler (Task)  | {state.auto_scheduler.last_run from scheduler-log.jsonl (last entry timestamp)} | {icon}  |
  | Memory Recall           | {last_run} | {icon}  |
  | Memory Consolidation    | {last_run} | {icon}  |
  | Email Intelligence      | {state.auto_scheduler.last_email_scan from state.json — set by scheduler; fallback to state.last_email_scan} | {icon}  |
  | Voice Corpus            | {state.auto_scheduler.last_voice_analysis from state.json — set by scheduler} | {icon}  |
  | Scout Agent             | {last_run} | {icon}  |
  | Secretary Agent         | {last_run} | {icon}  |
  | Position #0 Compliance  | {rate}%    | {icon}  |

  Email Intelligence read logic (priority order):
  1. state.json -> auto_scheduler.last_email_scan  (set by daily-scheduler.py)
  2. state.json -> last_email_scan.timestamp       (set by manual "scan emails" trigger)
  3. Fallback: show "Not run" with suggestion to run scheduler

  Daily Scheduler read logic:
  1. Read last line of session/scheduler-log.jsonl
  2. Parse {"timestamp": ..., "system": "state_update", "status": ...}
  3. If log missing or empty -> show "Never" with note to run setup-task-scheduler.ps1

{IF violations_last_24h > 0}
  Protocol Violations (24h): {count}
{END IF}

MEMORY SYSTEM
  Vault: {total_notes} notes | Last Recall: {time}ms | Status: {status}
  {IF rollout_phase != "complete"}
  Hybrid Recall v7.1: {rollout_phase} ({confidence}%)
  {END IF}
  Working Memory: {wm_health_status}
  {IF stale_actions > 0}
  [!] {stale_count} stale pending actions (>7 days)
  {END IF}

BACKUP STATUS
{IF backup_day}
  | Repo | Changes | Last Commit |
  |------|---------|-------------|
  {for each repo}
  | {name} | {changes} | {hash} {msg} ({time}) |
  {end for}
{ELSE}
  Next backup: {next_backup_day}
{END IF}

POST-DEPLOY SECURITY
{contents of post-deploy-brief.md verbatim}

================================================================
CTO OFFICE
================================================================

{IF cto_onboarding}
  CTO Onboarding: Day {day}/30
  Current Focus: {onboarding_focus}
{ELSE}
  Architecture Decisions: {recent_count} this week
  Tech Debt Ratio: {ratio}% (target: <10%)
  Security: {vuln_count} open ({critical} critical)
  Dependencies: {dep_status}
{END IF}

================================================================
HR DEPARTMENT
================================================================

  Headcount: {current}/{target} ({pct}% of YoY goal)
  Hiring Pipeline: {open_reqs} open requisitions
  {IF talent_scout_report}
  Talent Scout: {discovery_count} discoveries
  {END IF}
  {IF performance_concerns}
  Performance: {concern_count} agents need attention
  {END IF}

================================================================
CODING DEPARTMENT
================================================================

{IF sprint_active}
  Sprint {num}: Day {day}/14 | {status}
  Story Points: {completed}/{committed} ({accuracy}%)
  Velocity: {trend} (6-sprint avg: {avg})
  {IF impediments > 0}
  Impediments: {count} open
  {for each impediment}
  - {description} (Owner: {agent}, {hours}h)
  {end for}
  {END IF}
{ELSE}
  No active sprint.
{END IF}
  Bugs: {count} open ({critical} critical)
  Releases: {release_status}
  Test Coverage: {avg}% average

================================================================
SCHEDULED WORKFLOWS (Next 7 Days)
================================================================

{IF today_workflows > 0}
TODAY - Ready to Run:
{for each workflow}
  {name}
    Last: {date} | Recurrence: {pattern}
    -> Ready? [1] Yes [2] Skip [3] Reschedule
{end for}
{END IF}

{IF upcoming_workflows > 0}
Upcoming:
{for each workflow}
  {days} days | {name} ({day})
{end for}
{END IF}

{IF no_workflows}
No scheduled workflows in the next 7 days.
{END IF}

================================================================
DAILY MAINTENANCE
================================================================

Cleanup Scan: {cleanup_status} (score: {cleanup_score})
{IF cleanup_score >= 10}
  [!!] Cleanup action needed - {total_files} files ({total_size_mb}MB)
{ELSE}
  System clean - no action required.
{END IF}

================================================================
MONDAY SECTIONS (Monday Only)
================================================================

{IF is_monday}
  -> Metrics Dashboard: Available (say "metrics")
  -> Token Burn Report: Available (say "weekly report")
  -> YoY Snapshot: Available (say "YoY")
  -> Memory Vault Cleanup: {status}
  -> Quarantine Purge: {purge_status}
{END IF}
```

### Data-to-Department Mapping Reference

| Old Section (v4.x) | New Department (v5.0) |
|---------------------|----------------------|
| Weather | Header (unchanged) |
| your CRM Sync | Revenue Generation > Pipeline Status |
| Email Intelligence | Revenue Generation > Client Communications |
| Calendar Summary | Executive Summary > Today's Calendar |
| Email Status | Revenue Generation > Client Communications |
| Tax Status | Executive Summary (quarterly alert) |
| YoY Snapshot | Monday Sections |
| One-Off Reminders | Operations > Reminders |
| Smart Todo Check | Operations > Smart Todo |
| Secretary Status | Executive Summary + Revenue Gen > Active Client Work |
| Auto-Systems Health | Infrastructure > Auto-Systems Health |
| Memory System Health | Infrastructure > Memory System |
| Working Memory Health | Infrastructure > Memory System |
| Scheduled Workflows | Scheduled Workflows (unchanged) |
| Daily Cleanup | Daily Maintenance + Monday Sections (vault/quarantine) |
| Token Burn | Monday Sections |
| Backup Reminder | Infrastructure > Backup Status |
| **MCP Health (NEW)** | **Infrastructure > MCP Health Status** |
| **CTO Status (NEW)** | **CTO Office** |
| **HR Status (NEW)** | **HR Department** |
| **Sprint Status (NEW)** | **Coding Department** |
| **Post-Deploy Security (NEW)** | **Infrastructure > Post-Deploy Security** |

---

## BASH COMMAND PATTERNS (CRITICAL - Exit Code 127 Prevention)

**Exit code 127 = "command not found"** - This happens repeatedly when using unavailable commands.

### Commands That WORK

| Command | Use For | Example |
|---------|---------|---------|
| `curl` | HTTP requests, API calls | `curl -s "https://api.example.com" -H "Authorization: Bearer {key}"` |
| `grep` | Text filtering | `grep -o '"active":true' \| wc -l` |
| `wc` | Counting | `wc -l` (line count) |
| `powershell -Command` | Date, Windows operations | `powershell -Command "Get-Date -Format 'dddd, MMMM d, yyyy'"` |

### Commands That FAIL (Exit Code 127)

| Command | Why It Fails | Alternative |
|---------|--------------|-------------|
| `jq` | Not installed | Use `grep -o` for simple JSON extraction |
| `python3` | Use `python` instead | `python script.py` |
| Complex PowerShell pipes | Parsing issues | Break into separate commands |
| Linux-only commands | Windows environment | Use PowerShell equivalent |

### JSON Parsing Without jq

**DON'T:**
```bash
curl -s "https://api.example.com" | jq '.count'  # Exit code 127!
```

**DO:**
```bash
# Count occurrences with grep
curl -s "https://api.example.com" | grep -o '"active":true' | wc -l

# Or use WebFetch tool instead of bash for API calls
```

### Rule: When Bash Fails

1. **First failure**: Try alternative command pattern from this table
2. **Second failure**: Use WebFetch tool instead of bash for API calls
3. **Never**: Keep retrying the same failing command pattern

---

## Error Handling

| Issue | Response |
|-------|----------|
| **Bash exit code 127** | Command not found - check "BASH COMMAND PATTERNS" section above |
| No scheduled workflows | Display "None" message, continue |
| Weather API fails | Display "Weather unavailable", continue |
| Calendar/Email API fails | Display "unavailable", continue |

---

================================================================
MONDAY METRICS DASHBOARD (Weekly Compliance Review)
================================================================

**Only triggered on Mondays.** Generate weekly enforcement system compliance report for previous 7 days.

### Detection Logic

```yaml
# After getting system date in Phase 1, check if Monday
if day_of_week == "Monday":
  # Generate dashboard for previous week
  monday_metrics_dashboard = True

# Run voice pattern analysis EVERY morning (background, lightweight)
daily_voice_analysis = True
```

### Dashboard Generation

```bash
# Generate dashboard for last 7 days
python "~/.claude\scripts\generate_dashboard.py" --days 7
```

### Display Format

```
================================================================
METRICS DASHBOARD (Weekly Compliance Review)
================================================================

Date Range: 2026-01-09 to 2026-01-16 (7 days)

COMPLIANCE SUMMARY
------------------
Gate Output:      95.2% ✅ (target: 95%+)
Tag Validation:   98.1% ✅ (147 accepted, 3 rejected)
Checkpoint:       94.3% ⚠️ (17 on-time, 1 late)
Cache Hit Rate:   92.4% ✅

TRENDS (Week-over-Week)
-----------------------
Gate:       +2.1%
Tags:       +0.5%
Checkpoints: -1.2% (slight decline)
Cache:      +3.8%

VIOLATIONS DETECTED
-------------------
3 checkpoint delays (16-18 min intervals)
2 tag rejections (invalid tag types)

TOP ISSUES
----------
Most Common Tag Rejections:
  1. "First tag must be folder tag" (2 occurrences)

Longest Checkpoint Intervals:
  1. 2026-01-15T10:30:00 - 18 minutes

EVENTS PER DAY
--------------
(ASCII chart showing daily event counts)

Status: action_required (checkpoint adherence below 95%)
Recommendation: Review checkpoint timing enforcement
```

### Save Dashboard Report

```bash
# Save to session folder for reference
python "~/.claude\scripts\generate_dashboard.py" --days 7 --output "~/.claude\session\metrics\weekly-dashboard-$(powershell -Command 'Get-Date -Format yyyy-MM-dd').md"
```

### Execution Order

1. Generate dashboard (Python script)
2. Display compliance summary in briefing
3. Save full report to `session/metrics/weekly-dashboard-YYYY-MM-DD.md`
4. Continue with other Monday tasks (cleanup, leadership report, etc.)

**Note:** Dashboard runs inline (not background) - takes <300ms to generate.

---

================================================================
DAILY VOICE ANALYSIS (Background Pattern Learning)
================================================================

**Runs EVERY morning.** Analyzes the user's linguistic corpus and updates voice profile. Lightweight script (<100ms), no performance impact.

### Why Daily (Not Monday-Only)

- **Simpler logic:** No day-detection failure risk
- **More responsive:** Voice profile updates as patterns emerge
- **Lightweight:** Script is <100ms, negligible cost
- **Reliable:** No missed analyses due to detection issues

### Spawn Trigger

```python
# In Phase 1, every morning:
if daily_voice_analysis:
    # Run voice pattern analysis (non-blocking)
    Bash(
        command="python ~/.claude\\scripts\\analyze-lingo-patterns.py",
        run_in_background=True,
        description="Daily voice pattern analysis"
    )
```

### Display Format (In Briefing Output)

```
================================================================
VOICE LEARNING STATUS (Monday Analysis)
================================================================

Corpus: {sample_count} messages captured
Profile: v{version} ({confidence})
Last Analysis: {timestamp}

{IF sample_count >= 10}
Top Vocabulary: {top_5_words}
Characteristic Phrases: {top_3_phrases}
Avg Sentence Length: {avg_length} words

Status: Voice profile v{version} updated
{ELSE}
Status: Collecting data ({sample_count}/10 minimum for analysis)
{END IF}

Next analysis: {next_monday}
```

### What Gets Updated

1. **Memory note:** `memory/Patterns/the user-Linguistic-Profile-v*.md`
   - Versioned based on sample size (v1 < 50, v2 < 200, v3 < 500, v4 500+)
   - Human-readable patterns for memory recall

2. **JSON profile:** `session/council-voice-profile.json`
   - Programmatic access for email composition
   - Contains vocabulary, phrases, sentence patterns, formality distribution

### Integration with Email Protocol

Voice profile is auto-loaded in `gmail-send-protocol.md` Step 3.5:
1. Memory system recalls `the user-Linguistic-Profile-v*.md`
2. Email composition skill applies patterns
3. Result: Emails sound like the user, not generic AI

---

================================================================
DAILY CLEANUP (Background Auto-Scan)
================================================================

**Runs EVERY morning.** This section spawns the janitor in background while the rest of the briefing continues. Replaces the old Monday-only cleanup -- user requested daily automation (2026-02-15).

### Detection Logic

```yaml
# Runs EVERY morning (no day-of-week check) - automated daily per user request
# Spawn janitor in background
Task(
  subagent_type="general-purpose",
  run_in_background=true,
  model="haiku",
  description="Daily cleanup scan",
  prompt="You are the janitor..."
  )

# DO NOT wait - continue with morning briefing
# Cleanup results surface after briefing completes (if score >= 10)
```

### Spawn Trigger

```python
# In Phase 1 - runs EVERY morning (daily, not Monday-only):
# Spawn cleanup orchestrator (non-blocking)
cleanup_task = Task(
    subagent_type="general-purpose",
    run_in_background=True,
    model="haiku",
    description="Daily cleanup scan",
    prompt=f"""
    You are the janitor orchestrator.

    PATHS:
    - Output: ~/.claude\\session\\cleanup-output.md
    - Manifest: ~/.claude\\session\\cleanup-manifest.json

    Spawn 10 parallel agents to scan these categories:
    1. debug/ (7 days)
    2. shell-snapshots/ (14 days)
    3. paste-cache/ (30 days)
    4. file-history/ (30 days)
    5. session/ (7 days, excluding state.json)
    6. temp/tmp/cache/ (3 days)
    7. Root scripts (temp_*.ps1, 14 days)
    8. Root data (*.csv, 30 days)
    9. projects/ (60 days, orphans)
    10. todos/ (14 days)

    Calculate cleanup_score = files + (size_mb * 2) + (categories * 5)
    Write results to cleanup-output.md
    """
)

# Store task_id in state.json for tracking
# Continue with rest of morning briefing
```

### Post-Briefing Check

```yaml
# After morning briefing output is complete:
if cleanup_spawned:
  # Read cleanup results
  cleanup_output = Read("session/cleanup-output.md")

  if cleanup_score >= 10:
    # Surface [CLEANUP] block
    display_cleanup_summary()
  else:
    # Silent - nothing to report
    pass
```

### Display Format (When Surfaced)

```
================================================================
DAILY CLEANUP SCAN
================================================================

Score: 47 | Threshold: 10 | Status: action_required

| Category          | Files | Size   | Action               |
|-------------------|-------|--------|----------------------|
| debug/            | 98    | 42MB   | Quarantine (>7 days) |
| shell-snapshots/  | 312   | 668KB  | Quarantine (>14 days)|
| todos/            | 480   | 1.2MB  | Quarantine (>14 days)|

Total: 890 files (~46MB) ready for quarantine

Actions: [1] Review details  [2] Auto-quarantine  [3] Skip this week
```

### Memory Vault Orphan Detection (Also on Mondays)

**Orphan Check Results:**

```
================================================================
MEMORY VAULT ORPHAN SCAN
================================================================

Orphans Detected: {count} / {total_notes} ({percentage}%)

{IF orphans > 0}
| Folder          | Orphans | Oldest | Recommendation          |
|-----------------|---------|--------|-------------------------|
| Patterns/       | 12      | 147d   | Review & add links      |
| Decisions/      | 5       | 89d    | Archive if obsolete     |
| Projects/your org/   | 8       | 203d   | Archive old projects    |

Recent Orphans (<90 days): {count} → Add wikilinks to integrate
Old Orphans (>90 days): {count} → Consider archiving

Actions:
  [1] View full report (session/orphan-report.md)
  [2] Archive old orphans
  [3] Skip - will recheck next Monday
{ELSE}
✅ No orphans detected. All notes are connected!
{END IF}
```

**How Orphan Detection Works:**
- Scans all notes for wikilinks ([[links]]) and embeds (![[embeds]])
- Identifies notes with ZERO incoming AND outgoing connections
- Orphans are flagged in memory-index.json (excluded from recall)
- Report generated: `.claude/session/orphan-report.md`

### Memory Vault Cleanup (Also on Mondays)

```yaml
# Check if memory cleanup needed (>7 days since last_cleanup)
if "Monday" in system_date:
  state = Read(".claude/session/state.json")
  last_cleanup = state.memory_system.last_cleanup

  if last_cleanup is null or days_since(last_cleanup) > 7:
    # Spawn memory organizer in background
    vault_cleanup_task = Task(
      subagent_type="general-purpose",
      run_in_background=True,
      model="haiku",
      description="Memory vault cleanup",
      prompt=f"""
      You are the memory vault organizer.

      VAULT PATH: ~/Projects\\memory\\

      Execute cleanup per skills/meta/memory-organizer.md:

      1. SCAN vault structure
         - Count folders per tier (limit: 10)
         - Find notes >90 days unreferenced
         - Find version duplicates (keep latest only)
         - Validate tag structure per STRICT RULES v1.0
         - **RUN ORPHAN DETECTION** (scripts/detect-memory-orphans.py)
           → Detects notes with NO wiki embeds or graph connections
           → Updates memory-index.json to flag orphans
           → Generates orphan-report.md

      2. VALIDATE TAGS (Auto-fix)
         - Ensure folder tag is first (decisions, patterns, etc.)
         - Remove invalid tags (descriptive, version, action types)
         - Limit to 4 tags max
         - Add missing folder tags from path

      3. ARCHIVE old versions
         - Move to System/Archive/{date}/
         - Keep only most recent version
         - Update wikilinks if needed

      4. CONSOLIDATE duplicates
         - Merge same-topic notes
         - Preserve history sections

      5. WRITE cleanup log
         - Update System/cleanup-log.md
         - Report: notes archived, tags fixed, stats

      6. UPDATE state.json
         - Set memory_system.last_cleanup = current timestamp

      OUTPUT: memory/System/cleanup-log.md
      """
    )

    # Continue with rest of morning briefing
```

**Memory cleanup runs silently in background. No user notification unless errors occur.**

### Quarantine Check (Also on Mondays)

```yaml
# Check for aged quarantine folders to purge
for folder in quarantine/:
  if folder_age >= 7 days:
    purge folder
    log: "Purged quarantine/{date}/"
```

---

================================================================
BACKUP REMINDER (Mon/Wed/Fri)
================================================================

**Triggered on Monday, Wednesday, and Friday.** Reminds user to push critical repositories to GitHub backup.

### Detection Logic

```yaml
# After getting system date in Phase 1
if day_of_week in ["Monday", "Wednesday", "Friday"]:
  backup_reminder = True

  # Check repo status in parallel
  Bash("cd '~/.claude' && git status --porcelain | wc -l")
  Bash("cd '~/.claude' && git log -1 --format='%h %s (%cr)'")
  Bash("cd '~/Projects\\your org' && git status --porcelain | wc -l")
  Bash("cd '~/Projects\\your org' && git log -1 --format='%h %s (%cr)'")
```

### Repositories

| Local Path | Remote | Description |
|------------|--------|-------------|
| `~/.claude` | github.com/<your-org>/<repo> | Claude config & skills |
| `~\Projects\your org` | github.com/<your-org>/<repo> | your org projects |

### Display Format

```
================================================================
BACKUP REMINDER (Mon/Wed/Fri)
================================================================

| # | Repository    | Status      | Last Commit              |
|---|---------------|-------------|--------------------------|
| 1 | .claude       | {X} changes | {hash} {msg} ({time})    |
| 2 | your org           | {X} changes | {hash} {msg} ({time})    |

Actions:
  [1] Push .claude to LeRoy
  [2] Push your org to org-backup-repo
  [3] Push both
  [4] Skip backup
```

### On Selection

Load skill: `routines/backup-reminder.md` for push execution logic.

---

================================================================
GRADE-READY SIGNAL (an LMS Grade-Entry Prompt)
================================================================

**Toggle key:** `grade_ready_signal`
**Default:** `enabled` (runs every morning if the key is absent or set to `true`)

When enabled, the morning briefing runs `tools/grade_ready_check.py` (read-only, no
writes, no mark-as-read) to count unread a course / a course completion emails in the
`guided assignments` label at personal@example.com.

- **Count > 0:** Print a single attention line — `🎓 {N} grade(s) ready — say "enter my grades" to process.`
- **Count = 0 or tool fails:** Silent-fail — no output, no error surfaced to the user.
- **Guarantee:** The check is strictly read-only (Gmail `readonly` scope).
  It never marks emails as read, never triggers grade entry.

**Disable for a session:** set `session/grade_ready_signal.off` (touch the file); remove to re-enable.
**Permanent disable:** add `"grade_ready_signal": false` to `session/state.json`.

*Added 2026-06-15 per decision dec-6fd5fc28.*

---

================================================================
SESSION END CONSOLIDATION (Automatic)
================================================================

**After briefing completes and user signs off:**

Load: `meta/memory-consolidation.md`

**Extracts from session:**
- Decisions made (if any architectural choices)
- Patterns observed (from growth monitor if active)
- Preferences learned (user style, communication)
- Project learnings (if applicable)

**Writes to:** `memory/Claude/{category}/`

**Output:**
```
[MEMORY] Saved 2 notes to LeRoy Memory:
• Preference: Morning briefing timing → Preferences/
• Pattern: System monitoring focus → Patterns/
```

---

*Last Updated: 2026-02-17*
*Changes:*
- *v5.2: EXTERNAL DAILY SCHEDULER - Added scripts/daily-scheduler.py (runs via Windows Task Scheduler at 8am daily, no Claude session required). Added scripts/setup-task-scheduler.ps1 (one-time registration script). AUTO-SYSTEMS HEALTH table now shows "Daily Scheduler (Task)" row sourced from scheduler-log.jsonl, and Email Intelligence row reads from state.json auto_scheduler.last_email_scan (written by scheduler) instead of showing "Not run".*
- *v5.1: DAILY CLEANUP AUTOMATION - Cleanup scan now runs EVERY morning (not just Mondays). User requested automation because manual trigger was consistently forgotten. Cleanup spawns in background, stays silent unless score >= 10. Monday-only items (vault cleanup, quarantine purge, orphan detection) remain Monday-only. Added DAILY MAINTENANCE section to output template.*
- *v5.0: DEPARTMENT-BASED RESTRUCTURE - Morning briefing now organized by your org Office departments (Executive, Revenue Gen, Operations, Infrastructure, CTO Office, HR, Coding) instead of system-by-system. Added Chief of Staff agent as briefing coordinator. Added MCP Health Monitoring to Infrastructure department. New sections for CTO Office, HR, and Coding departments. Data gathering unchanged, output format completely redesigned.*
- *v4.1: Fixed Google MCP integration - Updated to correct tool names (mcp__email-primary__list_events, mcp__email-primary__search_mail), removed personal calendar/email (personal-account), added Step 4.6 Smart Todo Check for automatic completion detection and new todo suggestions based on email/calendar/memory cross-referencing*
- *v4.0: LEROY Phase 4 - Added Step 2.5 Calendar Summary with weekly view, reminder scan, missing invite detection, and overdue alerts*
- *v3.2: Removed all n8n monitoring (no longer applicable to LeRoy/your org system) and removed Monday Leadership Report reminder (archived to memory/Projects/your organization/) - system detached from your organization operations*
- *v3.1: Restored calendar and email checking for your org and Personal accounts (no your organization) - morning briefing now includes today's events and unread email counts*
- *v3.0: Removed all Google MCP functionality (calendars, emails, LeRoy ATTENTION) - focused on system monitoring only*
- *v2.7: Added Monday Token Burn Report reminder - asks about weekly efficiency report with WoW trends and year-to-date projections*
- *v2.6: Added Memory Recall (Step 0) and Session End Consolidation - automatic Obsidian integration*
- *v2.5: Added Backup Reminder section (Mon/Wed/Fri) for .claude->LeRoy and your org->org-backup-repo*
- *v2.4: Added Monday Leadership Report reminder section - prompts user to generate 2-page PDF for leadership meeting*
*Maintainer: the user*
