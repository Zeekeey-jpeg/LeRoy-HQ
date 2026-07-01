---
name: git-pushing
description: |
  Stage, commit, and push git changes with conventional commits.

  Activate on:
  - "push this", "commit and push"
  - "save to github", "push to remote"
  - "let's push this up"

  Includes: Smart commit script, conventional format, push workflow.
---

# Git Push Workflow

Stage all changes, create conventional commit, push to remote.

## When to Activate
- "push this", "commit and push"
- "save to github", "push to remote"
- Completes feature and wants to share
- "let's push this up"

## Quick Workflow

```bash
# 1. Check status
git status

# 2. Stage all changes
git add .

# 3. Commit with conventional message
git commit -m "feat(scope): description

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>"

# 4. Push with upstream tracking
git push -u origin $(git branch --show-current)
```

## Conventional Commit Format

```
<type>(<scope>): <description>

[optional body]

🤖 Generated with [Claude Code](https://claude.ai/code)
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
```bash
git commit -m "feat(auth): add OAuth2 login flow

🤖 Generated with [Claude Code](https://claude.ai/code)"

git commit -m "fix(api): handle null response from vendor

🤖 Generated with [Claude Code](https://claude.ai/code)"
```

## Pre-Push Checklist

Before pushing:
- [ ] All tests pass
- [ ] Build succeeds
- [ ] No linting errors
- [ ] Commit message is conventional
- [ ] No sensitive data in commit

## Branch Management

```bash
# Create feature branch
git checkout -b feature/name

# Push new branch
git push -u origin feature/name

# After merge, cleanup
git checkout main
git pull
git branch -d feature/name
git push origin --delete feature/name
```

## Force Push Safety

**NEVER force push to main/master**

Only use force push when:
- On personal feature branch
- No one else is working on branch
- Rewriting history before first push

```bash
# Safe force push (fails if remote has changes)
git push --force-with-lease
```

## Handling Conflicts

```bash
# If push rejected due to remote changes
git pull --rebase origin main
# Resolve conflicts if any
git push
```

## Commit Amending

Only amend when:
- Commit hasn't been pushed yet
- OR you're on a personal branch

```bash
# Amend last commit message
git commit --amend -m "new message"

# Add files to last commit
git add forgotten-file.ts
git commit --amend --no-edit
```

## Push Output Tags

After successful push:
```
[PUSHED] feature/auth-login -> origin/feature/auth-login
Commits: 3
Files changed: 7
Ready for PR: gh pr create
```
