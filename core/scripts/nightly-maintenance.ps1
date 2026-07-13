# nightly-maintenance.ps1 — Leroy nightly housekeeping (registered: Leroy-Nightly-Maintenance, 02:30 daily)
#
# Split out of nightly-backup.ps1 on 2026-07-01 when Brian moved to manual-only
# doomsday backups (see skills/routines/backup-reminder.md). This script keeps the
# non-push housekeeping that nightly-backup.ps1 used to bundle in, with EVERY git
# push and HQ whitehat/publish step removed:
#   1. Zip snapshot of single-source-of-truth state -> ~\Backups\leroy\
#      (uncommitted work in both repos captured as git-diff patches — read-only,
#      no push, no commit)
#   2. Log janitor: prune backend log litter + old snapshots
#   3. RAG sidecar nightly reindex
#   4. Skill index nightly rebuild
#
# ── WHAT THIS SCRIPT NEVER DOES ─────────────────────────────────────────────────
#   No `git push`, no `git commit`, no build-public.py, no HQ scan, no PR. Private
#   and HQ pushes are 100% manual now (skills/routines/backup-reminder.md §A/§B/§C).
#   Do not add push/publish logic back into this script — put it in a separate,
#   explicitly-invoked flow instead.
#
# PowerShell 5.1 compatible. Safe to run manually:  powershell -File nightly-maintenance.ps1
# Dry-run the whole script (no real network calls):  powershell -File nightly-maintenance.ps1 -DryRun

param(
    [switch]$DryRun
)

$ErrorActionPreference = "Continue"
$stamp   = Get-Date -Format "yyyyMMdd-HHmm"
$claude  = "~/.claude"
$pwa     = "~/.claude\memory\Projects\leroy-pwa-app"
$dest    = "~\Backups\leroy"
$logFile = Join-Path $dest "nightly-maintenance.log"

New-Item -ItemType Directory -Force -Path $dest | Out-Null
function Log($msg) {
    $line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $msg"
    Add-Content -Path $logFile -Value $line -Encoding utf8
    Write-Output $line
}

Log "=== nightly maintenance start ==="

# ── 1. State snapshot (read-only — no git push) ────────────────────────────────
$staging = Join-Path $env:TEMP "leroy-maint-$stamp"
New-Item -ItemType Directory -Force -Path $staging | Out-Null

$targets = @(
    @{ src = "$pwa\backend\data";          name = "backend-data" },
    @{ src = "$claude\session\boardroom";  name = "boardroom" },
    @{ src = "$claude\session\state.json"; name = "session-state" },
    @{ src = "$pwa\backend\auth_config.json"; name = "auth-config" }
)
foreach ($t in $targets) {
    if (Test-Path $t.src) {
        $to = Join-Path $staging $t.name
        if ((Get-Item $t.src) -is [System.IO.DirectoryInfo]) {
            robocopy $t.src $to /E /R:1 /W:1 /NFL /NDL /NJH /NJS `
                /XD worktrees portraits _scratch-merge-test node_modules __pycache__ | Out-Null
        } else {
            New-Item -ItemType Directory -Force -Path $staging | Out-Null
            Copy-Item $t.src (Join-Path $staging ($t.name + [System.IO.Path]::GetExtension($t.src)))
        }
    } else {
        Log "WARN: missing target $($t.src)"
    }
}

# Uncommitted work captured as patches inside the snapshot — read-only, never pushed.
git -C $claude diff HEAD 2>$null | Out-File (Join-Path $staging "claude-dirty.patch") -Encoding utf8
git -C $pwa    diff HEAD 2>$null | Out-File (Join-Path $staging "pwa-dirty.patch") -Encoding utf8
git -C $claude log --oneline -5 2>$null | Out-File (Join-Path $staging "claude-head.txt") -Encoding utf8
git -C $pwa    log --oneline -5 2>$null | Out-File (Join-Path $staging "pwa-head.txt") -Encoding utf8

$zip = Join-Path $dest "leroy-state-$stamp.zip"
try {
    Compress-Archive -Path "$staging\*" -DestinationPath $zip -Force
    $size = [math]::Round((Get-Item $zip).Length / 1MB, 1)
    Log "snapshot OK: $zip (${size}MB)"
} catch {
    Log "ERROR: snapshot failed: $_"
}
Remove-Item -Recurse -Force $staging -ErrorAction SilentlyContinue

# ── 2. Janitor ────────────────────────────────────────────────────────────────
# Snapshots: keep 14 days
Get-ChildItem $dest -Filter "leroy-state-*.zip" | Where-Object {
    $_.LastWriteTime -lt (Get-Date).AddDays(-14)
} | ForEach-Object { Log "prune snapshot: $($_.Name)"; Remove-Item $_.FullName -Force }

# Backend log litter: be-*.log / uvicorn-*.log older than 7 days
Get-ChildItem "$pwa\backend" -Filter "*.log" -ErrorAction SilentlyContinue | Where-Object {
    $_.Name -match "^(be-|uvicorn-)" -and $_.LastWriteTime -lt (Get-Date).AddDays(-7)
} | ForEach-Object { Log "prune log: $($_.Name)"; Remove-Item $_.FullName -Force }

# Our own log: cap ~1MB
if ((Test-Path $logFile) -and ((Get-Item $logFile).Length -gt 1MB)) {
    $tail = Get-Content $logFile -Tail 500
    Set-Content -Path $logFile -Value $tail -Encoding utf8
}

# ── 3. RAG sidecar nightly reindex ───────────────────────────────────────────
if ($DryRun) {
    Log "[dry-run] would: POST http://localhost:7742/reindex {full:false}"
} else {
    try {
        $resp = Invoke-RestMethod -Uri "http://localhost:7742/reindex" -Method Post `
            -ContentType "application/json" -Body '{"full": false}' -TimeoutSec 10
        Log "rag reindex: $($resp.status)"
    } catch {
        Log "WARN: rag reindex failed (sidecar down?): $_"
    }
}

# ── 4. Skill index nightly rebuild ───────────────────────────────────────────
if ($DryRun) {
    Log "[dry-run] would: python build-skill-index.py"
} else {
    try {
        & python "~/.claude\scripts\build-skill-index.py" 2>&1 | Select-Object -Last 1 | ForEach-Object { Log "skill-index: $_" }
    } catch {
        Log "WARN: skill-index rebuild failed: $_"
    }
}

Log "=== nightly maintenance done ==="
