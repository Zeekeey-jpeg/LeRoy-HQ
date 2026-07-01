# Routine Dashboard

## Trigger

This skill activates when:
- `"show scheduled routines"`
- `"list schedules"`
- `"routine dashboard"`
- `"details {routine_id}"` (for individual routine details)

---

## Purpose

Provides comprehensive visibility into all scheduled routines with:
- Summary table of all workflows
- Next run countdown
- Execution history
- Management commands
- Detailed view for individual routines

---

## Protocol

### Determine View Type

Parse user prompt to determine view:
```python
if "details" in prompt and routine_id_provided:
    display_detailed_view(routine_id)
else:
    display_summary_view()
```

---

## Summary View (Default)

### Step 1: Load Registry

```python
registry_path = "~/.claude\\skills\\routines\\schedule-registry.json"
registry = load_json(registry_path)
workflows = registry["workflows"]

# Filter enabled workflows (optional: show all with status indicator)
enabled_workflows = [w for w in workflows if w.get("enabled", True)]
```

### Step 2: Calculate Next Run Countdown

```python
from datetime import datetime, timedelta

today = datetime.now()

for workflow in workflows:
    next_run_str = workflow.get("next_run", "Unknown")

    if next_run_str != "Unknown":
        next_run_date = datetime.strptime(next_run_str, "%Y-%m-%d")
        days_until = (next_run_date - today).days

        workflow["days_until"] = days_until
        workflow["next_run_display"] = format_countdown(days_until, next_run_date)
    else:
        workflow["days_until"] = 999
        workflow["next_run_display"] = "Not scheduled"

# Sort by next run (soonest first)
workflows_sorted = sorted(workflows, key=lambda w: w["days_until"])
```

### Step 3: Format Schedule Display

```python
def format_schedule(workflow):
    """Convert recurrence pattern to human-readable format"""
    recurrence = workflow.get("recurrence", "Unknown")

    patterns = {
        "daily": "Daily",
        "every_monday": "Mon",
        "every_tuesday": "Tue",
        "every_wednesday": "Wed",
        "every_thursday": "Thu",
        "every_friday": "Fri",
        "1st_of_month": "1st @",
        "15th_of_month": "15th @",
        "last_day_of_month": "Last day @"
    }

    schedule_display = patterns.get(recurrence, recurrence)

    # Append time if available
    if "schedule_time" in workflow:
        schedule_display += f" {workflow['schedule_time']}"
    else:
        # Default times based on recurrence
        if "monday" in recurrence:
            schedule_display += " 6am"
        elif "friday" in recurrence:
            schedule_display += " 8am"

    return schedule_display
```

### Step 4: Display Table

```
┌─ SCHEDULED ROUTINES DASHBOARD ──────────────────────────────────────┐
│                                                                      │
│ ID                       │ Name                  │ Schedule          │
│──────────────────────────┼───────────────────────┼───────────────────│
│ monday-cleanup           │ System Cleanup        │ Mon 6am           │
│ leroy-weekly-reports    │ LeRoy Factory        │ Fri 8am           │
│ weekly-crm-sales     │ your CRM Sales Report  │ Mon 8am           │
│ monthly-pipeline-check   │ Pipeline Health       │ 1st @ 9am         │
│                                                                      │
│ Total: {count} routines                                              │
│ Next: {next_routine_name} ({next_run_display})                       │
│                                                                      │
│ {status_indicators_if_any_disabled}                                  │
└──────────────────────────────────────────────────────────────────────┘

Commands:
  • "details {id}" - View execution history and full details
  • "cancel {id}" - Delete routine (removes from all locations)
  • "pause {id}" - Temporarily disable (keeps configuration)
  • "run scheduled {id}" - Manual trigger for testing

Create new routine: "schedule this" or "create routine"
```

**Status Indicators:**
```
If any workflows disabled:
  ⚠️  1 routine disabled: {disabled_routine_name}
      Enable with: "enable {id}"
```

### Step 5: Additional Context

Display helpful information:
```
Recent Executions (last 24 hours):
  • {routine_name} - {time} ago - {status icon}

Upcoming (next 7 days):
  • {routine_name} - {date} at {time}
  • {routine_name} - {date} at {time}
```

---

## Detailed View (Individual Routine)

Triggered by: `"details {routine_id}"`

### Step 1: Find Routine

```python
routine_id = extract_routine_id_from_prompt()
registry = load_json(registry_path)
workflow = find_by_id(registry["workflows"], routine_id)

if not workflow:
    print(f"Routine '{routine_id}' not found.")
    print("Available routines:")
    for w in registry["workflows"]:
        print(f"  • {w['id']}: {w['name']}")
    exit()
```

### Step 2: Load Execution History

```python
# Check state.json for recent execution
state = load_json("session/state.json")
recent_execution = state.get("scheduled_execution_history", [])

# Filter to this routine
history = [e for e in recent_execution if e["routine_id"] == routine_id]

# Sort by timestamp (most recent first)
history_sorted = sorted(history, key=lambda e: e["executed_at"], reverse=True)

# Limit to last 5
history_display = history_sorted[:5]
```

### Step 3: Calculate Stats

```python
total_executions = len(history)
success_count = len([e for e in history if e["status"] == "completed"])
failure_count = len([e for e in history if e["status"] == "failed"])

if total_executions > 0:
    success_rate = (success_count / total_executions) * 100
    avg_duration = sum([e.get("duration_seconds", 0) for e in history]) / total_executions
else:
    success_rate = 0
    avg_duration = 0
```

### Step 4: Display Detailed View

```
┌─ ROUTINE: {routine_id} ──────────────────────────────────────────────┐
│                                                                      │
│ Name: {workflow["name"]}                                             │
│ Skill: {workflow["skill_path"]}                                      │
│ Schedule: {format_schedule(workflow)}                                │
│ Status: {ACTIVE | DISABLED}                                          │
│ Created: {workflow.get("created", "Unknown")}                        │
│                                                                      │
│ Next Run: {workflow["next_run"]} at {time}                           │
│ Last Run: {workflow.get("last_run", "Never")} ({last_status})        │
│                                                                      │
│ Recipients:                                                          │
│   To: {", ".join(workflow["recipients"]["to"])}                      │
│   CC: {", ".join(workflow["recipients"]["cc"])}                      │
│   {god_mode_indicator if workflow.get("god_mode_cc") else ""}       │
│                                                                      │
│ Stats:                                                               │
│   Total executions: {total_executions}                               │
│   Success rate: {success_rate:.1f}%                                  │
│   Avg duration: {avg_duration:.0f}s                                  │
│                                                                      │
│ Execution History (last 5):                                          │
│   {timestamp_1} {status_icon_1} {duration_1}s                        │
│   {timestamp_2} {status_icon_2} {duration_2}s                        │
│   {timestamp_3} {status_icon_3} {duration_3}s                        │
│   ...                                                                │
│                                                                      │
│ Files:                                                               │
│  • Registry: skills/routines/schedule-registry.json                  │
│  • Task: Task Scheduler → Claude\{task_name}                         │
│  • Memory: memory/Routines/{routine_id}.md                    │
│  • Logs: automation/logs/{routine_id}-*.log                          │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘

Commands:
  • "run scheduled {id}" - Manual trigger
  • "cancel {id}" - Delete routine
  • "pause {id}" - Disable temporarily
  • "edit {id}" - Modify schedule or recipients
```

**Status Icons:**
```
✅ - Success
❌ - Failed
⚠️ - Partial success / timeout
🔄 - Running
```

---

## Helper Functions

### Format Countdown

```python
def format_countdown(days_until, next_run_date):
    """Human-readable countdown"""
    if days_until < 0:
        return "Overdue"
    elif days_until == 0:
        return "Today"
    elif days_until == 1:
        return "Tomorrow"
    elif days_until <= 7:
        return f"in {days_until} days"
    else:
        # Display date
        return next_run_date.strftime("%b %d")
```

### Format Duration

```python
def format_duration(seconds):
    """Human-readable duration"""
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        minutes = seconds // 60
        return f"{minutes}m {seconds % 60}s"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours}h {minutes}m"
```

---

## Integration with Memory System

The dashboard can optionally fetch additional context from memory:

```python
# Check if memory file exists
memory_path = f"~/Projects\\memory\\Routines\\{routine_id}.md"

if file_exists(memory_path):
    memory_content = read_file(memory_path)

    # Extract purpose from memory
    purpose = extract_frontmatter(memory_content, "purpose")

    # Display in detailed view
    print(f"Purpose: {purpose}")
```

---

## Error Handling

| Error | Response |
|-------|----------|
| **Registry file not found** | "Schedule registry not found. No routines configured yet. Create one with 'schedule this'." |
| **Empty registry** | "No scheduled routines found. Create your first: 'schedule this'." |
| **Routine ID not found** | Display list of available routines with IDs |
| **Malformed registry JSON** | "Registry file corrupted. Please check: {path}" |
| **Memory file not found** | Display without memory context (non-critical) |

---

## Example Output

**Summary View:**
```
┌─ SCHEDULED ROUTINES DASHBOARD ──────────────────────────────────────┐
│                                                                      │
│ ID                       │ Name                  │ Schedule          │
│──────────────────────────┼───────────────────────┼───────────────────│
│ monday-cleanup           │ System Cleanup        │ Mon 6am           │
│ leroy-weekly-reports    │ LeRoy Factory        │ Fri 8am           │
│ weekly-crm-sales     │ your CRM Sales Report  │ Mon 8am           │
│ monthly-pipeline         │ Pipeline Health       │ 1st @ 9am         │
│                                                                      │
│ Total: 4 routines                                                    │
│ Next: monday-cleanup (in 6 days)                                     │
└──────────────────────────────────────────────────────────────────────┘

Recent Executions:
  • LeRoy Factory - 2 days ago - ✅ Success (342s)
  • System Cleanup - 8 days ago - ✅ Success (67s)

Commands: "details {id}", "cancel {id}", "schedule this"
```

**Detailed View:**
```
┌─ ROUTINE: weekly-crm-sales ──────────────────────────────────────┐
│                                                                      │
│ Name: Weekly your CRM Sales Report                                    │
│ Skill: routines/crm-report.md                                    │
│ Schedule: Every Monday at 8:00 AM                                    │
│ Status: ACTIVE                                                       │
│ Created: 2026-01-14                                                  │
│                                                                      │
│ Next Run: 2026-01-20 at 08:00                                        │
│ Last Run: 2026-01-13 at 08:00 (✅ Success, 127s)                     │
│                                                                      │
│ Recipients:                                                          │
│   To: you@example.com, you@example.com               │
│   CC: you@example.com                                         │
│                                                                      │
│ Stats:                                                               │
│   Total executions: 8                                                │
│   Success rate: 100.0%                                               │
│   Avg duration: 131s                                                 │
│                                                                      │
│ Execution History (last 5):                                          │
│   2026-01-13 08:00 ✅ 127s                                           │
│   2026-01-06 08:00 ✅ 134s                                           │
│   2025-12-30 08:00 ✅ 129s                                           │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

*Routine Dashboard v1.0 | Full Visibility into Scheduled Automation*
