# Skill Tool Routing Logic
*Decision protocol for when to use the Skill tool vs. Read directly.*

---

## The Rule

The Skill tool ONLY works for skills registered in its "Available skills:" list.

Before using the Skill tool, follow this decision tree:

1. Check if "Available skills:" section contains any registered skills
2. If section is **empty** → Skip Skill tool entirely, go directly to Read
3. If section has skills → Check if target skill is in the list
4. If skill **not found** in list → Skip Skill tool, go directly to Read
5. If skill **found** → Use Skill tool

---

## Why This Matters

The system has 260+ skills. The Skill tool only has a handful registered at any given time. Most skill loading is done via the Read tool directly (e.g., `Read("~/.claude\skills\meta\memory-recall.md")`).

**Default behavior:** For any skill invocation, attempt Skill tool first. If skill not registered, fall back to Read immediately — do NOT retry or report an error.

---

## Registration Rule

Only register high-frequency skills (<10 total) in the Skill tool manifest. The Read-based architecture is optimal for 250+ low-frequency skills.

Current registered skills are visible in the `<system-reminder>` block at session start under "Available skills:".

---

## Graceful Degradation — Retry-to-Next-Best-Skill Fallback Chain

When any tool call in a skill invocation fails (tool unavailable, MCP server disconnected, timeout, or `InputValidationError`), do NOT silently error or halt. Instead, walk the fallback chain below in order, stopping at the first option that succeeds.

### Failure Triggers

| Signal | Example |
|--------|---------|
| Skill tool returns error | "skill not found", "tool not registered" |
| MCP tool unavailable | server still connecting, `mcp__*` tool absent |
| Tool call denied by user | user rejects a permission prompt |
| Tool call times out | no response within reasonable window |

### Fallback Chain (ordered by preference)

```
1. Skill tool (if registered)
       ↓ fail
2. Read the skill file directly
   Read("~/.claude\skills\<path>.md")
       ↓ file not found or Read fails
3. Search for closest skill via Grep/Glob
   Grep(pattern=<keyword>, path="~/.claude\skills\")
   → pick highest-relevance match, Read it
       ↓ no match found
4. ToolSearch for a deferred MCP tool
   ToolSearch("select:<tool-name>") or keyword query
   → load schema, retry the original MCP call
       ↓ MCP still unavailable
5. Degrade gracefully — complete the task using only built-in tools
   (Read, Grep, Glob, Bash, Edit, Write)
       ↓ task truly cannot be completed without the missing tool
6. Surface a clear, specific error to the user:
   "Tool X is unavailable. Here's what I CAN do: [alternatives]."
   Never: silent failure, empty response, or vague "I can't do that."
```

### Scoring the Next-Best Option

When multiple fallback paths are viable at the same level, score them:

| Factor | Scoring note |
|--------|-------------|
| **Directness** | Fewer hops to the data = preferred |
| **Freshness** | Live MCP call > cached Read > reconstructed from memory |
| **Reliability** | Tool with working schema > tool schema not yet loaded |
| **Cost** | Free/local > API call > broad search scan |

Pick the highest-scoring option. Log the fallback choice in a brief inline comment so it's traceable.

### Example — MCP Server Not Yet Connected

```
Target: mcp__canvas__list_courses
Status: server still connecting (shown in system-reminder)

Chain walk:
  Step 1: Skill tool — not applicable (not a registered skill)
  Step 2: ToolSearch("LMS list courses") — triggers server wait + schema load
  Step 3: If server still unavailable after ToolSearch → degrade:
          Read LMS skill file for cached lookup strategy
  Step 4: Surface to user: "LMS MCP is connecting; retrying in a moment or
          use 'LMS' keyword to force a ToolSearch."
```

### Example — Skill File Moved or Renamed

```
Target: skills/integrations/client-context-detection.md (Read fails — not found)

Chain walk:
  Step 1: Glob("**/client-context*.md") → locate new path
  Step 2: Read the found path
  Step 3: Proceed normally
```

### Invariants

- **Never surface a raw tool error to the user without context.** Wrap it: "X failed — trying Y instead."
- **Never retry the identical failing call** without a schema load (ToolSearch) or path correction first.
- **Always complete the user's original intent** at some level, even if degraded. Partial completion with a clear note beats a dead stop.
