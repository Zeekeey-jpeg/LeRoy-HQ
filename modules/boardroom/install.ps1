# install.ps1 - register the leroy-boardroom module as OPT-IN (default OFF).
#
# This script only RECORDS the module and marks it disabled. It generates no
# scenes, spends no tokens, and makes no network calls. The Boardroom does
# nothing until you explicitly enable it:
#
#     leroy enable boardroom      # start convening
#     leroy disable boardroom     # pause (or create the kill-switch flag below)
#
# The Boardroom is TOKEN-HEAVY (every scene is a full model call). A flat-rate
# plan (e.g. Claude Max) is recommended over metered API billing.

$ErrorActionPreference = "Stop"

$Module      = "boardroom"
$SrcDir      = Split-Path -Parent $MyInvocation.MyCommand.Path
$ClaudeHome  = if ($env:CLAUDE_HOME) { $env:CLAUDE_HOME } else { Join-Path $HOME ".claude" }
$ModulesDir  = Join-Path $ClaudeHome "modules"
$StateDir    = Join-Path $ClaudeHome "state\boardroom"
$Registry    = Join-Path $ClaudeHome "modules.json"
$KillSwitch  = Join-Path $StateDir "boardroom.disabled"

New-Item -ItemType Directory -Force -Path $ModulesDir, $StateDir | Out-Null

# Copy the module into ~/.claude/modules/boardroom (idempotent).
$DestDir = Join-Path $ModulesDir $Module
New-Item -ItemType Directory -Force -Path $DestDir | Out-Null
Copy-Item -Path (Join-Path $SrcDir "*") -Destination $DestDir -Recurse -Force

# Record enablement = false in a simple JSON registry (default OFF).
if (-not (Test-Path $Registry)) {
    '{ "modules": {} }' | Out-File -FilePath $Registry -Encoding utf8
}
$reg = Get-Content $Registry -Raw | ConvertFrom-Json
if (-not $reg.modules) {
    $reg | Add-Member -NotePropertyName modules -NotePropertyValue (New-Object PSObject) -Force
}
$entry = [PSCustomObject]@{
    enabled      = $false
    installed_at = (Get-Date).ToUniversalTime().ToString("o")
    token_heavy  = $true
}
$reg.modules | Add-Member -NotePropertyName $Module -NotePropertyValue $entry -Force
($reg | ConvertTo-Json -Depth 8) | Out-File -FilePath $Registry -Encoding utf8

# Ensure the kill switch is present until the user opts in. Enabling removes it.
if (-not (Test-Path $KillSwitch)) { New-Item -ItemType File -Path $KillSwitch | Out-Null }

Write-Host ""
Write-Host "leroy-boardroom installed - DISABLED (opt-in, token-heavy)."
Write-Host ""
Write-Host "  Enable:   leroy enable boardroom"
Write-Host "  Disable:  leroy disable boardroom"
Write-Host "  Kill now: New-Item -ItemType File '$KillSwitch'"
Write-Host ""
Write-Host "  Registry: $Registry"
Write-Host "  State:    $StateDir"
Write-Host "  Config:   $(Join-Path $DestDir 'config')"
Write-Host ""
Write-Host "Recommended on a flat-rate plan (e.g. Claude Max). Nothing runs until enabled."
