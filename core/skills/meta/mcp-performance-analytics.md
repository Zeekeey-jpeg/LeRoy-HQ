---
name: mcp-performance-analytics
description: |
  Performance tracking and analytics for all MCP operations.

  Logs every MCP call to session/mcp-performance.jsonl.
  Tracks latency, success rates, error patterns, and retries.
  Provides aggregation patterns for reporting and optimization.

  Part of Integration Ecosystem v1.0 (Vertical 1, Phase 2)
---

# MCP Performance Analytics

## Purpose

Track, analyze, and report on MCP operation performance. This data enables:
- Identifying slow or unreliable endpoints
- Detecting degradation before failures
- Optimizing pagination and retry strategies
- Supporting the health dashboard

## Log File Location

```
session/mcp-performance.jsonl

Format: JSON Lines (one JSON object per line)
Rotation: Daily (mcp-performance-YYYY-MM-DD.jsonl)
Retention: 30 days
```

---

## Event Types

### 1. Tool Call Event

Logged for every MCP tool invocation:

```json
{
  "timestamp": "2026-01-18T10:30:00.123Z",
  "event_type": "tool_call",
  "session_id": "abc123",
  "tool": "list_deals",
  "server": "crm",
  "params": {
    "limit": 200,
    "after": "cursor_xyz"
  },
  "result": {
    "success": true,
    "records_returned": 200,
    "has_more_pages": true
  },
  "performance": {
    "latency_ms": 342,
    "retry_count": 0,
    "bytes_received": 45230
  }
}
```

### 2. Retry Event

Logged when a retry occurs:

```json
{
  "timestamp": "2026-01-18T10:30:01.500Z",
  "event_type": "retry",
  "session_id": "abc123",
  "tool": "list_deals",
  "server": "crm",
  "attempt": 2,
  "error": {
    "code": 429,
    "type": "rate_limited",
    "message": "Rate limit exceeded"
  },
  "retry_config": {
    "delay_ms": 2000,
    "retry_after_header": 2,
    "backoff_applied": true
  }
}
```

### 3. Pagination Complete Event

Logged when fetch_all completes:

```json
{
  "timestamp": "2026-01-18T10:31:15.000Z",
  "event_type": "pagination_complete",
  "session_id": "abc123",
  "tool": "list_deals",
  "server": "crm",
  "pagination": {
    "style": "cursor",
    "pages_fetched": 12,
    "total_records": 2400,
    "expected_count": null,
    "verified": false
  },
  "performance": {
    "total_time_ms": 15230,
    "avg_page_time_ms": 1269,
    "total_retries": 1,
    "total_bytes": 542760
  }
}
```

### 4. Error Event

Logged when a permanent error occurs:

```json
{
  "timestamp": "2026-01-18T10:32:00.000Z",
  "event_type": "error",
  "session_id": "abc123",
  "tool": "crm_tool",
  "server": "crm",
  "error": {
    "code": 404,
    "type": "not_found",
    "message": "Deal 12345 not found",
    "retryable": false
  },
  "params": {
    "dealId": "12345"
  }
}
```

---

## Metrics Tracked

### Per-Tool Metrics

| Metric | Description | Calculation |
|--------|-------------|-------------|
| `call_count` | Total invocations | Count of tool_call events |
| `success_rate` | % successful calls | success / total |
| `avg_latency_ms` | Average response time | Mean of latency_ms |
| `p95_latency_ms` | 95th percentile latency | Percentile calculation |
| `retry_rate` | % calls needing retry | retries / total |
| `error_rate` | % permanent failures | errors / total |

### Per-Server Metrics

| Metric | Description | Calculation |
|--------|-------------|-------------|
| `total_calls` | All calls to server | Sum across tools |
| `availability` | Uptime percentage | success / (success + errors) |
| `avg_latency_ms` | Server-wide latency | Mean across tools |
| `rate_limit_hits` | 429 responses | Count of rate_limited errors |

### Session Metrics

| Metric | Description | Calculation |
|--------|-------------|-------------|
| `total_mcp_calls` | All MCP calls | Count of all tool_call events |
| `total_records_fetched` | Data volume | Sum of records_returned |
| `total_retries` | Retry overhead | Sum of retry events |
| `slowest_tool` | Performance outlier | Max avg_latency_ms |

---

## Logging Implementation

### Basic Logging

```python
import json
from datetime import datetime

def log_mcp_event(event: dict):
    """
    Append event to performance log.
    """
    event['timestamp'] = datetime.utcnow().isoformat() + 'Z'

    log_path = 'session/mcp-performance.jsonl'
    with open(log_path, 'a') as f:
        f.write(json.dumps(event) + '\n')
```

### Wrapper for Tool Calls

```python
import time

def tracked_mcp_call(tool_name: str, **params):
    """
    MCP call with automatic performance tracking.
    """
    start_time = time.time()
    session_id = get_current_session_id()

    try:
        result = call_mcp_tool(tool_name, **params)

        # Log success
        log_mcp_event({
            'event_type': 'tool_call',
            'session_id': session_id,
            'tool': tool_name,
            'server': get_server_for_tool(tool_name),
            'params': sanitize_params(params),
            'result': {
                'success': True,
                'records_returned': count_records(result)
            },
            'performance': {
                'latency_ms': int((time.time() - start_time) * 1000)
            }
        })

        return result

    except Exception as e:
        # Log error
        log_mcp_event({
            'event_type': 'error',
            'session_id': session_id,
            'tool': tool_name,
            'server': get_server_for_tool(tool_name),
            'error': {
                'type': type(e).__name__,
                'message': str(e),
                'retryable': is_retryable(e)
            },
            'performance': {
                'latency_ms': int((time.time() - start_time) * 1000)
            }
        })
        raise
```

---

## Aggregation Patterns

### Daily Summary

```python
def generate_daily_summary(date: str) -> dict:
    """
    Generate summary statistics for a specific day.
    """
    log_file = f'session/mcp-performance-{date}.jsonl'
    events = load_jsonl(log_file)

    tool_calls = [e for e in events if e['event_type'] == 'tool_call']
    errors = [e for e in events if e['event_type'] == 'error']
    retries = [e for e in events if e['event_type'] == 'retry']

    return {
        'date': date,
        'total_calls': len(tool_calls),
        'success_rate': calculate_success_rate(tool_calls, errors),
        'total_retries': len(retries),
        'avg_latency_ms': calculate_avg_latency(tool_calls),
        'by_server': aggregate_by_server(tool_calls),
        'by_tool': aggregate_by_tool(tool_calls),
        'top_errors': count_error_types(errors)
    }
```

### Server Health Score

```python
def calculate_server_health(server: str, events: list) -> float:
    """
    Calculate health score (0-100) for a server.

    Factors:
    - Success rate (40%)
    - Latency vs baseline (30%)
    - Retry rate (20%)
    - Error diversity (10%)
    """
    server_events = [e for e in events if e.get('server') == server]

    success_rate = calculate_success_rate(server_events)
    latency_score = calculate_latency_score(server_events)
    retry_score = calculate_retry_score(server_events)
    error_score = calculate_error_diversity_score(server_events)

    return (
        success_rate * 0.4 +
        latency_score * 0.3 +
        retry_score * 0.2 +
        error_score * 0.1
    )
```

---

## Reports

### Performance Report Template

```
┌─ MCP PERFORMANCE REPORT ────────────────────────────────┐
│ Date: 2026-01-18 | Session: abc123                     │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ OVERVIEW                                               │
│ Total Calls: 1,247                                     │
│ Success Rate: 98.4%                                    │
│ Avg Latency: 287ms                                     │
│ Total Retries: 23                                      │
│                                                         │
│ BY SERVER                                              │
│ ┌────────────┬───────┬────────┬─────────┬───────────┐ │
│ │ Server     │ Calls │ Success│ Latency │ Retries   │ │
│ ├────────────┼───────┼────────┼─────────┼───────────┤ │
│ │ crm    │ 523   │ 99.2%  │ 312ms   │ 8         │ │
│ │ ticketing│ 412   │ 97.8%  │ 256ms   │ 12        │ │
│ │ catalog     │ 187   │ 98.9%  │ 198ms   │ 2         │ │
│ │ email-alt │ 125   │ 98.4%  │ 341ms   │ 1         │ │
│ └────────────┴───────┴────────┴─────────┴───────────┘ │
│                                                         │
│ TOP ERRORS                                             │
│ 1. 429 Rate Limited (crm): 8 occurrences          │
│ 2. 503 Service Unavailable (ticketing): 5 occ.      │
│ 3. 404 Not Found (catalog): 3 occurrences              │
│                                                         │
│ SLOWEST ENDPOINTS                                      │
│ 1. bom_tool: 1,230ms avg (5000 records)     │
│ 2. crm_tool: 856ms avg                    │
│ 3. ticketing_tool: 634ms avg                │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Week-over-Week Comparison

```python
def generate_wow_comparison(current_week: str, previous_week: str) -> dict:
    """
    Compare performance metrics between two weeks.
    """
    current = aggregate_week(current_week)
    previous = aggregate_week(previous_week)

    return {
        'period': f'{previous_week} vs {current_week}',
        'call_volume_change': percent_change(current['total_calls'], previous['total_calls']),
        'success_rate_change': current['success_rate'] - previous['success_rate'],
        'latency_change': percent_change(current['avg_latency'], previous['avg_latency']),
        'retry_rate_change': current['retry_rate'] - previous['retry_rate'],
        'improving_servers': identify_improving(current, previous),
        'degrading_servers': identify_degrading(current, previous)
    }
```

---

## Integration Points

### With Token Tracking

```python
def correlate_with_tokens(mcp_events: list, token_events: list) -> dict:
    """
    Correlate MCP calls with token consumption.

    Goal: Identify which MCP operations are most token-efficient.
    """
    # Match MCP calls to token burn
    # Calculate tokens per record fetched
    # Identify optimization opportunities
```

### With Health Dashboard

```python
def get_realtime_metrics() -> dict:
    """
    Get current metrics for dashboard display.
    """
    recent_events = load_recent_events(minutes=5)

    return {
        'calls_per_minute': calculate_rate(recent_events),
        'current_success_rate': calculate_success_rate(recent_events),
        'current_avg_latency': calculate_avg_latency(recent_events),
        'active_servers': get_active_servers(recent_events),
        'recent_errors': get_recent_errors(recent_events)
    }
```

---

## Alert Thresholds

| Metric | Warning | Critical | Action |
|--------|---------|----------|--------|
| Success Rate | < 95% | < 90% | Investigate server |
| Avg Latency | > 1000ms | > 3000ms | Check network/server |
| Retry Rate | > 10% | > 25% | Check rate limits |
| Error Rate | > 5% | > 15% | Review error types |

```python
def check_thresholds(metrics: dict) -> list:
    """
    Check metrics against alert thresholds.

    Returns list of alerts to raise.
    """
    alerts = []

    if metrics['success_rate'] < 0.90:
        alerts.append({
            'level': 'critical',
            'metric': 'success_rate',
            'value': metrics['success_rate'],
            'threshold': 0.90
        })
    elif metrics['success_rate'] < 0.95:
        alerts.append({
            'level': 'warning',
            'metric': 'success_rate',
            'value': metrics['success_rate'],
            'threshold': 0.95
        })

    # ... similar for other metrics

    return alerts
```

---

## Quick Commands

```
┌─ ANALYTICS COMMANDS ────────────────────────────────────┐
│                                                         │
│ "mcp performance report"      - Today's summary        │
│ "mcp performance [date]"      - Specific date          │
│ "mcp server health"           - All server scores      │
│ "mcp slowest endpoints"       - Latency outliers       │
│ "mcp error summary"           - Error breakdown        │
│ "mcp wow comparison"          - Week-over-week         │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## Related Skills

| Skill | Relationship |
|-------|--------------|
| `mcp-auto-retry.md` | Logs retry events |
| `mcp-pagination-wrapper.md` | Logs pagination events |
| `mcp-registry.md` | Server/tool mapping |
| `mcp-health-dashboard.md` | Consumes analytics |
| `token-goal-management.md` | Token correlation |

---

*MCP Performance Analytics v1.0 | Integration Ecosystem Phase 2 | Days 3-4 Deliverable*
