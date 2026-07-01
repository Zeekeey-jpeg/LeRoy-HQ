# Skill: New Computer Setup

## Triggers
- "new computer"
- "i'm at a new computer"
- "set up my tasks for this computer"
- "set up my scheduler for this computer"
- "set up my automation for this computer"
- "set this computer up"
- "set up leroy on this computer"
- "fresh machine"
- "new machine setup"

---

## What This Skill Does

Guides the user through restoring the full LeRoy autonomous system on a new or wiped machine after cloning the doomsday backup from GitHub. Covers Python, Claude CLI, secrets, and all 12 Task Scheduler jobs.

---

## Execution Protocol

### Step 1: Confirm Context

Say:
> "Starting new computer setup. I'll walk you through getting LeRoy fully operational — Python, Claude CLI, secrets, and all 12 scheduled tasks. Estimated time: ~30 min. Let's go step by step."

Read and display `memory/Projects/NewComputer/RECOVERY.md` in full.

---

### Step 2: Walk Through Each Phase

Present the RECOVERY.md steps in order. After each step, ask:
> "Done with Step [N] — ready for next?"

If the user hits an error, troubleshoot inline before moving on.

---

### Step 3: Run the Master Installer

When the user reaches Step 6 (Task Scheduler), instruct:

```powershell
powershell -ExecutionPolicy Bypass -File "~/.claude\tools\install-all-tasks.ps1"
```

After running, verify all 12 tasks registered:

```powershell
Get-ScheduledTask | Where-Object { $_.TaskName -match "your org|Claude-" } | Select-Object TaskName, State
```

Display results. Flag any `[MISSING]` tasks for manual fix.

---

### Step 4: Start Always-On Services

```powershell
Start-ScheduledTask -TaskName "your org-TelegramBot"
Start-ScheduledTask -TaskName "RagSidecar"
Start-ScheduledTask -TaskName "your org-ProcessGuard"
```

Verify:
```powershell
Get-ScheduledTask -TaskName "your org-TelegramBot" | Select-Object State
Invoke-RestMethod http://localhost:7742/health -ErrorAction SilentlyContinue
```

---

### Step 5: Smoke Test

Run these three diagnostics:
1. `"morning"` — full briefing, no errors
2. `"heartbeat"` — active items surface
3. `"health check"` — all systems green

If any fail, read `session/leroy.log` (tail last 50 lines) to diagnose.

---

### Step 6: First Doomsday Backup

Say `"backup"` to confirm git push works and the cycle is live on this machine.

---

## Files Referenced

| File | Purpose |
|------|---------|
| `memory/Projects/NewComputer/RECOVERY.md` | Full step-by-step recovery guide |
| `tools/install-all-tasks.ps1` | Registers all 12 scheduled tasks |
| `tools/requirements.txt` | Python package list for pip install |

---

## What to Do If Python Path Changed

The `install-all-tasks.ps1` auto-detects Python from:
1. `$env:LOCALAPPDATA\Programs\Python\Python312\python.exe`
2. `$env:LOCALAPPDATA\Programs\Python\Python311\python.exe`
3. System PATH via `Get-Command python`

If a different version is installed, edit paths in the script before running.

---

## What to Do If Username Changed

All paths in `install-all-tasks.ps1` use `$env:USERPROFILE` dynamically — no hardcoded username. It will adapt automatically.

---

*Skill version: 1.0 | Created: 2026-05-23*
