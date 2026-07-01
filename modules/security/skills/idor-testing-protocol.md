# Skill: IDOR Testing Protocol
**Vertical:** Access Control — Insecure Direct Object Reference
**Trigger:** "idor", "access control", "object reference", "horizontal access", "vertical idor", "autorize"
**Autonomy:** FULL — Two-account model; write operations require reversible-only changes
**Avg test time:** 30–60 minutes per target
**Severity range:** Medium–Critical (Critical for financial data, auth material)
**Bounty range:** $500–$5,000+ (High/Critical tier)

**Pattern Reference:** `a technique-reference note` (full methodology, checklists, ID bypass techniques)

---

## Quick Setup

### Two-Account Model
```
Account A: Attacker (your session in Burp/Autorize)
Account B: Victim (creates test data, note all IDs)

Test data to create in Account B:
- Name: "IDOR-Test-Victim-B"
- Order/item: "IDOR-Test-Item-B"
- File: "idor-test-victim-b.pdf"
- Message: "IDOR-Test-Message-B"
```

### Autorize Configuration
```
1. BApp Store → install Autorize
2. Autorize tab → Configuration:
   Cookie: session=ACCOUNT_A_SESSION
   # OR: Authorization: Bearer ACCOUNT_A_JWT_TOKEN
3. Exclusions: \.js$, \.css$, /login, /logout, /register, /oauth, /health
4. Enforcement detectors: "403", "Forbidden", "Unauthorized", "Access denied"
5. Toggle Autorize ON → browse everything as Account B
6. Review RED (IDOR candidates) and ORANGE (auth bypass candidates)
```

---

## Core Test Matrix

```
HORIZONTAL (same role):
  □ GET other user's: profile, settings, orders, messages, files, payment-methods, api-keys
  □ PUT/PATCH other user's resources (reversible changes: name → "IDOR-Test-[timestamp]")
  □ DELETE test resources (create expendable resources in Account B first)
  □ Test all parameter locations: URL path, query string, request body, headers

VERTICAL (privilege escalation):
  □ Discover admin endpoints: JS bundles, source maps, Wayback, error messages
  □ Access admin endpoints as regular user: /api/admin/*, /internal/*, /manage/*
  □ Role parameter tampering in profile update / registration
  □ Test impersonation endpoints

INDIRECT:
  □ Add user_id to endpoints that don't normally accept it (parameter injection)
  □ Search/export endpoints — check if scoped to current user
  □ Batch/bulk endpoints: POST /api/users/batch {"ids": ["MY_ID", "USER_B_ID"]}
```

---

## ID Type Quick Reference

| Format | Attack Method |
|--------|--------------|
| Sequential integer | Enumerate ±100: change `1234` → `1235` |
| Base64-encoded | Decode → increment → re-encode: `MTIzNA==` → `MTIzNQ==` |
| Relay global ID (GraphQL) | Decode: `VXNlcjoxMjM0` = `User:1234` → encode `User:1235` |
| UUID v4 | Find via leakage: team member lists, public profiles, error messages, pagination cursors |
| Composite `org-42_user-1234` | Modify each component independently |

---

## HTTP Method Matrix

For every endpoint, test:
```
GET    → read access
POST   → create/overwrite
PUT    → full update
PATCH  → partial update
DELETE → destroy (test resources only)
HEAD   → metadata / existence probe
```
Same endpoint may have different authorization per method. GET protected ≠ PUT protected.

---

## GraphQL IDOR

```graphql
# Direct node access:
{ node(id: "USER_B_GLOBAL_ID") { ... on User { email orders { totalAmount } } } }

# Mutation:
mutation { updateUser(id: "USER_B_ID", input: {email: "attacker@evil.com"}) { id } }

# Relay ID decode → re-encode with +1 ID
```

---

## Severity Calibration

| Resource | Severity |
|----------|---------|
| Full PII (email, phone, SSN, address) | High |
| Financial data (balances, cards, transactions) | Critical |
| Auth material (passwords, API keys, tokens) | Critical |
| Messages / private content | Medium-High |
| Admin function execution | High-Critical |
| Metadata only (existence, count) | Low-Medium |

---

## Report Template

```
Title: IDOR in [endpoint] allows [read/write/delete] of other users' [resource]
Severity: [High/Critical]

Steps:
1. Create Account A (attacker), Account B (victim)
2. In Account B, create: [test data]
3. Note Account B's [resource] ID: [how to find]
4. As Account A, send: [exact HTTP request]
5. Response contains Account B's data: [what to look for]

Impact:
- Any authenticated user can [read/modify/delete] ANY user's [resource type]
- Affected data: [fields — email, SSN, etc.]
- Scale: [all N registered users]
- No rate limiting → mass enumeration possible

Remediation:
- Implement object-level authorization check on [endpoint]
- Before returning resource, verify: WHERE user_id = auth_user.id AND resource_id = requested_id
```

**Mass IDOR:** Don't enumerate all users. Show 3 IDs, state total user count from X-Total-Count header, redact all real PII.

---

## Autorize Manual Supplements (what Autorize misses)

```
□ Sequential ID enumeration (script it with requests.Session)
□ Parameter injection (add user_id where it doesn't belong)
□ HTTP method variation (GET→PUT→DELETE)
□ Admin endpoint discovery
□ Encoded/obfuscated ID manipulation
□ Cross-tenant org_id/tenant_id testing
□ GraphQL field-level IDOR
□ WebSocket message authorization
□ Batch endpoint authorization
```

---

*Cyber Skill | Owner: cyber-operator | IDOR Testing Protocol | 2026-02-25*
