---
name: nuclei-template-generator
description: "Generate custom Nuclei YAML templates from confirmed findings or Burp request exports. Use when: a manual finding needs automated re-testing across full scope, replicating a finding on similar endpoints, sharing a finding as a reproducible template. Covers: SSRF, IDOR, XSS, open redirect, exposed file patterns. Integrates with nuclei-workflow.md Workflow 4."
version: 1.0
created: 2026-04-11
owner: cyber-operator
trigger_keywords: "nuclei template, custom nuclei, nuclei yaml, generate template, nuclei custom, nuclei finding, nuclei from burp"
---

# Nuclei Custom Template Generator

## Purpose

Community Nuclei templates cover known CVEs and misconfigs. Custom templates cover YOUR program-specific findings — unique endpoints, parameter names, application logic. A custom template lets you scan 100+ subdomains for the same vulnerability that you found manually on one endpoint, multiplying payout potential.

---

## Workflow 4 — Custom Template from Confirmed Finding

**When to use:** After manual confirmation of any repeatable finding (SSRF, XSS, open redirect, exposed file, IDOR pattern).

**Input needed:**
1. The vulnerable HTTP request (copy from Burp > Copy as cURL or use Burp Intruder exported request)
2. The vulnerability class
3. The expected response that proves exploitation

---

## Template Skeleton

All custom templates share this structure:

```yaml
id: custom-{program-name}-{finding-class}-{YYYYMMDD}

info:
  name: "{Program} — {Finding Description}"
  author: your-h1-handle
  severity: {critical|high|medium|low|info}
  description: "{One sentence: what the vuln is and what an attacker can do}"
  tags: custom,{class},{program-name}
  cvss-metrics: CVSS:4.0/{vector-string-from-cvss4-calculator.md}
  cvss-score: {score}
  cwe-id: CWE-{number}

http:
  - method: {GET|POST|PUT|DELETE}
    path:
      - "{{BaseURL}}/path/to/endpoint"
    
    headers:
      Content-Type: application/json
      # Add auth headers if needed:
      # Authorization: "Bearer {{token}}"
    
    body: |
      {request body if POST/PUT}
    
    matchers-condition: and
    matchers:
      - type: status
        status:
          - 200
      
      - type: {word|regex|dsl}
        {words|regex|dsl}:
          - "{string that proves exploitation}"
```

---

## Pre-Built Templates by Vulnerability Class

### Template 1 — SSRF (Interactsh OOB)

```yaml
id: custom-ssrf-oob-{{program}}-{{date}}

info:
  name: "SSRF — OOB Callback via {{parameter}}"
  author: your-h1-handle
  severity: high
  description: "Server fetches attacker-controlled URL via {{parameter}} parameter, confirmed via Interactsh DNS/HTTP callback"
  tags: custom,ssrf,oob
  cvss-metrics: CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:H/VI:N/VA:N/SC:N/SI:N/SA:N
  cvss-score: 8.0

http:
  - method: GET
    path:
      - "{{BaseURL}}/api/endpoint?{{parameter}}=http://{{interactsh-url}}/ssrf-probe"
    
    matchers:
      - type: word
        part: interactsh_protocol
        words:
          - "http"
        # Nuclei automatically handles Interactsh correlation when using {{interactsh-url}}
```

**Usage:**
```bash
nuclei -t custom/ssrf-oob.yaml -u https://target.com -interactsh-url your-token.oast.pro
```

### Template 2 — IDOR (Response Body Match)

```yaml
id: custom-idor-{{resource}}-{{program}}-{{date}}

info:
  name: "IDOR — {{resource}} accessible by other user"
  author: your-h1-handle
  severity: high
  description: "Authenticated user can access {{resource}} belonging to victim by changing {{id_parameter}}"
  tags: custom,idor,authorization
  cvss-metrics: CVSS:4.0/AV:N/AC:L/AT:N/PR:L/UI:N/VC:H/VI:N/VA:N/SC:N/SI:N/SA:N
  cvss-score: 7.1

http:
  - method: GET
    path:
      - "{{BaseURL}}/api/{{resource}}/{{victim_id}}"
    
    headers:
      Authorization: "Bearer {{attacker_token}}"
      # Replace {{attacker_token}} with your test account token
    
    matchers-condition: and
    matchers:
      - type: status
        status:
          - 200
      
      - type: word
        words:
          - "{{victim_email_fragment}}"
          # String only present in victim's data — proves access
        part: body
```

### Template 3 — Reflected XSS

```yaml
id: custom-rxss-{{param}}-{{program}}-{{date}}

info:
  name: "Reflected XSS — {{parameter}} parameter"
  author: your-h1-handle
  severity: medium
  description: "Unsanitized {{parameter}} reflects into HTML response, enabling XSS execution"
  tags: custom,xss,reflected
  cvss-metrics: CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:A/VC:L/VI:L/VA:N/SC:N/SI:N/SA:N
  cvss-score: 5.3

http:
  - method: GET
    path:
      - '{{BaseURL}}/search?{{parameter}}="><script>alert(document.domain)</script>'
    
    matchers-condition: and
    matchers:
      - type: status
        status:
          - 200
      
      - type: word
        words:
          - '"><script>alert(document.domain)</script>'
        part: body
```

### Template 4 — Open Redirect

```yaml
id: custom-open-redirect-{{program}}-{{date}}

info:
  name: "Open Redirect — {{parameter}} parameter"
  author: your-h1-handle
  severity: medium
  description: "{{parameter}} parameter allows redirect to external domains without validation"
  tags: custom,redirect,open-redirect
  cvss-metrics: CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:A/VC:N/VI:N/VA:N/SC:L/SI:N/SA:N
  cvss-score: 4.8

http:
  - method: GET
    path:
      - "{{BaseURL}}/redirect?{{parameter}}=https://evil.com"
    
    redirects: false
    max-redirects: 0
    
    matchers-condition: and
    matchers:
      - type: status
        status:
          - 301
          - 302
          - 303
          - 307
          - 308
      
      - type: word
        words:
          - "https://evil.com"
        part: header
```

### Template 5 — Exposed Sensitive File

```yaml
id: custom-exposed-{{filetype}}-{{program}}-{{date}}

info:
  name: "Exposed {{filetype}} — Sensitive File"
  author: your-h1-handle
  severity: high
  description: "{{filetype}} file accessible without authentication, containing {{content_type}}"
  tags: custom,exposure,misconfiguration

http:
  - method: GET
    path:
      - "{{BaseURL}}/{{file_path}}"
    
    matchers-condition: and
    matchers:
      - type: status
        status:
          - 200
      
      - type: word
        words:
          - "{{distinctive_content_string}}"
        part: body
      
      - type: word
        negative: true
        words:
          - "404"
          - "Not Found"
          - "Access Denied"
        part: body
```

---

## Filling in the Variables

| Variable | How to Find It |
|----------|----------------|
| `{{BaseURL}}` | Nuclei replaces this with each target URL automatically |
| `{{parameter}}` | The vulnerable parameter name from your manual finding |
| `{{interactsh-url}}` | Nuclei replaces with your Interactsh token (use `-interactsh-url` flag) |
| `{{victim_id}}` | The ID of victim account's resource (use your second test account) |
| `{{attacker_token}}` | Your test account's auth token — hardcode for initial test, generalize for scope-wide |
| `{{distinctive_content_string}}` | A string unique to exploitation (not present in 404 pages) |

---

## Output Path Convention

```
Save templates to:
~/nuclei-templates/custom/{program-name}/{finding-id}.yaml

Example:
~/nuclei-templates/custom/acme-corp/ssrf-fetch-url-2026-04-11.yaml
```

---

## Validation Before Running

Always validate template syntax before running:
```bash
nuclei -t custom/{program}/{template}.yaml -validate
# Must show: [INF] All templates validated successfully
```

---

## Running Against Full Scope

```bash
# Single target
nuclei -t custom/{program}/{template}.yaml -u https://target.com -v

# Full subdomain list (use after recon delivers subdomains.txt)
nuclei -t custom/{program}/{template}.yaml -l subdomains.txt -rate-limit 5 -v

# Multiple custom templates at once
nuclei -t custom/{program}/ -l subdomains.txt -rate-limit 5 -o custom-scan-results.txt
```

---

*Nuclei Template Generator v1.0 | Whitehat System | Custom Finding Automation*
