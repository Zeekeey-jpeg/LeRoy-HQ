---
name: cvss4-calculator
description: "CVSS 4.0 auto-calculator for bug bounty report scoring. Pre-filled vectors for 15+ common finding classes. Use when: calculating severity for report submission, Immunefi/H1 programs using CVSS scoring, determining payout tier. Covers: all 9 Base metrics, pre-built vector strings, score-to-severity mapping."
version: 1.0
created: 2026-04-11
owner: cyber-operator
trigger_keywords: "cvss, cvss 4.0, cvss score, severity score, cvss vector, cvss calculator, cvss4, base score, finding severity"
---

# CVSS 4.0 Auto-Calculator

## Purpose

CVSS 4.0 replaced CVSS 3.1 in 2023. Many H1 programs and all Immunefi programs use CVSS 4.0 for payout tier determination. Incorrect or missing CVSS vectors cause reports to be downgraded at triage. This skill auto-generates the correct vector string for common finding classes.

---

## CVSS 4.0 Base Metrics

All 9 metrics are required. Format: `CVSS:4.0/AV:X/AC:X/AT:X/PR:X/UI:X/VC:X/VI:X/VA:X/SC:X/SI:X/SA:X`

| Metric | Code | Values | Description |
|--------|------|--------|-------------|
| Attack Vector | AV | N (Network), A (Adjacent), L (Local), P (Physical) | How attacker reaches vulnerable component |
| Attack Complexity | AC | L (Low), H (High) | Conditions beyond attacker's control |
| Attack Requirements | AT | N (None), P (Present) | Prerequisites needed beyond scope |
| Privileges Required | PR | N (None), L (Low), H (High) | Auth level needed before attack |
| User Interaction | UI | N (None), P (Passive), A (Active) | User action required |
| Vulnerable System Confidentiality | VC | H, L, N | Data disclosure in affected component |
| Vulnerable System Integrity | VI | H, L, N | Data modification in affected component |
| Vulnerable System Availability | VA | H, L, N | Service disruption in affected component |
| Subsequent System Confidentiality | SC | H, L, N | Data disclosure beyond affected component |
| Subsequent System Integrity | SI | H, L, N | Data modification beyond affected component |
| Subsequent System Availability | SA | H, L, N | Service disruption beyond affected component |

---

## Score → Severity Mapping (CVSS 4.0)

| Score Range | Severity | Typical H1 Payout | Typical Immunefi |
|-------------|----------|-------------------|------------------|
| 9.0 – 10.0 | **Critical** | $5K – $100K | $500K – $15M |
| 7.0 – 8.9 | **High** | $2.5K – $25K | $50K – $500K |
| 4.0 – 6.9 | **Medium** | $500 – $2.5K | $10K – $50K |
| 0.1 – 3.9 | **Low** | $100 – $500 | Rarely paid |

---

## Pre-Built Vector Table (Common Finding Classes)

Use these directly in reports. Modify metrics only if your specific scenario differs.

### Network / Web Application Findings

| Finding Class | CVSS 4.0 Vector | Score | Severity |
|---------------|----------------|-------|----------|
| **SSRF → IMDS IAM credential theft** | `CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:H/VI:H/VA:H/SC:H/SI:H/SA:H` | **9.3** | Critical |
| **Blind SSRF (DNS callback only)** | `CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:L/VI:N/VA:N/SC:N/SI:N/SA:N` | **6.9** | Medium |
| **Full SSRF (HTTP callback, no IMDS)** | `CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:H/VI:N/VA:N/SC:N/SI:N/SA:N` | **8.0** | High |
| **Stored XSS → ATO (admin bot)** | `CVSS:4.0/AV:N/AC:L/AT:N/PR:L/UI:P/VC:H/VI:H/VA:N/SC:H/SI:H/SA:N` | **8.7** | High |
| **Reflected XSS (user interaction)** | `CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:A/VC:L/VI:L/VA:N/SC:N/SI:N/SA:N` | **5.3** | Medium |
| **JWT alg:none → admin escalation** | `CVSS:4.0/AV:N/AC:L/AT:N/PR:L/UI:N/VC:H/VI:H/VA:N/SC:H/SI:H/SA:N` | **9.1** | Critical |
| **JWT RS256→HS256 algorithm confusion** | `CVSS:4.0/AV:N/AC:H/AT:N/PR:L/UI:N/VC:H/VI:H/VA:N/SC:H/SI:H/SA:N` | **8.3** | High |
| **IDOR — cross-account PII disclosure** | `CVSS:4.0/AV:N/AC:L/AT:N/PR:L/UI:N/VC:H/VI:N/VA:N/SC:N/SI:N/SA:N` | **7.1** | High |
| **IDOR — cross-account data modification** | `CVSS:4.0/AV:N/AC:L/AT:N/PR:L/UI:N/VC:H/VI:H/VA:N/SC:N/SI:N/SA:N` | **8.2** | High |
| **Open Redirect** | `CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:A/VC:N/VI:N/VA:N/SC:L/SI:N/SA:N` | **4.8** | Medium |
| **CORS misconfiguration + credentialed** | `CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:A/VC:H/VI:N/VA:N/SC:N/SI:N/SA:N` | **6.9** | Medium |
| **GraphQL BOLA (cross-user data)** | `CVSS:4.0/AV:N/AC:L/AT:N/PR:L/UI:N/VC:H/VI:N/VA:N/SC:N/SI:N/SA:N` | **7.1** | High |
| **SQL Injection (error-based, no auth)** | `CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:H/VI:H/VA:H/SC:N/SI:N/SA:N` | **9.3** | Critical |
| **SSTI → RCE** | `CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:H/VI:H/VA:H/SC:H/SI:H/SA:H` | **9.3** | Critical |
| **XXE → file read** | `CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:H/VI:N/VA:N/SC:N/SI:N/SA:N` | **8.7** | High |
| **XXE → SSRF → IMDS** | `CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:H/VI:H/VA:H/SC:H/SI:H/SA:H` | **9.3** | Critical |
| **Race condition — coupon/OTP reuse** | `CVSS:4.0/AV:N/AC:H/AT:P/PR:L/UI:N/VC:N/VI:H/VA:N/SC:N/SI:H/SA:N` | **6.4** | Medium |
| **Race condition → ATO (single-use token)** | `CVSS:4.0/AV:N/AC:H/AT:P/PR:N/UI:N/VC:H/VI:H/VA:N/SC:H/SI:H/SA:N` | **8.6** | High |
| **Auth bypass (MFA skip)** | `CVSS:4.0/AV:N/AC:L/AT:N/PR:L/UI:N/VC:H/VI:H/VA:N/SC:H/SI:H/SA:N` | **9.1** | Critical |
| **Password reset poisoning** | `CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:A/VC:H/VI:H/VA:N/SC:H/SI:H/SA:N` | **8.7** | High |
| **CSRF → account modification** | `CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:A/VC:N/VI:H/VA:N/SC:N/SI:N/SA:N` | **6.9** | Medium |
| **Subdomain takeover** | `CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:A/VC:L/VI:H/VA:N/SC:L/SI:H/SA:N` | **7.1** | High |

### AI / LLM Findings

| Finding Class | CVSS 4.0 Vector | Score | Severity |
|---------------|----------------|-------|----------|
| **Indirect prompt injection → ATO** | `CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:P/VC:H/VI:H/VA:N/SC:H/SI:H/SA:N` | **9.1** | Critical |
| **RAG poisoning → data exfil** | `CVSS:4.0/AV:N/AC:H/AT:P/PR:N/UI:P/VC:H/VI:N/VA:N/SC:H/SI:N/SA:N` | **8.3** | High |
| **System prompt disclosure with credentials** | `CVSS:4.0/AV:N/AC:L/AT:N/PR:L/UI:N/VC:H/VI:N/VA:N/SC:N/SI:N/SA:N` | **7.5** | High |

### Cloud / Infrastructure

| Finding Class | CVSS 4.0 Vector | Score | Severity |
|---------------|----------------|-------|----------|
| **S3 public bucket — sensitive data** | `CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:H/VI:N/VA:N/SC:N/SI:N/SA:N` | **8.7** | High |
| **GitHub Actions secret exfil** | `CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:H/VI:H/VA:N/SC:H/SI:H/SA:N` | **9.3** | Critical |
| **Kubernetes pod escape → node** | `CVSS:4.0/AV:N/AC:H/AT:P/PR:L/UI:N/VC:H/VI:H/VA:H/SC:H/SI:H/SA:H` | **9.2** | Critical |

---

## How to Customize a Vector

If your finding doesn't match a pre-built entry:

```
1. Start with the closest pre-built entry from the table
2. Adjust only the metrics that differ from your specific scenario:
   - No auth required? Set PR:N
   - User must click a link? Set UI:A (Active)  
   - Only affects the vulnerable system? Set SC:N/SI:N/SA:N
   - Attacker needs specific conditions (race, timing)? Set AC:H
3. Use the CVSS 4.0 calculator at: https://www.first.org/cvss/calculator/4.0

Key "Subsequent System" guidance:
  SC/SI/SA = N: Impact stays within the vulnerable component
  SC/SI/SA = L/H: Impact crosses to other systems (lateral movement, cascading failures)
  Example: SSRF on payment microservice that can reach internal DB = SC:H/SI:H
```

---

## Integration with EV Engine

When a finding is scored with CVSS 4.0:
- **Score ≥ 9.0:** Use `payout_ceiling` at Critical tier for EV calculation
- **Score 7.0-8.9:** Use High tier ceiling
- **Score 4.0-6.9:** Use Medium tier ceiling
- If program uses CVSS-based payout table: substitute program's exact ceiling at that score

**Auto-include in report header:**
```
Severity: [Critical/High/Medium/Low]
CVSS 4.0 Score: [X.X]
CVSS 4.0 Vector: CVSS:4.0/AV:X/AC:X/AT:X/PR:X/UI:X/VC:X/VI:X/VA:X/SC:X/SI:X/SA:X
```

---

*CVSS 4.0 Calculator v1.0 | Whitehat System | Report Severity Scoring*
