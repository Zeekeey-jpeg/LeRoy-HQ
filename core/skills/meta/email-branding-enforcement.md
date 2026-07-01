# Email Branding Enforcement Protocol

> **CRITICAL:** MANDATORY pre-flight check before ANY send_mail MCP call
> **Version:** 1.0.0
> **Created:** 2026-02-03
> **Enforcement Level:** ZERO TOLERANCE

---

## Purpose

**PROBLEM:** Claude can "forget" to use the email-composer library and call `mcp__email-primary__send_mail` directly, resulting in unbranded emails without signature.

**SOLUTION:** Gate-level enforcement that BLOCKS direct MCP calls and REQUIRES library usage.

---

## Enforcement Rules (MANDATORY)

### Rule 1: Direct MCP Call = BLOCKED

**NEVER call `mcp__email-primary__send_mail` directly.**

**ALWAYS route through:**
```
CLAUDE.md trigger "send email"
  → skills/integrations/gmail-send-protocol.md (wrapper)
    → libs/skills/compositions/email-composer.md (library) ✅
      → mcp__email-primary__send_mail (with HTML branding)
```

### Rule 2: Gate Validator Check

Before ANY response containing `mcp__email-primary__send_mail`:
1. **Check:** Was `email-composer.md` loaded in this conversation?
2. **If NO:** BLOCK response, output error, force library load
3. **If YES:** Allow send, verify HTML branding applied

### Rule 3: HTML Branding = DEFAULT

**ALL substantive emails MUST use HTML branded format:**
- Logo header on dark background
- "<your tagline>" tagline
- Styled content area
- Footer with contact info + "Business Integration Management"

**EXCEPTION:** Only single-line confirmations ("ok thanks", "got it") use plain text + signature.

---

## Implementation (3-Layer Defense)

### Layer 1: Pre-Response Validation (Gate Enforcer)

**File:** `hooks/gate-enforcer.py`

**Add check:**
```python
def validate_email_branding(response_text, tool_calls):
    """
    MANDATORY: Validate email branding before allowing response.

    Returns:
        (bool, str) - (is_valid, error_message)
    """
    # Check if response contains send_mail
    has_send_mail = 'mcp__email-primary__send_mail' in response_text

    if not has_send_mail:
        return True, None  # No email send, pass

    # Check if email-composer.md was loaded
    has_composer = 'email-composer.md' in response_text or \
                   'libs/skills/compositions/email-composer.md' in response_text

    if not has_composer:
        error = """
❌ EMAIL BRANDING ENFORCEMENT VIOLATION

Direct send_mail call detected without email-composer library.

REQUIRED ACTION:
1. Load: libs/skills/compositions/email-composer.md
2. Use compose_email() function
3. Apply HTML branding template

This is MANDATORY. No exceptions.
"""
        return False, error

    # Check if HTML branding applied (isHtml: true in call)
    has_html_flag = '"isHtml": true' in response_text or \
                    '"isHtml":true' in response_text

    if not has_html_flag:
        # Check if it's a single-line confirmation (exception allowed)
        body_content = extract_email_body(response_text)
        if len(body_content) > 50:  # Substantive email
            error = """
⚠️  EMAIL BRANDING WARNING

Substantive email detected without HTML branding.

DEFAULT: HTML branded emails for ALL substantive content.
EXCEPTION: Only single-line confirmations use plain text.

Set isHtml: true and use branded template.
"""
            return False, error

    return True, None  # All checks passed
```

### Layer 2: Skill Wrapper Enforcement

**File:** `skills/integrations/gmail-send-protocol.md`

**Add at top:**
```yaml
## CRITICAL ENFORCEMENT (v2.1)

**BEFORE ANY EMAIL SEND:**
1. MUST load libs/skills/compositions/email-composer.md
2. MUST call compose_email() - NEVER call MCP directly
3. MUST use HTML branding (isHtml: true) for substantive emails

**VIOLATION = RESPONSE BLOCKED BY GATE ENFORCER**
```

### Layer 3: Library Documentation

**File:** `libs/skills/compositions/email-composer.md`

**Already updated (v1.0.2):**
- ✅ HTML branding documented as DEFAULT
- ✅ Plain text as EXCEPTION only
- ✅ Anti-pattern: "Bypass email-composer library" flagged as #1 violation

---

## Validation Checklist (Pre-Send)

Before sending ANY email, verify:

- [ ] **Library loaded?** `email-composer.md` referenced in conversation
- [ ] **HTML flag set?** `isHtml: true` in MCP call parameters
- [ ] **Body wrapped?** Content inside HTML branded template
- [ ] **Signature included?** Footer with contact info present
- [ ] **Preview shown?** Terminal preview displayed to user

**If ANY checkbox is NO → BLOCK SEND**

---

## Error Messages

### Violation Type 1: Direct MCP Call
```
❌ BLOCKED: Direct send_mail call without email-composer library

You MUST route through the email composition library.

Fix: Load libs/skills/compositions/email-composer.md first
```

### Violation Type 2: Missing HTML Branding
```
⚠️  WARNING: Substantive email without HTML branding

DEFAULT: All emails get full branding (logo, tagline, footer)
EXCEPTION: Only "ok thanks" type confirmations use plain text

Fix: Set isHtml: true and wrap in branded template
```

### Violation Type 3: Signature Missing
```
❌ BLOCKED: Plain text email without signature

ALL emails must include signature block:
the user
your org | example.com | you@example.com | 
Business Integration Management

Fix: Append signature to body before sending
```

---

## Integration with Gate System

### Update CLAUDE.md (Quick Triggers section)

```markdown
| Trigger | Action | Enforcement |
|---------|--------|-------------|
| "send email", "email to", "compose email" | Gmail send protocol | **BRANDING ENFORCED** |
```

### Update gate-enforcer.py

Add `validate_email_branding()` to validation chain:
```python
# In main validation loop
if contains_tool_call(response, 'send_mail'):
    is_valid, error = validate_email_branding(response, tool_calls)
    if not is_valid:
        block_response(error)
        sys.exit(1)
```

---

## Testing Protocol

### Test Case 1: Direct MCP Call (Should BLOCK)
```
User: "Send email to contact@exampleclient.com saying thanks"
Claude: [Attempts direct mcp__email-primary__send_mail call]
Gate: ❌ BLOCKED - email-composer library not loaded
```

### Test Case 2: Library Usage (Should PASS)
```
User: "Send email to contact@exampleclient.com with proposal"
Claude: [Loads email-composer.md, calls compose_email()]
Gate: ✅ PASS - branded email with HTML template
```

### Test Case 3: Plain Text Substantive Email (Should WARN)
```
User: "Send plain text email to client"
Claude: [Sends plain text without HTML]
Gate: ⚠️  WARN - substantive email requires HTML branding
```

---

## Rollout Plan

### Phase 1: Documentation (COMPLETE)
- ✅ email-composer.md updated (v1.0.2)
- ✅ Branding rules documented
- ✅ Anti-patterns flagged
- ✅ This enforcement protocol created

### Phase 2: Gate Integration (PENDING)
- [ ] Update gate-enforcer.py with validation function
- [ ] Add email branding check to validation chain
- [ ] Test with all 3 test cases above
- [ ] Deploy to production

### Phase 3: Monitoring (ONGOING)
- [ ] Track enforcement violations in error-log.jsonl
- [ ] Weekly review of email sends (branded vs plain)
- [ ] Adjust thresholds if needed

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-02-03 | Initial enforcement protocol after a client contact email incident |

---

*ZERO TOLERANCE: Email branding is NOT optional | Gate-level enforcement | v1.0.0*
