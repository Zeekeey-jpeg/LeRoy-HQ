# Human-in-the-Loop (HiL) Gate

**Version:** 1.0 — NemoClaw-inspired, Claude Code native
**Trigger:** `"hil gate"`, `"approve action"`, `"policy check"`, `"hil approve"`
**Integrates with:** guardian, agent-spawn-validator.py, network-policy.yaml

---

## Purpose

The HiL gate surfaces high-risk agent actions for explicit operator approval before execution. Inspired by NemoClaw's approval TUI — implemented natively in Claude Code without Linux kernel requirements.

Not a blocker for normal work. A checkpoint for actions with external, financial, or destructive consequences.

---

## High-Risk Action Taxonomy

### Tier A — ALWAYS Gate (stop and confirm)
These actions MUST surface for approval before execution:

| Action Type | Examples | Why |
|-------------|----------|-----|
| **Email sends** | `send_mail`, `send_gmail_message` | Irreversible. Visible to external parties. |
| **External API writes** | your CRM create/update deal/contact, your CRM create ticket | Modifies customer data in production systems. |
| **Financial operations** | Stripe charge, payment processing | Direct monetary impact. |
| **Repository pushes** | `git push`, `gh pr create` | Visible to collaborators, triggers CI/CD. |
| **Bulk deletes** | Delete 10+ records, `rm -rf` patterns | Potentially catastrophic data loss. |
| **Permission changes** | Add/remove user access, API key rotation | Security surface change. |

### Tier B — FLAG and LOG (surface as warning, continue with acknowledgment)
These actions surface a warning and log the event:

| Action Type | Examples | Why |
|-------------|----------|-----|
| **High-risk domain access** | Domains in `network-policy.yaml` high_risk list | Unusual egress patterns. |
| **File writes outside allowed zones** | Writes outside `~/.claude/` or `~/Desktop/Projects/` | Out-of-zone filesystem access. |
| **Destructive file operations** | Overwrite of files >50 lines, delete with no backup | Potentially unrecoverable. |
| **Calendar event creation** | External calendar invites | Visible to attendees. |

### Tier C — AUDIT ONLY (log, no interruption)
- All WebFetch calls (logged to `network-policy-log.jsonl`)
- All Write/Edit calls (logged to `filesystem-policy-log.jsonl`)
- All agent spawns (logged to `agent-spawn-log.jsonl`)

---

## Approval Protocol

### Step 1: Identify high-risk action
Before executing any Tier A action, the COO presents:

```
┌─ HiL GATE ──────────────────────────────────────────────────┐
│ Action: Send email to [recipient]                            │
│ Subject: [subject line]                                      │
│ Body preview: [first 100 chars...]                           │
│ Risk: TIER A — External send (irreversible)                  │
│                                                              │
│ Approve? [yes / no]                                          │
└──────────────────────────────────────────────────────────────┘
```

### Step 2: Wait for explicit approval
- "yes", "approve", "go ahead", "send it", "do it" → execute
- "no", "stop", "block", "don't", "cancel" → abort and log
- Silence / ambiguous → prompt again (do NOT auto-execute)

### Step 3: Log decision
Every HiL gate decision is logged to `session/hil-gate-log.jsonl`:

```json
{
  "timestamp": "2026-03-18T14:22:00",
  "action_type": "email_send",
  "description": "Email to tom@example.com — Re: Proposal",
  "decision": "approved",
  "decided_by": "council"
}
```

---

## Integration Points

### Guardian Agent
Before issuing APPROVED verdict on commits that involved external actions:
- Check `session/hil-gate-log.jsonl` for Tier A actions
- Verify each logged action has a corresponding `"decision": "approved"` entry
- Flag missing HiL entries as WARN severity

### agent-spawn-validator.py
Logs Tier B actions (high-risk domain, out-of-zone filesystem) automatically.
Does NOT pause execution for Tier B — COO surfaces at end of task if pattern detected.

### Network Policy
`session/network-policy-log.jsonl` feeds HiL gate for pattern review.
If high_risk domain count > 3 in a session → surface summary to COO.

---

## Quick Reference: What Requires Approval

```
ALWAYS ASK FIRST (Tier A):
  ✓ Send email
  ✓ Create/update your CRM deal or contact
  ✓ Create your CRM ticket
  ✓ git push / gh pr create
  ✓ Stripe charge
  ✓ Bulk delete (10+ records)

LOG AND SURFACE (Tier B):
  ⚠ High-risk domain access
  ⚠ File write outside ~/.claude/ or ~/Desktop/Projects/
  ⚠ Calendar invite creation

AUDIT ONLY (Tier C):
  📋 WebFetch calls
  📋 Write/Edit file operations
  📋 Agent spawns
```

---

## Implementation Notes

This is a **protocol skill**, not executable code. The HiL gate runs in the COO's judgment layer:
1. COO recognizes Tier A action is about to be requested
2. COO presents HiL gate format above BEFORE calling the tool
3. COO waits for the user's explicit approval
4. Only then calls the actual tool (send_mail, etc.)

The `agent-spawn-validator.py` hook handles Tier B/C logging automatically in the background.

---

*HiL Gate v1.0 | NemoClaw-inspired architecture | Claude Code native*
