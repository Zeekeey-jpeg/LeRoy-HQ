# System Health Check

**Trigger:** "health check", "system check", "diagnostic"
**Version:** 1.0
**Created:** 2026-01-28

## Purpose

Comprehensive CLAUDE.md diagnostic routine that validates system integrity, skill references, protocol versions, and agent deployment configurations.

## Quick Start

Say "health check" or "system diagnostic" to run a full system validation.

## Diagnostic Categories

### 1. Path Validation (Critical)

**Check:** All file paths referenced in CLAUDE.md exist on disk.

```
Paths to Validate:
- Skills directory: ~/.claude\skills\
- Agents directory: ~/.claude\agents\
- Memory vault: ~/.claude\memory\
- Session directory: ~/.claude\session\
- Hooks directory: ~/.claude\hooks\
```

**Validation Steps:**
1. Read CLAUDE.md
2. Extract all paths (backtick paths and explicit paths)
3. Verify each path exists using Glob
4. Report missing paths with severity level

**Scoring:**
- All paths valid: 100/100
- 1-2 missing: 80/100
- 3-5 missing: 60/100
- 6+ missing: 40/100

### 2. Skill Reference Validation (High Priority)

**Check:** All "See {skill-path}" references in CLAUDE.md point to existing files.

**Pattern Matching:**
```
Patterns to extract:
- `skills/{path}.md`
- `routines/{path}.md`
- `agents/{path}.md`
- See `{any-path}`
```

**Validation Steps:**
1. Extract all skill references from CLAUDE.md
2. Normalize paths (routines/ -> skills/routines/)
3. Check each file exists
4. Report broken references

**Scoring:**
- All references valid: 100/100
- 1-3 broken: 70/100
- 4-6 broken: 50/100
- 7+ broken: 30/100

### 3. Protocol Version Verification (Medium Priority)

**Check:** Protocol versions are consistent and current.

**Protocols to Verify:**
| Protocol | Expected Version | Location |
|----------|------------------|----------|
| Gate | v3.0 | CLAUDE.md line ~7 |
| Memory System | v3.2 | CLAUDE.md line ~218 |
| Identity System | v6.0 | CLAUDE.md line ~92 |
| Enforcement | v5.2 | CLAUDE.md line ~182 |
| Prediction Engine | v3.1 | hooks/prediction-engine.py |

**Validation Steps:**
1. Extract version numbers from CLAUDE.md
2. Cross-reference with actual file versions
3. Flag mismatches or outdated versions

**Scoring:**
- All versions match: 100/100
- 1 mismatch: 85/100
- 2+ mismatches: 70/100

### 4. Agent Deployment Validation (Medium Priority)

**Check:** Agent specifications are complete and consistent.

**Agents to Verify:**
```
Required agents:
- @agent-conductor
- @agent-builder
- @agent-designer
- @agent-forge
- @agent-guardian
- @agent-professor
- @agent-scout
- @agent-planner
- @agent-validator
```

**Validation Steps:**
1. Check agents/ directory for agent files
2. Verify each referenced agent exists
3. Validate agent specification format
4. Check for orphaned agents (exist but not referenced)

**Scoring:**
- All agents valid: 100/100
- 1-2 missing: 75/100
- 3+ missing: 50/100

### 5. Hook Chain Health (High Priority)

**Check:** Python hooks are functional and error-free.

**Hooks to Validate:**
```
~/.claude\hooks\
- gate-enforcer.py
- prediction-engine.py
- response-monitor.py (if exists)
```

**Validation Steps:**
1. Check each hook exists
2. Read error-log.jsonl for recent errors
3. Categorize errors by type and frequency
4. Check for syntax errors (python -m py_compile)

**Error Categories:**
- `unicode_encode`: Encoding issues (usually stdin/stdout)
- `prediction_timeout`: Performance issues (>200ms)
- `state_load_error`: Corrupted state files
- `prompt_history_corruption`: JSONL parse failures

**Scoring:**
- No errors (7 days): 100/100
- <10 errors: 80/100
- 10-50 errors: 60/100
- 50+ errors: 40/100

### 6. Auto-Systems Health (Critical Priority)

**Check:** All automated systems are running and not stale.

**Systems to Validate:**
| System | Max Stale Time | Auto-Repair |
|--------|----------------|-------------|
| memory_recall | 2 hours | Yes |
| memory_consolidation | 4 hours | Yes |
| scout | 4 hours | Yes |
| secretary | 24 hours | Yes |
| email_scan | 24 hours | Alert only |

**Validation Steps:**
1. Read state.json -> auto_systems
2. Check each system's last_run timestamp
3. Compare against max stale time
4. Auto-repair any NEVER_RAN or STALE systems
5. Update state.json with repair timestamps

**Status Mapping:**
- NEVER_RAN: Red (auto-repair triggered)
- STALE: Yellow (auto-repair triggered)
- ACTIVE: Green (within thresholds)
- PENDING: Blue (requires user action, e.g., baseline email scan)

**Scoring:**
- All systems active: 100/100
- 1 system stale (repaired): 90/100
- 2+ systems stale (repaired): 80/100
- Any system unrecoverable: 50/100

**Auto-Repair Protocol:**
When NEVER_RAN or STALE detected:
1. Execute appropriate repair action
2. Update state.json with new timestamp
3. Log repair to system-repair-log.md
4. User never sees red status

### 7. Memory System Health (Medium Priority)

**Check:** Memory vault structure and integrity.

**Checks:**
1. Vault directory exists and is accessible
2. memory-index.json exists and is valid JSON
3. Shard files are properly formatted
4. Tag governance compliance

**Scoring:**
- All checks pass: 100/100
- Index issues: -20 points
- Shard issues: -10 points per shard
- Tag violations: -5 points each

## Output Format

```
================================================================
           CLAUDE.md SYSTEM HEALTH CHECK
           Date: {YYYY-MM-DD HH:MM}
================================================================

OVERALL HEALTH SCORE: {XX}/100

┌─ PATH VALIDATION ───────────────────────────────────────────┐
│ Score: {XX}/100                                             │
│ Status: {PASS/WARN/FAIL}                                    │
│ Issues:                                                     │
│   - {issue 1}                                               │
│   - {issue 2}                                               │
└─────────────────────────────────────────────────────────────┘

┌─ SKILL REFERENCES ──────────────────────────────────────────┐
│ Score: {XX}/100                                             │
│ Status: {PASS/WARN/FAIL}                                    │
│ Broken References:                                          │
│   - {path 1} (line {N})                                     │
│   - {path 2} (line {N})                                     │
└─────────────────────────────────────────────────────────────┘

┌─ PROTOCOL VERSIONS ─────────────────────────────────────────┐
│ Score: {XX}/100                                             │
│ Status: {PASS/WARN/FAIL}                                    │
│ Versions:                                                   │
│   - Gate: v{X.X} [OK/MISMATCH]                             │
│   - Memory: v{X.X} [OK/MISMATCH]                           │
│   - Identity: v{X.X} [OK/MISMATCH]                         │
└─────────────────────────────────────────────────────────────┘

┌─ AGENT DEPLOYMENT ──────────────────────────────────────────┐
│ Score: {XX}/100                                             │
│ Status: {PASS/WARN/FAIL}                                    │
│ Agents: {N} found / {N} expected                           │
│ Missing: {list or "none"}                                   │
└─────────────────────────────────────────────────────────────┘

┌─ HOOK CHAIN HEALTH ─────────────────────────────────────────┐
│ Score: {XX}/100                                             │
│ Status: {PASS/WARN/FAIL}                                    │
│ Error Summary (last 7 days):                                │
│   - unicode_encode: {N}                                     │
│   - prediction_timeout: {N}                                 │
│   - state_load_error: {N}                                   │
└─────────────────────────────────────────────────────────────┘

┌─ AUTO-SYSTEMS HEALTH ───────────────────────────────────────┐
│ Score: {XX}/100                                             │
│ Status: {PASS/WARN/FAIL}                                    │
│ Systems:                                                    │
│   - Memory Recall:       {ACTIVE/STALE/NEVER_RAN}          │
│   - Memory Consolidation: {ACTIVE/STALE/NEVER_RAN}         │
│   - Scout Agent:         {ACTIVE/STALE/NEVER_RAN}          │
│   - Secretary Agent:     {ACTIVE/STALE/NEVER_RAN}          │
│   - Email Intelligence:  {ACTIVE/PENDING/NEVER_RAN}        │
│ Repairs Made: {N}                                           │
└─────────────────────────────────────────────────────────────┘

┌─ MEMORY SYSTEM ─────────────────────────────────────────────┐
│ Score: {XX}/100                                             │
│ Status: {PASS/WARN/FAIL}                                    │
│ Notes: {N} total | Index: {OK/ERROR} | Shards: {N}         │
└─────────────────────────────────────────────────────────────┘

================================================================
                    RECOMMENDATIONS
================================================================
Priority 1 (Critical):
  - {recommendation}

Priority 2 (High):
  - {recommendation}

Priority 3 (Medium):
  - {recommendation}

================================================================
                    END OF REPORT
================================================================
```

## Execution Protocol

When triggered:

1. **Load CLAUDE.md** - Read full file
2. **Extract all references** - Parse paths, versions, agent names
3. **Run validation checks** - Execute each category
4. **Calculate scores** - Apply scoring rubrics
5. **Generate report** - Output formatted report
6. **Log results** - Save to session/health-check-{date}.md

## Automated Recommendations

Based on findings, auto-generate remediation suggestions:

| Finding | Recommendation |
|---------|----------------|
| Broken skill reference | "Update CLAUDE.md line {N}: change `{old}` to `{new}`" |
| Missing agent | "Create agent file at agents/{name}.md" |
| Unicode errors in hooks | "Add encoding='utf-8' to stdin.read() in {file}" |
| High timeout rate | "Increase LATENCY_TIMEOUT_MS or optimize {hook}" |
| Stale protocol version | "Update {protocol} from v{old} to v{new}" |

## Integration Points

- **Morning routine:** Can be included in daily briefing
- **Monday cleanup:** Run as part of weekly maintenance
- **Pre-commit:** Optional gate before major changes

## Related Skills

- `skills/meta/skill-reference-validator.md` - Automated reference checking
- `skills/meta/memory-organizer.md` - Memory cleanup
- `skills/routines/monday-cleanup.md` - Weekly maintenance

---

*System Health Check v1.0 - Created 2026-01-28*
