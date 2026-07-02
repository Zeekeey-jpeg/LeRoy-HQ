<#
.SYNOPSIS
    LeRoy CLI (Windows) — dispatches leroy subcommands.

.DESCRIPTION
    Single entrypoint for the LeRoy command surface:

        leroy [chat]        Start a session (drops into Claude Code with LeRoy loaded)
        leroy init          First-run interview + build your memory vault
        leroy doctor        Health check: prereqs, MCPs, sidecar + autonomy on/off
        leroy enable <f>    Turn on an autonomy feature (and wire it)
        leroy disable <f>   Turn off an autonomy feature (and unschedule it)
        leroy add <module>  Opt-in module: boardroom | security  (memory/mesh/gate are core)
        leroy mcp add       Conversationally build a new connector
        leroy memory        Open the vault / show stats
        leroy backup        Back up ~/.claude (your remote if configured, else a local
                             zip) then auto-run housekeeping (log prune, RAG reindex)
        leroy start         Launch the desktop app (beta, desktop-only)
        leroy update        Pull upstream code (never touches your grown memory)
        leroy reset         Clean rollback (restores the pre-LeRoy backup)

    init / doctor / merge are fully wired. start / desktop are stubs that print
    what they will do.

    Paths are always derived from $HOME\.claude — nothing is hardcoded.
#>

[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [string]$Command = "chat",

    [Parameter(Position = 1, ValueFromRemainingArguments = $true)]
    [string[]]$Rest
)

$ErrorActionPreference = "Stop"

# --- path anchors -----------------------------------------------------------
# The repo root is the parent of bin\. The live config dir is $HOME\.claude.
$RepoRoot   = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
$ClaudeHome = Join-Path $HOME ".claude"
$Installer  = Join-Path $RepoRoot "installer"

function Get-Python {
    foreach ($c in @("python", "py", "python3")) {
        $cmd = Get-Command $c -ErrorAction SilentlyContinue
        if ($cmd) { return $cmd.Source }
    }
    throw "Python 3.11+ not found on PATH. Run 'leroy doctor' for how to fix."
}

function Invoke-Py([string]$Script, [string[]]$PyArgs) {
    $py = Get-Python
    $path = Join-Path $Installer $Script
    if (-not (Test-Path $path)) { throw "missing installer script: $path" }
    & $py $path @PyArgs
    return $LASTEXITCODE
}

function Say([string]$msg) { Write-Host "  $msg" }

# --- subcommands ------------------------------------------------------------
function Cmd-Doctor {
    $rc = Invoke-Py "doctor.py" $Rest
    # Follow the prereq check with the autonomy on/off summary.
    Invoke-Py "autonomy.py" @("status") | Out-Null
    exit $rc
}

function Cmd-Enable {
    if (-not $Rest -or $Rest.Count -lt 1) {
        Say "Usage: leroy enable <boardroom|morning_briefing|email_digests|scheduled_automations>"
        exit 1
    }
    exit (Invoke-Py "autonomy.py" @("enable", $Rest[0]))
}

function Cmd-Disable {
    if (-not $Rest -or $Rest.Count -lt 1) {
        Say "Usage: leroy disable <feature>"
        exit 1
    }
    exit (Invoke-Py "autonomy.py" @("disable", $Rest[0]))
}

function Cmd-Init {
    # doctor first so init never runs on a broken machine.
    Say "Running prerequisite check..."
    $rc = Invoke-Py "doctor.py" @()
    if ($rc -ne 0) {
        Say "Fix the prerequisites above, then re-run 'leroy init'."
        exit $rc
    }
    exit (Invoke-Py "wizard.py" $Rest)
}

function Cmd-Merge { exit (Invoke-Py "merge.py" $Rest) }

function Cmd-Backup { exit (Invoke-Py "backup.py" $Rest) }

function Cmd-Chat {
    $claude = Get-Command "claude" -ErrorAction SilentlyContinue
    if (-not $claude) {
        Say "Claude Code (`claude`) isn't on PATH. Run 'leroy doctor' for the install link."
        exit 1
    }
    Say "Starting a LeRoy session..."
    # Claude Code auto-loads ~/.claude, so LeRoy's CLAUDE.md/agents/skills are live.
    & $claude.Source @Rest
    exit $LASTEXITCODE
}

function Cmd-Add {
    if (-not $Rest -or $Rest.Count -lt 1) {
        Say "Usage: leroy add <boardroom|security>   (memory, mesh & gate are core — already installed)"
        exit 1
    }
    $module = $Rest[0].ToLower()
    $modSrc = Join-Path $RepoRoot (Join-Path "modules" $module)
    if (-not (Test-Path $modSrc)) {
        Say "Unknown module '$module'. Opt-in modules: boardroom, security. (memory, mesh, gate are core.)"
        exit 1
    }
    # Each module ships its own installer — it handles auth-gates (security) and
    # opt-in / default-off wiring (boardroom). Fall back to an additive merge.
    $inst = Join-Path $modSrc "install.ps1"
    if (Test-Path $inst) { & $inst; exit $LASTEXITCODE }
    Say "Adding module '$module' (additive merge)..."
    exit (Invoke-Py "merge.py" @("--source", $modSrc))
}

function Cmd-Mcp {
    if ($Rest -and $Rest[0] -eq "add") {
        $tmpl = Join-Path $RepoRoot (Join-Path "mcps" "_template")
        Say "[stub] leroy mcp add — conversational connector builder."
        Say "Will scaffold from: $tmpl"
        Say "Then start a session and say e.g. 'talk to my Notion' to wire it."
        exit 0
    }
    Say "Usage: leroy mcp add"
    exit 1
}

function Cmd-Memory {
    $vault = Join-Path $ClaudeHome "memory"
    if (-not (Test-Path $vault)) {
        Say "No vault yet. Run 'leroy init' to build one."
        exit 1
    }
    $notes = (Get-ChildItem -Path $vault -Recurse -File -Filter *.md -ErrorAction SilentlyContinue)
    $count = ($notes | Measure-Object).Count
    $bytes = ($notes | Measure-Object -Property Length -Sum).Sum
    $kb = if ($bytes) { [math]::Round($bytes / 1KB, 1) } else { 0 }
    Say "Vault: $vault"
    Say "Notes: $count markdown file(s), ~$kb KB"
    Say "Open it in your editor or Obsidian to browse."
    exit 0
}

function Cmd-Start {
    # Desktop app ships in v1.1; be clear rather than half-launch.
    Say "The LeRoy desktop app is coming in a future release (v1.1) — it's not part of this build."
    Say "LeRoy v1 is CLI-first and fully complete. Run 'leroy' to start a session."
    exit 0
}

function Cmd-Update {
    Push-Location $RepoRoot
    try {
        if (-not (Test-Path (Join-Path $RepoRoot ".git"))) {
            Say "Not a git checkout — can't self-update. Re-clone to get the latest."
            exit 1
        }
        # main is the only user-facing tracked branch (item 33). If a checkout
        # somehow ended up elsewhere, switch back before pulling rather than
        # silently fast-forwarding whatever branch happens to be checked out.
        $branch = (git rev-parse --abbrev-ref HEAD).Trim()
        if ($branch -ne "main") {
            Say "On branch '$branch', not 'main' — switching to 'main' before updating."
            git checkout main
            if ($LASTEXITCODE -ne 0) {
                Say "Could not switch to 'main' (uncommitted local changes?). Resolve manually, then re-run 'leroy update'."
                exit $LASTEXITCODE
            }
        }
        Say "Pulling upstream code (your memory vault is never touched)..."
        git pull --ff-only origin main
        if ($LASTEXITCODE -ne 0) {
            Say "Update failed — pull was not fast-forward-only safe. Resolve manually (git status), then re-run."
            exit $LASTEXITCODE
        }
        Say "Re-running additive merge to apply any new core files..."
        Invoke-Py "merge.py" @() | Out-Null
        Say "Refreshing the RAG index with any memory notes added since last update..."
        Invoke-Py "memory_migrate.py" @() | Out-Null
        Say "Update complete (main)."
        exit 0
    } finally { Pop-Location }
}

function Cmd-Reset {
    # Find the most recent backup and restore it.
    $backups = Get-ChildItem -Path (Split-Path -Parent $ClaudeHome) -Directory `
        -Filter ".claude.backup-*" -ErrorAction SilentlyContinue | Sort-Object Name -Descending
    if (-not $backups) {
        Say "No pre-LeRoy backup found (~\.claude.backup-*). Nothing to restore."
        exit 1
    }
    $latest = $backups[0].FullName
    Say "This will restore your pre-LeRoy config from:"
    Say "  $latest"
    $confirm = Read-Host "  Type 'restore' to proceed"
    if ($confirm -ne "restore") { Say "Aborted."; exit 1 }
    $stamp = Get-Date -Format "yyyy-MM-dd-HHmmss"
    if (Test-Path $ClaudeHome) {
        Rename-Item -Path $ClaudeHome -NewName ".claude.pre-reset-$stamp"
    }
    Copy-Item -Path $latest -Destination $ClaudeHome -Recurse
    Say "Restored. Your current config was moved aside to .claude.pre-reset-$stamp."
    exit 0
}

# --- dispatch ---------------------------------------------------------------
switch ($Command.ToLower()) {
    "chat"      { Cmd-Chat }
    ""          { Cmd-Chat }
    "init"      { Cmd-Init }
    "doctor"    { Cmd-Doctor }
    "enable"    { Cmd-Enable }
    "disable"   { Cmd-Disable }
    "merge"     { Cmd-Merge }
    "backup"    { Cmd-Backup }
    "add"       { Cmd-Add }
    "mcp"       { Cmd-Mcp }
    "memory"    { Cmd-Memory }
    "start"     { Cmd-Start }
    "desktop"   { Cmd-Start }
    "update"    { Cmd-Update }
    "reset"     { Cmd-Reset }
    "uninstall" { Cmd-Reset }
    default {
        Write-Host ""
        Write-Host "  leroy <command>"
        Write-Host "    (chat)      start a session       init       first-run interview"
        Write-Host "    doctor      health check          add <m>    add a module"
        Write-Host "    enable <f>  turn on a feature     disable<f> turn off a feature"
        Write-Host "    mcp add     build a connector     memory     vault stats"
        Write-Host "    backup      back up + housekeeping start      desktop app (beta)"
        Write-Host "    update      pull upstream          reset      restore pre-LeRoy backup"
        Write-Host ""
        exit 1
    }
}
