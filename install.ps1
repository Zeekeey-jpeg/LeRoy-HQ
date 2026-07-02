<#
.SYNOPSIS
    LeRoy — install.ps1  (the ONE command: paste, run, done)

.DESCRIPTION
    This is the remote-hosted target of the README's one-liner:

        irm https://raw.githubusercontent.com/Zeekeey-jpeg/LeRoy-HQ/main/install.ps1 | iex

    Unlike setup.ps1 (which assumes you're already inside a clone), this script
    is the true "one command" bootstrap (item 3 / G1):

      1. Check for git (fail with a clear fix if missing — nothing else works
         without it).
      2. Pick an install directory (default: %USERPROFILE%\LeRoy-HQ; override
         with -InstallDir).
      3. git clone -b main (item 33 / G8 — main is the ONLY branch this ever
         clones or tracks).
      4. cd in and invoke setup.ps1, forwarding -SkipInit / -SkipDeps.

    Safe to re-run: if the install directory already contains a LeRoy clone,
    this re-uses it (git pull --ff-only) instead of failing or clobbering.

    Nothing here touches ~\.claude directly — that is entirely setup.ps1 +
    installer\merge.py's job (backup-first, additive). This script only gets
    the code onto disk and hands off.

.PARAMETER InstallDir
    Where to clone the LeRoy-HQ repo. Default: $HOME\LeRoy-HQ.

.PARAMETER RepoUrl
    Override the source repo (mainly for testing forks). Default is the public
    LeRoy-HQ repo.

.EXAMPLE
    irm https://leroy.helpmebim.com/install.ps1 | iex
    .\install.ps1 -InstallDir "D:\Tools\LeRoy" -SkipInit
#>

[CmdletBinding()]
param(
    [string]$InstallDir = (Join-Path $HOME "LeRoy-HQ"),
    [string]$RepoUrl    = "https://github.com/Zeekeey-jpeg/LeRoy-HQ.git",
    [switch]$SkipInit,
    [switch]$SkipDeps
)

$ErrorActionPreference = "Stop"

function Section($t) { Write-Host ""; Write-Host "== $t ==" -ForegroundColor Cyan }
function Say($t)     { Write-Host "  $t" }

Write-Host ""
Write-Host "  LeRoy one-command install" -ForegroundColor Green
Write-Host "  This will: clone LeRoy -> $InstallDir, then run setup." -ForegroundColor Green

# --- Step 1: git is the one hard requirement for THIS script ----------------
Section "1/3  Checking for git"
$git = Get-Command git -ErrorAction SilentlyContinue
if (-not $git) {
    Say "git wasn't found on PATH."
    Say "Install it from https://git-scm.com/downloads, then re-run this command."
    Say "(Everything else — Python, Node, Claude Code — is checked next, inside setup.)"
    exit 1
}
Say "git found: $($git.Source)"

# --- Step 2: clone (or reuse) -b main ----------------------------------------
Section "2/3  Getting the code (branch: main)"
if (Test-Path (Join-Path $InstallDir ".git")) {
    Say "Existing LeRoy checkout found at $InstallDir — updating instead of re-cloning."
    Push-Location $InstallDir
    try {
        $branch = (& git rev-parse --abbrev-ref HEAD).Trim()
        if ($branch -ne "main") {
            Say "Checkout was on '$branch' — switching to 'main' (the only user-facing branch)."
            & git checkout main
        }
        & git pull --ff-only
        if ($LASTEXITCODE -ne 0) {
            Say "git pull failed (local changes in the way?). Resolve manually, or delete $InstallDir and re-run."
            exit $LASTEXITCODE
        }
    } finally { Pop-Location }
} else {
    if (Test-Path $InstallDir) {
        Say "$InstallDir exists but isn't a LeRoy git checkout."
        Say "Pick a different -InstallDir, or remove that folder and re-run."
        exit 1
    }
    Say "Cloning $RepoUrl (branch: main) into $InstallDir ..."
    & git clone -b main $RepoUrl $InstallDir
    if ($LASTEXITCODE -ne 0) {
        Say "git clone failed — check your network connection and the repo URL, then re-run."
        exit $LASTEXITCODE
    }
}
Say "Code is at: $InstallDir (tracking main)"

# --- Step 3: hand off to setup.ps1 ------------------------------------------
Section "3/3  Handing off to setup"
$setup = Join-Path $InstallDir "setup.ps1"
if (-not (Test-Path $setup)) {
    Say "setup.ps1 not found in the cloned repo at $setup — clone may be incomplete."
    exit 1
}

$setupArgs = @()
if ($SkipInit) { $setupArgs += "-SkipInit" }
if ($SkipDeps) { $setupArgs += "-SkipDeps" }

Push-Location $InstallDir
try {
    & powershell -NoProfile -ExecutionPolicy Bypass -File $setup @setupArgs
    exit $LASTEXITCODE
} finally { Pop-Location }
