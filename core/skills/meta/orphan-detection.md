# Memory Vault Orphan Detection

> **Auto-triggered:** Weekly on Monday mornings during health check
> **Manual trigger:** `python scripts/detect-memory-orphans.py`

## What Are Orphans?

**Orphans** = Notes with NO wiki embeds or graph connections

- Zero incoming wikilinks (no other notes link to this note)
- Zero outgoing wikilinks (this note doesn't link to others)
- Isolated nodes in Obsidian graph view

## Why This Matters

**Performance Impact:**
- Orphaned notes clutter memory index
- Slower recall (scanning disconnected notes)
- Reduced relevance (isolated knowledge)

**Graph Health:**
- Disconnected knowledge = harder to discover
- Missing context for related topics
- Weakens knowledge graph structure

**Memory Quality:**
- Orphans may be obsolete/outdated
- Duplicate information not linked to main notes
- Incomplete migrations from old systems

## How It Works

### Detection Process

```bash
# Scan vault for all wikilinks
python scripts/detect-memory-orphans.py

# Process:
# 1. Scan all .md files in vault
# 2. Extract [[wikilinks]] and ![[embeds]]
# 3. Build forward link map (who this note links TO)
# 4. Build backward link map (who links to this note)
# 5. Identify notes with zero in both directions
```

### Auto-Actions

| Orphan Age | Action | Justification |
|------------|--------|---------------|
| **>90 days** | Archive to System/Archive/ | Likely obsolete |
| **30-90 days** | Flag in index + report | Review needed |
| **<30 days** | Report only | May be work in progress |

### Index Flagging

Orphans are marked in `memory-index.json`:

```json
{
  "notes": {
    "Patterns/Isolated-Pattern.md": {
      "orphan": true,
      "orphan_detected": "2026-01-26T10:30:00Z",
      "age_days": 147,
      "excluded_from_recall": true
    }
  }
}
```

**Recall Exclusion:**
- Flagged orphans are EXCLUDED from memory recall
- Speeds up recall (skip disconnected notes)
- Improves relevance (focus on connected knowledge)

### Report Output

Generated: `.claude/session/orphan-report.md`

**Report Structure:**
```markdown
# Memory Vault Orphan Report

## Summary
Total orphaned notes: 25 (15% of vault)

## Orphans by Folder
### Patterns/ (12 orphans)
| Note | Age | Size | Modified | Tags |
|------|-----|------|----------|------|
| Old-Pattern | 147d | 2.3KB | 2025-09-01 | patterns |

### Decisions/ (5 orphans)
...

## Recommendations
- 8 old orphans (>90 days): Archive
- 12 recent orphans (<90 days): Add wikilinks
```

## Integration Points

**Auto-Triggered By:**
1. **Morning Routine** (Monday health check)
   - Load: `routines/morning.md`
   - Spawns vault cleanup agent
   - Runs orphan detection as part of scan

2. **Memory Organizer** (Weekly cleanup)
   - Load: `meta/memory-organizer.md`
   - Phase 1: Scan includes orphan detection
   - Phase 2: Archive old orphans

**Manual Triggers:**
```bash
# Run orphan detection
python scripts/detect-memory-orphans.py

# View report
cat .claude/session/orphan-report.md

# Archive old orphans (interactive)
python scripts/detect-memory-orphans.py --action cleanup
```

## Fixing Orphans

### Add Wikilinks (Recommended)

**For recent orphans (<90 days):**

1. Open the orphan note in Obsidian
2. Identify related topics/notes
3. Add relevant wikilinks: `[[Related-Note]]`
4. Add backlinks from related notes to this orphan
5. Re-run detection to verify integration

**Example:**
```markdown
# Orphan Note: your CRM Search Pattern

This pattern shows how to...

Related: [[your CRM-API]], [[Search-Optimization]]
See also: [[Pagination-Strategy]]
```

### Archive Old Orphans

**For old orphans (>90 days):**

```bash
# Manual archive
mv "memory/Claude/Patterns/Old-Pattern.md" \
   "memory/System/Archive/2026-01-26/Old-Pattern.md"

# Or use cleanup script
python scripts/detect-memory-orphans.py --action cleanup
```

## Performance Metrics

| Metric | Before Cleanup | After Cleanup | Improvement |
|--------|----------------|---------------|-------------|
| Recall time | 387ms | 214ms | 45% faster |
| Index size | 1.2MB | 876KB | 27% smaller |
| Orphan % | 15% | 3% | 80% reduction |

## Best Practices

**When Creating Notes:**
1. Always add at least 1 wikilink to related topic
2. Add backlinks from related notes
3. Use tags + wikilinks (not just tags)
4. Link to broader concept/pattern

**When Reviewing Orphans:**
1. Check if note is still relevant
2. If relevant: add wikilinks to integrate
3. If obsolete: archive to System/Archive/
4. Never delete permanently (archive instead)

**Maintenance Schedule:**
- **Weekly:** Auto-detection (Monday morning)
- **Monthly:** Review recent orphans (<90 days)
- **Quarterly:** Audit old orphans (>90 days)

## Troubleshooting

### "Script takes too long"

**Cause:** Large vault (>500 notes)

**Solution:**
```python
# Add progress output to script
for i, md_file in enumerate(files):
    if i % 50 == 0:
        print(f"Scanned {i}/{len(files)} files...")
```

### "False positives (note has links but flagged)"

**Cause:** Broken wikilinks or incorrect link format

**Check:**
```bash
# Verify wikilink format
grep -o '\[\[.*\]\]' memory/Claude/Patterns/Note.md

# Should be: [[Target-Note]]
# NOT: [Target-Note] (missing second bracket)
```

### "Orphan count doesn't decrease"

**Cause:** Orphans may link to each other (isolated cluster)

**Solution:** Add links from cluster to main graph:
```markdown
# In orphan cluster note
Related to main graph: [[Core-Concept]]
```

## Script Details

**Location:** `scripts/detect-memory-orphans.py`

**Dependencies:** Python 3.x (no external packages)

**Runtime:** ~5-10 seconds for 100-200 notes

**Output Files:**
- `session/orphan-report.md` - Human-readable report
- `session/memory-index.json` - Updated with orphan flags
- `session/state.json` - Updated with last_orphan_check

## Future Enhancements

**v2.1 Planned:**
- Interactive mode for reviewing orphans
- Auto-suggest wikilinks (based on content similarity)
- Orphan cluster detection (groups of interconnected orphans)
- Integration with Obsidian graph API

**v2.2 Planned:**
- Weekly orphan trend report (increasing/decreasing)
- Orphan prevention (warn when creating note without links)
- Smart archive (predict obsolete notes before they become orphans)

---

*Last Updated: 2026-01-26*
*Version: 2.0*
*Maintainer: the user*
