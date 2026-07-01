---
title: Chain Finder — Multi-Finding Chain Detection
version: 1.0
added: 2026-04-11
owner: cyber-operator
trigger: Auto-runs in TIER 3 CTO Agent when confirmed_findings >= 2. Manual: "chain", "combine findings", "chain detection"
---

# Chain Finder

> **Purpose:** Detect when 2+ findings form an exploitable chain with higher combined severity
> than the sum of individual findings. Elite hunters file chains — not fragments.
> ATO chains are 2.5x EV. RCE chains are 3.0x. Filing fragments leaves money on the table.

**When to run:** AUTOMATICALLY in TIER 3 CTO Agent when `confirmed_findings.count >= 2`

---

## CHAIN DETECTION MATRIX

Input: `confirmed_findings[]` from current sweep + dedup-intelligence output
Run ALL 12 rules in order. Flag any match.

```
RULE 1: SSRF + IMDS Reachable
  IF finding_type == "SSRF" AND (imds_reached OR aws_metadata_returned):
    chain_type = "SSRF→CLOUD_CREDENTIAL_THEFT"
    chain_severity = Critical
    chain_multiplier = 3.0x
    action = FILE_AS_CHAIN_CRITICAL

RULE 2: SSRF + Internal Service
  IF finding_type == "SSRF" AND internal_service_reachable:
    chain_type = "SSRF→INTERNAL_NETWORK_PIVOT"
    chain_severity = High→Critical
    chain_multiplier = 2.0x
    action = FILE_AS_CHAIN

RULE 3: XSS + CORS Credentialed
  IF finding_type == "XSS" AND cors_reflection_with_credentials_true:
    chain_type = "XSS→ATO_VIA_CORS"
    chain_severity = High→Critical (ATO)
    chain_multiplier = 2.5x
    action = FILE_AS_CHAIN_CRITICAL

RULE 4: XSS + PostMessage
  IF finding_type == "XSS" AND postmessage_target_found:
    chain_type = "XSS→POSTMESSAGE_ATO"
    chain_severity = High
    chain_multiplier = 2.0x
    action = FILE_AS_CHAIN

RULE 5: Open Redirect + OAuth
  IF finding_type == "OPEN_REDIRECT" AND oauth_flow_detected:
    chain_type = "REDIRECT→OAUTH_TOKEN_THEFT→ATO"
    chain_severity = Critical (ATO)
    chain_multiplier = 2.5x
    action = FILE_AS_CHAIN_CRITICAL

RULE 6: Subdomain Takeover + OAuth Redirect URI
  IF finding_type == "SUBDOMAIN_TAKEOVER" AND oauth_redirect_uri_matches_taken_domain:
    chain_type = "TAKEOVER→OAUTH_ATO"
    chain_severity = Critical
    chain_multiplier = 3.0x
    action = FILE_AS_CHAIN_CRITICAL

RULE 7: IDOR + Mass Assignment
  IF finding_type == "IDOR" AND mass_assignment_confirmed:
    chain_type = "IDOR+MASS_ASSIGN→PRIVILEGE_ESCALATION"
    chain_severity = High
    chain_multiplier = 1.8x
    action = FILE_AS_CHAIN

RULE 8: IDOR + PII Export
  IF finding_type == "IDOR" AND pii_data_returned:
    chain_type = "IDOR→DATA_BREACH"
    chain_severity = Critical (GDPR/data breach)
    chain_multiplier = 2.0x
    action = FILE_AS_CHAIN_CRITICAL

RULE 9: Path Traversal + File Upload
  IF finding_type == "PATH_TRAVERSAL" AND file_upload_endpoint_exists:
    chain_type = "TRAVERSAL+UPLOAD→STORED_RCE"
    chain_severity = Critical
    chain_multiplier = 3.0x
    action = RESEARCH_NEEDED (need to confirm write path)

RULE 10: JWT Forged + Admin Endpoint
  IF finding_type == "JWT_BYPASS" AND admin_endpoint_accessible_with_forged_token:
    chain_type = "JWT→ADMIN_ACCESS→PRIVILEGE_ESCALATION"
    chain_severity = Critical
    chain_multiplier = 2.5x
    action = FILE_AS_CHAIN_CRITICAL

RULE 11: Swagger UI + SSRF Endpoint in Spec
  IF finding_type == "SWAGGER_UI_EXPOSED" AND spec_contains_ssrf_candidate_endpoint:
    chain_type = "SWAGGER→SSRF_DISCOVERY→ESCALATION"
    chain_severity = High (from Medium Swagger)
    chain_multiplier = 2.0x
    action = RESEARCH_NEEDED (confirm SSRF in discovered endpoint)

RULE 12: GitHub Actions Poisoning + Secrets
  IF finding_type == "GITHUB_CI_POISONING" AND secrets_in_workflow_environment:
    chain_type = "CI_POISONING→SECRET_EXFIL→SUPPLY_CHAIN"
    chain_severity = Critical
    chain_multiplier = 3.0x
    action = FILE_AS_CHAIN_CRITICAL
```

---

## CHAIN SCORING

```
chain_ev = max(individual_evs) × chain_multiplier

chain_multipliers:
  ATO confirmed:                2.5x
  RCE confirmed:                3.0x  
  Supply chain / CI poisoning:  3.0x
  Critical data breach (PII):   2.0x
  Financial fraud impact:       2.5x
  Privilege escalation chain:   1.8x
  Two-step escalation:          1.5x

Example:
  Finding A: SSRF — EV $1,500
  Finding B: IMDS reachable — EV $0 (not fileable standalone)
  Chain: SSRF→CLOUD_CREDENTIAL_THEFT
  chain_ev = $1,500 × 3.0 = $4,500
  vs. filing A standalone: $1,500
  Revenue gain from chaining: +$3,000
```

---

## FILING STRATEGY RULES

```
FILE_AS_CHAIN_CRITICAL:
  → Always file components together as one Critical/High report
  → Do NOT file fragments — triagers will see the chain and upgrade severity
  → Title: "Chain: [Component A] + [Component B] = [Impact]"

FILE_AS_CHAIN:
  → Strongly prefer combined filing
  → If one component is borderline (Low confidence), file the confirmed component
    now and note chain potential in the "Impact" section

RESEARCH_NEEDED:
  → Do NOT file chain yet
  → File confirmed component (A) standalone
  → Add note in report: "Note: If [condition X] can be confirmed, this chains to [impact Y]"
  → Flag for follow-up in your program index

FILE_SEPARATE:
  → File separately if: components are on different assets, different programs, or independent attack paths
  → Note any correlation but do not force a chain narrative
```

---

## OUTPUT FORMAT

```
CHAIN FINDER COMPLETE — {N} findings analyzed
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CHAINS DETECTED: {N}

Chain 1: {chain_type}
  Component A: {finding_id} — {vector} — standalone EV: ${X}
  Component B: {finding_id} — {vector} — standalone EV: ${X}
  Chain Type: {chain_type}
  Combined EV: ${chain_ev} (vs. individual total: ${X+Y})
  Revenue gain from chaining: +${delta}
  Filing strategy: {FILE_AS_CHAIN_CRITICAL | FILE_AS_CHAIN | RESEARCH_NEEDED}
  Recommended report title: "{title}"

NO CHAINS DETECTED: [List findings and why they don't chain]

WRITE TO: a local state file
  { "confirmed_findings": {N}, "chains_found": {N}, "chain_checked": true }
```

---

## SESSION STATE FILE

Write after every run — read by gate-validator-trigger.py for chain reminder enforcement:

```json
{
  "sweep_date": "2026-04-11",
  "target": "example.com",
  "confirmed_findings": 3,
  "chain_checked": true,
  "chains_found": 1,
  "chains": [
    {
      "type": "SSRF→CLOUD_CREDENTIAL_THEFT",
      "component_findings": ["FINDING-ID", "FINDING-ID"],
      "combined_ev": 4500,
      "individual_evs": [1500, 0],
      "filing_strategy": "FILE_AS_CHAIN_CRITICAL"
    }
  ]
}
```
