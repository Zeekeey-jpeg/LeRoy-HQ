---
user-invocable: false
---

# Permissions

> **Trigger keywords:** permissions, can I delete, approval needed, autonomous, ask permission

---

## Autonomous Permissions (Local Operations)

### Always Proceed (No Asking)
- **File:** read/write/create/delete any source file
- **Git:** add, commit, push, pull, branch, merge, stash, PR
- **Packages:** pip, npm, nuget, dotnet
- **Build:** msbuild, npm run, python execution
- **Shell:** any development command
- **Database:** Supabase API, migrations, queries

### Ask Only When
- API keys/secrets needed
- Multiple valid architectural paths
- Destructive production operations
- Cost-incurring external signups
- Genuine ambiguity requiring clarification

**Rule:** Do the work. Don't ask permission. Only pause for genuine blockers.

---

## External System Permissions

These rules apply to **connected external systems** (your CRM, ITGlue, n8n, Google Calendar, etc.), NOT local code/files.

### Permission Matrix

| Action | Permission | Notes |
|--------|------------|-------|
| **READ** | Always allowed | Query, search, fetch, list - no restrictions |
| **CREATE** | Always allowed | Add new records, contacts, tickets, workflows |
| **MODIFY** | Always allowed | Update existing records, change fields, edit configs |
| **DELETE** | **REQUIRES APPROVAL** | Must confirm before removing ANY record |

### Systems Covered

```yaml
Business Systems (API/MCP):
  - your CRM Manage (tickets, companies, contacts, configs)
  - your CRM (deals, contacts, companies, notes)
  - ITGlue (documents, passwords, configs, assets)
  - n8n (workflows, credentials, executions)
  - Supabase (rows, tables - production data)

Google Workspace (MCP - 3 accounts):
  - Gmail (emails, labels, filters) - your organization, your org, Personal
  - Google Calendar (events, calendars) - your organization, your org, Personal
  - Google Drive (files, folders, shared drives) - your organization, your org only
    - List files/folders
    - Search by name/type/modified date
    - Read file content/metadata
    - Create files/folders
    - Upload files
    - Move/copy files
    - Share/permission management

your desktop app (MCP - requires your BIM tool open):
  - Family parameters (create, modify, delete, formulas)
  - Family types (create, modify, delete, rename)
  - Geometry and dimension references
  - Current selection (real-time)
  - Document operations (save, load into project)
  - See: ~/.claude\mcps\bim\README.md
```

---

## Deletion Rules

### Default: ASK BEFORE DELETE

```
Before deleting in external system:
1. State what will be deleted (system, record type, identifier)
2. Wait for explicit "yes" / "approved" / "go ahead"
3. Only then execute deletion
```

### Exception: Pre-Approved Deletions

If user specifies deletion target upfront, proceed without re-asking:

```
User: "Delete all emails from noreply@spam.com"
→ Approved - execute without additional confirmation

User: "Clean up my inbox"
→ NOT approved - ask what specifically to delete
```

---

## Examples

```yaml
ALLOWED (no asking):
  - Create your CRM ticket
  - Update your CRM deal stage
  - Add n8n workflow
  - Modify ITGlue document
  - Create calendar event
  - Send email
  - Archive email (move, not delete)

REQUIRES APPROVAL:
  - Delete your CRM company
  - Remove your CRM contact
  - Delete n8n workflow
  - Trash ITGlue password entry
  - Delete calendar event
  - Permanently delete email
  - Delete Supabase rows

PRE-APPROVED (user specified target):
  - "Delete the test ticket I just created" → OK
  - "Remove duplicates from this your CRM list" → OK (if list specified)
  - "Delete emails older than 30 days from Promotions" → OK
```

---

## Why This Matters

External system deletions are often **irreversible** or require admin intervention to restore. Local code has Git; external systems usually don't.

---

*Extracted from CLAUDE.md v2.0 | Permission rules*
