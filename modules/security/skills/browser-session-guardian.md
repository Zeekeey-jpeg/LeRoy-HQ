---
name: browser-session-guardian
description: "Chrome/Chromium lockfile collision prevention and session hygiene for CTF browser automation. Load when: Playwright session about to start, profile lock error encountered, browser crash occurred, new CTF session initializing. Returns browser_ready: true/false before any automated browser action. Owner: cyber-operator."
version: 1.0
created: 2026-02-24
owner: cyber-operator
---

# Browser Session Guardian

Detects, prevents, and resolves Chrome/Chromium lockfile conflicts before they interrupt CTF exploit chains. Run before every Playwright session launch. Zero tolerance for profile lock collisions.

---

## The Problem

Chrome writes lock files (`SingletonLock`, `SingletonSocket`, `SingletonCookie`) to the user data directory when a profile is open. Stale processes — crashed bots, leftover automation sessions, zombie chromedriver instances — leave these locks behind, blocking new sessions with "profile already in use" errors.

**Guardian eliminates this proactively, before it interrupts an attack chain.**

---

## Lock File Locations

| Environment | Path |
|-------------|------|
| Linux Chrome | `~/.config/google-chrome/[Profile]/SingletonLock` |
| Linux Chromium | `~/.config/chromium/[Profile]/SingletonLock` |
| Docker/CTF containers | `/home/<user>/.config/chromium/` or `/root/.config/chromium/` |
| Custom --user-data-dir | `[custom_path]/SingletonLock` |
| MacOS Chrome | `~/Library/Application Support/Google/Chrome/` |

---

## Detection Protocol (Run Before EVERY Browser Launch)

### Step 1: Scan for Lock Files

```bash
find [user_data_dir] -name "SingletonLock" -o -name "SingletonSocket" -o -name "lock" 2>/dev/null
```

### Step 2: Validate Process Association

```bash
# On Linux — SingletonLock is a symlink containing: <hostname>-<pid>
readlink ~/.config/chromium/SingletonLock
# Extract PID, then verify:
ps aux | grep <pid>
```

### Step 3: Classify Lock State

| Classification | Condition | Action |
|----------------|-----------|--------|
| `LIVE_LOCK` | PID exists AND process is active | Do NOT kill — use different profile path |
| `STALE_LOCK` | PID missing OR process dead | Safe to remove immediately |
| `ZOMBIE_LOCK` | PID exists but process is defunct/unresponsive | `kill -9` then remove |

---

## Remediation Procedures

### Standard Stale Lock Cleanup

```bash
find ~/.config/chromium -name "SingletonLock" -delete
find ~/.config/chromium -name "SingletonSocket" -delete
find ~/.config/chromium -name "SingletonCookie" -delete
```

### Nuclear Option (Only After Confirming Stale)

```bash
pkill -f chromium || true
pkill -f chrome || true
pkill -f chromedriver || true
sleep 2
find ~/.config -name "SingletonLock" -delete
```

### Preferred: Isolated Profile Strategy

```bash
# Timestamp-named profiles never collide
chromium --user-data-dir=/tmp/ctf-profile-$(date +%s) --no-sandbox [URL]

# UUID variant for guaranteed uniqueness
chromium --user-data-dir=/tmp/ctf-$(python3 -c 'import uuid; print(uuid.uuid4())') --no-sandbox [URL]
```

**Isolated profile is the default recommendation** — always use a fresh `--user-data-dir` per CTF session to avoid any state bleed between challenges.

---

## Playwright / Selenium / WebDriver Specifics

- After any `WebDriverException`, run full lock cleanup before retry
- Set `--user-data-dir` to a unique temp path per test run (UUID or timestamp)
- Always include in container environments: `--no-sandbox --disable-dev-shm-usage`
- If a session crashes mid-exploit: guardian auto-cleans before next Playwright call
- For Playwright specifically: use `userDataDir` in `browser.launch_persistent_context()` with a unique path

---

## Pre-Launch Checklist

Before calling any `browser_navigate()` or `browser_snapshot()`:

```
[ ] Scan for existing lock files at target profile path
[ ] Validate any found PIDs are actually alive
[ ] Remove all stale/zombie locks
[ ] Confirm --user-data-dir is either isolated or clean
[ ] Confirm --no-sandbox is set (container environments)
[ ] Report browser_ready status
```

---

## Status Report Format

```json
{
  "scan_time": "<ISO timestamp>",
  "locks_found": [
    {
      "path": "<absolute path to lock file>",
      "pid": "<pid from symlink or null>",
      "status": "stale|live|zombie"
    }
  ],
  "actions_taken": [
    "Removed stale lock at /home/user/.config/chromium/SingletonLock — PID 1234 no longer active",
    "Killed zombie process PID 5678"
  ],
  "browser_ready": true,
  "recommended_profile_path": "/tmp/ctf-profile-1708734000"
}
```

---

## Integration Rule

**BEFORE every payload dispatch that requires browser automation:**
1. Run guardian check
2. Proceed only on `browser_ready: true`
3. If `browser_ready: false` (LIVE_LOCK detected): use `recommended_profile_path` from status report
4. Log guardian action inline: `[GUARDIAN] Browser ready. Profile: /tmp/ctf-profile-1708734000`

**After any Playwright exception or crash:**
1. Run guardian immediately before retry
2. Do NOT retry without guardian clearance — guaranteed collision otherwise

---

## Common Error → Guardian Action Map

| Error | Guardian Action |
|-------|----------------|
| "Profile already in use" | Full stale lock sweep → isolated profile |
| WebDriver session invalid | Kill zombie → fresh profile |
| `DevToolsActivePort file doesn't exist` | Kill all chrome/chromium → fresh profile |
| `session not created: Chrome failed to start` | Check --no-sandbox, --disable-dev-shm-usage, then fresh profile |
| Playwright timeout on launch | Lock sweep → isolated profile → increase timeout to 30s |

---

*browser-session-guardian v1.0 | Chrome/Chromium lock collision prevention | CTF Playwright sessions | 2026-02-24*
