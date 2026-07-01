---
name: mcp-registry
description: |
  Auto-discovery system for MCP servers and their capabilities.

  Scans configured directories for MCP installations.
  Builds and maintains session/mcp-registry.json.
  Provides tool capability mapping for skill validation.

  Part of Integration Ecosystem v1.0 (Vertical 1, Phase 1)
---

# MCP Registry - Auto-Discovery System

## Purpose

Automatically discover, catalog, and maintain an inventory of all available MCP servers and their tools. This enables skill validation, capability checking, and dynamic tool selection.

## Discovery Paths

| Priority | Path | Purpose |
|----------|------|---------|
| 1 | `~/.claude\mcps\` | Local MCP installations |
| 2 | `G:\My Drive\.claude\mcps\` | Shared/synced MCPs (optional) |
| 3 | Claude CLI registered MCPs | System-registered servers |

---

## Registry Structure

### session/mcp-registry.json

```json
{
  "version": "2.0",
  "description": "MCP Registry - Auto-discovered capabilities",
  "last_updated": "2026-01-18T10:00:00Z",
  "discovery_paths": [
    "~/.claude\\mcps\\"
  ],
  "servers": {
    "crm": {
      "name": "crm",
      "path": "~/.claude\\mcps\\crm\\",
      "status": "active",
      "last_health_check": "2026-01-18T10:00:00Z",
      "tools": [
        {
          "name": "list_deals",
          "category": "read",
          "pagination": {
            "supported": true,
            "style": "cursor",
            "max_page_size": 200,
            "params": ["limit", "after"]
          },
          "rate_limit": {
            "calls_per_second": 10,
            "daily_limit": null
          }
        }
      ],
      "capabilities": {
        "pagination": true,
        "retry_after": true,
        "count_endpoints": false,
        "batch_operations": false
      }
    }
  },
  "tool_index": {
    "list_deals": "crm",
    "crm_tool": "crm",
    "ticketing_tool": "ticketing"
  },
  "statistics": {
    "total_servers": 13,
    "total_tools": 187,
    "read_tools": 142,
    "write_tools": 45,
    "last_full_scan": "2026-01-18T10:00:00Z"
  }
}
```

---

## Discovery Protocol

### Step 1: Scan MCP Directories

```python
def discover_mcp_servers(paths: list[str]) -> list[dict]:
    """
    Scan configured paths for MCP installations.

    Looks for:
    - package.json (Node.js MCPs)
    - dist/index.js (compiled MCPs)
    - src/ directory (source MCPs)
    - .env or .env.example (configuration)
    """
    servers = []

    for base_path in paths:
        if not os.path.exists(base_path):
            continue

        for folder in os.listdir(base_path):
            server_path = os.path.join(base_path, folder)
            if is_mcp_server(server_path):
                servers.append({
                    'name': folder,
                    'path': server_path,
                    'type': detect_mcp_type(server_path)
                })

    return servers
```

### Step 2: Extract Tool Definitions

```python
def extract_tools(server_path: str) -> list[dict]:
    """
    Extract tool definitions from MCP source.

    Sources (in priority order):
    1. src/tools.ts - TypeScript tool definitions
    2. src/index.ts - Main entry with tool exports
    3. package.json - Tool metadata
    4. README.md - Documentation parsing
    """
    tools = []

    # Parse TypeScript source for tool definitions
    tools_file = os.path.join(server_path, 'src', 'tools.ts')
    if os.path.exists(tools_file):
        tools = parse_typescript_tools(tools_file)

    return tools
```

### Step 3: Detect Capabilities

```python
def detect_capabilities(server_name: str, tools: list[dict]) -> dict:
    """
    Analyze tools to determine server capabilities.
    """
    capabilities = {
        'pagination': any(t.get('pagination', {}).get('supported') for t in tools),
        'retry_after': server_name in KNOWN_RETRY_AFTER_SERVERS,
        'count_endpoints': any('count_' in t['name'] for t in tools),
        'batch_operations': any('batch_' in t['name'] or 'bulk_' in t['name'] for t in tools)
    }

    return capabilities
```

---

## Known MCP Servers

### Current Inventory (13 servers)

| Server | Tools | Pagination | Write | Status |
|--------|-------|------------|-------|--------|
| **ticketing** | 80+ | page-based | Yes | Active |
| **crm** | 18 | cursor-based | Yes | Active |
| **catalog** | 15+ | page-based | Limited | Active |
| **email-primary** | 20+ | token-based | Yes | Active |
| **itglue** | 9 | cursor-based | No | Ready |
| **playwright** | 10+ | N/A | N/A | Active |
| **bim-tool** | 50+ | N/A | Yes | Active |
| **bim** | 30+ | N/A | Yes | Inactive |
| **supabase** | 10+ | offset-based | Yes | Active |

---

## Tool Categories

### Read Operations (Safe)

```
list_*      - Paginated list retrieval
get_*       - Single record fetch
search_*    - Filtered search
count_*     - Record counting
```

### Write Operations (Requires Caution)

```
create_*    - New record creation
update_*    - Record modification
delete_*    - Record removal
add_*       - Append operations
```

### Special Operations

```
associate   - Link records
batch_*     - Bulk operations
sync_*      - Synchronization
```

---

## Pagination Style Detection

### Cursor-Based (your CRM, ITGlue)

```json
{
  "style": "cursor",
  "params": ["limit", "after"],
  "response_cursor": "paging.next.after",
  "max_page_size": 200
}
```

### Page-Based (your CRM, your catalog service)

```json
{
  "style": "page",
  "params": ["page", "pageSize"],
  "response_indicator": "array_length < pageSize",
  "max_page_size": 1000
}
```

### Offset-Based (Supabase)

```json
{
  "style": "offset",
  "params": ["limit", "offset"],
  "response_indicator": "array_length < limit",
  "max_page_size": 1000
}
```

### Token-Based (Google)

```json
{
  "style": "token",
  "params": ["page_size", "page_token"],
  "response_cursor": "nextPageToken",
  "max_page_size": 100
}
```

---

## Usage Patterns

### Check Tool Availability

```python
def is_tool_available(tool_name: str) -> bool:
    """Check if a tool exists in the registry."""
    registry = load_registry()
    return tool_name in registry['tool_index']
```

### Get Tool Configuration

```python
def get_tool_config(tool_name: str) -> dict:
    """Get full configuration for a tool."""
    registry = load_registry()
    server_name = registry['tool_index'].get(tool_name)
    if not server_name:
        return None

    server = registry['servers'][server_name]
    for tool in server['tools']:
        if tool['name'] == tool_name:
            return {
                'server': server_name,
                'tool': tool,
                'capabilities': server['capabilities']
            }

    return None
```

### Get Pagination Config

```python
def get_pagination_config(tool_name: str) -> dict:
    """Get pagination configuration for a tool."""
    config = get_tool_config(tool_name)
    if not config:
        return None

    return config['tool'].get('pagination', {
        'supported': False
    })
```

---

## Registry Refresh Protocol

### Automatic Refresh Triggers

| Trigger | Action |
|---------|--------|
| Session start | Check last_updated, refresh if >24h |
| New MCP detected | Add to registry |
| Tool call 404 | Re-scan that server |
| Manual request | Full registry rebuild |

### Refresh Command

```
┌─ REGISTRY REFRESH ──────────────────────────────────────┐
│                                                         │
│ Command: "refresh mcp registry"                        │
│                                                         │
│ Process:                                               │
│ 1. Scan all discovery paths                            │
│ 2. Compare with existing registry                      │
│ 3. Add new servers/tools                               │
│ 4. Remove missing servers                              │
│ 5. Update capabilities                                 │
│ 6. Write session/mcp-registry.json                     │
│                                                         │
│ Output:                                                │
│ [REGISTRY] Refreshed: 13 servers, 187 tools            │
│ [REGISTRY] Added: itglue (9 tools)                     │
│ [REGISTRY] Removed: old-mcp (deprecated)               │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## Integration with Skill Composer

The registry is used by `skill-composer.md` to validate tool references:

```python
def validate_skill_tools(skill_content: str) -> list[str]:
    """
    Check that all MCP tools referenced in a skill exist.

    Returns list of validation errors (empty = valid).
    """
    errors = []
    registry = load_registry()

    # Find all tool references in skill
    tool_refs = extract_tool_references(skill_content)

    for tool in tool_refs:
        if tool not in registry['tool_index']:
            errors.append(f"Unknown tool: {tool}")

    return errors
```

---

## Health Check Integration

Registry provides data for `mcp-health-dashboard.md`:

```python
def get_server_health_status(server_name: str) -> dict:
    """
    Get health status for a server from registry.
    """
    registry = load_registry()
    server = registry['servers'].get(server_name)

    if not server:
        return {'status': 'unknown', 'reason': 'Not in registry'}

    return {
        'status': server.get('status', 'unknown'),
        'last_check': server.get('last_health_check'),
        'tools_count': len(server.get('tools', [])),
        'capabilities': server.get('capabilities', {})
    }
```

---

## Quick Reference

```
┌─ MCP REGISTRY COMMANDS ─────────────────────────────────┐
│                                                         │
│ "refresh mcp registry"    - Full rescan                │
│ "list mcp servers"        - Show all servers           │
│ "check tool X"            - Verify tool exists         │
│ "mcp capabilities"        - Show all capabilities      │
│                                                         │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ REGISTRY LOCATION:                                     │
│ session/mcp-registry.json                              │
│                                                         │
│ DISCOVERY PATHS:                                       │
│ 1. ~/.claude\mcps\                  │
│ 2. G:\My Drive\.claude\mcps\ (if mounted)              │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## Related Skills

| Skill | Relationship |
|-------|--------------|
| `mcp-pagination.md` | Uses registry for page size lookup |
| `mcp-auto-retry.md` | Uses registry for retry config |
| `mcp-pagination-wrapper.md` | Uses registry for auto-detection |
| `mcp-health-dashboard.md` | Monitors registry servers |
| `skill-composer.md` | Validates tool references |

---

*MCP Registry v1.0 | Integration Ecosystem Phase 1 | Day 2 Deliverable*
