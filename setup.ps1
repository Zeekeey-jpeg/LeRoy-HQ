<#
.SYNOPSIS
    LeRoy - setup.ps1  (Windows bootstrap)

.DESCRIPTION
    The one command that turns your Claude Code into LeRoy. Runs the eight
    steps from onboarding-and-install.md:

      1. Preflight (doctor.py) - check Claude Code / Node 18+ / Python 3.11+ / git,
         printing a clean fix for every miss.
      2. Detect existing ~\.claude, back it up, and merge core\ in additively
         (never clobbers your settings; hooks are appended).
      3. Install Python deps (from requirements.txt if present).
      4. Register the `leroy` command on PATH (per-user).
      5. Create both Desktop shortcuts - "Leroy" (UI) + "Leroy CLI" (terminal).
      6. Index memory\ into the RAG sidecar (existing-user upgrades keep their
         vault; this only builds a derived index, never touches the vault).
      7. Launch the interview -> leroy init.
      8. Print a friendly "you're live" card.

    Every path derives from $HOME\.claude - nothing is hardcoded.
    No secrets are read or written by this script.

.EXAMPLE
    .\setup.ps1
    .\setup.ps1 -SkipInit        # merge + install, skip the interview
#>

[CmdletBinding()]
param(
    [switch]$SkipInit,
    [switch]$SkipDeps,
    [switch]$SkipShortcuts,
    # How to treat an existing ~\.claude: "enhance" (additive, nothing overwritten),
    # "fresh" (move the old one aside to a backup, install clean), or "ask" (prompt).
    [ValidateSet("enhance", "fresh", "ask")]
    [string]$Mode = "ask"
)

$ErrorActionPreference = "Stop"

$RepoRoot   = Split-Path -Parent $PSCommandPath
$Installer  = Join-Path $RepoRoot "installer"
$BinDir     = Join-Path $RepoRoot "bin"
$ClaudeHome = Join-Path $HOME ".claude"

function Section($t) { Write-Host ""; Write-Host "== $t ==" -ForegroundColor Cyan }
function Say($t)     { Write-Host "  $t" }

function Get-Python {
    foreach ($c in @("python", "py", "python3")) {
        $cmd = Get-Command $c -ErrorAction SilentlyContinue
        if ($cmd) { return $cmd.Source }
    }
    return $null
}

Write-Host ""
Write-Host "  Installing LeRoy - your self-growing AI company." -ForegroundColor Green
Write-Host "  Repo: $RepoRoot"

# --- Step 1: preflight ------------------------------------------------------
Section "1/8  Preflight check"
$py = Get-Python
if (-not $py) {
    Say "Python 3.11+ is required and wasn't found on PATH."
    Say "Install it from https://www.python.org/downloads/ (check 'Add to PATH'), then re-run setup."
    exit 1
}
& $py (Join-Path $Installer "doctor.py")
if ($LASTEXITCODE -ne 0) {
    Say "Prerequisites are missing (see above). Fix them, then re-run .\setup.ps1."
    exit $LASTEXITCODE
}

# --- Step 2: add LeRoy to ~\.claude (enhance existing, or start fresh) -------
Section "2/8  Add LeRoy to ~\.claude (backup first)"
$freshFlag = @()
if (Test-Path $ClaudeHome) {
    $choice = $Mode
    if ($choice -eq "ask") {
        Say "You already have a ~\.claude (an existing Claude Code setup). How should I add LeRoy?"
        Say "  [1] Enhance it  - add LeRoy's agents, memory + skills on top. Your settings win; nothing is overwritten."
        Say "  [2] Start fresh - set your current ~\.claude aside as a backup and install a clean LeRoy."
        $ans = Read-Host "  Choose 1 or 2 (default 1)"
        if ($ans -eq "2") { $choice = "fresh" } else { $choice = "enhance" }
    }
    if ($choice -eq "fresh") {
        Say "Start fresh: your current ~\.claude will be moved to a timestamped backup, then a clean LeRoy is installed."
        $freshFlag = @("--fresh")
    } else {
        Say "Enhance: your ~\.claude will be backed up, then LeRoy is added additively (your own files/settings win)."
    }
} else {
    Say "No existing ~\.claude - setting you up fresh."
}
& $py (Join-Path $Installer "merge.py") @freshFlag
if ($LASTEXITCODE -ne 0) { Say "Install failed. Nothing was overwritten (your backup is intact)."; exit $LASTEXITCODE }
Say "Done. Your original config (if any) is backed up - undo anytime with 'leroy reset'."

# Record where this checkout lives so future lookups (e.g. a scheduled
# maintenance task, or `leroy backup` run from a different cwd) can find the
# repo without guessing (WS4.1 user-finding protocol).
& $py -c "import sys; sys.path.insert(0, r'$Installer'); import find_user; from pathlib import Path; find_user.write_repo_pointer(Path(r'$ClaudeHome'), Path(r'$RepoRoot'))"

# --- Step 3: python deps ----------------------------------------------------
Section "3/8  Install Python dependencies"
$req = Join-Path $RepoRoot "requirements.txt"
if ($SkipDeps) {
    Say "Skipped (--SkipDeps)."
} elseif (Test-Path $req) {
    Say "Installing from requirements.txt..."
    & $py -m pip install --user -q -r $req
    if ($LASTEXITCODE -ne 0) { Say "pip install reported an error - continuing (installer/CLI are stdlib-only)." }
} else {
    Say "No requirements.txt - installer + CLI are stdlib-only, nothing to install."
}

# --- Step 4: register `leroy` on PATH --------------------------------------
Section "4/8  Register the 'leroy' command"
# Create a tiny shim in a user-local bin dir and add it to the user PATH.
$UserBin = Join-Path $HOME ".local\bin"
New-Item -ItemType Directory -Force -Path $UserBin | Out-Null
$Shim = Join-Path $UserBin "leroy.ps1"
$LeroyPs1 = Join-Path $BinDir "leroy.ps1"
# The shim just forwards to the repo's CLI so `leroy update` keeps it current.
@"
# LeRoy shim - forwards to the repo CLI. Auto-generated by setup.ps1.
& '$LeroyPs1' @args
"@ | Set-Content -Path $Shim -Encoding UTF8

# Also drop a .cmd wrapper so `leroy` works from cmd.exe / plain shells.
$CmdShim = Join-Path $UserBin "leroy.cmd"
@"
@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "$LeroyPs1" %*
"@ | Set-Content -Path $CmdShim -Encoding ASCII

$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($userPath -notlike "*$UserBin*") {
    [Environment]::SetEnvironmentVariable("Path", "$userPath;$UserBin", "User")
    Say "Added $UserBin to your user PATH (open a new terminal to pick it up)."
} else {
    Say "$UserBin already on PATH."
}
Say "Registered: leroy -> $LeroyPs1"

# --- Step 5: desktop shortcuts ----------------------------------------------
Section "5/8  Desktop shortcuts"
if ($SkipShortcuts) {
    Say "Skipped (--SkipShortcuts)."
} else {
    $ShortcutsScript = Join-Path $Installer "shortcuts.ps1"
    if (Test-Path $ShortcutsScript) {
        & powershell -NoProfile -ExecutionPolicy Bypass -File $ShortcutsScript -ClaudeHome $ClaudeHome -RepoRoot $RepoRoot
    } else {
        Say "installer\shortcuts.ps1 not found - skipping shortcut creation."
    }
}

# --- Step 6: memory -> RAG integration --------------------------------------
Section "6/8  Memory + RAG integration"
$MemMigrate = Join-Path $Installer "memory_migrate.py"
if (Test-Path $MemMigrate) {
    & $py $MemMigrate
    if ($LASTEXITCODE -ne 0) {
        Say "(RAG indexing didn't complete - your memory vault is untouched. Re-run 'python installer\memory_migrate.py' once the RAG sidecar is up.)"
    }
} else {
    Say "installer\memory_migrate.py not found - skipping RAG indexing."
}

# --- Step 7: the interview --------------------------------------------------
Section "7/8  Get-to-know-you interview"
if ($SkipInit) {
    Say "Skipped (--SkipInit). Run 'leroy init' whenever you're ready."
} else {
    & $py (Join-Path $Installer "wizard.py")
}

# --- Step 8: you're live ----------------------------------------------------
Section "8/8  You're live"
Write-Host ""
Write-Host "  +--------------------------------------------------------------+" -ForegroundColor Green
Write-Host "  |  LeRoy is installed. Welcome aboard.                         |" -ForegroundColor Green
Write-Host "  |                                                              |" -ForegroundColor Green
Write-Host "  |   Start a session ....... leroy                              |" -ForegroundColor Green
Write-Host "  |   Health check .......... leroy doctor                       |" -ForegroundColor Green
Write-Host "  |   See your memory ....... leroy memory                       |" -ForegroundColor Green
Write-Host "  |   Desktop app (beta) .... leroy start                        |" -ForegroundColor Green
Write-Host "  |   Update later .......... leroy update                       |" -ForegroundColor Green
Write-Host "  |   Undo everything ....... leroy reset                        |" -ForegroundColor Green
Write-Host "  |                                                              |" -ForegroundColor Green
Write-Host "  |  Your memory lives at ~\.claude\memory\                      |" -ForegroundColor Green
Write-Host "  |  (Open a NEW terminal so 'leroy' is on your PATH.)           |" -ForegroundColor Green
Write-Host "  |  From here on, use your 'Leroy CLI' Desktop shortcut.        |" -ForegroundColor Green
Write-Host "  +--------------------------------------------------------------+" -ForegroundColor Green
Write-Host ""

# --- Star nudge --------------------------------------------------------------
Write-Host "  If LeRoy earns its keep, a star helps other people find it:" -ForegroundColor Yellow
Write-Host "    https://github.com/Zeekeey-jpeg/LeRoy-HQ" -ForegroundColor Yellow
$openStar = Read-Host "  Open that page in your browser now? (y/N)"
if ($openStar -match '^[Yy]') {
    Start-Process "https://github.com/Zeekeey-jpeg/LeRoy-HQ"
}
Write-Host ""
