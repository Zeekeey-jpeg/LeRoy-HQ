---
name: sub-agent-spawning
description: |
  Infrastructure for spawning and managing background sub-agents.

  Use when:
  - Need background processing while continuing main work
  - Spawning scout or other background agents
  - Managing long-running tasks asynchronously
  - Collecting results from background workers

  Includes: Spawn patterns, output monitoring, handoff protocols, error handling.
---

# Sub-Agent Spawning Infrastructure

Background sub-agents enable parallel work without blocking the main conversation.

## Quick Reference

### Spawn Background Agent
```
Task tool with:
  subagent_type: "general-purpose"
  run_in_background: true
  prompt: "[agent instructions]"
```

### Check Output
```
Read tool on output_file path returned from Task
  OR
Bash: tail -50 [output_file]
```

### Get Final Results
```
TaskOutput tool with:
  task_id: "[id from spawn]"
  block: true (wait) or false (check status)
```

---

## When to Use Background vs Inline

### Use Background When:
| Scenario | Why Background |
|----------|----------------|
| Growth monitoring | Continuous, shouldn't interrupt |
| Long analysis | User can continue other work |
| Batch processing | Results needed later, not immediately |
| Parallel tasks | Multiple independent jobs |
| Non-blocking checks | Validation that doesn't gate progress |

### Stay Inline When:
| Scenario | Why Inline |
|----------|------------|
| Results needed immediately | Can't proceed without output |
| Sequential dependency | Next step depends on this result |
| User interaction required | Agent needs to ask questions |
| Short tasks (<30 seconds) | Overhead not worth it |
| Critical path work | Must complete before moving on |

---

## Spawning Patterns

### Pattern 1: Fire and Forget (Monitoring)

For agents that run continuously and report at breakpoints.

```yaml
Spawn:
  Task tool:
    subagent_type: "general-purpose"
    run_in_background: true
    description: "Background growth monitor"
    prompt: |
      You are the scout agent running in background.

      Monitor this conversation for:
      - Repeated tool sequences (3+ same pattern)
      - Clarification gaps (same questions asked)
      - Workflow patterns worth capturing
      - Domain knowledge used repeatedly

      Accumulate silently. Do not output until:
      - You detect 3+ actionable patterns
      - Session approaches end
      - Explicitly asked for report

      Output format when surfacing:
      [GROWTH] Patterns detected: X
      [List patterns with suggested skill/agent paths]

Result: Returns task_id and output_file path
Action: Store task_id, continue main work
Check: Periodically read output_file or wait for TaskOutput
```

### Pattern 2: Background Processing (Results Needed Later)

For work that takes time but results are needed eventually.

```yaml
Spawn:
  Task tool:
    subagent_type: "general-purpose"
    run_in_background: true
    description: "Analyze codebase for patterns"
    prompt: |
      Analyze the codebase at [path] for:
      - Common patterns
      - Potential refactoring targets
      - Documentation gaps

      Return structured JSON with findings.

Result: Returns task_id and output_file
Action: Continue other work
Later:
  TaskOutput tool:
    task_id: "[stored id]"
    block: true
    timeout: 60000
```

### Pattern 3: Parallel Execution (Multiple Jobs)

For running multiple independent tasks simultaneously.

```yaml
Spawn Multiple (single message, multiple tool calls):
  Task tool #1:
    subagent_type: "general-purpose"
    run_in_background: true
    description: "Analyze module A"
    prompt: "..."

  Task tool #2:
    subagent_type: "general-purpose"
    run_in_background: true
    description: "Analyze module B"
    prompt: "..."

  Task tool #3:
    subagent_type: "general-purpose"
    run_in_background: true
    description: "Analyze module C"
    prompt: "..."

Result: Three task_ids
Action: Continue work or wait for all
Collect: TaskOutput for each, or read output_files
```

---

## Output Monitoring

### Method 1: Read Output File

```yaml
When: Need to check progress without blocking

Tool: Read
Path: [output_file from spawn result]

Pro: Non-blocking, see partial progress
Con: May see incomplete output
```

### Method 2: Tail Output File

```yaml
When: Want recent output only

Tool: Bash
Command: tail -50 [output_file]

Pro: Quick check, recent activity
Con: Limited context
```

### Method 3: TaskOutput (Blocking)

```yaml
When: Need final results, ready to wait

Tool: TaskOutput
Params:
  task_id: "[id]"
  block: true
  timeout: 30000  # ms, max 600000

Pro: Complete results, knows when done
Con: Blocks until complete or timeout
```

### Method 4: TaskOutput (Non-Blocking Check)

```yaml
When: Quick status check

Tool: TaskOutput
Params:
  task_id: "[id]"
  block: false

Pro: Immediate status
Con: May not have results yet
```

---

## Handoff Protocols

### Background → Main Conversation

When background agent has results for main flow:

```yaml
1. Background agent writes to output_file
2. Main conversation checks output_file at breakpoint
3. If actionable results:
   a. Parse output
   b. Present to user
   c. Take action based on response
4. If no results: Continue, check later
```

### Main → Background Agent

When main conversation needs to update background agent:

```yaml
Option A: Kill and respawn with new instructions
  KillShell tool: shell_id
  Task tool: new spawn with updated prompt

Option B: Use resume parameter
  Task tool:
    resume: "[previous task_id]"
    prompt: "Updated instructions: ..."
```

### Agent → Agent (via files)

When one background agent needs to pass to another:

```yaml
1. Agent A writes to known file path
2. Agent B monitors that file path
3. Or: Agent A completes, main spawns Agent B with A's output
```

---

## Error Handling

### Timeout Handling

```yaml
Scenario: TaskOutput times out

Response:
  1. Check if task still running (TaskOutput block: false)
  2. If running: Extend timeout or let continue
  3. If stuck: KillShell and handle gracefully
  4. Log issue for debugging
```

### Agent Failure

```yaml
Scenario: Background agent errors

Detection:
  - TaskOutput returns error status
  - Output file contains error messages
  - No output after reasonable time

Response:
  1. Read output_file for error details
  2. Decide: retry, skip, or escalate
  3. If critical: Inform user
  4. If non-critical: Log and continue
```

### Resource Cleanup

```yaml
After background work completes:
  1. Collect final results via TaskOutput
  2. Process/store results as needed
  3. No explicit cleanup needed (auto-managed)
```

---

## Growth Monitor Integration

The scout agent is the primary use case for this infrastructure.

### Auto-Spawn Trigger

```yaml
When: First substantial task detected (3+ steps, multi-file, planning required)
How: Session gate triggers spawn automatically
```

### Spawn Command (used by session-gate)

```yaml
Task tool:
  subagent_type: "general-purpose"
  run_in_background: true
  model: "haiku"  # Lightweight for monitoring
  description: "Growth monitor - background"
  prompt: |
    Load and execute: skills/agents/scout.md

    Monitor the main conversation for patterns.
    Accumulate silently.
    Surface at breakpoints only.
```

### Check Points

```yaml
Surface growth suggestions at:
  - Task completion ("done", "finished", "that's all")
  - Commit preparation
  - User request ("growth report", "what patterns?")
  - Session winding down
  - 3+ patterns accumulated

Do NOT surface:
  - Mid-task
  - During user input
  - For every small observation
```

---

## Best Practices

### DO:
- Use `haiku` model for monitoring agents (lightweight)
- Store task_ids for later reference
- Check output at natural breakpoints
- Handle timeouts gracefully
- Clean up references when done

### DON'T:
- Spawn background for tasks needing immediate results
- Forget to check background agent output
- Block main conversation waiting for non-critical background work
- Spawn too many parallel agents (context/resource limits)
- Ignore error states

---

## Examples

### Example: Spawn Growth Monitor at Session Start

```
[Session starts, substantial task detected]

Claude spawns:
  Task tool:
    subagent_type: "general-purpose"
    run_in_background: true
    model: "haiku"
    description: "Growth monitor"
    prompt: "[scout instructions]"

Result: task_id: "abc123", output_file: "/tmp/agent_abc123.txt"

Claude stores: scout_id = "abc123"
Claude continues: Main conversation work

[Later, at task completion]

Claude checks:
  Read tool: /tmp/agent_abc123.txt

If patterns found: Surface to user
If none: Continue silently
```

### Example: Parallel Analysis

```
User: "Analyze all three modules for refactoring opportunities"

Claude spawns (single message, 3 tool calls):
  Task #1: Analyze module-a/
  Task #2: Analyze module-b/
  Task #3: Analyze module-c/

All run in parallel.

Claude: "I've started analyzing all three modules in parallel.
         I'll compile results when complete."

[Continue other work or wait]

Claude collects:
  TaskOutput: task_1_id
  TaskOutput: task_2_id
  TaskOutput: task_3_id

Claude: "Analysis complete. Here's what I found..."
```

---

## Reference: Task Tool Parameters

```yaml
Task tool schema:
  subagent_type: string (required)
    - "general-purpose": Full capabilities
    - "Bash": Command execution
    - "Explore": Codebase exploration
    - "Plan": Architecture planning

  prompt: string (required)
    - Instructions for the agent

  description: string (required)
    - Short (3-5 word) summary

  run_in_background: boolean (optional)
    - true: Returns immediately with task_id
    - false/omitted: Blocks until complete

  model: string (optional)
    - "haiku": Fast, cheap
    - "sonnet": Balanced
    - "opus": Most capable
    - omit: Inherits parent model

  resume: string (optional)
    - Previous task_id to continue from
```

---

*Sub-Agent Spawning Infrastructure v1.0*
