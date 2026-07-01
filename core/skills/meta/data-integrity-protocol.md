# Data Integrity Protocol (BULLETPROOF)

**Version:** 1.0
**Created:** 2026-01-12
**Context:** LeRoy cross-report data consistency
**Status:** MANDATORY - NO EXCEPTIONS

---

## THE RULE (MEMORIZE THIS)

```
+=========================================================================+
|                    DATA INTEGRITY PROTOCOL                               |
+=========================================================================+
|                                                                          |
|  PHASE 1 (Collection):  API calls ALLOWED                               |
|  PHASE 2 (Generation):  API calls FORBIDDEN                             |
|                                                                          |
|  ALL reports MUST use the SAME manifest snapshot.                        |
|  If reports show different numbers, DATA INTEGRITY HAS FAILED.          |
|                                                                          |
+=========================================================================+
```

---

## WHY THIS EXISTS

**Incident (2026-01-12):** During LeRoy test run, context compaction caused:
- Executive Report: 69 active projects
- Finance Report: 126 active projects

**Root Cause:** Instead of reading cached manifest data, generator made fresh API queries with different filters. Different queries = different results = inconsistent reports.

**Impact:** Leadership receives reports with conflicting numbers. Trust destroyed.

---

## HARD RULES (ENFORCED)

### Rule 1: Single Source of Truth

```
MANIFEST.JSONL is the ONLY source of data for ALL reports.

Collected once -> Used 10 times -> Numbers match across ALL reports.
```

### Rule 2: Phase 2 API Ban

```
+-----------------------------------------------------------------------+
|  DURING PHASE 2 (GENERATION), THE FOLLOWING ARE FORBIDDEN:            |
+-----------------------------------------------------------------------+
|  - crm_tool()                                              |
|  - list_deals()                                                |
|  - ticketing_tool*()                                              |
|  - ticketing_tool*()                                                |
|  - ticketing_tool*()                                                 |
|  - ANY MCP call that fetches business data                             |
+-----------------------------------------------------------------------+
|  ALLOWED: Gmail send, file read/write, status updates                  |
+-----------------------------------------------------------------------+
```

### Rule 3: Manifest Lock

```
Once manifest_ready = true in status.json:
  - NO NEW DATA may be added
  - NO EXISTING DATA may be modified
  - ALL reports read from this frozen snapshot
```

### Rule 4: Cross-Report Verification

Before sending ANY report, verify shared metrics match:

| Metric | Must Match Across |
|--------|-------------------|
| Active Projects | 01, 02, 05, 10 |
| Won Deals MTD | 01, 03, 10 |
| Pipeline Total | 01, 03, 04 |
| MRR/ARR | 01, 02, 10 |
| Open Tickets | 02, 09 |
| Team Count | 01, 08 |

---

## DATA FLOW (VISUAL)

```
PHASE 1A: COLLECTION
====================

  [your CRM API] --+
  [ticketing API A]  ----+--> [manifest.jsonl] --> LOCKED
  [ticketing API B]  ----+
  [ticketing API C]  ----+
                        |
                        v
PHASE 1B: DISTRIBUTION
====================
                        |
  +---------------------+---------------------+
  |                     |                     |
  v                     v                     v
[01-data.md]      [02-data.md]  ...    [10-data.md]
  |                     |                     |
  |     SAME DATA, DIFFERENT VIEWS            |
  |                     |                     |
  v                     v                     v
PHASE 2: GENERATION (NO API CALLS!)
===================================
  |                     |                     |
  v                     v                     v
[Email 01]        [Email 02]   ...     [Email 10]

  ALL 126 projects   ALL 126 projects   ALL 126 projects
```

---

## ENFORCEMENT CHECKPOINTS

### Checkpoint 1: Before Phase 2

```
VERIFY:
  - status.json shows manifest_ready = true
  - manifest.jsonl exists and is non-empty
  - ALL 10 data files exist (01 through 10)

IF ANY MISSING:
  BLOCK Phase 2
  MESSAGE: "Cannot generate - run Phase 1 first"
```

### Checkpoint 2: During Generation

```
MONITOR for forbidden patterns:
  - "crm_tool" in tool calls -> BLOCK
  - "ticketing_tool" in tool calls -> BLOCK
  - "let me query" in response -> WARN
  - "fresh data" in response -> WARN

IF DETECTED:
  STOP generation
  MESSAGE: "DATA INTEGRITY VIOLATION - API call during Phase 2"
```

### Checkpoint 3: Before Send

```
FOR critical metrics (projects, pipeline, won):
  READ value from current report
  COMPARE to manifest source value

IF MISMATCH:
  BLOCK send
  MESSAGE: "Data mismatch - Report shows X, manifest has Y"
```

---

## RECOVERY PROTOCOL

### If Data Integrity Fails During Run

```
1. STOP all generation
2. LOG the discrepancy
3. OPTIONS:
   a. Re-run Phase 1B (distribute manifest again)
   b. Re-run entire LeRoy (if manifest suspect)
4. NEVER patch one report - fix the source
```

### If Compaction Loses Context

```
1. READ status.json to determine phase
2. IF phase = "generation":
   - READ manifest.jsonl for ALL data
   - DO NOT make API calls
   - Continue from data files only
3. IF data files missing:
   - Run Phase 1B (distribution) only
   - Keep existing manifest
```

---

## MANIFEST CATEGORIES

The following categories MUST exist in manifest.jsonl before Phase 2:

| Category | Source | Used By Reports |
|----------|--------|-----------------|
| HS_DEALS_WON_MTD | your CRM | 01, 03, 10 |
| HS_DEALS_STAGE_6 | your CRM | 01, 03, 04, 10 |
| HS_DEALS_STAGE_65 | your CRM | 01, 03 |
| HS_DEALS_STAGE_5 | your CRM | 04, 07 |
| CW_PROJECTS | your CRM | 01, 02, 05, 10 |
| CW_SCHEDULES | your CRM | 05, 08 |
| CW_TICKETS | your CRM | 02, 09 |
| CW_AGREEMENTS | your CRM | 02, 10 |
| CW_TIME_ENTRIES | your CRM | 02, 08, 09 |
| CW_PURCHASE_ORDERS | your CRM | 06, 10 |
| CW_MEMBERS | your CRM | 01, 08 |
| CW_INVOICES | your CRM | 10 |

---

## SHARED METRICS REFERENCE

These numbers MUST be identical wherever they appear:

### Active Projects
```
Source: CW_PROJECTS where closedFlag=false
Used in: 01-Executive, 02-Operations, 05-Projects, 10-Finance
Value MUST match across all 4 reports
```

### Won Deals MTD
```
Source: HS_DEALS_WON_MTD
Used in: 01-Executive, 03-Sales, 10-Finance
Value MUST match across all 3 reports
```

### Pipeline (Stage 6 + 6.5)
```
Source: HS_DEALS_STAGE_6 + HS_DEALS_STAGE_65
Used in: 01-Executive, 03-Sales, 04-Sales Engineering
Value MUST match across all 3 reports
```

### MRR/ARR
```
Source: CW_AGREEMENTS where status=Active, normalized to monthly
Used in: 01-Executive, 02-Operations, 10-Finance
Value MUST match across all 3 reports
```

---

## GENERATOR AGENT OVERRIDE

Add this to the TOP of any generator agent prompt:

```
## DATA INTEGRITY PROTOCOL (MANDATORY)

YOU ARE IN PHASE 2 - GENERATION MODE.

+-----------------------------------------------------------------------+
|  DO NOT CALL ANY CRM OR TICKETING APIs                          |
|  ALL DATA MUST COME FROM THE DATA FILE                                |
|  IF DATA IS MISSING, USE EMPTY STATE - DO NOT QUERY                   |
+-----------------------------------------------------------------------+

Your ONLY data source is: session/leroy/{DATE}/{NN}-{slug}-data.md
Read it. Use it. Do not supplement with API calls.
```

---

## AUDIT LOG

When data integrity protocol is invoked, log:

```json
{
  "timestamp": "2026-01-12T12:00:00Z",
  "phase": "generation",
  "report": "01-executive",
  "checkpoint": "before_send",
  "metrics_verified": {
    "active_projects": { "manifest": 126, "report": 126, "match": true },
    "won_mtd": { "manifest": 5771.55, "report": 5771.55, "match": true }
  },
  "result": "PASS"
}
```

---

## QUICK REFERENCE CARD

```
+=========================================================================+
|              LeRoy DATA INTEGRITY - QUICK REFERENCE                     |
+=========================================================================+
|                                                                          |
|  Phase 1: API calls OK  |  Phase 2: API calls FORBIDDEN                 |
|                                                                          |
|  manifest.jsonl = SINGLE SOURCE OF TRUTH                                |
|                                                                          |
|  Before send: VERIFY shared metrics match manifest                      |
|                                                                          |
|  If mismatch: BLOCK and investigate - never patch                       |
|                                                                          |
|  After compaction: READ from data files, NEVER re-query                 |
|                                                                          |
+=========================================================================+
```

---

*Data Integrity Protocol v1.0 - Created 2026-01-12 after discovering cross-report inconsistency*
