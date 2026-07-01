---
user-invocable: false
disable-model-invocation: true
---

# Leroy Improve — System Health Audit Skill

## Triggers
- "leroy audit", "system health", "improve leroy", "run improve" → Run audit on demand
- "🔧 Improve" button in Telegram → Fires `_leroy_improve_thread` in telegram-bot.py
- Task Scheduler: `your org-LeroyImprove` — daily 7:00 AM, every day (including weekends)

---

## Purpose

Leroy Improve audits the *gears* of the Leroy system — not how the user uses it (that's Dream), but whether what was built is actually running.

**Distinct from Dream:**
- Dream → 24h interaction scan → suggests new skills/agents to build
- Improve → system health scan → flags broken/degraded/misaligned infrastructure

**Key motivating failure pattern:** A system is architected, deployed, and appears "working" but is silently blocked (example: continuous memory pipeline stalled). Improve catches this.

---

## What It Checks (4 Core + Auto-Discovered)

### Core Verticals (always run)

| Vertical | What it audits |
|----------|---------------|
| Agents & Skills | Skill orphans, dead agent refs, cold skill usage (30d), new agents from topology delta |
| Memory / RAG | Sidecar health (localhost:7742), consolidation freshness, index staleness, note count regression |
| MCPs | Configured MCP list vs. log activity, key MCPs (email-primary, crm, memory) |
| Autonomous Builds | Cron last-fire dates, Task Scheduler your org-* tasks, duplicate PID detection |

### Dynamic Verticals (auto-discovered via Phase 0)

Phase 0 runs before every audit. It walks the `.claude/` tree and diffs against `memory/LeroyImprove/system-manifest.json`.

When 3+ new files share a naming prefix (any protocol family — linguistic, sub-agent, mesh, etc.):
1. New vertical auto-generated via `claude -p` for health check design
2. Vertical added to `memory/LeroyImprove/verticals.json` → persists to future runs
3. Reported in Telegram as `🆕 {Protocol Name} — {score}/100`

This means Improve self-expands as Leroy grows — no manual update required.

---

## Execution

```bash
python scripts/leroy-improve.py              # print report only
python scripts/leroy-improve.py --telegram   # print + send to Telegram
```

**Script:** `scripts/leroy-improve.py`
**Runtime target:** <3 minutes (4 parallel workers × 45s timeout each)
**Hard timeout:** 5 minutes (enforced by telegram-bot.py thread)

---

## Cron Registration (Dedup-Safe)

```python
active_crons_path = Path("~/.claude/session/active-crons.json")
active_crons = json.loads(active_crons_path.read_text()) if active_crons_path.exists() else {}

if "leroy-improve" not in active_crons:
    active_crons["leroy-improve"] = {
        "schedule": "0 7 * * *",
        "prompt": "Leroy system health audit (Task Scheduler: your org-LeroyImprove)",
        "registered_at": datetime.now().isoformat(),
        "durable": True,
    }
    active_crons_path.write_text(json.dumps(active_crons, indent=2))
```

**Primary trigger:** Task Scheduler (`your org-LeroyImprove`)
**Install:** `powershell -ExecutionPolicy Bypass -File tools\install-leroy-improve.ps1`

---

## Dedup Guard

`session/leroy-improve-heartbeat.txt` stores today's date (`YYYY-MM-DD`).
Script exits silently if date matches. Heartbeat written at start of run (not end) to block parallel PID collisions.

---

## Memory Architecture

```
memory/LeroyImprove/
├── README.md              # Rolling index (30-day purge policy)
├── system-manifest.json   # Topology snapshot for diff
├── verticals.json         # Active vertical registry (grows over time)
└── YYYY-MM-DD.md          # Full daily audit report
```

Auto-purge: reports older than 30 days are deleted on each run. Monthly summary synthesis planned for future release.

---

## Output

### Telegram Card Format
```
🔧 Leroy Health Report — YYYY-MM-DD
Score: N/100 {emoji}

── Agents & Skills ── N/100 {emoji}
  {1-line summary}

── Memory / RAG ───── N/100 {emoji}
  {1-line summary}

── MCPs ────────────── N/100 {emoji}
  {1-line summary}

── Autonomous Builds ── N/100 {emoji}
  {1-line summary}
━━━━━━━━━━━━━━━━━━━━━━
💡 Top Improvements (N):
1. {suggestion}
2. {suggestion}
```

Emoji: ✅ ≥90 | ⚠️ 70-89 | ❌ <70

### Session Files Written
- `session/leroy-audit-results.json` — compact summary (score, verticals, suggestions)
- `session/a2a-cache.json` key `leroy-improve.summary.{date}` — for daily-ops integration

---

## Task Scheduler

**Task:** `your org-LeroyImprove`
**Schedule:** Daily 7:00 AM (all days, including weekends)
**Command:** `python ~/.claude\scripts\leroy-improve.py --telegram`
**Install:** `powershell -ExecutionPolicy Bypass -File tools\install-leroy-improve.ps1`
