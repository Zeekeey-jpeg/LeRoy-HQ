---
title: Dedup Intelligence — Pre-Submission Risk Scoring
version: 1.0
added: 2026-04-11
owner: cyber-operator
trigger: Auto-runs in TIER 2.5 for every confirmed POC. Manual: "dedup", "check duplicate", "before filing"
---

# Dedup Intelligence

> **Purpose:** Cross-check every confirmed finding against public disclosure databases BEFORE drafting
> a report. Outputs a `dup_probability` (0.0–1.0) that feeds directly into the EV formula as
> `duplicate_discount`. Prevents the most expensive outcome in bug bounty: filing a duplicate.

**When to run:** AUTOMATICALLY in TIER 2.5 — do not wait for the operator to ask.

---

## DEDUP CHECK WORKFLOW

Run all 4 steps for each `confirmed_finding`. Steps 1-3 can run in parallel.

### STEP 1 — HackerOne Hacktivity Search

```
Search: site:hackerone.com/reports "{vector_type}" "{target_domain}"
OR:     site:hackerone.com/reports "{company_name}" "{vulnerability_class}"

Examples:
  - site:hackerone.com/reports "SSRF" "example.com" disclosed
  - site:hackerone.com/reports "subdomain takeover" "example.com"
  - site:hackerone.com/reports "Swagger UI" "an example company"

Parse results:
  FOR each result:
    - Does the URL/endpoint match?
    - Is the vulnerability type the same?
    - Was it RESOLVED (not just triaged)?
    - Was it filed within the last 12 months?

Score:
  Same endpoint + same vector + resolved = dup_probability += 0.7
  Same vector + same asset class + resolved = dup_probability += 0.3
  Same vector class + different program = dup_probability += 0.1
```

### STEP 2 — Program-Specific Hacktivity Check

```
WebFetch: https://hackerone.com/{program_handle}/hacktivity (if public program)

Parse: disclosed reports list
  - Filter by: vulnerability_type matching current finding
  - Filter by: asset matching current finding's target asset
  - Check: was this exact endpoint/parameter disclosed?

Score:
  Exact endpoint disclosed in same program = dup_probability += 0.6
  Same parameter class disclosed in same program = dup_probability += 0.3
```

### STEP 3 — Intigriti / YesWeHack / Bugcrowd Check

```
WebSearch: site:yeswehack.com "{company_name}" "{finding_type}"
WebSearch: site:intigriti.com disclosure "{company_name}" "{vector}"
WebSearch: "bugcrowd" "{company_name}" "{vulnerability_type}" disclosed

Score:
  Disclosed on same platform + same company = dup_probability += 0.5
  Disclosed on different platform + same company = dup_probability += 0.3
```

### STEP 4 — Program Age + Saturation Adjustment

```
program_age_months = (today - program_launch_date) / 30

IF program_age_months > 36:
  saturation_factor = 0.8  # Old program — most easy vectors found
ELIF program_age_months > 18:
  saturation_factor = 0.5
ELIF program_age_months > 6:
  saturation_factor = 0.2
ELSE:
  saturation_factor = 0.05  # New program — low saturation

dup_probability = min(dup_probability + saturation_factor * 0.1, 0.95)
```

---

## OUTPUT SCHEMA

Write to `a local state file` per finding. Read by pre-filing-dedup-check.py hook.

```json
{
  "findings": [
    {
      "finding_id": "FINDING-ID",
      "vector": "GitHub Actions pull_request_target + branch-pinned action",
      "target_domain": "example.com",
      "program_handle": "example-program",
      "dup_probability": 0.15,
      "duplicate_risk": "LOW",
      "evidence_url": null,
      "recommendation": "FILE_NOW",
      "dedup_checked": true,
      "checked_at": "2026-04-11T14:30:00Z",
      "search_queries_run": [
        "site:hackerone.com/reports pull_request_target an example program",
        "site:hackerone.com/reports GitHub Actions an example program"
      ]
    }
  ]
}
```

---

## DECISION RULES

```
dup_probability > 0.70:
  → duplicate_risk = HIGH
  → recommendation = HOLD
  → Action: "Strong evidence this vector was disclosed. Check evidence_url. the operator decides."

dup_probability 0.40-0.70:
  → duplicate_risk = MEDIUM
  → recommendation = FILE_WITH_CAUTION
  → Action: "Moderate duplicate risk. Add note in report: 'Searched H1 hacktivity — no exact match found.'"

dup_probability 0.20-0.40:
  → duplicate_risk = LOW
  → recommendation = FILE_NOW
  → Action: "Low duplicate risk. Proceed normally."

dup_probability < 0.20:
  → duplicate_risk = LOW
  → recommendation = FILE_NOW
  → Action: "Very low duplicate risk. File immediately."
```

---

## EV FORMULA INTEGRATION

Feed `dup_probability` directly into the EV formula as `duplicate_discount`:

```
BEFORE (the base EV formula):
  EV = ceiling × confidence × uniqueness × program_responsiveness

AFTER (the EV formula v2 — with dedup):
  EV = ceiling × confidence × uniqueness × program_responsiveness × (1 - dup_probability)

Example:
  Ceiling: an example ceiling (an example program High)
  Confidence: 0.90
  Uniqueness: 0.95
  Program Responsiveness: 0.85
  dup_probability: 0.15

  BEFORE: EV = $1,750 × 0.90 × 0.95 × 0.85 = $1,270
  AFTER:  EV = $1,270 × (1 - 0.15) = $1,080

  Impact: Filing a HIGH dup_probability (0.80) finding:
  EV = $1,270 × (1 - 0.80) = $254 expected value — not worth the session cost risk
```

---

## DELIVERY FORMAT

```
DEDUP INTELLIGENCE COMPLETE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Finding: {finding_id}
Vector: {vector_type} on {endpoint}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
dup_probability:   {X.XX}
Duplicate Risk:    {LOW | MEDIUM | HIGH}
Recommendation:    {FILE_NOW | FILE_WITH_CAUTION | HOLD | SKIP}
Evidence:          {URL or "No prior disclosure found"}

EV Impact:
  Gross EV (no dedup): ${X}
  Net EV (post-dedup): ${X}

Action: {action text}
```
