---
disable-model-invocation: true
context: fork
---

# OS/Network Recon v1.0 — Service Enumeration & Attack Surface Mapping
**Owner: cyber-operator**
**Trigger:** OS/network recon track — run when an IP, CIDR, or host with known server software is in scope
**Classification: ZERO-AUTH** — passive/low-impact enumeration
**Purpose:** Systematic service enumeration, banner grabbing, OS fingerprinting, and CVE correlation for OS/server-level attack surface mapping.

---

## When This File Activates

Auto-activate when ANY of these are true:
- Scope includes an IP address, CIDR range, or hostname with known server software
- Target's tech stack includes: `nginx`, `apache`, `sshd`, `sendmail`, `postfix`, `vsftpd`, `proftpd`, `samba`, `rdp`, `openbsd`, `freebsd`, `ubuntu`, `debian`, `centos`, `rhel`
- Bug bounty program scope explicitly lists "infrastructure" or "network devices"
- CTF box with IP provided (HTB, THM, Vulnhub)
- Any hostname resolves to a non-cloud IP (not AWS/GCP/Azure ranges)

---

## SCAN PROTOCOL: 4-Phase nmap Chain

**Zero-check-in execution. Run all phases automatically.**

### Phase 1 — Stealth Discovery (Fast)
```bash
# Fast SYN scan — top 1000 ports, OS detection off, no DNS
nmap -sS -T4 --open -n -Pn {TARGET_IP} -oN phase1.txt

# Parse open ports for Phase 2
grep "^[0-9]" phase1.txt | cut -d'/' -f1 | tr '\n' ','
```

**Output expected:** List of open ports (e.g., `22,80,443,25,21,3306`)

### Phase 2 — Full Port Sweep (If Phase 1 finds <10 ports)
```bash
# Full 65535 port scan if initial scan looks sparse
nmap -sS -T4 --open -n -Pn -p- {TARGET_IP} -oN phase2-full.txt
```

### Phase 3 — Version + OS Detection
```bash
# Service version + OS fingerprint on confirmed open ports
nmap -sV -sC -O -T3 -p {OPEN_PORTS} {TARGET_IP} -oN phase3-versions.txt

# Key flags:
#   -sV  → service version detection
#   -sC  → default NSE scripts (safe, no exploitation)
#   -O   → OS detection (requires root/sudo)
#   -T3  → normal timing (less noisy than T4 for version scan)
```

**Critical output to capture:**
- Service name + version per port
- OS detection result
- Any NSE script output (HTTP titles, SSL cert CN, SSH hostkey, etc.)

### Phase 4 — Targeted NSE Scripts
```bash
# Run targeted safe scripts per service type

# SSH
nmap --script ssh-auth-methods,ssh-hostkey,ssh2-enum-algos -p 22 {TARGET_IP}

# HTTP/HTTPS
nmap --script http-title,http-headers,http-methods,http-server-header -p 80,443,8080,8443 {TARGET_IP}

# SMTP
nmap --script smtp-commands,smtp-open-relay,smtp-enum-users -p 25,465,587 {TARGET_IP}

# FTP
nmap --script ftp-anon,ftp-syst,ftp-vsftpd-backdoor -p 21 {TARGET_IP}

# SMB (if Windows target)
nmap --script smb-os-discovery,smb-security-mode,smb-vuln-ms17-010 -p 445,139 {TARGET_IP}

# MySQL/PostgreSQL
nmap --script mysql-info,mysql-empty-password,pgsql-brute -p 3306,5432 {TARGET_IP}

# RDP
nmap --script rdp-enum-encryption,rdp-vuln-ms12-020 -p 3389 {TARGET_IP}
```

---

## Banner Grabbing Protocol

### Netcat Banner Grab (per service)
```bash
# Generic banner grab
nc -nv -w3 {TARGET_IP} {PORT}

# HTTP banner
curl -sv --max-time 5 http://{TARGET_IP}/ 2>&1 | head -30

# SMTP banner
nc -nv -w5 {TARGET_IP} 25
# Expected: 220 mail.target.com ESMTP Postfix (Ubuntu)

# FTP banner
nc -nv -w5 {TARGET_IP} 21
# Expected: 220 (vsFTPd 3.0.3)

# SSH banner
nc -nv -w5 {TARGET_IP} 22
# Expected: SSH-2.0-OpenSSH_8.4p1 Debian-5
```

### OpenBSD-Specific Banner Patterns
```
SSH-2.0-OpenSSH_7.9       → OpenBSD 6.4 (2018) — check CVE-2018-15919
SSH-2.0-OpenSSH_8.0       → OpenBSD 6.6 (2019) — check CVE-2019-16905
SSH-2.0-OpenSSH_8.1       → OpenBSD 6.7 (2020)
SSH-2.0-OpenSSH_8.4       → OpenBSD 6.9 (2021)
SSH-2.0-OpenSSH_9.0       → OpenBSD 7.1 (2022)
SSH-2.0-OpenSSH_9.3       → OpenBSD 7.3 (2023)
SSH-2.0-OpenSSH_9.6       → OpenBSD 7.4 (2024) — current stable
httpd/7.x                  → OpenBSD httpd (native)
```

---

## Service → CVE Correlation Workflow

For each detected service version, execute:

```
STEP 1: WebSearch query:
  "{service_name} {version} CVE site:nvd.nist.gov"
  Example: "OpenSSH 7.9 CVE site:nvd.nist.gov"

STEP 2: WebSearch query:
  "{service_name} {version} exploit 2024 OR 2025"
  Example: "vsftpd 3.0.3 exploit 2025"

STEP 3: Check ExploitDB:
  WebFetch: https://www.exploit-db.com/search?q={service}+{version}

STEP 4: Classify finding:
  - CVE with CVSS ≥ 7.0 + public POC → HIGH PRIORITY → report to findings
  - CVE with CVSS ≥ 7.0, no POC → MEDIUM → add to opportunities
  - EOL/unsupported version → LOW → flag in report
  - No CVE → mark CLEAR, continue
```

---

## Service Classification Table

After Phase 3 scan, classify each open port:

| Port | Service | Attack Class | Technique File |
|------|---------|--------------|---------------|
| 21 | FTP | Anonymous access, bounce attack | (this file) |
| 22 | SSH | Version CVE, cipher audit, brute | `ssh-audit-methodology.md` |
| 23 | Telnet | Cleartext credentials, MitM | HIGH PRIORITY — cleartext protocol |
| 25/465/587 | SMTP | Open relay, user enum, STARTTLS | `network-attacks.md` |
| 53 | DNS | Zone transfer, cache poison | `network-attacks.md` |
| 80/443/8080 | HTTP/S | Web track → web overseers | web-track vectors |
| 111/2049 | RPC/NFS | Mount enumeration, export abuse | `network-attacks.md` |
| 139/445 | SMB | MS17-010, share enum, null session | `network-attacks.md` |
| 3306 | MySQL | Empty password, auth bypass | (this file + version CVE) |
| 3389 | RDP | MS12-020, brute, NLA bypass | `network-attacks.md` |
| 4444/5555 | Unusual | Default backdoor ports | IMMEDIATE — document + verify |
| 5432 | PostgreSQL | Auth bypass, version CVE | (this file) |
| 6379 | Redis | No-auth access, RCE via config | HIGH PRIORITY — auth-free access |
| 8443/8080 | Alt-HTTP | Admin panels, default creds | `arsenal-index.md` → default creds |
| 9200/9300 | Elasticsearch | Unauthenticated access | HIGH PRIORITY — data exposure |
| 27017 | MongoDB | No-auth access | HIGH PRIORITY — data exposure |

---

## FTP Enumeration Protocol

```bash
# Step 1: Test anonymous login
ftp {TARGET_IP}
# Username: anonymous
# Password: (blank or any@email.com)
# If login succeeds → document CRITICAL (anonymous access)

# Step 2: List directory
ftp> ls -la
ftp> dir

# Step 3: Check for readable/writable dirs
ftp> cd /pub
ftp> put test.txt     # test write access

# Step 4: Get interesting files
ftp> get /etc/passwd  # if misconfigured
ftp> mget *           # download all accessible files
```

**Evidence standard:** Screenshot/output of `ls -la` + any sensitive file retrieved

---

## Redis/Elasticsearch/MongoDB No-Auth Check

```bash
# Redis — unauthenticated check
nc -nv -w3 {TARGET_IP} 6379
# Type: PING
# Expected if vulnerable: +PONG

# If PONG received → execute:
redis-cli -h {TARGET_IP} info server    # get version + config
redis-cli -h {TARGET_IP} config get *   # dump full config
redis-cli -h {TARGET_IP} keys *         # list all keys (evidence of data access)

# Elasticsearch — unauthenticated check
curl -sv http://{TARGET_IP}:9200/
# If returns JSON cluster info → CRITICAL (unauthenticated access)
curl http://{TARGET_IP}:9200/_cat/indices?v   # list all indices
curl http://{TARGET_IP}:9200/_cat/nodes?v     # list nodes

# MongoDB — unauthenticated check
nc -nv -w3 {TARGET_IP} 27017
# Or: mongosh --host {TARGET_IP} --norc
# > show dbs     ← if works without creds → CRITICAL
```

---

## OpenBSD-Specific Enumeration

When OpenBSD fingerprint detected (via SSH banner or nmap OS detection):

```bash
# 1. Enumerate native daemons
nmap -sV -p 22,25,80,443,110,143 {TARGET_IP}

# 2. Check httpd (OpenBSD native web server)
curl -sv http://{TARGET_IP}/
# Look for: "Server: OpenBSD httpd" header
# OpenBSD httpd is minimal — check for directory listing, version disclosure

# 3. Check smtpd (OpenBSD native mail server)
nc -nv -w5 {TARGET_IP} 25
# Look for: "220 hostname.domain ESMTP OpenSMTPD"
# OpenSMTPD CVE history: CVE-2020-7247 (RCE), CVE-2020-8794 (LPE)

# 4. Check for pf (Packet Filter) fingerprint
# nmap OS detection often shows: "OpenBSD 6.x-7.x"
# Cross-reference with SSH banner for version confirmation

# 5. Check pkg_add-managed service versions
# (If shell access obtained) → pkg_info -a | grep -i {service}
```

**Key OpenBSD CVEs to check (all daemons):**

| CVE | Daemon | CVSS | Description |
|-----|--------|------|-------------|
| CVE-2020-7247 | OpenSMTPD | 9.8 | Remote code execution via mail from/rcpt parsing |
| CVE-2020-8794 | OpenSMTPD | 9.8 | LPE + OOB write via mda_io |
| CVE-2019-16905 | OpenSSH | 7.8 | Memory corruption in xauth data |
| CVE-2018-15919 | OpenSSH | 5.3 | Username enumeration via auth timing |
| CVE-2023-38408 | OpenSSH | 9.8 | Remote code execution in ssh-agent (Terrapin) |
| CVE-2024-6387 | OpenSSH | 8.1 | regreSSHion race condition RCE (OpenSSH < 9.8) |

---

## Output Schema

Each sub-agent returns:
```json
{
  "vector": "FTP Anonymous Access",
  "target": "ftp://192.168.1.50:21",
  "service": "vsftpd 3.0.3",
  "technique_file": "os-network-recon.md",
  "status": "CONFIRMED | NOT_VULNERABLE | NEEDS_AUTH | ERROR",
  "POC_confirmed": true,
  "confidence": 0.90,
  "evidence": "Connected as anonymous@, listed /pub directory, retrieved /pub/readme.txt",
  "payout_ceiling": 5000,
  "auth_required": false,
  "escalation": "MEDIUM",
  "CVE": "N/A",
  "next_vector": "privilege-escalation.md — check writable dirs"
}
```

---

## Recon Delivery Format

```
OS/NETWORK RECON COMPLETE — [Target]
Open ports: [N] ([list])
OS fingerprint: [result]
Services detected:
  - Port 22: OpenSSH 9.0 (OpenBSD 7.1) → ssh-audit-methodology.md
  - Port 25: OpenSMTPD 6.8.0 → CVE-2020-7247 CONFIRMED (CVSS 9.8)
  - Port 80: OpenBSD httpd → directory listing ENABLED
  - Port 21: FTP CLOSED
High-priority findings: [N]
CVEs confirmed: [list]
Next: Handing SSH to ssh-audit-methodology.md, escalating SMTP CVE to findings
```

---

## Whitehat Constraints

```
SCAN LIMITS:
  - Max scan rate: -T3 (normal) for version scans — do NOT use T5 (insane)
  - Max 3 banner grab attempts per service
  - No SYN flood, no UDP flood, no DoS of any kind
  - Stop immediately if target shows signs of rate limiting (connection refused spike)
  - Test on staging/lab if staging environment detected
```

---

*OS/Network Recon v1.0 | Zero-Auth Track*
