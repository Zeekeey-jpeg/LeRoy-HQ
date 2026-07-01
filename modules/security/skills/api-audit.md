# API Audit — REST & GraphQL Security Checklist

**Owner:** cyber-operator
**Trigger:** `api audit`, `api security`, `api checklist`, `audit this api`, `rest audit`, `graphql audit`
**Purpose:** Structured REST and GraphQL API security audit mapped to OWASP API Security Top 10:2023. Outputs a priority-ranked finding table + per-finding evidence templates.

**Scope:** HackerOne in-scope API assets only. Verify target is in scope before any testing.

---

## Pre-Audit Setup

Before executing any section, complete this setup block:

```
## Target API: {Program} — {API Base URL}
**Auth token(s) available:** YES / NO
**Two test accounts configured:** YES / NO (required for IDOR/BOPLA)
**Burp Suite proxy active:** YES / NO
**Scope confirmed:** YES / NO → [scope URL verified]
```

If two accounts not available: skip IDOR (Section 3) and BOPLA (Section 4) — mark as "DEFERRED: requires two-account setup."

---

## OWASP API Security Top 10:2023 Mapping

| Section | OWASP ID | API Risk |
|---------|----------|---------|
| [1] Authentication | API2:2023 | Broken Auth |
| [2] JWT Security | API2:2023 | Broken Auth |
| [3] Object Level Auth / IDOR | API1:2023 | BOLA |
| [4] Mass Assignment / BOPLA | API3:2023 | Broken Object Property Auth |
| [5] Rate Limiting & Business Logic | API4:2023 | Unrestricted Resource Consumption |
| [6] Sensitive Data Exposure | API3:2023 + API8:2023 | Security Misconfiguration |
| [7] SSRF via Webhooks/URLs | API7:2023 | SSRF |
| [8] GraphQL-Specific | API1:2023 | BOLA + Introspection |
| [9] Parameter Pollution & Verb Tampering | API1:2023 + API3:2023 | Auth bypass |
| [10] Dependency & Version Exposure | API9:2023 | Improper Inventory |

---

## Section 1 — Authentication (OWASP API2:2023)

**Goal:** Find endpoints that process requests without valid authentication.

### Tests

**1.1 — Unauthenticated Access**
```
For each API endpoint:
1. Send request with NO Authorization header
2. Send request with empty Bearer token: Authorization: Bearer
3. Send request with null token: Authorization: Bearer null
4. Send request with token=false: Authorization: Bearer false

Expected: 401 Unauthorized
Finding if: 200 OK or actual data returned
```

**1.2 — Token Validation**
```
1. Send request with expired token (keep old token after logout)
2. Send request with modified token (change last 3 chars)
3. Send request after password change (should invalidate previous tokens)
4. Send request to Account A endpoints using Account B's token

Expected: 401 for all
Finding if: any succeeds
```

**1.3 — Password Reset Poison**
→ Load `host-header-attacks.md` → Section: Password Reset Poison

**1.4 — MFA/2FA Bypass**
→ Load `auth-bypass-methodology.md` → Section: MFA Bypass Techniques

### Evidence Template (Auth Finding)
```
Endpoint: [METHOD] /api/v1/[path]
Token State: [none/expired/modified/cross-account]
Request: [full HTTP request]
Response: [full HTTP response showing unauthorized access]
Impact: [what data/actions are accessible]
```

---

## Section 2 — JWT Security (OWASP API2:2023)

**Goal:** Exploit JWT implementation flaws for auth bypass or privilege escalation.

→ **Load `jwt-attack-playbook.md` for full protocol.**

**Quick checklist (execute in order):**

| Test | Command | Finding |
|------|---------|---------|
| Decode token | `echo "[payload]" \| base64 -d` | Read claims |
| alg:none bypass | Set `"alg":"none"`, remove signature | 200 = Critical |
| RS256→HS256 confusion | Sign with public key as HMAC secret | 200 = Critical |
| Weak secret bruteforce | `hashcat -a 0 -m 16500 [token] rockyou.txt` | Cracked = Critical |
| kid injection | `"kid":"../../../etc/passwd"` | File read = Critical |
| Expired token test | Use token past exp claim | 200 = High |

---

## Section 3 — Object Level Authorization / IDOR (OWASP API1:2023)

**Goal:** Access or modify another user's objects by manipulating IDs.

→ **Load `idor-testing-protocol.md` for full methodology.**

**Setup required:** Two separate accounts (A = attacker, B = victim)

### ID Discovery
```
Patterns to look for:
- /api/users/{id}/profile
- /api/orders/{id}
- /api/documents/{id}/download
- /api/payments/{id}
- /api/messages/{id}

ID types to test:
- Sequential integers: try victim_id = attacker_id ± 1
- UUID: swap Account B UUID into Account A request
- Base64 encoded: decode → swap → re-encode
- Composite IDs: {userId}-{resourceId} → swap userId only
```

### Test Protocol
```
1. With Account A: Create/view resource → note {resource_id}
2. With Account B: Create/view different resource → note {resource_id_b}
3. With Account A token: GET /api/resource/{resource_id_b}
4. If 200 + Account B data returned → IDOR confirmed
5. Test all CRUD: GET, PUT, PATCH, DELETE, POST (indirect)
```

### Horizontal vs Vertical
- **Horizontal IDOR:** Same role, different user's data (High 7.5)
- **Vertical IDOR:** Lower role accessing higher role's data (Critical 9.1)

---

## Section 4 — Mass Assignment / BOPLA (OWASP API3:2023)

**Goal:** Inject undocumented properties into PUT/PATCH/POST to modify privileged fields.

### Property Discovery
```
Sources for undocumented fields:
1. GET response properties → try injecting same fields in PUT/PATCH
2. API documentation → note readonly or admin-only fields
3. Source maps → load a source-map recon step if available
4. JS bundle analysis → search for role, isAdmin, privilege, tier, verified

Common high-value targets:
- "role": "admin"
- "isVerified": true
- "isAdmin": true
- "plan": "enterprise"
- "credit": 999999
- "balance": 99999
- "subscriptionTier": "premium"
- "emailVerified": true
- "twoFactorEnabled": false
```

### Test Protocol
```
1. Legitimate PATCH request: PATCH /api/users/me
   Body: {"displayName": "test"}

2. Injected PATCH: PATCH /api/users/me
   Body: {"displayName": "test", "role": "admin"}

3. Check response: does it reflect injected field?
4. Re-fetch profile: GET /api/users/me — does role show "admin"?

Repeat for isAdmin, plan, verified, balance, credit.
```

### API Version Regression
```
If /api/v2/ endpoint is patched, test /api/v1/ — often unpatched.
Also test: /api/v1.0/, /api/v1.1/, /api/mobile/, /api/internal/
```

---

## Section 5 — Rate Limiting & Business Logic (OWASP API4:2023)

**Note:** Do NOT mention "rate limiting" in reports (exclusion trigger). Frame as "enumeration" or "unrestricted resource consumption."

### Tests
```
1. Coupon/voucher abuse:
   - Apply coupon, remove from cart, re-apply → balance persists?
   - Apply 2 coupons simultaneously (race condition) → load race-condition.md

2. Quantity abuse:
   - Order quantity = 0 → still ships?
   - Order quantity = -1 → refund without purchase?
   - Order quantity = 99999 → price overflow?

3. Email enumeration:
   - POST /api/auth/reset {"email": "valid@test.com"} → timing diff vs invalid
   - Differential: 200 OK vs 404 = username enumeration (frame as privacy impact)

4. OTP/TOTP:
   - Same OTP reuse (should be single-use)
   - OTP from different session → replay
```

---

## Section 6 — Sensitive Data Exposure (OWASP API3 + API8:2023)

### Tests
```
1. Error verbosity:
   - Send malformed JSON → does error reveal stack trace / framework version?
   - Send SQL-like input → does error leak query structure?
   - Trigger 500 → is it a generic error or a full stack trace?

2. Debug endpoints:
   GET /api/debug
   GET /api/health (what does it reveal?)
   GET /api/status
   GET /api/v1/admin
   GET /api/internal

3. Response over-fetching:
   - User profile endpoint returning ALL fields (including hashed passwords, internal IDs, PII)
   - List endpoint returning 500 records when 10 expected

4. JavaScript source exposure:
   → Load a source-map recon step if .js.map files detected
```

---

## Section 7 — SSRF via Webhooks / URL Parameters (OWASP API7:2023)

**Goal:** Force the server to make outbound HTTP requests to internal infrastructure.

→ **Load `ssrf-methodology.md` for full bypass matrix.**

### Quick Surface Scan
```
API parameters to test:
- webhook_url, callback_url, redirect_url, return_url
- avatar_url, profile_picture_url, import_url
- notification_endpoint, hook_url
- Any parameter containing "url", "uri", "link", "host", "domain"

Test payload: https://[your-interactsh-id].oast.fun

Blind SSRF: no response body — check interactsh for DNS callback.
If DNS callback fires → SSRF confirmed.

Internal targets:
- http://169.254.169.254/latest/meta-data/
- http://localhost:80/
- http://127.0.0.1:8080/
```

---

## Section 8 — GraphQL-Specific

**Goal:** Exploit GraphQL-specific weaknesses: introspection, batching, depth.

→ **Load `skills/domains/cyber/` index for `Cyber-GraphQL-DirectiveDeception.md` vault note.**

### Tests
```
1. Introspection enabled:
   POST /graphql
   {"query": "{__schema{types{name}}}"}
   Finding if: returns schema → enumerate all types/fields

2. Field suggestion leakage:
   POST /graphql
   {"query": "{usr{id}}"}   ← typo
   Finding if: "Did you mean 'user'?" → confirms field names

3. Alias batching (rate limit bypass):
   {"query": "{ a:login(email:'test@test.com',pass:'a') b:login(email:'test@test.com',pass:'b') c:login(...) }"}
   Finding if: multiple attempts in one request → auth enumeration

4. Query depth attack:
   {"query": "{ user { friends { friends { friends { friends { id } } } } } }"}
   Finding if: no depth limit → server hangs or returns data

5. IDOR via GraphQL:
   {"query": "{ user(id: \"[victim-id]\") { email password } }"}
```

---

## Section 9 — Parameter Pollution & Verb Tampering

### Tests
```
1. HTTP Verb Tampering:
   Endpoint: GET /api/admin/users (403)
   Try: POST, PUT, DELETE, PATCH, OPTIONS, HEAD, TRACE, CONNECT
   Finding if: different verb returns 200

2. HTTP Parameter Pollution:
   ?user_id=attacker_id&user_id=victim_id
   ?user_id=victim_id&user_id=attacker_id
   Finding if: server processes victim_id

3. Method Override Headers:
   X-HTTP-Method-Override: DELETE
   X-Method-Override: DELETE
   X-HTTP-Method: DELETE
   Finding if: DELETE executed via GET/POST

4. Path Traversal in API Routes:
   /api/v1/users/../admin/users
   /api/v1/users/%2e%2e/admin/users
```

---

## Section 10 — Inventory & Version Exposure (OWASP API9:2023)

```
1. API version headers:
   Check responses for: X-API-Version, X-Version, Server, X-Powered-By
   Finding if: reveals framework/version → cross-ref CVE database

2. Legacy endpoint discovery:
   /api/v1/ (if current is v2)
   /api/v0/
   /api/beta/
   /api/legacy/
   Finding if: legacy endpoints respond with less security

3. .well-known endpoints:
   GET /.well-known/openapi.json
   GET /swagger.json
   GET /api-docs
   GET /openapi.yaml
   Finding if: API spec returned → full endpoint enumeration
```

---

## Priority Output Table

After executing all applicable sections, generate this table:

```markdown
## API Audit Findings — {Program Name} / {API URL}
**Date:** {date} | **Sections Executed:** {list} | **Two Accounts:** {YES/NO}

| # | Section | Finding | OWASP | Est. Severity | Evidence | Report? |
|---|---------|---------|-------|---------------|----------|---------|
| 1 | [section] | [what was found] | [API1-10]:2023 | Critical/High/Med/Low | [Y/N + type] | [YES/NO/NEEDS MORE] |
| 2 | ... | ... | ... | ... | ... | ... |

**Confirmed findings ready to report:** [count]
**Needs more evidence:** [count]
**Tested but nothing found:** [count]
```

**For each "YES" finding:** Run a report quality gate against the draft before submitting.

---

## Semgrep Integration (Source Access Only)

If you have API source code available:
```bash
# OWASP API Security Top 10 ruleset
semgrep --config "p/owasp-top-ten" /path/to/api/

# Auth bypass patterns
semgrep --config "p/jwt" /path/to/api/

# Injection
semgrep --config "p/sql-injection" /path/to/api/
semgrep --config "p/command-injection" /path/to/api/
```

---

*API Audit v1.0 | cyber-operator | OWASP API Security Top 10:2023 | HackerOne authorized scope | 2026-03-01*
