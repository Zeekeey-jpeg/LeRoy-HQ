<#
.SYNOPSIS
    LeRoy - shortcuts.ps1  (creates both Desktop shortcuts: "Leroy CLI" + "LeRoy UI")

.DESCRIPTION
    Creates up to two Desktop shortcuts:

      "Leroy CLI"  -> opens a terminal whose working directory is the user's
                      ~\.claude folder and starts Claude Code (`claude`) there,
                      so Claude Code loads the LeRoy config/agents/skills for
                      this account automatically. Always created.

      "LeRoy UI"   -> launches the installed LeRoy UI desktop app. Only
                      created if the app is actually found installed (via
                      -UiExePath, or auto-detected under
                      %LOCALAPPDATA%\Programs\LeRoy UI\ / the HKCU uninstall
                      registry for a custom install dir). Running this script
                      from setup.ps1 before the Electron app has ever been
                      installed simply skips this shortcut - it is NOT an
                      error, and re-running later (e.g. from the Electron
                      installer's own post-install hook, which passes
                      -UiExePath explicitly) creates it retroactively.

    Both shortcuts use the SAME Known-Folder-safe Desktop resolution, so
    neither one is exempt from the OneDrive fix below.

    Desktop resolution uses the Windows known-folder API
    ([Environment]::GetFolderPath('DesktopDirectory')), NOT $HOME\Desktop. On
    accounts where OneDrive has taken over the Desktop (Known Folder Move),
    $HOME\Desktop is a stale/empty folder and the *visible* Desktop lives under
    OneDrive - writing the .lnk to $HOME\Desktop is why an earlier build
    reported success but the icon never appeared. (Historically this script
    only fixed that for "Leroy CLI" - electron-builder's own NSIS shortcut
    logic for "LeRoy UI" was never verified against the same failure mode,
    which is why a from-the-.exe install could show zero Desktop icons even
    though the installer reported success.)

    All paths are bound PowerShell parameters (never string interpolation) so
    apostrophes/spaces in a username or path can't break the generated target.

    Idempotent: re-running deletes-by-exact-filename then recreates each .lnk
    cleanly, so upgrading from an older build's shortcut never leaves a stale
    duplicate behind.

    APPEARANCE-SAFE: this script only READS the Desktop location + icon
    references and WRITES .lnk files. It never changes wallpaper, theme,
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

.PARAMETER UiExePath
    Path to the installed "LeRoy UI.exe". Pass this explicitly from the
    Electron installer's post-install hook (it knows exactly where it just
    placed files). When omitted, this script tries to auto-detect an existing
    install; if none is found, the "LeRoy UI" shortcut is skipped (not an
    error - see DESCRIPTION).

.EXAMPLE
    powershell -File installer\shortcuts.ps1
    powershell -File installer\shortcuts.ps1 -UiExePath "C:\...\LeRoy UI.exe"
    powershell -File installer\shortcuts.ps1 -DesktopDir "C:\temp\fake-desktop" -DryRun
#>

[CmdletBinding()]
param(
    [string]$ClaudeHome  = (Join-Path $HOME ".claude"),
    [string]$RepoRoot    = "",
    [string]$DesktopDir  = "",
    [string]$UiExePath   = "",
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

function Say($t) { Write-Host "  $t" }
function Warn($t) { Write-Host "  ! $t" -ForegroundColor Yellow }

# --- resolve the REAL Desktop (honors OneDrive Known Folder Move) ------------
if (-not $DesktopDir) {
    try {
        $DesktopDir = [Environment]::GetFolderPath([Environment+SpecialFolder]::DesktopDirectory)
    } catch {
        $DesktopDir = ""
    }
    if (-not $DesktopDir) { $DesktopDir = Join-Path $HOME "Desktop" }
}

# --- warn (never block) if the profile itself lives inside a OneDrive tree ---
# The Known-Folder Desktop resolution above already fixes shortcut placement
# regardless of this; this is just a heads-up for anything else (e.g. the
# ~\.claude install target) that might assume $HOME is a plain local path.
foreach ($odVar in @("OneDrive", "OneDriveConsumer", "OneDriveCommercial")) {
    $odPath = [Environment]::GetEnvironmentVariable($odVar)
    if ($odPath -and $HOME -like "$odPath*") {
        Warn "Your Windows profile ($HOME) is inside a OneDrive-managed folder ($odVar=$odPath)."
        Warn "Shortcuts still resolve correctly via the known-folder API - this is informational only."
        break
    }
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
$uiShortcut   = Join-Path $DesktopDir "LeRoy UI.lnk"
$LaunchScript = Join-Path $ClaudeHome "leroy-start.ps1"

# --- locate the installed LeRoy UI app (unless the caller already told us) ---
if (-not $UiExePath) {
    $guess = Join-Path $env:LOCALAPPDATA "Programs\LeRoy UI\LeRoy UI.exe"
    if (Test-Path $guess) {
        $UiExePath = $guess
    } else {
        # Fall back to the per-user uninstall registry, in case the app was
        # installed to a custom directory (electron-builder's NSIS target
        # allows the user to change the install location).
        $uninstKeys = @(
            "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\LeRoy UI",
            "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\{*LeRoy*}"
        )
        foreach ($k in $uninstKeys) {
            $hit = Get-ItemProperty -Path $k -ErrorAction SilentlyContinue | Select-Object -First 1
            if ($hit -and $hit.InstallLocation) {
                $candidate = Join-Path $hit.InstallLocation "LeRoy UI.exe"
                if (Test-Path $candidate) { $UiExePath = $candidate; break }
            }
        }
    }
}
$haveUiExe = [bool]($UiExePath -and (Test-Path $UiExePath))

if ($DryRun) {
    Say "[dry-run] Desktop resolved to: $DesktopDir"
    Say "[dry-run] would write: $LaunchScript  (first-run welcome + claude launcher)"
    Say "[dry-run] would create: $cliShortcut -> $LaunchScript"
    if ($haveUiExe) {
        Say "[dry-run] would create: $uiShortcut -> $UiExePath"
    } else {
        Say "[dry-run] LeRoy UI.exe not found - would skip the 'LeRoy UI' shortcut."
    }
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

# --- shared shortcut writer ---------------------------------------------------
# Deletes any existing .lnk by exact filename first, so re-running (or
# upgrading from an older build that made the same shortcut a different way)
# never leaves a stale duplicate on the Desktop.
$W = New-Object -ComObject WScript.Shell
function New-LeroyShortcut([string]$Path, [string]$TargetPath, [string]$Arguments, [string]$WorkingDirectory, [string]$IconLocation, [string]$Description) {
    if (Test-Path $Path) { Remove-Item -Path $Path -Force -ErrorAction SilentlyContinue }
    $sc = $W.CreateShortcut($Path)
    $sc.TargetPath       = $TargetPath
    if ($Arguments)        { $sc.Arguments        = $Arguments }
    if ($WorkingDirectory) { $sc.WorkingDirectory = $WorkingDirectory }
    if ($IconLocation)     { $sc.IconLocation     = $IconLocation }
    $sc.Description       = $Description
    $sc.Save()
}

# --- "Leroy CLI" shortcut -> leroy-start.ps1 ---------------------------------
# Points to leroy-start.ps1 so first launch shows a welcome guide + instructions,
# then starts Claude Code. -NoExit keeps the window alive so errors are visible.
$psExe = Join-Path $env:SystemRoot "System32\WindowsPowerShell\v1.0\powershell.exe"
New-LeroyShortcut -Path $cliShortcut -TargetPath $psExe `
    -Arguments "-NoExit -NoLogo -ExecutionPolicy Bypass -File `"$LaunchScript`"" `
    -WorkingDirectory $ClaudeHome -IconLocation "$psExe,0" `
    -Description "Start LeRoy -- shows a welcome guide on first launch, then Claude Code"

Say "Created 'Leroy CLI' shortcut on your Desktop: $cliShortcut"
Say "First launch shows a welcome guide; subsequent launches go straight to Claude Code."

# --- "LeRoy UI" shortcut -> the installed desktop app -------------------------
if ($haveUiExe) {
    New-LeroyShortcut -Path $uiShortcut -TargetPath $UiExePath `
        -WorkingDirectory (Split-Path -Parent $UiExePath) -IconLocation "$UiExePath,0" `
        -Description "Launch the LeRoy UI desktop app"
    Say "Created 'LeRoy UI' shortcut on your Desktop: $uiShortcut"
} else {
    Say "LeRoy UI app not found yet - skipping the 'LeRoy UI' Desktop shortcut."
    Say "It will be created automatically once the LeRoy UI app is installed."
}
