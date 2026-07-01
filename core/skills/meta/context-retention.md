# Context Retention Skill

> **Purpose:** Preserve critical context across compaction events.
> **Trigger:** Any substantial task, context loss suspicion, or explicit request.

---

## The Problem

When Claude Code's context window fills, older messages are summarized (compacted). This causes:

1. **Original intent lost** - We remember what we did, not what we were asked
2. **Drift from goal** - Work continues but in the wrong direction
3. **Re-asking required** - User must repeat themselves

**Root cause:** The original user prompt is the most important context, but it's the first thing summarized away.

---

## The Solution: Multi-Layer Retention

| Layer | File | Shows | Purpose |
|-------|------|-------|---------|
| 1 | `session/state.json` | Full prompt | Machine-readable, recovery source |
| 2 | `session/context-anchor.md` | Full prompt | Human-readable backup |
| 3 | Hook banner | **Compact indicator** | Goal + project (saves context) |
| 4 | Gate output | Goal + criteria | Forces acknowledgment |

**Key insight:** Full prompt stored in FILES, compact indicator in banner to save context.

---

## Protocol: Task Start

When starting ANY substantial task:

### Step 1: Capture Original Prompt
```json
// In state.json
{
  "original_request": {
    "prompt": "EXACT user words - copy/paste, no editing",
    "interpreted_as": "My one-sentence understanding",
    "success_criteria": "How we know we're done",
    "captured_at": "2026-01-10T15:00:00Z",
    "project": "project name"
  }
}
```

### Step 2: Update Context Anchor
Create/update `session/context-anchor.md`:
```markdown
## ORIGINAL REQUEST (SACRED - NEVER MODIFY)
> Captured: {timestamp}

"{exact user prompt}"

**Interpreted As:** {interpretation}
**Success Criteria:** {criteria}
```

### Step 3: Include in Gate
Full gate MUST show:
```
┌─ ORIGINAL REQUEST (SACRED) ─────────────────────────────┐
│ "{first 100 chars of prompt}..."                        │
│ Goal: {interpreted goal}                                │
│ Done When: {success criteria}                           │
└─────────────────────────────────────────────────────────┘
```

---

## Protocol: During Task

### On Key Decisions
Add to context-anchor.md:
```markdown
## Key Decisions
| # | Decision | Rationale |
|---|----------|-----------|
| 1 | {decision} | {why} |
```

### On Phase Changes
Update state.json:
```json
{
  "phase": "discovery|planning|implementation|review",
  "progress": "3 of 7 steps"
}
```

### On File Modifications
Log to context-anchor.md:
```markdown
## Files Modified
| File | Change | Why |
|------|--------|-----|
```

---

## Protocol: After Compaction

When you suspect compaction occurred (confusion, missing context):

### Step 1: Read Hook Banner
The banner shows compact indicator:
```
TASK: {goal} | Project: {project} | Prompt: {N} chars (in state.json)
```

### Step 2: Read State File for Full Prompt
```bash
# Read state.json → original_request.prompt for FULL verbatim prompt
```
This is the authoritative source for what the user asked.

### Step 3: Read Context Anchor for Decisions
```bash
# Read session/context-anchor.md
```
This has full context including decisions made and files modified.

### Step 4: Re-Orient
Before continuing work:
1. State the original request (from state.json)
2. Confirm current phase
3. Verify next action aligns with goal

---

## Context Anchor Template

```markdown
# Context Anchor - Survives Compaction

## ORIGINAL REQUEST (SACRED - NEVER MODIFY)
> Captured: {timestamp} | Project: {project}

"{verbatim user prompt}"

**Interpreted As:** {one-line interpretation}
**Success Criteria:** {how we know we're done}

---

## Current State
| Field | Value |
|-------|-------|
| Phase | {discovery/planning/implementation/review} |
| Progress | {X of Y} |
| Started | {timestamp} |

---

## Key Decisions
| # | Decision | Rationale |
|---|----------|-----------|

---

## Files Modified
| File | Change | Why |
|------|--------|-----|

---

## Recovery Instructions
1. Re-read ORIGINAL REQUEST above
2. Check phase and progress
3. Resume from current state
```

---

## Edge Cases

### Multiple Tasks in Session
When switching tasks:
1. Archive current original_request to `previous_requests` array
2. Capture new original_request
3. Update context-anchor.md

### Subtasks vs New Tasks
- **Subtask:** Same original_request, update progress
- **New task:** New original_request, archive old

### Quick Triggers
Quick triggers (morning, leroy) don't need original_request capture - they're well-defined routines.

---

## Verification Checklist

Before any substantial work:
- [ ] Original prompt captured in state.json
- [ ] Context-anchor.md exists and updated
- [ ] Gate includes ORIGINAL REQUEST section
- [ ] Hook will inject prompt on next message

After compaction:
- [ ] Hook banner shows original request
- [ ] Can recover full context from files
- [ ] Work continues aligned with original goal

---

## Related Skills

- `meta/session-gate.md` - Gate protocol
- `CLAUDE.md` - Main config with enforcement rules

---

*Context Retention v1.0 | Multi-layer protection | Survives compaction*
