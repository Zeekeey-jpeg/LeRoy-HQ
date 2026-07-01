# Nuclei Automation Workflow Skill

**Trigger:** Nuclei, automated scanning, first-pass automation, template scan, CVE detection, subdomain scan
**Priority:** P0 — Force multiplier on ALL programs
**Use when:** Starting any new program OR after recon delivers subdomain list

---

## What Nuclei Does For Us

Nuclei runs 9,000+ community templates in ~60 seconds, catching:
- Known CVEs (exposed admin panels, version disclosures, known-vuln endpoints)
- Misconfigurations (S3, GCP, open redirects, directory listing)
- Takeover candidates (dangling CNAME fingerprints)
- Exposed files (`.git`, `.env`, `phpinfo`, backup files)
- Default credentials (admin/admin, login panels)

**In bug bounty: always run Nuclei before manual testing. It catches what scanners miss.**

> **Custom templates:** After manual confirmation of any finding, generate a custom Nuclei template to scan the full scope automatically. See **Workflow 4** below and `nuclei-template-generator.md`.

---

## Installation & Setup

```bash
# Install
go install -v github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest

# Update templates (run weekly)
nuclei -update-templates

# Verify
nuclei -version
```

---

## Core Workflows

### Workflow 1 — Single Target First Pass (BB-Safe)
```bash
# Safe mode: rate-limited, no intrusive checks, no fuzzing
nuclei -u https://target.com \
  -tags "safe,exposure,misconfiguration,takeovers,config" \
  -rate-limit 10 \
  -timeout 10 \
  -o nuclei-results.txt

# Review results immediately — any Critical/High = file now
```

### Workflow 2 — Subdomain List Scan (Post-Recon)
```bash
# v2.0: Input comes from active-recon.md output automatically (not manual subdomains.txt)
# active-recon.md writes: all-subdomains.txt + live-hosts.txt
# Use live-hosts.txt for faster results (already confirmed live)

# Preferred: scan live hosts (pre-confirmed by httpx — faster, fewer false positives)
nuclei -l live-hosts.txt \
  -tags "takeovers,exposure,misconfiguration,cves" \
  -rate-limit 20 \
  -bulk-size 25 \
  -concurrency 10 \
  -o nuclei-live-results.txt

# Also scan all subdomains for takeovers (includes dead subdomains — important for takeovers)
nuclei -l all-subdomains.txt \
  -tags "takeovers" \
  -rate-limit 20 \
  -bulk-size 50 \
  -o nuclei-takeover-results.txt

# Filter by severity
cat nuclei-live-results.txt | grep "\[critical\]\|\[high\]"
cat nuclei-takeover-results.txt
```

### Workflow 3 — Targeted CVE Check
```bash
# Check for specific known CVEs on a target
nuclei -u https://target.com -tags "cves" -severity "critical,high"

# Check for a specific CVE
nuclei -u https://target.com -id CVE-2021-44228   # Log4Shell
nuclei -u https://target.com -id CVE-2022-26134   # Confluence RCE
```

### Workflow 4 — Takeover Detection
```bash
# Run ONLY takeover templates (fast, safe)
nuclei -l subdomains.txt \
  -tags "takeovers" \
  -rate-limit 50 \
  -o takeover-candidates.txt
```

### Workflow 5 — Exposure Hunt
```bash
# Find exposed files, panels, debug endpoints
nuclei -u https://target.com \
  -tags "exposure,config,panel,login" \
  -severity "critical,high,medium" \
  -o exposure-results.txt
```

---

## High-Value Template Categories

| Category Tag | What It Finds | BB Value |
|-------------|---------------|----------|
| `takeovers` | Dangling CNAME → subdomain takeover | High |
| `exposure` | `.git`, `.env`, backup files, source | High-Critical |
| `misconfiguration` | Open redirects, CORS, weak headers | Medium-High |
| `cves` | Known CVE exploits | Critical |
| `panel` | Exposed admin panels | Medium-High |
| `login` | Default credentials | High |
| `config` | phpinfo, debug pages, config exposure | Medium |
| `network` | Open ports, protocols | Low-Medium |

---

## Custom Template (Quick Write)

```yaml
id: target-custom-endpoint-check
info:
  name: Target Custom Endpoint Check
  author: researcher
  severity: medium
  description: Check for exposed internal endpoint

requests:
  - method: GET
    path:
      - "{{BaseURL}}/internal/admin"
      - "{{BaseURL}}/api/v1/admin/users"
    matchers:
      - type: status
        status: [200]
      - type: word
        words: ["admin", "dashboard", "users"]
        condition: or
```

```bash
# Run custom template
nuclei -u https://target.com -t ./custom-templates/target-custom.yaml
```

---

## Integration with Whitehat Protocol

**In whitehat-protocol Phase 5 (Reconnaissance → Scanning):**
1. After subdomain enumeration → feed list to `nuclei -l subdomains.txt -tags takeovers`
2. After target confirmed → `nuclei -u TARGET -tags "safe,exposure,misconfiguration"`
3. Any Critical/High result → treat as primary finding → document + escalate
4. Any takeover candidate → switch to `Cyber-Subdomain-Takeover` methodology immediately

**Output integration:**
```bash
# Parse JSON output for severity filtering
nuclei -u https://target.com -json | jq '.[] | select(.info.severity=="critical")'

# Feed to report generator
nuclei -u https://target.com -o results.txt -severity "critical,high,medium"
```

---

## Bug Bounty Safety Rules

1. **Always use `-rate-limit`** — never hammer a target
2. **Use `-tags safe`** first — avoids intrusive/destructive templates
3. **Avoid `-tags fuzzing`** on production BB targets
4. **Document the Nuclei version and template date** in your report
5. **Verify every Nuclei finding manually** before filing — false positives exist

---

## Quick Wins to File After Nuclei

| Finding | Nuclei Template Tag | Typical Severity | File? |
|---------|-------------------|-----------------|-------|
| Subdomain takeover | takeovers | High | YES (immediately) |
| Exposed `.env` file | exposure | Critical | YES |
| Exposed `.git` directory | exposure | High | YES (if source readable) |
| phpinfo() exposed | exposure | Medium | Only if secrets visible |
| Admin panel no auth | panel | High | YES |
| Default creds working | login | Critical | YES |
| Open redirect | misconfiguration | Low-Medium | Only if chained |

---

---

## Advanced Templates (KB Part 2)

### Time-Based SQLi Detection Template
```yaml
id: custom-sqli-time-based
info:
  name: Time-Based SQL Injection
  severity: critical
  tags: sqli,custom
requests:
  - method: GET
    path:
      - "{{BaseURL}}/api/user?id=1' AND SLEEP(5)--"
    matchers:
      - type: dsl
        dsl:
          - "duration >= 5"
```

### SSTI Jinja2 Detection Template
```yaml
id: custom-ssti-jinja2
info:
  name: SSTI Jinja2 Detection
  severity: critical
  tags: ssti,custom
requests:
  - method: GET
    path:
      - "{{BaseURL}}/?name={{7*7}}"
    matchers:
      - type: word
        words:
          - "49"
```

### OOB XXE with Interactsh Template
```yaml
id: custom-oob-xxe
info:
  name: OOB XXE Detection
  severity: critical
requests:
  - raw:
      - |
        POST /api/xml HTTP/1.1
        Host: {{Hostname}}
        Content-Type: application/xml

        <?xml version="1.0"?><!DOCTYPE foo [<!ENTITY xxe SYSTEM "http://{{interactsh-url}}">]><foo>&xxe;</foo>
    matchers:
      - type: word
        part: interactsh_protocol
        words:
          - "http"
```

**Use case:** Run this OOB-XXE template against an entire subdomain list — any DNS pingback = confirmed XXE (Geek Freak research pattern: discovered wildfire subdomain XXEs this way).

### Full Pipeline Command (Subfinder + HTTPX + Nuclei)
```bash
# Complete recon-to-scan pipeline:
subfinder -d target.com -silent | \
  httpx -silent | \
  nuclei -t cves/,misconfigurations/ -o findings.json -je

# -je = JSON export (jq-parseable)
# Filter critical findings:
cat findings.json | jq '.[] | select(.info.severity=="critical")'
```

### CI/CD Integration (GitHub Actions)
```yaml
- name: Run Nuclei Security Scan
  uses: projectdiscovery/nuclei-action@main
  with:
    target: https://target.com
    flags: "-t cves/ -s critical,high"
```

### JSON Output for Severity Filtering
```bash
# JSON mode for programmatic filtering:
nuclei -u https://target.com -json | jq '.[] | select(.info.severity=="critical")'

# All critical + high with template ID:
nuclei -l subdomains.txt -json -o results.json
cat results.json | jq -r '[.info.severity, .templateID, .matched] | @tsv' | sort
```

### Burp Integration
```bash
# 1. Export scope from Burp → feed directly to nuclei -l
# 2. Use Nuclei to verify Burp-identified issues at scale across all subdomains
# 3. Nuclei finds it → Burp confirms it manually → file the report
```

## References

- Nuclei docs: https://docs.projectdiscovery.io/tools/nuclei
- Template library: https://github.com/projectdiscovery/nuclei-templates
- Community templates: https://github.com/projectdiscovery/nuclei-templates/tree/main/http

---

*Enhanced by KB Part 2 ingestion 2026-03-04*

*Skill: nuclei-workflow | Created 2026-03-04 | P0 priority force multiplier | Integrates with whitehat-protocol Phase 5*
