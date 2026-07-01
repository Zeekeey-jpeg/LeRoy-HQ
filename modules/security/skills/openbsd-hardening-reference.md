---
disable-model-invocation: true
context: fork
---

# OpenBSD Hardening Reference v1.0
**Owner: cyber-operator**
**Trigger:** Load when an OpenBSD fingerprint is detected during OS/network recon
**Purpose:** Reference guide for OpenBSD-specific security model, hardening defaults, and known attack vectors. Used to calibrate what to test vs. what is locked by design.

---

## OpenBSD Fingerprinting

An OpenBSD target is identified by any of:

```
SSH banner:     SSH-2.0-OpenSSH_X.X (X.X = version shipped with OpenBSD release)
nmap OS:        "OpenBSD 6.x-7.x"
Web server:     Server: OpenBSD httpd
Mail server:    220 host ESMTP OpenSMTPD
FTP:            220---------- Welcome to Pure-FTPd [privsep] [TLS] ----------  (less common)
Custom httpd:   "Server: OpenBSD httpd" in response headers
```

### OpenBSD Version → OpenSSH Version Map
| OpenBSD | OpenSSH | Released |
|---------|---------|---------|
| 7.5 | 9.7 | April 2024 |
| 7.4 | 9.5 | Oct 2023 |
| 7.3 | 9.3 | April 2023 |
| 7.2 | 9.1 | Oct 2022 |
| 7.1 | 9.0 | April 2022 |
| 7.0 | 8.8 | Oct 2021 |
| 6.9 | 8.6 | April 2021 |
| 6.8 | 8.4 | Oct 2020 |
| 6.7 | 8.2 | Oct 2020 |
| 6.6 | 8.1 | Oct 2019 |
| 6.5 | 8.0 | April 2019 |
| 6.4 | 7.9 | Oct 2018 |

**Cross-reference SSH banner against this table to estimate OpenBSD version.**

---

## Security Model Overview

### What OpenBSD Does By Default (Locked)
These are baked into the OS and almost never misconfigured:

| Feature | Default State | Attack Impact |
|---------|--------------|---------------|
| **pledge(2)** | All base system daemons use it | Compromised process is sandboxed — limits RCE severity |
| **unveil(2)** | Filesystem access restricted per-process | Even with code exec, filesystem access is limited |
| **W^X** | Write XOR Execute enforced system-wide | No writeable+executable memory pages — shellcode harder |
| **ASLR** | Enabled + randomizes libc, stack, heap | Stack/heap exploits harder to weaponize |
| **Stack canaries** | All userland binaries | Stack overflow detection |
| **LibreSSL** | Ships instead of OpenSSL | Many OpenSSL CVEs don't apply |
| **httpd chroot** | httpd runs in /var/www chroot by default | Web shell to root is blocked by chroot |
| **smtpd privilege separation** | Multiple processes with minimal privileges | SMTP exploit impact limited |
| **PermitRootLogin no** | Default since OpenBSD 6.1 | Direct root SSH blocked |

### What OpenBSD Leaves Testable

| Surface | Default State | Test How |
|---------|--------------|---------|
| **PasswordAuthentication** | YES (enabled) | Brute force / default creds via ssh-audit-methodology.md |
| **smtpd open relay** | NO by default, but misconfigured installs | RCPT TO external test via network-attacks.md |
| **PF ruleset gaps** | Config-dependent | pfctl -sr analysis via network-attacks.md |
| **pkg_add packages** | No automatic updates | Version audit → CVE lookup via os-network-recon.md |
| **doas.conf** | Config-dependent | doas -l + privilege-escalation.md |
| **httpd directory listing** | Disabled by default, but misconfigs exist | GET request enumeration |
| **NFS exports** | Disabled by default, but deployed manually | showmount -e via network-attacks.md |
| **IPv6 with IPv4-only PF** | IPv6 often left unfiltered | IPv6 bypass test via network-attacks.md |

---

## Base System Daemons (Default OpenBSD)

| Daemon | Binary | Default Port | pledge scope | Notes |
|--------|--------|-------------|-------------|-------|
| **sshd** | /usr/sbin/sshd | 22 | stdio rpath wpath cpath inet proc exec | Most restricted — test via ssh-audit-methodology.md |
| **httpd** | /usr/sbin/httpd | 80/443 | stdio rpath inet | Minimal — no PHP, no CGI by default |
| **smtpd** | /usr/sbin/smtpd | 25 | stdio rpath cpath proc exec | Check CVE-2020-7247 for version |
| **ntpd** | /usr/sbin/ntpd | 123 | stdio rpath inet proc | Usually locked, rarely exploitable |
| **relayd** | /usr/sbin/relayd | varies | stdio rpath inet | HTTP/TCP load balancer — check for relay misconfig |
| **inetd** | /usr/sbin/inetd | varies | stdio rpath | If enabled — finger, tftp, chargen exposure |
| **ftpd** | /usr/libexec/ftpd | 21 | stdio rpath | Rarely enabled — check for anonymous access |

---

## PF Firewall — Common Misconfigurations

### Reference: Secure vs. Insecure PF Config

```
# SECURE (default-deny):
set block-policy return
block all
pass out on egress inet from (egress) to any nat-to (egress)
pass in on egress inet proto tcp to (egress) port 22

# INSECURE patterns to look for:
pass all                                    # ← NO FILTERING — critical finding
pass in on egress from any to any           # ← allows all inbound
block return in quick on egress from any    # ← MISSING: this should also block out
pass in on egress inet proto tcp to any     # ← allows all TCP inbound

# IPv6 gap (common):
# File has: pass in inet proto tcp ...
# But missing: pass in inet6 proto tcp ...
# Result: IPv6 bypass of all TCP firewall rules
```

### pfctl Commands (Need root or doas permit)
```bash
pfctl -sr        # show filter rules
pfctl -sn        # show NAT rules  
pfctl -st        # show state table (active connections + source IPs)
pfctl -ss        # connection state summary
pfctl -si        # show interface statistics
pfctl -sa        # show ALL (verbose)

# If readable by current user (sometimes misconfigured):
cat /etc/pf.conf
```

---

## OpenSMTPD Attack Surface

### Version-Based Risk

| Version | CVE | Severity | Exploitable |
|---------|-----|----------|------------|
| < 6.6.2p1 | CVE-2020-7247 | CVSS 9.8 | REMOTE RCE — MAIL FROM injection |
| < 6.6.4 | CVE-2020-8794 | CVSS 9.8 | LPE + OOB write via mda_io |
| < 6.9.0 | CVE-2021-28799 | CVSS 7.5 | Header injection |

### OpenSMTPD Delivery Configuration Audit
```
# In smtpd.conf, check for:
action "local" mda "/usr/local/bin/custom_delivery.sh"   ← writable? = LPE via CVE-2020-8794
action "relay" relay                                       ← open relay if no auth required
listen on 0.0.0.0                                          ← listens on all interfaces
table aliases file:/etc/mail/aliases                       ← check aliases for shell commands
```

---

## httpd (OpenBSD Native) Attack Surface

OpenBSD httpd is intentionally minimal — no PHP, no CGI by default. However:

```
# Common misconfigurations:
directory auto index on          ← directory listing enabled
location "/.well-known/*" { ... }← sensitive paths exposed
location "/admin/*" { ... }      ← admin panel with no auth
root "/var/www/htdocs"           ← default docroot — check for default files

# Not affected by:
# - PHP file upload (PHP not included)
# - CGI injection (disabled by default)
# - mod_rewrite exploits (no rewrite engine)

# Still test:
# - Path traversal in location blocks
# - HTTP methods (PUT, DELETE enabled?)
# - TLS version/cipher via ssl-audit or nmap
```

---

## doas Configuration Reference

```
# /etc/doas.conf syntax
permit [options] [identity] [as target] [cmd command [args ...]]

# EXPLOIT: permit nopass user1 as root
→ user1 can run any command as root without password
→ Test: doas -u root id

# EXPLOIT: permit nopass :wheel as root  
→ all wheel group members = root instantly
→ Check: id (are you in wheel?) → doas id

# EXPLOIT: permit user1 as root cmd /usr/bin/vim
→ sudo vim -c ':!/bin/bash' equivalently: doas vim then :!/bin/bash
→ GTFOBins path: doas vim → :set shell=/bin/bash → :shell

# SAFER: permit user1 as root cmd /usr/sbin/rcctl args start nginx
→ limited to exact command + args — harder to abuse
→ Check: can rcctl script be modified?
```

---

## Post-Compromise Checklist (OpenBSD)

When shell access obtained on OpenBSD box:

```
[ ] Check OS version: uname -a
[ ] Check installed packages: pkg_info -a → look for outdated versions
[ ] Check doas.conf: cat /etc/doas.conf
[ ] Check rcctl services: rcctl ls on
[ ] Check crontab: crontab -l && cat /etc/crontab
[ ] Check sshd_config: cat /etc/ssh/sshd_config
[ ] Check smtpd.conf: cat /etc/mail/smtpd.conf
[ ] Check pf.conf: cat /etc/pf.conf (might need doas)
[ ] Check open ports: netstat -an | grep LISTEN
[ ] Check pledge'd processes (note: limited to root visibility): ps aux
[ ] Check NFS exports: showmount -e localhost (if nfsd running)
[ ] Check /etc/exports: cat /etc/exports
[ ] Check world-writable dirs: find / -perm -o+w -type f 2>/dev/null | head -20
[ ] Check SUID binaries: find / -perm -u=s -type f 2>/dev/null
[ ] Cross-reference pkg_info versions against CVE database
```

---

## Key Differences From Linux (Important for Methodology Adaptation)

| Topic | Linux | OpenBSD |
|-------|-------|---------|
| **Sudo** | /etc/sudoers | doas /etc/doas.conf |
| **Package manager** | apt/yum/dnf | pkg_add / pkg_delete / pkg_info |
| **Init system** | systemd/init.d | rcctl / /etc/rc.d/ |
| **Firewall** | iptables/nftables/ufw | PF (pf.conf) |
| **OpenSSL** | OpenSSL | LibreSSL (fork — different CVE space) |
| **Shell** | bash (default) | ksh (Korn shell — OpenBSD default) |
| **Log location** | /var/log/ | /var/log/ (same) |
| **Process sandbox** | seccomp/namespaces (Linux only) | pledge/unveil (OpenBSD only) |
| **Memory exec** | Depends on distro | W^X enforced system-wide |
| **LinPEAS** | Full support | Partial — doas/rcctl checks may differ |

---

*OpenBSD Hardening Reference v1.0 | OS/Network recon reference*
