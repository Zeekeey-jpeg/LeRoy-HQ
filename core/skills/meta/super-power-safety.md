# Super Power Safety Validator

**Version:** 1.0
**Purpose:** Enforce read-only boundaries for simulation framework
**Architecture:** Pre-execution validation with audit logging
**Last Updated:** 2026-01-18

---

## Critical Rule

```
+===========================================================================+
|                    SAFETY BOUNDARY ENFORCEMENT                            |
+===========================================================================+
|                                                                           |
|  EVERY tool call MUST be validated BEFORE execution.                     |
|  ONE violation = ENTIRE simulation FAILS.                                |
|  Zero tolerance policy.                                                  |
|                                                                           |
+===========================================================================+
```

---

## Validation Function (MANDATORY)

**Execute this BEFORE every tool call during simulation:**

```python
import re
import json
from datetime import datetime

def validate_tool_call(tool_name, params, audit_log_path="session/super_power/{date}/audit.log"):
    """
    Validates tool call against safety boundaries.

    Args:
        tool_name: Name of tool being called (e.g., "mcp__ticketing__update_opportunity")
        params: Dictionary of parameters for the tool call
        audit_log_path: Path to audit log file

    Returns:
        (is_allowed: bool, reason: str)

    Side Effects:
        - Logs to audit.log if blocked
        - Updates status.json with violation count
    """

    # BLOCKLIST PATTERNS (HARD-CODED - NO EXCEPTIONS)
    FORBIDDEN_OPS = [
        r".*_update_.*",     # All MCP update operations
        r".*_create_.*",     # All MCP create operations
        r".*_delete_.*",     # All MCP delete operations
        r"send_.*_message",  # Email sending (all accounts)
        r"draft_.*_message", # Email drafts
        r"git\s+(push|commit)", # Git write operations
        r"Edit",             # File editing tool
    ]

    # Check tool name against blocklist
    for pattern in FORBIDDEN_OPS:
        if re.match(pattern, tool_name, re.IGNORECASE):
            reason = f"BLOCKED: {tool_name} matches forbidden pattern: {pattern}"
            log_violation(tool_name, params, reason, audit_log_path)
            return False, reason

    # Special case: Write tool (only allowed to session/super_power/)
    if tool_name == "Write":
        file_path = params.get("file_path", "")
        if "session/super_power/" not in file_path and "session\\super_power\\" not in file_path:
            reason = f"BLOCKED: Write operation outside session/super_power/ directory: {file_path}"
            log_violation(tool_name, params, reason, audit_log_path)
            return False, reason

    # Check for production identifiers in params
    if contains_production_id(params):
        reason = f"BLOCKED: Production identifier detected in parameters"
        log_violation(tool_name, params, reason, audit_log_path)
        return False, reason

    # All checks passed
    log_allowed_operation(tool_name, audit_log_path)
    return True, "ALLOWED"

def contains_production_id(params):
    """
    Detect if parameters contain production identifiers.

    Returns:
        True if production ID found, False otherwise
    """
    # Convert params to string for scanning
    params_str = json.dumps(params).lower()

    # Production indicators
    PRODUCTION_INDICATORS = [
        "production",
        "live",
        "prod_",
        "master_",
        # Add known production IDs here if needed
    ]

    for indicator in PRODUCTION_INDICATORS:
        if indicator in params_str:
            return True

    return False

def log_violation(tool_name, params, reason, audit_log_path):
    """
    Logs blocked operation to audit log.

    Args:
        tool_name: Name of blocked tool
        params: Parameters that were blocked
        reason: Why it was blocked
        audit_log_path: Path to audit log
    """
    timestamp = datetime.utcnow().isoformat() + "Z"

    # Build log entry
    log_entry = {
        "timestamp": timestamp,
        "tool": tool_name,
        "params": params,
        "reason": reason,
        "status": "BLOCKED"
    }

    # Append to audit log
    with open(audit_log_path, "a") as f:
        f.write(json.dumps(log_entry) + "\n")

    # Update status.json violation count
    update_violation_count(audit_log_path)

    print(f"[SAFETY VIOLATION] {reason}")

def log_allowed_operation(tool_name, audit_log_path):
    """
    Logs allowed operation to audit log.

    Args:
        tool_name: Name of allowed tool
        audit_log_path: Path to audit log
    """
    timestamp = datetime.utcnow().isoformat() + "Z"

    log_entry = {
        "timestamp": timestamp,
        "tool": tool_name,
        "status": "ALLOWED"
    }

    with open(audit_log_path, "a") as f:
        f.write(json.dumps(log_entry) + "\n")

def update_violation_count(audit_log_path):
    """
    Updates status.json with current violation count.

    Args:
        audit_log_path: Path to audit log
    """
    # Read current audit log
    violations = 0
    try:
        with open(audit_log_path, "r") as f:
            for line in f:
                entry = json.loads(line)
                if entry.get("status") == "BLOCKED":
                    violations += 1
    except FileNotFoundError:
        violations = 0

    # Update status.json
    status_path = audit_log_path.replace("audit.log", "status.json")
    try:
        with open(status_path, "r") as f:
            status = json.load(f)
    except FileNotFoundError:
        status = {}

    if "safety" not in status:
        status["safety"] = {}

    status["safety"]["violations"] = violations

    with open(status_path, "w") as f:
        json.dump(status, f, indent=2)
```

---

## Allowlist (Read-Only Operations)

**These operations are ALWAYS allowed:**

```python
ALLOWED_OPS = [
    # MCP read operations
    r".*_search_.*",
    r".*_list_.*",
    r".*_get_.*",
    r".*_count_.*",

    # Web operations
    r"WebFetch",
    r"WebSearch",

    # File read operations
    r"Read",
    r"Grep",
    r"Glob",

    # Special: Write to session/super_power/ only
    r"Write",  # Validated separately

    # Task spawning (for parallel execution)
    r"Task",

    # Tool discovery
    r"MCPSearch",
]
```

**Validation Logic:**
1. Check if tool matches ALLOWED_OPS pattern
2. If tool is "Write", verify path contains "session/super_power/"
3. If neither matches allowlist nor blocklist, BLOCK by default (whitelist approach)

---

## Integration into Simulation Workflow

**Phase 1 (Scenario Generation):**
```python
# Before ANY tool call
for operation in scenario.operations:
    is_allowed, reason = validate_tool_call(operation.tool, operation.params)

    if not is_allowed:
        print(f"[SAFETY] Scenario {scenario.id} INVALID: {reason}")
        scenario.status = "INVALID"
        continue  # Skip this scenario, don't execute
```

**Phase 2 (Execution):**
```python
# Before executing each scenario
for step in scenario.steps:
    is_allowed, reason = validate_tool_call(step.tool, step.params)

    if not is_allowed:
        # FAIL the scenario immediately
        return {
            "scenario_id": scenario.id,
            "status": "FAIL",
            "error": reason,
            "runtime": 0
        }

    # Execute step (only if allowed)
    result = execute_tool(step.tool, step.params)
```

---

## Audit Log Format

**Location:** `session/super_power/{YYYY-MM-DD}/audit.log`

**Format:** JSONL (one JSON object per line)

**Entry Schema:**
```json
{
  "timestamp": "2026-01-18T10:15:32Z",
  "tool": "mcp__ticketing__update_opportunity",
  "params": {"id": 123, "status": "Won"},
  "reason": "BLOCKED: matches forbidden pattern: .*_update_.*",
  "status": "BLOCKED"
}
```

**Allowed Operation Entry:**
```json
{
  "timestamp": "2026-01-18T10:15:35Z",
  "tool": "mcp__ticketing__list_opportunities",
  "status": "ALLOWED"
}
```

---

## Violation Handling

**When violation detected:**

1. **Log to audit.log** - Record full details
2. **Update status.json** - Increment violation count
3. **Fail scenario** - Mark scenario as FAILED
4. **Continue execution** - Don't abort entire simulation
5. **Report violations** - Include in Phase 3 report

**Post-Simulation Review:**
```python
# After Phase 3, check violations
violations = count_violations("session/super_power/{date}/audit.log")

if violations > 0:
    print(f"[WARNING] {violations} safety violations detected during simulation")
    print(f"Review: session/super_power/{date}/audit.log")

    # Display violations in report
    report["safety_violations"] = violations
    report["audit_log"] = "session/super_power/{date}/audit.log"
```

---

## Production Identifier Detection

**Known Production Patterns:**
```python
PRODUCTION_PATTERNS = [
    "production",
    "prod_",
    "live",
    "master_",
    "_prod",
    "real_",
    "actual_",
]

# Check all param values (recursive)
def scan_params_for_production(obj):
    if isinstance(obj, str):
        return any(pattern in obj.lower() for pattern in PRODUCTION_PATTERNS)
    elif isinstance(obj, dict):
        return any(scan_params_for_production(v) for v in obj.values())
    elif isinstance(obj, list):
        return any(scan_params_for_production(item) for item in obj)
    return False
```

**Why this matters:**
- Even if tool is read-only, we don't want to query production data directly
- Simulation should use snapshots, cached data, or test environments
- Production queries could cause performance impact

---

## Validation Report (Included in Final Report)

**Section in report.md:**
```markdown
## SAFETY VALIDATION

- **Total Operations:** {N}
- **Allowed:** {M}
- **Blocked:** {violations}
- **Violation Rate:** {(violations / N) * 100}%

### Violation Details
{if violations > 0:}
  | Timestamp | Tool | Reason |
  |-----------|------|--------|
  | {timestamp} | {tool} | {reason} |

  **Action Required:** Review audit log for full details

{else:}
  ✅ Zero violations - All operations compliant with safety boundaries
```

---

## Testing Safety Boundaries

**Test Suite:**
```python
# Test 1: Block update operation
test_1 = validate_tool_call("mcp__ticketing__update_opportunity", {"id": 123})
assert test_1[0] == False, "Should block update operations"

# Test 2: Block create operation
test_2 = validate_tool_call("mcp__crm__create_deal", {"name": "Test"})
assert test_2[0] == False, "Should block create operations"

# Test 3: Block delete operation
test_3 = validate_tool_call("mcp__ticketing__delete_ticket", {"id": 456})
assert test_3[0] == False, "Should block delete operations"

# Test 4: Block email sending
test_4 = validate_tool_call("mcp__email-primary__send_gmail_message", {"to": "test@example.com"})
assert test_4[0] == False, "Should block email sending"

# Test 5: Block git push
test_5 = validate_tool_call("Bash", {"command": "git push origin main"})
assert test_5[0] == False, "Should block git push"

# Test 6: Block file edit
test_6 = validate_tool_call("Edit", {"file_path": "README.md", "old_string": "a", "new_string": "b"})
assert test_6[0] == False, "Should block file editing"

# Test 7: Block write outside session/super_power/
test_7 = validate_tool_call("Write", {"file_path": "~", "content": "x"})
assert test_7[0] == False, "Should block write outside session folder"

# Test 8: Allow write to session/super_power/
test_8 = validate_tool_call("Write", {"file_path": "session/super_power/2026-01-18/test.txt", "content": "x"})
assert test_8[0] == True, "Should allow write to session folder"

# Test 9: Allow read operations
test_9 = validate_tool_call("mcp__ticketing__list_opportunities", {})
assert test_9[0] == True, "Should allow list operations"

# Test 10: Allow search operations
test_10 = validate_tool_call("mcp__crm__search_deals", {"query": "test"})
assert test_10[0] == True, "Should allow search operations"

print("All safety boundary tests passed ✅")
```

---

## Error Messages (User-Facing)

**When simulation fails due to safety violation:**
```
[SIMULATION FAILED] Safety violation detected

Scenario: {scenario_id}
Operation: {tool_name}
Reason: {reason}

This simulation attempted to perform a write operation, which is forbidden.
Simulations are read-only to protect production systems.

Review audit log: session/super_power/{date}/audit.log
```

**When safety validation passes:**
```
[SAFETY] All {N} operations validated ✅
Audit log: session/super_power/{date}/audit.log (0 violations)
```

---

## Maintenance

**Weekly Review:**
- Check audit logs for patterns in blocked operations
- Update blocklist if new forbidden patterns discovered
- Review allowlist for any gaps

**After Each Simulation:**
- Verify audit.log shows 0 violations
- If violations found, investigate root cause
- Update safety validator if needed

---

## Integration with Report Template

**Safety section is MANDATORY in every report:**
- Shows violation count
- Links to audit log
- Pass/fail indicator
- Details on any blocked operations

**See:** `skills/meta/super-power-report-template.md` for full report structure

---

*Super Power Safety Validator v1.0 | Zero tolerance enforcement | Audit every operation*
