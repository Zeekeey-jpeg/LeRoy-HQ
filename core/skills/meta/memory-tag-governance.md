---
user-invocable: false
---

# Memory Tag Governance v1.0

**Purpose:** Document tag rules, rationale, and enforcement

**When to Use:** Before consolidating memory or when validating vault organization

**Critical Rule:** Tags are NOT for description - they're for O(1) lookup performance

---

## Tag Structure (MANDATORY)

### Tag 1: Folder Tag (REQUIRED)

**Must be ONE of:**
- `decisions` - Architectural decisions, protocol choices
- `patterns` - System patterns, workflows, architectures
- `preferences` - User preferences, rules, standards
- `skills-learned` - Learned capabilities, techniques, solutions
- `projects` - Project-specific documentation
- `error-solutions` - Error fixes, incidents, resolutions

**Purpose:** Map note to vault folder structure

**Example:**
```yaml
tags: [decisions, PSA tool, CRM]
      ^^^^^^^^^
      Folder tag (required)
```

### Tags 2-4: Software Tags (OPTIONAL)

**Valid Software/Integration Tags:**
```
PSA tool | CRM | product catalog tool | BIM tool | android
git | netlify | playwright | supabase | gas
python | memory-system | enforcement | leroy
cyber | tryhackme | hackthebox | burpsuite | portswigger | poker
```

**Purpose:** Enable O(1) tag intersection lookups (software-specific queries)

**Example:**
```yaml
tags: [patterns, memory-system, enforcement]
                ^^^^^^^^^^^^^  ^^^^^^^^^^^
                Software tags (optional)
```

### Maximum: 4 Tags Total

**Rule:** 1 folder tag + up to 3 software tags = MAX 4 tags

**Why:** Performance optimization - tag intersection index precomputes 2-3 tag combinations only

---

## INVALID Tags (NEVER Use)

### Category 1: Descriptive Tags ❌

**Examples:**
- `bulletproof` - Describes quality, not software
- `successful` - Describes outcome, not software
- `critical` - Describes importance, not software
- `important` - Describes priority, not software

**Why Invalid:** Descriptive tags don't enable filtering by software/domain

### Category 2: Action Tags ❌

**Examples:**
- `automation` - Describes what it does, not software used
- `validation` - Describes action, not software
- `workflow` - Describes type, not software
- `implementation` - Describes phase, not software

**Why Invalid:** Action tags duplicate folder tags and don't add filtering value

### Category 3: Version Tags ❌

**Examples:**
- `v5` - Version belongs in title/content, not tags
- `v5.1` - Same as above
- `v5.2` - Same as above
- `evolution` - Describes change process, not software

**Why Invalid:** Versions make tags non-permanent, break tag intersection index

### Category 4: Duplicate Tags ❌

**Examples:**
- `hooks` - Redundant with folder tag `patterns`
- `patterns` - Already the folder tag
- `decisions` - Already the folder tag
- `memory` - Too broad, use `memory-system` instead

**Why Invalid:** Duplicates folder tag without adding filtering value

---

## Why These Rules Exist

### Reason 1: O(1) Tag Intersection Lookups

**Problem Without Rules:**
```
Query: "Show me memory system patterns"
Process: Scan all 558 notes, keyword match "memory", keyword match "patterns"
Time: ~500ms (too slow)
```

**Solution With Rules:**
```
Query: "Show me memory system patterns"
Process: Lookup precomputed index for tags=[patterns, memory-system]
Time: <1ms (O(1) lookup)
```

**How It Works:**
- Index precomputes all 2-3 tag combinations
- Tags are fixed (software/integration names)
- Query maps to precomputed index key
- Instant lookup, no scanning

### Reason 2: Predictable Filtering

**With Structured Tags:**
```python
# Find all PSA tool decisions
notes = index["decisions"]["PSA tool"]  # O(1)
```

**Without Structured Tags:**
```python
# Find all "automation" notes (meaningless - what software?)
notes = scan_all_notes_for_keyword("automation")  # O(n)
```

### Reason 3: Tag Permanence

**Good (Permanent):**
```yaml
tags: [decisions, PSA tool]  # PSA tool will always exist
```

**Bad (Temporary):**
```yaml
tags: [decisions, v5.1]  # v5.1 is obsolete when v5.2 ships
```

**Why:** Tags in precomputed index must be stable across versions

### Reason 4: Semantic Precision

**Software Tags:**
- Precisely identify which systems are involved
- Enable "show me all CRM notes" queries
- Support multi-system filtering (e.g., "PSA tool + CRM")

**Descriptive Tags:**
- Subjective ("important" to whom?)
- Non-actionable (can't filter by "bulletproof")
- Duplicate information (title/content already describes)

---

## Tag Validation Process

### Step 1: Check Folder Tag

**Question:** Does tag 1 match a folder name?

**Valid:**
```yaml
tags: [decisions, ...]  # ✅ Folder: Claude/Decisions/
tags: [patterns, ...]   # ✅ Folder: Claude/Patterns/
tags: [skills-learned, ...]  # ✅ Folder: Claude/Skills-Learned/
```

**Invalid:**
```yaml
tags: [automation, ...]  # ❌ No folder named "Automation"
tags: [v5.2, ...]        # ❌ No folder named "v5.2"
```

### Step 2: Check Software Tags

**Question:** Are tags 2-4 in the valid software list?

**Valid Software Tags:**
```
PSA tool | CRM | product catalog tool | BIM tool | android
git | netlify | playwright | supabase | gas
python | memory-system | enforcement | leroy
cyber | tryhackme | hackthebox | burpsuite | portswigger | poker
```

**Valid:**
```yaml
tags: [decisions, PSA tool, CRM]  # ✅ Both in valid list
```

**Invalid:**
```yaml
tags: [decisions, bulletproof]  # ❌ "bulletproof" not in valid list
tags: [patterns, automation]    # ❌ "automation" not in valid list
```

### Step 3: Check Tag Count

**Question:** Are there ≤4 tags total?

**Valid:**
```yaml
tags: [decisions]                              # ✅ 1 tag
tags: [patterns, memory-system]                # ✅ 2 tags
tags: [decisions, PSA tool, CRM]        # ✅ 3 tags
tags: [patterns, memory-system, enforcement, git]  # ✅ 4 tags
```

**Invalid:**
```yaml
tags: [decisions, cw, hs, product catalog tool, python]  # ❌ 5 tags (max 4)
```

### Step 4: Check for Duplicates

**Question:** Is folder tag repeated in software tags?

**Valid:**
```yaml
tags: [patterns, memory-system]  # ✅ "patterns" only once
```

**Invalid:**
```yaml
tags: [patterns, hooks, memory-system]  # ❌ "hooks" duplicates "patterns" meaning
tags: [decisions, decisions, cw]        # ❌ "decisions" duplicated
```

---

## Common Mistakes and Fixes

### Mistake 1: Missing Folder Tag

**Bad:**
```yaml
tags: [PSA tool, CRM]
```

**Fix:**
```yaml
tags: [decisions, PSA tool, CRM]  # Added folder tag
```

### Mistake 2: Descriptive Tags

**Bad:**
```yaml
tags: [decisions, bulletproof, successful]
```

**Fix:**
```yaml
tags: [decisions, enforcement]  # Replaced descriptive with software
```

### Mistake 3: Version Tags

**Bad:**
```yaml
tags: [patterns, v5.2, enforcement]
```

**Fix:**
```yaml
tags: [patterns, enforcement]  # Removed version
```

### Mistake 4: Too Many Tags

**Bad:**
```yaml
tags: [decisions, cw, hs, product catalog tool, git, python]
```

**Fix:**
```yaml
tags: [decisions, PSA tool, CRM]  # Kept top 3 most relevant
```

### Mistake 5: Empty Tags

**Bad:**
```yaml
tags: []
```

**Fix:**
```yaml
tags: [patterns]  # Added minimum required folder tag
```

---

## Enforcement Mechanisms

### Mechanism 1: Consolidation Validation

**When:** Memory consolidation skill runs

**Check:** Validates tags before writing note to vault

**Action on Invalid:**
- Log warning
- Attempt auto-correction (folder tag from file path)
- Create note with corrected tags

### Mechanism 2: Index Build Validation

**When:** `build-memory-index.py` runs

**Check:** Scans all vault notes for tag compliance

**Action on Invalid:**
- Log errors to console
- Skip invalid notes from index
- Report summary of tag violations

### Mechanism 3: Weekly Cleanup

**When:** Monday morning cleanup (memory-organizer.md)

**Check:** Full vault audit for tag violations

**Action on Invalid:**
- Generate report of violations
- Suggest corrections
- Optionally auto-fix common mistakes

### Mechanism 4: Manual Review

**When:** Before major vault operations

**Command:**
```bash
python scripts/validate-tags.py  # (future tool)
```

**Output:** List of violations with suggested fixes

---

## Adding New Valid Software Tags

### When to Add

**Valid Reasons:**
- New integration added (e.g., new MCP server)
- New major software dependency (e.g., new database)
- Recurring domain area (e.g., specific framework)

**Invalid Reasons:**
- Temporary project name
- Descriptive category
- Version identifier

### Addition Process

1. **Verify recurrence** - Will this tag be used on 10+ notes?
2. **Check uniqueness** - Does an existing tag cover this? (e.g., use "git" not "github")
3. **Add to valid list** - Update this document + CLAUDE.md
4. **Update index** - Rebuild tag intersection index
5. **Document** - Add to memory system documentation

**Example Addition:**
```
New integration: Salesforce MCP
Valid tag: "salesforce"
Usage: tags: [decisions, salesforce, CRM]
```

---

## Tag Intersection Index (Technical)

**Purpose:** Precompute common tag combinations for O(1) lookups

**Structure:**
```json
{
  "tag_intersections": {
    "decisions+PSA tool": [/* note IDs */],
    "patterns+memory-system": [/* note IDs */],
    "decisions+PSA tool+CRM": [/* note IDs */]
  }
}
```

**Query Example:**
```python
# Fast lookup:
notes = index["tag_intersections"]["patterns+memory-system"]

# Slow scan (without index):
notes = [n for n in all_notes
         if "patterns" in n.tags and "memory-system" in n.tags]
```

**Why It Works:**
- Only ~10-15 valid software tags
- Only precompute 2-3 tag combinations (manageable size)
- All queries map to precomputed keys
- O(1) lookup performance

**Why Descriptive Tags Break It:**
- Infinite descriptive possibilities ("important", "critical", "urgent", etc.)
- Can't precompute all combinations
- Falls back to O(n) scanning

---

## Validation Checklist

**Before Consolidating Memory:**

- [ ] Note has at least 1 tag (folder tag)
- [ ] Tag 1 is a valid folder tag
- [ ] Tags 2-4 are valid software tags (if present)
- [ ] Total tags ≤ 4
- [ ] No descriptive tags (bulletproof, critical, etc.)
- [ ] No action tags (automation, validation, etc.)
- [ ] No version tags (v5, v5.1, etc.)
- [ ] No duplicate tags

---

## Reference

**Tag Rules:** CLAUDE.md → Memory System v3.2 → Tag Rules section
**Valid Software Tags:** This document (line 33)
**Consolidation Skill:** `skills/meta/memory-consolidation.md`
**Index Builder:** `scripts/build-memory-index.py`
**Hierarchy System:** `memory/Patterns/Memory-Hierarchy-System-v1.0.md`

---

## Reserved Frontmatter Fields v1.1

**System Fields (Do Not Use for Tags):**
- `created`, `modified` - Timestamps
- `project`, `domain`, `type` - Classification
- `tags` - Tag array (governed by this document)
- `related` - Wikilinks array
- `session`, `session_id`, `session_window` - Session tracking
- `consolidated_at` - Consolidation timestamp
- **`hierarchy`** (NEW v1.1) - Version tracking and supersession

**Hierarchy Field Structure:**
```yaml
hierarchy:
  status: active | superseded | archived
  version: v1.0
  supersedes: [...]
  superseded_by: null | "[[Title]]"
  changelog: "..."
  effective_date: YYYY-MM-DD
```

**Validation:** All hierarchy metadata validated via `scripts/migrate_memory_hierarchy.py`

---

**Last Updated:** 2026-02-02
**Version:** 1.1 (Added hierarchy field)
**Status:** Reference Guide
