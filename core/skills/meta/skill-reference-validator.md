# Skill Reference Validator

**Trigger:** Run as part of health check or manually
**Version:** 1.0
**Created:** 2026-01-28

## Purpose

Automatically validates all skill references in CLAUDE.md to detect broken "See {path}" links and incorrect routing paths. Prevents accumulation of dead references over time.

## Quick Start

This skill is typically invoked as part of the system health check. For manual validation:

```
"validate skill references"
"check CLAUDE.md references"
"find broken skill links"
```

## Validation Logic

### Step 1: Extract References

Parse CLAUDE.md for all skill-like references:

**Patterns to Match:**
```regex
# Backtick paths
`(skills|routines|agents|workflows)/[^`]+\.md`

# "See" references
See `([^`]+)`

# Skill column in tables
\| [^|]+ \| `([^`]+\.md)` \|

# Load instructions
Load[:\s]+`([^`]+)`
```

### Step 2: Normalize Paths

Handle path inconsistencies:

| Pattern | Normalization |
|---------|---------------|
| `routines/x.md` | `skills/routines/x.md` |
| `workflows/x.md` | `skills/workflows/x.md` |
| `domains/x.md` | `skills/domains/x.md` |
| `integrations/x.md` | `skills/integrations/x.md` |
| `meta/x.md` | `skills/meta/x.md` |
| `.claude/x` | Full path resolution |

### Step 3: Validate Existence

For each extracted reference:
1. Build absolute path: `~/.claude\{normalized_path}`
2. Check file exists using Glob
3. Record result (exists/missing)
4. Track line number in CLAUDE.md

### Step 4: Generate Report

**Output Format:**
```
================================================================
        SKILL REFERENCE VALIDATION REPORT
        Date: {YYYY-MM-DD HH:MM}
================================================================

Total References: {N}
Valid: {N} ({percentage}%)
Broken: {N} ({percentage}%)

┌─ BROKEN REFERENCES ─────────────────────────────────────────┐
│                                                             │
│ Line {N}: `{reference}`                                     │
│   Expected: {absolute_path}                                 │
│   Fix: Change to `{corrected_path}`                         │
│                                                             │
│ Line {N}: `{reference}`                                     │
│   Expected: {absolute_path}                                 │
│   Fix: Create file or remove reference                      │
│                                                             │
└─────────────────────────────────────────────────────────────┘

┌─ AUTO-FIX SUGGESTIONS ──────────────────────────────────────┐
│                                                             │
│ The following can be auto-fixed by updating CLAUDE.md:      │
│                                                             │
│ 1. Line {N}: `routines/x.md` -> `skills/routines/x.md`     │
│ 2. Line {N}: `workflows/x.md` -> `skills/workflows/x.md`   │
│                                                             │
│ Run "fix skill references" to apply auto-fixes.             │
│                                                             │
└─────────────────────────────────────────────────────────────┘

================================================================
```

## Known Path Mappings

Common corrections based on actual file locations:

| CLAUDE.md Reference | Actual Location |
|---------------------|-----------------|
| `routines/morning.md` | `skills/routines/morning.md` |
| `routines/crm-report.md` | `skills/routines/crm-report.md` |
| `routines/bim-connect.md` | `skills/routines/bim-connect.md` |
| `routines/monday-cleanup.md` | `skills/routines/monday-cleanup.md` |
| `routines/token-burn-report.md` | `skills/routines/token-burn-report.md` |
| `routines/heartbeat.md` | `skills/routines/heartbeat.md` |
| `routines/backup-reminder.md` | `skills/routines/backup-reminder.md` |
| `routines/product-backup.md` | `skills/routines/product-backup.md` |

## Auto-Fix Capability

When broken references have obvious fixes (e.g., missing `skills/` prefix), the validator can auto-generate Edit commands:

```markdown
## Auto-Fix Commands

Edit CLAUDE.md line 106:
- Old: `routines/morning.md`
- New: `skills/routines/morning.md`

Edit CLAUDE.md line 108:
- Old: `routines/crm-report.md`
- New: `skills/routines/crm-report.md`
```

## Prevention Strategy

### Pre-Commit Hook Integration

Add to guardian pre-commit checks:
1. Extract new/modified skill references
2. Validate before allowing commit
3. Block commit if broken references introduced

### Weekly Validation

Include in Monday cleanup routine:
1. Run full reference validation
2. Report broken references
3. Track reference health over time

## Metrics Tracking

Log validation results for trend analysis:

```json
{
  "date": "2026-01-28",
  "total_references": 45,
  "valid_references": 42,
  "broken_references": 3,
  "auto_fixable": 3,
  "health_percentage": 93.3
}
```

## Related Skills

- `skills/meta/system-health-check.md` - Parent diagnostic
- `skills/meta/quick-trigger-maintenance.md` - Trigger table updates
- `skills/routines/monday-cleanup.md` - Weekly maintenance

---

*Skill Reference Validator v1.0 - Created 2026-01-28*
