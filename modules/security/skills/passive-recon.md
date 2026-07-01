---
user-invocable: false
context: fork
agent: Explore
---

# Passive Reconnaissance

**Owner:** recon-agent
**Purpose:** OSINT source library, crt.sh patterns, Wayback/GitHub dork library, recon report template

**ABSOLUTE RULE:** No active packets. Public sources only. No account creation required.

> ⚠️ **ROUTING NOTE (v2.0 — 2026-04-11):**
> For full bug bounty sweeps: load **`active-recon.md`** instead.
> active-recon.md runs subfinder + amass + httpx + takeover detection — far more comprehensive.
> This file = OSINT-only contexts where ZERO active packets are permitted (CTI, threat intel, pre-auth assessment without permission). If in doubt: use active-recon.md.

---

## OSINT Source Library

### Certificate Transparency (crt.sh)
**What:** SSL certificates issued for domains — reveals subdomains.
**Access:** `https://crt.sh/?q=%25.{domain}&output=json`
**Yields:** Subdomain list from certificate registrations

**Query Pattern:**
```
WebFetch: https://crt.sh/?q=%25.example.com&output=json
Extract: common_name, name_value fields
Filter: Remove wildcards (*.), deduplicate
```

### Wayback Machine (Archive.org)
**What:** Historical snapshots of web pages — reveals old endpoints, configs, paths.
**Access:** `https://web.archive.org/cdx/search/cdx?url=*.{domain}/*&output=json&fl=original&collapse=urlkey`
**Yields:** Historical URL list for the domain

**Interesting Patterns to Look For:**
- `/api/v1/` or `/api/v2/` → old API versions
- `/admin/` or `/internal/` → admin panels
- `/.git/` → exposed git repo
- `/backup/` or `/old/` → backup files
- `/phpinfo.php` → exposed PHP info

### GitHub Dork Library
**Access:** WebSearch with targeted queries

| Dork Query | Finds |
|------------|-------|
| `site:github.com {domain} password` | Leaked passwords |
| `site:github.com {domain} api_key` | API keys |
| `site:github.com {domain} secret` | Secrets |
| `site:github.com {domain} aws_access` | AWS credentials |
| `site:github.com {domain} config` | Configuration files |
| `site:github.com {company} .env` | Environment files |
| `site:github.com {domain} token` | Auth tokens |
| `site:github.com {domain} private_key` | Private keys |

### Google Dork Library

| Dork Query | Finds |
|------------|-------|
| `site:{domain} filetype:pdf` | Exposed PDFs |
| `site:{domain} filetype:xls OR filetype:xlsx` | Exposed spreadsheets |
| `site:{domain} inurl:login` | Login pages |
| `site:{domain} inurl:admin` | Admin pages |
| `site:{domain} inurl:api` | API endpoints |
| `site:{domain} intext:"sql syntax"` | SQL errors |
| `site:{domain} intext:"error" intext:"warning"` | Error messages |
| `site:{domain} intitle:"index of"` | Directory listings |
| `site:{domain} ext:php inurl:id=` | Potential SQLi params |
| `site:{domain} filetype:log` | Log files |

### Shodan (Public Search)
**Access:** WebSearch `shodan.io {domain}` or `shodan.io {IP range}`
**Note:** Only use publicly indexed results, not authenticated Shodan API.
**Yields:** Known open ports, service banners, historical scan data

### LinkedIn (Tech Stack Discovery)
**Access:** WebSearch `site:linkedin.com jobs {company} {technology}`
**Yields:** Tech stack from job postings (AWS, React, PostgreSQL, etc.)
**Also check:** Company's own career page (no auth required)

### DNS History
**Access:** WebSearch `{domain} DNS history site:securitytrails.com` (public pages only)
**Yields:** Historical A records, old infrastructure

---

## Recon Workflow

```
Step 1: SCOPE CHECK
→ Read BB program rules
→ List in-scope domains/IPs
→ Note explicit exclusions

Step 2: SUBDOMAIN DISCOVERY
→ crt.sh query for each scope domain
→ Compile unique subdomain list
→ Remove wildcards, sort by likely interest

Step 3: WAYBACK SCAN
→ Query Wayback CDX for interesting paths
→ Note historical endpoints no longer visible
→ Flag /admin, /api, /backup, /.git paths

Step 4: GITHUB DORKS
→ Run 3-5 most relevant dorks
→ Check first page of results only
→ Note any leaked credentials (report to BB, don't exploit)

Step 5: TECH FINGERPRINT
→ LinkedIn job postings for tech stack
→ Error messages in Wayback pages
→ JavaScript library names in archived source

Step 6: COMPILE REPORT
→ Use report template below
→ Include source for every finding
→ List recommended active testing targets
→ Include scope confirmation reminder
```

---

## Recon Report Template

```markdown
# Passive Recon Report: {Target}
**Date:** {date}
**Scope Reference:** {BB program URL}
**Status:** Passive Only — No Active Packets Sent

## Scope Summary
In-scope: {domains/IP ranges}
Excluded: {explicitly excluded items}

## Subdomain Discovery (crt.sh)
Total found: {N} unique subdomains

| Subdomain | First Seen | Notes |
|-----------|-----------|-------|
| app.{domain} | 2025-11 | Likely main app |
| api.{domain} | 2025-09 | API endpoint |
| staging.{domain} | 2024-03 | May be in scope - verify |

## Wayback Machine Findings
Historical endpoints of interest:

| URL | Last Archived | Risk |
|-----|--------------|------|
| /api/v1/users | 2024-08 | Old API, may still exist |
| /admin/login | 2023-05 | Historical admin path |
| /.git/config | 2022-11 | Exposed git repo (check if still live) |

## GitHub Dork Findings

| Query | Results | Action |
|-------|---------|--------|
| {domain} api_key | 2 repos | Review for active keys |
| {domain} config | 5 repos | Review for sensitive config |

## Technology Fingerprint (Public Sources Only)
- **Frontend:** {inferred}
- **Backend:** {inferred}
- **Cloud:** {inferred}
- **Auth:** {inferred}
- **Source:** LinkedIn job postings (link), Wayback headers (link)

## Recommended Active Testing Targets
*Confirm in-scope before any active testing:*

| Target | Why Interesting | Priority |
|--------|----------------|---------|
| api.{domain} | Old API version in Wayback, may have IDOR | High |
| {domain}/admin | Historical admin path | Medium |

## Scope Confirmation Required
⚠️ Before beginning active testing:
1. Confirm all targets above are in current BB scope
2. Check program for recent scope changes
3. Read program-specific rules (rate limits, disclosure requirements)
```

---

## Recon Report Delivery

After completing report:
1. Store in your engagement notes, e.g. `recon/{program}/recon-{date}.md`
2. Summarize key targets for the active-testing handoff
3. Note any findings that suggest out-of-scope status

---

*Passive Recon v1.0 | Public sources only*
