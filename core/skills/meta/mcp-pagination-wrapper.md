---
name: mcp-pagination-wrapper
description: |
  Universal auto-pagination wrapper for all MCP tools.

  Extends mcp-pagination.md with automatic style detection.
  Integrates with mcp-auto-retry.md for resilience.
  Provides fetch_all() function for complete dataset retrieval.

  Part of Integration Ecosystem v1.0 (Vertical 1, Phase 2)
---

# MCP Pagination Wrapper - Universal Auto-Fetch

## Purpose

Provide a single `fetch_all()` function that automatically handles pagination for ANY MCP tool, regardless of pagination style (cursor, page, offset, token). Builds on the existing `mcp-pagination.md` rules and integrates retry logic from `mcp-auto-retry.md`.

## Core Function: fetch_all()

```python
def fetch_all(
    tool_name: str,
    progress_callback: callable = None,
    checkpoint_interval: int = 10,
    **base_params
) -> dict:
    """
    Fetch ALL records from a paginated MCP endpoint.

    Automatically detects pagination style and iterates through all pages.
    Integrates retry logic for resilient fetching.
    Provides progress callbacks for long-running operations.

    Args:
        tool_name: MCP tool to call (e.g., 'list_deals')
        progress_callback: Optional function(page, total_records) for progress
        checkpoint_interval: Pages between progress reports (default: 10)
        **base_params: Parameters to pass to the MCP tool

    Returns:
        dict: {
            'records': list,        # All fetched records
            'total_count': int,     # Total records fetched
            'pages_fetched': int,   # Number of pages
            'tool': str,            # Tool name
            'pagination_style': str # Detected style
        }

    Raises:
        MCPToolNotFound: Tool not in registry
        MCPPaginationError: Pagination failed (after retries)
        MCPDataIntegrityError: COUNT-FETCH-VERIFY mismatch
    """
```

---

## Auto-Detection Logic

### Step 1: Check Registry

```python
def detect_pagination_style(tool_name: str) -> dict:
    """
    Detect pagination style from mcp-registry.json.

    Returns pagination config or raises if not found.
    """
    registry = load_registry()
    config = get_tool_config(tool_name)

    if not config:
        raise MCPToolNotFound(f"Tool {tool_name} not in registry")

    pagination = config['tool'].get('pagination', {})

    if not pagination.get('supported'):
        # Tool doesn't paginate - single call
        return {'style': 'none', 'max_page_size': None}

    return pagination
```

### Step 2: Select Strategy

```python
PAGINATION_STRATEGIES = {
    'cursor': CursorPaginationStrategy,   # your CRM, ITGlue
    'page': PageBasedPaginationStrategy,  # your CRM, your catalog service
    'offset': OffsetPaginationStrategy,   # Supabase
    'token': TokenPaginationStrategy,     # Google
    'none': SingleFetchStrategy           # Non-paginated
}

def get_strategy(style: str) -> PaginationStrategy:
    """Get the appropriate pagination strategy."""
    return PAGINATION_STRATEGIES.get(style, SingleFetchStrategy)()
```

---

## Pagination Strategies

### Cursor-Based (your CRM, ITGlue)

```python
class CursorPaginationStrategy:
    """
    Pattern: Pass cursor from previous response to next request.

    Request:  list_deals(limit=200, after=cursor)
    Response: { results: [...], paging: { next: { after: "xyz" } } }
    """

    def fetch_all(self, tool_name, **params):
        all_records = []
        cursor = None

        while True:
            # Add cursor to params if we have one
            call_params = {**params, 'limit': 200}
            if cursor:
                call_params['after'] = cursor

            result = retry_mcp_call(tool_name, **call_params)

            records = result.get('results', [])
            all_records.extend(records)

            # Get next cursor
            paging = result.get('paging', {})
            cursor = paging.get('next', {}).get('after')

            if not cursor:
                break

        return all_records
```

### Page-Based (your CRM, your catalog service)

```python
class PageBasedPaginationStrategy:
    """
    Pattern: Increment page number until partial page returned.

    Request:  ticketing_tool(page=1, pageSize=1000)
    Response: [ ... ] (array of records)
    """

    def fetch_all(self, tool_name, **params):
        all_records = []
        page = 1
        page_size = self.get_max_page_size(tool_name)  # 1000 for ticketing

        while True:
            call_params = {**params, 'page': page, 'pageSize': page_size}
            result = retry_mcp_call(tool_name, **call_params)

            records = result if isinstance(result, list) else result.get('data', [])
            all_records.extend(records)

            # If we got less than page_size, we're done
            if len(records) < page_size:
                break

            page += 1

        return all_records
```

### Offset-Based (Supabase)

```python
class OffsetPaginationStrategy:
    """
    Pattern: Use offset to skip already-fetched records.

    Request:  supabase_select(table='x', limit=1000, offset=0)
    Response: { data: [...] }
    """

    def fetch_all(self, tool_name, **params):
        all_records = []
        offset = 0
        limit = 1000

        while True:
            call_params = {**params, 'limit': limit, 'offset': offset}
            result = retry_mcp_call(tool_name, **call_params)

            records = result.get('data', [])
            all_records.extend(records)

            if len(records) < limit:
                break

            offset += limit

        return all_records
```

### Token-Based (Google)

```python
class TokenPaginationStrategy:
    """
    Pattern: Use nextPageToken from response in next request.

    Request:  list_drive_items(page_size=100, page_token=token)
    Response: { items: [...], nextPageToken: "xyz" }
    """

    def fetch_all(self, tool_name, **params):
        all_records = []
        page_token = None

        while True:
            call_params = {**params, 'page_size': 100}
            if page_token:
                call_params['page_token'] = page_token

            result = retry_mcp_call(tool_name, **call_params)

            # Handle different Google response formats
            records = (result.get('items') or
                      result.get('messages') or
                      result.get('files') or
                      result.get('events') or
                      [])
            all_records.extend(records)

            page_token = result.get('nextPageToken')
            if not page_token:
                break

        return all_records
```

---

## COUNT-FETCH-VERIFY Integration

From `mcp-pagination.md`, always verify completeness:

```python
def fetch_all_with_verification(tool_name: str, **params) -> dict:
    """
    Fetch all with COUNT-FETCH-VERIFY pattern.
    """
    # STEP 1: COUNT (if available)
    count_tool = get_count_tool(tool_name)
    expected_count = None

    if count_tool:
        count_result = retry_mcp_call(count_tool, **params)
        expected_count = count_result.get('count')
        print(f"[FETCH] Expected: {expected_count} records")

    # STEP 2: FETCH
    records = fetch_all(tool_name, **params)

    # STEP 3: VERIFY
    if expected_count and len(records) != expected_count:
        raise MCPDataIntegrityError(
            f"COUNT-FETCH mismatch: expected {expected_count}, got {len(records)}"
        )

    # Quality warning
    pagination = detect_pagination_style(tool_name)
    max_size = pagination.get('max_page_size', 1000)
    if len(records) % max_size == 0 and len(records) > 0:
        print(f"[WARNING] Record count ({len(records)}) is exact multiple of {max_size}")

    return {
        'records': records,
        'total_count': len(records),
        'verified': expected_count is not None,
        'expected_count': expected_count
    }
```

---

## Progress Callbacks

For large datasets, provide progress feedback:

```python
def fetch_all(tool_name, progress_callback=None, checkpoint_interval=10, **params):
    """
    With progress callback support.
    """
    all_records = []
    page = 0

    while has_more_pages:
        page += 1
        records = fetch_page(...)
        all_records.extend(records)

        # Call progress callback at intervals
        if progress_callback and page % checkpoint_interval == 0:
            progress_callback(page, len(all_records))

    # Final callback
    if progress_callback:
        progress_callback(page, len(all_records), final=True)

    return all_records

# Usage:
def my_progress(page, total, final=False):
    status = "COMPLETE" if final else "IN PROGRESS"
    print(f"[{status}] Page {page}: {total} records")

result = fetch_all('crm_tool', progress_callback=my_progress)
```

---

## Usage Examples

### Simple Usage

```python
# Fetch all your CRM deals
result = fetch_all('list_deals')
print(f"Fetched {result['total_count']} deals")
```

### With Filters

```python
# Fetch all open your CRM tickets
result = fetch_all(
    'ticketing_tool',
    conditions="closedFlag=false"
)
```

### With Progress

```python
# Large dataset with progress reporting
result = fetch_all(
    'crm_tool',
    progress_callback=lambda p, t: print(f"Page {p}: {t} contacts"),
    checkpoint_interval=5
)
```

### With Verification

```python
# Full COUNT-FETCH-VERIFY
result = fetch_all_with_verification(
    'ticketing_tool',
    conditions="board/id=1"
)
if result['verified']:
    print(f"Verified: {result['total_count']} tickets")
```

---

## MCP-Specific Configurations

### Quick Reference Table

| MCP | Style | Max Size | Count Tool | Notes |
|-----|-------|----------|------------|-------|
| your CRM | cursor | 200 | No | Use `limit=200` always |
| your CRM | page | 1000 | Yes | `ticketing_tool*` |
| your catalog service | page | 5000 | No | Large page size |
| Google | token | 100 | No | Varies by endpoint |
| Supabase | offset | 1000 | No | Standard offset |
| ITGlue | cursor | 200 | No | Similar to your CRM |

### Per-Tool Overrides

```python
TOOL_OVERRIDES = {
    'bom_tool': {
        'max_page_size': 5000,  # Override for catalog
        'response_key': 'products'
    },
    'search_gmail_messages': {
        'max_page_size': 100,
        'response_key': 'messages'
    }
}
```

---

## Error Handling

```python
try:
    result = fetch_all('list_deals')
except MCPToolNotFound as e:
    # Tool not in registry
    print(f"Unknown tool: {e}")
except MCPDataIntegrityError as e:
    # COUNT-FETCH mismatch
    print(f"Data integrity issue: {e}")
    # Consider partial result or retry
except MCPMaxRetriesError as e:
    # Pagination failed after retries
    print(f"Fetch failed: {e}")
```

---

## Performance Logging

Each fetch_all operation logs to `mcp-performance.jsonl`:

```json
{
  "timestamp": "2026-01-18T10:30:00Z",
  "operation": "fetch_all",
  "tool": "list_deals",
  "pagination_style": "cursor",
  "pages_fetched": 12,
  "total_records": 2400,
  "expected_count": null,
  "verified": false,
  "total_time_ms": 15230,
  "avg_page_time_ms": 1269,
  "retries": 2
}
```

---

## Quick Reference

```
┌─ FETCH_ALL QUICK GUIDE ─────────────────────────────────┐
│                                                         │
│ BASIC:                                                 │
│ result = fetch_all('tool_name')                        │
│ records = result['records']                            │
│                                                         │
│ WITH FILTERS:                                          │
│ result = fetch_all('tool', conditions="field=value")   │
│                                                         │
│ WITH PROGRESS:                                         │
│ result = fetch_all('tool', progress_callback=fn)       │
│                                                         │
│ WITH VERIFICATION:                                     │
│ result = fetch_all_with_verification('tool')           │
│                                                         │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ MAX PAGE SIZES (MEMORIZE):                             │
│ • your CRM: 200                                         │
│ • your CRM: 1000                                    │
│ • your catalog service catalog: 5000                                │
│ • Google: 100                                          │
│ • Supabase: 1000                                       │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## Related Skills

| Skill | Relationship |
|-------|--------------|
| `mcp-pagination.md` | Rules this wrapper implements |
| `mcp-auto-retry.md` | Retry logic used internally |
| `mcp-registry.md` | Source for pagination config |
| `mcp-performance-analytics.md` | Logs fetch operations |
| `data-integrity-protocol.md` | COUNT-FETCH-VERIFY pattern |

---

*MCP Pagination Wrapper v1.0 | Integration Ecosystem Phase 2 | Days 3-4 Deliverable*
