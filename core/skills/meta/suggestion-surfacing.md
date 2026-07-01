# Suggestion Surfacing - Context-Aware Workflow Recommendations

> **Purpose:** Check workflow catalog during memory recall and surface relevant workflows naturally when context matches.
> **Trigger:** Called automatically by memory-recall.md after Tier 1 loading completes.
> **Frequency:** Once per session per workflow (no spamming).

## Fixed Paths

| Purpose | Path |
|---------|------|
| Workflow Catalog | `.claude/session/workflow-catalog.json` |
| Session State | `.claude/session/state.json` |
| Suggestion Log | `.claude/session/suggestion-log.jsonl` |

## Trigger

This skill is called automatically by `skills/meta/memory-recall.md` after Tier 1 notes are loaded.

**Integration point:** After line ~300 in memory-recall.md (post Tier 1 loading).

## Logic Flow

### Step 1: Read Workflow Catalog

```python
def load_workflow_catalog():
    """Load workflow catalog from session directory."""
    catalog_path = ".claude/session/workflow-catalog.json"

    try:
        with open(catalog_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {"version": "1.0", "total_workflows": 0, "workflows": []}
    except json.JSONDecodeError:
        return {"version": "1.0", "total_workflows": 0, "workflows": []}
```

### Step 2: Filter by Context Match

```python
def filter_by_context(workflows, prompt):
    """
    Filter workflows where 50%+ of context_keywords match the prompt.

    Args:
        workflows: List of workflow dicts from catalog
        prompt: Current user prompt (lowercase)

    Returns:
        List of (workflow, overlap_score) tuples
    """
    prompt_lower = prompt.lower()
    matches = []

    for workflow in workflows:
        keywords = workflow.get("context_keywords", [])
        if not keywords:
            continue

        # Count matching keywords
        matched = sum(1 for kw in keywords if kw.lower() in prompt_lower)
        overlap = matched / len(keywords)

        if overlap >= 0.5:  # 50% threshold
            matches.append((workflow, overlap))

    return matches
```

### Step 3: Filter by Session State

```python
def filter_by_session_state(matches, state):
    """
    Filter out workflows that:
    - Were already suggested this session
    - Were dismissed in past 7 days

    Args:
        matches: List of (workflow, score) tuples
        state: Current session state dict

    Returns:
        Filtered list of (workflow, score) tuples
    """
    session_id = state.get("session_id", "")
    now = datetime.utcnow()
    seven_days_ago = now - timedelta(days=7)

    filtered = []
    for workflow, score in matches:
        # Skip if already suggested this session
        if workflow.get("suggested_this_session", False):
            continue

        # Check dismissal history
        last_dismissed = workflow.get("last_dismissed")
        if last_dismissed:
            dismissed_dt = datetime.fromisoformat(last_dismissed.replace("Z", ""))
            if dismissed_dt > seven_days_ago:
                continue  # Skip - dismissed within 7 days

        filtered.append((workflow, score))

    return filtered
```

### Step 4: Rank by Relevance

```python
def rank_workflows(matches):
    """
    Rank workflows by weighted score.

    Score = (keyword_overlap * 0.6) + (execution_count * 0.2) + (recency * 0.2)

    Args:
        matches: List of (workflow, overlap_score) tuples

    Returns:
        Sorted list, highest score first
    """
    now = datetime.utcnow()
    scored = []

    for workflow, overlap in matches:
        # Keyword overlap: 60% weight
        keyword_score = overlap * 0.6

        # Execution count: 20% weight (normalized to 0-1)
        exec_count = workflow.get("execution_count", 1)
        exec_score = min(exec_count / 10, 1.0) * 0.2

        # Recency: 20% weight (1.0 if today, 0 if >30 days)
        last_executed = workflow.get("last_executed")
        if last_executed:
            last_dt = datetime.fromisoformat(last_executed.replace("Z", ""))
            days_ago = (now - last_dt).days
            recency_score = max(0, 1 - (days_ago / 30)) * 0.2
        else:
            recency_score = 0

        total_score = keyword_score + exec_score + recency_score
        scored.append((workflow, total_score))

    # Sort by score descending
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored
```

### Step 5: Select Top 1 Workflow

```python
def select_suggestion(ranked_workflows):
    """
    Select top 1 workflow for suggestion.

    Never suggest multiple at once - too noisy.

    Args:
        ranked_workflows: Sorted list of (workflow, score) tuples

    Returns:
        Single workflow dict or None
    """
    if not ranked_workflows:
        return None

    return ranked_workflows[0][0]
```

### Step 6: Surface Naturally

```python
def format_suggestion(workflow):
    """
    Format suggestion for natural conversation output.

    Args:
        workflow: Workflow dict from catalog

    Returns:
        Formatted suggestion string
    """
    title = workflow.get("title", "workflow")
    exec_count = workflow.get("execution_count", 1)
    parameters = workflow.get("parameters", [])

    base_msg = f"By the way, you've run '{title}' {exec_count} time(s)."

    if parameters:
        param_str = ", ".join(parameters)
        return f"{base_msg} Want to run it again? I'll need: {param_str}"
    else:
        return f"{base_msg} Want to run it again?"
```

### Step 7: Track Suggestion

```python
def track_suggestion(workflow_id, action, parameters=None, reason=None):
    """
    Append suggestion event to suggestion-log.jsonl and update catalog.

    Args:
        workflow_id: ID of the workflow
        action: "suggested" | "accepted" | "dismissed"
        parameters: Dict of parameters (for accepted)
        reason: Dismissal reason (for dismissed)
    """
    log_path = ".claude/session/suggestion-log.jsonl"
    catalog_path = ".claude/session/workflow-catalog.json"

    # Build log entry
    entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "workflow_id": workflow_id,
        "action": action,
        "session_id": get_session_id()
    }

    if parameters:
        entry["parameters"] = parameters
    if reason:
        entry["reason"] = reason

    # Append to log
    with open(log_path, 'a') as f:
        f.write(json.dumps(entry) + "\n")

    # Update catalog
    with open(catalog_path, 'r') as f:
        catalog = json.load(f)

    for workflow in catalog["workflows"]:
        if workflow["id"] == workflow_id:
            if action == "suggested":
                workflow["suggested_this_session"] = True
                workflow["suggestion_count"] = workflow.get("suggestion_count", 0) + 1
                workflow["last_suggested"] = entry["timestamp"]
            elif action == "accepted":
                workflow["suggestion_accepted"] = workflow.get("suggestion_accepted", 0) + 1
                workflow["execution_count"] = workflow.get("execution_count", 0) + 1
                workflow["last_executed"] = entry["timestamp"]
            elif action == "dismissed":
                workflow["suggestion_dismissed"] = workflow.get("suggestion_dismissed", 0) + 1
                workflow["last_dismissed"] = entry["timestamp"]
            break

    catalog["last_updated"] = entry["timestamp"]

    with open(catalog_path, 'w') as f:
        json.dump(catalog, f, indent=2)
```

## Main Function

```python
def check_workflow_suggestions(prompt, state):
    """
    Main entry point for suggestion surfacing.

    Called by memory-recall.md after Tier 1 loading.

    Args:
        prompt: Current user prompt
        state: Session state dict

    Returns:
        Dict with:
            - should_suggest: bool
            - suggestion_text: str (if should_suggest)
            - workflow_id: str (if should_suggest)
    """
    # Step 1: Load catalog
    catalog = load_workflow_catalog()
    workflows = catalog.get("workflows", [])

    if not workflows:
        return {"should_suggest": False}

    # Step 2: Filter by context
    matches = filter_by_context(workflows, prompt)

    if not matches:
        return {"should_suggest": False}

    # Step 3: Filter by session state
    filtered = filter_by_session_state(matches, state)

    if not filtered:
        return {"should_suggest": False}

    # Step 4: Rank by relevance
    ranked = rank_workflows(filtered)

    # Step 5: Select top 1
    selected = select_suggestion(ranked)

    if not selected:
        return {"should_suggest": False}

    # Step 6: Format suggestion
    suggestion_text = format_suggestion(selected)

    # Step 7: Track (mark as suggested)
    track_suggestion(selected["id"], "suggested")

    return {
        "should_suggest": True,
        "suggestion_text": suggestion_text,
        "workflow_id": selected["id"],
        "workflow": selected
    }
```

## User Response Handling

### If User Accepts

```python
def handle_acceptance(workflow_id, parameters=None):
    """
    Handle user accepting a workflow suggestion.

    1. Track acceptance
    2. Execute workflow from pattern note
    3. Check automation threshold

    Args:
        workflow_id: ID of the workflow
        parameters: Dict of user-provided parameters
    """
    # Track acceptance
    track_suggestion(workflow_id, "accepted", parameters=parameters)

    # Load catalog to get workflow details
    catalog = load_workflow_catalog()
    workflow = None
    for w in catalog["workflows"]:
        if w["id"] == workflow_id:
            workflow = w
            break

    if not workflow:
        return

    # Check automation threshold
    exec_count = workflow.get("execution_count", 0)
    threshold = workflow.get("automation_threshold", 3)
    automated = workflow.get("automated", False)

    if exec_count >= threshold and not automated:
        # Surface automation offer
        return {
            "offer_automation": True,
            "message": f"You've run this {exec_count} times. Want me to create a trigger for it?"
        }

    return {"offer_automation": False}
```

### If User Dismisses

```python
def handle_dismissal(workflow_id, reason="not_needed"):
    """
    Handle user dismissing a workflow suggestion.

    1. Track dismissal
    2. Suppress for 7 days

    Args:
        workflow_id: ID of the workflow
        reason: Why user dismissed (default: "not_needed")
    """
    track_suggestion(workflow_id, "dismissed", reason=reason)
```

### If User Ignores

No action needed. The suggestion can be surfaced again in a future session.

## Output Format

**When suggestion found:**
```
[SUGGESTION] By the way, you've run 'Quarterly New Clients Report' 2 time(s). Want to run it again? I'll need: quarter, year
```

**When no suggestion:**
No output (silent).

**When automation threshold reached:**
```
[AUTOMATION OFFER] You've run 'Quarterly New Clients Report' 3 times. Want me to create a trigger for it?
```

## Suggestion Log Format

Append-only JSONL for analytics and debugging:

```json
{"timestamp": "2026-01-25T16:00:00Z", "workflow_id": "crm-quarterly-new-clients", "action": "suggested", "session_id": "abc123"}
{"timestamp": "2026-01-25T16:02:00Z", "workflow_id": "crm-quarterly-new-clients", "action": "accepted", "parameters": {"quarter": "Q2", "year": 2026}}
{"timestamp": "2026-01-26T10:00:00Z", "workflow_id": "crm-quarterly-new-clients", "action": "dismissed", "reason": "not_needed"}
```

## Integration Points

**Called By:**
- `skills/meta/memory-recall.md` - After Tier 1 loading (Step 6)

**Calls:**
- Reads `.claude/session/workflow-catalog.json`
- Reads `.claude/session/state.json`
- Writes `.claude/session/suggestion-log.jsonl`

**Updates:**
- Workflow catalog `suggested_this_session`, `suggestion_count`, etc.

## Performance

| Operation | Time |
|-----------|------|
| Load catalog | <5ms |
| Filter by context | <10ms |
| Rank workflows | <5ms |
| Track suggestion | <5ms |
| **Total** | <25ms |

---

*Suggestion Surfacing v1.0 | Context-aware workflow recommendations | Once per session per workflow*
