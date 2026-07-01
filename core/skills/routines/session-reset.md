# Session Reset - Clean Slate Protocol

**Version:** 1.0 (Phase 4 - Working Memory Integration)
**Purpose:** Reset session context, archive working memory, clear history
**Trigger:** User says "done", "i'm done", "we're done", "start over", "clear session", "reset chat", "new conversation"

---

## What This Does

**Session Reset = Fresh Start**

1. Archive working memory to vault (preserves session work)
2. Clear working memory files (reset to bootstrap state)
3. Clear session context (0% context usage)
4. Clear prompt history (clean conversation)
5. Reset state.json counters
6. Notify user: "Session reset. Fresh start ready."

**When to Use:**
- Task complete, starting new unrelated work
- Context cluttered, need clean slate
- Switching projects/clients
- End of work session
- WhatsApp `/new` command workaround

**What's Preserved:**
- ✅ Vault notes (all consolidated memories)
- ✅ Working memory archived to vault
- ✅ State.json core settings
- ✅ Identity (SOUL.md, USER.md)

**What's Cleared:**
- ❌ Working memory (archived first, then cleared)
- ❌ Prompt history (conversation log)
- ❌ Session context (back to 0%)
- ❌ Task list (archived to vault if any open tasks)

---

## Reset Protocol

### Step 1: Archive Working Memory to Vault

**BEFORE clearing anything, preserve working memory in vault:**

```python
import shutil
from pathlib import Path
from datetime import datetime

WORKING_MEMORY_DIR = Path(".claude/session/working-memory")
VAULT_DIR = Path(".claude/memory")

def archive_working_memory_to_vault():
    """Archive working memory to vault before session reset."""

    if not WORKING_MEMORY_DIR.exists():
        print("[INFO] No working memory to archive")
        return

    # Create archive folder in vault
    timestamp = datetime.now().strftime("%Y-%m-%d-%H%M")
    archive_dir = VAULT_DIR / "Sessions" / f"Session-{timestamp}"
    archive_dir.mkdir(parents=True, exist_ok=True)

    # Copy all working memory files to vault
    files_to_archive = [
        "index.md",
        "active-clients.md",
        "active-projects.md",
        "active-tasks.md",
        "context-threads.md",
        "pending-actions.md",
        "background-findings.md"
    ]

    archived_count = 0
    for filename in files_to_archive:
        source = WORKING_MEMORY_DIR / filename
        dest = archive_dir / filename

        if source.exists():
            shutil.copy2(source, dest)
            archived_count += 1

    # Create session summary in vault
    with open(WORKING_MEMORY_DIR / "index.md", 'r', encoding='utf-8') as f:
        index_content = f.read()

    summary = f"""# Session Archive - {timestamp}

## Working Memory Snapshot

{index_content}

## Archived Files

{archived_count}/7 working memory files archived from session.

**Archive location:** `memory/Sessions/Session-{timestamp}/`

---

**Session completed:** {timestamp}
**Reset trigger:** User requested session reset
"""

    with open(archive_dir / "session-summary.md", 'w', encoding='utf-8') as f:
        f.write(summary)

    print(f"[OK] Working memory archived to vault: Sessions/Session-{timestamp}/")
    return archive_dir

# Execute archival FIRST (before any clearing)
archive_location = archive_working_memory_to_vault()
```

---

### Step 2: Clear Working Memory Files

**Reset all working memory files to bootstrap state:**

```python
def clear_working_memory():
    """Clear working memory and reset to bootstrap state."""

    if not WORKING_MEMORY_DIR.exists():
        return

    # Bootstrap template for index.md
    bootstrap_index = """# Working Memory - Session Active Intelligence

**Last updated:** {timestamp} | Auto-injected Position #0
**Purpose:** Persistent RAM - always loaded, never forgotten
**Status:** BOOTSTRAPPED (session reset)

---

## Quick Context (Read This First)

- **Active client**: None (session just reset)
- **Current task**: No task active
- **Pending action**: None

---

## Active Threads

→ See [[context-threads.md]] for conversation patterns

**Key Patterns:** None yet (fresh session)

---

## Active Clients

→ See [[active-clients.md]] for full details

**Current:** None

---

## Active Projects

→ See [[active-projects.md]] for full details

**Current:** None

---

## Active Tasks

→ See [[active-tasks.md]] for full details

**Current:** No tasks

---

## Pending Actions

→ See [[pending-actions.md]] for full details

**Current:** 0 pending actions

---

## Today's Findings (Background Agents)

→ See [[background-findings.md]] for full details

📋 **Secretary**: Not yet active
🔍 **Scout**: Not yet active
📈 **Growth**: Not yet active

---

**Working Memory Status:** RESET
**Files:** 7/7 (bootstrap state)
**Integration:** Position #0 injection (gate-enforcer.py)
**Session:** Fresh start
"""

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    # Write bootstrap index
    with open(WORKING_MEMORY_DIR / "index.md", 'w', encoding='utf-8') as f:
        f.write(bootstrap_index.format(timestamp=timestamp))

    # Clear all other working memory files (write minimal templates)
    # Files: active-clients, active-projects, active-tasks, context-threads,
    #        pending-actions, background-findings
    # (Templates omitted for brevity - use Phase 2 bootstrap templates)

    print(f"[OK] Working memory cleared and reset to bootstrap state")

# Execute clearing AFTER archival
clear_working_memory()
```

---

### Step 3: Clear Prompt History

**Reset conversation log:**

```python
PROMPT_HISTORY_FILE = Path(".claude/session/prompt-history.jsonl")

def clear_prompt_history():
    """Clear prompt history for fresh conversation."""

    if PROMPT_HISTORY_FILE.exists():
        # Backup before clearing (just in case)
        backup = PROMPT_HISTORY_FILE.with_suffix(".jsonl.bak")
        shutil.copy2(PROMPT_HISTORY_FILE, backup)

        # Clear history (write empty file)
        with open(PROMPT_HISTORY_FILE, 'w', encoding='utf-8') as f:
            pass  # Empty file

        print(f"[OK] Prompt history cleared (backup: prompt-history.jsonl.bak)")
    else:
        print(f"[INFO] No prompt history to clear")

# Execute clearing
clear_prompt_history()
```

---

### Step 4: Reset State Counters

**Reset session-specific counters in state.json:**

```python
STATE_FILE = Path(".claude/session/state.json")

def reset_state_counters():
    """Reset session counters but preserve core settings."""

    if not STATE_FILE.exists():
        print(f"[WARNING] state.json not found")
        return

    import json

    with open(STATE_FILE, 'r', encoding='utf-8') as f:
        state = json.load(f)

    # Reset session counters
    if "memory_system" in state:
        state["memory_system"]["notes_created_this_session"] = 0
        state["memory_system"]["last_consolidation"] = None

    # Reset enforcement queue
    state["enforcement_queue_count"] = 0

    # Reset context monitor
    if "context_monitor" in state:
        state["context_monitor"]["current_usage_percent"] = 0
        state["context_monitor"]["last_compaction"] = None

    # Generate new session ID
    import uuid
    state["session_id"] = str(uuid.uuid4())
    state["session_start"] = datetime.now().isoformat()

    # Write back atomically
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=4)

    print(f"[OK] State counters reset, new session ID: {state['session_id']}")

# Execute reset
reset_state_counters()
```

---

### Step 5: Notify User

**Confirm session reset:**

```
[SESSION RESET]

Working memory archived: memory/Sessions/Session-2026-02-04-0015/
Context cleared: 0% usage
Prompt history: Reset
State: Fresh session ID

Fresh start ready. What would you like to work on?
```

---

## Integration with Memory Consolidation

**Difference between Session Reset and Compaction:**

| Operation | Session Reset | Compaction |
|-----------|---------------|------------|
| **Trigger** | User request ("done") | Context 95% full (automatic) |
| **Working Memory** | Archived to vault, cleared | Snapshotted, restored |
| **Context** | Cleared to 0% | Cleared to 0% |
| **Vault Notes** | Created (consolidation first) | Created (3-5 notes) |
| **Purpose** | Fresh start | Continue seamlessly |
| **Recovery** | None (intentional reset) | context-anchor.md + restoration |

**When user says "done":**
1. Run memory consolidation FIRST (save session learnings)
2. Run session reset (archive + clear)
3. Result: Session learnings preserved, working memory archived, fresh start

**When compaction triggers automatically:**
1. Working memory snapshotted (Step 0.5)
2. Consolidation runs (3-5 notes created)
3. Working memory restored (Step 11.5)
4. Result: Seamless continuation, no context loss

---

## Testing

**Test Scenario 1: User Request**

```
User: "done"
Claude: [Runs memory consolidation]
Claude: [Runs session reset]
Claude: [SESSION RESET] Working memory archived... Fresh start ready.
```

**Test Scenario 2: With Active Working Memory**

```
Setup:
- Working memory has 2 active clients, 1 project, 3 tasks
- User says "start over"

Expected:
- All working memory archived to vault
- Vault gets Session-YYYY-MM-DD-HHMM/ folder
- Working memory cleared to bootstrap state
- Next response: Fresh index with no active items
```

**Test Scenario 3: Verify Archive**

```
After reset:
- Check vault: memory/Sessions/Session-YYYY-MM-DD-HHMM/
- Should contain: 7 working memory files + session-summary.md
- Session summary shows snapshot of working memory at time of reset
```

---

## Best Practices

### When to Use Session Reset

**DO use session reset when:**
- ✅ Task complete, switching to unrelated work
- ✅ Context too cluttered (many projects/clients)
- ✅ End of work day (natural boundary)
- ✅ Major context switch (client to client, project to project)

**DON'T use session reset when:**
- ❌ Just want to continue current work (no need to reset)
- ❌ Context still low (<50%) and work ongoing
- ❌ Active task not complete (will lose task context)

### Archive Review

**After session reset, working memory is archived to:**
```
memory/Sessions/Session-YYYY-MM-DD-HHMM/
├── index.md (working memory snapshot)
├── active-clients.md
├── active-projects.md
├── active-tasks.md
├── context-threads.md
├── pending-actions.md
├── background-findings.md
└── session-summary.md (metadata)
```

**Review archived sessions:**
- Browse `memory/Sessions/` folder in Obsidian
- Each session has full working memory snapshot
- session-summary.md shows when/why session ended
- Can review past session context anytime

---

## Error Handling

**If archival fails:**
- Log error but DON'T clear working memory
- Better to keep stale working memory than lose it
- User can manually trigger reset again

**If clearing fails:**
- Try individual file clear (don't fail on one file)
- Report which files couldn't be cleared
- Continue with remaining reset steps

**If state reset fails:**
- Non-critical - state.json will be updated on next prompt
- Log warning but don't block reset

---

## Success Criteria

**Session reset is successful when:**
1. ✅ Working memory archived to vault (7/7 files)
2. ✅ Working memory cleared to bootstrap state
3. ✅ Prompt history reset
4. ✅ State counters reset
5. ✅ Context at 0%
6. ✅ Fresh session ID generated
7. ✅ User notified of reset completion

**Result:** Clean slate, previous session preserved, ready for new work.

---

**Version:** 1.0 (Phase 4 Integration)
**Status:** Working memory archival integrated
**Purpose:** Session reset WITHOUT losing working memory - it's archived to vault first
