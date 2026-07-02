# leroy-security installer (Windows) - refuses to install without authorized-use consent.
$ErrorActionPreference = 'Stop'
$dir = Split-Path -Parent $MyInvocation.MyCommand.Path
Write-Output "----------------------------------------------------------"
Get-Content (Join-Path $dir 'ACKNOWLEDGMENT.md') | Write-Output
Write-Output "----------------------------------------------------------"
$ans = Read-Host "Type 'I AGREE' to confirm authorized-use only"
if ($ans -ne 'I AGREE') { Write-Output 'Not installed. The security module requires authorized-use consent.'; exit 1 }
$dest = Join-Path $env:USERPROFILE '.claude\skills\security'
New-Item -ItemType Directory -Force -Path $dest | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $env:USERPROFILE '.claude\config') | Out-Null
Copy-Item (Join-Path $dir 'skills\*') $dest -Recurse -Force
"$(Get-Date -Format o) consent=I_AGREE" | Out-File -Encoding utf8 (Join-Path $env:USERPROFILE '.claude\config\security-consent.txt')
Write-Output 'leroy-security installed to ~/.claude/skills/security. Use only where you are authorized.'
