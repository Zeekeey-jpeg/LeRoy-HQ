# Doomsday Backup Skill

## Purpose
Execute full mirror backup of the LeRoy system to GitHub when user says "backup". Single repo contains EVERYTHING — config, skills, session data, memory vault, AND all project source code.

**CRITICAL:** This is the user's EXPLICIT instruction to commit and push EVERYTHING to git.

---

## Repository to Backup

| Local Path | Remote URL | Description |
|------------|------------|-------------|
| `~/.claude` | https://github.com/<your-org>/<repo> | Everything: config, skills, session, memory vault, ALL project source code |

**Note:** Single-repo architecture. All projects consolidated into `memory/Projects/` as of 2026-04-20.

**Version Control:** `BACKUP_VERSION` file increments with each backup.

---

## Trigger

**User says:** "backup", "push backup", "github backup", or "doomsday backup"

**Automatic reminder on:** Monday, Wednesday, Friday mornings (status check only - no auto-execute)

---

## File Exclusions (STANDING RULE)

**CRITICAL:** The following file types are NEVER pushed to GitHub:
- ❌ `.rvt` files (your BIM tool project files - too large, exceed GitHub 100MB limit)
- ❌ `.dwg` files (AutoCAD drawings - project artifacts, not source code)

**Enforcement:** Always verify `.gitignore` includes these exclusions before backup.

---

## Doomsday Backup Protocol

When user triggers "backup", execute full mirror backup:

### Step 0: Verify Exclusions

```bash
# Ensure .gitignore exists and excludes .rvt/.dwg + build artifacts
cd "~/.claude" && (grep -q "*.rvt" .gitignore || echo "*.rvt" >> .gitignore) && (grep -q "*.dwg" .gitignore || echo "*.dwg" >> .gitignore)
```

### Step 1: Pre-Flight Check

```bash
# Check repo status
cd "~/.claude" && git status --porcelain
```

### Step 1.5: Memory Vault Integrity Check ⚠️

**CRITICAL SAFEGUARD:** Before backing up, scan for memory deletions.

```bash
cd "~/.claude"

# Count memory deletions
MEMORY_DELETIONS=$(git status --porcelain memory/ | grep "^.D" | wc -l)

# Count memory additions
MEMORY_ADDITIONS=$(git status --porcelain memory/ | grep "^.A" | wc -l)

# Display findings
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "MEMORY VAULT INTEGRITY CHECK"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Memory deletions detected: $MEMORY_DELETIONS"
echo "Memory additions detected: $MEMORY_ADDITIONS"
```

**Decision Matrix:**

| Deletions | Action | Behavior |
|-----------|--------|----------|
| 0 | ✅ PROCEED | No deletions - safe to backup |
| 1-5 | ⚠️ WARN | Display deleted files, pause 10 seconds, allow user to Ctrl+C |
| >5 | ❌ BLOCK | Require explicit approval file `.memory-backup-approved` |

**Blocking Logic (>5 deletions):**

```bash
if [ $MEMORY_DELETIONS -gt 5 ]; then
    echo ""
    echo "❌ BACKUP BLOCKED: Memory vault mass deletion detected"
    echo ""
    echo "Deleted files:"
    git status --porcelain memory/ | grep "^.D" | head -20
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "To approve this backup:"
    echo "  1. Review deletions above"
    echo "  2. Create approval: echo 'reason' > .memory-deletion-approved"
    echo "  3. Re-run backup"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    # Check for approval file
    if [ -f ".memory-deletion-approved" ]; then
        echo "✅ Deletion approved: $(cat .memory-deletion-approved)"
        rm .memory-deletion-approved
    else
        echo "BACKUP ABORTED - Create .memory-backup-approved to proceed"
        exit 1
    fi
fi

# Warning for small deletions (1-5)
if [ $MEMORY_DELETIONS -ge 1 ] && [ $MEMORY_DELETIONS -le 5 ]; then
    echo ""
    echo "⚠️ WARNING: Memory deletions detected"
    echo ""
    git status --porcelain memory/ | grep "^.D"
    echo ""
    echo "Backup will proceed in 10 seconds..."
    echo "Press Ctrl+C to abort if these deletions are unintentional"
    sleep 10
fi

echo "✅ Memory vault check passed"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
```

**Approval Bypass Example:**

```bash
# If >5 memory files deleted and you approve it:
cd "~/.claude"
echo "Migration: Claude/* to root folders (v3.2 upgrade)" > .memory-backup-approved

# Re-run backup
# Will proceed and auto-delete approval file
```

### Step 2: Capture + Display Change Summary (MANDATORY — SHOW BEFORE COMMITTING)

**CRITICAL ENFORCEMENT:** Claude MUST run `git status --porcelain` and `git diff --stat HEAD` for EACH repo BEFORE `git add -A`, then write a plain-English narrative summary in the chat. No raw file lists. No technical noise. Just a human-readable story of what changed since the last backup.

**Required output format (numbers + plain English narrative — show in chat):**

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
LEROY (.claude) — since last backup:
  + 2 added  |  ~ 3 modified  |  - 5 deleted
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Since last backup, you updated the backup protocol twice — first
to require a change summary, then to switch it to a plain-English
narrative with counts. Also rotated 5 old session backup files.
No memory vault deletions.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PROJECTS (Desktop) — since last backup:
  + 0 added  |  ~ 2 modified  |  - 0 deleted
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Since last backup, you modified the your product memory module and
updated the main Rust entry point. No new files added.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**How Claude generates the narrative:**
1. Run `git status --porcelain` to get the raw file list (Bash tool)
2. Group files by folder/domain (skills/, memory/, agents/, etc.)
3. Write 2–4 sentences in plain English describing: what was added, what was updated, what was removed — by topic, not by filename
4. Mention memory vault status explicitly (deletions or clean)
5. THEN commit — never commit without showing the narrative first

**Narrative writing rules:**
- Use "you" — write from the user's perspective ("you updated...", "you added...")
- Group by meaning, not by file path ("updated the backup protocol" not "modified skills/routines/backup-reminder.md")
- Keep it short — 2–5 sentences per repo is ideal
- Always end with memory vault status ("No memory vault deletions" or "X memory files removed")

---

### Step 3: Execute Full Backup (with Version Control)

**Version Increment Function:**
```bash
# Increment version in BACKUP_VERSION file
increment_version() {
    local repo_path="$1"
    local version_file="$repo_path/BACKUP_VERSION"

    if [ -f "$version_file" ]; then
        local current_version=$(cat "$version_file")
        local new_version=$((current_version + 1))
        echo "$new_version" > "$version_file"
        echo "$new_version"
    else
        echo "1" > "$version_file"
        echo "1"
    fi
}
```

**Smart Push Function:**
```bash
# Push with automatic tracking setup on first push
smart_push() {
    # Check if remote origin exists
    if ! git remote get-url origin >/dev/null 2>&1; then
        echo "❌ No remote configured. Run remote setup first."
        return 1
    fi

    # Check if branch has upstream tracking
    if git rev-parse --abbrev-ref --symbolic-full-name @{u} >/dev/null 2>&1; then
        # Tracking exists, normal push
        git push
    else
        # No tracking (first push) - set it up
        git push -u origin master
    fi
}
```

**Change Summary Function:**
```bash
# Capture and display a human-readable summary of what changed before committing
capture_changes() {
    local label="$1"

    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "CHANGES IN ${label}:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    # Count by status type
    ADDED=$(git status --porcelain | grep "^??" | wc -l)
    MODIFIED=$(git status --porcelain | grep "^ M\|^M" | wc -l)
    DELETED=$(git status --porcelain | grep "^ D\|^D" | wc -l)

    echo "  + New files:      $ADDED"
    echo "  ~ Modified files: $MODIFIED"
    echo "  - Deleted files:  $DELETED"
    echo ""

    # List all changed files (up to 40, then summarize)
    TOTAL=$(git status --porcelain | wc -l)
    if [ "$TOTAL" -eq 0 ]; then
        echo "  (no changes — already up to date)"
    elif [ "$TOTAL" -le 40 ]; then
        git status --porcelain | awk '{print "  " $0}'
    else
        git status --porcelain | head -40 | awk '{print "  " $0}'
        echo "  ... and $((TOTAL - 40)) more files"
    fi

    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
}
```

**LeRoy (.claude) Backup:**
```bash
cd "~/.claude"
capture_changes "LEROY (.claude)"
VERSION=$(increment_version "~/.claude")
git add -A && git commit -m "Doomsday backup v${VERSION} - $(date +%Y-%m-%d-%H%M)" && smart_push
```

### Step 4: Verification

```bash
# Verify push
cd "~/.claude" && git log -1 --format="%h %s (%cr)"
```

---

## Success Output

```
================================================================
DOOMSDAY BACKUP COMPLETE
================================================================

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CHANGES IN LEROY (.claude):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  + New files:      {X}
  ~ Modified files: {X}
  - Deleted files:  {X}

  M  skills/routines/backup-reminder.md
  M  session/state.json
  ?? memory/Projects/NewProject.md
  ... (full file list up to 40, then summarized)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ LeRoy v{version}
   Pushed to: github.com/<your-org>/<repo>
   Latest: {hash} {msg} ({time})

Full mirror copy secured on GitHub (single repository — all projects included).
```

---

## Monday/Wednesday/Friday Reminder (STATUS CHECK ONLY)

During morning briefing, display status but DON'T execute backup:

```
================================================================
BACKUP STATUS CHECK (Mon/Wed/Fri)
================================================================

| Repository | Version | Status      | Last Commit              | Remote                                  |
|------------|---------|-------------|--------------------------|------------------------------------------|
| .claude    | v{X}    | {X} changes | {hash} {msg} ({time})    | github.com/<your-org>/<repo>           |

Say "backup" to execute doomsday backup now.
```

### Status Indicators

| Status | Meaning |
|--------|---------|
| `Clean` | No uncommitted changes |
| `X changes` | X files modified/untracked |
| `Ahead by X` | Commits ready to push |


---

## What Gets Backed Up

**Full mirror includes:**
- ✅ All modified files
- ✅ All new/untracked files
- ✅ All deleted files (AFTER memory vault check)
- ✅ Session state and history
- ✅ Memory vault notes (in .claude/memory)
- ✅ Skills and agents
- ✅ Settings and configs
- ✅ All project source code (in memory/Projects/ — your BIM connector, your product, LeRoy Swarm, BtcTrader, etc.)
- ✅ Version tracking (BACKUP_VERSION files)

**Excluded (STANDING RULE):**
- ❌ `.rvt` files (your BIM tool projects - too large for GitHub)
- ❌ `.dwg` files (CAD drawings - project artifacts)

**Protected (MEMORY VAULT):**
- ⚠️ Memory deletions (1-5 files) trigger 10-second warning
- ❌ Memory mass deletions (>5 files) require approval file

**Note:** `git add -A` captures complete system state, but `.gitignore` prevents large binary files from being tracked.

---

## Error Handling

| Error | Response | Action |
|-------|----------|--------|
| `Memory mass deletion` | >5 memory files deleted | Block backup, require `.memory-backup-approved` file |
| `Memory deletion warning` | 1-5 memory files deleted | 10-second pause, show deleted files, allow Ctrl+C |
| `Authentication failed` | GitHub auth failed | Display: `Run: gh auth login` |
| `Remote not found` | Remote not configured | Auto-configure in Step 2 first-time setup |
| `Merge conflict` | Conflicts detected | Abort backup, show: `git status` output |
| `Nothing to commit` | No changes since last backup | Display: "System already mirrored. No backup needed." |
| `Push rejected` | Remote has newer commits | Display: `git pull --rebase` then retry |

---

## Remote Configuration (One-Time Setup)

If remote needs manual setup:

```bash
cd "~/.claude"
git remote add origin https://github.com/<your-org>/<repo>
```

**Note:** Desktop/Projects repo (PROJECTS) was archived on 2026-04-20. All project source code now lives in memory/Projects/ and backs up via the LeRoy repo.

---

## Authorization

**User Explicit Instruction:** When user says "backup", they are explicitly authorizing:
- Full commit of all changes
- Push to GitHub remote
- Overriding Git Safety Protocol for this specific operation

This is NOT auto-commit. This is user-triggered doomsday backup.

---

*Created: 2026-01-10*
*Updated: 2026-01-28 - Added .rvt/.dwg exclusion rule*
*Updated: 2026-01-31 - Added memory vault deletion protection (Step 1.5)*
*Updated: 2026-02-03 - Added LeRoy Swarm repo + version control system (BACKUP_VERSION)*
*Updated: 2026-02-11 - Added your product repo as 5th repository + corrected path to EXAMPLECLIENT\your product*
*Updated: 2026-02-21 - Consolidated to 2 repos: removed your BIM connector/your product/LeRoy Swarm as separate entries; replaced with single Desktop\Projects → PROJECTS (covers all projects). First-time push handled automatically.*
*Maintainer: the user*
