# Auto Context Anchor v1.0

> **Purpose:** Automatically create/update context-anchor.md on substantial tasks to survive compaction
> **Trigger:** Every substantial task start (3+ steps, multi-file, architectural)
> **Location:** `.claude/session/context-anchor.md`

## When to Update Context Anchor

**MANDATORY** on these events:
1. Substantial task starts (after gate output, before first action)
2. Major decision made (architectural choice, approach selected)
3. File modifications committed
4. Task phase changes (planning → implementation → testing)
5. Before spawning agents (capture current state)

## What to Capture

```markdown
# Context Anchor (Post-Compaction Recovery)

> **Purpose:** Preserve original task context through compaction cycles
> **Last Updated:** [timestamp]

## Original User Request

**Prompt:** "[Full verbatim prompt from state.json]"

**Goal:** [What user wants to achieve - one sentence]

**Success Criteria:** [Done when... - bullet list]
- [ ] Criterion 1
- [ ] Criterion 2

## Task Status

- **Current Phase:** [Planning / Implementation / Testing / Review / Blocked]
- **Last Action:** [What was just completed]
- **Next Action:** [What needs to happen next - be specific]
- **Blockers:** [None / List specific blockers]

## Files Modified

- `path/to/file.ext` - [Brief description of changes]

## Active Agents

- **Foreground:** [Agent names with task assignments]
- **Background:** scout, planner (auto-spawned)

## Decisions Made

- [Key decision 1 - why this approach]
- [Key decision 2 - alternatives considered]

## Context for Next Response

[1-2 sentence summary of where we are and what's happening next]

---

*This file is your lifeline after compaction. Read it FIRST before responding to anything.*
```

## Auto-Update Protocol

**Position #1 (After Gate, Before First Tool):**
```bash
# Silently update context anchor (no output to user)
python scripts/update-context-anchor.py \
  --prompt "$(jq -r '.current_prompt.text' session/state.json)" \
  --goal "[extracted goal]" \
  --phase "Planning" \
  --next-action "[specific next step]"
```

**After Major Events:**
- File written → Update "Files Modified" section
- Decision made → Update "Decisions Made" section
- Phase change → Update "Current Phase" and "Next Action"

## Recovery Flow (After Compaction)

When Claude comes back online after compaction:

1. **Sees:** `<task-notification>` for scout completion
2. **IGNORES IT** (per CLAUDE.md recovery protocol)
3. **Reads:** `session/context-anchor.md` FIRST
4. **Orients:** To original goal and next action
5. **Continues:** Work from where it left off
6. **NEVER:** Responds to background agent status

## Script: update-context-anchor.py

```python
#!/usr/bin/env python3
"""
Auto-update context anchor for post-compaction recovery
"""
import json
import sys
from pathlib import Path
from datetime import datetime
import argparse

def update_context_anchor(
    prompt: str,
    goal: str = None,
    phase: str = "Planning",
    last_action: str = None,
    next_action: str = None,
    files_modified: list = None,
    decisions: list = None,
    agents: dict = None
):
    """Update context anchor with current task state"""

    anchor_path = Path(".claude/session/context-anchor.md")

    # Read existing if present (to preserve decisions/files)
    existing_content = {}
    if anchor_path.exists():
        # Parse existing to preserve sections
        pass  # TODO: Implement smart merge

    # Build new content
    content = f"""# Context Anchor (Post-Compaction Recovery)

> **Purpose:** Preserve original task context through compaction cycles
> **Last Updated:** {datetime.now().isoformat()}

## Original User Request

**Prompt:** "{prompt}"

**Goal:** {goal or "[To be determined]"}

**Success Criteria:**
- [ ] [Add criteria as task progresses]

## Task Status

- **Current Phase:** {phase}
- **Last Action:** {last_action or "[None yet]"}
- **Next Action:** {next_action or "[To be determined]"}
- **Blockers:** None

## Files Modified

{chr(10).join(f'- `{f}` - [Changes]' for f in (files_modified or [])) or '- [No files modified yet]'}

## Active Agents

- **Foreground:** {agents.get('foreground', '[None]') if agents else '[None]'}
- **Background:** scout, planner (auto-spawned)

## Decisions Made

{chr(10).join(f'- {d}' for d in (decisions or [])) or '- [No decisions recorded yet]'}

## Context for Next Response

{goal or "Working on user request. See 'Next Action' for immediate next step."}

---

*This file is your lifeline after compaction. Read it FIRST before responding to anything.*
"""

    # Write anchor
    anchor_path.parent.mkdir(parents=True, exist_ok=True)
    anchor_path.write_text(content, encoding='utf-8')

    print(f"✅ Context anchor updated: {phase}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--prompt', required=True)
    parser.add_argument('--goal')
    parser.add_argument('--phase', default='Planning')
    parser.add_argument('--last-action')
    parser.add_argument('--next-action')
    parser.add_argument('--files', nargs='*')
    parser.add_argument('--decisions', nargs='*')

    args = parser.parse_args()

    update_context_anchor(
        prompt=args.prompt,
        goal=args.goal,
        phase=args.phase,
        last_action=args.last_action,
        next_action=args.next_action,
        files_modified=args.files,
        decisions=args.decisions
    )
```

## Integration Points

**Called by:**
- Position #1 in protocol-position-architecture.md (after gate, before first tool)
- conductor (before major decisions)
- guardian (before commits)
- Any agent before long-running operations

**Updates:**
- `session/context-anchor.md` (the recovery file)
- No user output (silent background operation)

---

*Context anchor v1.0 | Post-compaction recovery | Silent updates*
