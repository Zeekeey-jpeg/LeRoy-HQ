<#
.SYNOPSIS
    LeRoy - shortcuts.ps1  (creates the two onboarding desktop shortcuts)

.DESCRIPTION
    Creates BOTH required Desktop shortcuts (item 12 / G2):

      1. "Leroy"      -> opens the web UI (the packaged desktop app), falling
                         back to a friendly "not installed yet" launcher if the
                         app isn't packaged into this checkout.
      2. "Leroy CLI"  -> opens a terminal, cd's into the user's ~\.claude, and
                         auto-runs the `leroy` CLI (Claude Code w/ LeRoy loaded).

    All paths are bound PowerShell parameters - never f-string / string-eval
    interpolation - so apostrophes, spaces, and other punctuation in usernames
    or install paths can't break the generated .lnk targets (WS5 polish item).

    Idempotent: re-running overwrites the two .lnk files cleanly.

.PARAMETER ClaudeHome
    The user's ~\.claude directory (defaults to $HOME\.claude).

.PARAMETER RepoRoot
    The LeRoy repo checkout root (defaults to the parent of this script's dir).

.PARAMETER AppEntry
    Optional path to the packaged desktop app's launch target (an .exe or a
    .cmd/.ps1 starter script). When absent, the "Leroy" shortcut launches a
    small notice instead of a broken target.

.PARAMETER DesktopDir
    Override the Desktop folder (used by WS6 sandbox tests so the stress test
    doesn't write onto the real operator Desktop).

.EXAMPLE
    powershell -File installer\shortcuts.ps1
    powershell -File installer\shortcuts.ps1 -AppEntry "C:\Users\me\.claude\app\LeRoy.exe"
    powershell -File installer\shortcuts.ps1 -DesktopDir "C:\temp\fake-desktop" -DryRun
#>

[CmdletBinding()]
param(
    [string]$ClaudeHome  = (Join-Path $HOME ".claude"),
    [string]$RepoRoot    = (Split-Path -Parent $PSScriptRoot),
    [string]$AppEntry    = "",
    [string]$DesktopDir  = (Join-Path $HOME "Desktop"),
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

function Say($t) { Write-Host "  $t" }

if (-not (Test-Path $DesktopDir)) {
    Say "Desktop folder not found at $DesktopDir - skipping shortcut creation."
    Say "You can still launch LeRoy any time: open a terminal in $ClaudeHome and type 'leroy'."
    exit 0
}

$cliShortcut = Join-Path $DesktopDir "Leroy CLI.lnk"
$uiShortcut  = Join-Path $DesktopDir "Leroy.lnk"

# Resolve a real desktop-app entry point if one is packaged into this checkout.
# WS4.8 packages the app under $RepoRoot\app\; look for the most likely launch
# targets without assuming any one of them exists yet.
if (-not $AppEntry) {
    $candidates = @(
        (Join-Path $RepoRoot "app\LeRoy.exe"),
        (Join-Path $RepoRoot "app\dist\LeRoy.exe"),
        (Join-Path $RepoRoot "app\start-app.cmd"),
        (Join-Path $RepoRoot "app\start-app.ps1")
    )
    foreach ($c in $candidates) {
        if (Test-Path $c) { $AppEntry = $c; break }
    }
}

if ($DryRun) {
    Say "[dry-run] would create: $cliShortcut  (terminal -> leroy, cwd=$ClaudeHome)"
    if ($AppEntry) {
        Say "[dry-run] would create: $uiShortcut  (target=$AppEntry)"
    } else {
        Say "[dry-run] would create: $uiShortcut  (no packaged app found -> 'coming soon' notice shortcut)"
    }
    exit 0
}

$W = New-Object -ComObject WScript.Shell

# --- "Leroy CLI" - terminal, cwd = ~/.claude, auto-runs `leroy` -------------
$psExe = Join-Path $env:SystemRoot "System32\WindowsPowerShell\v1.0\powershell.exe"
$cli = $W.CreateShortcut($cliShortcut)
$cli.TargetPath       = $psExe
$cli.Arguments        = "-NoExit -NoLogo -Command leroy"
$cli.WorkingDirectory = $ClaudeHome
$cli.IconLocation     = "$psExe,0"
$cli.Description      = "Open a terminal and start a LeRoy session"
$cli.Save()
Say "Created 'Leroy CLI' shortcut on your Desktop."

# --- "Leroy" - web UI / desktop app -----------------------------------------
$ui = $W.CreateShortcut($uiShortcut)
if ($AppEntry -and (Test-Path $AppEntry)) {
    if ($AppEntry -like "*.exe") {
        $ui.TargetPath = $AppEntry
        $ui.WorkingDirectory = Split-Path -Parent $AppEntry
    } else {
        # .cmd / .ps1 starter - launch via the interpreter, cwd at the app dir.
        $ui.TargetPath = $psExe
        $ui.Arguments  = "-NoLogo -ExecutionPolicy Bypass -File `"$AppEntry`""
        $ui.WorkingDirectory = Split-Path -Parent $AppEntry
    }
    $ui.Description = "Open the LeRoy desktop app (UI)"
    $ui.Save()
    Say "Created 'Leroy' shortcut on your Desktop (opens the desktop app)."
} else {
    # No packaged app in this checkout yet. Ship a real, non-broken shortcut
    # that explains the situation rather than pointing at nothing (never a
    # dead .lnk) - CLI-first is still fully functional via 'Leroy CLI'.
    $notice = Join-Path $ClaudeHome "installer\_ui_not_packaged_notice.cmd"
    $noticeDir = Split-Path -Parent $notice
    New-Item -ItemType Directory -Force -Path $noticeDir | Out-Null
    @'
@echo off
echo.
echo   The LeRoy desktop app isn't packaged into this checkout yet.
echo   LeRoy is CLI-first and fully working right now: use the "Leroy CLI"
echo   shortcut, or open a terminal anywhere and type "leroy".
echo.
pause
'@ | Set-Content -Path $notice -Encoding ASCII
    $ui.TargetPath       = $notice
    $ui.WorkingDirectory = $ClaudeHome
    $ui.Description      = "LeRoy desktop app (not yet packaged in this build)"
    $ui.Save()
    Say "Created 'Leroy' shortcut on your Desktop (desktop app not packaged yet - shows a friendly notice; use 'Leroy CLI' for now)."
}

Say "Both shortcuts are on your Desktop: 'Leroy' and 'Leroy CLI'."
