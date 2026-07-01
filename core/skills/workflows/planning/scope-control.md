---
name: scope-control
description: |
  Scope validation and creep prevention.

  Use for:
  - Validating changes stay within boundaries
  - Detecting unintended modifications
  - Preventing regression in core functionality
  - Managing scope violations

  Includes: Detection patterns, response protocol, escalation triggers.
---

# Scope Control

## Purpose
Prevent scope creep and maintain focused, reviewable changes.

## Core Rule
**Agents MUST stay within scope. No "while I was in there" changes.**

## Scope Definition

At task start, define:
1. **Files that WILL change** (explicit list)
2. **Files that MUST NOT change** (protected)
3. **Acceptable adjacent files** (may need minor updates)

## Scope Creep Patterns

### Violations (Flag Immediately)
- Files modified outside task packet list
- Refactoring that wasn't requested
- Style changes mixed with functional changes
- Dependency updates not in scope
- Config changes affecting other features
- "Improvements" not in original request

### Detection Methods

```bash
# Compare intended vs actual changes
git diff --name-only HEAD~1

# Check for unexpected modifications
git diff --stat

# Show files changed in branch
git diff --name-only main...HEAD
```

## Response Protocol

When scope violation detected:

1. **Document** - Exactly what changed and why
2. **Assess** - Beneficial or risky?
3. **Recommend**:
   - `REVERT` - Change should not have happened
   - `SEPARATE_PR` - Good change, but needs own PR
   - `APPROVE_WITH_NOTE` - Minor, acceptable deviation

4. **NEVER** silently allow unscoped changes

## Regression Prevention

Before touching shared code:

1. Identify all dependents
2. Run existing tests
3. Verify build succeeds
4. Test affected features
5. Document validation

**Core Functionality = NEVER break without explicit approval**

## Scope Tracking Template

```json
{
  "task_id": "TC-001",
  "intended_scope": {
    "files_to_modify": [
      "src/components/LoginForm.tsx",
      "src/api/auth.ts"
    ],
    "files_protected": [
      "src/config/*",
      "package.json"
    ],
    "adjacent_allowed": [
      "src/types/auth.ts"
    ]
  },
  "actual_changes": [],
  "violations": [],
  "status": "in_progress"
}
```

## Escalation Triggers

Escalate to Architect immediately if:
- Core functionality touched unexpectedly
- Security-sensitive files modified
- Database schema changes not in scope
- API contracts changed without versioning
- More than 20% changes are out of scope
- Build fails after changes

## Violation Severity Levels

| Severity | Description | Action |
|----------|-------------|--------|
| Critical | Core/security files changed | Immediate revert |
| High | Functional changes out of scope | Separate PR required |
| Medium | Adjacent file modified | Review and document |
| Low | Formatting/comments only | Approve with note |

## Prevention Strategies

### Before Starting
- Define explicit file list
- Identify protected areas
- Document assumptions

### During Development
- Check git status frequently
- Review changes before commit
- Stay focused on task

### Before PR
- Run git diff against scope
- Remove unintended changes
- Document any necessary deviations

## Common Scope Creep Examples

| What Happened | Why It's Wrong | Correct Approach |
|---------------|----------------|------------------|
| "Fixed typo while I was there" | Mixes concerns | Separate commit |
| "Updated dependencies too" | Untested changes | Separate PR |
| "Refactored for readability" | Not requested | Discuss first |
| "Added logging everywhere" | Scope expansion | Get approval |

## Cleanup After Violation

```bash
# Undo specific file changes
git checkout HEAD -- path/to/file

# Interactive revert
git add -p

# Create separate branch for good changes
git stash
git checkout -b separate-fix
git stash pop
```
