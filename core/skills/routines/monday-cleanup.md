# Monday Cleanup Routine

## Trigger
- **Automatic:** Every Monday via schedule-registry.json (background scan)
- **Manual:** "run cleanup", "monday cleanup", "system cleanup", "clean claude"

---

## Purpose

Background auto-scan of `.claude/` folder to identify cleanup candidates across 11 folder categories including file organization validation. Only surfaces when significant issues found (cleanup_score >= 10). Uses quarantine-first approach with 7-day auto-purge.

**File Organization Enforcement:** Category 11 validates files are in correct locations per `session/CLEANUP-PROTOCOL.md`. Detects scripts/data/reports in root, project files in session root, etc.

---

## Execution Mode

| Mode | Behavior |
|------|----------|
| **Automatic (Monday)** | Background spawn, silent unless cleanup_score >= 10 |
| **Manual** | Foreground with immediate feedback |

---

## Process

### Phase 1: Spawn Orchestrator

```yaml
Load: agents/janitor.md
Mode: run_in_background: true
Model: haiku
Output: session/cleanup-output.md
Manifest: session/cleanup-manifest.json
```

### Phase 2: Wait for Completion

The orchestrator spawns 11 parallel Task agents (one per category).
Typical completion: 30-60 seconds.

### Phase 3: Check Score

```yaml
Read: session/cleanup-output.md
Parse: cleanup_score

if cleanup_score >= 10:
  Surface [CLEANUP] block
else:
  Stay silent (logged to session/cleanup-manifest.json)
```

### Phase 4: User Decision

Options presented:
```
[1] Review candidates - Show detailed breakdown by category
[2] Auto-quarantine   - Move all to quarantine/{date}/
[3] Skip this week    - Log skip, no action
[4] Adjust thresholds - Modify category thresholds
```

### Phase 5: Execute Quarantine

If quarantine selected:
1. Create `quarantine/{YYYY-MM-DD}/`
2. Move files preserving relative paths
3. Write `quarantine-manifest.json`
4. Update `session/state.json`
5. Confirm completion with summary

---

## 11 Category Thresholds

| # | Category | Age | Size | Count | Pattern |
|---|----------|-----|------|-------|---------|
| 1 | debug/ | 7d | >10MB/file | >100 | Debug logs |
| 2 | shell-snapshots/ | 14d | - | >500 | Bash artifacts |
| 3 | paste-cache/ | 30d | - | >20 | Clipboard temp |
| 4 | file-history/ | 30d | >50MB/file | >200 | Transcripts |
| 5 | session/ | 7d | - | Stale only | Session files (not state.json) |
| 6 | temp/tmp/cache/ | 7d | - | Any | Auto-purge temp files >7 days |
| 7 | Root scripts | 14d | - | - | temp_*.ps1, calc_*.ps1 |
| 8 | Root data | 30d | - | - | *.csv (except protected) |
| 9 | projects/ | 60d | - | No activity | Orphan UUID folders |
| 10 | todos/ | 14d | - | >200 | Agent remnants |
| 11 | Organization | - | - | Any | Files in wrong locations (see CLEANUP-PROTOCOL.md) |

---

## Scoring Formula

```
cleanup_score = files_over_threshold + (size_mb * 2) + (categories_flagged * 5)

Surface threshold: 10
```

### Examples

| Scenario | Calculation | Result |
|----------|-------------|--------|
| 15 files over threshold | 15 | SURFACE |
| 5 files + 10MB debris | 5 + 20 = 25 | SURFACE |
| 3 files + 1MB + 1 category | 3 + 2 + 5 = 10 | SURFACE |
| 2 files + 0.5MB + 1 category | 2 + 1 + 5 = 8 | SILENT |

---

## Output Format

```
[CLEANUP] Monday Scan Complete

Score: {N} | Threshold: 10 | Status: {action_required|clean}

┌─ FINDINGS ──────────────────────────────────────────────┐
│ Category          │ Count │ Size   │ Recommendation     │
├───────────────────┼───────┼────────┼────────────────────┤
│ debug/            │  127  │ 44MB   │ Quarantine 98      │
│ shell-snapshots/  │  415  │ 668KB  │ Quarantine 312     │
│ todos/            │  560  │ 1.2MB  │ Quarantine 480     │
└───────────────────┴───────┴────────┴────────────────────┘

Total: 890 files (~46MB)

Actions: [1] Review  [2] Quarantine  [3] Skip
```

---

## Quarantine Flow

```
1. SCAN    → 11 agents scan in parallel (including organization check)
2. SCORE   → Orchestrator calculates cleanup_score
3. SURFACE → Only if score >= 10, show [CLEANUP] block
4. REVIEW  → User picks: Review | Quarantine | Skip | Fix Organization
5. MOVE    → Files → quarantine/{YYYY-MM-DD}/ OR proper location
6. TRACK   → Write quarantine-manifest.json
7. PURGE   → Auto-delete after 7 days (next Monday checks)
```

### Quarantine Manifest Schema

```json
{
  "date": "2026-01-13",
  "source_scan": "monday-cleanup",
  "total_files": 890,
  "total_size_mb": 46,
  "auto_purge_date": "2026-01-20",
  "categories": {
    "debug": {
      "count": 98,
      "size_mb": 42,
      "files": [
        {
          "source": "debug/abc123.txt",
          "age_days": 12,
          "size_kb": 450,
          "reason": "age > 7 days"
        }
      ]
    }
  },
  "status": "pending_review | confirmed | purged"
}
```

---

## Skill Creation Prompt

When same cleanup pattern repeats 3+ Mondays:

```
[CLEANUP-SKILL] Recurring pattern detected:

Pattern: temp_*.ps1 files in root
Occurrences: 3 consecutive weeks
Recommendation: Create auto-move rule

Create skill? [1] Yes  [2] No  [3] Remind later
```

---

## Protected Files (Never Cleanup)

```yaml
protected:
  - CLAUDE.md
  - settings.json
  - settings.local.json
  - .credentials.json
  - .gitignore
  - history.jsonl
  - session/state.json
  - session/prompt-history.jsonl  # Bulletproof prompt capture
  - session/context-anchor.md     # Task context recovery
  - session/growth-output.md
  - session/growth-history.md
  - skills/**/*  # Entire skill library
  - agents/**/*  # Entire agent library
  - hooks/**/*   # Hook scripts
```

---

## State Tracking

Add to `session/state.json`:

```json
{
  "cleaner": {
    "active": false,
    "task_id": null,
    "last_run": "2026-01-13T08:00:00Z",
    "last_score": 47,
    "last_action": "quarantined",
    "quarantine_path": "quarantine/2026-01-13",
    "patterns_tracked": ["temp_*.ps1"]
  }
}
```

---

## Manual Execution

When triggered manually (not Monday morning):

1. Skip schedule check
2. Run full scan immediately
3. Surface results regardless of score
4. Present same action options

```bash
# User triggers manually
"run cleanup"

# Claude responds
[CLEANUP] Manual scan initiated...

[After scan completes]
[CLEANUP] Scan Complete

Score: 47 | Threshold: 10 | Status: action_required
...
```

---

## Purge Check (Weekly)

Each Monday cleanup also checks for aged quarantine folders:

```yaml
for each folder in quarantine/:
  parse folder date from name (YYYY-MM-DD)
  calculate age = today - folder_date

  if age >= 7 days AND status != "restored":
    delete entire folder
    log: "Purged quarantine/{date} - {N} files, {X}MB"
```

---

## Error Handling

| Issue | Response |
|-------|----------|
| Agent spawn fails | Retry once, then surface error |
| Scan timeout (>5min) | Surface partial results |
| No cleanup needed | Silent log, no user prompt |
| Quarantine folder exists | Append date suffix (2026-01-13-2) |
| Protected file matched | Skip with warning in manifest |

---

## A2A Parallel Scan Coordination

The 11 category scan agents write results directly to cache — janitor aggregates from cache rather than waiting for each agent to report back through conductor.

**Each category agent broadcasts on completion:**
```
[A2A:BROADCAST]
key: monday-cleanup.{YYYY-MM-DD}.cat_{N}
data: { "category": "debug/", "flagged_files": [...], "total_size_mb": N, "score_contribution": N }
[/A2A:BROADCAST]
```

**Janitor aggregates when all 11 keys are present (or after 90s timeout):**
```
[A2A:SUBSCRIBE]
keys:
  - monday-cleanup.{date}.cat_1  through  monday-cleanup.{date}.cat_11
[/A2A:SUBSCRIBE]
```

**Alignment-monitor SUBSCRIBES for orphan findings:**
```
[A2A:SUBSCRIBE]
keys:
  - monday-cleanup.{date}.cat_9   # projects/ orphan UUID folders
  - monday-cleanup.{date}.cat_11  # organization violations
[/A2A:SUBSCRIBE]
```
Alignment-monitor surfaces file-organization violations to memory-organizer without requiring janitor to relay them.

**Benefit:** All 11 scans run fully in parallel; janitor only reads final cache keys, never waits for sequential agent returns.

---

*Monday Cleanup Routine v1.0 | Background auto-scan | Quarantine-first | 7-day purge*
