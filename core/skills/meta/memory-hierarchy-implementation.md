# Memory Hierarchy Implementation Plan v1.0

> **Purpose:** Step-by-step rollout plan for Memory Hierarchy System
> **Design Reference:** `memory/Patterns/Memory-Hierarchy-System-v1.0.md`
> **Status:** Implementation Guide
> **Timeline:** 4 phases over 2-3 weeks

---

## Overview

Deploy memory hierarchy system to enable version tracking, supersession, and automatic prioritization in memory recall. System must remain backward compatible with existing 775+ notes.

---

## Phase 1: Metadata Schema + Validation (Week 1)

**Goal:** Add hierarchy metadata support without breaking existing notes.

**Duration:** 2-3 days

**Tasks:**

### Task 1.1: Update Tag Whitelist

Add `hierarchy` as reserved frontmatter field.

**File:** `.claude/session/tag-whitelist.json`

**Changes:**
```json
{
  "version": "1.1",
  "reserved_fields": [
    "created", "modified", "project", "domain", "type", "tags",
    "related", "session", "session_id", "session_window",
    "consolidated_at",
    "hierarchy"  // NEW
  ],
  "hierarchy_statuses": ["active", "superseded", "archived"]  // NEW
}
```

### Task 1.2: Create Hierarchy Validator

**File:** `scripts/validate_hierarchy.py`

**Function:**
```python
def validate_hierarchy_metadata(hierarchy):
    """
    Validate hierarchy frontmatter field.

    Args:
        hierarchy: Dict from frontmatter (or None)

    Returns:
        (is_valid: bool, errors: list)
    """
    if hierarchy is None:
        # Optional field - absence is valid
        return True, []

    errors = []

    # Validate status
    valid_statuses = ["active", "superseded", "archived"]
    status = hierarchy.get("status")
    if status and status not in valid_statuses:
        errors.append(f"Invalid status '{status}'. Must be one of: {valid_statuses}")

    # Validate version format (if present)
    version = hierarchy.get("version")
    if version:
        import re
        if not re.match(r'v\d+\.\d+', version):
            errors.append(f"Invalid version '{version}'. Expected format: v1.0, v2.1, etc.")

    # Validate supersedes is array of wikilinks
    supersedes = hierarchy.get("supersedes")
    if supersedes:
        if not isinstance(supersedes, list):
            errors.append("supersedes must be an array")
        else:
            for link in supersedes:
                if not re.match(r'\[\[.+\]\]', link):
                    errors.append(f"Invalid wikilink in supersedes: {link}")

    # Validate superseded_by is single wikilink or null
    superseded_by = hierarchy.get("superseded_by")
    if superseded_by:
        if superseded_by != "null" and not re.match(r'\[\[.+\]\]', superseded_by):
            errors.append(f"Invalid wikilink in superseded_by: {superseded_by}")

    # Validate effective_date format
    effective_date = hierarchy.get("effective_date")
    if effective_date:
        if not re.match(r'\d{4}-\d{2}-\d{2}', effective_date):
            errors.append(f"Invalid effective_date '{effective_date}'. Expected: YYYY-MM-DD")

    return len(errors) == 0, errors
```

**Integration:** Called during memory consolidation before writing notes.

### Task 1.3: Update Memory Consolidation

**File:** `skills/meta/memory-consolidation.md`

**Add section after "Write Structured Notes":**

```markdown
### 5.5. Add Hierarchy Metadata (If Versioned Document)

**OPTIONAL:** If writing a versioned document (supersedes previous version).

**Detection Pattern:**
- Title contains version number (v1.0, v2.0, etc.)
- Prompt mentions "update", "new version", "supersede"
- Session context shows evolution of existing note

**Add hierarchy block:**
```yaml
hierarchy:
  status: active
  version: v2.0
  supersedes:
    - "[[Previous Version Title v1.0]]"
  superseded_by: null
  changelog: "Brief description of what changed"
  effective_date: 2026-02-02
```

**Auto-update older version:**
When writing a note with `supersedes` field:
1. Load the superseded note(s) from vault
2. Update their frontmatter:
   ```yaml
   hierarchy:
     status: superseded
     superseded_by: "[[New Version Title v2.0]]"
   ```
3. Save updated frontmatter
4. Continue with new note creation

**Validation:**
```python
# Before writing note
hierarchy = frontmatter.get("hierarchy")
if hierarchy:
    is_valid, errors = validate_hierarchy_metadata(hierarchy)
    if not is_valid:
        log_rejection(errors, "Invalid hierarchy metadata")
        continue  # Skip this note
```
```

### Task 1.4: Testing

**Test Cases:**

1. **Create note without hierarchy** - Should work normally
2. **Create note with valid hierarchy** - Should validate and write
3. **Create note with invalid status** - Should reject with error
4. **Create note with invalid wikilink** - Should reject with error
5. **Create note superseding another** - Should auto-update old note

**Success Criteria:**
- All test cases pass
- No existing notes broken
- Validation logs to memory-rejections.log

---

## Phase 2: Memory Recall Enhancement (Week 1-2)

**Goal:** Prioritize active notes over superseded/archived in recall.

**Duration:** 2-3 days

**Tasks:**

### Task 2.1: Update Relevance Scoring

**File:** `skills/meta/memory-recall.md`

**Add new pass after "Pass 5: Relevance Scoring":**

```markdown
### Pass 6: Hierarchy Status Adjustment (NEW v4.0)

**Apply status multiplier to final scores**

Expected effect: Active notes score 3-10x higher than superseded/archived

```python
def apply_hierarchy_multiplier(notes):
    """
    Adjust relevance scores based on hierarchy status.

    Args:
        notes: List of notes with relevance_score already computed

    Returns:
        List of notes with adjusted scores
    """
    status_multipliers = {
        "active": 1.0,      # No adjustment
        "superseded": 0.3,  # 30% of original score
        "archived": 0.1     # 10% of original score
    }

    for note in notes:
        # Default to active if no hierarchy metadata
        hierarchy = note.get("hierarchy", {})
        status = hierarchy.get("status", "active")

        # Apply multiplier
        multiplier = status_multipliers.get(status, 1.0)
        note["relevance_score"] *= multiplier

        # Add flag for output formatting
        note["_hierarchy_status"] = status

    # Re-sort by adjusted scores
    return sorted(notes, key=lambda n: n["relevance_score"], reverse=True)
```

**Integration point:**
```python
# After Pass 5 (original relevance scoring)
ranked_notes = score_relevance(notes, context)

# NEW Pass 6: Apply hierarchy multiplier
ranked_notes = apply_hierarchy_multiplier(ranked_notes)

# Continue with tiered loading
tier1 = ranked_notes[:5]
```
```

### Task 2.2: Add Status Indicators to Output

**File:** `skills/meta/memory-recall.md`

**Update output format in "Output Formats" section:**

```markdown
### On Successful Recall (v4.0 with Hierarchy)

```markdown
[MEMORY] Loaded 5 relevant notes (203ms):

1. **Protocol Enforcement v5.2** ✓ LATEST (Decision, 2026-01-13)
   User-friendly priority system for enforcement queue.
   File: Decisions/Protocol-Enforcement-v5.2.md

2. **Protocol Enforcement v5.1** ⚠️ SUPERSEDED → v5.2 (Decision, 2026-01-10)
   Command queue automation (replaced by v5.2 with better UX).
   File: Decisions/Protocol-Enforcement-v5.1.md
   → Upgrade available: [[Protocol Enforcement v5.2]]

3. **Memory Recall Gap** (Pattern, 2026-01-13)
   Consolidation working but recall never executed.
   File: Patterns/Memory-Recall-Gap.md

...
```

**Status indicator logic:**
```python
def format_status_indicator(note):
    """Generate status indicator for note title."""
    hierarchy = note.get("hierarchy", {})
    status = hierarchy.get("status", "active")

    if status == "active":
        # Check if this is explicitly versioned
        if hierarchy.get("version") or hierarchy.get("supersedes"):
            return "✓ LATEST"
        else:
            return ""  # Standard note, no indicator

    elif status == "superseded":
        superseded_by = hierarchy.get("superseded_by")
        if superseded_by:
            # Extract title from wikilink
            newer_title = superseded_by.strip("[]")
            return f"⚠️ SUPERSEDED → {newer_title}"
        else:
            return "⚠️ SUPERSEDED"

    elif status == "archived":
        return "📦 ARCHIVED"

    return ""
```
```

### Task 2.3: Implement Supersession Chain Following

**File:** `scripts/memory_recall_helpers.py` (new file)

```python
def follow_supersession_chain(note_path, index, max_depth=10):
    """
    Follow superseded_by links to find latest version.

    Args:
        note_path: Starting note path
        index: Memory index data
        max_depth: Max chain depth (prevent infinite loops)

    Returns:
        Path to latest version, or original if already latest
    """
    current_path = note_path
    depth = 0

    while depth < max_depth:
        note = find_note_in_index(index, current_path)
        if not note:
            break  # Note not found

        hierarchy = note.get("hierarchy", {})
        superseded_by = hierarchy.get("superseded_by")

        if not superseded_by or superseded_by == "null":
            # This is the latest version
            return current_path

        # Extract path from wikilink
        newer_path = resolve_wikilink_to_path(superseded_by, index)
        if not newer_path or newer_path == current_path:
            break  # Invalid link or loop detected

        current_path = newer_path
        depth += 1

    # Return current path (either latest or loop detected)
    return current_path


def check_for_upgrade(note_path, index):
    """
    Check if note has been superseded and offer upgrade.

    Args:
        note_path: Note to check
        index: Memory index data

    Returns:
        Dict with upgrade info or None
    """
    note = find_note_in_index(index, note_path)
    if not note:
        return None

    hierarchy = note.get("hierarchy", {})
    status = hierarchy.get("status")

    if status in ["superseded", "archived"]:
        latest_path = follow_supersession_chain(note_path, index)

        if latest_path != note_path:
            latest_note = find_note_in_index(index, latest_path)
            return {
                "upgrade_available": True,
                "current_status": status,
                "latest_path": latest_path,
                "latest_title": latest_note.get("title"),
                "changelog": hierarchy.get("changelog")
            }

    return None
```

**Integration into recall:**
```python
# After loading Tier 1 notes
for note in tier1_notes:
    upgrade_info = check_for_upgrade(note["path"], index)
    if upgrade_info:
        note["_upgrade_info"] = upgrade_info
```

### Task 2.4: Testing

**Test Cases:**

1. **Recall with mixed statuses** - Active scores higher than superseded
2. **Recall superseded note** - Shows upgrade banner
3. **Follow chain A→B→C** - Returns C as latest
4. **Handle circular chain** - Breaks at max_depth
5. **Recall archived note** - Shows 📦 ARCHIVED indicator

**Success Criteria:**
- Active notes appear first in Tier 1
- Superseded notes show upgrade links
- Chain following works correctly
- Performance overhead <15ms

---

## Phase 3: Migration Tooling (Week 2)

**Goal:** Create script to add hierarchy metadata to existing notes.

**Duration:** 1-2 days

**Tasks:**

### Task 3.1: Create Migration Script

**File:** `scripts/migrate_memory_hierarchy.py`

**Full implementation:**

```python
#!/usr/bin/env python3
"""
Migrate existing memory notes to add hierarchy metadata.

Usage:
    python migrate_memory_hierarchy.py --scan     # Dry run, report only
    python migrate_memory_hierarchy.py --migrate  # Apply changes
    python migrate_memory_hierarchy.py --auto     # Auto-detect supersession
"""

import os
import re
import json
from pathlib import Path
from datetime import datetime
import yaml

VAULT_PATH = Path.home() / ".claude" / "memory"

def load_note(path):
    """Load note and parse frontmatter."""
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Split frontmatter
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            frontmatter_str = parts[1]
            body = parts[2].strip()
            frontmatter = yaml.safe_load(frontmatter_str)
            return frontmatter, body

    return {}, content


def save_note(path, frontmatter, body):
    """Save note with updated frontmatter."""
    frontmatter_str = yaml.dump(frontmatter, default_flow_style=False, sort_keys=False)
    content = f"---\n{frontmatter_str}---\n\n{body}"

    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)


def detect_version(title):
    """
    Extract version number from title.

    Returns: (version_str, base_title) or (None, title)
    """
    # Match patterns like "v1.0", "v2.5", "Version 3.0"
    patterns = [
        r'v(\d+\.\d+)',
        r'Version (\d+\.\d+)',
        r'\(v(\d+\.\d+)\)'
    ]

    for pattern in patterns:
        match = re.search(pattern, title, re.IGNORECASE)
        if match:
            version = f"v{match.group(1)}"
            # Remove version from title to get base
            base_title = re.sub(pattern, '', title, flags=re.IGNORECASE).strip()
            return version, base_title

    return None, title


def find_related_versions(note_path, all_notes):
    """
    Find other versions of the same note (same base title).

    Returns: List of (path, version, date) tuples
    """
    frontmatter, _ = load_note(note_path)
    title = extract_title_from_note(note_path)
    version, base_title = detect_version(title)

    if not version:
        return []  # Not a versioned document

    related = []
    for other_path in all_notes:
        if other_path == note_path:
            continue

        other_title = extract_title_from_note(other_path)
        other_version, other_base = detect_version(other_title)

        # Same base title?
        if other_base.lower() == base_title.lower() and other_version:
            other_frontmatter, _ = load_note(other_path)
            other_date = other_frontmatter.get("created", "")
            related.append((other_path, other_version, other_date))

    # Sort by version
    return sorted(related, key=lambda x: parse_version(x[1]))


def parse_version(version_str):
    """Convert v1.2 to (1, 2) for sorting."""
    match = re.match(r'v(\d+)\.(\d+)', version_str)
    if match:
        return (int(match.group(1)), int(match.group(2)))
    return (0, 0)


def extract_title_from_note(note_path):
    """Extract title from first # heading."""
    with open(note_path, 'r', encoding='utf-8') as f:
        content = f.read()

    for line in content.split('\n'):
        if line.startswith('# '):
            return line[2:].strip()

    # Fallback: filename
    return Path(note_path).stem


def auto_detect_supersession(note_path, all_notes):
    """
    Auto-detect if this note supersedes older versions.

    Returns: List of wikilinks to superseded notes
    """
    frontmatter, _ = load_note(note_path)
    created = frontmatter.get("created", "")
    title = extract_title_from_note(note_path)
    version, base_title = detect_version(title)

    if not version:
        return []  # Not versioned

    # Find older versions
    related = find_related_versions(note_path, all_notes)
    superseded = []

    current_ver = parse_version(version)

    for other_path, other_version, other_date in related:
        other_ver = parse_version(other_version)

        # Is other version older?
        if other_ver < current_ver:
            # Create wikilink
            other_title = extract_title_from_note(other_path)
            superseded.append(f"[[{other_title}]]")

    return superseded


def scan_vault(vault_path, auto_detect=False):
    """
    Scan vault and report hierarchy opportunities.

    Args:
        vault_path: Path to memory vault
        auto_detect: If True, auto-detect supersession relationships

    Returns:
        Dict with scan results
    """
    results = {
        "total_notes": 0,
        "notes_with_hierarchy": 0,
        "versioned_notes": 0,
        "supersession_candidates": [],
        "errors": []
    }

    all_notes = []
    for root, dirs, files in os.walk(vault_path):
        for file in files:
            if file.endswith('.md'):
                all_notes.append(Path(root) / file)

    results["total_notes"] = len(all_notes)

    for note_path in all_notes:
        try:
            frontmatter, _ = load_note(note_path)

            # Check if already has hierarchy
            if "hierarchy" in frontmatter:
                results["notes_with_hierarchy"] += 1
                continue

            # Check if versioned
            title = extract_title_from_note(note_path)
            version, base_title = detect_version(title)

            if version:
                results["versioned_notes"] += 1

                if auto_detect:
                    supersedes = auto_detect_supersession(note_path, all_notes)
                    if supersedes:
                        results["supersession_candidates"].append({
                            "path": str(note_path.relative_to(vault_path)),
                            "title": title,
                            "version": version,
                            "supersedes": supersedes
                        })

        except Exception as e:
            results["errors"].append({
                "path": str(note_path.relative_to(vault_path)),
                "error": str(e)
            })

    return results


def migrate_note(note_path, hierarchy_metadata, dry_run=False):
    """
    Add hierarchy metadata to note frontmatter.

    Args:
        note_path: Path to note file
        hierarchy_metadata: Dict with hierarchy fields
        dry_run: If True, don't save changes

    Returns:
        True if migrated, False if skipped/error
    """
    try:
        frontmatter, body = load_note(note_path)

        # Skip if already has hierarchy
        if "hierarchy" in frontmatter:
            return False

        # Add hierarchy
        frontmatter["hierarchy"] = hierarchy_metadata

        if not dry_run:
            save_note(note_path, frontmatter, body)

        return True

    except Exception as e:
        print(f"Error migrating {note_path}: {e}")
        return False


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Migrate memory notes to hierarchy system")
    parser.add_argument("--scan", action="store_true", help="Scan and report only")
    parser.add_argument("--auto", action="store_true", help="Auto-detect and migrate supersession")
    parser.add_argument("--migrate", action="store_true", help="Apply migrations")
    parser.add_argument("--dry-run", action="store_true", help="Show changes without saving")

    args = parser.parse_args()

    # Scan mode
    if args.scan or args.auto or args.dry_run:
        print("Scanning vault for hierarchy opportunities...")
        results = scan_vault(VAULT_PATH, auto_detect=args.auto)

        print(f"\n=== Scan Results ===")
        print(f"Total notes: {results['total_notes']}")
        print(f"Notes with hierarchy: {results['notes_with_hierarchy']}")
        print(f"Versioned notes: {results['versioned_notes']}")
        print(f"Supersession candidates: {len(results['supersession_candidates'])}")

        if results["supersession_candidates"]:
            print(f"\n=== Supersession Candidates ===")
            for candidate in results["supersession_candidates"]:
                print(f"\n{candidate['title']} ({candidate['version']})")
                print(f"  Path: {candidate['path']}")
                print(f"  Supersedes: {', '.join(candidate['supersedes'])}")

        if results["errors"]:
            print(f"\n=== Errors ({len(results['errors'])}) ===")
            for error in results["errors"]:
                print(f"  {error['path']}: {error['error']}")

        # Save report
        report_path = Path.home() / ".claude" / "session" / "hierarchy-migration-report.json"
        with open(report_path, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\nReport saved to: {report_path}")

    # Migrate mode
    if args.migrate or args.auto:
        if args.auto:
            print("\n=== Auto-Migration ===")
            results = scan_vault(VAULT_PATH, auto_detect=True)

            migrated = 0
            for candidate in results["supersession_candidates"]:
                note_path = VAULT_PATH / candidate["path"]

                hierarchy = {
                    "status": "active",
                    "version": candidate["version"],
                    "supersedes": candidate["supersedes"],
                    "superseded_by": None,
                    "changelog": "Auto-detected supersession relationship",
                    "effective_date": datetime.now().strftime("%Y-%m-%d")
                }

                if migrate_note(note_path, hierarchy, dry_run=args.dry_run):
                    migrated += 1
                    action = "Would migrate" if args.dry_run else "Migrated"
                    print(f"{action}: {candidate['title']}")

            print(f"\nTotal migrated: {migrated}")

        else:
            print("Manual migration not yet implemented.")
            print("Use --auto to auto-detect supersession relationships.")


if __name__ == "__main__":
    main()
```

### Task 3.2: Testing Migration Script

**Test Cases:**

1. **Scan without changes** - Report generation
2. **Auto-detect versioned notes** - Find v1.0, v2.0 chains
3. **Dry run migration** - No file modifications
4. **Live migration** - Updates frontmatter correctly
5. **Error handling** - Corrupted frontmatter doesn't break script

**Success Criteria:**
- Scan completes in <30 sec for 775 notes
- Auto-detection finds version chains accurately
- Migration adds valid hierarchy metadata
- No data loss or corruption

---

## Phase 4: Integration & Rollout (Week 2-3)

**Goal:** Integrate hierarchy system into production workflows.

**Duration:** 2-3 days

**Tasks:**

### Task 4.1: Update Memory Consolidation Skill

**File:** `skills/meta/memory-consolidation.md`

**Add automatic hierarchy for new versions:**

```python
def should_add_hierarchy(note_data, memory_index):
    """
    Determine if new note should have hierarchy metadata.

    Criteria:
    - Title contains version (v1.0, v2.0, etc.)
    - Prompt mentions "update", "new version", "replace"
    - Similar note exists in vault (same base title)

    Returns: hierarchy dict or None
    """
    title = note_data["title"]
    version, base_title = detect_version(title)

    if not version:
        return None  # Not versioned

    # Search for older versions
    candidates = find_notes_by_base_title(base_title, memory_index)

    if candidates:
        # Create hierarchy with supersession
        supersedes = [f"[[{c['title']}]]" for c in candidates]

        return {
            "status": "active",
            "version": version,
            "supersedes": supersedes,
            "superseded_by": None,
            "changelog": extract_changelog_from_prompt(),
            "effective_date": datetime.now().strftime("%Y-%m-%d")
        }

    # Versioned but no predecessors - still add hierarchy
    return {
        "status": "active",
        "version": version,
        "supersedes": [],
        "superseded_by": None,
        "effective_date": datetime.now().strftime("%Y-%m-%d")
    }
```

### Task 4.2: Update Index Builder

**File:** `scripts/build-memory-index.py`

**Add hierarchy metadata to index:**

```python
# After extracting frontmatter
hierarchy = frontmatter.get("hierarchy", {})

note_metadata["hierarchy_index"] = {
    "status": hierarchy.get("status", "active"),
    "has_version": bool(hierarchy.get("version")),
    "supersedes_count": len(hierarchy.get("supersedes", [])),
    "has_newer": bool(hierarchy.get("superseded_by"))
}
```

### Task 4.3: Documentation Updates

**Files to update:**

1. **CLAUDE.md** - Add hierarchy system to Memory section
2. **memory-system-overview.md** - Add hierarchy reference
3. **memory-tag-governance.md** - Add hierarchy field to reserved fields

**Add to CLAUDE.md:**

```markdown
## Memory Hierarchy (v4.0)

**Purpose:** Track document evolution and prioritize latest versions.

**Status Types:**
- `active` - Current version (default)
- `superseded` - Replaced by newer version
- `archived` - Historical reference only

**Recall Behavior:**
- Active notes score 3-10x higher than superseded/archived
- Superseded notes show upgrade links
- Status indicators: ✓ LATEST, ⚠️ SUPERSEDED, 📦 ARCHIVED

**See:** `memory/Patterns/Memory-Hierarchy-System-v1.0.md` for full design
```

### Task 4.4: Production Deployment

**Deployment Checklist:**

- [ ] All validation scripts pass
- [ ] Migration script tested on dev vault
- [ ] Memory recall updated and tested
- [ ] Memory consolidation updated and tested
- [ ] Documentation updated
- [ ] Backup vault before migration
- [ ] Run migration script on production vault
- [ ] Rebuild memory index
- [ ] Test recall with mixed statuses
- [ ] Verify backward compatibility

**Rollback Plan:**

If issues occur:
1. Restore vault from backup
2. Rollback memory-recall.md changes
3. Rollback memory-consolidation.md changes
4. Keep validation scripts (no harm)

---

## Timeline Summary

| Phase | Duration | Tasks |
|-------|----------|-------|
| **Phase 1: Schema + Validation** | 2-3 days | Validator, consolidation updates, testing |
| **Phase 2: Recall Enhancement** | 2-3 days | Scoring, indicators, chain following |
| **Phase 3: Migration Tooling** | 1-2 days | Script creation, testing, dry runs |
| **Phase 4: Integration** | 2-3 days | Consolidation, index, docs, deployment |
| **Total** | 7-11 days | Full system operational |

---

## Success Metrics

### Functional Metrics

- [ ] 100% backward compatibility (notes without hierarchy work)
- [ ] Active notes score higher than superseded in recall
- [ ] Superseded notes show upgrade links
- [ ] Migration script handles 775+ notes without errors
- [ ] No data loss during migration

### Performance Metrics

- [ ] Recall overhead <15ms (target: 203ms vs 187ms baseline)
- [ ] Index rebuild <10 sec for 10K notes
- [ ] Migration script <60 sec for 1K notes
- [ ] Chain following <5ms per chain

### User Experience Metrics

- [ ] Clear status indicators in recall output
- [ ] Automatic supersession detection works
- [ ] No manual intervention for basic use
- [ ] Evolution tracking visible and useful

---

## Risk Mitigation

### Risk 1: Data Corruption During Migration

**Mitigation:**
- Backup vault before migration
- Dry-run mode in migration script
- Validation before saving each note
- Rollback plan ready

### Risk 2: Performance Degradation

**Mitigation:**
- Benchmark before/after
- Target <15ms overhead
- Pre-compute hierarchy metadata in index
- Lazy loading of chain following

### Risk 3: User Confusion

**Mitigation:**
- Clear status indicators (✓ ⚠️ 📦)
- Upgrade links in output
- Documentation in CLAUDE.md
- Examples in design doc

### Risk 4: Backward Compatibility Break

**Mitigation:**
- All hierarchy fields optional
- Default to active status
- Existing notes work unchanged
- Extensive testing before rollout

---

## Maintenance & Support

### Weekly Cleanup

Add to `skills/meta/memory-organizer.md`:

```markdown
### Check Hierarchy Consistency

Weekly maintenance task:

1. Scan for orphaned supersession links (link to non-existent note)
2. Detect circular supersession chains (A→B→A)
3. Find notes with superseded status but no superseded_by field
4. Report inconsistencies for manual review
```

### Monitoring

Track in metrics:

```python
log_event("hierarchy_usage",
    active_count=count_by_status["active"],
    superseded_count=count_by_status["superseded"],
    archived_count=count_by_status["archived"],
    chain_depth_avg=avg_chain_depth
)
```

---

**Implementation Version:** 1.0
**Status:** Ready for Phase 1
**Author:** Claude Sonnet 4.5
**Date:** 2026-02-02
