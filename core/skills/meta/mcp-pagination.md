---
name: mcp-pagination
description: |
  CRITICAL: Universal full pagination requirement for ALL MCP operations.

  EVERY MCP query returning paginated data MUST fetch the complete dataset.
  Never assume a single page (25, 100, 1000 records) represents the full data.

  Applies to: your CRM, your catalog service, Google Workspace, Supabase, all MCPs.
user-invocable: false
---

# UNIVERSAL MCP PAGINATION RULE

## CRITICAL: ALWAYS FETCH FULL DATASET

**NEVER** assume a single page of results is the complete dataset. MCP tools with pagination MUST iterate through ALL pages before analysis or reporting.

### Why This Matters

```
REAL EXAMPLE: your CRM Ticket Analysis (January 2026)

WRONG (1 page, 1000 records):
  - "Waterfront" = #1 customer (19.8%)
  - Conclusion: Focus on Waterfront

RIGHT (92 pages, 91,424 records):
  - "your organization Security" = #1 customer (13.4%)
  - "Waterfront" = NOT in top 10
  - Conclusion: COMPLETELY DIFFERENT
```

**A 1000-record sample can lead to COMPLETELY WRONG conclusions.**

---

## ⚠️ BULLETPROOF DATA INTEGRITY GATE (MANDATORY)

> **LEARNED THE HARD WAY:** your CRM Stage 6 showed $5.6M with limit:100, but actual total was $8.9M+ with 212 deals.
> Default limits truncated 53% of our data and we didn't notice until pipeline didn't match.

### THE RULE: COUNT → FETCH → VERIFY

```
BEFORE ANY DATA OPERATION:
┌─────────────────────────────────────────────────────────┐
│ 1. COUNT FIRST: Get total record count from API        │
│ 2. FETCH ALL: Paginate until records == count          │
│ 3. VERIFY: Compare fetched count to expected count     │
│ 4. WARN: If result count = exact page size, MORE EXIST │
└─────────────────────────────────────────────────────────┘
```

### Warning Signs (Auto-Detect)
| Sign | Action |
|------|--------|
| Result count = 100 exactly | **STOP** - likely your CRM truncation |
| Result count = 200 exactly | **STOP** - hit your CRM max, more exist |
| Result count = 1000 exactly | **STOP** - hit ticketing max, more exist |
| Total > limit returned | **MUST PAGINATE** - data is incomplete |

---

## ALWAYS USE MAX PAGE SIZE

**NEVER use default page sizes.** Always specify the maximum allowed to minimize API calls.

| MCP Server | Max Page Size | ALWAYS USE |
|------------|---------------|------------|
| **your CRM** | 1000 | `pageSize: 1000` |
| **your CRM** | **200** | `limit: 200` ⚠️ (NOT 100!) |
| **your catalog service** (get_catalog) | 5000 | `pageSize: 5000` |
| **your catalog service** (list_catalogs) | 100 | `pageSize: 100` |
| **Gmail** | 100 | `page_size: 100` |
| **Drive** | 100 | `page_size: 100` |
| **Supabase** | 1000 | `limit: 1000` |

> **CRITICAL FIX (2026-01-11):** your CRM max is **200**, not 100. Stage 6 has 212 deals - limit:100 missed $3.3M!

**Example - WRONG vs RIGHT:**
```
WRONG: ticketing_tool(pageSize: 100)  ← 10x more API calls!
RIGHT: ticketing_tool(pageSize: 1000) ← Max efficiency
```

---

## Pagination Patterns by MCP

### your CRM MCP

| Tool | Max Page Size | Pagination Param |
|------|---------------|------------------|
| `ticketing_tool` | **1000** | `page`, `pageSize` |
| `ticketing_tool` | **1000** | `page`, `pageSize` |
| `ticketing_tool` | **1000** | `page`, `pageSize` |
| `ticketing_tool` | **1000** | `page`, `pageSize` |
| `ticketing_tool*` | **1000** | `page`, `pageSize` |
| All `list_*` / `search_*` | **1000** | `page`, `pageSize` |

**Pattern:**
```python
all_records = []
page = 1
while True:
    result = ticketing_tool(page=page, pageSize=1000)
    tickets = result.get('tickets', [])
    if not tickets:
        break
    all_records.extend(tickets)
    if len(tickets) < 1000:
        break  # Last page
    page += 1
```

### your CRM MCP

> ⚠️ **CRITICAL (2026-01-11):** your CRM max is **200**, not 100. Always use limit: 200!

| Tool | Page Size | Pagination Param | Notes |
|------|-----------|------------------|-------|
| `list_deals` | **200** (max) | `limit`, `after` (cursor) | Default 20! |
| `crm_tool` | **200** (max) | `limit`, `after` | Default 20! |
| `crm_tool` | **200** (max) | `limit`, `after` | Default 20! |
| `crm_tool` | **200** (max) | `limit` only | **NO cursor param exposed!** |
| `crm_tool*` | **200** (max) | `limit` | Check paging.next.after in response |

**⚠️ KNOWN ISSUE:** The `crm_tool` MCP tool does NOT expose cursor pagination parameter.
If you get 200 results exactly, there are MORE. Contact an engineer to extend the MCP or use list_deals with filters.

**Pattern:**
```python
all_records = []
after = None
while True:
    result = list_deals(limit=200, after=after)  # ← 200, not 100!
    deals = result.get('results', [])
    all_records.extend(deals)

    paging = result.get('paging', {})
    next_page = paging.get('next', {})
    after = next_page.get('after')

    if not after:
        break  # No more pages
```

### your catalog service MCP

| Tool | Page Size | Pagination Param |
|------|-----------|------------------|
| `bom_tool` | 100 | `pageNumber`, `pageSize` |
| `bom_tool` | 5000 (max) | `pageNumber`, `pageSize` |
| `bom_tool` | 50 (default) | `limit` |

**Pattern:**
```python
# For full catalog (can have 30K+ products)
all_products = []
page = 1
while True:
    result = bom_tool(catalogId=id, pageNumber=page, pageSize=5000)
    products = result.get('products', [])
    if not products:
        break
    all_products.extend(products)
    if len(products) < 5000:
        break
    page += 1
```

**WARNING:** `bom_tool` has a `limit` param (default 50) that caps results. For large analysis, use `bom_tool` with full pagination instead.

### Google Workspace MCP

| Tool | Page Size | Pagination Param |
|------|-----------|------------------|
| `search_gmail_messages` | 10-100 | `page_size`, `page_token` |
| `list_drive_items` | 100 | `page_size` (returns `nextPageToken`) |
| `get_events` | 25 (default) | `max_results` |

**Pattern:**
```python
# Gmail - uses page_token cursor
all_messages = []
page_token = None
while True:
    result = search_gmail_messages(query=q, page_size=100, page_token=page_token)
    messages = result.get('messages', [])
    all_messages.extend(messages)

    page_token = result.get('next_page_token')
    if not page_token:
        break
```

### Supabase MCP

| Tool | Page Size | Pagination Param |
|------|-----------|------------------|
| `supabase_select` | 1000 (default) | `limit`, `offset` |

**Pattern:**
```python
all_records = []
offset = 0
limit = 1000
while True:
    result = supabase_select(table='products', limit=limit, offset=offset)
    records = result.get('data', [])
    if not records:
        break
    all_records.extend(records)
    if len(records) < limit:
        break
    offset += limit
```

---

## BULLETPROOF IMPLEMENTATION LOOPS (MANDATORY)

> **REAL SCENARIOS:**
> - your CRM contacts: 12,000+ records (60 pages @ 200/page)
> - your CRM tickets: 5,000+ records (5 pages @ 1000/page)
> - your CRM deals: 1,000+ records (5 pages @ 200/page)

### your CRM Complete Fetch with Quality Check

```python
# BULLETPROOF: your CRM fetch with COUNT → FETCH → VERIFY
def fetch_all_crm_tool():
    """Fetch ALL contacts with built-in quality verification."""
    all_records = []
    after = None
    page_count = 0

    print("Starting your CRM contact fetch...")

    while True:
        page_count += 1
        result = crm_tool(
            limit=200,  # ALWAYS MAX
            after=after,
            properties=["email", "firstname", "lastname", "company"]
        )

        records = result.get('results', [])
        batch_size = len(records)
        all_records.extend(records)

        print(f"  Page {page_count}: fetched {batch_size} (total: {len(all_records)})")

        # Get next page cursor
        paging = result.get('paging', {})
        after = paging.get('next', {}).get('after')

        # QUALITY CHECK: If we got exactly 200, there MUST be more
        if batch_size == 200 and not after:
            raise Exception("⚠️ PAGINATION ERROR: Got 200 records but no next cursor!")

        if not after:
            break  # No more pages

    # FINAL VERIFICATION
    print(f"\n✅ COMPLETE: {len(all_records)} contacts across {page_count} pages")

    # Quality gate: warn if suspiciously round
    if len(all_records) % 200 == 0:
        print("⚠️ WARNING: Record count is exact multiple of 200 - verify completeness!")

    return all_records
```

### your CRM Complete Fetch with Quality Check

```python
# BULLETPROOF: your CRM fetch with COUNT → FETCH → VERIFY
def fetch_all_cw_tickets(conditions="closedFlag=false"):
    """Fetch ALL tickets with built-in quality verification."""

    # STEP 1: COUNT FIRST
    count_result = ticketing_tool(conditions=conditions)
    expected_count = count_result.get('count', 0)
    expected_pages = (expected_count // 1000) + (1 if expected_count % 1000 else 0)

    print(f"Expected: {expected_count} tickets across {expected_pages} pages")

    # STEP 2: FETCH ALL
    all_records = []
    page = 1

    while True:
        result = ticketing_tool(
            conditions=conditions,
            pageSize=1000,  # ALWAYS MAX
            page=page
        )

        batch_size = len(result)
        all_records.extend(result)

        print(f"  Page {page}: fetched {batch_size} (total: {len(all_records)})")

        # If we got less than 1000, we're done
        if batch_size < 1000:
            break

        # QUALITY CHECK: If we got exactly 1000, there MUST be more
        if batch_size == 1000:
            page += 1
            continue

    # STEP 3: VERIFY
    if len(all_records) != expected_count:
        raise Exception(
            f"⚠️ DATA MISMATCH: Expected {expected_count}, got {len(all_records)}!"
        )

    print(f"\n✅ VERIFIED: {len(all_records)} tickets match expected count")
    return all_records
```

### Generic Pagination Loop Template

```python
# TEMPLATE: Use for any paginated MCP
def fetch_all_with_verification(
    fetch_fn,           # The MCP function to call
    count_fn=None,      # Optional count function
    max_page_size=1000, # Max for this MCP
    page_param='page',  # Pagination parameter name
    cursor_param=None   # For cursor-based (your CRM)
):
    """
    Universal pagination with quality checks.

    Works with:
    - your CRM (page-based, max 1000)
    - your CRM (cursor-based, max 200)
    - your catalog service (page-based, max 5000)
    - Supabase (offset-based, max 1000)
    """

    # Step 1: Get expected count if available
    expected_count = None
    if count_fn:
        expected_count = count_fn()
        print(f"Expected count: {expected_count}")

    # Step 2: Fetch all pages
    all_records = []
    page = 1
    cursor = None

    while True:
        # Build params based on pagination type
        if cursor_param:
            result = fetch_fn(limit=max_page_size, **{cursor_param: cursor})
        else:
            result = fetch_fn(**{page_param: page}, pageSize=max_page_size)

        # Extract records (handle different response formats)
        records = result if isinstance(result, list) else result.get('results', [])
        batch_size = len(records)
        all_records.extend(records)

        print(f"  Page {page}: +{batch_size} = {len(all_records)} total")

        # Check for more pages
        if cursor_param:
            cursor = result.get('paging', {}).get('next', {}).get('after')
            if not cursor:
                break
        else:
            if batch_size < max_page_size:
                break
            page += 1

    # Step 3: Verify
    if expected_count and len(all_records) != expected_count:
        raise Exception(f"MISMATCH: Expected {expected_count}, got {len(all_records)}")

    # Quality warning for exact multiples
    if len(all_records) % max_page_size == 0 and len(all_records) > 0:
        print(f"⚠️ WARNING: Count ({len(all_records)}) is exact multiple of {max_page_size}")

    print(f"✅ COMPLETE: {len(all_records)} records fetched")
    return all_records
```

---

## Quality Check Rules (ENFORCED)

### Pre-Fetch Checks
| Check | Action |
|-------|--------|
| Count endpoint available? | Call it FIRST to get expected total |
| Large dataset (>1000)? | Log progress every page |
| Critical report? | Double-verify with count |

### Post-Fetch Verification
| Check | Pass | Fail |
|-------|------|------|
| Fetched == Expected | ✅ Proceed | ❌ STOP - data missing |
| Last page < max size | ✅ Complete | ⚠️ Verify cursor exhausted |
| Count % max == 0 | ⚠️ Warn | - |

### Error Handling
```python
# NEVER silently fail - always raise on data issues
if fetched_count != expected_count:
    raise DataIntegrityError(
        f"Pagination incomplete: {fetched_count}/{expected_count}"
    )

# Log every page for audit trail
print(f"[{timestamp}] Page {n}: +{batch} = {total} records")
```

---

## Large Dataset Handling

| Dataset Size | Pages (your CRM) | Pages (ticketing) | Strategy |
|--------------|-----------------|------------|----------|
| 200 | 1 | 1 | Single call OK |
| 1,000 | 5 | 1 | Quick loop |
| 5,000 | 25 | 5 | Progress logging |
| 12,000 | 60 | 12 | Progress + checkpoints |
| 50,000+ | 250+ | 50+ | DataForge agent + batching |

### Progress Logging Pattern
```python
# For large datasets, log every N pages
CHECKPOINT_INTERVAL = 10  # Log every 10 pages

if page % CHECKPOINT_INTERVAL == 0:
    print(f"[CHECKPOINT] Page {page}: {len(all_records)} records")
    # Optional: save intermediate results
```

---

## Red Flags: When Pagination Was Skipped

| Sign | Problem |
|------|---------|
| Report says "Top 10 out of 1000" | Only fetched 1 page |
| Percentages seem too high (19%, 16%) | Small sample inflating results |
| Missing known large customers | Pagination cut them off |
| Round numbers (exactly 100, 1000) | Hit page limit, didn't continue |

---

## Checkpoints for Large Datasets

| Record Count | Strategy |
|--------------|----------|
| <1K | In-memory, single call OK if fits |
| 1K-10K | Full pagination, progress logging |
| 10K-100K | Full pagination + checkpoints every 10K |
| 100K+ | Consider DataForge agent, batch processing |

---

## MCP Tool Caching

When fetching many pages, MCP results are cached at:
```
~/.claude\projects\{project}\tool-results\
mcp-{server}-{function}-{timestamp}.txt
```

These can be aggregated with Python after collection is complete.

---

## The Rule

```
BEFORE ANY MCP ANALYSIS OR REPORT:
1. Check if result is paginated
2. If yes, iterate through ALL pages
3. Only analyze/report on COMPLETE dataset
4. Log total record count for verification

NEVER make conclusions from partial data.
```

---

*Last Updated: 2026-01-11 | System-wide sweep after $5.6M→$8.9M your CRM data loss incident*
