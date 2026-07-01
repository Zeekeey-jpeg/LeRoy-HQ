# Dual-List Safety Pattern

**Version:** 1.0
**Type:** Meta-Skill (Design Pattern)
**Purpose:** Standardize blocklist + allowlist validation for safety-critical operations
**Last Updated:** 2026-01-18

---

## Pattern Overview

**The Rule:** ALL safety validation uses BOTH blocklist AND allowlist. Not one or the other.

This pattern ensures:
- Explicit forbidden operations (blocklist)
- Explicit allowed operations (allowlist)
- Default-deny for anything not in allowlist
- Zero-tolerance enforcement
- Audit trail for all decisions

---

## Why Two Lists?

**Blocklist alone is insufficient:**
- Cannot anticipate all dangerous operations
- Easy to miss edge cases
- Default-allow is unsafe

**Allowlist alone is insufficient:**
- Hard to express all valid operations
- Overly restrictive
- Legitimate operations may be blocked

**Together they provide defense-in-depth:**
1. Blocklist catches known dangerous operations (HIGH confidence blocks)
2. Allowlist catches everything else (default-deny for unknown operations)
3. Audit log records all decisions

---

## Core Components

### 1. Blocklist (Forbidden Operations)
**Purpose:** Explicitly block known dangerous operations

**Structure:**
```python
BLOCKLIST = [
    r".*_update_.*",     # MCP update operations
    r".*_create_.*",     # MCP create operations
    r".*_delete_.*",     # MCP delete operations
    r"send_.*_message",  # Email sending
    r"git\s+(push|commit)", # Git write operations
    r"Edit",             # File editing
    r"rm\s+-rf",         # Dangerous shell commands
    r"DROP\s+TABLE",     # SQL destructive operations
]
```

**Pattern rules:**
- Use regex for flexibility
- Case-insensitive matching
- Broad patterns (e.g., `.*_update_.*` catches ALL update operations)
- Document why each pattern is forbidden

### 2. Allowlist (Permitted Operations)
**Purpose:** Explicitly allow safe operations

**Structure:**
```python
ALLOWLIST = [
    r".*_search_.*",     # MCP search operations
    r".*_list_.*",       # MCP list operations
    r".*_get_.*",        # MCP get operations
    r".*_count_.*",      # MCP count operations
    r"WebFetch",         # Web reading
    r"WebSearch",        # Web searching
    r"Read",             # File reading
    r"Grep",             # File searching
    r"Glob",             # File pattern matching
]
```

**Pattern rules:**
- Use regex for flexibility
- Case-insensitive matching
- Broad patterns for categories of safe operations
- Document what each pattern enables

### 3. Validation Function
**Purpose:** Check operation against both lists

**Logic flow:**
```
1. Check blocklist FIRST
   - If matches: BLOCK immediately (HIGH confidence)
   - Log to audit: "BLOCKED by blocklist: {pattern}"

2. Check allowlist SECOND
   - If matches: ALLOW
   - Log to audit: "ALLOWED by allowlist: {pattern}"

3. If neither matches: BLOCK by default
   - Log to audit: "BLOCKED by default-deny: not in allowlist"
```

**Implementation:**
```python
def validate_operation(tool_name, params, audit_log_path):
    """
    Validates operation against blocklist and allowlist.

    Args:
        tool_name: Name of tool being called
        params: Parameters for the tool call
        audit_log_path: Path to audit log file

    Returns:
        (is_allowed: bool, reason: str)

    Side Effects:
        - Logs decision to audit log
        - Updates violation count if blocked
    """
    import re

    # STEP 1: Check blocklist (HIGH priority blocks)
    for pattern in BLOCKLIST:
        if re.match(pattern, tool_name, re.IGNORECASE):
            reason = f"BLOCKED by blocklist: {tool_name} matches {pattern}"
            log_blocked(tool_name, params, reason, audit_log_path)
            return False, reason

    # STEP 2: Check allowlist
    for pattern in ALLOWLIST:
        if re.match(pattern, tool_name, re.IGNORECASE):
            reason = f"ALLOWED by allowlist: {tool_name} matches {pattern}"
            log_allowed(tool_name, reason, audit_log_path)
            return True, reason

    # STEP 3: Default deny (not in allowlist)
    reason = f"BLOCKED by default-deny: {tool_name} not in allowlist"
    log_blocked(tool_name, params, reason, audit_log_path)
    return False, reason
```

---

## Special Case Handling

### Write Operations (Restricted Paths)
**Pattern:** Allow Write tool ONLY to specific directories

```python
def validate_write_operation(file_path, audit_log_path):
    """
    Special validation for Write tool.

    Allowed paths:
    - session/super_power/ (simulation outputs)
    - session/temp/ (temporary files)

    Forbidden:
    - All other paths
    """
    ALLOWED_WRITE_PATHS = [
        "session/super_power/",
        "session\\super_power\\",  # Windows path
        "session/temp/",
        "session\\temp\\",
    ]

    # Check if path contains any allowed prefix
    for allowed_path in ALLOWED_WRITE_PATHS:
        if allowed_path in file_path:
            reason = f"ALLOWED: Write to {file_path} (matches {allowed_path})"
            log_allowed("Write", reason, audit_log_path)
            return True, reason

    # Block all other write paths
    reason = f"BLOCKED: Write to {file_path} (outside allowed directories)"
    log_blocked("Write", {"file_path": file_path}, reason, audit_log_path)
    return False, reason
```

**Integration into main validator:**
```python
def validate_operation(tool_name, params, audit_log_path):
    # ... blocklist check ...

    # Special case: Write tool
    if tool_name == "Write":
        file_path = params.get("file_path", "")
        return validate_write_operation(file_path, audit_log_path)

    # ... allowlist check ...
```

### Parameter Scanning (Production Identifiers)
**Pattern:** Block operations with production identifiers in params

```python
def contains_production_id(params):
    """
    Scan parameters for production identifiers.

    Returns:
        True if production ID found, False otherwise
    """
    import json

    params_str = json.dumps(params).lower()

    PRODUCTION_INDICATORS = [
        "production",
        "prod_",
        "live",
        "master_",
        "_prod",
        "real_",
        "actual_",
    ]

    for indicator in PRODUCTION_INDICATORS:
        if indicator in params_str:
            return True

    return False
```

**Integration into main validator:**
```python
def validate_operation(tool_name, params, audit_log_path):
    # ... blocklist check ...
    # ... allowlist check ...

    # Check for production identifiers
    if contains_production_id(params):
        reason = f"BLOCKED: Production identifier detected in parameters"
        log_blocked(tool_name, params, reason, audit_log_path)
        return False, reason

    # ... final allow/deny ...
```

---

## Audit Logging

### Log Format
**Location:** `{audit_log_path}` (framework-specific)

**Format:** JSONL (one JSON object per line)

**Entry Schema:**
```json
{
  "timestamp": "2026-01-18T10:15:32Z",
  "tool": "mcp__ticketing__update_opportunity",
  "params": {"id": 123, "status": "Won"},
  "decision": "BLOCKED",
  "reason": "BLOCKED by blocklist: matches .*_update_.*",
  "list": "blocklist"
}
```

**Allowed operation entry:**
```json
{
  "timestamp": "2026-01-18T10:15:35Z",
  "tool": "mcp__ticketing__list_opportunities",
  "decision": "ALLOWED",
  "reason": "ALLOWED by allowlist: matches .*_list_.*",
  "list": "allowlist"
}
```

**Default-deny entry:**
```json
{
  "timestamp": "2026-01-18T10:15:40Z",
  "tool": "unknown_tool",
  "params": {},
  "decision": "BLOCKED",
  "reason": "BLOCKED by default-deny: not in allowlist",
  "list": "default-deny"
}
```

### Log Implementation
```python
import json
from datetime import datetime

def log_blocked(tool, params, reason, audit_log_path):
    """Log blocked operation."""
    entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "tool": tool,
        "params": params,
        "decision": "BLOCKED",
        "reason": reason,
        "list": extract_list_from_reason(reason)
    }
    append_to_log(entry, audit_log_path)
    update_violation_count(audit_log_path)

def log_allowed(tool, reason, audit_log_path):
    """Log allowed operation."""
    entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "tool": tool,
        "decision": "ALLOWED",
        "reason": reason,
        "list": "allowlist"
    }
    append_to_log(entry, audit_log_path)

def append_to_log(entry, audit_log_path):
    """Append entry to audit log file."""
    with open(audit_log_path, "a") as f:
        f.write(json.dumps(entry) + "\n")

def extract_list_from_reason(reason):
    """Extract which list caused the decision."""
    if "blocklist" in reason.lower():
        return "blocklist"
    elif "allowlist" in reason.lower():
        return "allowlist"
    elif "default-deny" in reason.lower():
        return "default-deny"
    else:
        return "unknown"
```

---

## Violation Handling

### When Violation Detected
```python
def handle_violation(tool_name, params, reason, audit_log_path):
    """
    Handle safety violation.

    Actions:
    1. Log to audit log
    2. Update violation count in status file
    3. Print error message
    4. Fail operation (return error to caller)
    """
    # Log violation
    log_blocked(tool_name, params, reason, audit_log_path)

    # Update status file
    update_violation_count(audit_log_path)

    # Print error
    print(f"[SAFETY VIOLATION] {reason}")

    # Return error to caller
    return {
        "status": "BLOCKED",
        "reason": reason,
        "tool": tool_name
    }
```

### Violation Count Tracking
```python
def update_violation_count(audit_log_path):
    """
    Update status.json with current violation count.

    Reads audit log, counts BLOCKED entries, updates status file.
    """
    # Count violations in audit log
    violations = 0
    try:
        with open(audit_log_path, "r") as f:
            for line in f:
                entry = json.loads(line)
                if entry.get("decision") == "BLOCKED":
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
    status["safety"]["last_updated"] = datetime.utcnow().isoformat() + "Z"

    with open(status_path, "w") as f:
        json.dump(status, f, indent=2)
```

---

## Testing Safety Boundaries

### Test Suite
```python
def test_dual_list_safety():
    """Comprehensive test suite for dual-list pattern."""

    audit_log = "session/test/audit.log"

    # Test 1: Blocklist blocks update operations
    result, reason = validate_operation("mcp__ticketing__update_opportunity", {}, audit_log)
    assert result == False, "Should block update operations"
    assert "blocklist" in reason.lower()

    # Test 2: Blocklist blocks create operations
    result, reason = validate_operation("mcp__crm__create_deal", {}, audit_log)
    assert result == False, "Should block create operations"
    assert "blocklist" in reason.lower()

    # Test 3: Allowlist allows search operations
    result, reason = validate_operation("mcp__crm__search_deals", {}, audit_log)
    assert result == True, "Should allow search operations"
    assert "allowlist" in reason.lower()

    # Test 4: Allowlist allows list operations
    result, reason = validate_operation("mcp__ticketing__list_opportunities", {}, audit_log)
    assert result == True, "Should allow list operations"
    assert "allowlist" in reason.lower()

    # Test 5: Default-deny blocks unknown operations
    result, reason = validate_operation("unknown_tool", {}, audit_log)
    assert result == False, "Should block unknown operations"
    assert "default-deny" in reason.lower()

    # Test 6: Write to allowed path
    result, reason = validate_operation("Write", {"file_path": "session/super_power/test.txt"}, audit_log)
    assert result == True, "Should allow write to session/super_power/"

    # Test 7: Write to forbidden path
    result, reason = validate_operation("Write", {"file_path": "C:/production/file.txt"}, audit_log)
    assert result == False, "Should block write outside allowed paths"

    # Test 8: Production identifier in params
    result, reason = validate_operation("mcp__crm__search_deals", {"env": "production"}, audit_log)
    assert result == False, "Should block operations with production identifiers"

    print("All dual-list safety tests passed ✅")
```

---

## Integration Examples

### Example 1: Super Power Safety Validator
**File:** `skills/meta/super-power-safety.md`

```python
# Blocklist patterns
FORBIDDEN_OPS = [
    r".*_update_.*",
    r".*_create_.*",
    r".*_delete_.*",
    r"send_.*_message",
    r"draft_.*_message",
    r"git\s+(push|commit)",
    r"Edit",
]

# Allowlist patterns
ALLOWED_OPS = [
    r".*_search_.*",
    r".*_list_.*",
    r".*_get_.*",
    r".*_count_.*",
    r"WebFetch",
    r"WebSearch",
    r"Read",
    r"Grep",
    r"Glob",
    r"Write",  # Validated separately
    r"Task",
    r"MCPSearch",
]

# Validation function
def validate_tool_call(tool_name, params, audit_log_path):
    # Check blocklist
    for pattern in FORBIDDEN_OPS:
        if re.match(pattern, tool_name, re.IGNORECASE):
            reason = f"BLOCKED: {tool_name} matches forbidden pattern: {pattern}"
            log_violation(tool_name, params, reason, audit_log_path)
            return False, reason

    # Special case: Write tool
    if tool_name == "Write":
        file_path = params.get("file_path", "")
        if "session/super_power/" not in file_path:
            reason = f"BLOCKED: Write outside session/super_power/: {file_path}"
            log_violation(tool_name, params, reason, audit_log_path)
            return False, reason

    # Check production identifiers
    if contains_production_id(params):
        reason = f"BLOCKED: Production identifier in parameters"
        log_violation(tool_name, params, reason, audit_log_path)
        return False, reason

    # Check allowlist
    for pattern in ALLOWED_OPS:
        if re.match(pattern, tool_name, re.IGNORECASE):
            log_allowed_operation(tool_name, audit_log_path)
            return True, "ALLOWED"

    # Default deny
    reason = f"BLOCKED: {tool_name} not in allowlist"
    log_violation(tool_name, params, reason, audit_log_path)
    return False, reason
```

### Example 2: Skill Composer Security Validation
**File:** `skills/meta/skill-composer.md`

```python
# Security blocklist for credential exposure
CRITICAL_PATTERNS = [
    "api_key", "apikey", "api-key",
    "password", "passwd", "pwd",
    "secret", "secret_key",
    "token", "access_token", "bearer",
    "auth", "authorization",
    "credential", "credentials"
]

# Dangerous operations blocklist
DANGEROUS_OPS = [
    "rm -rf", "del /f",
    "DROP TABLE", "DELETE FROM",
    "eval(", "exec(",
    "system(", "shell_exec"
]

# Safe patterns allowlist
SAFE_PATTERNS = [
    r"\$\{.*\}",  # Environment variables
    r"~/\.config/",  # Config file references
    r"mcp__.*",  # MCP tool calls
]

def validate_generated_skill(skill_content, audit_log_path):
    # Check for credentials (CRITICAL - fail immediately)
    for pattern in CRITICAL_PATTERNS:
        if pattern in skill_content.lower():
            reason = f"BLOCKED: Credential pattern detected: {pattern}"
            log_violation("skill_generation", {"pattern": pattern}, reason, audit_log_path)
            return False, reason

    # Check for dangerous operations (HIGH - warn and confirm)
    for op in DANGEROUS_OPS:
        if op in skill_content:
            reason = f"WARNING: Dangerous operation detected: {op}"
            log_blocked("skill_generation", {"operation": op}, reason, audit_log_path)
            # Could prompt user for confirmation here
            return False, reason

    # Check for safe patterns (allowlist)
    has_safe_pattern = False
    for pattern in SAFE_PATTERNS:
        if re.search(pattern, skill_content):
            has_safe_pattern = True
            break

    if not has_safe_pattern:
        # No credential handling at all - might be fine
        log_allowed("skill_generation", "No credential patterns found", audit_log_path)

    return True, "PASSED security validation"
```

---

## Best Practices

### 1. Blocklist Design
- **Start narrow, expand as needed** - Don't try to anticipate everything
- **Use regex for flexibility** - `.*_update_.*` catches all update variants
- **Document each pattern** - Future maintainers need to know why
- **Review quarterly** - Add new patterns as threats emerge

### 2. Allowlist Design
- **Start with known-safe operations** - Search, list, get, count
- **Use categories** - All MCP search operations, all read operations
- **Keep it minimal** - Only add when proven safe
- **Prefer explicit over broad** - Better to require approval than auto-allow

### 3. Validation Logic
- **Blocklist first, allowlist second** - High-confidence blocks before permissive allows
- **Default deny** - Unknown operations should be blocked
- **Log everything** - Every decision to audit log
- **Fail safely** - When in doubt, block

### 4. Audit Trail
- **Log all decisions** - BLOCKED and ALLOWED
- **Include context** - Tool name, params, reason, which list
- **Timestamp everything** - ISO 8601 format
- **Make it queryable** - JSONL format for easy parsing

---

## Migration Guide

### Adding Dual-List Safety to Existing Framework

**Step 1: Identify Operations**
- List all tools your framework calls
- Categorize: Definitely safe, definitely dangerous, uncertain

**Step 2: Create Blocklist**
- Add definitely dangerous operations
- Use broad patterns (e.g., `.*_delete_.*`)
- Document why each is blocked

**Step 3: Create Allowlist**
- Add definitely safe operations
- Use broad patterns where appropriate
- Document what each enables

**Step 4: Handle Special Cases**
- Write tool with path restrictions
- Parameter scanning for production IDs
- Any framework-specific edge cases

**Step 5: Implement Validator**
- Copy template validation function
- Customize blocklist/allowlist
- Add special case handling
- Test thoroughly

**Step 6: Add Audit Logging**
- Create audit log file
- Log all decisions
- Update violation counts
- Include in framework report

**Step 7: Test Safety Boundaries**
- Write comprehensive test suite
- Test blocklist blocks forbidden ops
- Test allowlist allows safe ops
- Test default-deny blocks unknown ops
- Test special cases (Write paths, production IDs)

---

## Related Patterns

**Combines well with:**
- **Mandatory Phase Gating** - Validate safety during planning phase
- **Risk Classification Framework** - HIGH risk operations go on blocklist
- **Simulation Testing Methodology** - Test safety boundaries with scenarios
- **Quantified Performance Targets** - Target: 0 safety violations

**See also:**
- `skills/meta/super-power-safety.md` - Full implementation example
- `skills/meta/skill-composer.md` - Security validation step (Step 6)
- `skills/meta/mandatory-phase-gating.md` - Planning phase integration

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Safety violations | 0 | Count from audit log |
| False positives (safe ops blocked) | <1% | User reports + audit review |
| False negatives (dangerous ops allowed) | 0 | Security audits |
| Audit log completeness | 100% | All operations logged |

---

*Dual-List Safety Pattern v1.0 | Defense in depth | Always validate*
