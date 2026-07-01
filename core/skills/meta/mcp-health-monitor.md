# MCP Health Monitor

**Trigger:** Automatic during morning briefing (via Chief of Staff), or manual: "MCP status", "check MCPs"
**Version:** 1.0
**Created:** 2026-02-07
**Department:** Infrastructure
**Owner:** @forge (VP Engineering Data) with @chief-of-staff (reporting)

## Purpose

Track the health and availability of all MCP tool servers used by your org Office. Detect failures during morning briefing data collection, log them persistently, and escalate persistent failures through the Infrastructure department.

## Why This Exists

Before this system, MCP failures during morning briefing were silently swallowed or shown as generic "unavailable" messages. Nobody owned the problem. Calendar API could be down for a week and it would just show "Calendar unavailable" every morning without anyone investigating.

Now: Infrastructure department owns MCP health. Chief of Staff detects failures during briefing. Persistent failures get escalated. Someone is accountable.

## MCP Server Registry

All MCP servers monitored by this system:

| Server ID | Server Name | Auth Type | Tools Monitored | Departments Using |
|-----------|-------------|-----------|-----------------|-------------------|
| email-primary | Google Workspace | OAuth | list_events, search_mail | Revenue Gen, Executive |
| crm | your CRM | API Key | list_deals, search_contacts | Revenue Gen |
| ticketing | your ticketing tool | API Key | list_tickets, list_companies | Revenue Gen, Operations |
| firecrawl | Firecrawl | API Key | scrape, crawl | Revenue Gen (scraper) |

## Health Check Process

### During Morning Briefing (Automatic)

The Chief of Staff runs data collection during the morning briefing. Each MCP tool call is monitored for success/failure:

```yaml
For each MCP tool call in morning briefing:
  1. Record tool name, server, timestamp
  2. IF success:
     - Update state.json: consecutive_failures = 0, status = "ok"
     - Store response time for performance tracking
  3. IF failure:
     - Update state.json: consecutive_failures += 1, status = "failed"
     - Record error type and message
     - Classify failure type (see below)
     - Apply escalation rules
```

### Failure Classification

| Failure Type | Indicators | Common Cause | Resolution Path |
|-------------|-----------|--------------|----------------|
| **auth_expired** | 401/403 error, "unauthorized" | OAuth token expired, API key rotated | Re-authenticate via MCP config |
| **api_unavailable** | Connection refused, timeout, 503 | Service outage, network issue | Wait and retry, check service status |
| **rate_limited** | 429 error, "too many requests" | Exceeded API quota | Reduce call frequency, check plan |
| **invalid_request** | 400 error, "bad request" | API changed, parameter mismatch | Update MCP tool config |
| **unknown** | Any other error | Investigate | Check logs, MCP server docs |

### Manual Health Check

When triggered manually ("MCP status" or "check MCPs"):

```yaml
Step 1: Read MCP health state from state.json
Step 2: For each registered MCP server:
  - Attempt lightweight health check call
  - Google: list_events (limit 1, today only)
  - your CRM: list_deals (limit 1)
  - your CRM: list_tickets (limit 1)
  - Firecrawl: N/A (check on-demand only)
Step 3: Update state.json with results
Step 4: Display formatted health report
```

## State Schema

Location: `session/state.json` under `chief_of_staff.mcp_health`

```json
{
  "chief_of_staff": {
    "mcp_health": {
      "email-primary": {
        "list_events": {
          "status": "ok|failed|degraded",
          "consecutive_failures": 0,
          "last_success": "2026-02-07T09:00:00Z",
          "last_failure": null,
          "last_error": null,
          "failure_type": null,
          "response_time_ms": 450,
          "history": [
            {
              "date": "2026-02-07",
              "status": "ok",
              "response_time_ms": 450
            },
            {
              "date": "2026-02-06",
              "status": "failed",
              "error": "API unavailable",
              "failure_type": "api_unavailable"
            }
          ]
        },
        "search_mail": {
          "status": "failed",
          "consecutive_failures": 3,
          "last_success": "2026-02-04T09:15:00Z",
          "last_failure": "2026-02-07T09:05:00Z",
          "last_error": "Connection refused",
          "failure_type": "api_unavailable",
          "response_time_ms": null,
          "history": []
        }
      }
    },
    "mcp_health_summary": {
      "total_tools": 6,
      "healthy": 4,
      "degraded": 0,
      "failed": 2,
      "last_check": "2026-02-07T09:15:00Z",
      "overall_status": "degraded"
    }
  }
}
```

## Escalation Rules

### Level 1: Info (First Failure)

```yaml
Condition: Tool fails once, no previous consecutive failures
Action:
  - Log in state.json (consecutive_failures = 1)
  - Show in Infrastructure section: "{tool}: FAILED (first occurrence)"
  - No further action needed
```

### Level 2: Warning (2 Consecutive Days)

```yaml
Condition: Tool has failed 2 consecutive morning briefings
Action:
  - Log in state.json (consecutive_failures = 2)
  - Show in Infrastructure section with warning indicator
  - Auto-add one-off reminder: "Investigate {server}/{tool} MCP failure (2 consecutive days)"
  - Suggest diagnostic steps in briefing
```

### Level 3: Critical (3+ Consecutive Days)

```yaml
Condition: Tool has failed 3+ consecutive morning briefings
Action:
  - Log in state.json (consecutive_failures >= 3)
  - Show in Executive Summary as CRITICAL item
  - Show in Infrastructure section with critical indicator
  - Auto-add HIGH priority one-off reminder if not already present
  - Suggest manual workaround (e.g., "Check calendar at calendar.google.com")
  - Recommend re-authentication or MCP server restart
```

## Display Formats

### Infrastructure Section (Morning Briefing)

```
MCP HEALTH STATUS
  email-primary/calendar:    [OK]  450ms
  email-primary/gmail:       [!!]  FAILED (3 days) - Connection refused
                                -> Re-authenticate: check OAuth token
  crm/deals:      [OK]  320ms
  crm/contacts:   [OK]  280ms
  ticketing:        [OK]  510ms
  firecrawl:              [--]  Not checked (on-demand only)

  Summary: 4/6 healthy | 0 degraded | 1 critical | 1 not checked
```

### Executive Summary Escalation

```
CRITICAL ITEMS REQUIRING ATTENTION:
[!!] Infrastructure: Gmail MCP down 3 consecutive days - email data unavailable
     -> Action: Re-authenticate email-primary OAuth token
```

### Manual Health Check Output

```
================================================================
MCP HEALTH REPORT
================================================================
Generated: 2026-02-07 09:30:00 EST

SERVER: email-primary (Google Workspace)
  list_events:  OK    (450ms) | Last failure: 2026-02-04
  search_mail:         FAIL  (timeout) | Failing since: 2026-02-05
    Error: Connection refused
    Type: api_unavailable
    Consecutive: 3 days
    Action: Re-authenticate OAuth token
    Manual: https://calendar.google.com

SERVER: crm (your CRM)
  list_deals:       OK  (320ms) | No recent failures
  search_contacts:  OK  (280ms) | No recent failures

SERVER: ticketing (your ticketing tool)
  list_tickets:    OK  (510ms) | No recent failures
  list_companies:  OK  (480ms) | No recent failures

SERVER: firecrawl (Web Extraction)
  Status: On-demand only (not checked in morning briefing)
  Last used: 2026-02-03

SUMMARY
  Healthy:  4/6 tools
  Failed:   1/6 tools (search_mail)
  Skipped:  1/6 tools (firecrawl - on-demand)
  Overall:  DEGRADED

RECOMMENDED ACTIONS
  1. [CRITICAL] Re-authenticate email-primary OAuth token for Gmail access
  2. [INFO] Consider adding firecrawl to daily health checks if usage increases
================================================================
```

## Diagnostic Steps (for Infrastructure team)

When a tool fails persistently, provide these diagnostic steps:

### Google MCP (OAuth Issues)

```yaml
Symptoms: calendar or gmail tools return auth errors
Steps:
  1. Check if OAuth token expired (common every 7 days)
  2. Re-run Google MCP authentication flow
  3. Verify correct scopes: calendar.readonly, gmail.readonly
  4. Check if Google account has 2FA changes
  5. Restart MCP server process
```

### your CRM MCP (API Key Issues)

```yaml
Symptoms: crm tools return 401 or connection errors
Steps:
  1. Verify API key in MCP config (has it been rotated?)
  2. Check your CRM account status (active, not suspended)
  3. Verify API rate limits not exceeded (10K/day on free)
  4. Test with curl: curl -H "Authorization: Bearer {key}" https://api.hubapi.com/crm/v3/objects/deals
  5. Restart MCP server process
```

### your CRM MCP (API Key Issues)

```yaml
Symptoms: ticketing tools return auth or connection errors
Steps:
  1. Verify API keys (public + private) in MCP config
  2. Check your CRM member account status
  3. Verify API permissions (Admin or appropriate role)
  4. Test connectivity to your CRM URL
  5. Restart MCP server process
```

## History Retention

- Keep 30 days of daily health check history per tool
- Prune older entries during Monday cleanup
- History enables trend analysis: "Gmail has been flaky every Tuesday"
- Store in state.json (lightweight, just status + response time per day)

## Integration Points

**Morning Briefing (Chief of Staff):**
- CoS calls MCP tools during Phase 1 data gathering
- Failure/success recorded automatically
- Results formatted into Infrastructure section

**Manual Health Check:**
- User says "MCP status" or "check MCPs"
- Runs active health probe on all registered servers
- Displays full diagnostic report

**One-Off Reminders (Operations):**
- Level 2+ failures auto-create reminders
- Reminders include diagnostic steps
- Reminders cleared when tool recovers

**Monday Cleanup:**
- Prune health history >30 days
- Generate weekly MCP reliability report

## Performance

- State read/write: <10ms
- Health check per tool: <2 seconds (timeout)
- Total overhead to morning briefing: <5 seconds
- No blocking: if health check hangs, timeout and mark as failed

---

*MCP Health Monitor v1.0 | Infrastructure Department | Persistent failure tracking | Escalation pipeline*
