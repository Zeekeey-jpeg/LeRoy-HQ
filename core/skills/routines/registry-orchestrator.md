# Registry Orchestrator

## Trigger

This skill activates when:
- `"AUTOMATED RUN: Execute scheduled routine {id}"` (automated from Task Scheduler)
- `"run scheduled {id}"` (manual trigger)

---

## Purpose

Central dispatcher for scheduled workflows. Reads schedule-registry.json, validates configuration, and executes the appropriate skill file.

**Integration Point:** Bridges Windows Task Scheduler automation → Claude skill execution.

---

## Protocol

### Step 1: Parse Trigger & Extract Routine ID

Extract routine ID from prompt:
```
"AUTOMATED RUN: Execute scheduled routine monday-cleanup" → monday-cleanup
"run scheduled leroy-weekly-reports" → leroy-weekly-reports
```

If routine ID not found in prompt:
```
ERROR: No routine ID specified
Usage:
  Automated: "AUTOMATED RUN: Execute scheduled routine {id}"
  Manual: "run scheduled {id}"

View available routines: "show scheduled routines"
```

### Step 2: Load Registry & Find Workflow

Read registry file:
```python
registry_path = "~/.claude\\skills\\routines\\schedule-registry.json"

if not exists(registry_path):
    ERROR: Registry file not found at {registry_path}
    Exit with failure

registry = read_json(registry_path)
workflow = find_workflow_by_id(registry, routine_id)

if not workflow:
    ERROR: Workflow '{routine_id}' not found in registry

    Available routines:
    {list all workflow IDs and names from registry}

    Exit with failure
```

### Step 3: Validate Workflow Configuration

Check if workflow is enabled and properly configured:
```python
if not workflow["enabled"]:
    LOG: Workflow '{workflow["name"]}' is DISABLED - skipping execution
    Exit with success (not an error condition)

if not workflow["skill_path"]:
    ERROR: Workflow '{workflow["name"]}' has no skill_path defined
    Exit with failure

skill_full_path = "~/.claude\\skills\\" + workflow["skill_path"]

if not exists(skill_full_path):
    ERROR: Skill file not found: {skill_full_path}
    Configured path: {workflow["skill_path"]}
    Exit with failure
```

### Step 4: Update Session State (Execution Tracking)

Write to session/state.json for tracking:
```json
{
  "scheduled_execution": {
    "active": true,
    "routine_id": "{routine_id}",
    "routine_name": "{workflow.name}",
    "skill_path": "{workflow.skill_path}",
    "triggered_by": "automated" | "manual",
    "executed_at": "{ISO timestamp}",
    "status": "running"
  }
}
```

### Step 5: Load & Execute Skill

Load the skill file content:
```python
LOG: Loading skill from: {skill_full_path}

skill_content = read_file(skill_full_path)

LOG: Skill loaded successfully ({len(skill_content)} bytes)
LOG: Executing routine: {workflow["name"]}
```

**Execute the skill's protocol:**
- Follow the skill file's instructions
- Run all steps defined in the skill
- If skill requires parameters, use fixed parameters from registry (if configured)

### Step 6: Post-Execution Updates

After skill completes successfully:

**Update Registry:**
```python
workflow["last_run"] = today() # YYYY-MM-DD format
workflow["next_run"] = calculate_next_run(workflow["recurrence"], today())

write_json(registry, registry_path)

LOG: Registry updated
LOG:   Last run: {workflow["last_run"]}
LOG:   Next run: {workflow["next_run"]}
```

**Update Session State:**
```python
state["scheduled_execution"]["status"] = "completed"
state["scheduled_execution"]["completed_at"] = now_iso()
state["scheduled_execution"]["duration_seconds"] = duration

write_json(state, state_path)
```

**NOTE:** Email notification is handled by orchestrator.ps1, NOT by this skill.

---

## Error Handling

| Error Scenario | Response | Exit Code |
|----------------|----------|-----------|
| **Registry file not found** | Log error with path, instruct user to check file exists | 1 |
| **Routine ID not found** | Display available routines, suggest "show scheduled routines" | 1 |
| **Workflow disabled** | Log info message, exit successfully (not an error) | 0 |
| **Skill file not found** | Log error with full path, suggest checking skill_path in registry | 1 |
| **Skill execution fails** | Log error details, preserve error for email notification | Exit with skill's code |
| **State update fails** | Log warning, continue (non-critical) | 0 |
| **Registry update fails** | Log warning, continue (non-critical) | 0 |

**Critical vs Non-Critical Errors:**
- **Critical** (exit with failure): Registry/skill file missing, workflow not found, skill execution failure
- **Non-Critical** (log warning only): State/registry updates failing (these are informational, not essential)

---

## Integration with Automation System

**Call Chain:**
```
Windows Task Scheduler (scheduled time)
    ↓
launcher.bat (silent wrapper)
    ↓
orchestrator.ps1 (PowerShell engine)
    ↓
Claude CLI with prompt: "AUTOMATED RUN: Execute scheduled routine {id}"
    ↓
THIS SKILL (registry-orchestrator.md)
    ↓
Individual Routine Skill (based on skill_path)
    ↓
orchestrator.ps1 sends email notification
```

**State Tracking:**
- `session/state.json` - Current execution status
- `schedule-registry.json` - last_run and next_run timestamps
- `automation/logs/{routine_id}-{date}.log` - PowerShell execution log

**Email Notifications:**
- Success email: Sent by orchestrator.ps1 after Claude exits with code 0
- Error email: Sent by orchestrator.ps1 if Claude exits with non-zero code
- This skill does NOT send emails directly

---

## Manual Triggering (Testing)

Users can manually trigger any scheduled routine:
```
"run scheduled monday-cleanup"
"run scheduled leroy-weekly-reports"
```

This is useful for:
- Testing routine execution
- Running routine outside of schedule
- Debugging issues before setting up Task Scheduler

Manual execution follows same protocol but:
- Sets `triggered_by: "manual"` in state
- Does NOT automatically update next_run (only automated runs do this)

---

## Example Execution Flow

**Scenario:** Task Scheduler triggers monday-cleanup at 6:00 AM Monday

1. **Task Scheduler** executes `launcher.bat monday-cleanup "Monday System Cleanup"`
2. **launcher.bat** calls `orchestrator.ps1` with routine ID
3. **orchestrator.ps1** sends prompt: `"AUTOMATED RUN: Execute scheduled routine monday-cleanup"`
4. **Claude routes** to registry-orchestrator.md (this skill)
5. **This skill:**
   - Parses routine ID: `monday-cleanup`
   - Loads registry, finds workflow
   - Validates: enabled=true, skill_path exists
   - Updates state.json: status="running"
   - Loads skill file: `routines/monday-cleanup.md`
   - Executes monday-cleanup protocol
   - Updates registry: last_run=2026-01-20, next_run=2026-01-27
   - Updates state.json: status="completed"
6. **Claude exits** with code 0
7. **orchestrator.ps1:**
   - Detects success (code 0)
   - Updates registry with new next_run
   - Sends success email to you@example.com
8. **launcher.bat** exits with code 0
9. **Task Scheduler** logs successful execution

**Total execution time:** Varies by routine (cleanup: ~60s, LeRoy: ~5min)

---

## Registry Schema Reference

Expected structure in schedule-registry.json:
```json
{
  "workflows": [
    {
      "id": "monday-cleanup",
      "name": "Monday System Cleanup",
      "skill_path": "routines/monday-cleanup.md",
      "recurrence": "every_monday",
      "next_run": "2026-01-20",
      "last_run": "2026-01-13",
      "enabled": true,
      "recipients": {
        "to": [],
        "cc": ["you@example.com"],
        "bcc": []
      }
    }
  ]
}
```

**Required fields for this skill:**
- `id` - Unique routine identifier
- `name` - Human-readable name
- `skill_path` - Relative path to skill file
- `enabled` - Boolean flag

**Used but not required:**
- `last_run`, `next_run` - Updated by this skill
- `recurrence` - Used for next_run calculation
- `recipients` - Used by individual skills for email sending

---

*Registry Orchestrator v1.0 | Automated Execution Dispatcher*
