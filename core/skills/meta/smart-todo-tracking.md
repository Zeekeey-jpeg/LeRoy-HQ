# Smart Todo Cross-Referencing System

## Purpose
Intelligent todo tracking that automatically detects completions and suggests new tasks based on email activity, calendar events, and memory notes.

---

## When to Run

**Auto-triggered during:**
- Morning briefing (after loading one-off-reminders.json)
- Session start (when returning to work)
- After major email sends
- After calendar events complete

**Manual trigger:** "check todos" or "todo status"

---

## Detection Algorithms

### 1. Email Evidence (Primary)

Check bash history and Gmail sent folder for evidence:

```python
# Search bash history for email sends
bash_history = Bash("history | grep 'send_mail' | tail -20")

# Search Gmail sent folder for matching contacts
gmail_sent = mcp__email-primary__search_mail(
    query=f"in:sent to:{email_address} after:{yesterday}",
    maxResults=50
)

# Cross-reference with todo context
for todo in active_todos:
    if todo.get('email'):
        # Check if email was sent to this contact
        if email_in_sent_folder(todo['email'], gmail_sent):
            suggest_completion(todo, evidence="Email sent")
```

### 2. Memory Note Evidence

```python
# Check if memory notes were created with matching context
memory_notes = search_memory_vault(
    path="~/.claude\\memory\\",
    search_terms=[todo['company'], todo['context']],
    created_after=todo['created']
)

if memory_notes:
    suggest_completion(todo, evidence=f"Memory note created: {memory_notes[0]['title']}")
```

### 3. Calendar Event Evidence

```python
# Check if calendar events occurred with matching contacts
calendar_events = mcp__email-primary__list_events(
    calendarId="primary",
    timeMin=todo['created'],
    timeMax="now"
)

for event in calendar_events:
    if todo.get('email') in [a['email'] for a in event.get('attendees', [])]:
        if event['start'] < now:
            suggest_completion(todo, evidence=f"Meeting occurred: {event['summary']}")
```

### 4. your CRM Activity Evidence

```python
# If todo has crm_tool or crm_tool
if todo.get('crm_tool'):
    # Check for recent activities (notes, emails, calls)
    contact_activity = check_crm_tool(todo['crm_tool'])

    if contact_activity:
        suggest_completion(todo, evidence=f"your CRM activity: {activity_summary}")
```

---

## Completion Suggestion Format

When evidence is found, present to user:

```
================================================================
SMART TODO CHECK
================================================================

COMPLETION DETECTED ({count} items):

[high] Check and send NDA to a client contact
  Evidence: Email sent to contact@exampleclient.com (Jan 25 11:42am)
  → Mark complete? [1] Yes [2] No [3] See email

[high] Back-check Stephen ExampleClient training material
  Evidence: Calendar event "BIM Handoff - Get Started Material" at 10:30am today
  Status: Event in progress
  → Mark complete after meeting? [1] Yes (schedule) [2] No

SUGGESTED NEW TODOS ({count} items):

Based on unread emails:
[ ] Follow up with {contact} on {topic} (from email Jan 25)
    Priority: medium | Context: {email_summary}
    → Add to todos? [1] Yes [2] No

Based on calendar:
[ ] Prepare materials for {meeting} on {date}
    Priority: high | Context: {attendees}
    → Add to todos? [1] Yes [2] No
```

---

## Integration with Morning Routine

Add this to morning.md after reading one-off-reminders.json:

```python
# STEP 4.7: SMART TODO CHECK
# Load smart todo tracking skill
from skills.meta import smart_todo_tracking

# Run cross-reference
todo_results = smart_todo_tracking.check_completions(
    active_todos=active_reminders,
    check_email=True,
    check_calendar=True,
    check_memory=True,
    check_crm=True
)

# Also generate suggestions
new_todo_suggestions = smart_todo_tracking.suggest_new_todos(
    from_emails=True,
    from_calendar=True,
    from_memory=True
)

# Store results for output
smart_todo_data = {
    'completions_detected': todo_results['completions'],
    'new_suggestions': new_todo_suggestions,
    'confidence_scores': todo_results['confidence']
}
```

---

## Output in Morning Briefing

Insert after ONE-OFF REMINDERS section:

```
================================================================
SMART TODO CHECK
================================================================

COMPLETIONS DETECTED:
{IF completions > 0}
{for each completion}
[{priority}] {task}
  Evidence: {evidence_type} - {evidence_summary}
  Confidence: {high/medium/low}
  → Mark complete? [1] Yes [2] No [3] Details

{ELSE}
No automatic completions detected. Review todos manually.
{END IF}

NEW TODO SUGGESTIONS:
{IF suggestions > 0}
Based on recent activity:

{for each suggestion}
[ ] {suggested_task}
    Source: {email/calendar/memory}
    Priority: {suggested_priority}
    Context: {brief_context}
    → Add? [1] Yes [2] No

{ELSE}
No new todo suggestions at this time.
{END IF}
```

---

## Confidence Scoring

| Confidence | Criteria | Auto-mark? |
|------------|----------|------------|
| **High** | Direct email sent + calendar event occurred | Suggest auto-mark |
| **Medium** | Email sent OR calendar event OR memory note | Prompt user |
| **Low** | Indirect evidence (related activity) | Show but don't prompt |

---

## User Actions

### On Completion Detection

```python
if user_selects("Yes"):
    # Mark todo as complete
    todo['completed'] = True
    todo['completed_at'] = now
    todo['completion_evidence'] = evidence

    # Update one-off-reminders.json
    save_reminders(reminders_data)

    # Log to memory vault (optional)
    if significant:
        memory_consolidation.log_completion(todo)

if user_selects("Details"):
    # Show full evidence
    display_evidence_details(todo, evidence)
```

### On New Todo Suggestion

```python
if user_selects("Yes"):
    # Generate todo ID
    new_id = generate_todo_id()

    # Create todo with suggested values
    new_todo = {
        'id': new_id,
        'created': now,
        'task': suggested_task,
        'priority': suggested_priority,
        'due_date': suggested_due_date,
        'context': suggestion_context,
        'completed': False,
        'source': 'auto_suggested'
    }

    # Add to one-off-reminders.json
    reminders_data['reminders'].append(new_todo)
    save_reminders(reminders_data)
```

---

## Performance Targets

| Operation | Target Time |
|-----------|-------------|
| Email history check | <2 sec |
| Memory vault search | <500ms |
| Calendar event check | <1 sec |
| your CRM activity check | <3 sec |
| **Total** | **<7 sec** |

Run in parallel when possible to hit 3-4 sec total.

---

## Error Handling

| Issue | Response |
|-------|----------|
| Gmail API unavailable | Skip email evidence, use other sources |
| Calendar API unavailable | Skip calendar evidence |
| Memory vault unreadable | Skip memory evidence |
| your CRM API unavailable | Skip your CRM evidence |
| All sources fail | Display "Smart check unavailable - review manually" |

---

## Future Enhancements

1. **ML confidence scoring** - Learn from user acceptance/rejection patterns
2. **Priority prediction** - Suggest priorities based on urgency signals
3. **Due date inference** - Extract dates from email context
4. **Recurring todo detection** - Identify patterns and suggest automation
5. **Dependency detection** - Link todos that block each other

---

*Last Updated: 2026-01-26*
*Author: the-user*
*Version: 1.0 - Initial smart todo tracking system*
