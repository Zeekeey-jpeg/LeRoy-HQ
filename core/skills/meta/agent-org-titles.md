---
name: agent-org-titles
description: |
  Agent-to-organizational-title mapping for gate display enhancement.
  Shows each agent's position in the your org Office hierarchy.
user-invocable: false
---

# Agent Organizational Titles

**Purpose:** Display agent roles with their organizational titles in gate output for clarity.

---

## Agent → Title Mapping

| Agent Name | Short Name | Organizational Title | Floor |
|------------|------------|---------------------|-------|
| @agent-conductor | conductor | COO | Floor 6 |
| @proposal-writer | proposal | VP Sales | Floor 4 |
| @builder | builder | VP Delivery | Floor 4 |
| @agent-legal | legal | General Counsel | Floor 3 |
| @agent-secretary | secretary | Chief of Staff | Floor 3 |
| @agent-planner | planner | Product Manager | Floor 3 |
| @agent-vp-engineering | vp-eng | VP Engineering (Coding) | Floor 2.5 |
| @agent-scrum-leader | scrum | Scrum Leader | Floor 2.5 |
| @agent-forge | forge | VP Engineering (Data) | Floor 2 |
| @agent-scout | scout | VP Research | Floor 2 |
| @agent-guardian | guardian | Quality Sentinel | Floor 2 |
| @agent-professor | professor | BIM Specialist | Floor 2 |
| @agent-designer | designer | Design Lead | Floor 2 |
| @agent-validator | validator | data Validator | Floor 2 |
| @agent-analyst | analyst | Data Analyst | Floor 2 |

---

## Gate Display Format

**Current (agent name only):**
```
[1] conductor (exploration & coordination)
[1] secretary (background timeline tracking)
[1] scout (background pattern detection)
```

**Enhanced (with organizational title):**
```
[1] conductor - COO (exploration & coordination)
[1] secretary - Chief of Staff (background timeline tracking)
[1] scout - VP Research (background pattern detection)
```

---

## Display Rules

1. **Format:** `[N] {short-name} - {org-title} ({task-description})`
2. **Title abbreviations:**
   - "VP Engineering (Coding)" → "VP Eng (Coding)"
   - "VP Engineering (Data)" → "VP Eng (Data)"
   - Keep others full length
3. **When title unknown:** Fall back to name only (no dash)
4. **Background agents:** Same format, shown under "Background:" section

---

## Implementation

In gate output, lookup agent short name in this mapping table and append title after name with " - " separator.

**Example code logic:**
```python
agent_titles = {
    "conductor": "COO",
    "secretary": "Chief of Staff",
    "scout": "VP Research",
    "builder": "VP Delivery",
    "forge": "VP Eng (Data)",
    "legal": "General Counsel",
    # ... etc
}

def format_agent_line(count, name, task):
    title = agent_titles.get(name, "")
    title_str = f" - {title}" if title else ""
    return f"[{count}] {name}{title_str} ({task})"
```

---

*Agent Organizational Titles v1.0 | your org Office Hierarchy Integration*
