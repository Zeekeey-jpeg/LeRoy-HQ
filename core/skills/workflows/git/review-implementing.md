---
name: review-implementing
description: |
  Process and implement code review feedback systematically.

  Activate when:
  - User provides reviewer comments
  - Pastes PR review notes
  - "address these comments"
  - "implement feedback"

  Includes: Parsing workflow, todo creation, systematic implementation.
---

# Review Feedback Implementation

Systematically process code review feedback.

## When to Activate
- User provides reviewer comments
- Pastes PR review notes
- "address these comments"
- "implement feedback"
- "fix review comments"

## Workflow

### 1. Parse Reviewer Notes
- Split numbered lists
- Handle bullet points
- Extract distinct change requests
- Clarify ambiguous items first

### 2. Create Todo List
Each feedback item becomes one or more todos:
```
- Add type hints to extract function
- Fix duplicate tag detection logic
- Update docstring in chain.py
- Add unit test for edge case
```

### 3. Implement Systematically
For each todo:
1. **Locate**: Grep for functions/classes
2. **Change**: Edit tool, preserve functionality
3. **Verify**: Run tests, check syntax
4. **Update**: Mark todo `completed`

### 4. Handle Different Types

| Type | Action |
|------|--------|
| Code changes | Edit tool, follow conventions |
| New features | Create files, add tests |
| Documentation | Update docstrings/markdown |
| Tests | pytest conventions, descriptive names |
| Refactoring | Preserve functionality, run tests |
| Style | Apply formatter, check linting |

### 5. Validation
- Run affected tests
- Check linting
- Verify no regressions

## Parsing Examples

### Numbered List
```
1. Add error handling to the API call
2. Update the return type to Optional[str]
3. Add a test for the empty case
```
-> 3 todos

### Bullet Points
```
- Consider using a dataclass here
- The loop could be simplified with a list comprehension
- Missing docstring
```
-> 3 todos

### Inline Comments
```
src/api.py:45 - This should handle the 404 case
src/utils.py:12 - Unused import
```
-> 2 todos (with file locations)

### Mixed Format
```
Main issues:
1. Error handling is missing throughout
2. Tests needed for:
   - Happy path
   - Error cases
   - Edge cases
```
-> 4 todos (1 + 3 sub-items)

## Implementation Order

1. **Critical/Blockers first** - Must fix before merge
2. **Functional changes** - Logic updates
3. **Tests** - Verify changes work
4. **Documentation** - Update docs
5. **Style/cleanup** - Non-functional improvements

## Communication

### After Each Item
```
Completed: "Add type hints to extract function"
- Modified: src/utils.py:45-52
- Added: Optional[str] return type
```

### After All Items
```
Review feedback addressed:
- 5/5 items completed
- All tests passing
- Ready for re-review
```

## Rules

- **Always use TodoWrite** for tracking
- **Mark completed immediately** after each item
- **Only one in_progress** at a time
- **Ask questions** for unclear feedback
- **Run tests** if changes affect tested code
- **Preserve functionality** during refactoring

## Ambiguous Feedback

If feedback is unclear:
1. List possible interpretations
2. Ask user to clarify
3. Don't guess on important changes

Example:
```
Reviewer said: "This could be cleaner"

Possible interpretations:
1. Extract to separate function
2. Use more descriptive variable names
3. Simplify the logic

Which approach would you like?
```

## Verification Checklist

After implementing all feedback:
- [ ] All todos marked complete
- [ ] Tests pass
- [ ] Linting passes
- [ ] Build succeeds
- [ ] Changes match reviewer intent
- [ ] No unintended modifications
