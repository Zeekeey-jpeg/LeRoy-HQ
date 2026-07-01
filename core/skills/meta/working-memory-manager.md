# Working Memory Manager - Persistent Session Intelligence

**Version:** 1.0 (Phase 2 Complete)
**Purpose:** LEROY-style persistent working memory that's ALWAYS loaded in Position #0
**Integration:** gate-enforcer.py, update-working-memory.py, memory-recall.md

---

## What This Is

**Working Memory = Session RAM**

Just like LEROY maintains state across time entries, Working Memory maintains session intelligence across responses. It's the answer to "sometimes you forget."

**Key Principle:** Working memory is ALWAYS loaded (Position #0 injection) → Forgetting becomes impossible.

---

## Architecture

### File Structure

```
session/working-memory/
├── index.md                # HUB - loaded every response (<50ms)
├── active-clients.md       # Clients mentioned this session
├── active-projects.md      # Projects being worked on
├── active-tasks.md         # Tasks in progress
├── context-threads.md      # Conversation patterns to remember
├── pending-actions.md      # Things promised but not yet done
└── background-findings.md  # Secretary/scout/growth highlights
```

**Total size:** ~15-25KB (all 7 files combined)
**Load time:** <50ms target (Position #0 injection)

### Data Flow

```
User message
    ↓
gate-enforcer.py (pre-prompt hook)
    ↓
Load working-memory/index.md (<50ms)
    ↓
Inject into Claude's context
    ↓
Claude sees working memory EVERY response
    ↓
Working memory directs vault recall
    ↓
Response generated with full context
    ↓
update-working-memory.py (post-action hook)
    ↓
Update relevant files
    ↓
Rebuild index.md
```

---

## Position #0 Integration

### How It Works

**gate-enforcer.py enhancement (Phase 2):**

```python
# Load working memory index (around line 1310)
WORKING_MEMORY_INDEX = CLAUDE_DIR / "session" / "working-memory" / "index.md"

if WORKING_MEMORY_INDEX.exists():
    try:
        wm_start = time.time()
        with open(WORKING_MEMORY_INDEX, 'r', encoding='utf-8') as f:
            working_memory_content = f.read()
        wm_end = time.time()
        working_memory_load_time = int((wm_end - wm_start) * 1000)
        working_memory_status = f"LOADED ({working_memory_load_time}ms)"
    except IOError as e:
        working_memory_status = "ERROR"
else:
    working_memory_status = "NOT_FOUND"
```

**Banner display:**
```
WORKING_MEMORY: LOADED (42ms)
```

**Context injection (after banner):**
```
================================================================================
    WORKING MEMORY - SESSION ACTIVE INTELLIGENCE (v1.0)
================================================================================
[Full index.md content injected here - ~2-5KB]
================================================================================
```

**Result:** Claude sees working memory automatically, every response, no exceptions.

---

## Update Protocols

### Manual Updates (CLI)

**Add client:**
```bash
python scripts/update-working-memory.py --add-client "ExampleClient Engineering"
```

**Add project:**
```bash
python scripts/update-working-memory.py --add-project "your product v1.1.0.0"
```

**Add task:**
```bash
python scripts/update-working-memory.py --add-task "Phase 2 implementation" --task-id 7
```

**Add pending action:**
```bash
python scripts/update-working-memory.py --add-pending "Follow up on ExampleClient payment" --due-date "2026-02-10"
```

**Rebuild index:**
```bash
python scripts/update-working-memory.py --rebuild-index
```

### Automatic Updates (Phase 3+)

**Post-action hooks will trigger automatic updates:**

1. **Client mentioned** → Auto-add to active-clients.md
2. **Project started** → Auto-add to active-projects.md
3. **Task created** → Auto-add to active-tasks.md
4. **Promise made** → Auto-add to pending-actions.md
5. **Background agent completes** → Update background-findings.md
6. **Any update** → Auto-rebuild index.md

**Hook integration (Phase 3):**
```python
# After substantive action (email sent, doc signed, task complete)
subprocess.run([
    "python",
    "scripts/update-working-memory.py",
    "--add-client",
    extracted_client_name
])
```

---

## Working Memory Files

### 1. index.md (HUB)

**Purpose:** Quick context snapshot - loaded every response

**Content:**
- Quick Context (1-line summaries)
- Active clients (names only)
- Active projects (names only)
- Current task (1-line)
- Pending action count
- Background findings (last 3 highlights)

**Size:** ~2-5KB
**Load time:** <50ms
**Update frequency:** After every change to any file

**Pattern:** Wiki embeds link to detail files (`[[active-clients.md]]`)

---

### 2. active-clients.md

**Purpose:** Track clients mentioned/worked on this session

**When to add:**
- User mentions client name
- Email sent to client
- Work done for client
- Client-related action taken

**When to remove:**
- Session ends (archive to vault)
- Client work complete

**Structure:**
```markdown
## ExampleClient Engineering

**Status:** Active - Phase 1 delivery in progress
**Last interaction:** 2026-02-03 14:30 (email sent)
**Current work:** DC-2 project, weekly deliveries starting 2/5
**Pending:** Invoice $5K for Phase 1

**Recent Activity:**
- 2026-02-03: Email sent with progress update
- 2026-02-01: Plan request submitted

**Vault Notes:** [[ExampleClient Engineering]] (3 notes loaded)
```

**Benefit:** Next response auto-loads ExampleClient vault notes (directed recall)

---

### 3. active-projects.md

**Purpose:** Track projects being worked on this session

**When to add:**
- Implementation started
- Project planning begins
- Multi-session project

**When to remove:**
- Project complete
- Archived to vault

**Structure:**
```markdown
## Working Memory Manager

**Status:** Phase 2 - Working Memory Foundation (in progress)
**Started:** 2026-02-03 14:30
**Progress:** 80% complete

**Phases:**
- ✅ Phase 1: Position #0 Enforcement (COMPLETE)
- 🔄 Phase 2: Working Memory Foundation (80%)
- ⚠️ Phase 3: Background Output Surfacing (PENDING)

**Current Task:** Testing working memory injection (Task #9)

**Files Modified:**
- CLAUDE.md
- gate-enforcer.py
- update-working-memory.py
```

---

### 4. active-tasks.md

**Purpose:** Track tasks in progress (mirrors TodoWrite but session-scoped)

**When to add:**
- TaskCreate tool used
- Multi-step implementation starts
- Deliverable committed to

**When to remove:**
- Task complete (TaskUpdate status=completed)
- Session ends (archive to vault)

**Structure:**
```markdown
### Task #9: Test working memory injection
**Status:** IN_PROGRESS
**Started:** 2026-02-03 16:00
**Progress:** 40% (2/5 scenarios complete)

**Deliverable:** Validate 5 scenarios all pass
- [x] Working memory loads in Position #0
- [x] Index appears in enforcement box
- [ ] Active clients/projects visible
- [ ] Updates persist across responses
- [ ] Performance <50ms
```

**Benefit:** Always know what you're working on, where you left off

---

### 5. context-threads.md

**Purpose:** Track conversation patterns and decision threads to remember

**When to add:**
- Important architectural decision made
- Pattern emerges in user requests
- Recurring theme appears
- Key insight discovered

**When to remove:**
- Thread resolved/complete
- Consolidated to vault notes

**Structure:**
```markdown
### Working Memory Manager Architecture

**Started:** 2026-02-03
**Pattern:** Multi-phase implementation (6 phases)

**Key Decisions:**
- LEROY-style markdown (not complex JSON)
- Hook-driven automation (enforcement.todo → updates)
- Position #0 injection (<50ms target)
- Self-healing protocol for violations

**Why This Matters:**
User frustrated by "I forgot" incidents. Working memory = standing
background intelligence that's ALWAYS loaded. Makes forgetting
structurally impossible.
```

**Benefit:** Never lose context on why decisions were made

---

### 6. pending-actions.md

**Purpose:** Track things promised but not yet done (prevents "I forgot")

**When to add:**
- Promise made to user
- Deliverable committed to
- Follow-up scheduled
- Action item created

**When to remove:**
- Action complete
- Promise fulfilled
- Explicitly cancelled

**Structure:**
```markdown
### Follow up on ExampleClient payment
**Promised:** Email to client (2026-01-29)
**Status:** OVERDUE (due 2026-01-29, now 2026-02-03)
**What:** Invoice $12K for Phase 2 completion
**Action:** Send payment reminder email
**Priority:** HIGH (4 days overdue)
```

**Self-healing:** If action >7 days overdue → AUTO-SURFACE in morning routine with RED FLAG

**Benefit:** Never leave user hanging, never forget promises

---

### 7. background-findings.md

**Purpose:** Surface secretary/scout/growth outputs automatically (Phase 3)

**When to add:**
- Secretary tracks event (post-action hook)
- Scout detects pattern (background agent completion)
- Growth recommends skill (background agent completion)

**When to remove:**
- Findings addressed/actioned
- Session ends (archive to vault)

**Structure (Phase 3):**
```markdown
## Secretary Findings

📋 **Recent Events** (Last 3)
1. Email sent to ExampleClient - Phase 1 update (2026-02-03 14:30)
2. Contract signed ExampleClient - OBID project (2026-02-02 16:00)
3. Calendar event created - Prebid meeting (2026-02-01 09:00)

[Full timeline: secretary-output.md (12 events)]

## Scout Findings

🔍 **Patterns Detected** (Top 3)
1. Annotation handlers (3 files): Common pattern detected
2. Ribbon UI components (5 files): Initialization pattern
3. DXF export workflow (2 files): Similar logic

[Full report: growth-output.md (7 patterns)]

## Growth Findings

📈 **Skill Recommendations** (Top 2)
1. Dimension placement automation - 4 manual workflows detected
2. DXF converter skill - Export pattern repeated 3x

[Full recommendations: growth-output.md (5 skills)]
```

**Benefit:** Background work becomes VISIBLE without asking

---

## Smart Memory Recall (Phase 5)

### How Working Memory Directs Vault Recall

**Current:** memory-recall.md loads random 5 notes (bootstrap mode)

**Phase 5 enhancement:**

**memory-recall.md reads working memory index:**
```python
# Extract active entities from working memory
working_memory_index = read_working_memory_index()

active_clients = extract_clients(working_memory_index)
# → ["ExampleClient Engineering", "ExampleClient"]

active_projects = extract_projects(working_memory_index)
# → ["your product v1.1.0.0", "Working Memory Manager"]

# Build targeted recall query
recall_query = {
    "clients": active_clients,
    "projects": active_projects,
    "limit": 2  # 2 notes per active entity
}

# Load 4 notes (2 clients × 2 notes) instead of random 5
vault_notes = targeted_recall(recall_query)
```

**Result:** Memory recall is DIRECTED, not random. Load notes about what you're actually working on.

---

## Recovery Procedures

### Session Reset (Intentional)

**Command:** `session reset` or `done` trigger

**Process:**
1. Archive all working memory to vault (memory consolidation)
2. Clear all 7 working memory files
3. Rebuild index.md with bootstrap template
4. Reset session context to 0%

**Recovery:** Clean slate for new session

---

### Compaction Recovery (Automatic)

**Trigger:** Memory consolidation triggered (context >85%)

**Process (Phase 4):**
1. **BEFORE compaction:** Snapshot all working memory files
2. Consolidate session to vault (normal flow)
3. **Populate context-anchor.md** with working memory snapshot
4. **AFTER compaction:** Restore working memory from snapshot

**context-anchor.md format:**
```markdown
# Context Recovery Anchor

## Working Memory Snapshot (Pre-Compaction)

[Full index.md content]

## Resume From Here

**Next action:** Continue Phase 2 testing
**Active clients:** ExampleClient Engineering
**Pending items:** 3 pending actions

## Recovery Protocol
1. Reload working memory from snapshot above
2. Continue work on: Testing working memory injection (Task #9)
3. Don't respond to background agent notifications - user task is priority
```

**Result:** After compaction, Position #0 loads context-anchor.md → working memory restored → seamless continuation

---

## Performance Targets

| Metric | Target | Acceptable | Critical |
|--------|--------|------------|----------|
| index.md load time | <30ms | <50ms | >75ms |
| Full injection time | <50ms | <75ms | >100ms |
| Index rebuild time | <100ms | <150ms | >200ms |
| Total Position #0 time | <300ms | <400ms | >500ms |

**Monitoring:** Working memory load time shown in gate banner

**Optimization:**
- Keep index.md <5KB (summaries only, details in other files)
- Cache working memory content (reload only if files modified)
- Use atomic writes (temp file + rename)

---

## Integration Points

### 1. gate-enforcer.py (Position #0 - Phase 2)

**Location:** ~line 1310 (before banner)
**What:** Load working-memory/index.md and inject into context
**Status:** ✅ IMPLEMENTED (Phase 2)

---

### 2. update-working-memory.py (Manual updates - Phase 2)

**Location:** scripts/update-working-memory.py
**What:** CLI tool for atomic updates + index rebuilding
**Status:** ✅ IMPLEMENTED (Phase 2)

---

### 3. memory-recall.md (Directed recall - Phase 5)

**Location:** skills/meta/memory-recall.md
**What:** Read working memory to build targeted recall query
**Status:** ⚠️ PENDING (Phase 5)

---

### 4. memory-consolidation.md (Recovery - Phase 4)

**Location:** skills/meta/memory-consolidation.md
**What:** Snapshot working memory before compaction, restore after
**Status:** ⚠️ PENDING (Phase 4)

---

### 5. surface-background-findings.py (Auto-surfacing - Phase 3)

**Location:** scripts/surface-background-findings.py (NEW)
**What:** Aggregate secretary/scout/growth outputs into background-findings.md
**Status:** ⚠️ PENDING (Phase 3)

---

## Success Criteria

**Phase 2 (Working Memory Foundation) - COMPLETE:**
- [x] Create working-memory folder with 7 files
- [x] Modify gate-enforcer.py for Position #0 injection
- [x] Create update-working-memory.py script
- [x] Write working-memory-manager.md specification
- [ ] Test working memory injection across 5 scenarios (Task #9 in progress)

**Phase 3 (Background Output Surfacing) - PENDING:**
- [ ] Create surface-background-findings.py
- [ ] Integrate with secretary-auto-tracking.md
- [ ] Add post-response hook to gate-enforcer.py

**Phase 4 (Context Recovery) - PENDING:**
- [ ] Add working memory preservation to memory-consolidation.md
- [ ] Implement context-anchor.md auto-population
- [ ] Add working memory archival to session-reset.md

**Phase 5 (Smart Memory Recall) - PENDING:**
- [ ] Enhance memory-recall.md with working-memory-directed queries
- [ ] Modify gate-enforcer.py recall step to use working memory

**Phase 6 (Self-Healing & Monitoring) - PENDING:**
- [ ] Create response-monitor.py with Position #0 violation detection
- [ ] Add self-healing injection to gate-enforcer.py
- [ ] Add compliance metrics to morning.md dashboard

---

## Troubleshooting

### Issue: Working memory not loading

**Symptoms:** Banner shows "WORKING_MEMORY: NOT_FOUND"

**Check:**
1. Does session/working-memory/ directory exist?
2. Does session/working-memory/index.md exist?
3. Is index.md readable (file permissions)?

**Fix:**
```bash
# Rebuild working memory structure
mkdir -p session/working-memory
python scripts/update-working-memory.py --rebuild-index
```

---

### Issue: Working memory load time >100ms

**Symptoms:** Banner shows "WORKING_MEMORY: LOADED (150ms)" (too slow)

**Check:**
1. How large is index.md? (should be <5KB)
2. Are there performance issues on disk I/O?

**Fix:**
```bash
# Check index size
ls -lh session/working-memory/index.md

# If >10KB, index has too much detail - rebuild with summaries only
python scripts/update-working-memory.py --rebuild-index
```

---

### Issue: Working memory out of sync

**Symptoms:** Index shows client but active-clients.md doesn't have details

**Check:**
1. When was index.md last rebuilt?
2. Were manual edits made to files?

**Fix:**
```bash
# Force index rebuild
python scripts/update-working-memory.py --rebuild-index
```

---

## Best Practices

### 1. Keep index.md Lean

**DO:** Summaries only (1-line descriptions)
**DON'T:** Copy entire sections from detail files

**Example:**
```markdown
## Active Clients
**Current:** ExampleClient Engineering, ExampleClient
```

**NOT:**
```markdown
## Active Clients
**ExampleClient Engineering** - Full detailed description here...
**ExampleClient** - Another full description...
```

---

### 2. Update Atomically

**DO:** Use update-working-memory.py script
**DON'T:** Edit files manually (risk of corruption)

**Why:** Atomic writes ensure no corruption if process interrupted

---

### 3. Archive, Don't Delete

**DO:** Move completed items to vault notes during consolidation
**DON'T:** Delete working memory content

**Pattern:**
```bash
# When session ends
# Consolidation copies working memory to vault
# Then clears working memory for next session
```

---

### 4. Let Hooks Handle Updates

**DO:** Let post-action hooks update working memory automatically (Phase 3+)
**DON'T:** Manually update after every action

**Pattern:** Email sent → Secretary tracks → surface-background-findings.py → Update working memory → Index rebuilt

---

## Future Enhancements

**Phase 3 (Background Output Surfacing):**
- Auto-aggregate secretary/scout/growth outputs
- Show highlights in working memory automatically
- No asking "what did secretary find?" → It's just THERE

**Phase 4 (Context Recovery):**
- Snapshot working memory before compaction
- Populate context-anchor.md for recovery
- Seamless continuation after consolidation

**Phase 5 (Smart Memory Recall):**
- Directed recall based on active clients/projects
- Load 2 notes per active entity (not random 5)
- Better context relevance

**Phase 6 (Self-Healing & Monitoring):**
- Working memory compliance metrics
- Auto-detect stale pending actions (>7 days)
- Morning dashboard shows working memory health

---

**Version:** 1.0
**Status:** Phase 2 complete, Phases 3-6 pending
**Next:** Task #9 - Test working memory injection across 5 scenarios
**Purpose:** Making "I forgot" structurally impossible through persistent session intelligence
