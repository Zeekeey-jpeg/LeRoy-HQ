---
disable-model-invocation: true
---

# Position #0 Enforcement - Bulletproof Protocol Execution

**Version:** 2.0 (Comprehensive Specification)
**Purpose:** Make Position #0 execution structurally unavoidable through mandatory gate display and self-healing
**Integration:** CLAUDE.md lines 13-48, gate-enforcer.py, validate-gate-compliance.py

---

## Problem Statement

**Root Cause:** Position #0 is described but not enforced. Claude can skip `enforcement.todo` execution with zero consequences.

**Evidence:**
- `enforcement.todo` from Jan 30 still exists (4+ days stale)
- Memory recall NEVER_RAN for multiple sessions
- Background outputs (secretary, scout, growth) invisible in files
- No verification in gate output showing what executed

**Impact:** "I forgot" incidents, stale enforcement queues, invisible background work, context loss after compaction.

---

## Solution Architecture

**Purpose:** Make Position #0 execution visible in gate output to prevent silent protocol violations.

---

## What This Displays

Every gate output MUST include an enforcement status box showing what Position #0 actions were executed BEFORE the gate.

---

## Display Format

### Full Gate (Substantial Tasks)

```
[GATE] Project: your org | Background: spawning

┌─ POSITION #0 ENFORCEMENT ───────────────────────────────────┐
│ ✅ enforcement.todo read (2 actions queued)                  │
│ ✅ RECALL_MEMORY executed (5 notes loaded, 187ms)            │
│ ✅ CONSOLIDATE_MEMORY queued (background)                    │
│ Memory: 5 notes | Scout: active | Voice: 847 samples         │
│ A2A: ✅ {card_count} cards loaded | mesh v3.0               │
│ Interrupts: {⚠️ N pending | none}    (v6.1 — Interrupts-A)  │
└──────────────────────────────────────────────────────────────┘
```

**Interrupts row (v6.1):** Read `session/interrupts.queue` (JSONL). Count entries where `acked=false` (regardless of `surfaced` state). Display:
- `none` (cyan) — queue absent, empty, or all acked
- `⚠️ N pending` (yellow) — 1+ unACKed entries; show priority breakdown if N≥3 (e.g. `⚠️ 3 pending (1 HIGH, 2 MEDIUM)`)
- `🚨 CRITICAL` (red) — at least one CRITICAL unACKed entry; user attention required

Pseudocode:
```python
queue_path = Path.home() / ".claude" / "session" / "interrupts.queue"
unacked = []
if queue_path.exists():
    for line in queue_path.read_text(encoding="utf-8").splitlines():
        try:
            e = json.loads(line)
            if not e.get("acked"):
                unacked.append(e)
        except json.JSONDecodeError:
            continue
if not unacked:
    interrupts_line = "Interrupts: none"
elif any(e.get("priority","").upper() == "CRITICAL" for e in unacked):
    interrupts_line = "Interrupts: 🚨 CRITICAL — see queue"
else:
    interrupts_line = f"Interrupts: ⚠️ {len(unacked)} pending"
```

```
┌─ ORIGINAL REQUEST (SACRED) ─────────────────────────────────┐
│ "{verbatim prompt - first 100 chars}..."                    │
│ Goal: {interpreted goal}                                    │
│ Done When: {success criteria}                               │
└──────────────────────────────────────────────────────────────┘

... rest of full gate ...
```

**FLIGHT PLAN box (Orchestration Architect):** when `enforcement.todo` contains a
`PLAN_EXECUTION_STRATEGY` action (written by `hooks/orchestration-planner.py` on
substantial prompts), the CTO auto-selects the execution modality stack and a FLIGHT PLAN
box renders **between this enforcement box and ROUTES LOADED**. Format + logic:
`skills/meta/session-gate.md` and `skills/meta/execution-strategy-matrix.md`. Suppressed
in shadow mode (default) or when `session/orchestration-planner.disabled` exists.

### Mini Gate (Trivial Tasks)

```
[GATE] Project: your org | Agents: [1] quick | Background: yes

┌─ ENFORCEMENT ───────────────────────────────────────────────┐
│ Position #0: ✅ Executed (215ms) | Memory: 5 notes          │
│ Voice: ✅ Captured (#848) | Scout: Background               │
└──────────────────────────────────────────────────────────────┘
```

---

## Status Indicators

### Position #0 Execution

| Status | Indicator | Meaning |
|--------|-----------|---------|
| **Executed** | ✅ | enforcement.todo was read and all actions completed |
| **Partial** | ⚠️  | Some actions executed, some failed |
| **Skipped** | ❌ | enforcement.todo NOT read (PROTOCOL VIOLATION) |
| **No Queue** | ℹ️  | No enforcement.todo (no actions required) |

### System Status

| System | Status | Display |
|--------|--------|---------|
| **Memory Recall** | Executed | ✅ 5 notes loaded, 187ms |
| **Memory Recall** | Skipped | ❌ Not executed |
| **Memory Recall** | Not Required | ℹ️  Not needed |
| **Voice Capture** | Success | ✅ Sample #848 |
| **Voice Capture** | Failed | ❌ Capture failed |
| **Scout** | Active | ✅ Active (patterns: 3) |
| **Scout** | Spawned | ✅ Spawning (id: abc123) |
| **Scout** | Not Required | ℹ️  Not needed |

---

## How to Generate This Display

### Step 1: Check for enforcement.todo

```python
from pathlib import Path
import json

ENFORCEMENT_FILE = Path.home() / ".claude" / "session" / "enforcement.todo"

if ENFORCEMENT_FILE.exists():
    # Read and execute
    executor_result = execute_enforcement_queue()

    display = {
        'executed': True,
        'actions_count': executor_result['actions_executed'],
        'duration_ms': executor_result['duration_ms'],
        'results': executor_result['results']
    }
else:
    display = {
        'executed': False,
        'no_queue': True
    }
```

### Step 2: Load state for system status

```python
STATE_FILE = Path.home() / ".claude" / "session" / "state.json"

with open(STATE_FILE, 'r') as f:
    state = json.load(f)

auto_sys = state.get("auto_systems", {})
memory_sys = state.get("memory_system", {})
scout = state.get("scout", {})
voice = auto_sys.get("voice_capture", {})

system_status = {
    'memory_notes': memory_sys.get('notes_loaded', 0),
    'voice_samples': voice.get('corpus_size', 0),
    'scout_active': scout.get('active', False),
    'scout_patterns': scout.get('patterns_detected', 0)
}
```

### Step 3: Format display box

```python
def format_enforcement_box_full(display, system_status):
    """Format enforcement box for full gate"""
    lines = []
    lines.append("┌─ POSITION #0 ENFORCEMENT ───────────────────────────────────┐")

    if display['executed']:
        emoji = "✅"
        actions = display['actions_count']
        duration = display['duration_ms']
        lines.append(f"│ {emoji} enforcement.todo read ({actions} actions queued)" + " " * 18 + "│")

        # Show each action result
        for result in display['results']:
            action = result['action']
            status = result['status']

            if action == 'RECALL_MEMORY' and status == 'success':
                notes = result['notes_loaded']
                ms = result['duration_ms']
                lines.append(f"│ ✅ RECALL_MEMORY executed ({notes} notes loaded, {ms}ms)" + " " * 15 + "│")
            elif action == 'CONSOLIDATE_MEMORY' and status == 'queued':
                lines.append(f"│ ✅ CONSOLIDATE_MEMORY queued (background)" + " " * 21 + "│")
            elif action == 'SPAWN_SCOUT' and status == 'queued':
                lines.append(f"│ ✅ SPAWN_SCOUT queued (background)" + " " * 27 + "│")
            elif action == 'RUN_LOOP' and status == 'success':
                interval = result.get('interval', '?')
                lines.append(f"│ ✅ RUN_LOOP registered ({interval} trading status loop)" + " " * 10 + "│")
    elif display['no_queue']:
        lines.append(f"│ ℹ️  No enforcement queue (no actions required)" + " " * 17 + "│")
    else:
        lines.append(f"│ ❌ WARNING: enforcement.todo NOT READ" + " " * 25 + "│")
        lines.append(f"│ ⚠️  PROTOCOL VIOLATION: Skipped Position #0" + " " * 19 + "│")

    # System summary line
    memory_count = system_status['memory_notes']
    voice_count = system_status['voice_samples']
    scout_status = "active" if system_status['scout_active'] else "background"

    summary = f"Memory: {memory_count} notes | Scout: {scout_status} | Voice: {voice_count} samples"
    padding = 62 - len(summary)
    lines.append(f"│ {summary}" + " " * padding + "│")

    lines.append("└──────────────────────────────────────────────────────────────┘")

    return "\n".join(lines)


def format_enforcement_box_mini(display, system_status):
    """Format enforcement box for mini gate"""
    if display['executed']:
        duration = display['duration_ms']
        status = f"Position #0: ✅ Executed ({duration}ms)"
    elif display['no_queue']:
        status = "Position #0: ℹ️  No queue"
    else:
        status = "Position #0: ❌ NOT EXECUTED"

    memory = system_status['memory_notes']
    voice = system_status['voice_samples']
    scout = "Active" if system_status['scout_active'] else "Background"

    details = f"Memory: {memory} notes | Voice: ✅ Captured (#{voice}) | Scout: {scout}"

    lines = []
    lines.append("┌─ ENFORCEMENT ───────────────────────────────────────────────┐")
    lines.append(f"│ {status} | {details}" + " " * (60 - len(status) - len(details) - 3) + "│")
    lines.append("└──────────────────────────────────────────────────────────────┘")

    return "\n".join(lines)
```

---

## Frontend Scope — DESIGN.md Injection (Conditional)

**Gate:** ONLY fires when the session is frontend-scoped. Zero overhead for non-UI sessions.

### Trigger Conditions (ANY one match fires the gate)

| Signal | Examples |
|--------|---------|
| **Project** | `leroy-pwa-app`, `integrator-os`, `quote-ui`, `product-ui`, any project under `memory/Projects/leroy-pwa-app/` |
| **Active skill** | `web-development`, `designer`, `design-sync`, `integratorOS-agent` |
| **UI build keywords in prompt** | `component`, `UI`, `frontend`, `stylesheet`, `CSS`, `Tailwind`, `theme`, `color`, `typography`, `layout`, `button`, `panel`, `modal`, `sidebar`, `nav`, `dark mode`, `brand`, `design system` |

### Enforcement Rule

When any trigger matches:

1. **Load** `~/.claude\DESIGN.md` (the your org brand source of truth).
2. **Apply** Product UI tokens (colors, typography, spacing) to all component output.  
   — Use Brand Identity tokens only for proposals / emails / PDFs, never for app UI.
3. **Gate display** — add a `🎨 DESIGN.md` line to the enforcement box.

```
│ 🎨 DESIGN.md loaded (frontend scope — brand tokens active)   │
```

### Pseudocode

```python
FRONTEND_PROJECTS = {
    "leroy-pwa-app", "integrator-os", "quote-ui", "product-ui"
}
FRONTEND_SKILLS = {
    "web-development", "designer", "design-sync", "integratorOS-agent"
}
FRONTEND_KEYWORDS = {
    "component", "UI", "frontend", "stylesheet", "css", "tailwind",
    "theme", "color", "typography", "layout", "button", "panel",
    "modal", "sidebar", "nav", "dark mode", "brand", "design system"
}

def is_frontend_scoped(project: str, active_skill: str, prompt: str) -> bool:
    if project in FRONTEND_PROJECTS:
        return True
    if active_skill in FRONTEND_SKILLS:
        return True
    prompt_lower = prompt.lower()
    return any(kw.lower() in prompt_lower for kw in FRONTEND_KEYWORDS)

DESIGN_MD = Path.home() / ".claude" / "DESIGN.md"

if is_frontend_scoped(current_project, active_skill, user_prompt):
    design_tokens = DESIGN_MD.read_text(encoding="utf-8")
    # Inject into context — product UI tokens authoritative for all component output
    inject_design_context(design_tokens)
    enforcement_box_extras.append(
        "🎨 DESIGN.md loaded (frontend scope — brand tokens active)"
    )
```

### Exclusions (do NOT fire)

- Pure backend / API / database tasks with no UI output
- CLI tooling, scripts, data pipelines
- your BIM tool / BIM work (uses its own annotation doctrine)
- Email / PDF / proposal creation (uses Brand Identity layer, not Product UI layer)
- Morning briefing, daily ops, and other routine non-UI sessions

---

## When to Display

**ALWAYS.** Every response must show enforcement status.

**Before or after gate banner?**
- **AFTER gate banner line** for visual hierarchy
- Gate banner is first line
- Enforcement box is second section

---

## Error States

### enforcement.todo exists but wasn't read

```
┌─ POSITION #0 ENFORCEMENT ───────────────────────────────────┐
│ ❌ CRITICAL: enforcement.todo EXISTS BUT NOT READ            │
│ ⚠️  PROTOCOL VIOLATION: Position #0 skipped                 │
│ File: .claude/session/enforcement.todo (2 actions queued)   │
└──────────────────────────────────────────────────────────────┘
```

### Execution failed

```
┌─ POSITION #0 ENFORCEMENT ───────────────────────────────────┐
│ ✅ enforcement.todo read (2 actions queued)                  │
│ ✅ RECALL_MEMORY executed (5 notes, 187ms)                   │
│ ❌ CONSOLIDATE_MEMORY FAILED: Memory index not found         │
└──────────────────────────────────────────────────────────────┘
```

---

## Integration Points

1. **Gate output** - Display MUST appear after [GATE] line
2. **execute-enforcement.py** - Provides execution results
3. **state.json** - Provides system status
4. **response-monitor.py** - Post-response validation

---

## Violation Logging

When enforcement box shows ❌ or ⚠️:

```python
from scripts.protocol_violations import log_violation

if not display['executed'] and not display['no_queue']:
    log_violation(
        "position_zero_skipped",
        "enforcement.todo exists but was not read",
        severity="critical"
    )
```

---

## Performance Targets

### Position #0 Execution Time

| Component | Target | Acceptable | Critical |
|-----------|--------|------------|----------|
| enforcement.todo read | <10ms | <20ms | >50ms |
| SOUL.md + USER.md load | <60ms | <80ms | >100ms |
| Memory recall | <150ms | <200ms | >300ms |
| Working memory load (Phase 2) | <50ms | <75ms | >100ms |
| **Total Position #0** | <250ms | <350ms | >500ms |

**Monitoring:** Log actual times in state.json, alert on >500ms executions

### Compliance Targets

| Metric | Target | Minimum | Critical |
|--------|--------|---------|----------|
| Position #0 box presence | 100% | 98% | <95% |
| Self-healing success rate | 100% | 95% | <90% |
| Enforcement.todo processing | 100% | 100% | <100% |
| Avg time to self-heal | <1 response | <2 responses | >3 responses |

---

## Self-Healing Protocol

### Detection (Post-Response Hook)

**Script:** `scripts/validate-gate-compliance.py` (enhanced)

**Detection Logic:**
1. Check if `session/enforcement.todo` exists
2. Parse gate output for Position #0 enforcement box
3. If file exists but box shows "No enforcement.todo present" → VIOLATION
4. If file exists and no Position #0 box in gate → VIOLATION
5. Log violation to `session/protocol-violations.jsonl`

**Violation Log Format:**
```json
{
  "timestamp": "2026-02-03T14:30:00Z",
  "violation_type": "position_zero_skipped",
  "enforcement_file": "session/enforcement.todo",
  "actions_queued": 4,
  "gate_output_present": false,
  "session_id": "abc123"
}
```

### Correction (Pre-Prompt Hook)

**Script:** `hooks/gate-enforcer.py` (enhanced pre-prompt section)

**Self-Healing Logic:**
```python
def inject_self_healing_reminder():
    """Inject CRITICAL reminder if recent violation detected."""

    # Check for violations in last response
    violations = load_recent_violations(limit=1)

    if violations and violations[0]["timestamp"] > time.time() - 300:  # Last 5 min
        # Force enforcement execution
        reminder = """
        ⚠️ CRITICAL: Position #0 violation detected in previous response.

        MANDATORY CORRECTION:
        1. Read session/enforcement.todo IMMEDIATELY
        2. Execute ALL queued actions
        3. Display Position #0 VIOLATION box in gate
        4. Include self-healing confirmation in box
        5. Delete enforcement.todo after execution

        This is NOT optional. Display the violation box NOW.
        """

        inject_system_reminder(reminder)
        log_self_healing_attempt()
```

**Result:** Next response MUST show VIOLATION box and execute queued actions.

---

## Testing Protocol

### Unit Tests (Validation Script)

**Test scenarios:**
1. ✅ Position #0 box present in gate output
2. ✅ enforcement.todo exists → box shows "READ (N actions)"
3. ✅ No enforcement.todo → box shows "No enforcement.todo present"
4. ❌ enforcement.todo exists → box claims none → VIOLATION
5. ❌ No Position #0 box in gate → VIOLATION
6. ✅ VIOLATION box shown after detection → self-healing successful

**Test command:**
```bash
python scripts/validate-gate-compliance.py --test-position-zero
```

### Integration Tests (Phase 1 Task 4)

**10 sample scenarios:**
1. Trivial request (mini-gate)
2. Substantial task (full gate)
3. With enforcement.todo present (4 actions queued)
4. Without enforcement.todo (clean state)
5. After violation (self-healing box)
6. During recovery (VIOLATION → EXECUTED)
7. With background agents spawning
8. With memory recall active
9. During morning routine
10. During session reset

**Success criteria:** 100% of scenarios show Position #0 box in correct format

---

## Metrics & Monitoring

### State.json Schema Addition

```json
{
  "position_zero": {
    "last_execution_timestamp": "2026-02-03T14:30:00Z",
    "last_execution_time_ms": 187,
    "compliance_rate_7d": 0.942,
    "violations_7d": 2,
    "self_heals_7d": 2,
    "enforcement_queue_current": 0,
    "enforcement_queue_max_age_hours": 0
  }
}
```

### Protocol Violations Log Schema

**File:** `session/protocol-violations.jsonl`

```json
{
  "timestamp": "2026-02-03T14:30:00Z",
  "violation_type": "position_zero_skipped",
  "enforcement_file_exists": true,
  "enforcement_actions_queued": 4,
  "enforcement_file_age_hours": 96,
  "gate_output_present": false,
  "position_zero_box_present": false,
  "self_heal_injected": true,
  "self_heal_timestamp": "2026-02-03T14:31:00Z",
  "self_heal_successful": true,
  "session_id": "abc123"
}
```

---

## Success Criteria (Phase 1)

**Completion requires:**
- ✅ CLAUDE.md updated with Position #0 enforcement box requirement
- ✅ This specification document enhanced (v2.0)
- ⚠️ validate-gate-compliance.py enhanced with Position #0 validation
- ⚠️ 10/10 test scenarios show Position #0 box correctly
- ⚠️ Self-healing protocol tested and verified
- ⚠️ Compliance metrics integrated into morning dashboard

**Validation:**
1. Run 10 diverse prompts → 100% show Position #0 box
2. Create stale enforcement.todo → Next response shows VIOLATION → Self-heals
3. Check morning dashboard → Compliance metrics visible
4. Verify protocol-violations.jsonl → Violation logging works

**Outcome:** "I forgot" becomes structurally impossible. Position #0 ALWAYS executes, violations ALWAYS visible, self-healing ALWAYS recovers.

---

## Future Enhancements (Phase 2+)

### Working Memory Integration

**Position #0 Step 3 enhancement (Phase 2):**
```
3. >>> LOAD WORKING MEMORY INDEX <<< (NEW - <50ms)
   - Read session/working-memory/index.md
   - Inject into context (always available)
```

**Enforcement box addition:**
```
│ • WORKING_MEMORY loaded (index + 3 files, 48ms)              │
│ Active: 2 clients, 1 project, 3 pending actions              │
```

### Background Output Surfacing

**Position #0 Step 6 enhancement (Phase 3):**
```
6. >>> SURFACE BACKGROUND FINDINGS <<< (NEW - <30ms)
   - Aggregate secretary/scout/growth outputs
   - Update working-memory/background-findings.md
   - Show highlights in enforcement box
```

**Enforcement box addition:**
```
│ Background: 12 secretary events, 7 scout patterns detected   │
│ [Details: working-memory/background-findings.md]             │
```

---

**Version:** 2.0 (Comprehensive Specification)
**Status:** Phase 1 Tasks 1-2 complete (CLAUDE.md + specification)
**Next:** Task 3 - Enhance validate-gate-compliance.py, Task 4 - Testing
**Purpose:** Making "I forgot" structurally impossible through bulletproof Position #0 enforcement
