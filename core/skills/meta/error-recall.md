# Error Recall - Proactive Failure Prevention

> **PURPOSE:** Check memory for known errors before executing potentially failing operations.
> **TRIGGER:** Before bash commands, file operations, or MCP calls that match known failure patterns.

## When to Run

**Automatic triggers:**
- BEFORE bash command execution (if command matches known failure signature)
- BEFORE file read operations (if path previously failed)
- BEFORE MCP tool calls (if similar call failed before)
- ON explicit request: "check for errors", "any known issues?"

**Manual triggers:**
- User asks: "Will this work?" or "Has this failed before?"
- Before repeating a recently-attempted operation
- During troubleshooting workflows

## How It Works

### 1. Extract Operation Signature

From proposed action, generate signature:

```python
def generate_signature(operation):
    """Generate error signature from proposed operation"""

    # For bash commands
    if operation.startswith("bash:"):
        cmd = operation.replace("bash:", "")
        # Normalize command (remove paths, focus on structure)
        normalized = normalize_command(cmd)
        return f"bash_command:{hash(normalized)}"

    # For file reads
    elif operation.startswith("read:"):
        path = operation.replace("read:", "")
        # Check if specific path or pattern matches known failures
        return f"read_path:{hash(path)}"

    # For MCP calls
    elif operation.startswith("mcp:"):
        server, tool = parse_mcp_operation(operation)
        return f"mcp_{server}:{tool}"

    return None
```

### 2. Query Memory Index

```python
# Load memory index
index = read_json("session/memory-index.json")

# Filter for error-solution notes
error_notes = [
    note for note in index["notes"]
    if note["type"] == "error-solution"
]

# Match by signature or context
matches = []
for note in error_notes:
    if note.get("signature") == operation_signature:
        matches.append(note)
    elif operation_context in note.get("keywords", []):
        matches.append(note)

# Sort by relevance (most recent first)
matches.sort(key=lambda x: x["modified"], reverse=True)

# Return top 3
return matches[:3]
```

### 3. Load Error Solution Notes

```python
# For each match, load full note
for match in matches:
    note_path = f"memory/{match['path']}"
    note_content = read_file(note_path)

    # Extract key fields
    error_details = parse_frontmatter(note_content)
    status = error_details["status"]  # unresolved | resolved | workaround
    occurrences = error_details["occurrences"]
    last_seen = error_details["last_seen"]

    # Parse solution section
    solution = extract_solution_section(note_content)
```

### 4. Output [ERROR-CHECK] Block

```
[ERROR-CHECK] Known issue detected:

⚠️  {ERROR_TYPE}: {command or operation}
   Occurred {N}x previously (last: {timestamp})
   Status: {RESOLVED|WORKAROUND|UNRESOLVED}

   {Brief description of error}

   Solution: {solution if status=resolved}
   OR
   Workaround: {workaround if status=workaround}
   OR
   Note: This error is UNRESOLVED - proceed with caution

   Recommendation: {proceed|modify|avoid}
```

## Output Examples

### Example 1: Resolved Error

```
[ERROR-CHECK] Known issue detected:

⚠️  BASH ERROR: ls /missing/directory
   Occurred 3x previously (last: 2026-01-15T10:30:00Z)
   Status: RESOLVED

   Error: Directory does not exist - exits with code 1

   Solution: Check directory existence first:
   ```bash
   if [ -d "/path/to/dir" ]; then
       ls "/path/to/dir"
   else
       echo "Directory not found"
   fi
   ```

   Recommendation: Apply solution before executing ✅
```

### Example 2: Workaround Available

```
[ERROR-CHECK] Known issue detected:

⚠️  MCP ERROR: ticketing_tool with pageSize=1000
   Occurred 2x previously (last: 2026-01-14T15:20:00Z)
   Status: WORKAROUND

   Error: API timeout when requesting 1000 items in single call

   Workaround: Use pagination with pageSize=200:
   ```python
   all_items = []
   page = 1
   while True:
       batch = ticketing_tool(pageSize=200, page=page)
       if not batch: break
       all_items.extend(batch)
       page += 1
   ```

   Recommendation: Use workaround approach ⚠️
```

### Example 3: Unresolved Error

```
[ERROR-CHECK] Known issue detected:

⚠️  IO ERROR: Failed to save state.json
   Occurred 5x previously (last: 2026-01-15T11:45:00Z)
   Status: UNRESOLVED

   Error: Permission denied or file lock contention

   Note: This error is UNRESOLVED - root cause still under investigation

   Potential causes:
   - File lock by another process
   - Antivirus interference
   - Disk permissions issue

   Recommendation: Proceed with caution - error may recur 🚨
```

### Example 4: No Known Issues

```
[ERROR-CHECK] No known failures for this operation.

Operation: bash("git status")
Status: ✅ SAFE (no previous failures recorded)

Recommendation: Proceed normally
```

## Integration with Main Conversation

**Automatic Check Pattern:**

```python
# When Claude is about to execute a bash command:
User: "Run ls -la /some/path"

# BEFORE executing, Claude runs error-recall:
Claude: [Internal check - error recall for "ls -la /some/path"]

# If match found:
Claude: [ERROR-CHECK] Known issue detected: ...
        [Presents solution or workaround]
        [Asks user: "Would you like me to apply the solution?"]

# If no match:
Claude: [Executes command normally]
```

**Performance Note:**
- Error recall is FAST: query index (O(1) hash lookup) + load 1-3 notes (<200ms)
- Only runs when operation matches known failure patterns
- Prevents wasted time repeating known failures

## Signature Matching Rules

### Bash Commands

**Exact match:**
- `ls /nonexistent/path` matches previous `ls /nonexistent/path`

**Pattern match:**
- `ls /any/missing/dir` matches pattern "ls {path} → exit code 1"
- `git push origin feature/*` matches pattern "git push → authentication failed"

### File Operations

**Path match:**
- `Read("missing-file.txt")` matches previous read failure on same path

**Extension match:**
- `Read("*.log")` matches pattern "log files exceed size limit"

### MCP Calls

**Tool match:**
- `ticketing_tool(pageSize=1000)` matches previous timeout
- `list_deals(limit=200)` matches pagination trigger

## Error Categories

| Category | Signature Pattern | Example |
|----------|-------------------|---------|
| Bash Exit Code | `bash_exit_{code}:{command_hash}` | `bash_exit_1:ls_missing` |
| File Not Found | `io_error:file_not_found:{path_pattern}` | `io_error:file_not_found:*.log` |
| Permission Denied | `io_error:permission:{resource}` | `io_error:permission:state.json` |
| MCP Timeout | `mcp_{server}:timeout:{tool}` | `mcp_ticketing:timeout:list` |
| MCP Pagination | `mcp_{server}:pagination:{tool}` | `mcp_crm:pagination:deals` |
| State Corruption | `state_corruption:{file}` | `state_corruption:state.json` |
| JSON Decode | `json_decode:{file}` | `json_decode:memory-index.json` |

## When NOT to Check

**Skip error recall for:**
- First-time operations (no history to check)
- Operations that can't fail (read from guaranteed paths)
- Low-risk operations (formatting, calculations)
- Operations with built-in error handling

## Error Recall vs. Error Logging

| Feature | Error Logging (Phase 2) | Error Recall (Phase 6) |
|---------|------------------------|------------------------|
| **When** | AFTER operation fails | BEFORE operation runs |
| **Purpose** | Capture failures for learning | Prevent known failures |
| **Output** | error-log.jsonl | [ERROR-CHECK] block |
| **Action** | Record for pattern detection | Apply solution proactively |

**Flow:**
1. Operation attempted → Fails → Logged to error-log.jsonl
2. Growth monitor detects pattern (2+ occurrences)
3. Memory consolidation creates error-solution note
4. Error recall loads note and prevents future failures

## Fixed Paths

| Purpose | Path |
|---------|------|
| Error Log | `.claude/session/error-log.jsonl` |
| Memory Index | `.claude/session/memory-index.json` |
| Error Solutions | `memory/Claude/Error-Solutions/{category}/` |

## Success Metrics

**Effectiveness:**
- Errors prevented per week (target: 5+)
- Time saved by avoiding known failures (target: 30+ min/week)
- Reduction in repeated error occurrences (target: 50%+)

**Example:**
Week 1: 12 bash errors recorded
Week 2: 6 bash errors (50% reduction) - 6 prevented by error recall

---

*Part of Token Burn Optimization Plan - Phase 6*
*Integrates with: error-log.jsonl (Phase 2), scout (Phase 3), memory-consolidation (Phase 4)*
