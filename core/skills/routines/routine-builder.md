# Routine Builder

## Trigger

This skill activates when:
- `"schedule this"`
- `"automate this report"`
- `"create routine"`
- `"add to schedule"`

---

## Purpose

Interactive wizard for creating scheduled routines. Guides user through:
1. Naming and describing the routine
2. Selecting recipients (with god mode CC logic)
3. Choosing schedule pattern
4. Previewing configuration
5. Automatic infrastructure creation via background agent

**Result:** Fully configured routine in registry, Task Scheduler, and memory system.

---

## Interactive Workflow

### Step 1: Context Detection

Analyze recent activity to suggest what to schedule:

```python
# Check session state for recent skill execution
recent_skills = get_recent_skills_from_state()

# Check prompt history for last command
last_command = get_last_user_command()

# Detect pattern
if "leroy" in last_command or "weekly reports" in last_command:
    suggested_skill = "workflows/leroy/factory.md"
    suggested_name = "LeRoy Weekly Reports"

elif "hs report" in last_command or "crm report" in last_command:
    suggested_skill = "routines/crm-report.md"
    suggested_name = "your CRM Sales Report"

elif "monday cleanup" in last_command or "cleanup" in last_command:
    suggested_skill = "routines/monday-cleanup.md"
    suggested_name = "Monday System Cleanup"

else:
    # Ask user to specify
    suggested_skill = None
    suggested_name = None
```

Display detected context:
```
📋 Context detected:
   Recent activity: {last_command}
   Suggested skill: {suggested_skill}
   Suggested name: {suggested_name}

Is this correct? [Y/n]
```

If user says no or context not detected:
```
Which skill file should be scheduled?
Examples:
  - routines/crm-report.md
  - workflows/leroy/factory.md
  - routines/monday-cleanup.md

Skill path:
```

### Step 2: Collect Metadata

**Routine Name:**
```
What should we call this routine?
Suggested: {suggested_name or "Weekly Report"}
Name:
```

**Purpose/Description:**
```
Brief description (1 sentence):
Purpose:
```

**Recipients:**
```
Who should receive this report? (comma-separated emails)
Recipients:
```

**God Mode CC Check:**
```python
routine_name_lower = routine_name.lower()
routine_id_lower = generate_id(routine_name).lower()

# Check if "leroy" appears in name or ID
if "leroy" in routine_name_lower or "leroy" in routine_id_lower:
    # Auto-add the-user@ to CC
    cc_recipients = ["you@example.com"]
    god_mode_cc = True

    Display:
    ⚡ God Mode CC Detected
       "leroy" found in routine name
       Auto-adding you@example.com to CC for oversight

else:
    cc_recipients = []
    god_mode_cc = False

# Ask if user wants additional CC
additional_cc = ask("Additional CC recipients? (optional):")
if additional_cc:
    cc_recipients.extend(parse_emails(additional_cc))
```

**Parameters (if applicable):**
```
Should parameters be:
[1] Fixed (always use same settings) - Recommended for automated routines
[2] Prompt (ask for input each time) - For manual trigger flexibility

Choice:
```

### Step 3: Schedule Selection (AskUserQuestion)

Use AskUserQuestion to present schedule options:

```json
{
  "questions": [{
    "question": "How often should this routine run?",
    "header": "Schedule",
    "multiSelect": false,
    "options": [
      {
        "label": "Daily at specific time",
        "description": "Runs every day at the same time (e.g., 6:00 AM daily)"
      },
      {
        "label": "Weekly on specific day",
        "description": "Runs once per week on chosen day (e.g., every Monday at 8:00 AM)"
      },
      {
        "label": "Monthly (1st, 15th, last day)",
        "description": "Runs once per month on a specific day number"
      },
      {
        "label": "Custom (1st Monday, 3rd Friday, etc.)",
        "description": "Advanced: Nth weekday of month"
      }
    ]
  }]
}
```

**Based on selection, collect additional details:**

**If Daily:**
```
What time each day? (HH:MM format, 24-hour)
Time: [suggest: 06:00]
```

**If Weekly:**
```
Which day of the week?
[1] Monday
[2] Tuesday
[3] Wednesday
[4] Thursday
[5] Friday
Day:

What time? (HH:MM format, 24-hour)
Time: [suggest: 08:00]
```

**If Monthly:**
```
Which day of month?
[1] 1st of month
[2] 15th of month
[3] Last day of month
Day:

What time? (HH:MM format, 24-hour)
Time: [suggest: 09:00]
```

**If Custom:**
```
Which occurrence and weekday?
Examples:
  - 1st Monday
  - 3rd Friday
  - Last Monday

Pattern:

What time? (HH:MM format, 24-hour)
Time:
```

**Calculate first run date:**
```python
from datetime import datetime, timedelta

today = datetime.now()

if schedule_type == "daily":
    first_run = today + timedelta(days=1)
    recurrence = "daily"

elif schedule_type == "weekly":
    # Calculate next occurrence of chosen day
    days_ahead = (chosen_day - today.weekday()) % 7
    if days_ahead == 0:
        days_ahead = 7  # If today is the day, schedule for next week
    first_run = today + timedelta(days=days_ahead)
    recurrence = f"every_{weekday_names[chosen_day]}"

elif schedule_type == "monthly":
    if chosen_pattern == "1st":
        recurrence = "1st_of_month"
        # Calculate next 1st of month
        ...
    elif chosen_pattern == "15th":
        recurrence = "15th_of_month"
        ...
    elif chosen_pattern == "last":
        recurrence = "last_day_of_month"
        ...

# Format first_run as YYYY-MM-DD
first_run_str = first_run.strftime("%Y-%m-%d")
```

### Step 4: Preview & Confirm

Generate unique routine ID:
```python
# Slugify name
routine_id = slugify(routine_name)  # "Weekly your CRM Sales" → "weekly-crm-sales"

# Check for conflicts in registry
registry = load_registry()
if routine_id in [w["id"] for w in registry["workflows"]]:
    # Append number
    counter = 2
    while f"{routine_id}-{counter}" in [w["id"] for w in registry["workflows"]]:
        counter += 1
    routine_id = f"{routine_id}-{counter}"
```

Display preview:
```
┌─ ROUTINE PREVIEW ───────────────────────────────────────────────┐
│                                                                  │
│ Name: {routine_name}                                             │
│ ID: {routine_id}                                                 │
│ Skill: {skill_path}                                              │
│ Schedule: {human_readable_schedule}                              │
│ First Run: {first_run_str}                                       │
│                                                                  │
│ Recipients:                                                      │
│   To: {", ".join(to_recipients)}                                 │
│   CC: {", ".join(cc_recipients)}                                 │
│   {god_mode_indicator if god_mode_cc else ""}                   │
│                                                                  │
│ Enabled: Yes                                                     │
│ Parameters: {fixed | prompt}                                     │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘

Build this routine? [Y/n]
```

If user confirms NO:
```
Routine creation cancelled.
Changes discarded.
```

### Step 5: Spawn Builder Agent (Background)

If user confirms YES:

```
✅ Building routine infrastructure...

Spawning background agent to create:
  ✓ Registry entry
  ✓ Task Scheduler XML
  ✓ Task Scheduler import
  ✓ Memory documentation
  ✓ Confirmation email

This will take ~30 seconds. You can continue working.
```

**Spawn builder agent in background:**

```python
agent_context = {
    "task": "Build scheduled routine infrastructure",
    "routine_id": routine_id,
    "routine_name": routine_name,
    "skill_path": skill_path,
    "recurrence": recurrence,
    "first_run": first_run_str,
    "schedule_time": time_str,
    "recipients": {
        "to": to_recipients,
        "cc": cc_recipients,
        "bcc": []
    },
    "god_mode_cc": god_mode_cc,
    "enabled": True,
    "purpose": purpose_description,
    "parameters": parameter_mode
}

agent_prompt = f"""
Create complete infrastructure for scheduled routine:

**Routine Details:**
- ID: {routine_id}
- Name: {routine_name}
- Skill: {skill_path}
- Schedule: {recurrence} at {time_str}
- First run: {first_run_str}

**Tasks to complete:**

1. **Update schedule-registry.json:**
   - Add new workflow entry with all metadata
   - Include recipients object (to, cc, bcc)
   - Set god_mode_cc flag if applicable
   - Validate JSON syntax

2. **Create Task Scheduler XML:**
   - Copy template.xml to task-definitions/{routine_id}.xml
   - Replace {{ROUTINE_ID}} with {routine_id}
   - Replace {{ROUTINE_NAME}} with {routine_name}
   - Configure trigger for {recurrence} at {time_str}
   - Set StartBoundary to {first_run_str}T{time_str}:00

3. **Import Task Scheduler task:**
   - Run: schtasks /Create /XML "path/to/{routine_id}.xml" /TN "Claude\\{task_name}"
   - Verify task created successfully
   - Log Task Scheduler task name

4. **Create Memory documentation:**
   - Write to: memory/Routines/{routine_id}.md
   - Use proper frontmatter (title, tags, routine_id, created, status)
   - Include metadata section
   - Document purpose, parameters, recipients
   - Add placeholders for execution history

5. **Send confirmation email:**
   - To: you@example.com
   - Subject: [ROUTINE CREATED] {routine_name}
   - Include all details: ID, schedule, first run, recipients
   - Include commands: "show scheduled routines", "details {routine_id}"

**Critical:**
- MUST validate all file writes
- MUST verify Task Scheduler import succeeds
- MUST send confirmation email on success
- If ANY step fails, send error email with details

Return: Success message with task name and next run date.
"""

spawn_agent(
    type="builder",
    description="Build routine infrastructure",
    prompt=agent_prompt,
    run_in_background=True
)
```

### Step 6: User Feedback (Immediate)

While agent works in background:
```
✅ Routine creation initiated

Background agent spawned: {agent_id}
Creating infrastructure for: {routine_name}

Estimated completion: 30 seconds
You'll receive email confirmation when ready.

View progress: "show scheduled routines"
```

**When agent completes, they'll see:**
```
✅ Routine created: {routine_id}

Next run: {human_readable_date_time}
Task Scheduler: Claude\{task_name}
Memory: memory/Routines/{routine_id}.md

Commands:
  • "show scheduled routines" - View dashboard
  • "details {routine_id}" - View full details
  • "run scheduled {routine_id}" - Manual trigger (testing)
```

---

## Error Handling

| Error | Response |
|-------|----------|
| **User cancels at any step** | "Routine creation cancelled. No changes made." |
| **Invalid skill path** | "Skill file not found: {path}. Please check path and try again." |
| **Duplicate routine ID** | Auto-append number suffix, show in preview |
| **Invalid schedule time** | "Invalid time format. Use HH:MM (24-hour). Example: 08:00" |
| **Invalid email addresses** | "Invalid email format: {email}. Please use valid email addresses." |
| **Agent spawn fails** | "Failed to spawn builder agent. Error: {error}. Retry?" |
| **Registry write fails** | Agent sends error email with details |
| **Task Scheduler import fails** | Agent sends error email with schtasks output |

---

## God Mode CC Logic

**Automatic the-user@ CC for LeRoy reports:**

```python
def check_god_mode_cc(routine_name, routine_id):
    """
    God Mode Rule: If routine contains 'leroy' in ID or name,
    automatically add you@example.com to CC for oversight.
    """
    name_lower = routine_name.lower()
    id_lower = routine_id.lower()

    if "leroy" in name_lower or "leroy" in id_lower:
        return True, ["you@example.com"]
    else:
        return False, []

# Apply rule
god_mode, auto_cc = check_god_mode_cc(routine_name, routine_id)

if god_mode:
    print("⚡ God Mode CC activated")
    print("   'leroy' detected → you@example.com added to CC")
    cc_recipients.extend(auto_cc)
```

**Display in preview:**
```
Recipients:
  To: you@example.com, you@example.com
  CC: you@example.com ⚡ (god mode oversight)
```

---

## Integration Points

| System | Integration |
|--------|-------------|
| **schedule-registry.json** | Background agent adds new workflow entry |
| **Task Scheduler** | Background agent creates and imports XML definition |
| **Memory System** | Background agent writes to memory/Routines/ |
| **Email** | Background agent sends confirmation to the-user@ |
| **Session State** | Tracks routine creation in progress |

---

## Example Session

```
User: "schedule this report"