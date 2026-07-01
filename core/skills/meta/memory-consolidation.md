---
user-invocable: false
---

# Memory Consolidation - Automatic Persistent Storage

> **AUTO-TRIGGERED:** At every checkpoint (task complete, commit, session end)
> **NO USER REQUEST NEEDED:** This runs silently in background
> **ALWAYS BACKGROUND:** ZERO blocking - user never waits for consolidation
> **METRICS-ENABLED:** Logs tag validation, write attempts, and checkpoint intervals

## Purpose

Extract key learnings from current session and persist them to Obsidian vault for long-term recall.

## Fixed Paths

| Purpose | Path |
|---------|------|
| Obsidian Vault | `~/.claude\memory\` |
| Session State | `.claude/session/state.json` |
| Growth Output | `.claude/session/growth-output.md` |
| Prompt History | `.claude/session/prompt-history.jsonl` |

## Confidence Decay (v6.1 — Decay-A) — MANDATORY READ

**When writing notes, decide if the fact is asserted or inferred:**
- **Asserted** (`inferred: false`, default) — user explicitly stated this. Never decays. Use for direct quotes, contracts, system facts.
- **Inferred** (`inferred: true`) — Claude inferred this from observation/pattern. Decays over time unless re-verified. Use for behavioral patterns, preferences guessed from sample size, correlations.

**When marking a note `inferred: true`, also set:**
```yaml
---
confidence: 0.85         # 0.0-1.0 starting confidence
inferred: true
asserted_at: 2026-04-29  # when first written
last_verified: 2026-04-29 # bump every time the fact is re-confirmed
half_life_days: 90       # OPTIONAL override — else type default below applies
---
```

**Per-type half-life defaults (council vote, 2026-04-29):**

| Note Type | Half-Life | Rationale |
|---|---|---|
| `decision` | ∞ (never) | Architectural choices stick until explicitly superseded |
| `pattern` | 90 days | Patterns are facts about how the system works |
| `skill-learned` | 90 days | Lessons from real incidents — facts about the world |
| `preference` | 180 days | the user's preferences are stable; user re-confirms slowly |
| `project-note` | 90 days | Project facts age but slowly |
| `general` | 30 days | Default for misc content — short leash |

**MCP types (if writing via `memory remember`):** fact=90, experience=30, preference=180, decision=∞, context=7, belief=30, warning=∞.

**Decay formula** (computed at index time by `build-memory-index.py`):
```
asserted          → effective_confidence = confidence  (no decay)
inferred          → effective_confidence = confidence * 0.5^(days_since_verified / half_life_days)
half_life is None → no decay even if inferred
```

**Recall floor:** notes with `effective_confidence < 0.3` are dropped at Pass 0.25 unless `--include-stale` is set.

**Re-verification:** when the user re-confirms a fact, consolidation MUST bump `last_verified` to today (resets decay clock). When the user explicitly states what was previously inferred, also flip `inferred: false` and bump `confidence: 1.0`.

**Backward compatibility:** existing 479 notes lack these fields → defaults make them asserted with confidence 1.0 → no behavior change. Only new writes carry decay metadata.

## Typed Memory Edges (v6.1 — Edges-A) — MANDATORY READ

**Promote raw `[[wikilinks]]` to typed relationships.** When writing a new note, decide which of the 5 edge types each link expresses. Untyped wikilinks still work (collapse to `refers_to`) but they don't unlock recall demotion or contradiction surfacing.

**Schema (frontmatter):**
```yaml
---
name: your organization CAO Ask v2
type: decision
edges:
  supersedes:    ["[[your organization-CAO-Ask-v1]]"]      # this note REPLACES the listed notes
  contradicts:   ["[[Old-your organization-Strategy]]"]    # this note disagrees with these
  supports:      ["[[the user-Voice-Style]]"]   # this note reinforces these
  derived_from:  ["[[Email-Thread-2026-04]]"] # this note was extracted from these
  refers_to:     ["[[Robin-Wonsetler]]"]      # generic reference (legacy bucket)
---
```

**Edge type semantics:**

| Edge | When to write | Example |
|---|---|---|
| `supersedes` | New version replaces old. Recall demotes the old by -0.5 score and tags `[SUPERSEDED]`. | v2 of an architecture decision |
| `contradicts` | Two notes disagree. Recall surfaces both with `[CONFLICT]` tag. (Phase B: blocks consolidation on CRITICAL topics.) | the user said X on Monday, Y on Friday |
| `supports` | This note reinforces another. Used for confidence boosts in Phase B. | A new pattern proves a prior preference |
| `derived_from` | Provenance chain. This note was extracted from another (email, transcript, doc). | Note built from a Gmail thread |
| `refers_to` | Generic reference. Legacy `[[wikilink]]` and `related:` field collapse here. | Mention of a person, project, or term |

**Decision tree for picking the type:**
1. Is this a newer version that should replace another? → `supersedes`
2. Does this contradict an existing note? → `contradicts` (and flag for Phase B review)
3. Does this confirm/strengthen an existing note? → `supports`
4. Was this content extracted from a source? → `derived_from`
5. Else (default for any reference): → `refers_to`

**When consolidating, ALWAYS ask before writing:**
- "Does this supersede any existing note?" — search vault for prior version on same topic
- "Does this contradict anything I previously stored?" — semantic check against opposing claims
- If yes to either, write the edge AND log a candidate to `session/edge-candidates.json` for Phase B human review.

**Never auto-promote inferred edges to typed.** Phase B will add an inference engine that writes candidates to `session/edge-candidates.json` for explicit the user approval. Until then, only Claude (during consolidation) or the user (manual) writes typed edges.

**Backward compatibility:** notes without `edges:` block keep working — body wikilinks and frontmatter `related:` automatically collapse to `refers_to`. Index emits both typed and flat formats (`memory-graph.json` v2.0 has `edges` + `legacy_edges` keys). One-shot backup of pre-typed graph saved as `memory-graph.json.pre-typed.bak`.

## Automatic Triggers

This skill runs automatically at these checkpoints (ALWAYS in background):

1. **Task Completion** - After marking final todo as completed
2. **Before Git Commit** - During sentinel review (async, doesn't block commit)
3. **Session End** - User says goodbye/thanks/done
4. **Explicit Request** - User says "save memory" or "remember this"
5. **Task Checkpoints** - Growth monitor checkpoints at natural task boundaries (task complete, topic change, before commit)
6. **Context Limit Reached (95%)** - Auto-compact triggered by context monitor (Position #0)
   - Triggered automatically when context usage reaches 95% (190K/200K tokens)
   - Consolidates conversation into 3-5 Obsidian notes before context reset
   - Creates context-anchor.md for recovery after compaction
   - ALWAYS background execution (WhatsApp-friendly, no blocking)
   - Updates context_monitor metrics in state.json after completion

**CRITICAL:** Consolidation is pure file I/O to Obsidian vault. It NEVER blocks user workflow, regardless of request type or priority level.

## Pre-Consolidation Check (MANDATORY - RUN FIRST)

**Check checkpoint status before consolidation:**

1. Read `session/state.json` → `enforcement.checkpoint_overdue` and `checkpoint_overdue_minutes`
2. Display status:
   - If `checkpoint_overdue == true`: `[CHECKPOINT] Overdue by {minutes} min - running now`
   - If `checkpoint_overdue_minutes >= 12`: `[CHECKPOINT] Recommended ({minutes} min since last)`
3. After consolidation: Update `scout.last_checkpoint` to NOW

## NEW INTEGRATION PROTOCOL (v2.3 - Prevents Disconnected Graph Nodes)

**TRIGGER:** When implementing a new software/integration with bulk documentation import (API docs, reference materials)

**MANDATORY STEPS BEFORE IMPORT:**

1. **Create HUB Note** - Central connector for all integration-related notes
   ```yaml
   # File: integrations/{software}/HUB - {Software} Integration.md
   ---
   tags: [integrations, {software}]
   type: hub
   related:
     - "[[HUB - Claude System]]"
     - "[[HUB - {Related Integration}]]"
     - (3-5 wikilinks total)
   ---
   ```

2. **Document Folder Structure** in HUB note
   - List all API endpoints/documentation files
   - Link to MCP implementation (if applicable)
   - Document integration patterns and use cases

3. **Run Wikilink Migration After Import**
   ```bash
   # After importing bulk documentation:
   python scripts/migrate-memory-frontmatter.py --live
   python scripts/build-memory-index.py
   ```

4. **Validate Graph Connectivity**
   - Check index build output for "0 isolated nodes"
   - Verify new hub appears in hub notes list
   - Confirm average links per note remains 3-5+

**WHY THIS MATTERS:**

Bulk documentation imports (like ITGlue's 27 API doc files) bypass the normal consolidation workflow that adds wikilinks. Without this protocol:
- New notes appear as isolated nodes in Obsidian graph
- Memory recall can't find them (no wikilinks to traverse)
- Integration knowledge becomes disconnected

**EVIDENCE:**

- 2026-01-15: ITGlue implementation - 27 API docs imported without wikilinks → 100% disconnected
- Fix: Created HUB note + ran migration → 100% connectivity restored

**INTEGRATION CHECKLIST:**

When implementing new software:
- [ ] Create HUB note BEFORE bulk import
- [ ] Document folder structure in HUB
- [ ] Import documentation files
- [ ] Run wikilink migration script
- [ ] Rebuild memory index
- [ ] Verify 0 isolated nodes in index output
- [ ] Add software to hub_map in memory-consolidation.md (line 157)

## Consolidation Process

### 0. Initialize Metrics Collection (FIRST STEP)

**MANDATORY:** Load metrics module at start of consolidation.

```python
#!/usr/bin/env python3
import sys
sys.path.append(".claude/scripts")
from metrics_collector import log_event, flush_metrics
```

**When to load:**
- Before ANY consolidation logic
- At top of script if implementing in Python
- After session context read if implementing in markdown

### 0.5. Preserve Working Memory (Phase 4 - BEFORE Compaction)

**PURPOSE:** Snapshot working memory BEFORE consolidation so context can be restored after compaction.

**WHEN:** Before ANY vault writes (Step 1-10). This ensures working memory state is captured before context resets.

**CRITICAL:** Without this step, compaction would lose all working memory (active clients, projects, tasks, pending actions). Phase 4 makes recovery possible.

**Snapshot Process:**

```python
import shutil
from pathlib import Path
from datetime import datetime

# Working memory paths
WORKING_MEMORY_DIR = Path(".claude/session/working-memory")
SNAPSHOT_DIR = Path(".claude/session/working-memory-snapshot")
CONTEXT_ANCHOR = Path(".claude/session/context-anchor.md")

def snapshot_working_memory():
    """Snapshot all working memory files before compaction."""

    if not WORKING_MEMORY_DIR.exists():
        return  # No working memory to snapshot

    # Create snapshot directory
    if SNAPSHOT_DIR.exists():
        shutil.rmtree(SNAPSHOT_DIR)
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)

    # Copy all 7 working memory files
    files_to_snapshot = [
        "index.md",
        "active-clients.md",
        "active-projects.md",
        "active-tasks.md",
        "context-threads.md",
        "pending-actions.md",
        "background-findings.md"
    ]

    for filename in files_to_snapshot:
        source = WORKING_MEMORY_DIR / filename
        if source.exists():
            shutil.copy2(source, SNAPSHOT_DIR / filename)

    print(f"[OK] Working memory snapshotted (7 files)")

# Execute snapshot FIRST
snapshot_working_memory()
```

**Populate context-anchor.md:**

```python
def populate_context_anchor(working_memory_index):
    """Populate context-anchor.md with working memory snapshot."""

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    # Extract key context from working memory index
    active_clients = extract_clients(working_memory_index)
    active_projects = extract_projects(working_memory_index)
    current_task = extract_current_task(working_memory_index)
    pending_count = count_pending_actions(working_memory_index)

    # Build recovery anchor
    anchor_content = f"""# Context Recovery Anchor

**Created:** {timestamp}
**Purpose:** Restore working memory after compaction
**Status:** Ready for recovery

---

## Working Memory Snapshot (Pre-Compaction)

{working_memory_index}

---

## Resume From Here

**Next action:** {current_task if current_task else "Continue current work"}
**Active clients:** {active_clients if active_clients else "None"}
**Active projects:** {active_projects if active_projects else "None"}
**Pending items:** {pending_count} pending actions

---

## Recovery Protocol

1. **Reload working memory from snapshot above**
   - Working memory preserved in: `session/working-memory-snapshot/`
   - All 7 files snapshotted before compaction

2. **Continue work on:** {current_task if current_task else "Current task"}

3. **Don't respond to background agent notifications**
   - Task notifications from compaction are stale
   - User's original task takes priority
   - Working memory shows current context

4. **Next user message:**
   - gate-enforcer.py will restore working memory from snapshot
   - Context seamlessly continues
   - No "what was I working on?" confusion

---

## Snapshot Metadata

- **Snapshot time:** {timestamp}
- **Files preserved:** 7/7
- **Active context items:** {len(active_clients.split(',')) if active_clients else 0} clients, {len(active_projects.split('\\n')) if active_projects else 0} projects

---

**Context recovery enabled. Working memory will restore automatically on next prompt.**
"""

    # Write context anchor
    with open(CONTEXT_ANCHOR, 'w', encoding='utf-8') as f:
        f.write(anchor_content)

    print(f"[OK] context-anchor.md populated for recovery")

# Read working memory index
if (WORKING_MEMORY_DIR / "index.md").exists():
    with open(WORKING_MEMORY_DIR / "index.md", 'r', encoding='utf-8') as f:
        working_memory_index = f.read()

    # Populate context anchor
    populate_context_anchor(working_memory_index)
```

**Result:**
- Working memory snapshotted to `session/working-memory-snapshot/`
- context-anchor.md populated with recovery instructions
- Ready for compaction without losing working memory context

---

### 1. Read Session Context

```python
# SESSION RESET CHECK (v2.7) - Reset counter on new chat window
# CRITICAL: Prevents counter accumulation across parallel sessions
current_session = state.get("session_id")
last_consolidated_session = state.get("memory_system", {}).get("last_session_id")

if current_session != last_consolidated_session:
    # NEW SESSION - Reset counter to 0
    if "memory_system" not in state:
        state["memory_system"] = {}
    state["memory_system"]["notes_created_this_session"] = 0
    state["memory_system"]["last_session_id"] = current_session
    # Write back to state.json atomically
    write_json("session/state.json", state)
```

```bash
# Load current session data - INCLUDING SESSION ISOLATION FIELDS
state.json → session_id, session_window, current_prompt, original_request, project
growth-output.md → detected patterns (if growth monitor active)
prompt-history.jsonl → full conversation for context extraction
```

**CRITICAL - Session Isolation (v2.3):**
MUST capture these fields from state.json for every note:
- `session_id`: Unique identifier (e.g., "protocol-enforcement-v5")
- `session_window`: User-friendly label (e.g., "Meta System Development")

**VALIDATION (MANDATORY - v2.5 with Graceful Recovery):**
```python
import json
from datetime import datetime
import random

def validate_session_isolation(state_path=".claude/session/state.json"):
    """
    Validates session_id and session_window exist in state.json.
    MUST be called BEFORE any note processing.

    v2.5: Graceful recovery - auto-generates session_id if missing.

    Returns:
        (session_id: str, session_window: str)

    Raises:
        ValueError: Only if state.json cannot be read at all
    """
    try:
        with open(state_path, 'r') as f:
            state = json.load(f)
    except FileNotFoundError:
        # Create minimal state.json if missing
        state = {}
    except json.JSONDecodeError as e:
        raise ValueError(f"state.json corrupted - cannot decode JSON: {e}")

    session_id = state.get("session_id", "")
    session_window = state.get("session_window", "")

    # Fallback 1: Check nested locations
    if not session_id:
        session_id = state.get("original_request", {}).get("session_id", "")
    if not session_window:
        session_window = state.get("original_request", {}).get("project", "")

    # Fallback 2: Auto-generate session_id if still missing (graceful recovery)
    state_modified = False
    if not session_id:
        session_id = f"session-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}-{random.randint(1000,9999)}"
        state["session_id"] = session_id
        state_modified = True
        print(f"[SESSION] Auto-generated session_id: {session_id}")

    if not session_window:
        session_window = "unknown"
        state["session_window"] = session_window
        state_modified = True

    # Persist changes if we auto-generated
    if state_modified:
        try:
            with open(state_path, 'w') as f:
                json.dump(state, f, indent=2)
        except IOError as e:
            print(f"[WARNING] Could not persist session_id to state.json: {e}")
            # Continue anyway - session_id is valid for this consolidation

    return session_id, session_window

# CALL AT START OF CONSOLIDATION (before any note processing):
session_id, session_window = validate_session_isolation()
```

**Why this matters (v2.5):**
- Prevents memory contamination between parallel chat sessions
- Graceful recovery: auto-generates session_id rather than failing
- Ensures every note has traceable origin
- Called ONCE at consolidation start, reused for all notes
- Tolerates missing/corrupted state.json (creates minimal version)

This prevents cross-session memory contamination where memories from parallel chats bleed into each other.

### 2. Extract Key Learnings

Scan session for:
- **Decisions Made** → `Decisions/YYYY-MM-DD-{topic}.md`
- **Patterns Detected** → `Patterns/{pattern-name}.md`
- **Workflow Patterns** → `Patterns/{workflow-name}.md` (with workflow_metadata block)
- **Preferences Learned** → `Preferences/{preference-type}.md`
- **Skills Applied** → `Skills-Learned/{workflow-name}.md`
- **SOPs Documented** → `SOPs/{project}/{sop-name}.md`
- **Project Learnings** → `Projects/{project}/{topic}.md`
  - **CRITICAL:** Path must be `Projects/{Client}/{topic}.md` NOT `{Client}/Projects/{topic}.md`
  - **Dynamic normalization (v2.1 - 2026-02-01):** Works for ALL clients (existing + future)
    - **Step 1:** Alias resolution (only true shortcuts: org → your org)
    - **Step 2:** Folder scan (case-insensitive: partner → your organization, exampleclient → ExampleClient)
    - **Step 3:** Auto-create new clients (title case: newclient → Newclient, acronyms: ACME → ACME)
  - **Alias map:** Only for shortcuts to different names (not case variations)
  - **No hardcoding required:** System adapts to new clients automatically
- **Error Solutions** → `Error-Solutions/{category}/{error-pattern}.md`
- **Agent Journal Entries** → `Agents/{agent-name}/journal.md` (append-only, per-agent persistent memory — NOT session-scoped. Written by the conductor on `[A2A:IMPACT]` receipt, or by any agent noting a cross-domain-relevant change. See `agents/mesh-wrapper.md` IMPACT protocol and `memory/Agents/index.md`. Never overwrite; always append with a dated entry.)

**PATH VALIDATION (MANDATORY):**

All paths MUST use a valid vault subfolder. NO files may be written directly to vault root.

```python
def validate_note_path(path):
    """
    Validates that note path uses a known vault subfolder.

    VALID:
        - Decisions/my-decision.md
        - Patterns/my-pattern.md
        - Skills-Learned/my-skill.md
        - Projects/your organization/my-note.md

    INVALID:
        - Claude/Decisions/my-decision.md  (ghost Claude/ prefix — legacy, never existed on disk)
        - my-note.md                        (vault root — no subfolder)

    Returns: Corrected path if invalid, original if valid
    Raises: ValueError if path cannot be corrected
    """
    vault_root = "~/.claude\\memory\\"

    # Remove vault root if present
    relative_path = path.replace(vault_root, "")

    # Strip ghost Claude/ prefix (legacy path format — never matched physical folders)
    if relative_path.startswith("Claude/"):
        relative_path = relative_path[len("Claude/"):]

    # Valid vault subfolders (physical folders that exist)
    valid_prefixes = [
        "Decisions/", "Patterns/", "Preferences/",
        "Skills-Learned/", "Projects/", "Error-Solutions/",
        "SOPs/", "Archive/", "Incidents/", "Agents/"
    ]

    if not any(relative_path.startswith(p) for p in valid_prefixes):
        raise ValueError(f"Invalid path: {path}. All notes must be in a valid vault subfolder.")

    return vault_root + relative_path

# BEFORE writing any note:
for note_path in notes_to_write:
    try:
        validated_path = validate_note_path(note_path)
        write_note(validated_path, content)
    except ValueError as e:
        # Log rejection to separate log file
        timestamp = datetime.utcnow().isoformat() + "Z"
        log_entry = f"{timestamp} | PATH_REJECTED | {note_path} | {str(e)}\n"
        with open("session/path-rejections.log", "a") as f:
            f.write(log_entry)
        # Skip this note
        continue
```

**Enforcement:**
- Called BEFORE every write operation
- Auto-strips ghost `Claude/` prefix from any legacy paths
- Fails consolidation if path cannot be mapped to a valid subfolder
- Prevents creation of files directly at vault root

### 2.5. Classify Inference Status — ACTIVATE DECAY (v6.1 — MANDATORY)

> **This step turns Decay-A from dormant schema into live behavior. Skipping it
> means the decay floor in `hybrid-recall-v7.py` Pass 0.25 has nothing to drop.**

For EVERY note about to be written, decide ONE of these classifications:

| Classification | Frontmatter | When to use |
|---|---|---|
| **Asserted** | `inferred: false` (or omit — default) | User explicitly stated this. Direct quotes, contracts, system facts, decisions the user made. NEVER decays. |
| **Inferred** | `inferred: true` + `confidence` + `last_verified` | YOU inferred from sample/observation. Behavioral guesses, pattern extrapolations, "the user seems to prefer X" with N<10 samples. DECAYS over time. |

**Decision rule (apply per note):**
1. Did the user **say** this in plain words this session? → asserted
2. Is this a contract, dollar figure, date, or signed commitment? → asserted
3. Is this an architectural decision the user explicitly chose? → asserted (`type: decision` → never decays anyway)
4. Did YOU pattern-match across <10 samples to infer this? → inferred
5. Is this "the user probably wants X based on context"? → inferred
6. Is this a workflow pattern observed once or twice? → inferred

**Frontmatter when inferred=true (REQUIRED):**

```yaml
---
type: preference          # OR pattern, project-note, skill-learned (NOT decision — those don't decay)
tags: [preferences, org]
inferred: true
confidence: 0.85          # 0.0–1.0 starting confidence; default 0.85 for new inferences
asserted_at: 2026-04-30   # today, ISO date — when first inferred
last_verified: 2026-04-30 # today; bump every time fact is re-confirmed in a later session
# half_life_days: 90      # OPTIONAL — else type default applies (see table at top of file)
---
```

**Re-verification protocol:** When YOU read an inferred note in a later session AND the user re-confirms the fact (or says/does something that re-asserts it), bump `last_verified` to today. This resets the decay clock without changing `confidence`.

**Promotion to asserted:** If user explicitly confirms an inference ("yes, exactly that"), promote: set `inferred: false`, `confidence: 1.0`, remove `last_verified`. Note no longer decays.

---

### 2.6. Decide Edge Relationships — ACTIVATE EDGE WALK (v6.1 — MANDATORY)

> **This step turns Edges-A from dormant schema into live behavior. Skipping it
> means the edge walk in `hybrid-recall-v7.py` Pass 6.5 has nothing to walk.**

For EVERY note about to be written, ask these THREE questions in order:

**Q1. Does this note REPLACE an older note on the same topic?**
- Use BM25 lookup or grep to find candidates: `grep -l "{topic-keywords}" memory/{folder}/`
- If found, decide: is the new note strictly newer/better, or just additional?
  - Strictly newer → write `edges.supersedes: ["[[Old-Note-Title]]"]`
  - Additional/related → use `supports` instead

**Q2. Does this note CONTRADICT an existing note?**
- If recall surfaced any note in this session that disagrees with what you're writing → write `edges.contradicts: ["[[Disagreeing-Note]]"]`
- BOTH notes should now have `contradicts` edges pointing at each other (1-directional is OK; bidirectional is better)
- Recall will surface both with `[CONFLICT]` markers when either is queried

**Q3. Does this note BUILD ON another note?**
- If yes → write `edges.supports: ["[[Foundation-Note]]"]` or `derived_from: ["[[Source-Note]]"]`

**Frontmatter shape (any subset is valid — all keys optional):**
```yaml
---
edges:
  supersedes:    ["[[Old-Auth-Pattern]]"]
  contradicts:   ["[[the user-Likes-Verbose]]"]
  supports:      ["[[the user-Voice-Profile]]"]
  derived_from:  ["[[2026-04-29-Email-Thread]]"]
---
```

**Backward compat:** Notes without `edges:` keep working — body wikilinks collapse to `refers_to` automatically. Don't add empty `edges:` blocks; just omit when nothing applies.

**Don't write contradictory edges silently.** If you write a `contradicts` edge, ALSO write a one-line note in the new note's body explaining WHY it contradicts. The recall conflict marker is the signal; the why is the resolution.

---

### 3. Validate Tags BEFORE Writing (MANDATORY - NO EXCEPTIONS)

**BULLETPROOF ENFORCEMENT:** Every note's tags are validated against the whitelist BEFORE writing. Invalid tags cause REJECTION (not warning). No exceptions.

**Load Whitelist (with graceful bootstrap):**

`session/tag-whitelist.json` is NOT a hard dependency. If the file is absent, bootstrap it
with a default whitelist BEFORE validating — treat a missing file as "seed defaults", never
as a block. The default `folders` list mirrors the `valid_prefixes` used by
`validate_note_path()` (lower-cased), so folder tags and physical vault subfolders stay in
sync — **including `agents`**.

```python
import json
import os
from datetime import datetime

def load_tag_whitelist(whitelist_path="session/tag-whitelist.json"):
    """
    Load the tag whitelist, bootstrapping a default if the file is missing.

    A missing whitelist file is a recoverable condition, not a failure: seed a
    sensible default and continue. `folders` mirrors validate_note_path()'s
    valid_prefixes (decisions/patterns/preferences/skills-learned/projects/
    error-solutions/sops/archive/incidents/agents) so tags and vault subfolders
    never drift apart.
    """
    if not os.path.exists(whitelist_path):
        default_whitelist = {
            "folders": [
                "decisions", "patterns", "preferences", "skills-learned",
                "projects", "error-solutions", "sops", "archive",
                "incidents", "agents"
            ],
            "software": [
                "memory-system", "enforcement", "git", "python",
                "javascript", "typescript", "api", "database",
                "testing", "ci-cd", "docs", "workflow"
            ],
            "max_tags": 4,
            "require_folder_first": True,
            "version": "bootstrap-1.0",
            "bootstrapped_at": datetime.utcnow().isoformat() + "Z"
        }
        os.makedirs(os.path.dirname(whitelist_path) or ".", exist_ok=True)
        with open(whitelist_path, "w") as f:
            json.dump(default_whitelist, f, indent=2)
        print(f"[WHITELIST] Bootstrapped default tag-whitelist.json at {whitelist_path}")
        return default_whitelist

    with open(whitelist_path) as f:
        return json.load(f)

whitelist = load_tag_whitelist()
```

**Validation Function (MANDATORY):**
```python
def validate_memory_tags(tags, note_title, whitelist_path="session/tag-whitelist.json"):
    """
    Validates memory tags against whitelist.

    Args:
        tags: List of tags from frontmatter
        note_title: Title of note being written
        whitelist_path: Path to tag-whitelist.json

    Returns:
        (is_valid: bool, error_msg: str)
    """
    # Load whitelist — bootstraps a default if the file is absent (never a block)
    whitelist = load_tag_whitelist(whitelist_path)

    folder_tags = whitelist['folders']
    software_tags = whitelist['software']
    max_tags = whitelist['max_tags']
    require_folder_first = whitelist['require_folder_first']

    # Check 1: At least 1 tag exists
    if not tags or len(tags) == 0:
        return False, "No tags provided - at least 1 folder tag required"

    # Check 2: First tag must be from folders list
    if require_folder_first and tags[0] not in folder_tags:
        return False, f"First tag '{tags[0]}' must be a folder tag: {folder_tags}"

    # Check 3: Max 4 tags total
    if len(tags) > max_tags:
        return False, f"Too many tags ({len(tags)}). Max {max_tags} allowed"

    # Check 4: Software tags (positions 2-4) must be in whitelist
    for tag in tags[1:]:
        if tag not in software_tags:
            return False, f"Invalid software tag '{tag}'. Valid tags: {software_tags}"

    return True, ""

def log_rejection(tags, error_msg, note_title, log_path="session/memory-rejections.log"):
    """
    Logs rejected note to rejection log.

    Args:
        tags: Tags that failed validation
        error_msg: Validation error message
        note_title: Title of rejected note
        log_path: Path to rejection log file
    """
    timestamp = datetime.utcnow().isoformat() + "Z"
    log_entry = f"{timestamp} | {tags} | {error_msg} | {note_title}\n"

    with open(log_path, "a") as f:
        f.write(log_entry)
```

**Integration into Write Flow (MANDATORY EXECUTION ORDER WITH METRICS):**
```python
# BEFORE writing ANY note to vault:
for note in notes_to_write:
    tags = note['frontmatter']['tags']
    title = note['title']

    # VALIDATE TAGS (HARD STOP)
    is_valid, error_msg = validate_memory_tags(tags, title)

    if not is_valid:
        # LOG REJECTION TO FILE
        log_rejection(tags, error_msg, title)

        # LOG REJECTION TO METRICS (MANDATORY)
        log_event("tag_rejected",
            tags=tags,
            error=error_msg,
            note_title=title
        )

        # STOP - Do not write this note
        print(f"[MEMORY REJECTED] {title}")
        print(f"  Error: {error_msg}")
        print(f"  Tags attempted: {tags}")
        print(f"  Logged to: session/memory-rejections.log")

        # Skip this note - continue to next
        continue

    # VALID - Proceed with write
    write_note_to_vault(note)

    # ALSO persist to MCP cross-session memory (memory integration v1.0)
    # Maps vault folder tag → MCP memory type
    _type_map = {
        "decisions":     "decision",
        "patterns":      "experience",
        "preferences":   "preference",
        "skills-learned":"experience",
        "projects":      "context",
        "sops":          "fact",
        "incidents":     "warning",
    }
    _mem_type  = _type_map.get(tags[0], "fact")
    _importance = 8 if tags[0] in ("decisions", "incidents") else 6
    _mcp_content = f"{note.title}: {note.summary or note.content[:300]}"
    _mcp_tags    = ",".join(tags)

    mcp__memory__remember(
        content    = _mcp_content,
        type       = _mem_type,
        tags       = _mcp_tags,
        importance = _importance
    )
    # Silent — never block consolidation if MCP fails

    # LOG SUCCESS TO METRICS (MANDATORY)
    log_event("memory_write",
        tags=tags,
        note_type=tags[0],  # Folder tag
        accepted=True
    )
```

**Validation Output Examples:**

**REJECTED - No folder tag:**
```
[MEMORY REJECTED] Automation Workflow Pattern
  Error: First tag 'automation' must be a folder tag: ['decisions', 'patterns', 'preferences', 'skills-learned', 'projects', 'sops']
  Tags attempted: ['automation', 'workflow']
  Logged to: session/memory-rejections.log
```

**REJECTED - Invalid software tag:**
```
[MEMORY REJECTED] Protocol Enforcement v5.2
  Error: Invalid software tag 'v5.2'. Valid tags: ['ticketing', 'crm', ...]
  Tags attempted: ['decisions', 'v5.2']
  Logged to: session/memory-rejections.log
```

**REJECTED - Too many tags:**
```
[MEMORY REJECTED] Memory System Update
  Error: Too many tags (5). Max 4 allowed
  Tags attempted: ['patterns', 'memory-system', 'enforcement', 'crm', 'extra']
  Logged to: session/memory-rejections.log
```

**VALID - Proceeding:**
```
[MEMORY] Writing: Protocol Enforcement v5.2
  Tags: ['decisions', 'enforcement', 'memory-system']
  Path: Claude/Decisions/Protocol-Enforcement-v5.2.md
```

**When Validation Fails:**
1. Note is NOT written to vault
2. Rejection logged to `session/memory-rejections.log`
3. Error displayed to user (if applicable)
4. Consolidation continues with remaining valid notes
5. User can review rejections and manually fix if needed

**Rejection Log Format:**
```
2026-01-16T10:30:00Z | ['automation', 'workflow'] | First tag 'automation' must be a folder tag | Automation Workflow Pattern
2026-01-16T10:30:05Z | ['decisions', 'v5.2'] | Invalid software tag 'v5.2' | Protocol Enforcement v5.2
2026-01-16T10:30:10Z | ['patterns', 'memory', 'enforcement', 'crm', 'extra'] | Too many tags (5). Max 4 allowed | Memory System Update
```

**Whitelist Management:**
- Location: `session/tag-whitelist.json`
- Update when new software added
- Version tracked in whitelist file
- No manual tag creation outside whitelist

**Why This Works:**
1. **Hard rejection** - Invalid notes never reach vault
2. **Audit trail** - Rejection log tracks all violations
3. **No pollution** - Whitelist prevents tag sprawl
4. **Self-documenting** - Error messages explain violations
5. **Maintainable** - Centralized whitelist, easy to update

### 4. Add Hierarchy Metadata (If Versioned) - NEW v3.0

**OPTIONAL:** If writing a versioned document (supersedes previous version).

**Detection Pattern:**
- Title contains version number (v1.0, v2.0, etc.)
- Prompt mentions "update", "new version", "supersede", "replace"
- Session context shows evolution of existing note

**Hierarchy Metadata Structure:**
```yaml
hierarchy:
  status: active | superseded | archived
  version: v2.0                       # Semantic version (optional)
  supersedes:                         # Documents this replaces
    - "[[Previous Version Title v1.0]]"
    - "[[Another Old Version]]"
  superseded_by: null                 # Set when this is superseded
  changelog: "Brief description of what changed"
  effective_date: YYYY-MM-DD          # When this version became active
```

**Auto-Detection Algorithm:**
```python
def should_add_hierarchy(note_data, memory_index):
    """
    Determine if new note should have hierarchy metadata.

    Criteria:
    - Title contains version (v1.0, v2.0, etc.)
    - Prompt mentions "update", "new version", "replace"
    - Similar note exists in vault (same base title)

    Returns: hierarchy dict or None
    """
    import re

    title = note_data["title"]

    # Detect version in title
    version_match = re.search(r'v(\d+\.\d+)', title, re.IGNORECASE)
    if not version_match:
        return None  # Not versioned

    version = f"v{version_match.group(1)}"

    # Extract base title (remove version)
    base_title = re.sub(r'v\d+\.\d+', '', title, flags=re.IGNORECASE).strip()
    base_title = re.sub(r'\s+', ' ', base_title)
    base_title = re.sub(r'\s*[-–—]\s*$', '', base_title)

    # Search for older versions in index
    candidates = []
    for note in memory_index.get("notes", []):
        note_title = note["title"]
        note_version_match = re.search(r'v(\d+\.\d+)', note_title, re.IGNORECASE)

        if note_version_match:
            note_version = f"v{note_version_match.group(1)}"
            note_base = re.sub(r'v\d+\.\d+', '', note_title, flags=re.IGNORECASE).strip()
            note_base = re.sub(r'\s+', ' ', note_base)
            note_base = re.sub(r'\s*[-–—]\s*$', '', note_base)

            # Same base title?
            if note_base.lower() == base_title.lower():
                # Parse versions
                def parse_ver(v):
                    m = re.match(r'v(\d+)\.(\d+)', v)
                    return (int(m.group(1)), int(m.group(2))) if m else (0, 0)

                current_ver = parse_ver(version)
                other_ver = parse_ver(note_version)

                # Is this an older version?
                if other_ver < current_ver:
                    candidates.append(f"[[{note_title}]]")

    # Extract changelog from prompt or session context
    changelog = extract_changelog_from_prompt(note_data.get("session_context", ""))

    # Build hierarchy metadata
    if candidates:
        # This version supersedes older versions
        return {
            "status": "active",
            "version": version,
            "supersedes": candidates,
            "superseded_by": None,
            "changelog": changelog or "Updated version",
            "effective_date": datetime.now().strftime("%Y-%m-%d")
        }
    else:
        # Versioned but no predecessors - still add hierarchy
        return {
            "status": "active",
            "version": version,
            "supersedes": [],
            "superseded_by": None,
            "changelog": changelog or "Initial version",
            "effective_date": datetime.now().strftime("%Y-%m-%d")
        }


def extract_changelog_from_prompt(context):
    """Extract what changed from prompt/session context."""
    # Look for phrases like "changed:", "updated:", "fixed:"
    patterns = [
        r'(?:changed|updated|fixed|added|removed):\s*(.+)',
        r'(?:now|instead)\s+(.+)',
        r'(?:replaces?|supersedes?)\s+.+?\s+(?:with|by)\s+(.+)'
    ]

    for pattern in patterns:
        match = re.search(pattern, context, re.IGNORECASE)
        if match:
            changelog = match.group(1).strip()
            # Truncate if too long
            if len(changelog) > 150:
                changelog = changelog[:147] + "..."
            return changelog

    return "Version update"
```

**Auto-Update Superseded Notes:**

When writing a note with `supersedes` field, MUST update the superseded notes:

```python
def update_superseded_notes(supersedes_list, new_note_title, vault_path):
    """
    Update older versions to mark them as superseded.

    Args:
        supersedes_list: List of wikilinks to update
        new_note_title: Title of the new version
        vault_path: Path to memory vault
    """
    for wikilink in supersedes_list:
        # Extract title from [[Title]]
        old_title = wikilink.strip("[]")

        # Find note file
        old_note_path = find_note_by_title(old_title, vault_path)
        if not old_note_path:
            continue  # Note not found

        # Load frontmatter
        frontmatter, body = load_note(old_note_path)

        # Update hierarchy metadata
        if "hierarchy" not in frontmatter:
            frontmatter["hierarchy"] = {}

        frontmatter["hierarchy"]["status"] = "superseded"
        frontmatter["hierarchy"]["superseded_by"] = f"[[{new_note_title}]]"

        # Save updated note
        save_note(old_note_path, frontmatter, body)
```

**Integration into Write Flow:**

```python
# After drafting note content, before writing to disk
note_data = {
    "title": extract_title(body),
    "session_context": state.get("current_prompt", "")
}

# Load memory index
memory_index = read_json("session/memory-index.json")

# Check if hierarchy should be added
hierarchy = should_add_hierarchy(note_data, memory_index)

if hierarchy:
    # Add to frontmatter
    frontmatter["hierarchy"] = hierarchy

    # Validate
    is_valid, errors = validate_hierarchy_metadata(hierarchy)
    if not is_valid:
        log_rejection(errors, "Invalid hierarchy metadata")
        continue  # Skip this note

    # Update superseded notes
    if hierarchy.get("supersedes"):
        update_superseded_notes(
            hierarchy["supersedes"],
            note_data["title"],
            vault_path
        )

# Continue with normal write process
write_note(path, frontmatter, body)
```

**Validation:**

Hierarchy metadata is validated using `validate_hierarchy_metadata()` function:
- Status must be one of: active, superseded, archived
- Version must match pattern: v\d+\.\d+
- Supersedes must be array of wikilinks
- Superseded_by must be single wikilink or null
- Effective_date must be YYYY-MM-DD format

**See:** `scripts/migrate_memory_hierarchy.py` for validation implementation

### 4.5. Remove Old Versions (DEPRECATED)

**NOTE:** With hierarchy system v3.0, old versions are NO LONGER removed. Instead:
- Old versions are marked as `status: superseded`
- They remain accessible for evolution tracking
- Memory recall prioritizes active versions automatically
- Users can see why changes happened

**Migration:** Existing notes without hierarchy default to `status: active`

### 4.7. Strip Private Content (NEW v6.0 - PRIVACY PROTECTION)

**PURPOSE:** Remove sensitive content marked with `<private>` tags before storing in vault.

**Adopted from:** claude-mem.ai's privacy tag system.

**How It Works:**
- Users can wrap sensitive content in `<private>...</private>` tags
- Content within these tags is stripped BEFORE writing to vault
- Replaced with `[REDACTED]` marker for visibility
- Original content never reaches persistent storage

**Implementation:**
```python
import re

def strip_private_content(content):
    """
    Remove <private>...</private> blocks from content before storage.

    Args:
        content: Raw content that may contain private tags

    Returns:
        Sanitized content with private blocks replaced by [REDACTED]
    """
    # Pattern matches <private>anything</private> including newlines
    pattern = r'<private>.*?</private>'

    # Count how many private blocks were stripped
    matches = re.findall(pattern, content, flags=re.DOTALL | re.IGNORECASE)
    stripped_count = len(matches)

    # Replace with [REDACTED] marker
    sanitized = re.sub(pattern, '[REDACTED]', content, flags=re.DOTALL | re.IGNORECASE)

    if stripped_count > 0:
        print(f"[PRIVACY] Stripped {stripped_count} private block(s) from content")

    return sanitized, stripped_count


# Also strip from frontmatter session field if present
def sanitize_session_context(session_text):
    """Sanitize session description in frontmatter."""
    return strip_private_content(session_text)[0]
```

**Integration into Write Flow:**
```python
# BEFORE writing ANY note, strip private content:
for note in notes_to_write:
    # Strip from body content
    note['content'], body_stripped = strip_private_content(note['content'])

    # Strip from session context in frontmatter
    if 'session' in note['frontmatter']:
        note['frontmatter']['session'] = sanitize_session_context(
            note['frontmatter']['session']
        )

    # Continue with normal validation and write flow
    # ...
```

**Usage Example:**
```markdown
## Context
Learned this while debugging <private>client API key: sk-abc123xyz</private>
authentication issues with the your CRM integration.

## Details
The endpoint requires <private>Authorization: Bearer SECRET_TOKEN</private>
but works with standard OAuth flow.
```

**After Stripping:**
```markdown
## Context
Learned this while debugging [REDACTED]
authentication issues with the your CRM integration.

## Details
The endpoint requires [REDACTED]
but works with standard OAuth flow.
```

**What Gets Protected:**
- API keys, tokens, secrets
- Passwords and credentials
- Personal identifiable information (PII)
- Client-specific sensitive data
- Anything the user wraps in `<private>` tags

**Validation:**
- Tags are case-insensitive (`<PRIVATE>`, `<Private>`, `<private>` all work)
- Nested tags not supported (use one pair per block)
- Empty tags `<private></private>` are removed silently
- Malformed tags (missing closing) are left as-is (safe failure)

---

### 4.8. Extract Causality Context (NEW v6.0 - RICHER MEMORY)

**PURPOSE:** Capture what preceded and followed decisions for richer context during recall.

**Adopted from:** claude-mem.ai's causality tracking ("what preceded decisions and what followed them").

**Why This Matters:**
Understanding WHY a decision was made is often more valuable than the decision itself. Causality tracking captures:
- What problem triggered the solution
- What the state was before the change
- What happened after implementation
- The cause-and-effect chain

**New Frontmatter Fields (OPTIONAL - backwards compatible):**
```yaml
causality:
  preceded_by: "Working on your CRM pagination, hitting 200 record limit"
  trigger: "API returning incomplete data, user complained about missing deals"
  followed_by: "Implemented pageSize: 1000 across all queries, verified complete data"
  outcome: "success"  # success | partial | failed | unknown
```

**Extraction Algorithm:**
```python
import re
from datetime import datetime

def extract_causality_context(session_context, prompt_history, note_content):
    """
    Extract causality context from session data.

    Args:
        session_context: Current prompt/task description
        prompt_history: Recent conversation history (last 5-10 turns)
        note_content: The actual learning/decision being recorded

    Returns:
        Dict with preceded_by, trigger, followed_by, outcome
    """
    causality = {
        "preceded_by": None,
        "trigger": None,
        "followed_by": None,
        "outcome": "unknown"
    }

    # 1. Extract TRIGGER from prompt history
    # Look for problem statements, errors, user complaints
    trigger_patterns = [
        r"(?:error|issue|problem|bug|fail).*?:?\s*(.+)",
        r"(?:user|client)\s+(?:complained|reported|said).*?:?\s*(.+)",
        r"(?:need|want|require).*?(?:to|a|the)\s+(.+)",
        r"(?:doesn't|doesn't|isn't|can't|won't)\s+(.+)"
    ]

    for pattern in trigger_patterns:
        for turn in prompt_history[-5:]:  # Last 5 turns
            match = re.search(pattern, turn, re.IGNORECASE)
            if match:
                trigger = match.group(1).strip()
                if len(trigger) > 10 and len(trigger) < 200:
                    causality["trigger"] = trigger[:150] + ("..." if len(trigger) > 150 else "")
                    break
        if causality["trigger"]:
            break

    # 2. Extract PRECEDED_BY from session context
    # What was being worked on before this decision
    preceded_patterns = [
        r"(?:working on|implementing|building|fixing|updating)\s+(.+?)(?:\.|,|$)",
        r"(?:during|while|when)\s+(.+?)(?:\.|,|$)",
        r"^(.+?)\s+(?:led to|caused|resulted in)"
    ]

    for pattern in preceded_patterns:
        match = re.search(pattern, session_context, re.IGNORECASE)
        if match:
            preceded = match.group(1).strip()
            if len(preceded) > 5:
                causality["preceded_by"] = preceded[:150] + ("..." if len(preceded) > 150 else "")
                break

    # 3. Extract FOLLOWED_BY from note content
    # Look for "then", "after", "resulted in", "now"
    followed_patterns = [
        r"(?:then|after|afterwards)\s+(.+?)(?:\.|$)",
        r"(?:now|currently)\s+(?:it|the|we|I)\s+(.+?)(?:\.|$)",
        r"(?:resulted in|led to|fixed by)\s+(.+?)(?:\.|$)",
        r"(?:implemented|applied|deployed)\s+(.+?)(?:\.|$)"
    ]

    for pattern in followed_patterns:
        match = re.search(pattern, note_content, re.IGNORECASE)
        if match:
            followed = match.group(1).strip()
            if len(followed) > 5:
                causality["followed_by"] = followed[:150] + ("..." if len(followed) > 150 else "")
                break

    # 4. Detect OUTCOME from content keywords
    success_keywords = ["fixed", "works", "solved", "complete", "success", "deployed", "implemented"]
    failure_keywords = ["failed", "broken", "reverted", "didn't work", "rollback"]
    partial_keywords = ["partially", "workaround", "temporary", "still needs"]

    content_lower = note_content.lower()
    if any(kw in content_lower for kw in success_keywords):
        causality["outcome"] = "success"
    elif any(kw in content_lower for kw in failure_keywords):
        causality["outcome"] = "failed"
    elif any(kw in content_lower for kw in partial_keywords):
        causality["outcome"] = "partial"

    return causality


def format_causality_for_frontmatter(causality):
    """Format causality dict for YAML frontmatter."""
    # Only include non-None fields
    formatted = {}
    for key, value in causality.items():
        if value and value != "unknown":
            formatted[key] = value

    # Return None if no useful causality extracted
    if not formatted or (len(formatted) == 1 and "outcome" in formatted):
        return None

    return formatted
```

**Integration into Write Flow:**
```python
# AFTER extracting note content, BEFORE writing:
for note in notes_to_write:
    # Extract causality context
    causality = extract_causality_context(
        session_context=state.get("current_prompt", ""),
        prompt_history=prompt_history[-10:],  # Last 10 turns
        note_content=note['content']
    )

    # Add to frontmatter if meaningful
    formatted_causality = format_causality_for_frontmatter(causality)
    if formatted_causality:
        note['frontmatter']['causality'] = formatted_causality

    # Continue with write flow
```

**Example Output (Note with Causality):**
```yaml
---
created: 2026-01-15T14:30:00Z
modified: 2026-01-15T14:30:00Z
project: partner
domain: crm
type: decision
tags: [decisions, crm]
causality:
  preceded_by: "Working on deal sync, noticing missing records"
  trigger: "API returning only 200 deals instead of expected 450"
  followed_by: "Implemented pageSize: 200 with pagination loop"
  outcome: success
session: Fixing your CRM pagination for complete deal extraction
session_id: crm-sync-jan-15
---

# your CRM Pagination Protocol

## Context
During deal synchronization, discovered API was truncating results...
```

**Recall Enhancement:**
When displaying notes with causality, include the context:
```markdown
3. **your CRM Pagination Protocol** (Decision, 2026-01-15) ~650
   API pagination fix for complete data extraction.
   Trigger: API returning only 200 deals instead of expected 450
   Outcome: ✅ success
   File: Decisions/your CRM-Pagination-Protocol.md
```

**Backwards Compatibility:**
- `causality` field is OPTIONAL
- Existing notes without it continue to work
- Recall shows causality only if present
- No migration required for existing vault

---

### 5. Write Structured Notes (with AUTOMATIC WIKILINK GENERATION)

**CRITICAL:** Wikilink generation is MANDATORY and happens automatically BEFORE writing each note. Every note MUST have 3-5 wikilinks in the `related:` frontmatter field. No human discipline required.

**SESSION ISOLATION (v2.3 - BLOCKING FIX):**
Before writing ANY note, MUST:
1. Read `session_id` and `session_window` from state.json
2. Include in frontmatter (required fields)
3. Validate they exist and are non-empty
4. FAIL consolidation if missing

This prevents memory contamination between parallel chat sessions.

**Template (MANDATORY - All Properties Required + v6.0 Enhancements):**
```markdown
---
created: YYYY-MM-DDTHH:MM:SSZ
modified: YYYY-MM-DDTHH:MM:SSZ
project: {meta|partner|org|lms}
domain: {ticketing|crm|memory-system|bim|android|etc}
type: {decision|pattern|preference|skill-learned|project-note|error-solution}
tags: [{folder-tag}, {software-tag-1}, {software-tag-2}]
related:
  - "[[Hub Note]]"
  - "[[Related Note 1]]"
  - "[[Related Note 2]]"
session: {task description}
session_id: {session identifier from state.json - e.g. "protocol-enforcement-v5"}
session_window: {user-friendly label - e.g. "your organization main", "an LMS grading", "your org dev"}
consolidated_at: YYYY-MM-DDTHH:MM:SSZ

# OPTIONAL: Causality context (v6.0 - auto-extracted if detectable)
causality:
  preceded_by: "What was happening before this decision"
  trigger: "The problem/event that prompted this"
  followed_by: "What happened after implementation"
  outcome: success  # success | partial | failed | unknown

# OPTIONAL: Hierarchy metadata (for versioned documents only)
hierarchy:
  status: active
  version: v2.0
  supersedes:
    - "[[Previous Version v1.0]]"
  superseded_by: null
  changelog: "Brief description of what changed"
  effective_date: YYYY-MM-DD
---

# {Title}

## Context
{Why this was learned - from conversation}

## Details
{The actual knowledge - specific, actionable}

## Applied To
- Files: {modified files}
- Commands: {key commands run}
- Tools: {MCPs/integrations used}

## Related
- [[Other relevant memories]]

## Success Criteria
{If applicable - how we knew this worked}
```

### WIKILINK GENERATION ALGORITHM v2.0 (AUTOMATIC + MANDATORY)

**BULLETPROOF DESIGN:** Wikilinks are generated automatically by the consolidation system. No human discipline required. The algorithm runs BEFORE writing each note and MUST complete successfully or consolidation fails.

**When It Runs:**
1. After drafting note content
2. Before writing to disk
3. As part of frontmatter construction
4. Validated before save (must have 3-5 links)

**5-Step Algorithm (MANDATORY EXECUTION ORDER):**

```python
def generate_wikilinks_mandatory(note_data, memory_index):
    """
    Automatic wikilink generation for new memory notes.
    MUST return 3-5 wikilinks or raise error.

    Args:
        note_data: Dict with 'title', 'domain', 'type', 'content'
        memory_index: Current memory-index.json from session/

    Returns:
        List of 3-5 wikilink strings like ["[[Hub]]", "[[Note 1]]", ...]
    """
    links = []
    title = note_data['title']
    domain = note_data['domain']
    note_type = note_data['type']
    content = note_data['content']

    # STEP 1: Hub link (ALWAYS add if domain has hub)
    hub_map = {
        'memory-system': 'HUB - Memory System',
        'enforcement': 'HUB - Protocol Enforcement',
        'ticketing': 'HUB - your CRM Integration',
        'crm': 'HUB - your CRM Integration',
        'leroy': 'HUB - LeRoy Reports',
        'bim': 'HUB - BIM',
        'android': 'HUB - Android Development',
        'git': 'HUB - Git Workflow',
        'catalog': 'HUB - your catalog service Integration',
    }
    hub_name = hub_map.get(domain)
    if hub_name:
        links.append(f"[[{hub_name}]]")

    # STEP 2: Find version predecessor (evolution chain)
    # Match patterns like "v5.2", "v2.0", "v1.5"
    version_match = re.search(r'v(\d+)\.(\d+)', title, re.IGNORECASE)
    if version_match:
        major = int(version_match.group(1))
        minor = int(version_match.group(2))
        base_title = re.sub(r'v\d+\.\d+', '', title).strip(' -')

        # Search index for previous version
        candidates = []
        for note in memory_index.get('notes', []):
            note_title = note['title']
            note_base = re.sub(r'v\d+\.\d+', '', note_title).strip(' -')

            if note_base.lower() == base_title.lower():
                note_version = re.search(r'v(\d+)\.(\d+)', note_title, re.IGNORECASE)
                if note_version:
                    note_major = int(note_version.group(1))
                    note_minor = int(note_version.group(2))
                    # Is this an earlier version?
                    if (note_major, note_minor) < (major, minor):
                        candidates.append((note_title, note_major, note_minor))

        if candidates:
            # Get closest predecessor
            candidates.sort(key=lambda x: (x[1], x[2]), reverse=True)
            predecessor = candidates[0][0]
            if f"[[{predecessor}]]" not in links:
                links.append(f"[[{predecessor}]]")

    # STEP 3: Pattern-Decision pairs
    if note_type in ['decision', 'pattern']:
        target_type = 'pattern' if note_type == 'decision' else 'decision'
        pairs = []
        for note in memory_index.get('notes', []):
            if note['type'] == target_type and note['domain'] == domain:
                pair_title = note['title']
                if f"[[{pair_title}]]" not in links:
                    pairs.append(pair_title)
                    if len(pairs) >= 2:
                        break
        links.extend([f"[[{p}]]" for p in pairs])

    # STEP 4: Domain siblings (same domain, different notes)
    siblings = []
    for note in memory_index.get('notes', []):
        if note['domain'] == domain and note['title'] != title:
            sibling_title = note['title']
            if f"[[{sibling_title}]]" not in links:
                siblings.append(sibling_title)
                if len(siblings) >= 2:
                    break
    links.extend([f"[[{s}]]" for s in siblings])

    # STEP 5: Content-mentioned notes (scan content for references)
    # Look for phrases like "builds on X" or "see X" or "related to X"
    for note in memory_index.get('notes', []):
        note_title = note['title']
        # Check if note title appears in content
        if note_title.lower() in content.lower() and f"[[{note_title}]]" not in links:
            links.append(f"[[{note_title}]]")

    # VALIDATION: Must return 3-5 unique links
    unique_links = list(dict.fromkeys(links))[:5]

    if len(unique_links) < 3:
        # FALLBACK: If still <3, add generic meta notes
        fallback_notes = [
            "HUB - Claude System",
            "HUB - Protocol Enforcement",
            "HUB - Memory System"
        ]
        for fallback in fallback_notes:
            if f"[[{fallback}]]" not in unique_links and len(unique_links) < 3:
                unique_links.append(f"[[{fallback}]]")

    if len(unique_links) < 3:
        raise ValueError(f"Failed to generate minimum 3 wikilinks for note: {title}")

    return unique_links
```

**Hub Note Mapping (Complete):**

| Domain | Hub Note |
|--------|----------|
| memory-system | `[[HUB - Memory System]]` |
| enforcement | `[[HUB - Protocol Enforcement]]` |
| ticketing | `[[HUB - your CRM Integration]]` |
| crm | `[[HUB - your CRM Integration]]` |
| leroy | `[[HUB - LeRoy Reports]]` |
| bim | `[[HUB - BIM]]` |
| android | `[[HUB - Android Development]]` |
| git | `[[HUB - Git Workflow]]` |
| catalog | `[[HUB - your catalog service Integration]]` |
| general | `[[HUB - Claude System]]` (fallback) |

**Integration into Consolidation Flow:**

```python
# BEFORE: Old flow (manual wikilinks)
frontmatter = build_frontmatter(metadata)
content = f"---\n{yaml.dump(frontmatter)}\n---\n\n{body}"
write_note(path, content)

# AFTER: New flow (automatic wikilinks)
frontmatter = build_frontmatter(metadata)

# Load memory index
memory_index = read_json("session/memory-index.json")

# MANDATORY wikilink generation
note_data = {
    'title': extract_title(body),
    'domain': frontmatter['domain'],
    'type': frontmatter['type'],
    'content': body
}
wikilinks = generate_wikilinks_mandatory(note_data, memory_index)

# Add to frontmatter
frontmatter['related'] = wikilinks

# Write with validated wikilinks
content = f"---\n{yaml.dump(frontmatter)}\n---\n\n{body}"
write_note(path, content)

# Validation check
assert 3 <= len(frontmatter['related']) <= 5, "Wikilink validation failed"
```

**Validation Rules (HARD CONSTRAINTS + ENFORCEMENT):**

Before writing any note, MUST verify:
1. `related:` field exists in frontmatter
2. Contains 3-5 wikilinks (not more, not less)
3. All wikilinks are properly formatted: `[[Title]]`
4. No duplicate wikilinks in list
5. If validation fails, retry generation OR fail consolidation

**ORPHAN PREVENTION VALIDATION (v3.0 - BULLETPROOF):**

```python
def validate_no_orphans_before_write(note_path, frontmatter, content):
    """
    MANDATORY validation before writing ANY note.
    Prevents orphan creation by ensuring wikilinks exist.

    Args:
        note_path: Path where note will be written
        frontmatter: Dict with metadata
        content: Full note content (frontmatter + body)

    Returns:
        (is_valid: bool, error_msg: str)

    Raises:
        ValueError if orphan detected (blocks write)
    """

    # Check 1: Frontmatter has 'related' field
    if 'related' not in frontmatter:
        error = "ORPHAN BLOCKED: No 'related' field in frontmatter"
        log_orphan_prevention(note_path, error)
        raise ValueError(error)

    # Check 2: Related field has 3-5 wikilinks
    related = frontmatter['related']
    if not related or len(related) < 3:
        error = f"ORPHAN BLOCKED: Only {len(related)} wikilinks (need 3-5)"
        log_orphan_prevention(note_path, error, related)
        raise ValueError(error)

    if len(related) > 5:
        error = f"ORPHAN BLOCKED: Too many wikilinks ({len(related)}, max 5)"
        log_orphan_prevention(note_path, error, related)
        raise ValueError(error)

    # Check 3: Wikilinks are properly formatted
    wikilink_pattern = r'\[\[.+?\]\]'
    for link in related:
        if not re.match(wikilink_pattern, link):
            error = f"ORPHAN BLOCKED: Invalid wikilink format: {link}"
            log_orphan_prevention(note_path, error, related)
            raise ValueError(error)

    # Check 4: No duplicate wikilinks
    if len(related) != len(set(related)):
        error = "ORPHAN BLOCKED: Duplicate wikilinks detected"
        log_orphan_prevention(note_path, error, related)
        raise ValueError(error)

    # PASS - Note is connected
    return True, ""

def log_orphan_prevention(note_path, error, wikilinks=None):
    """Log orphan prevention to track near-misses."""
    timestamp = datetime.now().isoformat() + "Z"
    log_entry = {
        'timestamp': timestamp,
        'note_path': str(note_path),
        'error': error,
        'wikilinks': wikilinks
    }

    log_file = Path("session/orphan-prevention.log")
    with open(log_file, "a") as f:
        f.write(json.dumps(log_entry) + "\n")

    print(f"[ORPHAN PREVENTED] {note_path.name}")
    print(f"  Error: {error}")
    if wikilinks:
        print(f"  Links: {wikilinks}")
```

**Integration into Write Flow (MANDATORY - POSITION BEFORE WRITE):**

```python
# BEFORE writing ANY note:
for note in notes_to_write:
    frontmatter = note['frontmatter']
    content = note['content']
    path = note['path']

    # 1. GENERATE WIKILINKS (if not already present)
    if 'related' not in frontmatter or len(frontmatter['related']) < 3:
        memory_index = read_json("session/memory-index.json")
        note_data = {
            'title': note['title'],
            'domain': frontmatter['domain'],
            'type': frontmatter['type'],
            'content': content
        }
        frontmatter['related'] = generate_wikilinks_mandatory(note_data, memory_index)

    # 2. VALIDATE NO ORPHANS (BLOCKING CHECK)
    try:
        validate_no_orphans_before_write(path, frontmatter, content)
    except ValueError as e:
        # ORPHAN DETECTED - BLOCK WRITE
        print(f"[WRITE BLOCKED] {path.name}")
        print(f"  Reason: {str(e)}")
        print(f"  Fix: Add wikilinks to frontmatter 'related' field")

        # Log to metrics
        log_event("orphan_prevented",
            note_path=str(path),
            error=str(e),
            wikilinks=frontmatter.get('related', [])
        )

        # SKIP THIS NOTE - DO NOT WRITE
        continue

    # 3. WRITE NOTE (validation passed)
    write_note_to_vault(path, frontmatter, content)

    # Log success
    log_event("memory_write",
        note_path=str(path),
        wikilinks=len(frontmatter['related']),
        orphan_prevented=True
    )
```

**Output Example (Orphan Blocked):**

```
[WRITE BLOCKED] Email-Pattern-Learning-System.md
  Reason: ORPHAN BLOCKED: Only 0 wikilinks (need 3-5)
  Fix: Add wikilinks to frontmatter 'related' field

[ORPHAN PREVENTED] Email-Pattern-Learning-System.md
  Error: ORPHAN BLOCKED: Only 0 wikilinks (need 3-5)
  Links: []
```

**Logging:**
- All blocked writes logged to `session/orphan-prevention.log`
- Metrics logged for dashboard tracking
- No notes written without 3-5 wikilinks (ZERO TOLERANCE)

**Example Output (Complete Note with Auto-Generated Wikilinks + v2.2 Multi-Session Tracking):**

```markdown
---
created: 2026-01-14T12:00:00Z
modified: 2026-01-14T12:00:00Z
project: meta
domain: memory-system
type: decision
tags: [decisions, memory-system]
related:
  - "[[HUB - Memory System]]"
  - "[[Pattern - Memory Recall Gap]]"
  - "[[Decision - Protocol Enforcement v5.2]]"
  - "[[Skill - Memory Consolidation]]"
session: Implementing auto-wikilink system for graph connectivity
session_id: protocol-enforcement-v5
session_window: Meta System Development
consolidated_at: 2026-01-14T12:05:00Z
---

# Auto-Wikilink System for Memory Notes

## Context
Obsidian's graph view shows isolated nodes because our notes lack explicit wikilinks. Tags alone don't create edges in the graph. This decision makes wikilink generation AUTOMATIC and MANDATORY during consolidation.

## Details
The consolidation system now calls `generate_wikilinks_mandatory()` BEFORE writing each note. This function:
- Uses the 5-step algorithm from migrate-memory-frontmatter.py
- Reads memory-index.json to find related notes
- Auto-detects hub links, version chains, pattern-decision pairs, domain siblings
- Validates that 3-5 wikilinks exist before saving
- Fails consolidation if validation fails (bulletproof enforcement)

## Applied To
- Files: skills/meta/memory-consolidation.md
- Updated: Frontmatter template, algorithm section, validation rules
- Integration: Growth Monitor, Project Sentinel, all agents writing notes

## Related
- [[HUB - Memory System]] - Parent hub for all memory system notes
- [[Pattern - Memory Recall Gap]] - The problem this solves
- [[Decision - Protocol Enforcement v5.2]] - Uses similar hook pattern for enforcement
- [[Skill - Memory Consolidation]] - This note updates that skill

## Success Criteria
- Every new note has 3-5 wikilinks automatically
- Obsidian graph shows connected nodes (no isolated islands)
- Zero manual wikilink creation required
- Validation catches any notes with missing links before save
```

**Why This Works:**

1. **No Manual Work:** Algorithm runs automatically, agents don't need to remember
2. **Bulletproof:** Validation fails consolidation if links missing
3. **Scales:** Uses memory-index.json (fast lookup, O(1) per note)
4. **Graph-Ready:** Every note appears connected in Obsidian graph view
5. **Proven:** Same algorithm used by migrate-memory-frontmatter.py (already tested)

**Required Properties (NEVER omit - v2.2 with Multi-Session Tracking):**
- `created`: ISO 8601 timestamp when note was created
- `modified`: ISO 8601 timestamp (same as created initially)
- `project`: One of [meta, partner, org, lms]
- `domain`: Specific domain (ticketing, crm, memory-system, bim, android, etc.)
- `type`: One of [decision, pattern, preference, skill-learned, project-note]
- `tags`: Array following STRICT TAG RULES (see below)
- `session`: Brief description of the task/session context
- `session_id`: Read from `state.json` → `session_id` field (e.g., "protocol-enforcement-v5")
- `session_window`: Read from `state.json` → `session_window` field OR infer from project (e.g., "your organization main")
- `consolidated_at`: ISO 8601 timestamp when consolidation executed (NOW)

### STRICT TAG RULES v2.1 (HARD CONSTRAINTS)

**FOR CLAUDE/ SUBFOLDER:**

**Tag 1 (REQUIRED):** MUST be the parent folder name (lowercase)
- `decisions` | `patterns` | `preferences` | `skills-learned` | `sops` | `projects`

**Tags 2-4 (OPTIONAL):** Software/integration tags ONLY
- `ticketing` | `crm` | `catalog` | `bim` | `android`
- `git` | `netlify` | `playwright` | `supabase` | `gas`
- `python` | `memory-system` | `enforcement` | `leroy`

**FOR INTEGRATIONS/ SUBFOLDER (OPTION 1 - Meaningful Context):**

**Tag 1:** `integrations` (always)
**Tag 2:** Software name (`ticketing` | `crm` | `catalog` | `products`)
**Tag 3:** Meaningful context from folder path

| Folder Path | Context Tag |
|-------------|-------------|
| `company/*` | `company` |
| `*/contacts/*` | `contacts` |
| `service-desk/*` | `service-desk` |
| `service-desk/tickets/*` | `tickets` |
| `sales/opportunities/*` | `opportunities` |
| `finance/*` | `finance` |
| `finance/agreements/*` | `agreements` |
| `procurement/*` | `procurement` |
| `scheduling/*` | `scheduling` |
| `projects/*` | `projects` |
| `system/*` | `system` |
| `reference/*` | `reference` |

**Context Tag Distribution (517 files):**
- reference: 74 (14.3%) | service-desk: 51 (9.9%) | members: 40 (7.7%)
- system: 40 (7.7%) | company: 38 (7.4%) | finance: 29 (5.6%)
- tickets: 14 (2.7%) | opportunities: 12 (2.3%) | ... (29 unique tags)

**Examples:**
```yaml
# Claude/ files - CORRECT:
tags: [decisions, ticketing, crm]
tags: [patterns, memory-system]
tags: [skills-learned, leroy, ticketing]

# Integrations/ files - CORRECT:
tags: [integrations, ticketing, company]      # company/companies/*.md
tags: [integrations, ticketing, tickets]       # service-desk/tickets/*.md
tags: [integrations, ticketing, opportunities] # sales/opportunities/*.md
tags: [integrations, crm]                    # crm/*.md (shallow path, no 3rd tag)

# INCORRECT:
tags: [hooks, enforcement, meta-architecture, bulletproof]  # No folder, invalid types
tags: []  # Missing required folder tag
tags: [decisions, v5.2, automation]  # Invalid version and action tags
tags: [integrations, ticketing]  # Missing context tag for deep path
```

**INVALID TAGS (NEVER USE):**
- Descriptive tags: bulletproof, successful, critical, important
- Action tags: automation, validation, workflow, implementation
- Version tags: v5, v5.1, v5.2, v2
- Duplicate category tags: hooks, patterns, preferences (use folder tag)
- Vague tags: meta-system, meta-architecture, user-expectations

**MAX TAGS:** 4 (1 folder + up to 3 software/context)

**Validation Rule:** If tags don't follow this structure, the note is INVALID and must be corrected before saving.

**Property Guidelines:**
- **created/modified**: Use ISO format `2026-01-13T15:43:59.776286Z`
- **project**: Infer from state.json or conversation context
- **domain**: Extract from tools used, files modified, or task keywords
- **type**: Match folder where note is saved (Decisions → decision, etc.)
- **tags**: MUST follow strict tag rules above (folder + software only) AND pass validation
- **session**: One sentence describing what was being worked on

**TAG VALIDATION (MANDATORY - v1.0):**

Before writing frontmatter, MUST validate tags using the validation function from section 3. If validation fails, the entire note is REJECTED and logged to memory-rejections.log. NO NOTES may be written with invalid tags.

**SOP-Specific Properties (Additional):**

For notes saved to `Claude/SOPs/`, add these additional frontmatter properties:

```yaml
---
# ... standard properties above ...
type: sop
version: v1.0                    # SOP version number (increment on updates)
last_reviewed: YYYY-MM-DD        # When SOP was last verified as current
owner: {role or person}          # Who maintains this SOP
status: active | draft | archived
---
```

**SOP Property Guidelines:**
- **version**: Start at v1.0, increment for updates (v1.1, v2.0, etc.)
- **last_reviewed**: Date when SOP was verified; triggers review reminders
- **owner**: Role (e.g., "Sales Engineering Manager") or person who maintains
- **status**: `active` (in use), `draft` (being developed), `archived` (obsolete)

**Error-Solution-Specific Properties (Additional):**

For notes saved to `Claude/Error-Solutions/`, add these additional frontmatter properties:

```yaml
---
# ... standard properties above ...
type: error-solution
error_type: {bash_exit_1|io_error|state_corruption|json_decode|mcp_error|etc}
signature: "{error_type}:{context_hash}"
status: unresolved | resolved | workaround
occurrences: N                   # How many times this error occurred
first_seen: YYYY-MM-DDTHH:MM:SSZ
last_seen: YYYY-MM-DDTHH:MM:SSZ
---

# {Error Title}

## Error Details

**Type:** `{error_type}`
**Command/Operation:** `{what was attempted}`
**Error Message:**
```
{exact error output}
```

## Context

What was being attempted when this error occurred:
- User asked: "{user prompt}"
- Session was working on: {task}
- Occurred {N} times across {M} sessions

## Occurrences

| Timestamp | Session | Context |
|-----------|---------|---------|
| {timestamp} | {session_id} | {context} |

## Root Cause

{Analysis of why this keeps happening}

## Solution

**Prevention:**
```bash
# Code to prevent this error
```

**Alternative:**
{Alternative approach that avoids the error}

**Workaround:**
{If solution not yet found, temporary workaround}

## Status

- [x] Pattern identified (2+ occurrences)
- [x] Root cause understood
- [ ] Solution applied successfully
- [ ] No recurrence after solution

## Related

- [[Related Error Pattern]]
- [[Prevention Best Practices]]
```

**Error-Solution Property Guidelines:**
- **error_type**: Category from error-log.jsonl (bash_exit_1, io_error, etc.)
- **signature**: Unique identifier = error_type + context hash
- **status**: `unresolved` (no fix yet), `resolved` (fix applied), `workaround` (temp solution)
- **occurrences**: Count from error-log.jsonl (threshold: 2+)
- **first_seen/last_seen**: ISO timestamps from error log

**Error-Solution Categories:**
- `Bash-Errors/` - Command execution failures
- `Read-Errors/` - File reading issues
- `MCP-Errors/` - MCP tool call failures
- `Hook-Errors/` - gate-enforcer.py errors
- `Git-Errors/` - Git operation failures

**Workflow Pattern Properties (Additional v3.0):**

For notes detected as custom workflows by scout, add `workflow_metadata` block:

```yaml
---
# ... standard properties above ...
type: pattern
tags: [patterns, {software-tag}]

# WORKFLOW METADATA BLOCK (for custom workflows)
workflow_metadata:
  is_workflow: true
  workflow_type: custom_report | data_pipeline | multi_step_task
  complexity: simple | medium | complex
  complexity_score: N  # Points from classifier

  # Execution tracking
  first_executed: YYYY-MM-DDTHH:MM:SSZ
  last_executed: YYYY-MM-DDTHH:MM:SSZ
  execution_count: 1
  automation_threshold: 2 | 3 | 5  # Variable by complexity
  automated: false
  automated_skill_path: null  # Set when skill created

  # Parameters (for single workflow with variables)
  parameters:
    - name: quarter
      type: string
      required: true
      default: null
      description: "Q1, Q2, Q3, Q4"

  # Tool sequence
  tools_used:
    - mcp__crm__crm_tool
    - mcp__crm__list_deals

  # Data sources (unique)
  data_sources:
    - crm

  # Output specification
  output:
    format: markdown | json | csv | excel
    recipients: ["you@example.com"]
    delivery_method: email | file | console

  # Suggestion tracking
  suggestion_count: 0
  last_suggested: null
  suggestion_accepted: 0
  suggestion_dismissed: 0
---
```

**Workflow Metadata Property Guidelines:**
- **workflow_type**: `custom_report` (data query + formatting), `data_pipeline` (ETL), `multi_step_task` (complex sequence)
- **complexity**: Determined by `skills/meta/workflow-complexity-classifier.md`
- **automation_threshold**: Simple=2, Medium=3, Complex=5
- **parameters**: Extracted from conversation context (quarter, year, date range, etc.)
- **tools_used**: List of MCP tool names in execution order
- **data_sources**: Unique sources (crm, ticketing, supabase, etc.)

**Workflow Catalog Update (MANDATORY for workflow patterns):**

After writing a workflow pattern note, update the workflow catalog:

```python
def update_workflow_catalog(workflow_note_path, workflow_metadata):
    """
    Update workflow-catalog.json with new or modified workflow entry.

    Args:
        workflow_note_path: Path to the pattern note (relative to vault)
        workflow_metadata: Dict from frontmatter workflow_metadata block

    Called by: Memory consolidation when writing workflow pattern notes
    """
    catalog_path = ".claude/session/workflow-catalog.json"

    # Read existing catalog
    try:
        with open(catalog_path, 'r') as f:
            catalog = json.load(f)
    except FileNotFoundError:
        catalog = {"version": "1.0", "total_workflows": 0, "workflows": []}

    # Generate workflow ID from note path
    workflow_id = os.path.basename(workflow_note_path).replace('.md', '').lower().replace(' ', '-')

    # Extract context keywords from note title and parameters
    title = extract_title_from_note(workflow_note_path)
    context_keywords = extract_keywords(title)
    for param in workflow_metadata.get("parameters", []):
        context_keywords.append(param.get("name", ""))

    # Build catalog entry
    entry = {
        "id": workflow_id,
        "note_path": workflow_note_path,
        "title": title,
        "complexity": workflow_metadata.get("complexity", "simple"),
        "execution_count": workflow_metadata.get("execution_count", 1),
        "last_executed": workflow_metadata.get("last_executed"),
        "automation_threshold": workflow_metadata.get("automation_threshold", 3),
        "automated": workflow_metadata.get("automated", False),
        "automated_skill_path": workflow_metadata.get("automated_skill_path"),
        "tags": workflow_metadata.get("tags", []),
        "parameters": [p.get("name") for p in workflow_metadata.get("parameters", [])],
        "context_keywords": context_keywords,
        "suggested_this_session": False
    }

    # Check if workflow already exists (update vs. insert)
    existing_idx = None
    for idx, w in enumerate(catalog["workflows"]):
        if w["id"] == workflow_id:
            existing_idx = idx
            break

    if existing_idx is not None:
        # Update existing entry
        catalog["workflows"][existing_idx] = entry
    else:
        # Insert new entry
        catalog["workflows"].append(entry)
        catalog["total_workflows"] += 1

    # Update timestamp
    catalog["last_updated"] = datetime.utcnow().isoformat() + "Z"

    # Write catalog
    with open(catalog_path, 'w') as f:
        json.dump(catalog, f, indent=2)
```

### 6. Update Memory Index (v2.0) AND INCREMENT COUNTER (v2.7)

**After writing each note, update the index:**

```python
def rebuild_index_from_vault():
    """
    Rebuild memory-index.json from scratch by scanning vault.

    Used when index is corrupted or missing.
    Returns new index structure.
    """
    vault_path = "~/Projects\\memory\\"
    index = {
        "version": "2.0",
        "total_notes": 0,
        "last_updated": datetime.utcnow().isoformat() + "Z",
        "notes": []
    }

    # Scan vault for all .md files
    import os
    for root, dirs, files in os.walk(vault_path):
        for file in files:
            if file.endswith(".md"):
                file_path = os.path.join(root, file)
                try:
                    content = read_file(file_path)
                    frontmatter = extract_frontmatter(content)

                    index["notes"].append({
                        "path": file_path,
                        "title": extract_title(content),
                        "created": frontmatter.get("created", ""),
                        "modified": frontmatter.get("modified", ""),
                        "project": frontmatter.get("project", ""),
                        "domain": frontmatter.get("domain", ""),
                        "type": frontmatter.get("type", ""),
                        "tags": frontmatter.get("tags", []),
                        "keywords": extract_keywords(content),
                        "wikilinks": extract_wikilinks(content),
                        "char_count": len(content)
                    })
                except Exception as e:
                    # Skip corrupted files
                    continue

    index["total_notes"] = len(index["notes"])
    return index

# Read current index with error handling
try:
    index = read_json("session/memory-index.json")
except (FileNotFoundError, json.JSONDecodeError) as e:
    # Index missing or corrupted - rebuild from vault
    print(f"[MEMORY INDEX] Corrupted or missing - rebuilding from vault")
    index = rebuild_index_from_vault()
    write_json("session/memory-index.json", index)

# Add new note metadata (extracted from frontmatter)
for note_path in notes_written:
    content = read_file(note_path)
    frontmatter = extract_frontmatter(content)  # Parse YAML frontmatter

    index["notes"].append({
        "path": note_path,
        "title": extract_title(content),  # From # heading
        "created": frontmatter["created"],  # From frontmatter (REQUIRED)
        "modified": frontmatter["modified"],  # From frontmatter (REQUIRED)
        "project": frontmatter["project"],  # From frontmatter (REQUIRED)
        "domain": frontmatter["domain"],  # From frontmatter (REQUIRED)
        "type": frontmatter["type"],  # From frontmatter (REQUIRED)
        "tags": frontmatter["tags"],  # From frontmatter (REQUIRED)
        "keywords": extract_keywords(content),  # Generated from content
        "wikilinks": extract_wikilinks(content),  # [[links]] in content
        "char_count": len(content)
    })

# Update index metadata
index["total_notes"] += len(notes_written)
index["last_updated"] = now()

# Write updated index
write_json("session/memory-index.json", index)

# INCREMENT COUNTER (v2.7 - CRITICAL FIX)
# MUST happen AFTER writing notes, BEFORE updating state
current_total = state.get("memory_system", {}).get("notes_created_this_session", 0)
notes_written_count = len(notes_written)
if "memory_system" not in state:
    state["memory_system"] = {}
state["memory_system"]["notes_created_this_session"] = current_total + notes_written_count

# PERSIST state.json atomically (includes counter update)
write_json("session/state.json", state)
```

**CRITICAL:** Index metadata MUST come from frontmatter, not inference. If frontmatter is missing or incomplete, the note is invalid and must be fixed before adding to index.

**Why this matters:**
- Recall v2.0 depends on the index being up-to-date
- Without index update, new notes won't be found by recall
- Index updates are fast (append-only operation)
- **Counter tracking (v2.7):** Prevents losing count across consolidations by immediately incrementing after each write

### 6.5. Process Deadline Notes and Create Calendar Events (NEW v2.8)

**AUTOMATIC CALENDAR CREATION:** After writing notes, scan for deadline fields and create calendar reminders.

**Integration:**
```python
# After writing notes and updating index
if notes_written:
    # Load deadline automation skill
    from deadline_calendar_automation import process_deadline_notes

    # Load calendar MCP tool (MANDATORY FIRST)
    MCPSearch(query="select:mcp__email-primary__calendar_createEvent")

    # Create calendar events for deadline notes
    events_created = process_deadline_notes(notes_written, state)

    if events_created > 0:
        print(f"[DEADLINE] Created {events_created} calendar events")
```

**See:** `skills/meta/deadline-calendar-automation.md` for complete implementation

**Why This Matters:**
- User relies on calendar for deadline visibility, not just memory notes
- Automatic calendar creation removes manual step
- Prevents missed deadlines from forgotten calendar entries
- Deadline → Calendar should be automatic (system knows this pattern)

### 6.6. Generate Session Note (If Archive Trigger Detected - NEW Phase 4)

**Trigger detection:**
- User said "done", "session reset", "archive session", or "we're done"
- Archive event detected in LeRoy Swarm (SESSION_ARCHIVE IPC call)
- Session explicitly marked for archival
- State flag: `state["session"]["archive_triggered"] == true`

**If triggered, execute session note generation:**

#### 1. Extract session metadata

Load from archived sessions index (LeRoy Swarm or Desktop Claude):

```python
# Check for LeRoy Swarm archive
leroy_archive = Path(os.environ.get('APPDATA', '')) / "leroy-swarm" / "archived-sessions.json"
desktop_sessions = Path.home() / ".claude" / "session" / "sessions-index.json"

session_data = None

if leroy_archive.exists():
    with open(leroy_archive) as f:
        archive = json.load(f)
        # Get current session
        current_id = state.get('session', {}).get('session_id')
        for session in archive.get('sessions', []):
            if session['sessionId'] == current_id:
                session_data = {
                    'id': session['sessionId'],
                    'name': session['sessionName'],
                    'cwd': session.get('cwd', ''),
                    'created': session['createdAt'],
                    'lastActive': session['lastActiveAt'],
                    'tokens': session.get('tokenCount', 0),
                    'summary': session.get('summary', ''),
                    'transcript': session.get('transcriptPath', ''),
                    'archived': session.get('archivedAt', datetime.now().isoformat())
                }
                break

if not session_data and desktop_sessions.exists():
    # Fallback to desktop sessions
    with open(desktop_sessions) as f:
        sessions = json.load(f)
        for session in sessions:
            if session['sessionId'] == current_id:
                session_data = {
                    'id': session['sessionId'],
                    'name': session.get('firstPrompt', '').split('\n')[0][:100],
                    'cwd': '',
                    'created': session['created'],
                    'lastActive': session['created'],
                    'tokens': 0,
                    'summary': session.get('summary', ''),
                    'transcript': session.get('fullPath', ''),
                    'archived': datetime.now().isoformat()
                }
                break
```

**Required fields:** `sessionId`, `name`, `cwd`, `createdAt`, `lastActiveAt`, `tokenCount`, `summary`, `transcriptPath`

#### 2. Detect project context

Analyze cwd path and consolidated notes for project:

```python
def detect_project(session_data, notes_written):
    """Detect project from session metadata and notes."""
    cwd = session_data.get('cwd', '').lower()
    name = session_data.get('name', '').lower()
    summary = session_data.get('summary', '').lower()

    # Check cwd path first
    if 'leroy' in cwd or 'leroy-swarm' in cwd:
        return 'LeRoy'
    if 'product' in cwd:
        return 'your product'
    if 'exampleclient' in cwd:
        return 'ExampleClient'
    if 'exampleclient' in cwd:
        return 'ExampleClient'
    if 'partner' in cwd:
        return 'your organization'
    if 'exampleclient' in cwd:
        return 'ExampleClient'

    # Check name/summary
    text = f"{name} {summary}"
    if 'leroy' in text:
        return 'LeRoy'
    if 'product' in text or 'bim' in text:
        return 'your product'
    if 'exampleclient' in text:
        return 'ExampleClient'
    if 'exampleclient' in text:
        return 'ExampleClient'
    if 'partner' in text:
        return 'your organization'
    if 'exampleclient' in text:
        return 'ExampleClient'

    # Check note tags
    for note_path in notes_written:
        with open(note_path, 'r', encoding='utf-8') as f:
            content = f.read()
            # Extract tags from frontmatter
            if 'tags:' in content:
                tags_line = [line for line in content.split('\n') if 'tags:' in line]
                if tags_line:
                    tags = tags_line[0].lower()
                    if 'leroy' in tags:
                        return 'LeRoy'
                    if 'product' in tags or 'bim' in tags:
                        return 'your product'
                    if 'exampleclient' in tags:
                        return 'ExampleClient'
                    if 'exampleclient' in tags:
                        return 'ExampleClient'

    # Default to Meta
    return 'Meta'
```

#### 3. Generate wikilinks from consolidated notes

Scan consolidated notes created this session:

```python
def extract_consolidated_note_links(notes_written):
    """Extract wikilinks from recently consolidated notes."""
    links = {
        'decisions': [],
        'patterns': [],
        'skills': []
    }

    for note_path in notes_written:
        relative_path = note_path.replace('~/.claude\\memory\\', '')

        if 'Decisions/' in relative_path:
            filename = Path(note_path).stem
            links['decisions'].append(f"[[memory/Decisions/{filename}.md]]")
        elif 'Patterns/' in relative_path:
            filename = Path(note_path).stem
            links['patterns'].append(f"[[memory/Patterns/{filename}.md]]")
        elif 'Skills-Learned/' in relative_path:
            filename = Path(note_path).stem
            links['skills'].append(f"[[memory/Skills-Learned/{filename}.md]]")

    return links
```

#### 4. Create session note file

Path: `memory/Projects/{Project}/Sessions/{YYYY-MM-DD}-{slug}.md`

```python
def create_session_note(session_data, project, note_links):
    """Generate session note with wikilinks."""
    from datetime import datetime
    import re

    # Calculate date and slug
    created_dt = datetime.fromisoformat(session_data['created'].replace('Z', '+00:00'))
    date = created_dt.strftime('%Y-%m-%d')

    # Create slug from session name
    name = session_data.get('name') or session_data.get('summary') or session_data['id'][:8]
    slug = re.sub(r'[^\w\s-]', '', name.lower())
    slug = re.sub(r'[\s_-]+', '-', slug)
    slug = slug.strip('-')[:50]

    filename = f"{date}-{slug}.md"

    # Calculate duration
    start = datetime.fromisoformat(session_data['created'].replace('Z', '+00:00'))
    end = datetime.fromisoformat(session_data['lastActive'].replace('Z', '+00:00'))
    delta = end - start
    hours = delta.seconds // 3600
    minutes = (delta.seconds % 3600) // 60
    duration = f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"

    # Build wikilinks sections
    decision_links = '\n'.join([f"- {link}" for link in note_links['decisions']])
    pattern_links = '\n'.join([f"- {link}" for link in note_links['patterns']])
    skill_links = '\n'.join([f"- {link}" for link in note_links['skills']])

    # Generate content
    content = f"""---
date: {date}
type: session
tags: [session, {project.lower()}, archived]
project: {project}
session_id: {session_data['id']}
duration: {duration}
token_count: {session_data.get('tokens', 0)}
status: completed
summary: {session_data.get('summary') or 'Session archived'}
---

# Session: {name}

## Context
{session_data.get('summary') or 'No summary provided'}

## Work Completed
{session_data.get('summary') or 'See session transcript for details'}

## Decisions Made
{decision_links or '- (No decisions consolidated this session)'}

## Patterns Applied
{pattern_links or '- (No patterns consolidated this session)'}

## Skills Learned
{skill_links or '- (No skills consolidated this session)'}

## Related Sessions
(Link to prior/next sessions manually if needed)

## Project Hub
[[memory/Projects/{project}/index.md|{project}]]

---
*Session auto-archived: {datetime.now().strftime('%Y-%m-%d %H:%M')}*
"""

    # Write session note
    session_path = Path.home() / ".claude" / "memory" / "Projects" / project / "Sessions" / filename
    session_path.parent.mkdir(parents=True, exist_ok=True)

    with open(session_path, 'w', encoding='utf-8') as f:
        f.write(content)

    return session_path, filename, name
```

#### 5. Update project index

Add session link to project hub:

```python
def update_project_index(project, session_filename, session_name, summary):
    """Update project index with session link."""
    index_path = Path.home() / ".claude" / "memory" / "Projects" / project / "index.md"

    # Create basic index if doesn't exist
    if not index_path.exists():
        index_path.parent.mkdir(parents=True, exist_ok=True)
        index_path.write_text(f"# {project}\n\n## Sessions\n\n", encoding='utf-8')

    content = index_path.read_text(encoding='utf-8')

    # Ensure ## Sessions section exists
    if '## Sessions' not in content:
        content += '\n## Sessions\n\n'

    # Create session link
    session_link = f"- [[{session_filename.replace('.md', '')}|{session_name}]] - {summary or 'No summary'}"

    # Insert after ## Sessions heading
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if line.strip() == '## Sessions':
            # Insert after heading + blank line
            lines.insert(i + 2, session_link)
            break

    # Write updated index
    index_path.write_text('\n'.join(lines), encoding='utf-8')
```

#### 6. Update sessions-index.json

Mark session as archived with memory note path:

```python
# Update session index with memory note path
if desktop_sessions.exists():
    with open(desktop_sessions, 'r') as f:
        sessions = json.load(f)

    for session in sessions:
        if session['sessionId'] == current_id:
            session['archived'] = True
            session['memory_note_path'] = str(session_path.relative_to(Path.home() / ".claude"))
            break

    with open(desktop_sessions, 'w') as f:
        json.dump(sessions, f, indent=2)
```

#### 7. Validate wikilink graph

Run basic validation to detect orphaned nodes:

```python
def validate_session_note(session_path):
    """Validate session note has required wikilinks."""
    with open(session_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Check for project hub link (mandatory)
    has_project_link = '[[memory/Projects/' in content

    # Check for at least one decision/pattern/skill link
    has_content_links = (
        '[[memory/Decisions/' in content or
        '[[memory/Patterns/' in content or
        '[[memory/Skills-Learned/' in content
    )

    # Check frontmatter
    has_frontmatter = content.startswith('---')

    issues = []
    if not has_frontmatter:
        issues.append('Missing YAML frontmatter')
    if not has_project_link:
        issues.append('Missing project hub link (mandatory)')

    return len(issues) == 0, issues
```

#### 8. Output confirmation

```python
if session_note_created:
    print(f"""
📋 Session archived: {project} → {session_name}
   - Note: memory/Projects/{project}/Sessions/{filename}
   - Links: {len(decision_links)} decisions, {len(pattern_links)} patterns, {len(skill_links)} skills
   - Validation: {'✅ No issues' if validation_passed else '⚠️ ' + ', '.join(validation_issues)}
""")
```

**Validation checks:**
- Minimum 1 wikilink to project hub (mandatory)
- Minimum 1 decision/pattern/skill link (if any consolidated notes exist)
- No orphaned nodes (bidirectional validation)
- Valid YAML frontmatter
- Date format: YYYY-MM-DD

**Session Note Template (Reference):**

See `scripts/generate-session-note.py` for full template implementation.

**Why This Matters:**
- Archived sessions become permanent knowledge graph nodes
- Wikilinks connect sessions to decisions, patterns, and skills
- Project timeline automatically includes session history
- Obsidian graph shows session evolution over time
- No manual session note creation required

### 7. Update State

```json
{
  "memory_system": {
    "last_consolidation": "ISO timestamp",
    "notes_created": 3,
    "notes_created_this_session": 22,  // Running total - RESET on new session_id
    "last_session_id": "protocol-enforcement-v5",  // v2.7: Tracks last session
    "vault_path": "memory/",
    "last_email_sent": "ISO timestamp",
    "email_send_count": 5,
    "last_email_status": "success"
  },
  "deadline_calendar_events": {
    "Claude/Decisions/ExampleClient-Payment-Follow-up-Jan29.md": {
      "event_id": "700ms3jv729qglmno1g76fsktc",
      "event_link": "https://...",
      "created_at": "2026-01-26T18:11:17Z",
      "deadline_date": "2026-01-29",
      "reminder_date": "2026-01-29"
    }
  }
}
```

### 8. Update Checkpoint Timestamp (After Consolidation)

**Reset checkpoint timer and log metrics:**

```python
# Read current state and calculate interval
state = read_json("session/state.json")
last_checkpoint = state.get("scout", {}).get("last_checkpoint")
now = datetime.utcnow()
interval_minutes = calculate_interval(last_checkpoint, now) if last_checkpoint else 0

# Log checkpoint execution
log_event("checkpoint_executed", interval_minutes=interval_minutes, notes_created=len(notes_written))

# Reset checkpoint timer
state["scout"]["last_checkpoint"] = now.isoformat() + "Z"
state["enforcement"]["checkpoint_overdue"] = False
state["enforcement"]["checkpoint_overdue_minutes"] = 0
write_json("session/state.json", state)
```

### 9. Email Notification (Background - MANDATORY)

**ALWAYS send email report after consolidation - user tracks memories via email instead of conversation interruption.**

**Recipient:** `you@example.com`
**Sender:** `you@example.com` (user_google_email for MCP)

**EXECUTABLE ALGORITHM (v2.6 - Fully Implemented):**

```python
import os
import json
from datetime import datetime

def send_memory_notification_email(notes_written, state, index):
    """
    Send email notification after memory consolidation.

    Args:
        notes_written: List of note file paths that were written
        state: Current state.json data (dict)
        index: Current memory-index.json data (dict)

    Returns:
        bool: True if email sent successfully, False otherwise
    """
    # STEP 1: Load MCP tool (MANDATORY FIRST)
    # Must use MCPSearch to load: select:mcp__email-primary__send_gmail_message
    # This MUST happen BEFORE calling this function (in consolidation main flow)

    # STEP 2: Build email body
    email_lines = []
    email_lines.append(f"[MEMORY] {len(notes_written)} new memory notes added to LeRoy Memory:\n")

    folder_tags = set()
    software_tags = set()

    # Type to folder mapping
    folder_map = {
        "decision": "Decisions",
        "pattern": "Patterns",
        "preference": "Preferences",
        "skill-learned": "Skills-Learned",
        "sop": "SOPs",
        "project-note": "Projects",
        "error-solution": "Error-Solutions"
    }

    for note_path in notes_written:
        # Read note to extract metadata
        with open(note_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Extract frontmatter (YAML between --- markers)
        frontmatter = {}
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                import yaml
                frontmatter = yaml.safe_load(parts[1])

        # Extract title (first # heading)
        title = "Untitled"
        for line in content.split("\n"):
            if line.startswith("# "):
                title = line[2:].strip()
                break

        # Extract type and infer folder
        note_type = frontmatter.get("type", "unknown")
        folder = folder_map.get(note_type, "Unknown")

        # Extract tags
        tags = frontmatter.get("tags", [])
        if tags:
            folder_tags.add(tags[0])  # First tag is folder tag
            software_tags.update(tags[1:])  # Rest are software tags

        tags_str = ", ".join(tags) if tags else "none"

        # Extract context (first non-empty line after ## Context heading)
        context = ""
        lines = content.split("\n")
        in_context = False
        for line in lines:
            if line.strip() == "## Context":
                in_context = True
                continue
            if in_context and line.strip() and not line.startswith("#"):
                context = line.strip()
                break

        # Build note entry
        filename = os.path.basename(note_path)
        email_lines.append(f"• {note_type.replace('-', ' ').title()}: {title}")
        email_lines.append(f"  Path: Claude/{folder}/{filename}")
        email_lines.append(f"  Tags: [{tags_str}]")
        if context:
            # Truncate context if too long (max 150 chars)
            if len(context) > 150:
                context = context[:147] + "..."
            email_lines.append(f"  Context: {context}")
        email_lines.append("")

    # STEP 3: Add session summary
    email_lines.append("---")
    session_desc = (
        state.get("original_request", {}).get("interpreted_as") or
        state.get("current_task") or
        "Memory consolidation"
    )
    email_lines.append(f"Session: {session_desc}")
    email_lines.append(f"Total vault notes: {index.get('total_notes', 'unknown')}")

    now = datetime.utcnow()
    email_lines.append(f"Consolidation timestamp: {now.isoformat()}Z")
    email_lines.append("")

    # STEP 4: Add tag summary
    email_lines.append("Tag Summary:")
    if folder_tags:
        folder_list = ", ".join(sorted(folder_tags))
        email_lines.append(f"• Folder tags used: {folder_list}")
    if software_tags:
        software_list = ", ".join(sorted(software_tags))
        email_lines.append(f"• Software tags used: {software_list}")

    email_body = "\n".join(email_lines)

    # STEP 5: Format timestamp for subject
    timestamp = now.strftime("%Y-%m-%d %H:%M")
    subject = f"[MEMORY] {len(notes_written)} New Notes Added - {timestamp}"

    # STEP 6: Send email via MCP
    try:
        # Call mcp__email-primary__send_gmail_message
        # NOTE: MCPSearch MUST have been called before this function
        result = mcp__email-primary__send_gmail_message(
            user_google_email="you@example.com",
            to="you@example.com",
            subject=subject,
            body=email_body,
            body_format="plain"
        )

        # STEP 7: Update state on success
        if "memory_system" not in state:
            state["memory_system"] = {}

        state["memory_system"]["last_email_sent"] = now.isoformat() + "Z"
        state["memory_system"]["email_send_count"] = state.get("memory_system", {}).get("email_send_count", 0) + 1
        state["memory_system"]["last_email_status"] = "success"

        return True

    except Exception as e:
        # STEP 8: Update state on failure (doesn't block consolidation)
        if "memory_system" not in state:
            state["memory_system"] = {}

        state["memory_system"]["last_email_status"] = "failed"
        state["memory_system"]["last_email_error"] = str(e)

        print(f"[MEMORY] Email notification failed: {e}")
        print(f"[MEMORY] User can review vault directly")

        return False

# INTEGRATION POINT: Call after writing notes and updating index
if notes_written:
    # CRITICAL: Load MCP tool FIRST using MCPSearch
    # MCPSearch(query="select:mcp__email-primary__send_gmail_message")

    # Send notification email
    email_sent = send_memory_notification_email(notes_written, state, index)

    # Update state.json with email status (happens regardless of email success)
    with open(".claude/session/state.json", "w") as f:
        json.dump(state, f, indent=2)
```

**Email Format Example:**
```
Subject: [MEMORY] 3 New Notes Added - 2026-01-14 21:45

[MEMORY] 3 new memory notes added to LeRoy Memory:

• Decision: Protocol Enforcement v5.2
  Path: Claude/Decisions/Protocol-Enforcement-v5.2.md
  Tags: [decisions, enforcement, memory-system]
  Context: Implemented user-friendly priority system for enforcement queue

• Pattern: your CRM Query Optimization
  Path: Claude/Patterns/your CRM-Query-Optimization.md
  Tags: [patterns, ticketing]
  Context: Using OR conditions to consolidate multiple API calls

• Skill-Learned: Auto-Wikilink Generation
  Path: Claude/Skills-Learned/Auto-Wikilink-Generation.md
  Tags: [skills-learned, memory-system]
  Context: Automatic wikilink generation for Obsidian graph connectivity

---
Session: Implement v5.0 enforcement system
Total vault notes: 38
Consolidation timestamp: 2026-01-14T21:45:00Z

Tag Summary:
• Folder tags used: decisions, patterns, skills-learned
• Software tags used: ticketing, enforcement, memory-system
```

**When to send:**
- ALWAYS after consolidation completes (step 9 of workflow)
- Sent in background (doesn't block workflow)
- User can review memories asynchronously via email

**Why this works:**
- User gets notified without conversation disruption
- Email provides permanent record of what was learned
- Can review and reflect on memories at their own pace
- No "output to user" clutter in conversation

**State Update Tracking:**
Updates `state.json` with:
```json
{
  "memory_system": {
    "last_email_sent": "2026-01-18T12:00:00Z",
    "email_send_count": 5,
    "last_email_status": "success"
  }
}
```

## Output to User

**MINIMAL OUTPUT - Email sent instead:**
```
[MEMORY] {N} notes saved → emailed report to you@example.com
```

That's it. User gets full details via email, not in conversation.

### 10. Voice Pattern Relay (If Updated)

**PURPOSE:** Relay learned voice patterns from analysis script to USER.md for conversational style application.

**AUTOMATIC CHECK:** After consolidation completes, check if voice patterns need relay.

```python
def relay_voice_patterns_to_user_md():
    """
    Relay voice patterns from analysis script to USER.md.

    Checks: Does .claude/session/voice-user-md-snippet.txt exist?
    If YES: Update USER.md Communication Style section
    If NO: Skip (no new patterns this cycle)

    Called by: Memory consolidation (after writing notes)
    """
    snippet_path = Path.home() / ".claude" / "session" / "voice-user-md-snippet.txt"
    user_md_path = Path.home() / ".claude" / "USER.md"

    # Check if snippet exists (voice analysis ran)
    if not snippet_path.exists():
        print("[VOICE] No new patterns to relay (snippet not found)")
        return False

    # Read snippet content
    with open(snippet_path, 'r', encoding='utf-8') as f:
        new_snippet = f.read().strip()

    # Read current USER.md
    with open(user_md_path, 'r', encoding='utf-8') as f:
        user_md_content = f.read()

    # Find and replace Communication Style section
    # Pattern: ### Communication Style (Voice Learning) ... until next ### or end of file
    import re
    pattern = r'### Communication Style \(Voice Learning\).*?(?=\n### |\Z)'

    if re.search(pattern, user_md_content, re.DOTALL):
        # Replace existing section
        updated_content = re.sub(pattern, new_snippet, user_md_content, flags=re.DOTALL)
    else:
        # Section doesn't exist - find Communication Preferences and add after
        comm_pref_pattern = r'(### Communication Preferences\n.*?\n\n)'
        match = re.search(comm_pref_pattern, user_md_content, re.DOTALL)
        if match:
            insert_point = match.end()
            updated_content = (
                user_md_content[:insert_point] +
                new_snippet + "\n\n" +
                user_md_content[insert_point:]
            )
        else:
            print("[VOICE] Could not find insertion point in USER.md")
            return False

    # Write updated USER.md
    with open(user_md_path, 'w', encoding='utf-8') as f:
        f.write(updated_content)

    # Delete snippet file (processed)
    snippet_path.unlink()

    # Extract version from snippet for logging
    version_match = re.search(r'\(v(\d+)', new_snippet)
    version = version_match.group(1) if version_match else "?"

    print(f"[VOICE] USER.md updated with voice patterns v{version}")
    return True

# INTEGRATION POINT: Call after note writing, before metrics flush
if notes_written:
    relay_voice_patterns_to_user_md()
```

**WHY THIS MATTERS:**
- Voice patterns learned from corpus → Applied to ALL communication
- USER.md loaded at session start → Claude's conversational style adapts
- Daily analysis → Daily relay → Progressive voice matching
- the user hears his own voice coming back in every conversation

**OUTPUT:**
```
[VOICE] USER.md updated with voice patterns v1
```
or
```
[VOICE] No new patterns to relay (snippet not found)
```

### 11. Flush Metrics (FINAL STEP - MANDATORY)

**CRITICAL:** Flush metrics buffer to disk before consolidation completes.

```python
# After all processing complete (email sent, state updated)
# FLUSH metrics to ensure all events persisted (v2.5: with error handling)
try:
    flush_metrics()
except Exception as e:
    # Log error but don't fail consolidation
    # Metrics loss is acceptable - consolidation success is priority
    timestamp = datetime.utcnow().isoformat() + "Z"
    error_log = f"{timestamp} | METRICS_FLUSH_FAILED | {str(e)}\n"
    try:
        with open("session/metrics-errors.log", "a") as f:
            f.write(error_log)
    except IOError:
        # Even logging failed - print and continue
        print(f"[WARNING] Metrics flush failed: {e}")
    # Continue - consolidation is complete, metrics are secondary
```

**Why this is mandatory:**
- Metrics are buffered in memory (default: 100 events)
- If consolidation completes without flush, events may be lost
- Flush happens in <5ms (non-blocking)
- MUST be last operation before function returns

**Error Handling (v2.5):**
- Flush failures are logged but do NOT fail consolidation
- Error logged to `session/metrics-errors.log` for debugging
- Consolidation success takes priority over metrics collection
- Prevents edge case where disk full/permission error kills entire workflow

---

### 11.5. Restore Working Memory (Phase 4 - AFTER Compaction)

**PURPOSE:** Restore working memory from snapshot AFTER consolidation completes. Ensures seamless context continuation.

**WHEN:** After Step 11 (Flush Metrics) completes. This is the LAST step before consolidation returns.

**CRITICAL:** Without this step, compaction would clear working memory and context would be lost. Phase 4 restoration makes "I forgot" impossible even after compaction.

**Restoration Process:**

```python
import shutil
from pathlib import Path

# Working memory paths
WORKING_MEMORY_DIR = Path(".claude/session/working-memory")
SNAPSHOT_DIR = Path(".claude/session/working-memory-snapshot")

def restore_working_memory():
    """Restore working memory from snapshot after compaction."""

    if not SNAPSHOT_DIR.exists():
        print("[INFO] No working memory snapshot to restore")
        return

    if not WORKING_MEMORY_DIR.exists():
        WORKING_MEMORY_DIR.mkdir(parents=True, exist_ok=True)

    # Restore all 7 working memory files from snapshot
    files_to_restore = [
        "index.md",
        "active-clients.md",
        "active-projects.md",
        "active-tasks.md",
        "context-threads.md",
        "pending-actions.md",
        "background-findings.md"
    ]

    restored_count = 0
    for filename in files_to_restore:
        source = SNAPSHOT_DIR / filename
        dest = WORKING_MEMORY_DIR / filename

        if source.exists():
            shutil.copy2(source, dest)
            restored_count += 1

    print(f"[OK] Working memory restored ({restored_count}/7 files)")

    # Clean up snapshot directory (no longer needed)
    shutil.rmtree(SNAPSHOT_DIR)
    print(f"[OK] Snapshot cleaned up")

# Execute restoration LAST (after metrics flush)
restore_working_memory()
```

**Result:**
- Working memory restored from `session/working-memory-snapshot/`
- All 7 files back in `session/working-memory/`
- Context seamlessly continues (active clients, projects, tasks preserved)
- Snapshot directory cleaned up

**Next Prompt Behavior:**
1. gate-enforcer.py runs (pre-prompt hook)
2. Loads `working-memory/index.md` (Position #0 injection)
3. Claude sees working memory WITH preserved context
4. Active clients/projects still visible
5. Pending actions still tracked
6. **Zero context loss despite compaction**

**Example Recovery Flow:**

```
BEFORE COMPACTION:
- Working memory shows: "Active client: ExampleClient Engineering"
- Current task: "Phase 2 implementation"
- Pending: "Follow up on payment"

DURING COMPACTION (Step 0.5):
- Snapshot created: working-memory-snapshot/ (7 files)
- context-anchor.md populated

CONSOLIDATION:
- Session context compacted to vault
- 3-5 notes created
- Memory index rebuilt

AFTER COMPACTION (Step 11.5):
- Working memory restored from snapshot
- All 7 files back in place
- Context preserved

NEXT PROMPT:
- gate-enforcer loads working memory
- Claude sees: "Active client: ExampleClient Engineering"
- Continues work seamlessly
- **User doesn't even notice compaction happened**
```

---

## PROJECT CONFIGURATION (v3.0 - UNIFIED MEMORY)

**NOTE:** As of v3.0, all projects share a unified memory vault. No blacklisting is applied.
The previous your organization-only restriction (v2.8) has been removed to support multi-project workflows.

**Supported Projects:**
- `partner` - your organization Security (your CRM, your catalog service, Android)
- `org` - your org / ExampleClient (your BIM tool, your product, BIM)
- `lms` - an LMS courses (LMS, education)
- `meta` - Claude system patterns and skills

**Supported Domains:**
- All domains are now supported in the unified vault
- Sharding separates notes by project for efficient loading

**Migration Note (2026-01-23):**
The blacklist was removed because your org/an LMS workflows are now active projects
requiring memory persistence. your product documentation and your BIM tool BIM knowledge
are critical for the your org consulting practice.

## What Gets Saved

| Type | Save When | Location |
|------|-----------|----------|
| **Decision** | Architectural choice made | `Decisions/` |
| **Pattern** | Repeatable workflow found | `Patterns/` |
| **Preference** | User style/comm learned | `Preferences/` |
| **Skill** | Successful workflow | `Skills-Learned/` |
| **SOP** | Standard Operating Procedure documented | `SOPs/{project}/` |
| **Project** | Project-specific learning | `Projects/{project}/` |

**All active projects (your organization, your org, an LMS, meta)**

## What Gets Ignored

- Trivial operations (single file reads, simple questions)
- Failed attempts (unless failure itself is learning)
- Duplicate knowledge (check existing notes first)
- Session housekeeping (cleanup, status checks)

## Error Handling

If Obsidian path doesn't exist:
1. Create missing directories
2. Log warning to state.json
3. Continue with consolidation

If note already exists:
1. Append to existing note under "## Update YYYY-MM-DD"
2. Don't create duplicate

## Integration Points

**Called By:**
- `routines/morning.md` → on session end detection
- `workflows/git/pr-workflow.md` → before commit
- `@agent-guardian` → during final review
- `@agent-scout` → when patterns detected

**Calls:**
- Obsidian filesystem (direct Write to vault)
- `mcp__email-primary__send_gmail_message` (email notifications)
- **MUST load MCP tool with MCPSearch before calling**

## Maintenance

Weekly background cleanup by `@agent-memory-organizer`:
- Archive old patterns (>90 days to `System/Archive/`)
- Consolidate duplicate learnings
- Enforce 10-folder-per-tier rule

## Index Management (v2.0)

**Critical:** Every consolidation MUST update the index. Without this:
- New notes won't be found by recall
- Index becomes stale
- Recall v2.0 breaks

**Index update is automatic:**
1. Write notes to vault (existing behavior)
2. Extract metadata from each note
3. Append to session/memory-index.json
4. Update total_notes and last_updated fields

**If index.json missing:**
1. Run `scripts/build-memory-index.py` to rebuild from scratch
2. Consolidation will fail gracefully if index missing
3. Warning logged to state.json

## Metrics Integration (v2.4)

**Purpose:** Track consolidation performance and tag validation quality.

**Events Logged:**

1. **tag_rejected** - When validation fails
   - Fields: `tags`, `error`, `note_title`
   - Purpose: Identify tag rule violations and tune whitelist

2. **memory_write** - When note successfully written
   - Fields: `tags`, `note_type`, `accepted=True`
   - Purpose: Track successful writes and tag distribution

3. **checkpoint_executed** - When consolidation completes
   - Fields: `interval_minutes`, `notes_created`
   - Purpose: Monitor checkpoint compliance (15-min rule)

**Data Storage:**
- Location: `.claude/session/metrics/events-YYYY-MM-DD.jsonl`
- Format: One JSON object per line
- Rotation: Daily files (automatic)

**Analysis Examples:**

```bash
# Check tag rejection rate
grep tag_rejected .claude/session/metrics/events-2026-01-16.jsonl | wc -l

# Check checkpoint intervals
grep checkpoint_executed .claude/session/metrics/events-2026-01-16.jsonl | jq .interval_minutes

# Check most rejected tags
grep tag_rejected .claude/session/metrics/events-2026-01-16.jsonl | jq .tags
```

**Why Metrics Matter:**
- Tag rejection trends → improve whitelist or validation rules
- Checkpoint intervals → ensure 15-min compliance
- Write counts → track memory system usage

---

*Auto-triggered skill | No user request needed | v2.8 (Voice Pattern Relay: USER.md integration for conversational style)*
