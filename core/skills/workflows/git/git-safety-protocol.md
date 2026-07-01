# Git Safety Protocol (MANDATORY)

> **Extracted from:** CLAUDE.md - Git Safety section
> **Purpose:** Absolute rules preventing unauthorized git operations

---

## CRITICAL RULE

NEVER execute git commit or git push without EXPLICIT user instruction.

---

## Prohibited Actions

- Auto-commits (even for "backup" or "routine" purposes)
- Auto-push operations
- Scheduled git operations
- Git operations triggered by time/date
- Git operations in background tasks

---

## Required Before ANY Git Write Operation

1. User MUST explicitly request commit/push with clear instruction
2. User MUST see exactly what will be committed (git status, git diff)
3. User MUST approve commit message
4. User MUST confirm push operation

---

## Allowed Git Operations (Read-Only, Always Safe)

- `git status` (checking repo state)
- `git log` (viewing history)
- `git diff` (viewing changes)
- `git branch` (listing branches)
- `git remote -v` (viewing remotes)

---

## Repo Boundary Verification (MANDATORY before destructive ops)

**Lesson from 2026-04-28 incident:** A failed `rm -rf` deleted `v5-source/.git` but left a locked `.vite/` folder behind. Subsequent `cd v5-source && git reset --hard origin/master` walked UP to find `.claude/.git` — and reset the **parent** `.claude` repo, wiping uncommitted edits to `cache/changelog.md`, `memory/your org_Business/Invoicing/invoice-counter.json`, and `sessions/30312.json`.

### Hard Rules

1. **Never `cd` into a directory and run a destructive git op.** Always use `git -C <abs-path>` so git fails loudly if `<path>/.git` is missing rather than walking up the tree.
2. **Before ANY `git reset --hard`, `git clean -fd[x]`, `git checkout --`, or `git rebase` — verify the repo root.** Run `git -C <path> rev-parse --show-toplevel` and confirm the output matches the path you intended. If it walks up to a parent, **STOP**.
3. **Verify `<path>/.git` exists with `ls -la <path>/.git/HEAD`** before any destructive op on a path that recently had a partial `rm -rf`, `mv`, or extraction failure.
4. **Confirm remote `origin` matches expectation.** Before `git reset --hard origin/...`, run `git -C <path> remote get-url origin` and pattern-match the URL against the project's known remote.
5. **Partial-failure recovery.** If `rm -rf` reports "Device or resource busy" or any non-zero exit, the directory is in an undefined state. Do NOT run `git`, `mv`, or any path-rewriting command against it until you've enumerated what survived (`ls -la`, `find` for `.git`).

### Required Pre-Flight for Destructive Git Ops

```bash
# BEFORE: git reset --hard, git clean -fdx, git checkout --, git rebase
TARGET="/abs/path/to/repo"

# 1. Verify .git exists
[ -f "$TARGET/.git/HEAD" ] || { echo "ABORT: $TARGET/.git/HEAD missing"; exit 1; }

# 2. Verify repo root matches target (no upward walk)
ROOT=$(git -C "$TARGET" rev-parse --show-toplevel)
[ "$ROOT" = "$TARGET" ] || { echo "ABORT: git resolved to $ROOT, expected $TARGET"; exit 1; }

# 3. Verify expected remote
REMOTE=$(git -C "$TARGET" remote get-url origin)
echo "Remote: $REMOTE"  # human-confirm before proceeding

# 4. Use -C, not cd
git -C "$TARGET" reset --hard origin/<branch>
```

### Triggers that REQUIRE this pre-flight

- After ANY failed `rm -rf` (any non-zero exit)
- After ANY failed `mv` of a folder containing `.git`
- After ANY `git clone` into a non-empty target
- When operating on a folder beneath another git repo (nested layout — e.g., `memory/Projects/IntegratorOS/v5-source/` lives under `.claude/.git`)
- When the user mentions "clone fresh", "overwrite", "wipe and reset" — these are exactly the ops with highest blast radius

---

## Enforcement

**Violation of this protocol is a system failure.**

Any agent (including background agents like @agent-scout, @agent-planner) that attempts git write operations without explicit user instruction is in violation.

---

*Extracted from CLAUDE.md to reduce hub file size. All routing pointers preserved.*
