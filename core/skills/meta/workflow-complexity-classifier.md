# Workflow Complexity Classifier

> **Purpose:** Consistent complexity scoring across growth monitor and skill composer

## Scoring Algorithm

Count the following factors for each detected workflow:

| Factor | Points | Description |
|--------|--------|-------------|
| Tool calls (each) | +1 | Each MCP tool or system tool invoked |
| Data sources (unique) | +2 | Distinct data sources accessed (your CRM, ticketing, etc.) |
| Parameters required | +1 each | User-supplied variables (quarter, date range, etc.) |
| Conditional logic | +3 | If/then/else branching in workflow |
| External API calls | +2 | Non-MCP API calls |
| File I/O operations | +1 | Reads or writes to files |
| Multi-step dependencies | +2 | Steps that depend on prior step output |

## Complexity Thresholds

| Total Score | Complexity | Automation Threshold |
|-------------|------------|---------------------|
| 0-5 points | Simple | 2 uses |
| 6-12 points | Medium | 3 uses |
| 13+ points | Complex | 5 uses |

## Classification Function

```python
def classify_workflow_complexity(workflow):
    """
    Classify workflow complexity based on detected characteristics.

    Args:
        workflow: Dict with keys:
            - tool_calls: List of tool names used
            - data_sources: Set of unique data sources
            - parameters: List of parameter dicts
            - has_conditionals: bool
            - external_api_calls: int
            - file_io_count: int
            - dependent_steps: int

    Returns:
        Dict with keys:
            - score: int (total points)
            - complexity: str ("simple" | "medium" | "complex")
            - automation_threshold: int (2, 3, or 5)
    """
    score = 0

    # Tool calls: +1 each
    score += len(workflow.get("tool_calls", []))

    # Data sources: +2 each unique
    score += len(workflow.get("data_sources", set())) * 2

    # Parameters: +1 each
    score += len(workflow.get("parameters", []))

    # Conditional logic: +3
    if workflow.get("has_conditionals", False):
        score += 3

    # External API calls: +2 each
    score += workflow.get("external_api_calls", 0) * 2

    # File I/O: +1 each
    score += workflow.get("file_io_count", 0)

    # Multi-step dependencies: +2 each
    score += workflow.get("dependent_steps", 0) * 2

    # Classify based on score
    if score <= 5:
        complexity = "simple"
        automation_threshold = 2
    elif score <= 12:
        complexity = "medium"
        automation_threshold = 3
    else:
        complexity = "complex"
        automation_threshold = 5

    return {
        "score": score,
        "complexity": complexity,
        "automation_threshold": automation_threshold
    }
```

## Scoring Examples

### Example 1: Simple Workflow (4 points)

**Scenario:** your CRM deal count report

```yaml
workflow:
  tool_calls: ["crm_tool", "list_deals"]  # +2
  data_sources: ["crm"]  # +2
  parameters: []  # +0
  has_conditionals: false  # +0
  external_api_calls: 0  # +0
  file_io_count: 0  # +0
  dependent_steps: 0  # +0

Score: 4 points
Complexity: simple
Automation Threshold: 2 uses
```

### Example 2: Medium Workflow (8 points)

**Scenario:** Cross-system deal-to-opportunity sync

```yaml
workflow:
  tool_calls: ["crm_tool", "crm_tool", "ticketing_tool", "ticketing_tool"]  # +4
  data_sources: ["crm", "ticketing"]  # +4
  parameters: []  # +0
  has_conditionals: false  # +0
  external_api_calls: 0  # +0
  file_io_count: 0  # +0
  dependent_steps: 0  # +0

Score: 8 points
Complexity: medium
Automation Threshold: 3 uses
```

### Example 3: Complex Workflow (17 points)

**Scenario:** Quarterly report with email delivery

```yaml
workflow:
  tool_calls: ["crm_tool", "crm_tool", "ticketing_tool", "google_drive_upload", "google_send_mail", "supabase_insert"]  # +6
  data_sources: ["crm", "ticketing", "supabase"]  # +6
  parameters: [{name: "quarter"}, {name: "year"}]  # +2
  has_conditionals: true  # +3 (filter by deal stage)
  external_api_calls: 0  # +0
  file_io_count: 0  # +0
  dependent_steps: 0  # +0

Score: 17 points
Complexity: complex
Automation Threshold: 5 uses
```

## Data Source Detection

Map tool prefixes to data sources:

| Tool Prefix | Data Source |
|-------------|-------------|
| `mcp__crm__*` | crm |
| `mcp__ticketing__*` | ticketing |
| `mcp__bom__*` | catalog |
| `mcp__supabase__*` | supabase |
| `mcp__google__*` | google |
| `browser_*` | browser |

## Parameter Detection

Detect parameters from conversation context:

| Pattern | Parameter Name | Type |
|---------|---------------|------|
| `Q1`, `Q2`, `Q3`, `Q4` | quarter | string |
| `2024`, `2025`, `2026` | year | integer |
| Date ranges (`Jan 1 - Mar 31`) | date_range | object |
| Email addresses | recipient | string |
| Company names | company | string |
| Board names | board_name | string |

## Integration Points

**Called By:**
- `agents/scout.md` - During workflow pattern detection
- `skills/meta/skill-composer.md` - When generating automation from workflow

**Outputs:**
- Complexity classification (`simple` | `medium` | `complex`)
- Automation threshold (2, 3, or 5)
- Point breakdown for debugging

---

*Workflow Complexity Classifier v1.0 | Consistent scoring for growth detection and automation thresholds*
