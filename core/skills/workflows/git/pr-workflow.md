---
name: pr-workflow
description: |
  Pull request and commit workflow standards.

  Use for:
  - Creating commits with conventional format
  - Preparing professional PRs
  - Running pre-commit audits
  - Managing merge workflow

  Includes: Commit convention, PR template, workflow stages.
---

# Pull Request Workflow

## Overview
Every commit flows through this mandatory process.

## Workflow Stages

```
1. DEVELOPMENT
   Work on feature branch
   Commit atomically with conventional format
          |
2. SENTINEL AUDIT
   Scope validation
   Hygiene scan
   Regression check
          |
3. PR CREATION
   Professional title and body
   Checklist populated
   Screenshots if UI changed
          |
4. HUMAN REVIEW
   the user reviews PR
   Approves or requests changes
          |
5. MERGE
   Squash and merge to main
   Delete feature branch
   Clean up worktree (if used)
```

## Commit Convention

### Format
```
type(scope): description

[optional body]

[optional footer]
```

### Types
| Type | Use For |
|------|---------|
| feat | New feature |
| fix | Bug fix |
| docs | Documentation |
| refactor | Code restructure |
| test | Adding tests |
| chore | Maintenance |
| style | Formatting |
| perf | Performance |

### Examples
```
feat(auth): add OAuth2 login flow
fix(api): handle null response from vendor
docs(readme): update installation instructions
refactor(utils): extract date formatting helpers
test(auth): add unit tests for login
chore(deps): update dependencies
```

### Bad Commits (NEVER)
```
WIP
stuff
changes
update
fix
asdf
misc
```

## PR Template

```markdown
## Summary
Brief description of what this PR accomplishes.

## Changes
- Added [feature/component]
- Modified [file/behavior]
- Fixed [bug description]

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing performed
- [ ] Localhost verified

## Screenshots
[If UI changes, include before/after]

## Checklist
- [ ] Code follows project style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] No console.log/debug statements
- [ ] Tests added for new functionality
```

## Branch Naming

| Pattern | Example |
|---------|---------|
| feature/ | feature/user-dashboard |
| fix/ | fix/login-redirect |
| docs/ | docs/api-reference |
| refactor/ | refactor/auth-module |
| test/ | test/api-coverage |

## Merge Strategy

1. **Squash and merge** for feature branches
2. **Create merge commit** for release branches
3. **Rebase** for small fixes on main

## Post-Merge Cleanup

```bash
# Delete local branch
git branch -d feature/branch-name

# Delete remote branch
git push origin --delete feature/branch-name

# Clean up worktree (if used)
git worktree remove ../feature-branch

# Prune remote tracking branches
git fetch --prune
```

## Pre-Commit Checklist

Before creating PR:
- [ ] All tests pass
- [ ] Build succeeds
- [ ] No linting errors
- [ ] No console.log statements
- [ ] Documentation updated
- [ ] Scope validated (no unintended changes)

## PR Review Guidelines

### For Author
- Keep PRs small (<400 lines when possible)
- Self-review before requesting review
- Respond to feedback promptly
- Don't force-push after review starts

### For Reviewer
- Review within 24 hours
- Be constructive, not critical
- Approve or request changes clearly
- Test locally if unsure

## Git Commands Reference

```bash
# Start feature
git checkout -b feature/name

# Stage changes
git add .

# Commit with message
git commit -m "feat(scope): description"

# Push to remote
git push -u origin feature/name

# Create PR (using gh CLI)
gh pr create --title "feat(scope): description" --body "..."

# After merge
git checkout main
git pull
git branch -d feature/name
```
