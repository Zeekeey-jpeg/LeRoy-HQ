---
user-invocable: false
---

# Memory Organizer - Background Vault Cleanup

> **AUTO-TRIGGERED:** Weekly on Monday mornings (during morning routine)
> **RUNS IN BACKGROUND:** Agent spawned silently, reports only if action needed

## Purpose

Keep Obsidian vault clean, organized, and under the 10-folder-per-tier limit.

## Scheduling

**Trigger:** Monday morning routine detects `last_cleanup > 7 days`

**Agent:** Spawned in background via Task tool
```json
{
  "subagent_type": "general-purpose",
  "run_in_background": true,
  "description": "Clean LeRoy Memory vault"
}
```

## Fixed Paths

| Purpose | Path |
|---------|------|
| Obsidian Vault | `~/.claude\memory\` |
| Cleanup Log | `~/.claude\memory\System\cleanup-log.md` |
| Archive | `~/.claude\memory\System\Archive\` |

## Organization Rules

### 1. 10-Folder-Per-Tier Limit

**Enforcement:**
```
Claude/
├── Patterns/          [Max 10 folders] ← Archive oldest if >10
├── Decisions/         [Max 10 folders]
├── Preferences/       [Max 10 folders]
├── Skills-Learned/    [Max 10 folders]
└── Projects/
    ├── your organization/          [Max 10 folders]
    ├── your org/          [Max 10 folders]
    └── an LMS/          [Max 10 folders]
```

**If limit exceeded:**
1. Sort by last-modified date
2. Move oldest to `System/Archive/YYYY-MM-DD/`
3. Keep most recent 10

### 2. Consolidation Rules

**Merge if:**
- Same topic, different dates → Combine into single note with timeline
- Duplicate learning → Keep most detailed, archive rest
- Superseded decision → Archive old, mark new as "Replaces: [[old-note]]"

**Example consolidation:**
```markdown
Before:
- your CRM-Pagination-2026-01-10.md
- your CRM-Pagination-2026-01-12.md

After:
- your CRM-Pagination.md
  ## History
  - 2026-01-10: Initial discovery
  - 2026-01-12: Refined pattern
```

### 3. Archival Rules

**Archive if:**
- Note older than 90 days AND not referenced by other notes
- Tagged `#deprecated` or `#superseded`
- Empty or placeholder notes

**Don't archive:**
- Core preferences (user style, communication)
- Active project notes (last modified <30 days)
- Notes with incoming wikilinks

### 4. ORPHAN DETECTION & HANDLING (v2.0)

**Orphans = notes with NO wiki embeds or graph connections**

**Detection:**
```python
# Run orphan detection script (O(n) fast version)
python scripts/detect-orphans-fast.py --action report

# Script scans for:
# - Notes with zero incoming wikilinks
# - Notes with zero outgoing wikilinks
# - Isolated nodes in graph view
```

**Auto-Actions:**

| Orphan Age | Action | Reason |
|------------|--------|--------|
| >90 days | Move to System/Archive/ | Likely obsolete |
| 30-90 days | Flag in index, report | Review needed |
| <30 days | Report only | May be in progress |

**Index Flagging:**
```json
// memory-index.json update
{
  "notes": {
    "Patterns/Old-Pattern.md": {
      "orphan": true,
      "orphan_detected": "2026-01-26T10:30:00Z",
      "age_days": 147
    }
  }
}
```

**Recall Exclusion:**
- Orphans flagged in index are EXCLUDED from memory recall
- Reduces recall time (skip disconnected notes)
- Improves recall relevance (focus on connected knowledge)

**Report Output:**
- Session/orphan-report.md
- Grouped by folder
- Sorted by age (oldest first)
- Includes recommendations

### 5. TAG VALIDATION (STRICT RULES v1.0)

**Every note MUST follow strict tag structure:**

```yaml
---
created: YYYY-MM-DDTHH:MM:SSZ
modified: YYYY-MM-DDTHH:MM:SSZ
project: meta|partner|org|lms
domain: ticketing|crm|memory-system|etc
type: decision|pattern|preference|skill-learned|project-note
tags: [folder-tag, software-tag-1, software-tag-2]
session: description
---
```

**TAG VALIDATION RULES:**

| Rule | Check | Auto-Fix |
|------|-------|----------|
| Tag 1 must be folder | `tags[0]` in [decisions, patterns, preferences, skills-learned, projects] | Infer from path |
| Tags 2-4 must be software | All remaining tags in valid software list | Remove invalid tags |
| Max 4 tags | `len(tags) <= 4` | Truncate to 4 |
| No empty tags | `len(tags) >= 1` | Add folder tag from path |
| No invalid tag types | No descriptive/action/version tags | Remove invalid tags |

**Valid Software Tags:**
- `ticketing` | `crm` | `catalog` | `bim` | `android`
- `git` | `netlify` | `playwright` | `supabase` | `gas`
- `python` | `memory-system` | `enforcement` | `leroy`

**Invalid Tags (REMOVE):**
- Descriptive: bulletproof, successful, critical, important
- Action: automation, validation, workflow, implementation
- Version: v5, v5.1, v5.2, v2
- Duplicate: hooks, patterns, preferences (use folder tag)
- Vague: meta-system, meta-architecture, user-expectations

**Auto-Fix Process:**
```python
def validate_and_fix_tags(note_path, tags):
    folder = get_folder_from_path(note_path)  # e.g., "Decisions" → "decisions"

    # Ensure folder tag is first
    if not tags or tags[0] != folder:
        tags.insert(0, folder)

    # Filter to valid software tags only (after folder tag)
    valid_software = ["ticketing", "crm", "catalog", "bim", "android",
                      "git", "netlify", "playwright", "supabase", "gas",
                      "python", "memory-system", "enforcement", "leroy"]

    clean_tags = [tags[0]]  # Keep folder tag
    for tag in tags[1:]:
        if tag in valid_software:
            clean_tags.append(tag)

    # Limit to 4 tags
    return clean_tags[:4]
```

**Report Invalid Tags:**
```markdown
## Tag Validation Report

### Fixed Automatically
- Decisions/Protocol-v5.md: [hooks, enforcement, v5] → [decisions, enforcement]
- Patterns/Hook-Pattern.md: [bulletproof, patterns] → [patterns]

### Manual Review Required
- Skills-Learned/Custom-Workflow.md: No valid software tags detected
```

## Cleanup Process

### Phase 1: Scan
```bash
# Count folders per tier
find memory/Claude/Patterns -maxdepth 1 -type d | wc -l

# Find old notes (>90 days, unreferenced)
find memory/Claude -name "*.md" -mtime +90

# Find duplicates (same topic, different date)
grep -r "^# " memory/Claude/ | sort | uniq -c | grep -v "^      1"

# ORPHAN DETECTION (fast O(n) version)
python scripts/detect-orphans-fast.py --action report

# Orphan detection identifies notes with:
# - NO incoming wikilinks (no other notes link to this note)
# - NO outgoing wikilinks (this note doesn't link to others)
# - NO graph connections (isolated nodes)
#
# Output: session/orphan-report.md
# Updates: memory-index.json (flags orphans)
```

### Phase 2: Analyze
```markdown
Findings:
- Patterns/ has 14 folders → Need to archive 4 oldest
- 8 notes older than 90 days with no references
- 3 duplicate notes on "your CRM Pagination"
```

### Phase 3: Execute
```bash
# Archive excess folders
mv memory/Claude/Patterns/oldest-1 System/Archive/2026-01-13/
mv memory/Claude/Patterns/oldest-2 System/Archive/2026-01-13/
...

# Consolidate duplicates
# (Manual merge of content, keep best version)

# Update tags
# (Add missing frontmatter)
```

### Phase 4: Report

**To cleanup-log.md:**
```markdown
# Cleanup 2026-01-13

## Actions Taken
- Archived 4 old patterns to System/Archive/2026-01-13/
- Consolidated 3 duplicate notes on your CRM Pagination
- Added missing tags to 7 notes
- Fixed 2 broken wikilinks

## Stats
- Total notes: 87
- Folders per tier: 8 (Patterns), 6 (Decisions), 4 (Preferences)
- Archive size: 23 notes
- Next cleanup: 2026-01-20
```

**To user (if significant):**
```
[MEMORY CLEANUP] Organized vault:
• Archived 4 old patterns
• Consolidated 3 duplicates
• All tiers under 10-folder limit
Full log: memory/System/cleanup-log.md
```

## Cleanup Metrics

Track in `System/cleanup-log.md`:
- Total notes (target: <200)
- Folders per tier (limit: 10)
- Archive size (grows over time)
- Broken links found/fixed
- Duplicates consolidated

## Error Handling

**If vault corrupted:**
1. Log error to cleanup-log.md
2. Skip cleanup this week
3. Alert user to manual review

**If 10-folder limit can't be met:**
1. Archive down to 8 folders (leave buffer)
2. If still over, consolidate aggressively
3. Alert user if still over after consolidation

## Integration Points

**Called By:**
- `routines/morning.md` → on Monday if `last_cleanup > 7 days`

**Calls:**
- Filesystem operations (Bash, Read, Write, Edit)
- No external dependencies

## Performance

**Scan time:**
- <100 notes: <5s
- 100-200 notes: <10s
- 200+ notes: Alert user to manual pruning

**Background execution:**
- Spawned as agent, user continues working
- Results logged, surface only if action needed

## Safety

**Before any deletion:**
1. Copy to System/Archive/ with timestamp
2. Never permanently delete
3. Keep archive indefinitely (user can prune manually)

**Consolidation:**
- Merge content, don't discard
- Preserve all history sections
- Update wikilinks to point to consolidated note

---

## Vault Audit Checklist

Run these steps IN ORDER during every memory vault audit:

### Step 1 — Orphan Detection
```bash
cd ~/.claude
python scripts/detect-orphans-fast.py --action report
```
Read: `session/orphan-report.md`
Fix: Connect orphans to hub notes. Target: 0 isolated nodes.

### Step 2 — Empty Tags Repair
```bash
python scripts/infer-empty-tags.py
```
Infers tags from file path for any `tags: []` files. Auto-rebuilds index.

### Step 3 — Tag Governance Enforcement
```bash
python scripts/batch-tag-repair.py
```
Enforces 4-tag max. Skips empty tags (handled by Step 2).

### Step 4 — Full Index Rebuild
```bash
python scripts/build-memory-index.py
```
Verify output: total indexed == total .md files in vault.

### Step 5 — Duplicate Detection
Check for same filename in multiple folders.
Diff divergent copies. Keep Projects/ over Skills-Learned/ for active project content.
Keep newer `updated:` date as canonical.

### Step 6 — Sidecar Start + Reindex
```bash
# Check if running
curl -s http://localhost:7742/status

# If not ready, start it (background)
start /B python tools/vault-rag-sidecar.py

# After cleanup, always force full reindex
curl -s -X POST http://localhost:7742/reindex
```
Wait for status to return `"status": "ready"` before declaring audit complete.

### Pass Criteria
- Orphans: 0
- Empty tags: 0
- Index coverage: total indexed == total .md files
- Sidecar: status = ready
- MEMORY.md: under 200 lines

---

## Auto-Archive Unused Growth Agent Skills

**When:** Monday cleanup (weekly)
**What:** Scan for auto-generated skills that nobody uses

1. Scan all `.md` files in `skills/` (recursive) for frontmatter containing `generated_by: growth-agent`
2. For each found:
   - Check `usage_count` in frontmatter (default 0 if missing)
   - Check `generated_at` date
   - If `usage_count == 0` AND age > 30 days:
     - Move to `memory/System/Archive/growth-agent/{YYYY-MM-DD}/`
     - Log: "Archived unused growth skill: {filename} (generated {date}, 0 uses in 30 days)"
3. Also scan `skills/quarantine/` for files older than 30 days:
   - Archive regardless of usage count (quarantine = temporary holding)
   - Log: "Archived quarantined skill: {filename} (quarantined {date})"
4. Write count to cleanup log: "Growth agent cleanup: {N} skills archived, {M} quarantined archived"

---

*Auto-triggered background agent | Runs weekly | v3.0 (Vault Audit Checklist rewritten 2026-02-24)*
