---
user-invocable: false
disable-model-invocation: true
context: fork
agent: Explore
---

# Growth Agent Status & Registration

## Triggers
- "growth agent status", "growth report" → Show last run results
- "register growth skills" → Register approved auto-generated skills in CLAUDE.md
- "dream", "dream scan", "24h review", "what did i do yesterday", "what did i work on" → Run dream scan (24h mode)

---

## Dream Mode (24h Activity Scan)

On-demand or scheduled daily at 8AM (Task Scheduler: `your org-DreamAgent`).
Also accessible via the 🌙 Dream button on the Telegram bot.

**What it does:**
1. Reads `session/prompt-history.jsonl` + `session/agent-spawn-log.jsonl` filtered to last 24h
2. Finds memory files modified in the last 24h (mtime check)
3. Calls `claude -p` for intelligence: SUMMARY → PATTERNS → SUGGESTIONS
4. Writes suggestion metadata to `session/dream-pending-approvals.json`
5. Sends formatted report to Telegram (8AM scheduled run) or returns text (on-demand)

**Key philosophy — AUTONOMOUS FOCUS LAW:**
Dream scan suggestions must be event-driven, scheduled, or threshold-based.
They fire WITHOUT the user typing anything. No new trigger keywords.

**To run on desktop:**
```
python scripts/dream-agent.py
```
Or with direct Telegram send:
```
python scripts/dream-agent.py --send-telegram
```

**Approval flow:**
1. Tap `➕ Queue [SN]` on Telegram → written to `session/skill-promotion-candidates.json`
2. On desktop say "register growth skills" → builder implements approved items

**Schedule registration:**
Task: `your org-DreamAgent` | Daily 8:00 AM | `python scripts/dream-agent.py --send-telegram`
To install: `powershell -ExecutionPolicy Bypass -File tools\install-dream-agent.ps1`

---

## Show Status

1. Read `session/growth-agent-output.json`
2. If file doesn't exist or `run_timestamp` is null: "Growth agent has never run. Check Task Scheduler for `Claude-GrowthAgent`."
3. Display summary:

```
Growth Agent Last Run
---------------------
Date: {run_timestamp}
Mode: {mode}
Duration: {duration_seconds}s
Status: {CLEAN if no errors, WARNINGS if errors array non-empty}

Vault Health:
  Notes: {total_notes} | Orphans: {orphans_found} | Tags fixed: {tag_violations_fixed}
  Index: {index_coverage_pct}% | Sidecar: {sidecar_status}

Skills Generated: {count}
{list each with name, quality score, status}

Pending Review: {count}
{list each item}

Next Run: {next_run}
```

4. If `run_timestamp` is more than 5 days old: flag "Growth agent may not be firing. Check Windows Task Scheduler > Claude-GrowthAgent."

---

## Register Growth Skills

1. Read `session/growth-agent-output.json`
2. Filter `skills_generated` for status = "approved"
3. For each approved skill:
   a. Update the skill's frontmatter to remove `disable-model-invocation: true` (now routable)
   b. Run reindex: `python ~/.claude\scripts\build-skill-index.py`
   c. Skill is now auto-discoverable via skill-matcher — **no CLAUDE.md edit required**
   d. Apply hot list check: does this skill meet criteria (>5×/week OR safety-critical)?
      - YES → propose hot list entry to the user, add to CLAUDE.md on approval, version bump + commit
      - NO → reindex was enough, nothing more to do
4. Output: "Registered N skills. Hot list additions: M (pending approval)."

---

## Check Quarantine

1. List files in `skills/quarantine/` (excluding README.md)
2. For each quarantined skill:
   - Show filename, generated_at date, quality score
   - Offer: [1] Promote (move to proper folder) [2] Archive [3] Skip
3. If folder is empty: "No quarantined skills."

---

## Weekly Hot List Audit (Runs as Part of Dream Scan on Mondays)

**Purpose:** Keep the 10-row hot list accurate — surface removal candidates (cold triggers) and promotion candidates (popular dynamic triggers).

**Data source:** `session/skill-usage.jsonl` (written by skill-usage-tracker.py hook on every skill invocation)

### Step 1: Load hot list

Read current hot list from CLAUDE.md (section: `## Hot List`). Extract the 10 trigger entries and their skill paths.

### Step 2: Count hits per hot list trigger (last 30 days)

```python
python scripts/skill-usage-tracker.py --report
# Reads skill-usage.jsonl, outputs session/skill-promotion-candidates.json
```

For each hot list skill, find its hit count in the last 30 days.

**Removal candidate:** hot list trigger with 0 hits in 30 days.
**Threshold:** HOT = ≥ 20 hits / 30d (≈ 5×/week)

### Step 3: Count hits for dynamic triggers (skill-matcher routed)

Same data source — look for skills that routed via skill-matcher (not hot list) and count their hits.

**Promotion candidate:** dynamic skill with ≥ 20 hits in 30 days.

### Step 4: Write candidates to dream-pending-approvals.json

Append two arrays to `session/dream-pending-approvals.json`:

```json
{
  "hot_list_removal_candidates": [
    {"skill": "skills/routines/heartbeat.md", "trigger": "heartbeat", "hits_30d": 0, "last_hit": "2026-04-10"},
    ...
  ],
  "hot_list_promotion_candidates": [
    {"skill": "skills/meta/cost-tracker.md", "trigger_phrase": "cost report", "hits_30d": 28, "routed_via": "skill-matcher"},
    ...
  ]
}
```

### Step 5: Include in Telegram dream report

Add section to the Monday dream scan Telegram message:

```
📊 Hot List Audit
  Removal candidates (0 hits/30d): [skill names]
  Promotion candidates (≥20 hits/30d): [skill names]
  Review: say "hot list audit" to act on these
```

COO reviews and acts on candidates — no automatic hot list changes. All CLAUDE.md changes require version bump + commit.
