# Skill Composer v2.0

> **Trigger keywords:** create skill, new skill, automate, generate skill

> **v2.0 UPDATES (2026-01-18):**
> - MANDATORY disambiguation (44% of requests need it)
> - MCP registry validation
> - Security blocklist enforcement
> - Template-based generation
> - Sandbox testing before registration
> - 10-step validation pipeline

---

## Context Budget Rule (MANDATORY — Step 0)

**Before generating any skill, classify its context budget type.**

This is Step 0 of the generation pipeline — before PARSE, DISAMBIGUATE, or anything else.

```yaml
Budget Classification Decision Tree:
  Does a user trigger this by keyword regularly?
    YES → Primary driver (no flag, counts toward budget)
    NO  → Background reference (user-invocable: false)

  Should it ONLY fire via explicit CLAUDE.md routing?
    YES → disable-model-invocation: true

  Does it spawn subagents?
    YES → add context: fork (combine with above)
```

**Auto-classification heuristics:**

| Request Pattern | Auto-Classification |
|----------------|---------------------|
| "Create a skill for [recurring task]" | Primary driver |
| "Create a reference for [knowledge]" | user-invocable: false |
| "Create an automation for [workflow]" | disable-model-invocation: true |
| "Create a skill that runs agents" | context: fork + primary or manual |

Add `user-invocable: false` or `disable-model-invocation: true` to the generated SKILL.md frontmatter automatically based on classification.

---

## Purpose

Generate working skills from natural language descriptions in <60 seconds with full validation and safety checks.

---

## When to Use

**ASK if:**
- User says "create skill for..."
- User wants to automate recurring workflow
- User describes trigger → action pattern
- User says "I need this to run automatically"
- Workflow automation offer accepted (suggestion engine threshold reached)

**DON'T USE if:**
- User asking about existing skills
- User wants to modify existing skill (use Edit instead)
- Request is for one-time execution (not automation)

## Input Sources

Skill composer accepts automation requests from three sources:

1. **Direct user request:** "Create a trigger for X"
2. **Growth monitor:** Pattern detected 3+ times
3. **Workflow automation offer (v2.1):** User accepts automation for tracked workflow

### NEW v2.1: Workflow-to-Skill Generation

When suggestion engine detects workflow hit automation threshold and user accepts:

**Input format from suggestion engine:**
```yaml
source: workflow_automation
workflow_id: crm-quarterly-new-clients
note_path: Claude/Patterns/your CRM-Quarterly-New-Clients-Report.md
workflow_metadata:
  complexity: simple
  tools_used:
    - mcp__crm__crm_tool
    - mcp__crm__list_deals
  parameters:
    - name: quarter
      type: string
      required: true
    - name: year
      type: integer
      default: 2026
  output:
    format: markdown
    recipients: ["you@example.com"]
    delivery_method: email
```

**Template selection for workflow automation:**
- If parameters exist AND scheduled recurrence → `conditional-routing.yaml` (prompt user for params, then execute)
- If scheduled recurrence (no params) → `simple-trigger.yaml` (cron schedule)
- If multi-step with dependencies → `multi-step-workflow.yaml`

**Workflow automation process:**
1. Read workflow pattern note from vault
2. Extract tool sequence from note content
3. Map parameters to skill input prompts
4. Generate skill file using appropriate template
5. Register trigger in CLAUDE.md Quick Triggers table
6. Update workflow catalog: `automated = true`, `automated_skill_path = {path}`

**Example generation:**
```yaml
# Generated from workflow_automation source
name: "crm-quarterly-report"
description: "Quarterly your CRM new clients report (auto-generated from workflow)"
version: "1.0"
source: workflow_automation
original_workflow: "Claude/Patterns/your CRM-Quarterly-New-Clients-Report.md"

trigger:
  type: "keyword"
  patterns: ["quarterly crm", "q1 report", "q2 report", "q3 report", "q4 report"]

parameters:
  - name: quarter
    prompt: "Which quarter? (Q1, Q2, Q3, Q4)"
    type: string
    required: true
  - name: year
    prompt: "Which year?"
    type: integer
    default: 2026

action:
  - tool: mcp__crm__crm_tool
    params:
      filters: "createdate >= {quarter_start} AND createdate <= {quarter_end}"
      limit: 200
  - format: markdown
  - deliver: email
    to: you@example.com

tags: [routines, crm]
```

---

## 10-Step Generation Pipeline

### Step 1: PARSE

Extract components from natural language:
- **Trigger:** When should this run?
- **Action:** What should it do?
- **Target:** What systems/files/data?

**Example:**
```
User: "send crm report to Scott every Friday 5pm"

Parsed:
- Trigger: "Friday 5pm" (schedule)
- Action: "send report" (email delivery)
- Target: "crm report to Scott" (your CRM data → email)
```

**Output:** `session/skill-composer-parse.json`

### Step 2: DISAMBIGUATE (BLOCKING - MANDATORY)

**CRITICAL:** Call `request-disambiguation.md` if ANY ambiguity detected.

**Ambiguity triggers (44% of requests):**
- Unclear target: "send to team" → Which team? What email addresses?
- Multiple interpretations: "create report" → Which report type?
- Missing parameters: "every Friday" → What time? Which timezone?
- System ambiguity: "deals" → your CRM or your CRM opportunities?
- Credential ambiguity: "google calendar" → your organization, your org, or Personal account?

**BLOCKS EXECUTION** until user provides clarification.

**Integration:**
```markdown
Load skills/meta/request-disambiguation.md
Ask user with 2-4 specific options
Record selection in session/prediction-state.json
Set "disambiguation_completed": true
Continue to Step 3 only after confirmation
```

**Example:**
```
Claude: "Which system should I use for 'deals'?

[1] your CRM (CRM deals)
[2] your CRM (opportunities)
[3] Other - specify"

User: "1"

Claude: [Records choice, continues to Step 3]
```

### Step 3: VALIDATE_MCP

Check MCP tools exist and are configured correctly.

**Process:**
1. Read `session/mcp-registry.json` (use Grep with head_limit to avoid token burn)
2. Extract tool names from parsed action
3. Verify tools exist in registry
4. Verify required parameters are available
5. Check pagination config if querying data

**Example:**
```yaml
Action requires: mcp__crm__crm_tool

Validation:
✅ Tool exists in registry
✅ Required params: filters, limit
✅ Pagination: limit=200 (max page size)
✅ Auto-approved (no user prompt needed)
```

**FAIL if:**
- Tool not in registry → Ask user which MCP server to use
- Tool requires params not in request → Ask for params
- Tool is deprecated → Suggest alternative

**Output:** `session/skill-composer-mcp-validation.json`

### Step 4: GENERATE

Use templates from `.claude/skills/templates/` for slot-filling.

**Template Selection:**
| Pattern | Template | Use For |
|---------|----------|---------|
| Scheduled action | `simple-trigger.yaml` | "every Friday 5pm do X" |
| Sequential steps | `multi-step-workflow.yaml` | "fetch X, then process Y, then send Z" |
| Conditional logic | `conditional-routing.yaml` | "if X then Y else Z" |

**Slot-Filling Process:**
```yaml
# Example: simple-trigger.yaml filled
name: "crm-weekly-report"
description: "Send your CRM report to Scott every Friday 5pm"
version: "1.0"
# Context budget: primary driver (user says "crm weekly" to trigger)
# context: fork  # uncomment if spawning subagents

trigger:
  type: "schedule"
  pattern: "0 17 * * 5"  # cron: Friday 5pm

action:
  tool: "mcp__crm__crm_tool"
  params:
    filters: "dealstage=closedwon"
    limit: 200

output:
  format: "markdown"
  destination: "email:you@example.com"

tags: [integrations, crm, automation]
```

**Advanced Features:**
- Multi-step workflows support error handling (continue/fail/retry)
- Conditional routing supports nested conditions
- All templates support environment variable substitution

**Output:** Generated skill YAML in memory

### Step 5: VALIDATE_SYNTAX

Run syntax validation based on skill type.

**Python Skills (.py):**
```python
import ast
try:
    ast.parse(generated_code)
    validation_passed = True
except SyntaxError as e:
    log_error(f"Syntax error at line {e.lineno}: {e.msg}")
    validation_passed = False
```

**YAML Skills (.yaml):**
```python
import yaml
try:
    yaml.safe_load(generated_yaml)
    validation_passed = True
except yaml.YAMLError as e:
    log_error(f"YAML error: {e}")
    validation_passed = False
```

**Markdown Skills (.md):**
```python
import frontmatter
try:
    post = frontmatter.load(generated_md)
    assert 'trigger' in post.metadata
    assert 'action' in post.metadata
    validation_passed = True
except Exception as e:
    log_error(f"Frontmatter error: {e}")
    validation_passed = False
```

**FAIL if:** Syntax errors detected → Show error, offer to fix and retry

**Output:** Validation log in `session/skill-composer-validation.log`

### Step 6: VALIDATE_SECURITY

Scan generated content for credential exposure and dangerous operations.

**Process:**
1. Read `session/security-blocklist.json`
2. Scan generated skill for blocklist patterns
3. Check severity level
4. Fail CRITICAL, warn HIGH, log MEDIUM

**Blocklist Categories:**

**CRITICAL - FAIL IMMEDIATELY:**
```python
credential_patterns = [
    "api_key", "apikey", "api-key",
    "password", "passwd", "pwd",
    "secret", "secret_key",
    "token", "access_token", "bearer",
    "auth", "authorization",
    "credential", "credentials"
]
```

**HIGH - WARN AND CONFIRM:**
```python
dangerous_operations = [
    "rm -rf", "del /f",
    "DROP TABLE", "DELETE FROM",
    "eval(", "exec(",
    "system(", "shell_exec"
]
```

**Safe Patterns (Allowed):**
```yaml
# Environment variable references (GOOD)
api_key: "${CRM_API_KEY}"

# Config file references (GOOD)
credentials_file: "~/.config/leroy/credentials.json"

# MCP tool calls (GOOD - credentials managed by MCP)
tool: "mcp__crm__crm_tool"
```

**Example Scan:**
```python
# FAIL - hardcoded credential
action:
  headers:
    Authorization: "Bearer sk-1234567890abcdef"

# PASS - environment variable
action:
  headers:
    Authorization: "${CRM_TOKEN}"
```

**Output:** Security scan results in `session/skill-composer-security.json`

### Step 7: VALIDATE_TAGS

Check tags against whitelist and auto-correct if possible.

**Valid Tag Categories:**
```python
valid_categories = [
    "integrations", "routines", "workflows",
    "domains", "stacks", "tooling", "meta"
]

valid_software = [
    "ticketing", "crm", "catalog", "bim", "android",
    "git", "netlify", "playwright", "supabase", "gas",
    "python", "memory-system", "enforcement", "leroy"
]
```

**Tag Rules:**
1. Max 4 tags total
2. First tag SHOULD be category (auto-add if missing)
3. Remaining tags SHOULD be software/integration
4. NO descriptive tags (bulletproof, successful, critical, etc.)
5. NO version tags (v5, v5.1, etc.)

**Auto-Correction Examples:**
```yaml
# INPUT (invalid)
tags: [automation, validation, critical]

# OUTPUT (corrected)
tags: [workflows, crm]

# INPUT (invalid - no category)
tags: [crm, ticketing]

# OUTPUT (corrected)
tags: [integrations, crm, ticketing]
```

**FAIL if:** Tags cannot be auto-corrected → Ask user for category

**Output:** Corrected tags in skill metadata

### Step 8: VALIDATE_DEPS

Build dependency graph and check for cycles/missing dependencies.

**Process:**
1. Extract skill dependencies from generated skill
2. Build directed graph
3. Check for circular dependencies (DFS cycle detection)
4. Check for missing skill files
5. Enforce max depth = 3

**Example:**
```yaml
# Generated skill depends on:
depends_on:
  - skills/integrations/crm/search-deals.md
  - skills/tooling/email-sender.md

Dependency Graph:
  crm-weekly-report
    ├── search-deals.md (depth 1)
    └── email-sender.md (depth 1)
        └── smtp-config.md (depth 2)

Validation:
✅ No cycles detected
✅ All dependencies exist
✅ Max depth = 2 (within limit of 3)
```

**FAIL if:**
- Circular dependency detected → Show cycle, ask user to resolve
- Missing dependency → Ask if should create or remove reference
- Depth > 3 → Suggest flattening or removing deep dependency

**Output:** Dependency graph in `session/skill-composer-deps.json`

### Step 9: SANDBOX_TEST

Execute skill in isolated environment with strict limits.

**Sandbox Configuration:**
```python
sandbox_config = {
    "timeout": 30,  # seconds
    "allow_file_write": False,
    "allow_network": False,
    "allow_subprocess": False,
    "env_vars": {
        # Only safe test values
        "TEST_MODE": "true"
    }
}
```

**Test Process:**
1. Create temporary sandbox directory
2. Copy skill + dependencies
3. Mock external services (MCP tools, APIs)
4. Execute skill with test inputs
5. Capture stdout, stderr, errors
6. Validate expected outputs
7. Clean up sandbox

**Example:**
```python
# Sandbox execution
try:
    result = execute_in_sandbox(
        skill_path="temp/crm-weekly-report.yaml",
        inputs={"test_mode": True},
        timeout=30
    )

    # Validate outputs
    assert result.status == "success"
    assert "you@example.com" in result.outputs

    sandbox_passed = True
except TimeoutError:
    log_error("Skill execution timeout (>30s)")
    sandbox_passed = False
except AssertionError as e:
    log_error(f"Output validation failed: {e}")
    sandbox_passed = False
```

**FAIL if:**
- Execution timeout (>30s)
- Runtime errors
- Missing expected outputs
- Unexpected file/network access

**Output:** Sandbox test results in `session/skill-composer-sandbox.log`

### Step 10: REGISTER

Add skill to system and update CLAUDE.md.

**Registration Steps:**

1. **Choose Skill Location:**
```python
# Map category to folder
category_to_folder = {
    "integrations": "skills/integrations/{software}/",
    "routines": "routines/",
    "workflows": "skills/workflows/",
    "domains": "skills/domains/{domain}/",
}

# Example: tags=[integrations, crm]
# Location: skills/integrations/crm/crm-weekly-report.yaml
```

2. **Write Skill File:**
```python
skill_path = f"{base_folder}/{skill_name}.yaml"
write_file(skill_path, generated_content)
```

3. **Update CLAUDE.md Quick Triggers:**
```markdown
# Add to Quick Triggers table if trigger is keyword-based
| "crm weekly" | your CRM weekly report to Scott | `skills/integrations/crm/crm-weekly-report.yaml` |
```

4. **Update Skill Routing Index:**
```markdown
# Add to appropriate skills/*/index.md
- `crm-weekly-report.yaml` - Auto-generated weekly report sender
```

5. **Create Git Commit:**
```bash
git add {skill_path} .claude/CLAUDE.md skills/integrations/crm/index.md
git commit -m "Skill: crm-weekly-report - Auto-generated

Generated from natural language: 'send crm report to Scott every Friday 5pm'

Components:
- Trigger: Schedule (cron: 0 17 * * 5)
- Action: your CRM search + email send
- Output: Markdown report to you@example.com

Tags: [integrations, crm, automation]
Validated: syntax, security, dependencies, sandbox

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

6. **Update Workflow Catalog (for workflow_automation source only):**
```python
# If skill was generated from workflow automation offer
if source == "workflow_automation":
    catalog_path = ".claude/session/workflow-catalog.json"

    with open(catalog_path, 'r') as f:
        catalog = json.load(f)

    for workflow in catalog["workflows"]:
        if workflow["id"] == workflow_id:
            workflow["automated"] = True
            workflow["automated_skill_path"] = skill_path
            workflow["automated_at"] = datetime.utcnow().isoformat() + "Z"
            break

    catalog["last_updated"] = datetime.utcnow().isoformat() + "Z"

    with open(catalog_path, 'w') as f:
        json.dump(catalog, f, indent=2)
```

**Output:** Skill registered and committed

---

## Safety Mechanisms

```yaml
mandatory_checks:
  disambiguation_required: true  # BLOCKS on ambiguity
  mcp_validation: true
  syntax_validation: true
  security_validation: true
  dependency_validation: true
  sandbox_test: true

limits:
  dependency_depth_limit: 3
  sandbox_timeout: 30  # seconds
  generation_timeout: 60  # seconds

blocklists:
  credentials:
    - api_key, password, secret, token, bearer, auth
  operations:
    - rm -rf, DROP TABLE, eval(, exec(
```

---

## Success Metrics

**Targets (from simulation report):**
- Generation success rate: >90%
- Generation time: <60 seconds
- Disambiguation rate: <30% (baseline: 44%)
- User adoption: 3+ skills/week

**Tracking:**
```json
{
  "total_generations": 127,
  "successful": 115,
  "failed_validation": 8,
  "failed_sandbox": 4,
  "success_rate": 90.6,
  "avg_generation_time_sec": 42,
  "disambiguation_rate": 28.3
}
```

---

## Integration Points

**Called By:**
- User via "create skill" trigger
- Agent teams for workflow automation
- LeRoy factory for report generation

**Calls:**
- `skills/meta/request-disambiguation.md` (Step 2)
- `session/mcp-registry.json` (Step 3)
- `skills/templates/*.yaml` (Step 4)
- `session/security-blocklist.json` (Step 6)

**Outputs:**
- New skill file in appropriate folder
- Updated CLAUDE.md Quick Triggers
- Updated skill routing index
- Git commit with full context

---

## Error Recovery

**Common Failures:**

| Error | Cause | Recovery |
|-------|-------|----------|
| Ambiguous intent | User request unclear | Ask disambiguation questions |
| MCP tool missing | Tool not in registry | Suggest alternative or manual fallback |
| Syntax error | Template bug or edge case | Show error, offer to fix and retry |
| Security violation | Credential in generated code | Block, explain issue, regenerate |
| Sandbox timeout | Infinite loop or slow operation | Analyze logic, optimize or fail |
| Dependency cycle | Circular reference | Show cycle, ask user to resolve |

**Escalation:**
- If 2+ retries fail → Escalate to @agent-conductor
- If security violation persists → Halt and require manual review
- If user cancels disambiguation → Abort generation

---

## Examples

### Example 1: Simple Schedule

**User:** "Send me a your CRM ticket summary every Monday 9am"

**Pipeline:**
1. PARSE: Trigger=schedule, Action=ticket summary, Target=ticketing tickets → email
2. DISAMBIGUATE: Which email? → you@example.com
3. VALIDATE_MCP: mcp__ticketing__ticketing_tool exists ✅
4. GENERATE: Use simple-trigger.yaml
5. VALIDATE_SYNTAX: YAML valid ✅
6. VALIDATE_SECURITY: No credentials ✅
7. VALIDATE_TAGS: [routines, ticketing] ✅
8. VALIDATE_DEPS: No dependencies ✅
9. SANDBOX_TEST: Executes in 3s ✅
10. REGISTER: routines/ticketing-monday-summary.yaml

**Time:** 38 seconds

### Example 2: Multi-Step Workflow

**User:** "When a deal closes in your CRM, create a project in your CRM and send me confirmation"

**Pipeline:**
1. PARSE: Trigger=event, Action=multi-step, Target=your CRM deal → ticketing project → email
2. DISAMBIGUATE: Which deal stage = "closed"? → closedwon
3. VALIDATE_MCP: crm_tool, ticketing_tool exist ✅
4. GENERATE: Use multi-step-workflow.yaml (3 steps)
5. VALIDATE_SYNTAX: YAML valid ✅
6. VALIDATE_SECURITY: No credentials ✅
7. VALIDATE_TAGS: [workflows, crm, ticketing] ✅
8. VALIDATE_DEPS: Depends on email-sender.md (depth 1) ✅
9. SANDBOX_TEST: Executes in 12s ✅
10. REGISTER: skills/workflows/crm-to-ticketing-sync.yaml

**Time:** 54 seconds

### Example 3: Conditional Routing

**User:** "If ticket priority is high, assign to Scott, otherwise assign to team queue"

**Pipeline:**
1. PARSE: Trigger=ticket create, Action=conditional, Target=ticketing ticket assignment
2. DISAMBIGUATE: Which your CRM board? → Service Board
3. VALIDATE_MCP: ticketing_tool, ticketing_tool exist ✅
4. GENERATE: Use conditional-routing.yaml
5. VALIDATE_SYNTAX: YAML valid ✅
6. VALIDATE_SECURITY: No credentials ✅
7. VALIDATE_TAGS: [workflows, ticketing] ✅
8. VALIDATE_DEPS: No dependencies ✅
9. SANDBOX_TEST: Executes in 5s ✅
10. REGISTER: skills/workflows/priority-ticket-routing.yaml

**Time:** 41 seconds

---

## Templates

Templates located in `.claude/skills/templates/`:
- `simple-trigger.yaml` - Scheduled or keyword triggers
- `multi-step-workflow.yaml` - Sequential actions with error handling
- `conditional-routing.yaml` - If/then logic with branching

See template files for full structure and slot definitions.

---

**Rule:** NEVER skip disambiguation or security validation. Speed is secondary to correctness.

---

*Skill Composer v2.1 | Context Budget Step 0 added (2026-03-12) | Success rate: 90%+*
