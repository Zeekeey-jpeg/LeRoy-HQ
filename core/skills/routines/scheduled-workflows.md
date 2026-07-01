# Scheduled Workflows

> **Trigger keywords:** scheduled, recurring, every monday, monthly, weekly, run report, workflow schedule, next run

---

## Purpose

Manage recurring workflows with calendar-aware scheduling. Integrates with morning routine to show upcoming tasks and prompt for execution on due dates.

---

## Schedule Registry

**Location:** `routines/schedule-registry.json`

All recurring workflows are tracked in this registry with:
- Workflow name and skill path
- Recurrence pattern
- Next run date
- Last run date
- Enabled status

---

## Recurrence Patterns

| Pattern | Code | Example |
|---------|------|---------|
| Daily | `daily` | Every day |
| Weekly (specific day) | `every_monday` | Every Monday |
| Monthly (date) | `1st_of_month` | 1st of each month |
| Monthly (date) | `15th_of_month` | 15th of each month |
| Monthly (weekday) | `3rd_monday` | 3rd Monday of month |
| Monthly (weekday) | `last_friday` | Last Friday of month |
| Custom | `custom` | User-defined |

### Weekday Calculation Reference

```yaml
2026 Reference (Jan 1 = Wednesday):
  1st Monday:  Day 6 (Jan 6, Feb 3, Mar 2...)
  2nd Monday:  Day 13 (Jan 13, Feb 10...)
  3rd Monday:  Day 20 (Jan 20, Feb 17...)
  4th Monday:  Day 27 (Jan 27, Feb 24...)
  Last Monday: Varies by month length
```

---

## Morning Routine Integration

### Display Format

When morning routine runs, read `schedule-registry.json` and display:

```
📅 SCHEDULED WORKFLOWS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  TODAY      Weekly Pipeline Check
             Ready to run? [1] Yes [2] Skip [3] Reschedule

  2 days     Vendor Status Update (Friday)
  5 days     Monthly Sales Report (Jan 13)
  7 days     3rd Monday ticketing Cleanup (Jan 15)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Days-Away Calculation

```yaml
For each workflow in registry:
  1. Parse next_run date
  2. Calculate days until next_run from today
  3. Sort by days ascending
  4. Display:
     - 0 days = "TODAY" (with run prompt)
     - 1 day = "Tomorrow"
     - 2-7 days = "X days"
     - >7 days = Don't show in morning (optional: show in weekly view)
```

### Day-Of Prompt

When workflow is due (days = 0):

```
[SCHEDULED] Weekly Pipeline Check is due today

This workflow: [brief description from skill file]

Ready to run?
[1] Yes - execute now
[2] Skip - mark as skipped, keep schedule
[3] Reschedule - move to tomorrow
[4] Disable - turn off recurring schedule
```

---

## Adding Scheduled Workflows

### Method 1: After Workflow Completion (Auto-Builder)

When auto-builder saves a new workflow skill:

```
[AUTO-BUILD] Created: workflows/vendor-update.md

Is this workflow recurring?
[1] No - one-time only
[2] Yes - set schedule

→ User selects [2]

How often should this run?
[1] Weekly - Every Monday
[2] Weekly - Every Friday
[3] Monthly - 1st of month
[4] Monthly - 15th of month
[5] Monthly - Specific weekday (e.g., 3rd Monday)
[6] Custom - describe your schedule

→ User selects [5]

Which weekday pattern?
[1] 1st Monday    [5] 1st Friday
[2] 2nd Monday    [6] 2nd Friday
[3] 3rd Monday    [7] 3rd Friday
[4] 4th Monday    [8] Last Friday

→ User selects [3]

Added to schedule:
  Name: Vendor Update
  Recurrence: 3rd Monday of each month
  Next run: January 20, 2026 (12 days)
```

### Method 2: Manual Registration

User says: "Schedule this workflow for every Monday"

```yaml
Process:
  1. Identify workflow skill path
  2. Determine recurrence pattern
  3. Calculate next run date
  4. Add entry to schedule-registry.json
  5. Confirm to user
```

### Method 3: Post-Workflow Request

After running a workflow, user says: "I need this every 3rd Monday"

```yaml
Process:
  1. Identify the workflow just completed
  2. Parse recurrence: "3rd Monday" → 3rd_monday
  3. Calculate next 3rd Monday
  4. Add to registry
  5. Confirm schedule
```

---

## Managing Scheduled Workflows

### View All Scheduled

User: "Show my scheduled workflows" or "What's on my schedule?"

```
📅 ALL SCHEDULED WORKFLOWS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

| Workflow                  | Recurrence      | Next Run   | Last Run   |
|---------------------------|-----------------|------------|------------|
| Weekly Pipeline Check     | Every Monday    | Jan 13     | Jan 6      |
| Monthly Sales Report      | 1st of month    | Feb 1      | Jan 1      |
| Vendor Update             | 3rd Monday      | Jan 20     | Dec 16     |
| ticketing Ticket Summary         | Every Friday    | Jan 10     | Jan 3      |

[1] Run one now
[2] Edit schedule
[3] Disable workflow
[4] Delete from schedule
```

### Edit Schedule

```
Editing: Weekly Pipeline Check
Current: Every Monday

New schedule:
[1] Keep current (Every Monday)
[2] Change to different day
[3] Change to monthly
[4] Custom pattern
```

### After Running Scheduled Workflow

```
✅ Weekly Pipeline Check completed

Updating schedule:
  Last run: January 8, 2026
  Next run: January 13, 2026 (Monday)

[Schedule updated in registry]
```

---

## Registry Operations

### Calculate Next Run

```yaml
Function: calculate_next_run(recurrence, from_date)

Cases:
  daily:
    return from_date + 1 day

  every_monday:
    return next Monday from from_date

  1st_of_month:
    if today < 1st: return 1st of this month
    else: return 1st of next month

  3rd_monday:
    find 3rd Monday of this month
    if passed: find 3rd Monday of next month
    return result
```

### Update Registry After Run

```yaml
After workflow execution:
  1. Find workflow in registry by id
  2. Set last_run = today
  3. Calculate new next_run based on recurrence
  4. Save registry
```

---

## Integration Points

| System | Integration |
|--------|-------------|
| `morning.md` | Reads registry, displays upcoming, prompts for due |
| `auto-builder.md` | Offers scheduling after workflow save |
| `schedule-registry.json` | Source of truth for all schedules |
| Individual workflow skills | Executed when user confirms |

---

## Examples

### Example: New Weekly Workflow

```
User completes your CRM ticket summary workflow

[AUTO-BUILD] Pattern detected: ticketing ticket aggregation
Save as skill? [1] Yes [2] No → Yes

Created: workflows/cw-ticket-summary.md

Is this recurring? [1] No [2] Yes → Yes
How often? → Every Friday

✅ Scheduled: ticketing Ticket Summary
   Every Friday, next run: January 10, 2026
```

### Example: Morning Shows Due Workflow

```
☀️ MORNING BRIEFING - Wednesday, January 8, 2026

📅 SCHEDULED WORKFLOWS
━━━━━━━━━━━━━━━━━━━━━━━
  TODAY      Monthly Report Sync
             Ready to run? [1] Yes [2] Skip

  2 days     Weekly ticketing Summary (Friday)
  5 days     Pipeline Check (Monday)
━━━━━━━━━━━━━━━━━━━━━━━

[User selects 1]

Running: Monthly Report Sync...
[Executes workflows/monthly-report-sync.md]

✅ Complete. Next run: February 8, 2026
```

---

*Scheduled workflows v1.0 | Calendar-aware recurring tasks*
