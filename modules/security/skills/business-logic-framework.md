---
name: business-logic-framework
description: "Business logic systematic testing framework for authorized security testing. Covers: STRIDE-BL framework, workflow state machine mapping, invariant violation testing (price manipulation, workflow skip, quantity abuse), IDOR horizontal access (dual account method), privilege escalation via parameter tampering, coupon/reward abuse, feature flag/subscription bypass. High-tier bounty ceiling. 12 PortSwigger labs. Converts unbounded category into systematic checklist — most underutilized technique in BB."
trigger_keywords: "business logic, logic flaw, price manipulation, workflow bypass, idor, horizontal access, privilege escalation, coupon abuse, discount abuse, payment bypass, quantity abuse, checkout bypass, parameter tampering, role tampering, subscription bypass, feature flag bypass, business logic testing, state machine, invariant"
version: 1.0
created: 2026-02-25
owner: cyber-operator
---

# Business Logic Systematic Testing Framework

## Purpose

Convert "business logic" — traditionally vague and scanner-invisible — into a structured checklist. 12 PortSwigger labs. High bounty ceiling (payment bypass, privilege escalation). These bugs are underexplored because most hunters don't have a systematic methodology.

---

## STRIDE-BL Framework

| Category | Business Logic Application | Example |
|---|---|---|
| **S**poofing | Act as another user without credentials | Change user_id in request |
| **T**ampering | Modify data you shouldn't control | Change price in checkout request |
| **R**epudiation | Perform action without attribution | Delete audit logs |
| **I**nformation Disclosure | Access data you shouldn't see | Enumerate user IDs, export unauthorized data |
| **D**enial of Service | Prevent legitimate use | Lock all accounts via failed logins |
| **E**levation of Privilege | Perform higher-role actions | Access admin functions, approve own requests |

---

## Workflow State Machine Mapping

Before testing, map the application's state machine:

```
Example: E-commerce checkout
States:     Cart → Shipping → Payment → Review → Confirmation
Invariants: Price = sum(items) + tax + shipping
            Quantity ≥ 1
            Coupon applied once
            Payment method valid
            Shipping address in supported region
```

For each invariant: **Can it be violated?**

---

## Systematic Testing Checklist

### Price & Payment Manipulation

```
□ Modify item price in checkout request
□ Change quantity to 0 or negative
□ Change currency code
□ Apply percentage discount > 100%
□ Modify tax amount / shipping cost
□ Apply same coupon multiple times (+ race condition version)
□ Use coupon from different product/category
□ Use expired coupon (replay the coupon application request)
□ Negative price items → negative total → store credit refund?
```

### Workflow Order Bypass

```
□ Skip step N → submit step N+1 directly
□ Bookmark the final confirmation URL → resubmit
□ Submit final step multiple times (duplicate order? duplicate payment?)
□ Go back to earlier step, change data → re-validate later steps?
□ Modify order after "confirmed" status
```

### IDOR — Horizontal Access (Dual Account Method)

```
Setup: Create Account A (your test account) and Account B (second test account)
Test: With Account B's session, replay every Account A request using Account A's resource IDs

For each request with an ID: Does Account B receive Account A's data?
Document: GET /api/orders/{A_order_id} with B's session → 200? → IDOR

All HTTP methods: GET (read), PUT/PATCH (modify), DELETE
All ID types: numeric, UUID, base64, hash
```

### Privilege Escalation via Parameter Tampering

```http
# Registration request with extra parameters
POST /api/register HTTP/1.1
{"email": "user@example.com", "password": "pass123", "role": "admin"}

# Profile update with role field
PUT /api/user/profile HTTP/1.1
{"name": "Test User", "role": "admin", "is_admin": true, "account_type": "premium"}

# Mass assignment: add any field not in the form, observe if it's accepted
```

### Coupon & Reward Abuse

```
□ Apply coupon to ineligible products
□ Stack multiple coupons when only one allowed
□ Create circular referral chains (A→B, B→A)
□ Refer yourself with different email addresses
□ Claim referral bonus before referred user completes required action
□ Race condition on coupon application (see race-conditions.md)
```

### Subscription/Feature Flag Bypass

```
□ The UI greys out "Export" for free users — does /api/data/export check subscription?
□ Premium-gated APIs: test with free-tier token
□ Feature flags controlled client-side? Modify JS boolean or localStorage value?

# Test direct API access as free user:
POST /api/data/export HTTP/1.1
Authorization: Bearer FREE_USER_TOKEN
{"format": "csv", "range": "all"}
```

### Numeric Boundary Testing

```
□ Minimum value: 0, -1, -2147483648
□ Maximum value: 2147483647, 9999999999
□ Decimal precision: 0.001, 0.00001
□ Scientific notation: 1e10, 1e-10
□ Special values: NaN, Infinity, -Infinity, null
□ Fractional quantities: 0.5 items
```

---

## Price Manipulation Pattern

```http
# Original checkout submit:
POST /api/checkout/submit HTTP/1.1
{"items":[{"id":"123","quantity":1}], "total": 99.99, "payment_token":"tok_abc"}

# Modified:
{"items":[{"id":"123","quantity":1}], "total": 0.01, "payment_token":"tok_abc"}
# If server uses client-provided total → purchase for $0.01
```

---

## Business Logic Bug Reporting Requirements

Unlike XSS/SQLi (generic fix), business logic reports need context-specific detail:

1. **Intended behavior** — describe the business rule being violated
2. **Violation steps** — exact reproduction steps
3. **Impact** — financial loss, data exposure, compliance issue
4. **Specific fix** — what server-side validation is missing (NOT "add input validation")

Example: "The quantity field on `/api/cart/update` accepts negative values. This allows an attacker to order -1 item at $99.99, generating a $99.99 credit applied to their account. The fix is to validate `quantity >= 1` server-side before processing the cart update."

---

## PortSwigger Coverage

12 labs across Apprentice → Expert — Business Logic Vulnerabilities category.
The most underutilized PortSwigger track because hunters lack structured methodology.

*business-logic-framework.md v1.0 | owner: cyber-operator | 2026-02-25*
