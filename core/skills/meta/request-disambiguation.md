---
user-invocable: false
---

# Request Disambiguation v2.0

> **Trigger keywords:** ambiguous request, which system, clarify system, incomplete request

> **v2.0 UPDATES:**
> - MANDATORY_BLOCKING flag for Skill Composer integration (Phase 1)
> - Explicit user confirmation required before proceeding
> - Disambiguation tracking in prediction-state.json

---

## MANDATORY_BLOCKING Protocol

**When Skill Composer detects ambiguous natural language (44% of requests):**

1. BLOCK execution immediately
2. Use AskUserQuestion tool with 2-4 specific options
3. Record user selection in `session/prediction-state.json`
4. Return explicit confirmation to calling system
5. Log disambiguation rate for metrics

**Integration:**
- Skill Composer calls this BEFORE generation pipeline
- Must complete successfully or generation fails
- Sets `"disambiguation_completed": true` in prediction state

---

## Rule

**STOP before querying external systems if the request uses ambiguous terms.**

---

## Ambiguous Terms → Multiple Systems

| Term Used | Could Mean | Systems to Clarify |
|-----------|------------|-------------------|
| "tickets" | Service tickets, support cases | your CRM (tickets) |
| "deals" | Sales opportunities | your CRM (opportunities) |
| "stage X" / "pipeline" | Deal stage, ticket status | your CRM (pipeline stages), your CRM (board statuses) |
| "contacts" | People records | your CRM, Google Contacts |
| "companies" | Organization records | your CRM, ITGlue |
| "tasks" | To-do items | your CRM, Google Tasks, Asana |
| "notes" | Activity notes | your CRM, ITGlue |
| "configs" / "configurations" | Asset configs | your CRM, ITGlue |
| "documents" | Stored files | ITGlue, Google Drive (your organization/your org), SharePoint |
| "files" / "drive" | Cloud storage | Google Drive (which account: your organization, your org, Personal?) |
| "shared drive" / "team drive" | Shared storage | Google Drive (your organization or your org workspace) |
| "passwords" | Credential storage | ITGlue |
| "calendar" / "events" | Meetings, appointments | Google Calendar (which account?) |
| "emails" | Email messages | Gmail (which account: your organization, your org, Personal?) |
| "catalog" / "products" | Product catalog | your catalog service SI, your CRM (procurement) |
| "catalog" / "bill of materials" | Project materials | your catalog service SI |

---

## When to Ask for Clarification

**ASK if:**
- Request mentions ambiguous term without system name
- Multiple MCPs/APIs could serve the request
- Person name mentioned but unclear which system tracks them

**DON'T ASK if:**
- System explicitly named: "your CRM deals", "ticketing tickets"
- Context makes it obvious: "sync your CRM to your CRM" (both named)
- Previous conversation established the system

---

## Clarification Format

```
Which system are you asking about?

| System | What I'd Query | MCP Available? |
|--------|----------------|----------------|
| **your CRM** | [specific object type] | ✅ Yes |
| **your CRM** | [specific object type] | ✅ Yes |
| **ITGlue** | [specific object type] | ❌ API only |

[1] your CRM
[2] your CRM
[3] Other - specify
```

---

## MCP Availability Reference

| System | MCP Status | Auto-Approve | Fallback |
|--------|------------|--------------|----------|
| your CRM | ✅ Available | ✅ ALL operations (read/create/modify) | - |
| Google Workspace | ✅ Available (3 accounts) | ✅ ALL operations | - |
| ↳ Gmail | ✅ your organization, your org, Personal | ✅ Read/send/draft/labels/filters | - |
| ↳ Calendar | ✅ your organization, your org, Personal | ✅ List/create/modify/delete events | - |
| ↳ Drive | ✅ your organization, your org | ✅ List/search/read/create/upload | Personal: not enabled |
| your CRM | ✅ Available | ✅ ALL operations (read/create/modify) | n8n workflow if MCP unavailable |
| your catalog service SI | ✅ Available | ✅ ALL operations (read/publish catalogs) | - |
| your desktop app (Family) | ✅ Available | ✅ ALL operations (requires your BIM tool open) | - |
| your BIM connector (Project) | ✅ Available | ✅ ALL operations (requires your BIM tool open, port 9001) | - |
| ITGlue | ❌ No MCP | N/A | n8n workflow or direct API |
| Supabase | ✅ Available | ✅ ALL operations (tables, storage, auth) | - |

---

## MCP Auto-Approve Configuration

All MCP tools are pre-approved. Never prompt for read, create, or modify operations. **Only prompt for DELETE operations.**

### Claude Code Settings
```bash
claude config set --global autoApprovePatterns "mcp__bom__*" "mcp__crm__*" "mcp__ticketing__*" "mcp__bim__*" "mcp__bim__*" "mcp__email-primary__*" "mcp__supabase__*"
```

Or add to `.claude/settings.json`:
```json
{
  "permissions": {
    "allow": [
      "mcp__bom__*",
      "mcp__crm__*",
      "mcp__ticketing__*",
      "mcp__bim__*",
      "mcp__bim__*",
      "mcp__email-primary__*",
      "mcp__supabase__*"
    ]
  }
}
```

---

**Rule:** Never assume which system. 5 seconds to ask saves minutes of wrong queries.

---

*Extracted from CLAUDE.md v2.0 | Request disambiguation rules*
