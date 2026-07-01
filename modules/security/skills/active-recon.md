---
title: Active Recon Pipeline
version: 1.0
added: 2026-04-11
owner: cyber-operator
trigger: Full sweeps with wildcard scope, IP ranges, or "infrastructure" in scope
---

# Active Recon Pipeline

> Replaces passive-only crt.sh recon. This is the NEW STANDARD for all full bounty sweeps.
> passive-recon.md = OSINT-only contexts (no active packets allowed). This file = everything else.

**Auto-load conditions (ANY triggers this file):**
```
IF scope.contains("*.")                  → load active-recon.md
IF scope.contains_cidr == TRUE           → load active-recon.md
IF scope.contains_ip_range == TRUE       → load active-recon.md
IF scope.contains("infrastructure")      → load active-recon.md
IF ctf_box == TRUE                       → load active-recon.md
IF program_scope is NOT single-domain    → load active-recon.md
```

---

## 5-PHASE PIPELINE

### Phase 1 — Passive Source Collection

Collect subdomains from passive sources (no active DNS queries):

```bash
# Certificate Transparency (crt.sh)
curl -s "https://crt.sh/?q=%.{TARGET}&output=json" | \
  jq -r '.[].name_value' | sort -u | grep -v "^*" > ct-log.txt

# Wayback Machine CDX API
curl -s "http://web.archive.org/cdx/search/cdx?url=*.{TARGET}&output=text&fl=original&collapse=urlkey" | \
  grep -oP '[a-zA-Z0-9.-]+\.{TARGET}' | sort -u > wayback.txt

# AlienVault OTX (no API key required)
curl -s "https://otx.alienvault.com/api/v1/indicators/domain/{TARGET}/passive_dns" | \
  jq -r '.passive_dns[].hostname' 2>/dev/null | sort -u > otx.txt

# Merge passive sources
cat ct-log.txt wayback.txt otx.txt | sort -u > passive-subdomains.txt
```

### Phase 2 — Active Enumeration

```bash
# subfinder (ProjectDiscovery — fastest multi-source passive DNS)
subfinder -d {TARGET} -all -recursive -silent -o subfinder-out.txt

# amass passive mode (OWASP — never use -brute on BB targets)
amass enum -passive -d {TARGET} -o amass-out.txt

# assetfinder
assetfinder --subs-only {TARGET} > assetfinder-out.txt

# Merge all sources — deduplicate
cat passive-subdomains.txt subfinder-out.txt amass-out.txt assetfinder-out.txt | \
  sort -u | grep -E "^[a-zA-Z0-9.-]+$" > all-subdomains.txt

echo "[RECON] Total unique subdomains: $(wc -l < all-subdomains.txt)"
```

**Rate Limit Doctrine (ABSOLUTE — no exceptions on BB targets):**
- `amass`: `-passive` flag MANDATORY. NEVER `-brute` on bug bounty programs.
- `subfinder`: passive DNS aggregation only. No active resolution in enum phase.
- Never enumerate on out-of-scope hosts. Cross-check against program scope before Phase 3.

### Phase 3 — Live Host Resolution

```bash
# httpx: resolve live hosts, grab status codes, titles, tech fingerprint
cat all-subdomains.txt | httpx \
  -silent \
  -status-code \
  -title \
  -tech-detect \
  -ip \
  -follow-redirects \
  -rate-limit 50 \
  -o live-hosts.json \
  -json

echo "[RECON] Live hosts: $(wc -l < live-hosts.json)"

# Extract clean live host list
cat live-hosts.json | jq -r '.url' > live-hosts.txt
```

**Tech fingerprint output feeds directly into Tier 2 overseer routing decisions:**
- React/Next.js/Vue/Angular → trigger js-pipeline.md
- GraphQL indicator → trigger graphql-abuse.md
- gRPC headers → trigger protocol-fuzzer.md
- WordPress/Drupal/Joomla → trigger nuclei CMS templates
- OAuth/SSO detected → trigger oauth-harvester.md

### Phase 4 — Port Reachability (Non-Standard Ports)

```bash
# Lightweight port check for common non-standard service ports
# Only on live hosts from Phase 3 — never on full IP ranges without scope confirmation
cat live-hosts.txt | httpx \
  -ports 80,443,8080,8443,3000,3001,4000,4443,5000,8000,8008,8888,9090,9200,27017 \
  -silent \
  -status-code \
  -o non-standard-ports.json \
  -json

# Feed any new hosts to Phase 3 live resolution
cat non-standard-ports.json | jq -r '.url' >> live-hosts.txt
sort -u live-hosts.txt -o live-hosts.txt
```

### Phase 5 — Takeover Pre-Check + Final Merge

```bash
# Takeover detection: every live host with a CNAME gets checked
nuclei -l all-subdomains.txt -tags takeovers -silent -o takeover-candidates.txt

# Dead subdomains that resolve but return error pages: extra takeover surface
cat live-hosts.json | jq -r 'select(.status_code == 404 or .status_code == 0) | .url' > dead-live.txt
nuclei -l dead-live.txt -tags takeovers -silent >> takeover-candidates.txt
```

---

## OUTPUT SCHEMA

Feeds into a downstream analysis stage as the canonical attack surface.

```json
{
  "target": "example.com",
  "total_subdomains_found": 247,
  "live_hosts": [
    {
      "url": "https://api.example.com",
      "status_code": 200,
      "title": "API Gateway",
      "tech": ["nginx", "Node.js"],
      "ip": "1.2.3.4"
    }
  ],
  "dead_subdomains": ["legacy.example.com", "old-api.example.com"],
  "takeover_candidates": [],
  "interesting_ports": {
    "https://api.example.com:9200": 200,
    "https://internal.example.com:8080": 403
  },
  "tech_fingerprint": {
    "frameworks": ["React", "Node.js"],
    "servers": ["nginx/1.24.0"],
    "cdn": ["Cloudflare"],
    "auth": ["OAuth2"]
  },
  "overseer_routing": {
    "js_pipeline": true,
    "graphql": false,
    "grpc": false,
    "oauth_harvester": true,
    "cms_templates": false
  }
}
```

---

## SCOPE ENFORCEMENT

Before running Phase 2-5, validate every discovered subdomain against program scope:

```
FOR each subdomain in all-subdomains.txt:
  IF subdomain NOT IN program_scope AND NOT WILDCARD_MATCH:
    → Remove from list
    → Log to out-of-scope.txt
  IF subdomain in exclusions list:
    → Remove from list
    → Log to excluded.txt

NEVER probe out-of-scope assets.
When in doubt: leave it out.
```

---

## RECON COMPLETE DELIVERY FORMAT

```
ACTIVE RECON COMPLETE — {TARGET}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Sources: crt.sh + Wayback + OTX + subfinder + amass + assetfinder
Total subdomains found:  {N}
Live hosts confirmed:    {N}
Dead/NXDOMAIN:           {N}
Takeover candidates:     {N}
Non-standard ports:      {N}
Tech detected:           {tech list}

→ Passing live-hosts.json to Tier 2 overseers
→ Passing tech_fingerprint to overseer router
→ Passing takeover-candidates.txt to Web Track Overseer
→ Starting js-pipeline.md on all live hosts with JS frameworks
```
