---
name: mcp-auto-retry
description: |
  Universal retry wrapper for all MCP operations with exponential backoff.

  Handles transient failures (network, rate limits, timeouts) automatically.
  Distinguishes between retryable and non-retryable errors.
  Respects Retry-After headers when present.

  Part of Integration Ecosystem v1.0 (Vertical 1, Phase 1)
---

# MCP Auto-Retry Wrapper

## Purpose

Provide resilient MCP operations by automatically retrying transient failures with exponential backoff. This skill wraps any MCP tool call to handle network hiccups, rate limits, and temporary service unavailability.

## Core Function: retry_mcp_call()

```python
def retry_mcp_call(
    tool_name: str,
    max_retries: int = 5,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_factor: float = 2.0,
    **params
) -> dict:
    """
    Wrap any MCP tool call with automatic retry logic.

    Args:
        tool_name: MCP tool to call (e.g., 'list_deals')
        max_retries: Maximum retry attempts (default: 5)
        base_delay: Initial delay in seconds (default: 1.0)
        max_delay: Maximum delay cap in seconds (default: 60.0)
        backoff_factor: Multiplier for each retry (default: 2.0)
        **params: Parameters to pass to the MCP tool

    Returns:
        dict: MCP response on success

    Raises:
        MCPPermanentError: Non-retryable error (auth, not found, validation)
        MCPMaxRetriesError: Exceeded max retries on transient errors
    """
```

---

## Error Classification

### Retryable Errors (TRANSIENT)

| Error Type | HTTP Codes | Behavior |
|------------|------------|----------|
| Rate Limited | 429 | Respect Retry-After, then backoff |
| Service Unavailable | 503 | Exponential backoff |
| Gateway Timeout | 504 | Exponential backoff |
| Connection Error | N/A | Exponential backoff |
| Timeout | N/A | Exponential backoff |
| Internal Server Error | 500 | Exponential backoff (up to 2 retries) |

### Non-Retryable Errors (PERMANENT)

| Error Type | HTTP Codes | Behavior |
|------------|------------|----------|
| Authentication | 401, 403 | Fail immediately |
| Not Found | 404 | Fail immediately |
| Bad Request | 400 | Fail immediately |
| Validation Error | 422 | Fail immediately |
| Method Not Allowed | 405 | Fail immediately |

---

## Exponential Backoff Algorithm

```python
def calculate_delay(attempt: int, base_delay: float, max_delay: float,
                    backoff_factor: float, retry_after: int = None) -> float:
    """
    Calculate delay before next retry attempt.

    Pattern: base_delay * (backoff_factor ^ attempt) + jitter

    Attempt 1: 1.0s  + jitter (0-0.5s)
    Attempt 2: 2.0s  + jitter (0-1.0s)
    Attempt 3: 4.0s  + jitter (0-2.0s)
    Attempt 4: 8.0s  + jitter (0-4.0s)
    Attempt 5: 16.0s + jitter (0-8.0s)

    Max delay capped at 60s regardless of calculation.
    Retry-After header overrides calculation when present.
    """
    if retry_after:
        return min(retry_after, max_delay)

    delay = base_delay * (backoff_factor ** attempt)
    jitter = random.uniform(0, delay * 0.5)  # Add up to 50% jitter
    return min(delay + jitter, max_delay)
```

---

## Retry-After Header Support

When an MCP returns a `Retry-After` header (common with rate limiting):

```python
# Extract Retry-After from response
retry_after = response.headers.get('Retry-After')

if retry_after:
    if retry_after.isdigit():
        # Seconds format: "120"
        wait_seconds = int(retry_after)
    else:
        # HTTP-date format: "Wed, 18 Jan 2026 12:00:00 GMT"
        retry_time = parse_http_date(retry_after)
        wait_seconds = (retry_time - datetime.now()).total_seconds()

    # Respect the header, capped at max_delay
    delay = min(wait_seconds, max_delay)
```

---

## Usage Patterns

### Basic Usage

```python
# Simple retry wrapper
result = retry_mcp_call(
    'list_deals',
    limit=200,
    after=cursor
)
```

### Custom Retry Settings

```python
# Aggressive retry for critical operations
result = retry_mcp_call(
    'ticketing_tool',
    max_retries=10,
    base_delay=0.5,
    max_delay=120.0,
    pageSize=1000,
    conditions="closedFlag=false"
)
```

### With Error Handling

```python
try:
    result = retry_mcp_call(
        'bom_tool',
        catalogId='primary',
        pageNumber=1,
        pageSize=5000
    )
except MCPPermanentError as e:
    # Non-retryable: auth failed, resource not found, etc.
    log_error(f"Permanent failure: {e}")
    raise
except MCPMaxRetriesError as e:
    # Exhausted retries on transient errors
    log_error(f"Max retries exceeded: {e}")
    notify_admin(e)
    raise
```

---

## Integration with Other Skills

### With mcp-pagination-wrapper.md

```python
# Pagination wrapper uses retry internally
def fetch_all(tool_name, **base_params):
    while has_more_pages:
        # Each page fetch is automatically retried
        page_result = retry_mcp_call(tool_name, **current_params)
        all_records.extend(page_result['results'])
```

### With mcp-performance-analytics.md

```python
# Log retry metrics for analysis
def retry_mcp_call(...):
    start_time = time.time()
    attempts = 0

    while attempts < max_retries:
        attempts += 1
        try:
            result = call_mcp_tool(tool_name, **params)
            # Log success with attempt count
            log_performance({
                'tool': tool_name,
                'success': True,
                'attempts': attempts,
                'total_time': time.time() - start_time
            })
            return result
        except TransientError:
            # Log retry attempt
            log_performance({
                'tool': tool_name,
                'success': False,
                'attempt': attempts,
                'error_type': 'transient'
            })
```

---

## MCP-Specific Configurations

### your CRM

| Setting | Value | Notes |
|---------|-------|-------|
| Rate Limit | 100 calls/10 sec | Enterprise tier |
| Retry-After | Yes | Provided on 429 |
| Recommended max_retries | 5 | Standard |

### your CRM

| Setting | Value | Notes |
|---------|-------|-------|
| Rate Limit | Variable | Per-endpoint |
| Retry-After | Sometimes | Check response |
| Recommended max_retries | 5 | Standard |

### your catalog service

| Setting | Value | Notes |
|---------|-------|-------|
| Rate Limit | Unknown | No documentation |
| Retry-After | No | Not implemented |
| Recommended max_retries | 3 | Conservative |

### Google Workspace

| Setting | Value | Notes |
|---------|-------|-------|
| Rate Limit | Per-user | Check quotas |
| Retry-After | Yes | Standard |
| Recommended max_retries | 5 | Standard |

---

## Logging Format

Each retry event is logged to `session/mcp-performance.jsonl`:

```json
{
  "timestamp": "2026-01-18T10:30:00Z",
  "tool": "list_deals",
  "event": "retry",
  "attempt": 2,
  "error_code": 429,
  "error_type": "rate_limited",
  "retry_after": 10,
  "delay_applied": 10.0,
  "params": {"limit": 200}
}
```

---

## Error Recovery Patterns

### Circuit Breaker (Future Enhancement)

```python
# Track consecutive failures per MCP server
circuit_breaker = {
    'crm': {'failures': 0, 'last_failure': None, 'state': 'closed'},
    'ticketing': {'failures': 0, 'last_failure': None, 'state': 'closed'}
}

# Open circuit after 5 consecutive failures
# Half-open after 60 seconds, allow 1 test request
# Close on success, open again on failure
```

### Graceful Degradation

```python
# When retries exhausted, return cached data if available
try:
    result = retry_mcp_call('list_deals', ...)
except MCPMaxRetriesError:
    # Check for recent cache
    cached = get_cached_result('list_deals', max_age_minutes=30)
    if cached:
        log_warning("Using cached data due to API unavailability")
        return cached
    raise
```

---

## Quick Reference

```
┌─ RETRY BEHAVIOR ────────────────────────────────────────┐
│                                                         │
│ Attempt 1: Call → Fail (429) → Wait 1.2s               │
│ Attempt 2: Call → Fail (503) → Wait 2.5s               │
│ Attempt 3: Call → Fail (504) → Wait 5.1s               │
│ Attempt 4: Call → Fail (500) → Wait 9.8s               │
│ Attempt 5: Call → Success!                             │
│                                                         │
│ Total time: ~19 seconds                                │
│ Result: Success after 5 attempts                       │
│                                                         │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ PERMANENT ERRORS (No Retry):                           │
│ • 401 Unauthorized → Check API key                     │
│ • 403 Forbidden → Check permissions                    │
│ • 404 Not Found → Check resource ID                    │
│ • 400 Bad Request → Check parameters                   │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## Related Skills

| Skill | Relationship |
|-------|--------------|
| `mcp-pagination.md` | Uses retry wrapper internally |
| `mcp-pagination-wrapper.md` | Builds on retry + pagination |
| `mcp-performance-analytics.md` | Logs retry metrics |
| `mcp-health-dashboard.md` | Monitors retry patterns |

---

*MCP Auto-Retry v1.0 | Integration Ecosystem Phase 1 | Day 1 Deliverable*
