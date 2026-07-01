---
user-invocable: false
---

# Deadline Calendar Automation

**Trigger:** AUTOMATIC - runs during memory consolidation when notes with deadlines are created

**Purpose:** Automatically create Google Calendar reminders for decision notes and follow-up items with deadlines.

---

## Overview

**Problem Solved:** User creates notes with deadline metadata but no calendar reminder gets created. User relies on calendar for visibility, not just memory vault.

**Solution:** After writing any note with a deadline field, automatically create a corresponding calendar event.

**Philosophy:** The system should know that deadlines → calendar events. No manual step required.

---

## Auto-Trigger During Consolidation

**Integration Point:** memory-consolidation.md → Step 9.5 (after writing notes, before email notification)

**Detection:**
1. After writing note to vault
2. Parse frontmatter for `deadline:` field
3. If deadline exists → extract date/time
4. Check if calendar event already exists for this note
5. If not exists → create calendar event
6. Log event ID to state.json for tracking

---

## Deadline Field Specification

**Frontmatter Format:**
```yaml
---
# ... standard fields ...
deadline:
  date: "2026-01-29"           # YYYY-MM-DD (REQUIRED)
  time: "09:00"                # HH:MM in EST (OPTIONAL - defaults to 09:00)
  action: "Follow up with Kim if check not received"  # What to do (OPTIONAL)
  reminder_hours: 24           # Hours before deadline to remind (OPTIONAL - defaults to 0 = day-of)
---
```

**Examples:**

**Simple deadline (date only):**
```yaml
deadline:
  date: "2026-02-15"
```
→ Creates reminder on 2026-02-15 at 9:00 AM EST

**Full deadline spec:**
```yaml
deadline:
  date: "2026-01-29"
  time: "14:00"
  action: "Contact Kim Cravish if check not received"
  reminder_hours: 24
```
→ Creates reminder on 2026-01-28 at 14:00 EST (24h before deadline)

---

## Calendar Event Creation Algorithm

```python
import json
from datetime import datetime, timedelta

def create_deadline_calendar_event(note_path, frontmatter, state):
    """
    Create Google Calendar event for note with deadline.

    Args:
        note_path: Path to note file (for reference)
        frontmatter: Dict with parsed YAML frontmatter
        state: Current state.json data

    Returns:
        event_id: Google Calendar event ID if created, None if skipped
    """
    # STEP 1: Check if note has deadline field
    deadline = frontmatter.get("deadline")
    if not deadline:
        return None

    # STEP 2: Extract deadline components
    deadline_date_str = deadline.get("date")
    deadline_time_str = deadline.get("time", "09:00")  # Default 9am
    action = deadline.get("action", "")
    reminder_hours = deadline.get("reminder_hours", 0)  # Default day-of

    if not deadline_date_str:
        print(f"[DEADLINE] Skipping {note_path} - no date specified")
        return None

    # STEP 3: Parse deadline datetime
    try:
        deadline_dt = datetime.fromisoformat(f"{deadline_date_str}T{deadline_time_str}:00")
    except ValueError as e:
        print(f"[DEADLINE] Invalid date/time format: {e}")
        return None

    # STEP 4: Calculate reminder datetime (apply offset)
    reminder_dt = deadline_dt - timedelta(hours=reminder_hours)

    # STEP 5: Build calendar event details
    note_title = frontmatter.get("title") or extract_title_from_note(note_path)

    # Event title format
    event_title = f"⚠️ {note_title}"
    if action:
        event_title += f" - {action}"

    # Event description (link back to note)
    event_description = f"Deadline: {deadline_date_str}\n"
    if action:
        event_description += f"Action: {action}\n"
    event_description += f"\nSource note: {note_path}"

    # Start/end times (30-minute reminder window)
    start_iso = reminder_dt.strftime("%Y-%m-%dT%H:%M:%S-05:00")
    end_dt = reminder_dt + timedelta(minutes=30)
    end_iso = end_dt.strftime("%Y-%m-%dT%H:%M:%S-05:00")

    # STEP 6: Check if event already exists (avoid duplicates)
    if "deadline_calendar_events" not in state:
        state["deadline_calendar_events"] = {}

    # Use note path as unique key
    if note_path in state["deadline_calendar_events"]:
        existing_event_id = state["deadline_calendar_events"][note_path]
        print(f"[DEADLINE] Calendar event already exists for {note_path}: {existing_event_id}")
        return existing_event_id

    # STEP 7: Create calendar event via MCP
    # CRITICAL: Must use MCPSearch to load tool first:
    # MCPSearch(query="select:mcp__email-primary__calendar_createEvent")

    try:
        result = mcp__email-primary__calendar_createEvent(
            calendarId="primary",
            summary=event_title,
            start={"dateTime": start_iso},
            end={"dateTime": end_iso}
        )

        event_id = result.get("id")
        event_link = result.get("htmlLink")

        # STEP 8: Store event ID in state (for deduplication)
        state["deadline_calendar_events"][note_path] = {
            "event_id": event_id,
            "event_link": event_link,
            "created_at": datetime.utcnow().isoformat() + "Z",
            "deadline_date": deadline_date_str,
            "reminder_date": reminder_dt.strftime("%Y-%m-%d")
        }

        print(f"[DEADLINE] Created calendar event: {event_title}")
        print(f"  Event ID: {event_id}")
        print(f"  Reminder: {reminder_dt.strftime('%Y-%m-%d %H:%M')}")

        return event_id

    except Exception as e:
        print(f"[DEADLINE] Failed to create calendar event: {e}")
        return None


# INTEGRATION POINT: Called from memory-consolidation.md step 9.5
def process_deadline_notes(notes_written, state):
    """
    Scan newly written notes for deadlines and create calendar events.

    Args:
        notes_written: List of note paths just written to vault
        state: Current state.json data

    Returns:
        int: Number of calendar events created
    """
    # CRITICAL: Load MCP tool FIRST (before loop)
    # MCPSearch(query="select:mcp__email-primary__calendar_createEvent")

    events_created = 0

    for note_path in notes_written:
        # Read note to extract frontmatter
        with open(note_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Parse frontmatter
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                import yaml
                frontmatter = yaml.safe_load(parts[1])

                # Check for deadline and create event
                event_id = create_deadline_calendar_event(note_path, frontmatter, state)

                if event_id:
                    events_created += 1

    # Update state.json with new event mappings
    with open(".claude/session/state.json", "w") as f:
        json.dump(state, f, indent=2)

    return events_created
```

---

## State Tracking

**Storage:** `.claude/session/state.json`

**Structure:**
```json
{
  "deadline_calendar_events": {
    "Claude/Decisions/ExampleClient-Payment-Follow-up-Jan29.md": {
      "event_id": "700ms3jv729qglmno1g76fsktc",
      "event_link": "https://www.google.com/calendar/event?eid=...",
      "created_at": "2026-01-26T18:11:17Z",
      "deadline_date": "2026-01-29",
      "reminder_date": "2026-01-29"
    }
  }
}
```

**Why Track Event IDs:**
- Prevents duplicate calendar events if consolidation runs twice
- Allows updating/deleting events if note deadline changes
- Audit trail of automated calendar entries

---

## Integration with Memory Consolidation

**Updated Flow (memory-consolidation.md):**

1. Extract key learnings (existing)
2. Validate tags (existing)
3. Remove old versions (existing)
4. Write structured notes (existing)
5. Update memory index (existing)
6. Update state (existing)
7. **NEW:** Check for deadlines and create calendar events
8. Update checkpoint timestamp (existing)
9. Email notification (existing)
10. Flush metrics (existing)

**Code Addition to memory-consolidation.md:**

```python
# Step 6.5: Process deadline notes (NEW)
if notes_written:
    # Load calendar MCP tool
    MCPSearch(query="select:mcp__email-primary__calendar_createEvent")

    # Create calendar events for deadline notes
    events_created = process_deadline_notes(notes_written, state)

    if events_created > 0:
        print(f"[DEADLINE] Created {events_created} calendar events")
```

---

## User Experience

**Before (Manual):**
1. User creates decision note with deadline
2. User manually checks calendar
3. User manually creates reminder
4. User forgets to do this → misses deadline

**After (Automatic):**
1. User creates decision note with deadline field
2. System automatically creates calendar reminder
3. User sees reminder in calendar (their preferred view)
4. No manual step required

**Example:**

User: "Note that I need to follow up with ExampleClient on Thursday if check doesn't arrive"

System:
1. Creates `Decisions/ExampleClient-Payment-Follow-up-Jan29.md`
2. Includes deadline field: `date: "2026-01-29"`
3. Automatically creates calendar event "⚠️ ExampleClient Payment Follow-up"
4. User sees it in calendar without asking

---

## Error Handling

**If calendar creation fails:**
- Log error to state.json
- Continue consolidation (don't block)
- User still has note in vault
- Can manually create calendar entry if needed

**If duplicate event detected:**
- Skip creation
- Use existing event ID from state
- Log "Calendar event already exists"

**If deadline format invalid:**
- Log warning with note path
- Skip calendar creation
- Note still saved to vault

---

## Future Enhancements

**Phase 2: Deadline Updates**
- If note deadline changes → update calendar event
- If note deleted → delete calendar event
- Sync vault ↔ calendar bidirectionally

**Phase 3: Smart Defaults**
- Learn user's preferred reminder times
- Auto-suggest deadline for common patterns
- Batch create reminders for multiple deadlines

**Phase 4: Recurring Deadlines**
- Support `deadline.recurring: "monthly"`
- Create series of calendar events
- Track completion in note updates

---

## Related Skills

- `meta/memory-consolidation.md` - Calls this skill automatically
- `meta/secretary-memory.md` - Pre-meeting briefs show upcoming deadlines
- `integrations/google-calendar.md` - Calendar MCP integration

---

## Testing Checklist

- [ ] Create note with simple deadline (date only)
- [ ] Verify calendar event created at 9am on deadline date
- [ ] Create note with full deadline spec (date, time, action, reminder_hours)
- [ ] Verify calendar event created at correct time with offset
- [ ] Run consolidation twice on same note
- [ ] Verify no duplicate calendar events created
- [ ] Create note without deadline field
- [ ] Verify no calendar event created (skipped correctly)
- [ ] Test invalid date format
- [ ] Verify error logged, consolidation continues

---

*Deadline Calendar Automation v1.0*
*Automatic calendar reminder creation from note deadlines*
