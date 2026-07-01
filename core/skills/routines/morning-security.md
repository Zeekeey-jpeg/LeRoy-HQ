# Morning Security Scan Skill v1.0
# Integrated into morning routine — runs automatically each morning

## Purpose
6-layer AI security scan of the user's machine and network.
Produces a threat brief that gets injected into the morning briefing.

## Scan Layers
1. **Processes** — running binaries, signatures, LOLBin abuse, encoded PS
2. **Network** — active connections, listening ports, bad IP detection
3. **Persistence** — registry run keys, scheduled tasks, startup folder, WMI subs
4. **File Integrity** — SHA256 hash comparison of 25 critical system binaries
5. **Auth Events** — failed logins, new accounts, privilege escalation (24h window)
6. **Behavioral Patterns** — suspicious process locations, double extensions, unsigned system binaries

## Execution

### Daily (called from morning routine)
```bash
cd ~/.claude
python tools/morning-security-scan.py
```

### First Run — Build Baseline (run ONCE on clean machine)
```bash
cd ~/.claude
python tools/baseline-builder.py
```

### Force Rebuild Baseline
```bash
python tools/morning-security-scan.py --baseline
```

## Output
- **Console**: Full security brief printed to terminal
- **File**: `tools/security-brief.md` — read this file and display in morning brief

## Morning Routine Integration
Insert the security brief block AFTER the calendar section, BEFORE the sales section.

Read `~/.claude\tools\security-brief.md` after scan completes.
Display it verbatim under a "SECURITY" heading in the morning brief.

If `security-brief.md` doesn't exist (first morning), run baseline-builder first, then scan.

## Threat Score Reference
| Score  | Level    | Action |
|--------|----------|--------|
| 0      | ALL CLEAR | Nothing needed |
| 1–19   | LOW       | Review advisory items |
| 20–39  | MODERATE  | Investigate flagged items today |
| 40–69  | ELEVATED  | Investigate immediately before other work |
| 70–100 | CRITICAL  | Stop — investigate before anything else |

## File Locations
- Scanner:  `~/.claude\tools\morning-security-scan.ps1`
- Python:   `~/.claude\tools\morning-security-scan.py`
- Baseline: `~/.claude\tools\security-baseline.json`
- Builder:  `~/.claude\tools\baseline-builder.py`
- Output:   `~/.claude\tools\security-brief.md`

## Baseline Strategy
- Baseline is auto-refreshed on clean scans (score < 15)
- Manually rebuild after: major Windows updates, new software installs
- Baseline captures: processes, ports, run keys, tasks, file hashes, WMI state
