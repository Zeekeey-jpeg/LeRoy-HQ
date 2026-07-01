---
name: mcp-health-dashboard
description: |
  Universal health monitoring dashboard for all MCP servers.

  Aggregates data from registry and performance analytics.
  Provides at-a-glance server status (UP/DEGRADED/DOWN).
  Supports background daemon monitoring with alerts.

  Part of Integration Ecosystem v1.0 (Vertical 1, Phase 3)
---

# MCP Health Dashboard

## Purpose

Provide real-time visibility into the health and availability of all MCP servers. This skill aggregates data from `mcp-registry.md` and `mcp-performance-analytics.md` to display a unified health view.

## Health Status Definitions

| Status | Color | Criteria | Action |
|--------|-------|----------|--------|
| **UP** | Green | Success rate >= 95%, latency < 1000ms | Normal operations |
| **DEGRADED** | Yellow | Success rate 80-95% OR latency 1000-3000ms | Monitor closely |
| **DOWN** | Red | Success rate < 80% OR latency > 3000ms OR no response | Investigate |
| **UNKNOWN** | Gray | No recent data (>15 min) | Needs health check |

---

## Dashboard Display

### Quick View (Default)

```
┌─ MCP HEALTH DASHBOARD ──────────────────────────────────┐
│ Last Updated: 2026-01-18 10:45:00 | Refresh: 5 min     │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ SERVER STATUS                                          │
│                                                         │
│ [UP]       crm       98.2%  |  287ms  |  523 calls │
│ [UP]       ticketing   97.8%  |  256ms  |  412 calls │
│ [UP]       catalog        99.1%  |  198ms  |  187 calls │
│ [UP]       email-alt    98.4%  |  341ms  |  125 calls │
│ [UP]       email-primary    99.0%  |  298ms  |   42 calls │
│ [UP]       supabase      100%   |  145ms  |   89 calls │
│ [DEGRADED] itglue        89.5%  |  1234ms |   19 calls │
│ [UNKNOWN]  bim-tool          --     |  --     |  0 calls   │
│ [UNKNOWN]  bim         --     |  --     |  0 calls   │
│ [DOWN]     playwright    72.1%  |  4521ms |   43 calls │
│                                                         │
│ SUMMARY: 6 UP | 1 DEGRADED | 1 DOWN | 2 UNKNOWN        │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Detailed View (Per-Server)

```
┌─ SERVER: crm ───────────────────────────────────────┐
│ Status: UP | Health Score: 94.2                        │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ METRICS (Last 24h)                                     │
│ ├─ Total Calls:    523                                 │
│ ├─ Success Rate:   98.2%                               │
│ ├─ Avg Latency:    287ms                               │
│ ├─ P95 Latency:    612ms                               │
│ ├─ Retry Rate:     1.5%                                │
│ └─ Error Rate:     1.8%                                │
│                                                         │
│ TOP TOOLS                                              │
│ ├─ list_deals:    312 calls | 99.0% | 298ms   │
│ ├─ crm_tool:  156 calls | 97.4% | 412ms   │
│ └─ crm_tool:       55 calls | 98.2% | 145ms   │
│                                                         │
│ RECENT ERRORS                                          │
│ ├─ 10:32 - 429 Rate Limited (list_deals)              │
│ ├─ 10:15 - 429 Rate Limited (search_deals)            │
│ └─ 09:45 - 500 Internal Error (list_contacts)         │
│                                                         │
│ LAST HEALTH CHECK: 10:45:00 | NEXT: 10:50:00          │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## Health Check Protocol

### Automatic Health Checks

```python
HEALTH_CHECK_CONFIG = {
    'interval_minutes': 5,        # Check every 5 minutes
    'timeout_seconds': 30,        # Timeout per server
    'required_uptime': 0.95,      # 95% for UP status
    'max_latency_ms': 3000,       # Max before DOWN
    'lookback_minutes': 15        # Window for metrics
}
```

### Health Check Implementation

```python
async def check_server_health(server_name: str) -> dict:
    """
    Perform health check on a specific server.

    1. Get recent performance data
    2. Attempt a lightweight probe call
    3. Calculate health score
    4. Determine status
    """
    # Get recent metrics from analytics
    metrics = get_server_metrics(server_name, minutes=15)

    # Perform probe call (lightweight operation)
    probe_result = await probe_server(server_name)

    # Calculate health score
    health_score = calculate_health_score(metrics, probe_result)

    # Determine status
    status = determine_status(health_score, metrics)

    return {
        'server': server_name,
        'status': status,
        'health_score': health_score,
        'metrics': metrics,
        'probe_result': probe_result,
        'checked_at': datetime.utcnow().isoformat()
    }
```

### Probe Calls

Each server has a lightweight probe operation:

| Server | Probe Call | Expected Response |
|--------|------------|-------------------|
| crm | `crm_tool(object='deals', limit=1)` | Properties list |
| ticketing | `ticketing_tool(conditions='id>0')` | Count object |
| catalog | `bom_tool(pageSize=1)` | Catalog list |
| google-* | `list_drive_items(page_size=1)` | Items list |
| supabase | `supabase_select(table='health', limit=1)` | Data array |
| itglue | `itglue_list_organizations(limit=1)` | Org list |
| playwright | `playwright_health_check()` | Status object |

---

## Health Score Calculation

```python
def calculate_health_score(metrics: dict, probe: dict) -> float:
    """
    Calculate health score (0-100) from multiple factors.

    Weights:
    - Success rate: 40%
    - Latency performance: 30%
    - Retry rate: 15%
    - Probe success: 15%
    """
    success_score = metrics['success_rate'] * 100  # 0-100
    latency_score = calculate_latency_score(metrics['avg_latency_ms'])
    retry_score = (1 - metrics['retry_rate']) * 100
    probe_score = 100 if probe['success'] else 0

    return (
        success_score * 0.40 +
        latency_score * 0.30 +
        retry_score * 0.15 +
        probe_score * 0.15
    )

def calculate_latency_score(latency_ms: int) -> float:
    """
    Convert latency to score (higher = better).

    < 200ms  = 100
    200-500ms = 80
    500-1000ms = 60
    1000-2000ms = 40
    2000-3000ms = 20
    > 3000ms = 0
    """
    if latency_ms < 200:
        return 100
    elif latency_ms < 500:
        return 80
    elif latency_ms < 1000:
        return 60
    elif latency_ms < 2000:
        return 40
    elif latency_ms < 3000:
        return 20
    else:
        return 0
```

---

## Background Daemon

### Daemon Specification

```python
class MCPHealthDaemon:
    """
    Background daemon for continuous health monitoring.

    Runs in background via Task tool.
    Checks all servers every 5 minutes.
    Raises alerts on status changes.
    Writes state to session/mcp-health.json.
    """

    def __init__(self):
        self.check_interval = 300  # 5 minutes
        self.state_file = 'session/mcp-health.json'
        self.alert_cooldown = 900  # 15 min between same alerts

    async def run(self):
        while True:
            results = await self.check_all_servers()
            self.update_state(results)
            self.check_for_alerts(results)
            await asyncio.sleep(self.check_interval)
```

### State File: session/mcp-health.json

```json
{
  "last_check": "2026-01-18T10:45:00Z",
  "next_check": "2026-01-18T10:50:00Z",
  "daemon_status": "running",
  "servers": {
    "crm": {
      "status": "UP",
      "health_score": 94.2,
      "success_rate": 0.982,
      "avg_latency_ms": 287,
      "last_check": "2026-01-18T10:45:00Z",
      "status_since": "2026-01-18T08:00:00Z"
    }
  },
  "summary": {
    "up": 6,
    "degraded": 1,
    "down": 1,
    "unknown": 2
  },
  "alerts": {
    "active": [
      {
        "server": "playwright",
        "type": "status_change",
        "from": "DEGRADED",
        "to": "DOWN",
        "timestamp": "2026-01-18T10:30:00Z"
      }
    ],
    "acknowledged": []
  }
}
```

---

## Alert System

### Alert Types

| Type | Trigger | Severity |
|------|---------|----------|
| `status_change` | UP->DEGRADED, DEGRADED->DOWN, etc. | Based on new status |
| `latency_spike` | >50% increase in 15 min | Warning |
| `error_surge` | >5x errors in 15 min | Critical |
| `prolonged_degradation` | DEGRADED >30 min | Warning |
| `server_down` | Status = DOWN | Critical |

### Alert Actions

```python
ALERT_ACTIONS = {
    'status_change': {
        'UP->DEGRADED': 'log_warning',
        'DEGRADED->DOWN': 'log_critical + notify',
        'DOWN->UP': 'log_info',
        'DEGRADED->UP': 'log_info'
    },
    'latency_spike': 'log_warning',
    'error_surge': 'log_critical + notify',
    'server_down': 'log_critical + notify + pause_operations'
}

async def handle_alert(alert: dict):
    """
    Process an alert based on type and severity.
    """
    alert_type = alert['type']
    action = ALERT_ACTIONS.get(alert_type, 'log_info')

    if 'notify' in action:
        await send_notification(alert)

    if 'pause_operations' in action:
        await pause_server_operations(alert['server'])

    log_alert(alert, action)
```

---

## Integration with Morning Routine

```python
def get_morning_health_summary() -> str:
    """
    Generate health summary for morning routine.
    """
    state = load_health_state()

    summary = f"""
    MCP Health Status:
    - {state['summary']['up']} servers UP
    - {state['summary']['degraded']} servers DEGRADED
    - {state['summary']['down']} servers DOWN

    Overnight Issues:
    """

    for alert in state['alerts']['active']:
        summary += f"- {alert['server']}: {alert['type']} at {alert['timestamp']}\n"

    return summary
```

---

## Quick Commands

```
┌─ HEALTH DASHBOARD COMMANDS ─────────────────────────────┐
│                                                         │
│ "mcp health"              - Quick status view          │
│ "mcp health [server]"     - Detailed server view       │
│ "mcp health alerts"       - Show active alerts         │
│ "mcp health history"      - Status change history      │
│ "refresh mcp health"      - Force health check         │
│                                                         │
│ DAEMON CONTROL                                         │
│ "start health daemon"     - Start background monitor   │
│ "stop health daemon"      - Stop daemon                │
│ "health daemon status"    - Check daemon state         │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## UI Design Notes (for @designer)

### Dashboard Interface Requirements

1. **Color Coding**
   - UP: Green (#22c55e)
   - DEGRADED: Yellow (#eab308)
   - DOWN: Red (#ef4444)
   - UNKNOWN: Gray (#6b7280)

2. **Layout**
   - Server cards in grid (3 columns)
   - Summary bar at top
   - Alert banner if critical issues
   - Last updated timestamp

3. **Interactions**
   - Click server for detailed view
   - Refresh button (manual check)
   - Alert acknowledge button
   - Time range selector for metrics

4. **Responsive**
   - Collapse to 2 columns on tablet
   - Single column on mobile
   - Maintain readability at all sizes

---

## Data Flow

```
┌─────────────────────────────────────────────────────────┐
│                     DATA FLOW                          │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  mcp-registry.json ─────────┐                          │
│  (server list)              │                          │
│                             ▼                          │
│  mcp-performance.jsonl ──► HEALTH ──► mcp-health.json  │
│  (metrics)                  DAEMON     (state)         │
│                             │                          │
│  Probe calls ───────────────┘                          │
│  (live checks)                       │                 │
│                                      ▼                 │
│                              Dashboard Display         │
│                              Alert Notifications       │
│                              Morning Summary           │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## Related Skills

| Skill | Relationship |
|-------|--------------|
| `mcp-registry.md` | Server list source |
| `mcp-performance-analytics.md` | Metrics source |
| `mcp-auto-retry.md` | Retry metrics |
| `mcp-pagination-wrapper.md` | Pagination health |
| `routines/morning.md` | Consumes health summary |

---

*MCP Health Dashboard v1.0 | Integration Ecosystem Phase 3 | Days 5-7 Deliverable*
