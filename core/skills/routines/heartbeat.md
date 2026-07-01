# Heartbeat - Proactive Check-in System

**Purpose:** Proactive but non-annoying check-ins for Clawdbot/WhatsApp to surface urgent items without constant notifications.

**Philosophy:** Be helpful without annoying. HEARTBEAT_OK = silent. Action needed = brief emoji summary.

## Triggers

| Trigger | Action |
|---------|--------|
| "heartbeat", "check in", "status check" | Manual heartbeat check |
| Auto-trigger | 3+ hours since last (work hours 9am-6pm EST) |
| Auto-trigger | 12+ hours since last (anytime) |

## Auto-Trigger Detection

**CRITICAL:** Only auto-trigger in Clawdbot/WhatsApp sessions.

```python
# Check if auto-trigger conditions met
import json
from datetime import datetime, timedelta
from pathlib import Path

state_file = Path('.claude/session/heartbeat-state.json')
if not state_file.exists():
    # First run - no auto-trigger
    should_auto_trigger = False
else:
    hb_state = json.load(state_file.open())
    last_hb = hb_state.get('last_heartbeat')

    if not last_hb:
        should_auto_trigger = False
    else:
        last_time = datetime.fromisoformat(last_hb)
        now = datetime.now()
        hours_since = (now - last_time).total_seconds() / 3600

        # Work hours: 9am-6pm EST
        is_work_hours = 9 <= now.hour < 18

        if is_work_hours and hours_since >= 3:
            should_auto_trigger = True
        elif hours_since >= 12:
            should_auto_trigger = True
        else:
            should_auto_trigger = False
```

## Rotation Logic

Check oldest task first based on `last_checks` timestamps.

**Rotation order:** email → calendar → crm → git

**Algorithm:**
1. Load heartbeat-state.json
2. Find task with oldest (or null) last_check timestamp
3. Check that task
4. Update last_check for checked task
5. Update last_heartbeat timestamp
6. Increment counters

## Task Checks

### Email Check (Gmail MCP)

**What to check:**
- Unread emails in last 3 hours
- Filter: Exclude newsletters, notifications
- Priority: Emails from known contacts (your CRM, clients, team)

**MCP calls:**
```javascript
// Use mcp__email-primary__search_mail
{
  query: "is:unread newer_than:3h",
  maxResults: 20
}
```

**Threshold for action:**
- 0-2 unread: HEARTBEAT_OK
- 3-5 unread: 📧 (show count)
- 6+ unread: 📧 + list top 3 senders

### Calendar Check (Google Calendar MCP)

**What to check:**
- Meetings in next 2 hours
- All-day events today
- Conflicts or double-bookings

**MCP calls:**
```javascript
// Use mcp__email-primary__list_events
{
  calendarId: "primary",
  timeMin: now,
  timeMax: now + 2 hours,
  singleEvents: true,
  orderBy: "startTime"
}
```

**Threshold for action:**
- No meetings in 2h: HEARTBEAT_OK
- 1 meeting in <30 min: 📅 + meeting name + time
- Multiple meetings: 📅 + count + next meeting

### your CRM Check (your CRM MCP)

**What to check:**
- Open deals updated in last 3 hours
- New contacts added
- Tasks due today

**MCP calls:**
```javascript
// Use mcp__crm__crm_tool
{
  filterGroups: [{
    filters: [{
      propertyName: "hs_lastmodifieddate",
      operator: "GTE",
      value: (now - 3h).timestamp()
    }]
  }],
  limit: 100
}
```

**Threshold for action:**
- No updates: HEARTBEAT_OK
- 1-2 updates: 💰 + deal names
- 3+ updates: 💰 + count

### Git Check (Bash)

**What to check:**
- Uncommitted changes
- Unpushed commits
- Unmerged branches

**Commands:**
```bash
git status --porcelain  # Uncommitted changes
git log @{u}.. --oneline  # Unpushed commits
git branch -a --no-merged  # Unmerged branches
```

**Threshold for action:**
- Clean state: HEARTBEAT_OK
- Uncommitted changes: 📝 + file count
- Unpushed commits: 📝 + commit count

## Response Format

### HEARTBEAT_OK Pattern

When nothing urgent found, return exactly:

```
HEARTBEAT_OK
```

**Important:** NO additional text, NO emoji, NO explanation. This allows the system to suppress notifications.

### Action Needed Pattern

When action needed, use emoji summary:

**Format:** `[emoji] [brief description]`

**Examples:**
```
📧 5 unread (3 from clients)
📅 Meeting in 20 min: your organization Standup
💰 2 deals updated: ExampleClient, an LMS Phase 2
📝 3 uncommitted files in your product
```

**Multiple items:**
```
📧 3 unread | 📅 Meeting in 15 min
💰 4 deals updated | 📝 5 uncommitted files
```

**Max length:** 100 chars (WhatsApp constraint)

### Group Chat Intelligence

**CRITICAL:** If last user message contains multiple participants or is clearly a group chat, return HEARTBEAT_OK unless:
- You're explicitly mentioned
- There's a direct question
- There's urgent action for the user

**Detection patterns:**
- Multiple "From:" lines in message
- Names in message that aren't the user
- Previous messages show conversation thread

## State Management

**File:** `.claude/session/heartbeat-state.json`

**Update after each heartbeat:**

```json
{
  "last_checks": {
    "email": "2026-01-25T14:30:00",
    "calendar": "2026-01-25T11:15:00",
    "crm": "2026-01-25T13:45:00",
    "git": "2026-01-25T12:00:00"
  },
  "schedule": {
    "morning": "09:00",
    "midday": "12:00",
    "afternoon": "15:00",
    "evening": "18:00"
  },
  "rotation": ["email", "calendar", "crm", "git"],
  "last_heartbeat": "2026-01-25T14:30:00",
  "heartbeat_count": 47,
  "heartbeat_ok_count": 32,
  "action_needed_count": 15
}
```

**Update logic:**
1. Read current state
2. Determine which task to check (oldest last_check)
3. Perform check
4. Update last_checks[task] = now
5. Update last_heartbeat = now
6. Increment heartbeat_count
7. Increment heartbeat_ok_count OR action_needed_count
8. Write state

## Implementation Steps

### Step 1: Load State

```python
import json
from pathlib import Path
from datetime import datetime

state_file = Path('.claude/session/heartbeat-state.json')
if not state_file.exists():
    # Initialize state
    state = {
        "last_checks": {
            "email": None,
            "calendar": None,
            "crm": None,
            "git": None
        },
        "schedule": {
            "morning": "09:00",
            "midday": "12:00",
            "afternoon": "15:00",
            "evening": "18:00"
        },
        "rotation": ["email", "calendar", "crm", "git"],
        "last_heartbeat": None,
        "heartbeat_count": 0,
        "heartbeat_ok_count": 0,
        "action_needed_count": 0
    }
else:
    state = json.load(state_file.open())
```

### Step 2: Determine Next Task

```python
# Find task with oldest (or null) last_check
from datetime import datetime

last_checks = state['last_checks']
oldest_task = None
oldest_time = None

for task in state['rotation']:
    check_time = last_checks.get(task)
    if check_time is None:
        oldest_task = task
        break
    elif oldest_time is None or check_time < oldest_time:
        oldest_time = check_time
        oldest_task = task

print(f"Checking: {oldest_task}")
```

### Step 3: Perform Check

Execute appropriate check based on task:
- email → Gmail MCP
- calendar → Calendar MCP
- crm → your CRM MCP
- git → Bash commands

### Step 4: Evaluate Results

Determine if HEARTBEAT_OK or action needed based on thresholds.

### Step 5: Update State

```python
now = datetime.now().isoformat()
state['last_checks'][oldest_task] = now
state['last_heartbeat'] = now
state['heartbeat_count'] += 1

if response == "HEARTBEAT_OK":
    state['heartbeat_ok_count'] += 1
else:
    state['action_needed_count'] += 1

# Write state
with state_file.open('w') as f:
    json.dump(state, f, indent=2)
```

### Step 6: Return Response

Return either "HEARTBEAT_OK" or emoji summary.

## Session Detection

**CRITICAL:** Only enable heartbeat for WhatsApp/Clawdbot sessions.

```python
# Check session window from state.json
import json
session_state = json.load(open('.claude/session/state.json'))
session_window = session_state.get('session_window', 'unknown')

if session_window not in ['whatsapp', 'clawdbot']:
    # Desktop session - skip heartbeat
    print("Heartbeat disabled for desktop sessions")
    exit()
```

## Metrics & Tuning

**Target metrics:**
- HEARTBEAT_OK rate: >60% (avoid notification fatigue)
- False positive rate: <5% (action needed but not urgent)
- Response time: <3 seconds (MCP calls included)

**Tuning parameters:**
- Thresholds (unread count, time until meeting, etc.)
- Check frequency (3h work hours, 12h anytime)
- Rotation order (priority order of checks)

## Error Handling

**If MCP call fails:**
- Skip that task, move to next in rotation
- Log error to session/error-log.jsonl
- Return HEARTBEAT_OK (don't annoy user with errors)

**If state.json corrupted:**
- Reinitialize with defaults
- Log warning
- Continue with check

## User Interaction

**User says "details":**
- Show full breakdown of last check
- Include all items found, not just summary
- Use markdown formatting (desktop) or plain text (WhatsApp)

**User says "disable heartbeat":**
- Set flag in state.json to disable auto-trigger
- Manual trigger still works
- Confirm with user

**User says "enable heartbeat":**
- Clear disable flag
- Resume auto-trigger behavior
- Confirm with user

## Integration Points

**Morning routine (routines/morning.md):**
- Runs heartbeat check at start
- Surfaces urgent items in briefing
- Updates heartbeat state

**Memory consolidation:**
- Consolidates heartbeat metrics (OK rate, patterns)
- Updates USER.md if preferences learned
- Tracks notification fatigue signals

## Testing

**Manual trigger test:**
```
User: "heartbeat"
Expected: Either "HEARTBEAT_OK" or emoji summary
```

**Auto-trigger test:**
```
# Wait 3+ hours during work hours
User: "hi"
Expected: Auto-trigger before responding, show result if action needed
```

**Rotation test:**
```
# Run 4 heartbeats
Expected: email → calendar → crm → git (in order)
```

**Group chat test:**
```
User: "[Group message with multiple participants]"
Expected: HEARTBEAT_OK (don't interrupt)
```

---

*Heartbeat v1.0: Helpful without annoying*
