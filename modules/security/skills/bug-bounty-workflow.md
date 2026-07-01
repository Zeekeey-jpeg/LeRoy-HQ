# Bug Bounty Workflow

**Owner:** cyber-operator
**Purpose:** HackerOne scope reading → CVSS scoring → structured report format

**SCOPE:** HackerOne in-scope assets only. Always verify scope before testing.

---

## CARDINAL RULE — NO REPORT WITHOUT CONFIRMED DISCOVERY

**ABSOLUTE RULE:** Never write or submit a bug bounty report unless you have:
1. A confirmed, reproducible vulnerability with proof of concept
2. Evidence the target is in scope (verified against current program policy)
3. Confirmed the issue is not on the exclusion list
4. A working PoC that a triager can reproduce independently

**WHY THIS MATTERS:** Submitting unconfirmed, speculative, or informational findings damages credibility. Programs track report quality. A low signal-to-noise ratio gets you deprioritized by triagers on future reports. **One quality report > ten low-quality reports.**

**Binary reporting standard:**
- ✅ 100% — Confirmed finding with PoC → proceed to report format below
- ❌ 0% — No confirmed finding → document what was tested, log null result, move on

**Never report:**
- Speculative vulnerabilities without PoC
- Theoretical attack chains not confirmed to work
- Known-excluded issues (see technical exclusions per program)
- Informational findings that require significant additional work to weaponize
- Self-XSS, clickjacking on non-sensitive pages, header issues

---

## Pre-Engagement Checklist

Before touching any target:
- [ ] Read the full program policy page
- [ ] Note in-scope domains/IPs explicitly
- [ ] Note explicitly out-of-scope items
- [ ] Note safe harbor language (is it explicit?)
- [ ] Note disclosure requirements (coordinated? public after fix?)
- [ ] Note scope-specific rules (rate limiting, account creation OK?, etc.)
- [ ] Estimated payout ranges by severity

---

## Scope Reading Protocol

### What to Extract from BB Program Page

```markdown
## Program: {Company Name}
**URL:** {HackerOne program URL}
**Last Updated:** {date}

### In-Scope
| Target | Type | Notes |
|--------|------|-------|
| *.example.com | Wildcard domain | All subdomains |
| api.example.com | Domain | API only |
| Android app | Mobile | Play Store only |

### Out-of-Scope
| Item | Reason |
|------|--------|
| staging.example.com | Explicit exclusion |
| Third-party plugins | Not owned |

### Rules
- No automated scanning (rate limit: manual only)
- No social engineering
- Stop testing on vulnerability confirmation
- Report through HackerOne only

### Rewards
| Severity | Range |
|----------|-------|
| Critical | $5,000 - $15,000 |
| High | $1,000 - $5,000 |
| Medium | $200 - $1,000 |
| Low | $50 - $200 |
```

---

## Target Priority Table (MANDATORY — Every Program)

After reading scope, generate this table **before any testing begins**. Always unauthenticated surface only. Sort by **Success %** descending — that column drives all decisions.

```markdown
## Target Priority Table — {Program Name}
**Rule:** No login required for every row. Sorted by Success % (highest ROI first).

| # | Target / Test | Tier | Max Bounty | Success % | No Login | Est. Time | What We Test |
|---|--------------|------|-----------|-----------|----------|-----------|-------------|
| 1 | {asset} — {vuln class} | {1/2/3} | ${amount} | {X}% | ✅ | {Xh} | {one-line test description} |
| 2 | ... | ... | ... | ... | ✅ | ... | ... |
| 3 | ... | ... | ... | ... | ✅ | ... | ... |
| 4 | ... | ... | ... | ... | ✅ | ... | ... |
| 5 | ... | ... | ... | ... | ✅ | ... | ... |
```

**Column definitions:**
| Column | Meaning |
|--------|---------|
| **#** | Priority rank — row 1 is always tested first |
| **Target / Test** | Exact asset + vulnerability class being tested |
| **Tier** | Reward tier from program scope (1 = highest bounty) |
| **Max Bounty** | Ceiling payout if Critical/High severity confirmed |
| **Success %** | Estimated probability of finding a valid, payout-eligible finding |
| **No Login** | Always ✅ — this table is unauthenticated surface only |
| **Est. Time** | Approximate wall-clock hours to complete the test |
| **What We Test** | One-line plain-English description of the attack |

**Scoring guidance for Success %:**

| Range | Meaning |
|-------|---------|
| 70%+ | Near-certain — new asset with 0 prior reports + known vulnerability pattern |
| 50–69% | High confidence — known attack class on fresh surface |
| 30–49% | Reasonable — class is likely but requires specific misconfiguration |
| 15–29% | Low — possible but depends on program-specific config |
| <15% | Skip — too low to justify time, move to next |

**Rule:** If row 1 success % < 30%, re-evaluate the entire list before testing anything.

---

## CVSS Scoring Guide

**CVSS v3.1 Quick Reference:**

| Factor | Low | Medium | High | Critical |
|--------|-----|--------|------|---------|
| **AV** (Attack Vector) | Physical | Local | Adjacent | Network |
| **AC** (Complexity) | High | — | — | Low |
| **PR** (Privileges Required) | High | Low | None | None |
| **UI** (User Interaction) | Required | — | — | None |
| **S** (Scope) | Unchanged | — | — | Changed |
| **C/I/A** (Impact) | None | Low | — | High |

**Common Vulnerability CVSS Scores:**

| Vulnerability | Typical CVSS | Severity |
|---------------|-------------|---------|
| SQLi (full data dump, no auth) | 9.8 | Critical |
| RCE (remote code exec) | 9.8 | Critical |
| SQLi (auth required) | 7.5 | High |
| Stored XSS (no auth, public) | 8.8 | High |
| IDOR (sensitive PII) | 7.5 | High |
| Reflected XSS (user interaction) | 6.1 | Medium |
| IDOR (non-sensitive data) | 5.3 | Medium |
| CSRF (state-changing action) | 6.5 | Medium |
| Open Redirect | 4.3 | Medium |
| Information Disclosure (stack trace) | 5.3 | Medium |
| Missing security headers | 3.1 | Low |

---

## HackerOne Report Format

> ⛔ PROOF GATE REQUIRED — Read your engagement protocol PROOF GATE section.
> Every box must be checked before writing the report.
> Reports written before proof is collected will be killed by automated triage.
> Lesson learned: an eth_accounts report — addresses confirmed exposed,
> impact never verified. All 5 addresses had zero balance, zero history, zero activity.
> 60-second Etherscan check would have killed this before submission.

```markdown
**Title:** [Vulnerability Type] in [Component] allows [Impact]
Example: "Reflected XSS in search parameter allows session hijacking"

---

## Summary
[2-3 sentence description of the vulnerability, what it is, where it exists,
and what an attacker could do with it.]

The [component] at [URL/endpoint] is vulnerable to [vulnerability class].
An attacker can [attack action] which results in [impact].
This affects [scope: all users / authenticated users / admin users].

---

## Severity
**CVSS Score:** [X.X] ([Critical/High/Medium/Low])
**CVSS Vector:** CVSS:3.1/AV:N/AC:L/PR:N/UI:R/S:C/C:L/I:L/A:N

---

## Steps to Reproduce

**Prerequisites:** [Account type needed, setup required]

1. Navigate to [URL]
2. [Specific action]
3. [Specific action]
4. Observe: [Expected malicious result]

---

## Proof of Concept

**Request:**
```
GET /endpoint?param=PAYLOAD HTTP/1.1
Host: example.com
Cookie: session=...
```

**Response:**
```
HTTP/1.1 200 OK
[Evidence of vulnerability in response]
```

**Screenshot/Video:** [Attach evidence]

---

## Impact

[Detailed impact description]

An attacker could:
- [Impact 1]
- [Impact 2]
- [Impact 3]

**Affected Users:** [All users / Authenticated users / Admins]
**Data at Risk:** [PII / Session tokens / Financial data / etc.]

---

## Remediation

[Specific fix recommendation]

Short term:
- [Immediate mitigation]

Long term:
- [Permanent fix with example code if applicable]

---

## References
- OWASP: [relevant OWASP link]
- CWE-[number]: [CWE name]
- [CVE if applicable]
```

---

## Disclosure Requirements

| Action | When |
|--------|------|
| Submit report | Immediately upon confirmation |
| Wait for triage | 7-14 days (check program SLA) |
| Follow up | After SLA exceeded |
| Public disclosure | Only after fix + program approval (coordinated) |
| Never disclose | Without fix or explicit permission |

---

## Report Quality Standards

**Before submitting:**
- [ ] Title clearly states vulnerability type + impact
- [ ] Steps are reproducible by a non-expert triager
- [ ] Proof of concept is included (screenshot or video)
- [ ] CVSS score calculated and vector included
- [ ] Remediation recommendation is specific
- [ ] No sensitive data (real user PII) in report
- [ ] Target verified to be in scope

---

*Bug Bounty Workflow v1.0 | cyber-operator | HackerOne authorized scope | 2026-02-23*
