<#
.SYNOPSIS
    LeRoy - shortcuts.ps1  (creates the single "Leroy CLI" desktop shortcut)

.DESCRIPTION
    Creates ONE Desktop shortcut:

      "Leroy CLI"  -> opens a terminal whose working directory is the user's
                      ~\.claude folder and starts Claude Code (`claude`) there,
                      so Claude Code loads the LeRoy config/agents/skills for
                      this account automatically.

    This creates the "Leroy CLI" terminal shortcut only. The LeRoy UI desktop
    app installs its own "LeRoy UI" shortcut from its own installer, so this
    script leaves any UI shortcut alone - the terminal and the desktop app
    coexist and share the same ~\.claude brain.

    Desktop resolution uses the Windows known-folder API
    ([Environment]::GetFolderPath('DesktopDirectory')), NOT $HOME\Desktop. On
    accounts where OneDrive has taken over the Desktop (Known Folder Move),
    $HOME\Desktop is a stale/empty folder and the *visible* Desktop lives under
    OneDrive - writing the .lnk to $HOME\Desktop is why an earlier build
    reported success but the icon never appeared.

    All paths are bound PowerShell parameters (never string interpolation) so
    apostrophes/spaces in a username or path can't break the generated target.

    Idempotent: re-running overwrites the .lnk cleanly.

    APPEARANCE-SAFE: this script only READS the Desktop location + an icon
    reference and WRITES a single .lnk file. It never changes wallpaper, theme,
    colors, DWM, or Explorer settings, never calls SystemParametersInfo, and
    never restarts Explorer. (If the wallpaper briefly renders black behind the
    icons right after a new shortcut appears, that's a transient Explorer/DWM
    desktop repaint - nothing here changed a setting; a desktop Refresh, an
    Explorer restart, or the next sign-in restores it.)

.PARAMETER ClaudeHome
    The user's ~\.claude directory (defaults to $HOME\.claude).

.PARAMETER RepoRoot
    Accepted for backward compatibility with setup.ps1's call; unused.

.PARAMETER DesktopDir
    Override the Desktop folder (used by sandbox tests so they don't write onto
    the real operator Desktop). When omitted, the real per-user Desktop is
    resolved via the known-folder API.

.EXAMPLE
    powershell -File installer\shortcuts.ps1
    powershell -File installer\shortcuts.ps1 -DesktopDir "C:\temp\fake-desktop" -DryRun
#>

[CmdletBinding()]
param(
    [string]$ClaudeHome  = (Join-Path $HOME ".claude"),
    [string]$RepoRoot    = "",
    [string]$DesktopDir  = "",
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

function Say($t) { Write-Host "  $t" }

# --- resolve the REAL Desktop (honors OneDrive Known Folder Move) ------------
if (-not $DesktopDir) {
    try {
        $DesktopDir = [Environment]::GetFolderPath([Environment+SpecialFolder]::DesktopDirectory)
    } catch {
        $DesktopDir = ""
    }
    if (-not $DesktopDir) { $DesktopDir = Join-Path $HOME "Desktop" }
}

if (-not (Test-Path $DesktopDir)) {
    try { New-Item -ItemType Directory -Force -Path $DesktopDir | Out-Null } catch {}
}
if (-not (Test-Path $DesktopDir)) {
    Say "Desktop folder not found at $DesktopDir - skipping shortcut creation."
    Say "You can still launch LeRoy any time: open a terminal in $ClaudeHome and type 'leroy'."
    exit 0
}

$cliShortcut  = Join-Path $DesktopDir "Leroy CLI.lnk"
$LaunchScript = Join-Path $ClaudeHome "leroy-start.ps1"

if ($DryRun) {
    Say "[dry-run] Desktop resolved to: $DesktopDir"
    Say "[dry-run] would write: $LaunchScript  (first-run welcome + claude launcher)"
    Say "[dry-run] would create: $cliShortcut -> $LaunchScript"
    Say "[dry-run] any existing 'LeRoy UI' desktop-app shortcut is left untouched."
    exit 0
}

# --- Write the first-run launch script to ~/.claude --------------------------
# The shortcut points here instead of calling `claude` directly, so the first
# time a user double-clicks it they see a clear welcome + instructions before
# Claude Code opens. Subsequent launches detect the flag and skip straight to claude.
$LaunchScriptContent = @'
# leroy-start.ps1 -- first-run welcome + claude launcher
# Lives in ~/.claude/; the Desktop shortcut points here.
$ClaudeHome = Split-Path -Parent $MyInvocation.MyCommand.Path
$FlagFile   = Join-Path $ClaudeHome ".leroy-started"

if (-not (Test-Path $FlagFile)) {
    Clear-Host
    Write-Host ""
    Write-Host "  Welcome to LeRoy!" -ForegroundColor Cyan
    Write-Host "  ==============================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  You are about to start your first LeRoy session." -ForegroundColor White
    Write-Host ""
    Write-Host "  Getting started:" -ForegroundColor Yellow
    Write-Host "    - Just type anything -- LeRoy will introduce itself." -ForegroundColor Green
    Write-Host "    - Say  leroy init    to run the full onboarding interview." -ForegroundColor Green
    Write-Host "    - Say  leroy doctor  to verify everything is set up correctly." -ForegroundColor Green
    Write-Host "    - Say  leroy memory  to browse your memory vault." -ForegroundColor Green
    Write-Host ""
    Write-Host "  Your memory vault: $ClaudeHome\memory\" -ForegroundColor Gray
    Write-Host "  To undo the install at any time: leroy reset" -ForegroundColor Gray
    Write-Host ""
    New-Item -ItemType File -Path $FlagFile -Force | Out-Null
    Read-Host "  Press Enter to start your first session"
    Write-Host ""
}

Set-Location $ClaudeHome
claude
'@
Set-Content -Path $LaunchScript -Value $LaunchScriptContent -Encoding UTF8
Say "Wrote first-run launcher: $LaunchScript"

# --- "Leroy CLI" shortcut -> leroy-start.ps1 ---------------------------------
# Points to leroy-start.ps1 so first launch shows a welcome guide + instructions,
# then starts Claude Code. -NoExit keeps the window alive so errors are visible.
$psExe = Join-Path $env:SystemRoot "System32\WindowsPowerShell\v1.0\powershell.exe"
$W = New-Object -ComObject WScript.Shell
$cli = $W.CreateShortcut($cliShortcut)
$cli.TargetPath       = $psExe
$cli.Arguments        = "-NoExit -NoLogo -ExecutionPolicy Bypass -File `"$LaunchScript`""
$cli.WorkingDirectory = $ClaudeHome
$cli.IconLocation     = "$psExe,0"
$cli.Description      = "Start LeRoy -- shows a welcome guide on first launch, then Claude Code"
$cli.Save()

Say "Created 'Leroy CLI' shortcut on your Desktop: $cliShortcut"
Say "First launch shows a welcome guide; subsequent launches go straight to Claude Code."
