# Predictive Business Todo System (v1.0)

> **Philosophy:** Your todo list should maintain itself. Detect tasks automatically, complete them automatically, and predict what's coming next.
> **Trigger:** ALWAYS ACTIVE - runs on every conversation turn
> **Integration:** Post-response analysis + morning briefing + memory system

---

## Purpose

A proactive todo system that:
- Auto-detects tasks from casual conversation
- Prevents duplicate todos
- Auto-completes when actions are taken
- Tracks business rhythms and recurring patterns
- Surfaces upcoming/overdue items proactively
- Learns your workflow and predicts next steps

---

## System Architecture

### Component 1: Conversation Parser (Auto-Detection)

**Runs after EVERY user message - analyzes for task signals**

#### Task Language Patterns

**High Confidence (auto-create immediately):**
```yaml
Explicit Commands:
  - "I need to [action]"
  - "Remind me to [action]"
  - "Don't let me forget to [action]"
  - "Add to my list: [action]"
  - "Todo: [action]"

Examples:
  - "I need to call Jim tomorrow" → Auto-create: "Call Jim"
  - "Remind me to send the invoice" → Auto-create: "Send invoice"
  - "Don't let me forget to follow up with Cathy" → Auto-create: "Follow up with Cathy"
```

**Medium Confidence (confirm before creating):**
```yaml
Implied Tasks:
  - "Should [action]"
  - "Have to [action]"
  - "Need to [action] at some point"
  - "[Person] needs [deliverable]"

Examples:
  - "I should update the proposal" → Suggest: "Update proposal?"
  - "Jim needs the report by Friday" → Suggest: "Send Jim report (Due: Friday)?"
```

**Low Confidence (monitor, don't create):**
```yaml
Casual Mentions:
  - "Might [action]"
  - "Could [action]"
  - "Thinking about [action]"

These are tracked but not converted to todos unless repeated/confirmed
```

#### Action Verb Detection

**Common action verbs that trigger task detection:**
```javascript
const actionVerbs = [
  // Communication
  'email', 'call', 'text', 'message', 'reach out', 'follow up', 'respond', 'reply',

  // Document/Deliverable
  'send', 'submit', 'deliver', 'share', 'upload', 'sign', 'review',

  // Creation
  'create', 'write', 'draft', 'prepare', 'make', 'build',

  // Financial
  'invoice', 'pay', 'bill', 'charge', 'collect payment',

  // Scheduling
  'schedule', 'book', 'set up meeting', 'arrange',

  // Research
  'look into', 'research', 'investigate', 'find out', 'check on',

  // Administrative
  'update', 'fix', 'handle', 'take care of', 'complete'
]
```

### Component 2: Duplicate Prevention Engine

**Before creating new todo, check existing todos across ALL sessions**

```yaml
Duplicate Detection Process:
  1. Extract task intent from parsed message
     Example: "I need to email Kim about payment" → Intent: [email, kim, payment]

  2. Search all task directories for pending todos
     Path: ~/.claude\tasks\*\*.json
     Filter: status == "pending"

  3. Calculate similarity score
     Algorithm:
       - Extract keywords from existing todo subject + description
       - Compare with new task intent keywords
       - Similarity = (matching keywords / total keywords) * 100

  4. Threshold-based decision:
     - Similarity ≥ 80% → DUPLICATE (don't create, reference existing)
     - Similarity 50-79% → RELATED (ask if same or different)
     - Similarity < 50% → NEW (create)

  5. Response format:
     - Duplicate: "Already on your list: 'Email Kim - request ACH payment'"
     - Related: "Similar todo exists: 'Email Kim about invoice' - same task or different?"
     - New: [Create silently, confirm: "✅ Added: Email Kim about payment"]

Examples:
  User: "I need to email Kim"
  Existing: "Email Kim - request ACH payment instead of check"
  → Similarity: 85% (email, kim match)
  → Response: "Already on your list: #3 - Email Kim about payment"

  User: "Need to call Cathy"
  Existing: "Get Cathy to sign the agreement"
  → Similarity: 40% (cathy matches, but call vs sign are different)
  → Response: "✅ Added: Call Cathy" (new task)
```

### Component 3: Auto-Completion via Secretary Integration

**Integrated with secretary-auto-tracking.md Step 1.5**

```yaml
When action is taken:
  1. Extract action details (who, what, when)
  2. Search pending todos for matches (fuzzy match, 60% threshold)
  3. Auto-complete matching todos
  4. Confirm: "✅ Todo completed: {subject}"

Already implemented in secretary-auto-tracking.md Step 1.5
```

### Component 4: Business Rhythm Tracker

**Learns recurring patterns and predicts upcoming tasks**

#### Pattern Learning

**Track task history to identify rhythms:**
```yaml
Data Sources:
  - Completed todos (with completion dates)
  - Email send patterns (via email-intelligence.md)
  - Calendar events (recurring meetings)
  - Memory system (project timelines, milestones)

Pattern Types:
  1. Daily Rhythms
     Example: "Morning email check" (every weekday 8-9am)

  2. Weekly Rhythms
     Example: "Send weekly report" (every Friday)

  3. Monthly Rhythms
     Example: "Send invoices" (1st of every month)
     Example: "Expense reports" (last day of month)

  4. Project-Based Rhythms
     Example: "Follow up with {client}" (3 days after proposal sent)
     Example: "Check on payment" (7 days after invoice sent)

Storage: memory/patterns/business-rhythms.json
```

**Rhythm Detection Algorithm:**
```javascript
// Example: Detect if task is recurring
function detectRhythm(taskHistory) {
  const completions = taskHistory
    .filter(t => t.status === 'completed')
    .map(t => t.completedDate)

  if (completions.length < 3) return null // Need 3+ samples

  // Check for weekly pattern
  const weeklyGaps = calculateDaysBetween(completions)
  if (isCloseToMultiple(weeklyGaps, 7)) {
    return { type: 'weekly', interval: 7, confidence: 0.8 }
  }

  // Check for monthly pattern
  if (isFirstOfMonth(completions)) {
    return { type: 'monthly', day: 1, confidence: 0.9 }
  }

  return null
}
```

#### Predictive Suggestions

**Proactively surface upcoming tasks:**
```yaml
Morning Briefing Integration:
  - "Upcoming today: Email Kim (from your todo list)"
  - "Reminder: Monthly invoicing usually happens today"
  - "Pattern detected: You typically follow up with clients on Mondays"

Threshold-based surfacing:
  - 1 day before predicted date → Yellow flag ⚠️
  - Day of predicted date → Red flag 🔴
  - 1+ days overdue → Critical 🚨

Display in morning briefing:
  📋 **Your Business Rhythm Predictions:**
  - 🔴 TODAY: Send monthly invoices (pattern: 1st of month)
  - ⚠️ TOMORROW: Weekly team check-in (pattern: every Friday)
  - 📊 NEXT WEEK: Expense reports due (pattern: end of month)
```

### Component 5: Proactive Overdue Flagging

**Surface overdue items automatically**

```yaml
When to Flag:
  1. Morning briefing (always show overdue items first)
  2. When user asks "status" or "todo status"
  3. Before end of day (if items still pending)

Overdue Criteria:
  - Todo has dueDate field AND dueDate < today
  - Todo created >7 days ago AND still pending (stale)
  - Pattern-predicted task is >2 days past expected date

Display Format:
  🚨 **OVERDUE (3 items):**
  1. Email Kim - ACH payment request (created 5 days ago)
  2. Research business insurance (created 8 days ago)
  3. Follow up with Jim (due 2 days ago)

Action Prompts:
  - "Want me to help you tackle these now?"
  - "Should I reschedule any of these?"
  - "Mark any as no longer needed?"
```

---

## Execution Flow (Automatic)

### Every Conversation Turn

```mermaid
User Message
  ↓
Parse for Task Language (Component 1)
  ↓
[Task Detected?]
  ├─ YES → Check for Duplicates (Component 2)
  │         ├─ Duplicate Found → Reference existing todo
  │         ├─ Related Found → Ask for clarification
  │         └─ New Task → Create todo silently
  │
  └─ NO → Continue normal conversation

[Tool Use Detected?]
  ├─ Email sent → Auto-complete matching todo (Component 3)
  ├─ Meeting scheduled → Auto-complete matching todo
  ├─ Document signed → Auto-complete matching todo
  └─ Other → Skip
```

### Morning Briefing Integration

```yaml
Order of display:
  1. 🚨 OVERDUE items (Component 5)
  2. 🔴 TODAY predictions (Component 4)
  3. ⚠️ UPCOMING this week (Component 4)
  4. ✅ Recently completed (last 24 hours)
  5. 📋 Full pending list

Example Morning Briefing:
  ================================================================================
  📋 YOUR TODO DASHBOARD
  ================================================================================

  🚨 OVERDUE (2 items):
  1. Email Kim - ACH payment request (5 days old)
  2. Research business insurance (8 days old)

  🔴 TODAY:
  3. Send monthly invoices (pattern: 1st of month)
  4. Follow up with Tom re: Friday meeting

  ⚠️ THIS WEEK:
  5. Weekly team check-in (Friday, predicted)
  6. Expense reports (end of month pattern)

  ✅ COMPLETED YESTERDAY:
  - Responded to Tom's email ✅
  - Created calendar event for Sales Comp AI meeting ✅

  📊 TOTAL: 6 pending, 2 overdue, 2 completed (24h)
```

---

## Data Storage

### Task Files (Existing)
```
~/.claude\tasks\{session-id}\{task-id}.json

Format:
{
  "id": "1",
  "subject": "Email Kim - request ACH payment",
  "description": "...",
  "activeForm": "Emailing Kim",
  "status": "pending|completed",
  "createdDate": "2026-01-28",
  "dueDate": "2026-01-30", // NEW - optional
  "completedDate": null, // NEW - set when completed
  "blocks": [],
  "blockedBy": []
}
```

### Business Rhythms Database (NEW)
```
~/.claude\memory\patterns\business-rhythms.json

Format:
{
  "patterns": [
    {
      "id": "monthly-invoicing",
      "taskPattern": "send invoice|invoicing|bill clients",
      "type": "monthly",
      "schedule": { "day": 1 },
      "confidence": 0.95,
      "lastOccurrence": "2026-01-01",
      "nextPredicted": "2026-02-01",
      "history": ["2025-12-01", "2026-01-01"]
    },
    {
      "id": "follow-up-after-proposal",
      "taskPattern": "follow up|check in",
      "type": "project-based",
      "trigger": "proposal sent",
      "delayDays": 3,
      "confidence": 0.78,
      "history": [
        { "trigger": "2025-12-15", "followUp": "2025-12-18" },
        { "trigger": "2026-01-10", "followUp": "2026-01-13" }
      ]
    }
  ]
}
```

### Task History Index (NEW)
```
~/.claude\session\todo-history-index.json

Purpose: Quick lookup for duplicate detection without scanning all files

Format:
{
  "pending": [
    { "id": "1", "session": "11693e0d-...", "keywords": ["email", "kim", "payment"] },
    { "id": "2", "session": "11693e0d-...", "keywords": ["business", "insurance"] }
  ],
  "completed": [
    { "id": "3", "session": "ba3047e5-...", "keywords": ["respond", "tom"], "completedDate": "2026-01-28" }
  ],
  "lastUpdated": "2026-01-28T23:50:00Z"
}

Rebuild from scratch on session start (fast - under 100ms)
```

---

## Integration Points

### 1. CLAUDE.md Hook (Conversation Parser)
```yaml
Location: After memory recall (Position #0)
Action: Parse user message for task language
Time: <50ms (fast keyword scan)
Output: New todo silently created or duplicate flagged
```

### 2. Secretary Auto-Tracking (Auto-Completion)
```yaml
Location: Post-action (Step 1.5)
Action: Search pending todos, mark matching as complete
Already implemented
```

### 3. Morning Briefing (Proactive Surfacing)
```yaml
Location: skills/routines/morning.md
Action: Display overdue + predicted + upcoming todos
Format: Dashboard view (see example above)
```

### 4. Memory Consolidation (Pattern Learning)
```yaml
Location: skills/meta/memory-consolidation.md
Action: Analyze completed todos, detect recurring patterns
Frequency: Weekly (during consolidation)
Output: Update business-rhythms.json
```

---

## Task Language Examples (Training Data)

### High Confidence - Auto-Create

| User Says | System Creates | Notes |
|-----------|---------------|-------|
| "I need to email Kim about payment" | "Email Kim - payment" | Direct action + recipient |
| "Remind me to call Jim tomorrow" | "Call Jim" | Explicit reminder request |
| "Don't let me forget to send the invoice" | "Send invoice" | Explicit memory aid |
| "Todo: research business insurance" | "Research business insurance" | Explicit todo command |
| "Add follow up with Cathy to my list" | "Follow up with Cathy" | Explicit list addition |

### Medium Confidence - Confirm First

| User Says | System Suggests | Reasoning |
|-----------|-----------------|-----------|
| "I should probably update the proposal" | "Update proposal?" | Implied obligation, less certain |
| "Jim needs the report by Friday" | "Send Jim report (Due: Fri)?" | Task for user implied, needs confirmation |
| "Have to look into insurance at some point" | "Research insurance?" | Vague timing, confirm priority |

### Low Confidence - Monitor Only

| User Says | System Action | Notes |
|-----------|---------------|-------|
| "Might call Jim later" | Track mention, don't create | Too uncertain |
| "Thinking about updating the website" | Track mention, don't create | Brainstorming, not commitment |
| "Could send the invoice today" | Track mention, don't create | Possibility, not decision |

---

## Performance Targets

| Operation | Target Time | Notes |
|-----------|-------------|-------|
| Parse message for tasks | <50ms | Keyword scan, regex match |
| Duplicate detection | <100ms | Index-based lookup |
| Auto-completion search | <150ms | Fuzzy match across sessions |
| Pattern learning | <500ms | Runs async during consolidation |
| Morning briefing generation | <200ms | Index read + format |

**Total overhead per turn:** <200ms (acceptable latency)

---

## Rollout Plan

### Phase 1: Foundation (Week 1)
- ✅ Auto-completion (secretary Step 1.5) - DONE TODAY
- ⏳ Conversation parser + duplicate detection
- ⏳ Todo history index builder
- ⏳ Morning briefing integration (basic)

### Phase 2: Intelligence (Week 2)
- ⏳ Business rhythm tracker
- ⏳ Pattern detection algorithm
- ⏳ Predictive suggestions in morning briefing

### Phase 3: Proactive Flagging (Week 3)
- ⏳ Overdue detection + alerts
- ⏳ Stale task cleanup suggestions
- ⏳ Smart rescheduling prompts

### Phase 4: Advanced Learning (Week 4)
- ⏳ Project-based pattern recognition
- ⏳ Client-specific rhythm detection
- ⏳ Confidence scoring refinement

---

## Testing Scenarios

### Scenario 1: Auto-Detect New Task
**User:** "I need to email Sarah about the quote"
**Expected:**
1. Parse message → Detect task language (high confidence)
2. Check for duplicates → None found
3. Create todo silently: "Email Sarah - quote"
4. Confirm: "✅ Added: Email Sarah about quote"

### Scenario 2: Prevent Duplicate
**User:** "Remind me to email Kim"
**Existing:** "Email Kim - request ACH payment instead of check"
**Expected:**
1. Parse message → Detect task language
2. Check for duplicates → 85% similarity
3. Don't create new todo
4. Response: "Already on your list: #3 - Email Kim about payment"

### Scenario 3: Auto-Complete on Action
**User:** [Sends email to Kim via send_mail]
**Existing:** "Email Kim - request ACH payment" (pending)
**Expected:**
1. Secretary detects email sent
2. Step 1.5 searches pending todos
3. Finds match: "Email Kim"
4. Auto-complete todo
5. Confirm: "✅ Todo completed: Email Kim - request ACH payment"
6. Continue with normal record updates

### Scenario 4: Pattern Prediction
**History:** User sends invoices on 1st of month (Dec 1, Jan 1)
**Date:** Jan 31, 2026
**Expected:**
1. Morning briefing runs
2. Pattern detector checks business-rhythms.json
3. Finds monthly-invoicing pattern (confidence: 0.90)
4. Tomorrow is Feb 1
5. Surface in briefing: "🔴 TOMORROW: Send monthly invoices (pattern: 1st of month)"

### Scenario 5: Overdue Flagging
**Todo:** "Research business insurance" (created Jan 20, status: pending)
**Date:** Jan 28 (8 days old)
**Expected:**
1. Morning briefing runs
2. Checks all pending todos for staleness (>7 days)
3. Flags as overdue
4. Surface at top: "🚨 OVERDUE: Research business insurance (8 days old)"

---

## Error Handling

**Ambiguous task language:**
- Ask for clarification: "Did you mean this as a todo, or just thinking out loud?"

**Duplicate detection false positive:**
- Allow override: "Create anyway" option if user insists it's different

**Pattern detection with low confidence (<0.6):**
- Don't surface prediction, continue learning silently

**Task history index corruption:**
- Rebuild from scratch (all task JSONs) - takes ~200ms for 1000 tasks

**Missing dueDate on overdue check:**
- Use createdDate + 7 days as staleness threshold instead

---

## Success Metrics

**Goal:** Reduce manual todo management by 90%

**Track:**
- Auto-creation hit rate (correct task detection)
- Duplicate prevention accuracy (true positives)
- Auto-completion rate (% of todos completed automatically)
- Pattern prediction accuracy (predicted date within ±1 day)
- User satisfaction (fewer "I forgot to..." moments)

**Targets:**
- Auto-creation accuracy: >85%
- Duplicate prevention: <5% false positives
- Auto-completion rate: >70% of todos
- Pattern prediction: >80% accuracy
- Overdue reduction: <2 items on average

---

## CRITICAL ENFORCEMENT RULES

1. **ALWAYS parse for task language** - every user message, no exceptions
2. **ALWAYS check for duplicates** - before creating any todo
3. **ALWAYS auto-complete on action** - integrated with secretary Step 1.5
4. **ALWAYS surface overdue** - in morning briefing (top priority)
5. **NEVER create duplicate todos** - similarity >80% = reference existing

A predictive todo system that requires manual management is useless.

---

*Predictive Business Todo System v1.0 | Auto-detect | Auto-complete | Pattern learning | Zero manual overhead*
