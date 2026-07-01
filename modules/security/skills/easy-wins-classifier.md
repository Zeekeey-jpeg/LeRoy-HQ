---
title: Easy Wins Classifier v1.0
owner: cyber-operator
trigger: "Loaded automatically at sweep end, before brief generation"
created: 2026-03-10
tags: [skills-learned, cyber, bounty]
---

# Easy Wins Classifier v1.0

**Purpose:** At the end of every sweep, classify confirmed findings into EASY WIN vs. OPPORTUNITY vs. DEPRIORITIZED. easy wins surface first — these are the "file immediately" candidates.

**Loaded by:** the reporting stage, before brief generation.
**Trigger:** "easy wins", "quick wins", "what should I file"

---

## EASY WIN Classification Criteria

A finding qualifies as EASY WIN if ALL 5 conditions are met:

```
1. POC CONFIRMED           → Actual data / callback / session / error — no simulation
2. WIN RATE ≥ 65%          → Per arsenal-index.md SEVERITY TIER MATRIX
3. DUP RISK LOW            → At least ONE of:
                               - Program < 30 days old
                               - Vector is program-specific or manual (not generic)
                               - Hacktivity shows no matching public disclosures
4. REPORT IS SIMPLE        → ≤ 6 steps to reproduce, no complex chain required
5. NOT ALREADY FILED       → Check your program index — not a duplicate of existing filed finding
```

If any condition fails → classify as OPPORTUNITY (needs more work) or DEAD END.

---

## Auto-Classification Table

These vectors AUTO-CLASSIFY as EASY WIN when POC is confirmed:

| Finding Type | Condition | Win Rate | EV Range | Notes |
|-------------|-----------|----------|----------|-------|
| Config / Default Credentials | admin/admin or common creds confirmed, panel accessible | 70% | $300–$3K | Most hunters skip this — low competition |
| Dependency Confusion | Interactsh/OOB callback received from target build | 90% | $2K–$30K | Near-certain if callback confirmed |
| IDOR — cross-account data | Different user's data returned with your session | 62% | $500–$5K | EASY WIN if program < 60 days old |
| Business Logic — price/quantity | Negative quantity or price bypass confirmed, financial gain | 80% | $500–$5K | Low dup rate, program-specific |
| LLM Indirect Injection + exfil | Exfiltration to attacker-controlled endpoint confirmed | 67% | $1K–$10K | New class, low competition |
| CI/CD injection + RCE in build | Code execution in build pipeline confirmed | 82% | $5K–$50K | Double bounty if CI/CD campaign active |
| SSRF + cloud metadata | IAM credentials retrieved from IMDS | 85% | $5K–$50K | File immediately — high triager priority |
| JWT alg:none accepted | Admin token forged and accepted | 72% | $1K–$10K | File immediately if confirmed |
| Subdomain takeover + DNS confirmed | NS records pointing to unclaimed provider confirmed | 68% | $500–$5K | Easy reproduction, clear evidence |
| Password / credentials in config | .env or config.php accessible, credentials valid | 70% | $500–$5K | Most hunters don't check these paths |

---

## Classification Output Format

At sweep end, easy-wins-classifier produces this block for the brief:

```
🎯 EASY WIN CANDIDATES (file immediately, high confidence):

[1] [Finding Type] — [Asset/Endpoint]
    Evidence: [1 sentence — what you saw, what was returned]
    Expected: [Severity] → $[EV range] | Win rate: [X]% | Dup risk: [LOW/MED]
    Report complexity: [N] steps. Simple is good here.

[2] [Finding Type] — [Asset/Endpoint]
    Evidence: [...]
    Expected: [...]
```

---

## When NOT to Classify as Easy Win

| Signal | Classification |
|--------|--------------|
| OOB callback only (no HTTP content) | OPPORTUNITY — escalate first, then classify |
| XSS reflected (generic, no ATO chain) | DEPRIORITIZED — high dup, low win rate (45%) |
| CORS without ACAC:true | DEPRIORITIZED — 25% win rate, almost never paid |
| Info disclosure only (no Act 2 demonstrated) | **BLOCKED** — must answer "as an attacker I could [specific action]" with evidence before filing. curl the exposed URL. Test the key. Chain it. If you can't complete that sentence with proof, do not file. (Lesson: an example program consumerHost 2026-03-17 — marked N/A, host unreachable externally) |
| Business logic theoretical (not confirmed with money) | BLOCKED — do NOT file |
| Dependency confusion, no callback | OPPORTUNITY — needs callback to confirm |

---

## Integration with Brief

After easy-wins-classifier runs, Report Agent writes the brief using:
1. Easy wins → "🎯 EASY WINS" section (file now)
2. Remaining confirmed findings → severity breakdown with win rates
3. Unconfirmed high-confidence → "⏳ OPPORTUNITIES" section
4. Tested-and-failed → "🚫 DEAD ENDS" (add to depletion registry)

**Next skill in chain:** `a report-voice guide` → `a report quality gate`

---

*Easy Wins Classifier v1.0 | cyber-operator | 2026-03-10*
