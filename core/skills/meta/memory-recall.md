---
user-invocable: false
context: fork
agent: general-purpose
---

# Memory Recall v5.2 - Working Memory Directed Queries

> **v5.2 NEW (Phase 5):** Working-memory-directed recall. Loads notes about ACTIVE clients/projects instead of random top 5. Uses working memory context to build priority tag queries and applies 2x relevance multipliers to active entity notes.
> **v5.1 FEATURES:** Hierarchy-aware scoring (active > superseded > archived). Status indicators in output.
> **v5.0 FEATURES:** Client note injection from prediction engine. Client notes marked [PRE-LOADED] in Tier 1.
> **v4.0 UPDATE:** Shards are now PRIMARY loading path (75% faster, 669KB saved per recall).
> **BREAKING CHANGE:** memory-index.json (889KB) exceeds Read limit → must use shards!
> **v3.0 FEATURES:** LRU cache (90%+ hit rate), tag intersection index (O(1)), pre-computed scores.
> **HOOK-ENFORCED:** Session start ALWAYS triggers auto-recall. No time gap checks.
> **INDEX-BASED:** Uses domain shards with fallback to full index.
> **METRICS-ENABLED:** Logs cache hit/miss, notes loaded, and recall reason.

## Purpose

Search Obsidian vault for relevant past learnings and load them into session context before taking action.

**v2.0 closes the memory recall gap:** Consolidation worked (writing notes), but recall never executed. This system makes recall automatic and bulletproof.

## Fixed Paths

| Purpose | Path |
|---------|------|
| Obsidian Vault | `~/.claude\memory\` |
| Session State | `.claude/session/state.json` |
| **Prediction State** | `.claude/session/prediction-state.json` (v5.0 - client notes) |
| Memory Index | `.claude/session/memory-index.json` |
| Session Cache | `.claude/session/memory-cache.json` |
| LRU Cache | `.claude/session/memory-cache-lru.json` |
| Domain Shards | `.claude/session/shards/{project}-shard.json` |
| Expansion State | `.claude/session/memory-expansion.md` |

## Auto-Trigger Mode (v2.1 - Enhanced Detection)

When `enforcement.must_recall_memory = true`, this skill executes automatically.

**Trigger Conditions:**
- Session start (ALWAYS - no time gap required), **OR**
- Major architect decision point
- Before entering plan mode
- Explicit user request ("remember...")

**Enforcement:**
- **Priority 0 (Blocking):** Substantial tasks - MUST complete before user request
- **Priority 2 (Background):** Trivial tasks - Runs in parallel with user request

**How it works:**
1. Hook detects recall trigger → sets `must_recall_memory = true`
2. Hook writes enforcement.todo with RECALL_MEMORY action
3. Claude reads enforcement.todo → executes this skill
4. Skill loads top 12 notes → outputs [MEMORY] block
5. Updates state.json `last_recall` timestamp

**CRITICAL CHECK (v2.1):**
Before executing any other action, this skill MUST check state.json:
```python
state = read_json("session/state.json")
enforcement = state.get("enforcement", {})

if enforcement.get("must_recall_memory", False):
    # MANDATORY: Execute recall NOW
    # DO NOT skip, DO NOT defer
    execute_recall()
```

## Smart Filtering Pipeline (7-Pass) - WORKING MEMORY DIRECTED v5.2

**v5.2 UPDATE (Phase 5):** Added Pass 0.5 for working-memory-directed recall. Loads notes about ACTIVE clients/projects instead of random top 5.

**v2.3 UPDATE:** Added Pass 0 for session isolation to prevent cross-session memory contamination.

v2.1 uses **tag-based filtering** as the PRIMARY filter mechanism. Tags follow strict rules (see memory-consolidation.md):
- **Tag 1:** Folder tag (decisions, patterns, preferences, skills-learned, projects)
- **Tags 2-4:** Software/integration tags (ticketing, crm, catalog, bim, etc.)

### Pre-Pass: MCP CROSS-SESSION RECALL (v5.3 — memory integration)
**Pull persistent memories that survive session resets and the vault's Pass 0 session filter**

> **Why this exists:** Pass 0 (below) intentionally excludes vault notes from other sessions.
> `memory` MCP fills this gap — it has NO session filter and persists learnings across ALL sessions.
> This is the layer that makes me remember things the user told me 3 sessions ago.

**When to run:** Every recall invocation — BEFORE Pass 0. Takes ~10ms (local SQLite).

```python
# Extract keywords from current prompt/active project
topic_keywords = " ".join(extract_topic_keywords(current_prompt))  # e.g. "your product your BIM tool build"

# Cross-session keyword recall
mcp_memories = mcp__memory__recall(query=topic_keywords, limit=8)

# If starting a new task/project — use reflect for broader surface
if has_active_project:
    mcp_context = mcp__memory__reflect(topic=active_project_name)
```

**Inject results into session context BEFORE vault results. Label with `[MCP]` prefix.**

**Output format (internal):**
```
[MCP-MEMORY] '{query}' — 2 cross-session memories
  ID:5 PREFERENCE imp:9 — the user prefers bulletproof direct solutions. Hates fluff.
  ID:7 FACT imp:8 — your product old-style .csproj needs Compile Include for every new .cs file.
```

**No results → continue to Pass 0 normally. Never block on MCP failure.**

---

### Pass 0: SESSION FILTER (NEW v2.3 - CRITICAL FIX)
**Filter by current session ONLY - prevents memory bleed between parallel chats**

Expected reduction: ALL notes → Current session notes only

**PROBLEM SOLVED:**
Before v2.3, all memories from ALL parallel chat sessions mixed together. This caused:
- Building features requested in other sessions
- Applying decisions from wrong context
- Confusing parallel work streams

**Solution (v4.3 - VERIFIED IMPLEMENTATION):**
```python
# Read current session ID
state = read_json("session/state.json")
current_session_id = state.get("session_id")

# BLOCKING VALIDATION: session_id must exist
if not current_session_id:
    raise ValueError("BLOCKING ERROR: session_id missing from state.json")

# ONLY load notes from THIS session
session_notes = []
for note in index["notes"]:
    note_session_id = note.get("session_id")

    # Skip notes without session_id (legacy notes)
    if not note_session_id:
        continue

    # Only load notes from THIS session
    if note_session_id == current_session_id:
        session_notes.append(note)

# Continue with remaining passes on session_notes ONLY
# If session_notes is empty, that's OK (new session, no memories yet)
```

**Validation Rules (ENFORCED):**
- ✅ If session_id missing from state.json → FAIL (blocking error raised)
- ✅ If note missing session_id → Skip (legacy note, exclude from results)
- ✅ If 0 matches → OK (new session, no memories yet)

**Override (Advanced):**
To explicitly load cross-session memories:
- User says "check all sessions" or "load from other chats"
- Skip Pass 0 and load from all sessions

---

### Pass 0.25: DECAY FILTER (NEW v6.1 — Decay-A)
**Drop inferred memories whose effective_confidence has decayed below the floor**

Expected reduction: small (most legacy notes have `inferred:false` → no decay applied)

**Why this exists:**
Inferred facts (things Claude guessed but the user never explicitly confirmed) shouldn't live forever. If Claude inferred "the user prefers terse summaries" 6 months ago and never re-verified, that fact is no longer load-bearing — it should age out so re-confirmation is required. Asserted facts (things the user stated outright) never decay.

**Floor:** `effective_confidence < 0.3` → drop unless query is `--include-stale` mode.

**How it runs (cheap, post-Pass-0):**
```python
# effective_confidence is pre-computed by build-memory-index.py at index time
# Reading from index.json — no math at recall time
filtered = [
    n for n in candidates
    if n.get("effective_confidence", 1.0) >= 0.3
       or include_stale_mode
]
```

**Decay formula** (computed at index time, stored on each note):
- Asserted (`inferred: false`) → effective_confidence = raw confidence (no decay).
- Inferred (`inferred: true`) → `effective_confidence = confidence * 0.5^(days_since_verified / half_life_days)`.
- Half-life is per-type (see `memory-consolidation.md` HALF_LIFE table) or per-note via `half_life_days` frontmatter override.
- Types with `half_life: None` (decision, warning) never decay even if marked inferred.

**Backward compatibility:**
Legacy notes (479 existing) lack the decay frontmatter fields → `inferred` defaults to `false`, `confidence` defaults to `1.0`, no decay applied. Behavior unchanged for existing recall.

**Override:**
- User says "include stale" / "show forgotten" / "all memories" → skip filter
- Cross-session reflect queries → skip filter (broader surface intentional)

**Output marker:** Notes with `effective_confidence < 0.5` (still passing floor) get `[FADING]` tag in recall output so Claude knows to re-verify on next user contact.

---

### Pass 0.5: WORKING MEMORY CONTEXT (NEW v5.2 - PHASE 5)
**Extract active entities from working memory to direct vault queries**

Expected effect: Load notes about ACTIVE clients/projects instead of random top 5

**PROBLEM SOLVED:**
Before v5.2, memory recall loaded "top 5 most relevant notes" by generic relevance scoring. This often missed notes about the actual work being done:
- Working on ExampleClient project, but recall loads generic your BIM tool patterns
- Active your product task, but recall loads unrelated your CRM notes
- Pending action for ExampleClient follow-up, but recall doesn't know to load ExampleClient context

**Solution (v5.2 - Phase 5 Implementation):**
```python
import os

WORKING_MEMORY_INDEX = Path(".claude/session/working-memory/index.md")

def extract_working_memory_context():
    """
    Read working memory and extract active entities for directed recall.

    Returns:
        dict with active_clients, active_projects, active_tasks, pending_actions
    """
    if not WORKING_MEMORY_INDEX.exists():
        # No working memory yet (bootstrap or fresh session)
        return {
            "active_clients": [],
            "active_projects": [],
            "active_tasks": [],
            "pending_actions": []
        }

    # Read working memory index
    with open(WORKING_MEMORY_INDEX, 'r', encoding='utf-8') as f:
        wm_content = f.read()

    # Extract active entities using regex patterns
    context = {
        "active_clients": [],
        "active_projects": [],
        "active_tasks": [],
        "pending_actions": []
    }

    # Extract active client from Quick Context section
    # Pattern: **Active client**: ExampleClient Engineering (DC-2 project)
    client_match = re.search(r'\*\*Active client\*\*:\s*([^\n(]+)', wm_content)
    if client_match:
        client = client_match.group(1).strip()
        if client.lower() not in ['none', 'none currently']:
            context["active_clients"].append(client)

    # Extract current task from Quick Context section
    # Pattern: **Current task**: your product v1.1.0.0 build preparation
    task_match = re.search(r'\*\*Current task\*\*:\s*([^\n]+)', wm_content)
    if task_match:
        task = task_match.group(1).strip()
        if task.lower() not in ['none', 'no task active', 'no task']:
            context["active_tasks"].append(task)

    # Extract pending action from Quick Context section
    # Pattern: **Pending action**: Follow up on ExampleClient payment
    action_match = re.search(r'\*\*Pending action\*\*:\s*([^\n]+)', wm_content)
    if action_match:
        action = action_match.group(1).strip()
        if action.lower() not in ['none', 'none currently']:
            context["pending_actions"].append(action)

    # Extract projects from Active Threads section
    # Pattern: - [ExampleClient DC-2](active-clients.md#exampleclient) - Phase 1 delivery
    thread_pattern = r'-\s*\[([^\]]+)\]\([^\)]+\)\s*-\s*([^\n]+)'
    thread_matches = re.findall(thread_pattern, wm_content)
    for thread_title, thread_desc in thread_matches:
        # Add project name to active_projects if not already there
        project_name = thread_title.strip()
        if project_name not in context["active_projects"]:
            context["active_projects"].append(project_name)

    return context


def build_directed_tag_queries(wm_context):
    """
    Build tag queries based on working memory entities.

    Args:
        wm_context: dict from extract_working_memory_context()

    Returns:
        list of tag patterns to prioritize
    """
    priority_tags = []

    # Map client names to potential tags
    client_tag_map = {
        "exampleclient": ["exampleclient", "exampleclient"],
        "product": ["product", "bim", "bim"],
        "exampleclient": ["exampleclient", "exampleclient"],
        "exampleclient": ["exampleclient"],
        "exampleclient": ["exampleclient"],
        # Add more mappings as needed
    }

    # Extract potential tags from active clients
    for client in wm_context["active_clients"]:
        client_lower = client.lower()
        for key, tags in client_tag_map.items():
            if key in client_lower:
                priority_tags.extend(tags)

    # Extract keywords from active tasks
    for task in wm_context["active_tasks"]:
        # Extract project names (e.g., "your product v1.1.0.0" → product)
        if "product" in task.lower():
            priority_tags.extend(["product", "bim"])
        if "crm" in task.lower():
            priority_tags.append("crm")
        if "ticketing" in task.lower():
            priority_tags.append("ticketing")
        if "catalog" in task.lower():
            priority_tags.append("catalog")

    # Remove duplicates and return
    return list(set(priority_tags))


# INTEGRATION: Call at start of recall process (after Pass 0)
wm_context = extract_working_memory_context()
priority_tags = build_directed_tag_queries(wm_context)

# Store in recall state for use in Pass 1 and Pass 5
recall_state = {
    "wm_context": wm_context,
    "priority_tags": priority_tags,
    "has_active_entities": len(wm_context["active_clients"]) > 0 or
                          len(wm_context["active_projects"]) > 0
}
```

**Output (internal - not shown to user):**
```python
{
    "wm_context": {
        "active_clients": ["ExampleClient Engineering"],
        "active_projects": ["ExampleClient DC-2", "your product Build"],
        "active_tasks": ["your product v1.1.0.0 build preparation"],
        "pending_actions": ["Follow up on ExampleClient payment"]
    },
    "priority_tags": ["exampleclient", "exampleclient", "product", "bim", "exampleclient"],
    "has_active_entities": True
}
```

**When to Skip:**
- Working memory doesn't exist (bootstrap or very fresh session)
- Working memory shows "No active client", "No task active" (idle state)
- In these cases, fall back to standard recall (generic top 5)

### Pass 1: TAG FILTER (PRIMARY + WORKING MEMORY DIRECTED v5.2)
**Match by strict tags first - fastest and most accurate**

**v5.2 Enhancement:** Prioritize tags from working memory BEFORE prompt-detected tags.

Expected reduction: 1000 → 50 notes (or directly to 10-15 if working memory has strong signal)

```python
# v5.2: START with working memory priority tags (Phase 5)
priority_tags = recall_state.get("priority_tags", [])

# THEN add tags detected from user prompt
prompt_tags = detect_software_tags(user_prompt)
# e.g., "help me with your CRM query" → ["ticketing"]

# COMBINE: Priority tags first, then prompt tags
all_tags = priority_tags + prompt_tags  # Order matters - priority first

# Filter notes that have ANY matching tag
matching_notes = []
note_scores = {}  # Track how many tags matched (for sorting)

for note in index["notes"]:
    note_tags = note["tags"]  # e.g., ["decisions", "ticketing", "crm"]
    software_tags = note_tags[1:]  # Skip folder tag

    # Count matching tags
    matches = [tag for tag in software_tags if tag in all_tags]

    if len(matches) > 0:
        matching_notes.append(note)
        note_scores[note["path"]] = {
            "tag_match_count": len(matches),
            "priority_tag_match": any(tag in priority_tags for tag in matches)
        }

# v5.2: BOOST notes that matched working memory priority tags
# These get 2x relevance multiplier in Pass 5
for note in matching_notes:
    score_data = note_scores.get(note["path"], {})
    note["_wm_priority_match"] = score_data.get("priority_tag_match", False)
    note["_wm_tag_count"] = score_data.get("tag_match_count", 0)
```

**Valid Software Tags (from memory-consolidation.md):**
- `ticketing` | `crm` | `catalog` | `bim` | `android`
- `git` | `netlify` | `playwright` | `supabase` | `gas`
- `python` | `memory-system` | `enforcement` | `leroy`

### Pass 1.5: VECTOR SIMILARITY (NEW v6.0 - SEMANTIC SEARCH)
**Boost notes by semantic similarity to user prompt**

**Adopted from:** claude-mem.ai's hybrid keyword+vector search pattern.

**Purpose:** Find conceptually related notes even without exact keyword matches.
- "authentication bugs" finds notes about "JWT token issues" or "login failures"
- "API rate limiting" finds notes about "pagination" and "throttling"

**Prerequisites:**
- `sentence-transformers` library installed
- Notes have embeddings in index (generated during consolidation)
- See `skills/meta/vector-embeddings.md` for setup

**Expected effect:** Semantic boost to relevance scores (doesn't filter, only boosts)

```python
import sys
sys.path.append(".claude/scripts")

try:
    from vector_embeddings import find_similar_notes, generate_embedding

    def pass_1_5_vector_similarity(notes, user_prompt, index, min_similarity=0.35):
        """
        Apply vector similarity boost to notes.

        Args:
            notes: List of notes from Pass 1 (tag filtered)
            user_prompt: Current user prompt/query
            index: Full memory index with embeddings
            min_similarity: Minimum threshold for boost

        Returns:
            Notes with _vector_similarity field added
        """
        # Find semantically similar notes from full index
        similar_results = find_similar_notes(
            query=user_prompt,
            index=index,
            top_k=30,  # Get more candidates
            min_similarity=min_similarity
        )

        # Build lookup: path -> similarity score
        similarity_map = {note["path"]: score for note, score in similar_results}

        # Apply boost to notes in our filtered set
        for note in notes:
            path = note["path"]
            similarity = similarity_map.get(path, 0.0)

            # Store for later scoring
            note["_vector_similarity"] = similarity

            # Notes with high semantic similarity get visibility boost
            if similarity >= 0.5:
                note["_semantic_match"] = True  # Flag for display

        return notes


    # INTEGRATION: Call after Pass 1 (tag filter), before Pass 2 (project filter)
    notes = pass_1_5_vector_similarity(matching_notes, user_prompt, index)

except ImportError:
    # Graceful fallback if sentence-transformers not installed
    # System continues with tag-only search
    print("[RECALL] Vector embeddings not available - using tag-only search")

    def pass_1_5_vector_similarity(notes, user_prompt, index, min_similarity=0.35):
        """Fallback: no-op when embeddings unavailable."""
        for note in notes:
            note["_vector_similarity"] = 0.0
        return notes
```

**Similarity Thresholds:**
| Similarity | Interpretation | Action |
|------------|----------------|--------|
| >= 0.7 | Very similar | Strong boost (2x multiplier) |
| 0.5 - 0.69 | Related | Moderate boost (1.5x) |
| 0.35 - 0.49 | Possibly related | Small boost (1.2x) |
| < 0.35 | Unrelated | No boost |

**Why This Pass:**
- Tag filtering is fast and precise but misses semantic relationships
- Vector search catches "same meaning, different words"
- Combining both gives best of both worlds
- Fallback to tag-only if embeddings unavailable

### Pass 2: Project Filter
**Match current project (your organization/your org/an LMS/meta)**

Expected reduction: 50 → 20 notes

```python
if note["project"] == current_project:
    pass_to_next_stage(note)
```

### Pass 3: Domain Filter (BACKUP)
**Only if tag filter returns <5 results**

Expected reduction: 20 → 15 notes

Domain detection from:
- Keywords in user prompt
- Current files being worked on
- Recent tool use (MCP servers)

```python
domains_in_prompt = extract_domains(user_prompt)
if note["domain"] in domains_in_prompt:
    pass_to_next_stage(note)
```

### Pass 4: Type Filter (Folder Tag)
**Match note type using FOLDER TAG from tags array**

Expected reduction: 15 → 10 notes

Type priority by task:
- **Planning task:** Load `decisions` + `patterns` tagged notes
- **Bug fix:** Load `patterns` + `skills-learned` tagged notes
- **Report generation:** Load `preferences` + `projects` tagged notes

```python
# Use folder tag (tags[0]) for type filtering
relevant_folder_tags = get_folder_tags_for_task(task_category)
if note["tags"][0] in relevant_folder_tags:
    pass_to_next_stage(note)
```

### Pass 5: Relevance Scoring (+ WORKING MEMORY + VECTOR SIMILARITY v6.0)
**Weighted formula combining tags, working memory, and semantic similarity**

**v6.0 Enhancement:** Adds vector similarity from Pass 1.5 to scoring formula.
**v5.2 Enhancement:** Applies working memory multipliers to boost notes about active entities.

Expected reduction: 10 → 5 notes (top ranked, combining all signals)

```python
# Base relevance score (UPDATED v6.0 - includes vector similarity)
base_score = (
    tag_match * 0.30 +         # Software tag match: 30% (reduced from 35%)
    project_match * 0.25 +     # Same project: 25% (reduced from 30%)
    vector_similarity * 0.20 + # Semantic similarity: 20% (NEW v6.0)
    domain_match * 0.10 +      # Same domain: 10% (reduced from 15%)
    type_relevance * 0.08 +    # Note type: 8% (reduced from 10%)
    recency * 0.07             # Recent notes: 7% (reduced from 10%)
)

# Get vector similarity from Pass 1.5 (default 0 if not available)
vector_similarity = note.get("_vector_similarity", 0.0)

# v6.0: Apply vector similarity boost
vector_boost = 1.0
if vector_similarity >= 0.7:
    vector_boost = 1.5  # Very similar = 50% boost
elif vector_similarity >= 0.5:
    vector_boost = 1.3  # Related = 30% boost
elif vector_similarity >= 0.35:
    vector_boost = 1.1  # Possibly related = 10% boost

# v5.2: Apply working memory multipliers
wm_multiplier = 1.0  # Default (no boost)

# Check if note matched working memory priority tags (from Pass 1)
if note.get("_wm_priority_match", False):
    # Note is about an active client/project from working memory
    wm_multiplier = 2.0  # 2x boost for active entity notes

# COMBINE ALL MULTIPLIERS
# Working memory × Vector similarity (multiplicative)
combined_multiplier = wm_multiplier * vector_boost

# Apply multipliers to base score
final_score = base_score * combined_multiplier

# Store all scores for debugging and display
note["base_score"] = base_score
note["wm_multiplier"] = wm_multiplier
note["vector_boost"] = vector_boost
note["vector_similarity"] = vector_similarity
note["combined_multiplier"] = combined_multiplier
note["relevance_score"] = final_score

# Sort by final score descending
ranked_notes = sorted(notes, key=lambda n: n["relevance_score"], reverse=True)
return ranked_notes[:12]  # Top 12 (combining all ranking signals)
```

**Multiplier Rules (v6.0 - Combined):**
| Signal | Condition | Multiplier |
|--------|-----------|------------|
| **Working Memory** | Active client/project match | 2.0x |
| **Vector Similarity** | >= 0.7 (very similar) | 1.5x |
| **Vector Similarity** | 0.5-0.69 (related) | 1.3x |
| **Vector Similarity** | 0.35-0.49 (possibly related) | 1.1x |
| **Combined** | WM match + High similarity | 2.0 × 1.5 = **3.0x** |

**Scoring Example (v6.0):**
```
Query: "authentication token issues"

Note A: "JWT Token Refresh Pattern"
  - tag_match: 0.0 (no direct tag match)
  - project_match: 1.0 (same project)
  - vector_similarity: 0.72 (very similar semantically)
  - base_score: 0.30*0.0 + 0.25*1.0 + 0.20*0.72 + ... = 0.52
  - vector_boost: 1.5x (>0.7)
  - final_score: 0.52 × 1.5 = **0.78**

Note B: "your CRM Authentication Setup"
  - tag_match: 0.5 (partial tag match)
  - project_match: 1.0 (same project)
  - vector_similarity: 0.45 (somewhat related)
  - base_score: 0.30*0.5 + 0.25*1.0 + 0.20*0.45 + ... = 0.55
  - vector_boost: 1.1x (0.35-0.49)
  - final_score: 0.55 × 1.1 = **0.61**

Result: Note A ranks higher despite no tag match (semantic wins)
```

**Why This Works (v6.0):**
- **Tags** provide fast, precise filtering
- **Vector similarity** catches "same meaning, different words"
- **Working memory** prioritizes active work context
- **Combined scoring** gives best of all worlds
- Graceful fallback: vector_similarity=0 if embeddings unavailable

### Pass 6: Hierarchy Status Adjustment (NEW v5.1)
**Apply status multiplier to prioritize active notes**

Expected effect: Active notes score 3-10x higher than superseded/archived

```python
def apply_hierarchy_multiplier(notes):
    """
    Adjust relevance scores based on hierarchy status.

    Args:
        notes: List of notes with relevance_score already computed

    Returns:
        List of notes with adjusted scores
    """
    status_multipliers = {
        "active": 1.0,      # No adjustment (default for notes without hierarchy)
        "superseded": 0.3,  # 30% of original score
        "archived": 0.1     # 10% of original score
    }

    for note in notes:
        # Default to active if no hierarchy metadata
        hierarchy = note.get("hierarchy", {})
        status = hierarchy.get("status", "active")

        # Apply multiplier
        multiplier = status_multipliers.get(status, 1.0)
        note["relevance_score"] *= multiplier

        # Add flag for output formatting
        note["_hierarchy_status"] = status
        note["_hierarchy_metadata"] = hierarchy

    # Re-sort by adjusted scores
    return sorted(notes, key=lambda n: n["relevance_score"], reverse=True)


# INTEGRATION POINT: Call after Pass 5
# After Pass 5 (original relevance scoring)
ranked_notes = score_relevance(notes, context)

# NEW Pass 6: Apply hierarchy multiplier
ranked_notes = apply_hierarchy_multiplier(ranked_notes)

# Continue with tiered loading
tier1 = ranked_notes[:5]
```

**Why This Works:**
- Notes without hierarchy default to `active` (backward compatible)
- Superseded notes can still surface if highly relevant
- Archived notes require 10x relevance to compete
- Evolution tracking preserved (old versions accessible)

**Scoring details:**
- **Tag match:** Count of matching software tags / total detected tags
- **Project match:** 1.0 if exact, 0.5 if related, 0 if different
- **Domain match:** 1.0 if exact, 0.3 if related, 0 if different
- **Type relevance:** Based on task category mapping (see above)
- **Recency:** `1.0 - (days_old / 90)` → newer notes score higher

---

### Pass 6.5: TYPED-EDGE WALK (NEW v6.1 — Edges-B)
**Demote superseded notes; surface contradictions; trace derivation chains**

Expected effect: superseded notes drop in rank, conflicting facts get flagged, Claude sees provenance.

**Why this exists (v6.1):**
After Edges-A (Phase A) wrote the typed graph, recall still ignored it. Pass 6.5 makes the graph load-bearing — recall now USES `supersedes` and `contradicts` edges to adjust ranking and surface conflicts to Claude in the [MEMORY] block.

**Inputs:** ranked candidates from Pass 6, typed graph from `session/memory-graph.json` (v2.0).

**Algorithm (1-hop only — cheap):**
```python
import json
from pathlib import Path

GRAPH_PATH = Path.home() / ".claude" / "session" / "memory-graph.json"

def edge_walk(candidates, top_n=20):
    """v6.1 Pass 6.5 — typed-edge ranking adjustments.

    For the top_n candidates, walk supersedes / contradicts / derived_from
    edges 1 hop and adjust scores + tags accordingly.
    """
    if not GRAPH_PATH.exists():
        return candidates

    graph = json.loads(GRAPH_PATH.read_text(encoding="utf-8"))
    edges = graph.get("edges", {})
    if not edges:
        return candidates

    # Build a fast path -> note map for the top_n
    head = candidates[:top_n]
    head_by_path = {n["path"]: n for n in head}
    candidate_paths = set(head_by_path.keys())

    # ---- supersedes: if A.supersedes -> B and both are candidates, demote B
    for path, note_edges in edges.items():
        if path not in candidate_paths:
            continue
        for target in note_edges.get("supersedes", []):
            # Resolve target wikilink to a candidate path
            target_paths = [p for p in candidate_paths if p.endswith(f"/{target}.md") or p.endswith(f"\\{target}.md")]
            for tp in target_paths:
                old_note = head_by_path[tp]
                old_note["relevance_score"] = old_note.get("relevance_score", 0) - 0.5
                old_note.setdefault("_edge_flags", []).append(f"[SUPERSEDED by {path.rsplit('/', 1)[-1]}]")

    # ---- contradicts: flag both sides if both are in candidate set
    for path, note_edges in edges.items():
        if path not in candidate_paths:
            continue
        for target in note_edges.get("contradicts", []):
            target_paths = [p for p in candidate_paths if p.endswith(f"/{target}.md") or p.endswith(f"\\{target}.md")]
            for tp in target_paths:
                head_by_path[path].setdefault("_edge_flags", []).append(f"[CONFLICT: see {tp.rsplit('/', 1)[-1]}]")
                head_by_path[tp].setdefault("_edge_flags", []).append(f"[CONFLICT: see {path.rsplit('/', 1)[-1]}]")

    # ---- derived_from: light score boost (+0.1) on the source if present in candidates
    #      (so users see provenance alongside derived notes)
    for path, note_edges in edges.items():
        if path not in candidate_paths:
            continue
        for target in note_edges.get("derived_from", []):
            target_paths = [p for p in candidate_paths if p.endswith(f"/{target}.md") or p.endswith(f"\\{target}.md")]
            for tp in target_paths:
                head_by_path[tp]["relevance_score"] = head_by_path[tp].get("relevance_score", 0) + 0.1

    # Re-sort the head; tail keeps original order
    new_head = sorted(head, key=lambda n: n.get("relevance_score", 0), reverse=True)
    return new_head + candidates[top_n:]
```

**Output marker handling:** when rendering the [MEMORY] block, append `_edge_flags` after the title:
- `[SUPERSEDED by Decision-v5.md]` — demoted; reader knows newer exists
- `[CONFLICT: see Other-Note.md]` — both sides surfaced; Claude must reconcile or escalate to user
- `[DERIVATION SOURCE]` — provenance hit (rendered if any candidate cites it via `derived_from`)

**Contradiction handling protocol:**
- If a `contradicts` pair both surface AND **either side has `criticality: high` or sits in a CRITICAL topic** (trading_bot, financial_data, contracts, dates_and_deadlines, medical, legal — see consolidation council vote Q1) → block silent recall: surface to user with explicit ask before proceeding.
- Otherwise: flag and continue. Claude must reconcile in its response.

**1-hop only. Why:**
- 2-hop traversal explodes cost (graph fan-out)
- 1-hop catches the high-value cases (direct supersession, direct contradiction)
- 2+ hop reserved for explicit `--trace` queries (Phase C)

**Cost:** O(top_n × avg_edges_per_note) — typically <20 × ~5 = <100 lookups. Adds <30ms.

**Backward compatibility:** if `memory-graph.json` is missing or v1.0 (pre-typed), Pass 6.5 returns candidates unchanged. No-op for legacy state.

**Integration point:** Call after `apply_hierarchy_multiplier()` (existing Pass 6) but before tiered loading:
```python
ranked = score_relevance(notes, context)        # Pass 5
ranked = apply_hierarchy_multiplier(ranked)     # Pass 6
ranked = edge_walk(ranked, top_n=20)            # Pass 6.5 (NEW)
tier1 = ranked[:5]                              # Tiered loading
```

---

## Tiered Loading System

v2.0 loads notes in tiers for on-demand expansion:

### Tier 1: Auto-Load (Top 5)
Most relevant notes loaded and displayed to Claude immediately.

**Output to Claude (v5.1 with Hierarchy Indicators):**
```markdown
[MEMORY] Loaded 5 relevant notes (203ms):

1. **Protocol Enforcement v5.2** ✓ LATEST (Decision, 2026-01-13)
   User-friendly priority system for enforcement queue.
   File: Decisions/Protocol-Enforcement-v5.2.md

2. **Protocol Enforcement v5.1** ⚠️ SUPERSEDED → v5.2 (Decision, 2026-01-10)
   Command queue automation (replaced by v5.2 with better UX).
   File: Decisions/Protocol-Enforcement-v5.1.md
   → Upgrade available: [[Protocol Enforcement v5.2]]

3. **Memory Recall Gap** (Pattern, 2026-01-13)
   Consolidation works but recall never executed.
   File: Patterns/Memory-Recall-Gap.md

4. **No Optional Protocols** (Preference, 2026-01-13)
   User expects 100% compliance on all protocols.
   File: Preferences/No-Optional-Protocols.md

5. **Legacy Hook System** 📦 ARCHIVED (Pattern, 2025-12-01)
   Original Python hook (replaced by gate-enforcer.py).
   File: Patterns/Legacy-Hook-System.md

Tier 2: 10 additional notes cached for expansion.
Tier 3: 4 more notes available via keyword search.
```

**Status Indicators:**

```python
def format_status_indicator(note):
    """Generate status indicator for note title."""
    hierarchy = note.get("_hierarchy_metadata", {})
    status = note.get("_hierarchy_status", "active")

    if status == "active":
        # Check if this is explicitly versioned
        if hierarchy.get("version") or hierarchy.get("supersedes"):
            return "✓ LATEST"
        else:
            return ""  # Standard note, no indicator

    elif status == "superseded":
        superseded_by = hierarchy.get("superseded_by")
        if superseded_by:
            # Extract title from wikilink [[Title]]
            newer_title = superseded_by.strip("[]")
            # Get version if present
            match = re.search(r'v\d+\.\d+', newer_title)
            if match:
                return f"⚠️ SUPERSEDED → {match.group()}"
            else:
                return "⚠️ SUPERSEDED"
        else:
            return "⚠️ SUPERSEDED"

    elif status == "archived":
        return "📦 ARCHIVED"

    return ""


def format_note_for_output(note, index_num):
    """Format note for [MEMORY] block output."""
    title = note["title"]
    note_type = note["type"]
    date = note.get("modified", note.get("created", ""))
    path = note["path"]

    # Status indicator
    status_indicator = format_status_indicator(note)
    if status_indicator:
        title_with_status = f"{title} {status_indicator}"
    else:
        title_with_status = title

    # Summary
    summary = generate_summary(note["content"])

    # Format output
    output = f"{index_num}. **{title_with_status}** ({note_type}, {date})\n"
    output += f"   {summary}\n"
    output += f"   File: {path}"

    # Add upgrade link if superseded
    if note.get("_hierarchy_status") == "superseded":
        hierarchy = note.get("_hierarchy_metadata", {})
        superseded_by = hierarchy.get("superseded_by")
        if superseded_by:
            output += f"\n   → Upgrade available: {superseded_by}"

    return output
```

### Tier 2: Cached (Next 10)
Ranked and cached for instant expansion if needed.

**Expansion trigger:**
Claude outputs: `[MEMORY] Need more context - loading from cache`

System loads additional notes from Tier 2 instantly (cached, no re-search).

**Expansion output:**
```markdown
[MEMORY] Loaded 3 additional notes from cache:

6. **your CRM Stage ID Audit** (Project-Note, 2026-01-09)
   Stage 6 ID is 1030070698 (fixed 3 files).
   File: Projects/your organization/your CRM-Stage-IDs.md

7. **MCP Pagination Protocol** (Decision, 2026-01-11)
   ALWAYS use pageSize=1000 for your CRM.
   File: Decisions/MCP-Pagination-Protocol.md

8. **your CRM Query Optimization** (Pattern, 2026-01-10)
   Combine board queries to reduce API calls.
   File: Patterns/your CRM-Query-Optimization.md
```

### Tier 3: Full Search (Remainder)
Available via keyword search if Tier 1+2 insufficient.

**Rare scenario:** Only if initial 15 notes don't contain needed info.

**Usage:**
Claude outputs: `[MEMORY] Searching for additional context: {keywords}`

System runs keyword search on remaining notes, loads top 3 matches.

## Client Note Injection (v5.0 - Predictive Client Context)

**Purpose:** When the prediction engine detects a client mention in the user's prompt, automatically inject the matching client notes into Tier 1 before standard memory recall runs.

### How It Works

1. **Prediction Engine** (hooks/prediction-engine.py) runs first:
   - Extracts entities: names, companies, deal IDs, your CRM IDs
   - Matches entities against entity_index in memory-index.json
   - Stores matched client_notes in prediction-state.json

2. **Memory Recall** reads prediction-state.json:
   - Checks `current_prediction.client_notes` array
   - If non-empty, these notes are INJECTED at top of Tier 1
   - Standard notes fill remaining Tier 1 slots

3. **[PRE-LOADED] Marker** for transparency:
   - Client notes marked with `[PRE-LOADED]` in output
   - User can see which notes came from client prediction vs. standard recall

### Implementation

```python
def recall_memory_with_client_context(project, domain, limit=5):
    """Enhanced recall that prioritizes client notes from prediction (v5.0)."""

    # Step 1: Check prediction state for client notes
    prediction_state = read_json("session/prediction-state.json")
    client_notes = prediction_state.get("current_prediction", {}).get("client_notes", [])

    # Step 2: Load domain shard (existing v4.0 logic)
    shard = load_json(f"session/shards/{project}-shard.json")

    # Step 3: Run standard filtering pipeline (existing)
    notes = filter_notes(shard, project, domain)

    # Step 4: INJECT client notes at top of Tier 1 (NEW in v5.0)
    final_tier1 = []
    preloaded_count = 0

    if client_notes:
        # Remove client notes from filtered results to avoid duplicates
        client_note_paths = set(client_notes)
        notes = [n for n in notes if n["path"] not in client_note_paths]

        # Add client notes to front of Tier 1
        for client_path in client_notes[:3]:  # Max 3 client notes
            note_meta = find_note_in_shard(shard, client_path)
            if note_meta:
                note_meta["_preloaded"] = True  # Mark as pre-loaded
                final_tier1.append(note_meta)
                preloaded_count += 1

    # Fill remaining Tier 1 slots with standard notes
    remaining_slots = limit - len(final_tier1)
    final_tier1.extend(notes[:remaining_slots])

    # Step 5: Load content with wikilinks (existing v4.1 logic)
    loaded = load_with_wikilinks(final_tier1, shard)

    return {
        "notes": loaded,
        "preloaded_count": preloaded_count,
        "total_count": len(loaded)
    }
```

### Output Format with [PRE-LOADED]

```markdown
[MEMORY] Loaded 5 relevant notes (220ms):

1. **ExampleClient - Client Overview** [PRE-LOADED] (Client, 2026-01-20)
   Equipment rental company, Jim Dale owner. $15K deal Contract Sent.
   File: Projects/your org/Clients/Client-ExampleClient-Shops.md

2. **Jim Dale - Contact** [PRE-LOADED] (Contact, 2026-01-15)
   Primary contact for ExampleClient. Email: contact@example.com
   File: Projects/your org/Contacts/your org-Contact-Jim-Dale.md

3. **your CRM Deal Management** (Decision, 2026-01-10)
   Standard pipeline stages for your org deals.
   File: Decisions/your CRM-Deal-Management.md

4. **Client Communication Patterns** (Pattern, 2026-01-08)
   Best practices for follow-up timing and messaging.
   File: Patterns/Client-Communication-Patterns.md

5. **Professional Services Pricing** (Preference, 2026-01-05)
   3-tier pricing model: Basic, Standard, Premium.
   File: Preferences/Professional-Services-Pricing.md

Tier 2: 10 additional notes cached for expansion.
Pre-loaded: 2 client notes from prompt context.
```

### Confidence-Based Behavior

| Prediction Confidence | Behavior |
|-----------------------|----------|
| **>0.8 (High)** | Inject up to 3 client notes into Tier 1 immediately |
| **0.5-0.79 (Medium)** | Inject up to 2 client notes |
| **0.3-0.49 (Low)** | Inject 1 client note only |
| **<0.3 (Very Low)** | Skip client injection, use standard recall |

### Cache Integration

Client notes are added to the LRU cache with higher priority:
- Client note cache entries have `is_client: true` flag
- Cache eviction favors keeping client notes
- Cache hit rate stays >90% (no degradation expected)

### Performance Impact

| Operation | Before v5.0 | After v5.0 |
|-----------|-------------|------------|
| Prediction engine | 19ms | 45ms (+26ms for entity extraction) |
| Memory recall | 187ms | 220ms (+33ms for client injection) |
| Total | 206ms | 265ms |

**Budget:** <300ms total (well within 500ms UX limit)

## Index-Based Search (v2.0)

v2.0 uses pre-built index.json for O(1) lookups instead of filesystem scans.

**Index Structure (with STRICT TAGS v1.0):**
```json
{
  "notes": [
    {
      "path": "Decisions/Auto-Recall-Memory-System.md",
      "title": "Auto-Recall Memory System Design",
      "created": "2026-01-13T20:45:00Z",
      "modified": "2026-01-13T20:45:00Z",
      "project": "meta",
      "domain": "memory-system",
      "type": "decision",
      "tags": ["decisions", "memory-system"],
      "keywords": ["hook", "tiered", "expansion", "index"],
      "wikilinks": [],
      "char_count": 8500
    },
    {
      "path": "Patterns/your CRM-Query-Optimization.md",
      "title": "your CRM Query Optimization",
      "created": "2026-01-13T12:00:00Z",
      "modified": "2026-01-13T15:30:00Z",
      "project": "partner",
      "domain": "ticketing",
      "type": "pattern",
      "tags": ["patterns", "ticketing"],
      "keywords": ["query", "optimization", "api"],
      "wikilinks": [],
      "char_count": 2000
    }
  ],
  "last_updated": "2026-01-13T20:45:00Z",
  "total_notes": 29
}
```

**Search algorithm (v4.0 - SHARDS-FIRST WITH METRICS):**
```python
def recall_memory(project, domain, limit=5, reason="session_start"):
    # Determine if this is a cache hit
    cache_hit = check_cache_exists_and_valid()

    # 🚀 v4.0: Load project shard FIRST (75% faster than full index)
    shard_path = f"session/shards/{project}-shard.json"

    try:
        # Primary path: Load domain shard (220KB vs 889KB full index)
        index = read_json(shard_path)
        shard_used = True
    except FileNotFoundError:
        # Fallback: Load full index if shard missing
        index = read_json("session/memory-index.json")
        shard_used = False
        log_warning(f"Shard {shard_path} not found, using full index")

    # 4-pass filtering (same as before)
    notes = index["notes"]
    notes = filter_by_project(notes, project)     # Pass 1 (redundant with shard, but safe)
    notes = filter_by_domain(notes, domain)       # Pass 2
    notes = filter_by_type(notes, task_type)      # Pass 3
    notes = score_relevance(notes, context)       # Pass 4

    # Tiered loading
    tier1 = notes[:5]          # Top 5 (load)
    tier2 = notes[5:15]        # Next 10 (cache)
    tier3 = notes[15:]         # Remainder (search)

    # Load Tier 1 content
    loaded_notes = []
    for note in tier1:
        content = read_file(note["path"])
        loaded_notes.append({
            "title": note["title"],
            "summary": generate_summary(content),
            "path": note["path"],
            "type": note["type"],
            "date": note["modified"]
        })

    # Cache Tier 2 for expansion
    cache_expansion_tier(tier2)

    # Track Tier 3 availability
    state["expansion_tier3_count"] = len(tier3)
    state["recall_shard_used"] = shard_used  # Track for metrics

    # LOG RECALL TO METRICS (MANDATORY)
    log_event("memory_recall",
        cache_hit=cache_hit,
        notes_loaded=len(loaded_notes),
        reason=reason  # "session_start" | "substantial_task" | "manual_request" | "expansion"
    )

    return loaded_notes
```

**Performance:**
- **Index read:** <10ms (small JSON file)
- **Filtering:** <50ms (in-memory operations)
- **File reads:** ~100ms (5 files @ 20ms each)
- **Total:** <200ms for full recall

**Scales to 10,000+ notes:**
- Index stays small (metadata only, ~10KB per 100 notes)
- Filtering is O(n) but fast (in-memory)
- Only top 5 files read (not all 10,000)

## Wikilink Following (v4.1 - SILENT EXPANSION)

**CRITICAL:** All memory operations are SILENT - no output to user. Just load and use.

**Purpose:** Follow wikilinks from loaded notes to expand context automatically (5 notes → 15-20 notes).

**Implementation:**
```python
def find_note_in_index(index, path):
    """
    Find note metadata by path in index.

    Args:
        index: Memory index or shard data
        path: Note file path to find

    Returns:
        Note metadata dict or None
    """
    notes = index.get("notes", [])
    for note in notes:
        if note["path"] == path:
            return note
    return None


def find_note_by_title(index, title):
    """
    Find note path by title (for wikilink resolution).

    Args:
        index: Memory index or shard data
        title: Note title to find

    Returns:
        Note path or None
    """
    notes = index.get("notes", [])
    for note in notes:
        if note["title"] == title:
            return note["path"]
    return None


def load_with_wikilinks(note_paths, index, depth=1, max_per_note=3):
    """
    Load notes and follow their wikilinks to expand context.
    SILENT - no console output, no user notification.

    Args:
        note_paths: List of primary note paths to load
        index: Memory index or shard data
        depth: How many levels to traverse (default 1)
        max_per_note: Max wikilinks to follow per note (default 3)

    Returns:
        List of loaded notes (primary + linked)
    """
    loaded = {}
    vault_path = "~/Projects\\memory\\"

    # Load primary notes (Tier 1)
    for path in note_paths:
        full_path = os.path.join(vault_path, path)
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            loaded[path] = {
                "path": path,
                "content": content
            }

            if depth > 0:
                # Get wikilinks from index
                note_meta = find_note_in_index(index, path)
                if note_meta:
                    wikilinks = note_meta.get("wikilinks", [])[:max_per_note]

                    # Follow top 3 most relevant wikilinks (SILENTLY)
                    for link_title in wikilinks:
                        # Find linked note path in index
                        linked_path = find_note_by_title(index, link_title)

                        if linked_path and linked_path not in loaded:
                            # Load linked note (depth=0 to prevent recursion)
                            linked_full_path = os.path.join(vault_path, linked_path)
                            try:
                                with open(linked_full_path, 'r', encoding='utf-8') as f:
                                    linked_content = f.read()
                                loaded[linked_path] = {
                                    "path": linked_path,
                                    "content": linked_content
                                }
                            except FileNotFoundError:
                                # Skip missing linked notes
                                pass
        except FileNotFoundError:
            # Skip missing primary notes
            pass

    return list(loaded.values())
```

**Integration:** Modify `recall_memory()` function to use wikilink loading:

```python
# OLD: Load Tier 1 only
for note in tier1:
    content = read_file(note["path"])
    loaded_notes.append({...})

# NEW: Load Tier 1 WITH wikilinks (SILENT - no output)
tier1_paths = [note["path"] for note in tier1]
loaded_with_links = load_with_wikilinks(tier1_paths, index, depth=1, max_per_note=3)

# Store in context (no user output)
# Claude just has 17 notes in context instead of 5
# User never knows it happened
```

**Result:** 5 notes → 15-20 notes loaded silently (no user notification)

**Performance Impact:** +33ms (220ms total vs 187ms before)

## Auto-Expand Tier 2 (v4.2 - SILENT OPERATION)

**CRITICAL:** Expansion happens silently - no output to user.

**Purpose:** Automatically expand from Tier 1 (5 notes) to Tier 2 (15 notes) when keyword coverage is low.

**Implementation:**
```python
def extract_keywords(prompt):
    """
    Extract meaningful keywords from user prompt.

    Returns: list of lowercase keywords
    """
    # Common stop words to exclude
    stop_words = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'been', 'be',
        'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'should',
        'can', 'could', 'may', 'might', 'must', 'i', 'you', 'we', 'they', 'it',
        'this', 'that', 'these', 'those', 'what', 'which', 'who', 'when', 'where',
        'why', 'how'
    }

    # Extract words (3+ chars, alphanumeric)
    words = re.findall(r'\b\w{3,}\b', prompt.lower())

    # Filter out stop words
    keywords = [w for w in words if w not in stop_words]

    return keywords


def calculate_keyword_coverage(loaded_notes, prompt_keywords):
    """
    Check what % of prompt keywords appear in loaded notes.
    SILENT - no output.

    Returns: float 0.0-1.0 (0% to 100%)
    """
    if len(prompt_keywords) == 0:
        return 1.0  # No keywords to match

    found_keywords = set()

    for note in loaded_notes:
        note_text = note["content"].lower()
        for keyword in prompt_keywords:
            if keyword.lower() in note_text:
                found_keywords.add(keyword)

    return len(found_keywords) / len(prompt_keywords)


def load_tier2_from_cache():
    """
    Load next 10 notes from Tier 2 cache.

    Returns: list of note dicts
    """
    try:
        with open("session/memory-cache.json", 'r', encoding='utf-8') as f:
            cache = json.load(f)

        tier2_notes = cache.get("tier2", [])

        # Load file contents for cached Tier 2 paths
        vault_path = "~/Projects\\memory\\"
        loaded = []

        for note_meta in tier2_notes[:10]:  # Max 10
            path = note_meta["path"]
            full_path = os.path.join(vault_path, path)
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                loaded.append({
                    "path": path,
                    "content": content
                })
            except FileNotFoundError:
                pass

        return loaded
    except FileNotFoundError:
        # Cache doesn't exist yet
        return []


def smart_recall_with_expansion(prompt, project, domain):
    """
    Recall with automatic Tier 2 expansion if coverage is low.
    SILENT - no user notification, just loads more context.

    Returns: list of loaded notes (5-15 depending on coverage)
    """
    # Extract keywords from prompt
    keywords = extract_keywords(prompt)

    # Load Tier 1 (top 5) with wikilinks
    tier1 = load_top_5_with_wikilinks(project, domain)

    # Check keyword coverage (SILENTLY)
    coverage = calculate_keyword_coverage(tier1, keywords)

    if coverage < 0.6:  # Less than 60% coverage
        # AUTO-EXPAND to Tier 2 (SILENTLY)
        tier2 = load_tier2_from_cache()

        # NO OUTPUT - just return expanded context
        # User never knows expansion happened
        return tier1 + tier2
    else:
        return tier1
```

**Integration:** Replace standard `recall_memory()` calls with `smart_recall_with_expansion(prompt, project, domain)`

**Result:** Automatic expansion from 5 to 15 notes when keyword coverage <60% (silent, no user notification)

## v5.3 Scout Background Memory Search (CEO Directive Fix)

### Problem
Scout exists and is spawned on substantial tasks, but NEVER performs background memory searches.
Working memory contains active project context, but scout does not use it for targeted vault queries.
Result: Relevant memory notes are missed during active work sessions.

### Solution: Scout-Driven Background Memory Search

**When scout is active**, it should silently perform targeted memory searches based on:
1. Current working memory entities (active projects, clients)
2. Keywords extracted from the last 3-5 prompts
3. Context shift signals from gate-enforcer.py

**Integration Point:** Scout output goes to `session/growth-output.md` which is already
surfaced to working memory by `surface-background-findings.py`.

### Scout Memory Search Protocol

**Step 1:** Extract active entities from `state.json` secretary_background tracking
  - Read all entries with `tracking_active: true`
  - Extract `project` and `client` fields
  - Also scan current prompt for entity keywords

**Step 2:** Extract keywords from recent prompts (last 5 in prompt-history.jsonl)
  - Filter out task-notifications and trivial prompts
  - Extract nouns and technical terms

**Step 3:** Build targeted search queries against memory-index.json
  - Entity searches (high priority): match by project/domain tags
  - Keyword searches (medium priority): match by content keywords

**Step 4:** Execute searches, deduplicate, rank by relevance

**Step 5:** Write top 5 findings to `session/growth-output.md`
  - Format: title, path, relevance score, tags
  - Appends (does not overwrite) existing growth output

**Step 6:** `surface-background-findings.py` auto-surfaces to working memory
  - Next response sees relevant vault notes in context
  - Zero user interruption

### Entity Extraction from Working Memory

Sources for active entities:
- `state.json -> secretary_background -> {project}.tracking_active == true`
- `state.json -> secretary_background -> {project}.project` and `.client`
- `state.json -> current_prompt.text` (keyword scan)

Entity keyword map:
- product -> your product, product -> your product, bim-tool -> your BIM connector
- exampleclient -> ExampleClient, exampleclient -> ExampleClient, exampleclient -> ExampleClient
- lms -> an LMS, leroy -> LeRoy, bim -> your BIM tool

### Scout Spawn Enhancement

When scout is spawned (via enforcement queue), include these tasks:
1. Monitor for repeatable patterns (existing)
2. **NEW:** Perform background memory search using working memory entities
3. **NEW:** Check if current session topics have relevant vault notes
4. **NEW:** Write findings to growth-output.md for automatic surfacing
5. Trigger: Every 5 minutes OR on context shift signal from gate-enforcer

### Gate-Enforcer Integration (v2.2)

The gate-enforcer now provides context shift signals that scout can consume:
- `enforcement.recall_context_entity`: Entity that triggered context shift
- `enforcement.recall_reason`: Contains "Context shift" when applicable
- Scout reads these flags and initiates targeted memory search

### Wiring Diagram

```
gate-enforcer.py --[context shift]--> enforcement flags
     |
     v
scout agent --[reads flags]--> targeted memory search
     |
     v
growth-output.md --[auto-surface]--> working memory
     |
     v
Next response sees relevant vault notes (zero interruption)
```

## v3.0 Scaling Enhancements

### LRU Cache Module

High-performance cache for repeated queries with 90%+ hit rate after warmup.

**Location:** `scripts/memory-cache.py`

**Features:**
- OrderedDict-based LRU (Least Recently Used) eviction
- O(1) get/put operations
- Hit rate tracking with statistics
- Cache warming from memory-index.json
- Persistence to disk (memory-cache-lru.json)

**Usage:**
```python
from memory_cache import MemoryCache, get_cache

# Get singleton cache instance
cache = get_cache(max_size=100)

# Check cache before expensive operations
result = cache.get("note_path")
if result is None:
    # Cache miss - load from disk
    result = load_note("note_path")
    cache.put("note_path", result)

# Get statistics
stats = cache.get_stats()
# {"hits": 95, "misses": 5, "hit_rate": 0.95, ...}
```

**Performance:**
- get(): O(1)
- put(): O(1)
- warm(): O(n) where n = notes to warm
- Cache hit: <5ms vs cache miss: ~20ms

### Tag Intersection Index

Pre-computed tag combinations for O(1) multi-tag queries.

**Location:** In memory-index.json under `tag_index`

**Structure:**
```json
{
  "tag_index": {
    "single": {
      "ticketing": ["path1", "path2", ...],
      "crm": ["path3", "path4", ...]
    },
    "combo_2": {
      "ticketing+decisions": ["path1"],
      "crm+patterns": ["path5", "path6"]
    },
    "combo_3": {
      "ticketing+decisions+leroy": ["path1"]
    },
    "stats": {
      "single_tags": 16,
      "two_tag_combos": 43,
      "three_tag_combos": 31
    }
  }
}
```

**Usage:**
```python
# O(1) lookup for single tag
notes = index["tag_index"]["single"]["ticketing"]

# O(1) lookup for 2-tag combo
notes = index["tag_index"]["combo_2"]["ticketing+decisions"]

# O(1) lookup for 3-tag combo
notes = index["tag_index"]["combo_3"]["ticketing+decisions+leroy"]
```

**Why it matters:**
- Without: Filter 10,000 notes for each tag = O(n) per tag
- With: Single dict lookup = O(1) regardless of note count

### Pre-computed Scoring

Each note has pre-calculated scores for instant ranking.

**Location:** In each note's `precomputed_scores` field

**Structure:**
```json
{
  "path": "Decisions/Auto-Recall.md",
  "title": "Auto-Recall Implementation",
  "precomputed_scores": {
    "recency": 0.95,      // 1.0 - (days_old / 90), min 0.1
    "type_relevance": 1.0, // decision=1.0, pattern=0.9, etc.
    "project_base": "meta" // For quick project filtering
  }
}
```

**Type Relevance Weights:**
| Type | Weight | Reason |
|------|--------|--------|
| decision | 1.0 | Highest - architectural choices |
| pattern | 0.9 | High - reusable solutions |
| skill-learned | 0.8 | High - valuable insights |
| preference | 0.7 | Medium - user preferences |
| project-note | 0.6 | Medium - project-specific |
| general | 0.4 | Lower - general notes |

**Why it matters:**
- Recency and type scores don't change during session
- Pre-computing saves ~10ms per recall (significant at scale)
- Only `keyword_match` computed at runtime (context-dependent)

### Domain Sharding (v4.0 - PRIMARY LOADING MECHANISM)

**⚡ CRITICAL OPTIMIZATION:** Shards are now the PRIMARY loading path. Full index used only as fallback.

**Location:** `.claude/session/shards/`

**Shard Files:**
- `org-shard.json` - your CRM, your catalog service, LeRoy, Android (~220KB)
- `org-shard.json` - your BIM tool, BIM, your product (~0KB currently)
- `lms-shard.json` - LMS, education, quiz (~0KB currently)
- `meta-shard.json` - Memory system, enforcement, git (~40KB)

**v4.0 Loading Priority:**
```python
# PRIMARY (v4.0): Load project shard FIRST
shard_path = f"session/shards/{project}-shard.json"
try:
    index = load_json(shard_path)  # 220KB - fast!
except FileNotFoundError:
    # FALLBACK: Full index only if shard missing
    index = load_json("memory-index.json")  # 889KB - slower
```

**Performance Impact:**
- **Shard load:** ~50ms (220KB)
- **Full index load:** ~200ms+ (889KB, exceeds Read tool limit)
- **Savings:** 75% faster (669KB saved per recall)

**Master Index Reference:**
```json
{
  "shards": {
    "partner": {"path": ".../org-shard.json", "count": 519},
    "org": {"path": ".../org-shard.json", "count": 0},
    "lms": {"path": ".../lms-shard.json", "count": 0},
    "meta": {"path": ".../meta-shard.json", "count": 39}
  }
}
```

**Why it matters:**
- At 10,000 notes, full index = ~1MB
- Per-project shard = ~250KB (4x faster to load)
- Most sessions work in ONE project (no need to load others)

## Session Cache (v2.0)

v2.0 caches recall results for 10x speedup on follow-up questions.

**Cache Structure:**
```json
{
  "session_id": "protocol-enforcement-v5",
  "recalled_at": "2026-01-13T20:45:00Z",
  "project": "meta",
  "domain": "memory-system",
  "notes_loaded": 5,
  "tier1": [
    {
      "path": "Decisions/Auto-Recall-Memory-System.md",
      "summary": "Automatic memory recall on session start.",
      "relevance_score": 0.95
    }
  ],
  "tier2": [
    { "path": "...", "relevance_score": 0.82 }
  ],
  "tier3_available": 4
}
```

**Cache behavior:**
- **First recall:** Full search (200ms)
- **Follow-up questions:** Cache hit (<20ms)
- **Cache invalidation:** On context compaction or session end
- **Cache file:** `.claude/session/memory-cache.json`

## Recall Process (v2.0)

### 0. Initialize Metrics Collection (FIRST STEP)

**MANDATORY:** Load metrics module at start of recall.

```python
#!/usr/bin/env python3
import sys
sys.path.append(".claude/scripts")
from metrics_collector import log_event, flush_metrics
```

**When to load:**
- Before ANY recall logic
- At top of script if implementing in Python
- After enforcement check if implementing in markdown

### 1. Determine Search Context

**From session state:**
- Current project (your organization/your org/an LMS/meta)
- Current domain (detected from prompt)
- Task type (detected from prompt or substantial_task_active)

**From user prompt:**
- Keywords mentioned
- Files/systems referenced
- Action words (implement, fix, analyze, etc.)

**From recent activity:**
- MCP servers used (your CRM, your catalog service)
- Files recently read/edited
- Agent types spawned

### 2. Execute 4-Pass Filter

See "Smart Filtering Pipeline" section above for details.

### 3. Load Tier 1 Notes

Read top 5 files from vault, generate 2-sentence summaries.

### 4. Output [MEMORY] Block

```markdown
[MEMORY] Loaded 5 relevant notes (187ms):

1. **{title}** ({type}, {date})
   {2-sentence summary}
   File: {path}

... (repeat for all 5)

Tier 2: {N} additional notes cached for expansion.
Tier 3: {N} more notes available via keyword search.
```

### 5. Workflow Suggestion Check (v5.1 - NEW)

After Tier 1 notes loaded, check if any workflows match current context.

**Call:** `skills/meta/suggestion-surfacing.md`

**Integration:**
```python
# After Tier 1 loading completes
tier1_notes = load_tier1_with_wikilinks(filtered_notes)

# NEW v5.1: Check for workflow suggestions
from suggestion_surfacing import check_workflow_suggestions

suggestion_result = check_workflow_suggestions(
    prompt=current_prompt,
    state=state
)

if suggestion_result.get("should_suggest"):
    # Surface suggestion naturally (not as [MEMORY] block)
    # Format: [SUGGESTION] By the way, you've run '{title}' N time(s)...
    output_suggestion(suggestion_result["suggestion_text"])

    # If user accepts, check for automation offer
    # If execution_count >= automation_threshold and not automated:
    #   Offer: "Want me to create a trigger for it?"
```

**Output:**
- If match found: Surfaces 1 workflow suggestion naturally
- If no match: Silent (no output)

**Frequency:** Once per session per workflow (tracked in catalog via `suggested_this_session` flag)

**Automation Threshold Check:**
When user accepts and runs workflow:
1. Increment `execution_count` in catalog
2. If `execution_count >= automation_threshold` AND NOT `automated`:
   - Surface: "You've run this {N} times. Want me to create a trigger for it?"
3. If user accepts automation:
   - Call `skills/meta/skill-composer.md` with `source: workflow_automation`

### 6. Update State & Validate (v2.1 - MANDATORY) + Flush Metrics

**CRITICAL:** MUST update state.json after every recall execution AND flush metrics.

```python
# Update state.json with recall metadata
state = read_json("session/state.json")
state["memory_system"]["last_recall"] = datetime.utcnow().isoformat() + "Z"
state["memory_system"]["notes_loaded"] = len(loaded_notes)
state["memory_system"]["cache_hit"] = cache_hit
state["memory_system"]["recall_time_ms"] = recall_duration_ms
state["memory_system"]["shard_used"] = shard_path if shard_used else "full_index"
state["enforcement"]["must_recall_memory"] = False
write_json("session/state.json", state)

# FLUSH METRICS (MANDATORY - FINAL STEP)
flush_metrics()
```

**Validation Checklist (MANDATORY):**
1. ✅ `last_recall` timestamp updated to NOW
2. ✅ `notes_loaded` matches actual count (0-5)
3. ✅ `enforcement.must_recall_memory` cleared to `false`
4. ✅ [MEMORY] block output to user (unless 0 notes)
5. ✅ If 0 notes loaded, log warning (may be empty vault)
6. ✅ Metrics flushed to disk before function returns

**Error Handling:**
- If recall fails → log error to state.json but DO NOT block workflow
- If shard missing → fallback to full index worked (log shard path used)
- If 0 notes found → output "[MEMORY] No relevant past context" and continue
- Flush metrics regardless of success/failure (use try/finally)

### 6. Write Session Cache

Save Tier 1, Tier 2, and Tier 3 metadata to cache file.

## Dynamic Expansion

If initial 5 notes insufficient, Claude can request more:

**Expansion request:**
```markdown
[MEMORY] Need more context - loading from cache
```

**System response:**
1. Read memory-cache.json
2. Load next N notes from Tier 2 (instant)
3. Output additional [MEMORY] block

**Expansion limits:**
- Max 3 expansions per session
- Max 15 total notes loaded (5 + 10 from Tier 2)
- If still insufficient, suggest manual search with keywords

## Output Formats

### Token Cost Awareness (NEW v6.0)

**Adopted from:** claude-mem.ai's progressive disclosure with explicit token costs.

**Purpose:** Help Claude make informed retrieval decisions by showing token impact of each note and expansion tiers.

**Token Estimation Function:**
```python
def estimate_tokens(content):
    """
    Estimate token count for content.
    Rule of thumb: ~4 characters per token for English text.

    Args:
        content: String content to estimate

    Returns:
        Estimated token count
    """
    if not content:
        return 0
    return len(content) // 4

def format_token_display(tokens):
    """Format token count for display."""
    if tokens < 1000:
        return f"~{tokens}"
    else:
        return f"~{tokens/1000:.1f}k"
```

**Integration into Recall Output:**
```python
def format_memory_output_with_tokens(loaded_notes, recall_time_ms, tier2_count, tier3_count):
    """Format [MEMORY] block with token costs."""

    total_tokens = 0
    note_outputs = []

    for i, note in enumerate(loaded_notes, 1):
        content = note.get('content', '')
        tokens = estimate_tokens(content)
        total_tokens += tokens

        note_output = f"{i}. **{note['title']}** ({note['type']}, {note['date']}) {format_token_display(tokens)}"
        note_output += f"\n   {note['summary']}"
        note_output += f"\n   File: {note['path']}"
        note_outputs.append(note_output)

    # Estimate Tier 2 tokens (avg ~800 tokens per note)
    tier2_tokens = tier2_count * 800

    output = f"[MEMORY] Loaded {len(loaded_notes)} notes ({format_token_display(total_tokens)} tokens) in {recall_time_ms}ms:\n\n"
    output += "\n\n".join(note_outputs)
    output += f"\n\nTier 2: {tier2_count} cached ({format_token_display(tier2_tokens)} if expanded)"
    output += f"\nTier 3: {tier3_count} available via keyword search"

    return output
```

### On Successful Recall (v6.0 with Token Costs)

```markdown
[MEMORY] Loaded 5 notes (~2.8k tokens) in 187ms:

1. **Protocol Enforcement v5.1** (Decision, 2026-01-13) ~720
   Command queue automation for mandatory enforcement actions.
   File: Decisions/Protocol-Enforcement-v5.1.md

2. **Memory Recall Gap** (Pattern, 2026-01-13) ~540
   Consolidation working but recall never executed (write-only).
   File: Patterns/Memory-Recall-Gap.md

3. **Wikilink Generation Algorithm** (Decision, 2026-01-14) ~680
   Automatic 5-step algorithm for graph connectivity.
   File: Decisions/Auto-Wikilink-System.md

4. **Tag Validation Rules** (Pattern, 2026-01-15) ~460
   Strict 4-tag taxonomy with whitelist enforcement.
   File: Patterns/Tag-Validation-Rules.md

5. **Session Isolation Fix** (Decision, 2026-01-13) ~400
   Prevents cross-session memory contamination.
   File: Decisions/Session-Isolation-v3.2.md

Tier 2: 10 cached (~8.0k if expanded)
Tier 3: 4 available via keyword search
```

**Token Cost Guidelines:**
| Scenario | Expected Tokens | Decision |
|----------|-----------------|----------|
| Tier 1 (5 notes) | ~2-4k tokens | Auto-load (acceptable) |
| Tier 2 expansion | ~6-10k tokens | Only if Tier 1 insufficient |
| Full expansion | ~15-20k tokens | Rarely needed |

**Why This Matters:**
- Claude can see token impact before expanding
- Prevents accidental context bloat
- Enables informed decisions on expansion
- Matches claude-mem.ai's progressive disclosure pattern

### On Cache Hit

```markdown
[MEMORY] Loaded 5 relevant notes from cache (<20ms):

... (same format as above)
```

### On No Relevant Notes

```markdown
[MEMORY] No relevant past context found for this task.
Building fresh context from session...
```

### On Expansion

```markdown
[MEMORY] Loaded 3 additional notes from cache:

6. **your CRM Stage ID Audit** (Project-Note, 2026-01-09)
   Stage 6 ID is 1030070698 (fixed 3 files).
   File: Projects/your organization/your CRM-Stage-IDs.md

...
```

## Recall Types

### Session Start (v2.0 PRIMARY)
```
Trigger: EVERY session start (no time gap required)
Priority: 0 (blocking) for substantial, 2 (background) for trivial
Load: Top 5 notes matching current project + domain
```

### Morning Routine
```
Load:
- Yesterday's incomplete tasks
- Upcoming scheduled work
- Recurring patterns (e.g., "Friday reports")
```

### Project Detection
```
Load:
- Last 5 project notes
- Common pitfalls for this project
- Preferred workflows
```

### Before Major Decision
```
Load:
- Similar past decisions
- Lessons learned
- Failed approaches (avoid repeating)
```

### Explicit Request
```
User: "remember the your CRM stage IDs"
Load: Search keywords ["ticketing", "stage", "id"]
```

## Integration Points

**Called By:**
- `hooks/gate-enforcer.py` → on session start (v2.0 AUTO)
- `routines/morning.md` → at morning routine
- `workflows/planning/planning-phase.md` → before planning
- `@agent-conductor` → before major decisions
- Manual trigger: user says "remember {topic}"

**Calls:**
- Read tool (session/memory-index.json, cache, vault files)
- NO Grep, NO Glob (index-based search only)
- NO external dependencies

**Updates:**
- `session/state.json` → last_recall timestamp
- `session/memory-cache.json` → recall results
- `session/memory-expansion.md` → tiered loading state

## Performance

**v3.0 Performance (With Scaling Enhancements):**
- **Cold start (first recall):** <200ms
- **Cache hit (follow-up):** <5ms (LRU cache)
- **Expansion:** <20ms (from cache)
- **Tag intersection lookup:** O(1) regardless of note count
- **Full keyword search:** 2-3 sec (rare, Tier 3 only)

**Scaling Benchmarks:**
| Notes | Cold Start | Cache Hit | Index Size |
|-------|------------|-----------|------------|
| 100 | <100ms | <5ms | ~100KB |
| 558 (current) | <200ms | <5ms | ~500KB |
| 1,000 | <200ms | <5ms | ~1MB |
| 10,000 | <200ms | <5ms | ~10MB (sharded: 4x 2.5MB) |

**Why It Stays Fast at 10K:**
1. **Pre-computed scores** - No recency/type calculations at runtime
2. **Tag intersection index** - O(1) multi-tag queries
3. **Domain sharding** - Load only relevant 25% of data
4. **LRU cache** - 90%+ hit rate after warmup

**Memory Impact:**
- Max 5 notes loaded initially (~5KB)
- Max 15 notes after expansion (~15KB)
- LRU cache: ~100 notes (~100KB)
- Session cache: ~2KB

## Error Handling

### If index.json missing
1. Output warning: `[MEMORY] Index not built - run bootstrap`
2. Fall back to filesystem search (slow but works)
3. Suggest: "Run build-memory-index.py script"

### If vault empty
1. Skip recall silently
2. Continue session normally
3. Log to state.json: `vault_empty: true`

### If search times out (>2s)
1. Return partial results
2. Log warning to state.json
3. Suggest vault cleanup or re-index

### If cache corrupted
1. Delete cache file
2. Re-run recall from index
3. Rebuild cache

## What Gets Recalled

| Situation | Load |
|-----------|------|
| **Session start (substantial)** | Top 5 by project + domain (Priority 0) |
| **Session start (trivial)** | Top 5 by project + domain (Priority 2) |
| **Starting your organization work** | your organization project notes, ticketing/your CRM patterns |
| **Before git commit** | Commit workflow lessons, sentinel flags |
| **Planning new feature** | Similar feature decisions, failed attempts |
| **Report generation** | Report format preferences, past corrections |
| **MCP API work** | Pagination patterns, error handling |

## What Gets Ignored

- Notes older than 90 days (unless high relevance score)
- Archived memories (in System/Archive/)
- Notes tagged `#deprecated`
- Notes with relevance score < 0.3

## Testing

### Test 1: Session Start Auto-Recall
```bash
# Wait 30+ min, send message
# Expected: [MEMORY] block shows 5 notes loaded
# Verify: state.json last_recall updated
```

### Test 2: Cache Hit
```bash
# First question → full recall (200ms)
# Second question → cache hit (<20ms)
# Verify: memory-cache.json exists
```

### Test 3: Tiered Expansion
```bash
# Ask question requiring info not in Tier 1
# Output: "[MEMORY] Need more context - loading from cache"
# Expected: Tier 2 notes loaded
```

### Test 4: Filtering Accuracy
```bash
# your CRM prompt → should load ticketing-related notes
# Verify: All 5 notes have domain="ticketing"
```

## Metrics Integration (v4.1)

**Purpose:** Track recall performance and cache effectiveness.

**Events Logged:**

1. **memory_recall** - Every recall execution
   - Fields: `cache_hit` (True/False), `notes_loaded`, `reason`
   - Purpose: Monitor cache hit rate and recall patterns

**Reason Values:**
- `session_start` - Auto-triggered on session start (30+ min gap)
- `substantial_task` - Triggered before major work
- `manual_request` - User explicitly asked ("remember X")
- `expansion` - Tier 2 expansion from cache

**Data Storage:**
- Location: `.claude/session/metrics/events-YYYY-MM-DD.jsonl`
- Format: One JSON object per line
- Rotation: Daily files (automatic)

**Analysis Examples:**

```bash
# Calculate cache hit rate
total=$(grep memory_recall .claude/session/metrics/events-2026-01-16.jsonl | wc -l)
hits=$(grep memory_recall .claude/session/metrics/events-2026-01-16.jsonl | grep '"cache_hit":true' | wc -l)
echo "Cache hit rate: $((hits * 100 / total))%"

# Check recall triggers
grep memory_recall .claude/session/metrics/events-2026-01-16.jsonl | jq .reason

# Average notes loaded
grep memory_recall .claude/session/metrics/events-2026-01-16.jsonl | jq .notes_loaded | awk '{sum+=$1; count++} END {print sum/count}'
```

**Why Metrics Matter:**
- Cache hit rate → validate 90%+ target
- Recall reasons → understand trigger patterns
- Notes loaded → optimize tiered loading

**Expected Performance:**
- Cache hit rate: 90%+ after session warmup
- Average notes loaded: 5 (Tier 1)
- Session start recalls: Most common reason

---

*Auto-triggered skill | Index-based search | Working-memory-directed | v5.2 (Phase 5: Smart Memory Recall)*
