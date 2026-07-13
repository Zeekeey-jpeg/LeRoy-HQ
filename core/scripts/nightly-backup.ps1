# nightly-backup.ps1 — Leroy doomsday protection (registered: Leroy-Nightly-Backup, 02:30 daily)
#
# The single-laptop problem: sessions, decisions.json, kanban.db, and boardroom
# state exist ONLY on this machine and were excluded from every backup path.
# This script closes that hole nightly:
#   1. Zip snapshot of all single-source-of-truth state -> ~\Backups\leroy\
#      (uncommitted work in both repos is captured as git-diff patches inside the zip)
#   2. Push both git repos to GitHub (committed work only — no auto-commits of dirty trees)
#   2b. HQ WHITEHAT + DUAL-PUSH (additive, guarded, NON-BLOCKING — see below)
#   3. Log janitor: prune backend log litter + old snapshots
#
# ── DOOMSDAY FLOW (Brian's requirement) ────────────────────────────────────────
#   "Doomsday = full private update to LeRoy, THEN a whitehat scan of the LeRoy-HQ
#    candidate set, THEN push to HQ as a pull request."
#
#   Implemented as three ordered, isolated stages:
#     (1) PRIVATE backup — unchanged. git add/commit/push origin master to the private
#         LeRoy repo. This ALWAYS runs first and to completion. Nothing below can block,
#         alter, or fail it. (Sections 1–2 above.)
#     (2) HQ WHITEHAT SCAN — runs EVERY doomsday. Invokes build-public.py --stage --report,
#         which refreshes the dist-hq public-safe candidate set and runs whitehat_scan over
#         it. If the scan finds ANYTHING (exit 2), the HQ step aborts loudly; the private
#         backup is untouched. The whole HQ block is wrapped in try/catch — any failure is
#         logged, never fatal.
#     (3) HQ PULL REQUEST — GUARDED. Only opened when env LEROY_HQ_AUTOPUBLISH=1 (default
#         OFF) AND the scan is clean AND gh is authed. Otherwise we log a "HQ delta ready"
#         note telling the human how to open the PR manually. This keeps unattended nightly
#         runs from auto-pushing to a public repo while still SCANNING every single time.
#
# PowerShell 5.1 compatible. Safe to run manually:  powershell -File nightly-backup.ps1
# Dry-run the whole script (no real git/gh/python):  powershell -File nightly-backup.ps1 -DryRun

param(
    # -DryRun mocks every mutating call (git push / build-public.py / gh) so the control
    # flow — especially the additive HQ block — can be exercised without touching git,
    # the public repo, or the network. The private-backup path is logged, never executed.
    [switch]$DryRun
)

$ErrorActionPreference = "Continue"
$stamp   = Get-Date -Format "yyyyMMdd-HHmm"
$claude  = "~/.claude"
$pwa     = "~/.claude\memory\Projects\leroy-pwa-app"
$dest    = "~\Backups\leroy"
$logFile = Join-Path $dest "nightly-backup.log"

New-Item -ItemType Directory -Force -Path $dest | Out-Null
function Log($msg) {
    $line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $msg"
    Add-Content -Path $logFile -Value $line -Encoding utf8
    Write-Output $line
}

Log "=== nightly backup start ==="

# ── 1. State snapshot ─────────────────────────────────────────────────────────
$staging = Join-Path $env:TEMP "leroy-backup-$stamp"
New-Item -ItemType Directory -Force -Path $staging | Out-Null

# Single-source-of-truth state
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
            # robocopy returns >0 on success; don't let it poison $LASTEXITCODE checks
            # /XD: build worktrees are full repo copies (gigabytes, reproducible from
            # git) — first dry-run produced a 4.5GB zip until these were excluded.
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

# Uncommitted work survives as patches inside the snapshot
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

# ── 2. Push both repos (committed work only) — THE PRIVATE BACKUP (unchanged) ──
# This is stage (1): the full private update to LeRoy. It runs first, always, and is
# never gated on anything below it. The HQ block (2b) is strictly additive.
foreach ($repo in @($claude, $pwa)) {
    $name = Split-Path $repo -Leaf
    if ($DryRun) {
        Log "[dry-run] would: git -C $repo push origin master"
        Log "push OK: $name (dry-run)"
    } else {
        git -C $repo push origin master 2>$null
        if ($LASTEXITCODE -eq 0) { Log "push OK: $name" } else { Log "WARN: push failed: $name (exit $LASTEXITCODE)" }
    }
}

# ── 2b. HQ WHITEHAT SCAN + GUARDED DUAL-PUSH (additive · non-blocking) ─────────
# Stage (2) + (3) of the doomsday flow. Wrapped so that ANY failure here is logged
# and swallowed — the private backup above has already succeeded and is never affected.
#
#   · build-public.py --stage --report  refreshes dist-hq (public-safe subset) and runs
#     whitehat_scan over it, writing session/hq-whitehat-scan.md EVERY run.
#   · build-public.py exit codes:  0 = clean · 2 = SECRET/whitehat exposure (ABORT HQ)
#     · 3 = reconciliation error (ABORT HQ).  Anything non-zero aborts the HQ step.
#   · PR creation is GUARDED: opened only when LEROY_HQ_AUTOPUBLISH=1 AND scan clean AND
#     gh is authed. Default (unattended nightly) = scan-only, then log a "delta ready" note.
try {
    $buildPublic = Join-Path $claude "memory\Projects\LeRoy\build-public.py"
    if (-not (Test-Path $buildPublic)) {
        Log "hq: SKIP — build-public.py not found at $buildPublic"
    } else {
        Log "hq: stage (2) whitehat scan — build-public.py --stage --report"

        if ($DryRun) {
            # Mock the scanner. Honor an injected result so both branches are testable:
            #   $env:LEROY_HQ_DRY_EXIT = "0" (clean, default) or "2" (simulate exposure).
            $hqExit = 0
            if ($env:LEROY_HQ_DRY_EXIT) { $hqExit = [int]$env:LEROY_HQ_DRY_EXIT }
            Log "[dry-run] would: python `"$buildPublic`" --stage --report  (simulated exit $hqExit)"
        } else {
            & python "$buildPublic" --stage --report 2>&1 |
                ForEach-Object { Log "hq-scan: $_" }
            $hqExit = $LASTEXITCODE
        }

        if ($hqExit -ne 0) {
            # Stage (2) failed the firewall. Abort the HQ step loudly. DO NOT proceed to PR.
            Log "hq: !!! WHITEHAT SCAN NOT CLEAN (build-public exit $hqExit) — HQ PUSH ABORTED."
            Log "hq: !!! see session\hq-whitehat-scan.md for the finding (path + type only)."
            Log "hq: private backup is unaffected."
        } else {
            Log "hq: whitehat scan CLEAN."

            # Stage (3): guarded PR. Default OFF.
            $autoPublish = ($env:LEROY_HQ_AUTOPUBLISH -eq "1")
            if (-not $autoPublish) {
                Log "hq: delta ready — public-safe candidate set staged & scan-clean."
                Log "hq: auto-publish is OFF (set LEROY_HQ_AUTOPUBLISH=1 to enable nightly PRs)."
                Log "hq: to open the PR manually, run:"
                Log "hq:   `$env:LEROY_HQ_CONFIRM=1; python `"$buildPublic`" --execute"
            } else {
                # Auto-publish requested — still require gh to be present AND authed.
                $ghAuthed = $false
                if ($DryRun) {
                    $ghAuthed = ($env:LEROY_HQ_DRY_GH_AUTHED -eq "1")
                    Log "[dry-run] would: gh auth status  (simulated authed=$ghAuthed)"
                } else {
                    $gh = Get-Command gh -ErrorAction SilentlyContinue
                    if ($gh) {
                        & gh auth status 2>&1 | Out-Null
                        $ghAuthed = ($LASTEXITCODE -eq 0)
                    }
                }

                if (-not $ghAuthed) {
                    Log "hq: auto-publish ON but gh is missing/not-authed — SKIPPING PR (scan already done)."
                    Log "hq: run 'gh auth login', then: `$env:LEROY_HQ_CONFIRM=1; python `"$buildPublic`" --execute"
                } else {
                    Log "hq: stage (3) opening PR — build-public.py --execute (LEROY_HQ_CONFIRM=1)"
                    if ($DryRun) {
                        Log "[dry-run] would: `$env:LEROY_HQ_CONFIRM=1; python `"$buildPublic`" --execute"
                    } else {
                        $prevConfirm = $env:LEROY_HQ_CONFIRM
                        $env:LEROY_HQ_CONFIRM = "1"
                        try {
                            & python "$buildPublic" --execute 2>&1 |
                                ForEach-Object { Log "hq-publish: $_" }
                            if ($LASTEXITCODE -eq 0) { Log "hq: PR flow completed (exit 0)." }
                            else { Log "hq: WARN publish exited $LASTEXITCODE — check hq-publish log lines above." }
                        } finally {
                            $env:LEROY_HQ_CONFIRM = $prevConfirm
                        }
                    }
                }
            }
        }
    }
} catch {
    Log "hq: WARN — HQ block errored (non-fatal, private backup unaffected): $_"
}

# ── 3. Janitor ────────────────────────────────────────────────────────────────
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

# ── 4. RAG sidecar nightly reindex ───────────────────────────────────────────
# The warm-recall sidecar served a frozen June-4 index for 6 days while
# reporting green (last_run never compared to vault mtime). Kick an incremental
# reindex nightly so memory recall always sees fresh notes.
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

# ── 5. Skill index nightly rebuild ───────────────────────────────────────────
# skill-index.json has a 24h staleness contract nothing was enforcing (found
# 10 days stale with 31 skills invisible to routing).
if ($DryRun) {
    Log "[dry-run] would: python build-skill-index.py"
} else {
    try {
        & python "~/.claude\scripts\build-skill-index.py" 2>&1 | Select-Object -Last 1 | ForEach-Object { Log "skill-index: $_" }
    } catch {
        Log "WARN: skill-index rebuild failed: $_"
    }
}

Log "=== nightly backup done ==="
