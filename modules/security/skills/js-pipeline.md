---
title: JS Bundle Extraction Pipeline
version: 1.0
added: 2026-04-11
owner: cyber-operator
trigger: Any target with React/Next.js/Vue/Angular/JS-heavy frontend
---

# JS Bundle Extraction Pipeline

> Automated JS bundle crawl → source map extraction → endpoint catalog → secret mining.
> Runs as Tier 1 sub-agent immediately after active-recon.md delivers live-hosts.json.

**Auto-load conditions:**
```
IF tech_fingerprint.frameworks contains React|Next.js|Vue|Angular|Svelte → LOAD
IF live-hosts.json shows *.js files > 50KB in network requests → LOAD
IF a source-map recon step trigger fires → delegate to this file first
IF target is SPA (Single Page Application) → LOAD
```

---

## STEP 1 — Bundle Discovery

Use playwright-cli to load each live host and capture all network JS requests:

```bash
# Capture all JS network requests for a target
playwright-cli fetch-resources {TARGET_URL} \
  --filter "*.js" \
  --filter "*.js.gz" \
  --output js-urls.txt

# Also check common static paths directly
for path in "/static/js/" "/_next/static/chunks/" "/assets/js/" "/dist/" "/build/static/"; do
  curl -s "${TARGET_URL}${path}" | grep -oP '"[^"]+\.js"' | tr -d '"' | \
    sed "s|^|${TARGET_URL}${path}|" >> js-urls.txt
done

# Check for manifest files (Next.js, Webpack)
for manifest in "/_next/static/chunks/webpack.js" "/asset-manifest.json" \
                "/webpack-manifest.json" "/build/asset-manifest.json"; do
  curl -s "${TARGET_URL}${manifest}" >> manifest-raw.txt 2>/dev/null
done
grep -oP 'https?://[^\s"]+\.js' manifest-raw.txt >> js-urls.txt
sort -u js-urls.txt -o js-urls.txt

echo "[JS-PIPELINE] Bundles discovered: $(wc -l < js-urls.txt)"
```

---

## STEP 2 — Source Map Check (Primary Path)

Source maps expose original source code. Always check before raw analysis.

```bash
for js_url in $(cat js-urls.txt); do
  map_url="${js_url}.map"
  status=$(curl -s -o /dev/null -w "%{http_code}" "$map_url")
  if [ "$status" = "200" ]; then
    echo "SOURCE_MAP_FOUND: $map_url" >> source-maps-found.txt
    # Delegate to a source-map recon step for full extraction
    echo "[JS-PIPELINE] Source map found: $map_url → escalate to a source-map recon step"
  else
    echo "$js_url" >> no-source-map.txt
  fi
done
```

If source maps found → **load a source-map recon step** for full reconstruction.
Continue with Step 3 for bundles without source maps.

---

## STEP 3 — Raw Bundle Analysis

For bundles without source maps, extract endpoints and secrets from minified JS.

### Endpoint Extraction (LinkFinder Pattern)

```bash
for js_url in $(cat no-source-map.txt); do
  # Download bundle
  bundle_file="bundle-$(echo $js_url | md5sum | cut -d' ' -f1).js"
  curl -s "$js_url" -o "$bundle_file"
  
  # LinkFinder pattern: extract all URL paths
  grep -oP "(?<=[\"'\`])(https?://[^\s\"'\`]+|/[a-zA-Z0-9_/.-]{3,}(?:\?[^\s\"'\`]*)?)(?=[\"'\`])" \
    "$bundle_file" | \
    grep -v "^//" | \
    grep -v "\.png\|\.jpg\|\.css\|\.ico\|\.woff\|\.svg" | \
    sort -u >> raw-endpoints.txt
  
  # Extract internal package references (company-specific)
  grep -oP '@[a-zA-Z0-9-]+/[a-zA-Z0-9-]+' "$bundle_file" >> internal-packages.txt
  
  # Extract API base URLs
  grep -oP '(https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(?:/[a-zA-Z0-9._/-]*)?)' \
    "$bundle_file" | sort -u >> api-base-urls.txt
done
```

### Secret Extraction (SecretFinder Patterns)

```bash
for bundle_file in bundle-*.js; do
  # AWS Access Key
  grep -oP 'AKIA[0-9A-Z]{16}' "$bundle_file" >> secrets-raw.txt && \
    echo "AWS_KEY: $(grep -oP 'AKIA[0-9A-Z]{16}' $bundle_file)" >> secrets-classified.txt

  # JWT tokens (active sessions, long-lived service tokens)
  grep -oP 'eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}' \
    "$bundle_file" >> secrets-raw.txt

  # Slack tokens
  grep -oP 'xox[baprs]-[0-9a-zA-Z]{10,48}' "$bundle_file" >> secrets-raw.txt

  # GitHub PATs
  grep -oP 'gh[pousr]_[A-Za-z0-9_]{36,255}' "$bundle_file" >> secrets-raw.txt

  # Stripe keys
  grep -oP 'sk_(live|test)_[0-9a-zA-Z]{24,}' "$bundle_file" >> secrets-raw.txt

  # SendGrid
  grep -oP 'SG\.[0-9A-Za-z\-_]{22,}\.[0-9A-Za-z\-_]{43,}' "$bundle_file" >> secrets-raw.txt

  # Generic API keys (high false positive — flag, don't auto-file)
  grep -oP '(?i)(api[_-]?key|apikey|api[_-]?secret|client[_-]?secret|access[_-]?token)\s*[:=]\s*["\x27]([A-Za-z0-9+/=_-]{20,})["\x27]' \
    "$bundle_file" >> secrets-generic.txt

  # Hardcoded passwords
  grep -oP '(?i)(password|passwd|pwd)\s*[:=]\s*["\x27]([^"]{8,})["\x27]' \
    "$bundle_file" | grep -v "placeholder\|example\|your-password" >> secrets-generic.txt
done

# Deduplicate secrets
sort -u secrets-raw.txt -o secrets-raw.txt
echo "[JS-PIPELINE] Secrets found: $(wc -l < secrets-raw.txt)"
```

---

## STEP 4 — Endpoint Catalog Build

```bash
# Normalize paths: strip query params for catalog entry
cat raw-endpoints.txt | sed 's/?.*$//' | sort -u > endpoint-catalog-raw.txt

# Classify endpoints
grep -E "^/api/" endpoint-catalog-raw.txt > catalog-api.txt
grep -E "^/admin" endpoint-catalog-raw.txt > catalog-admin.txt
grep -E "^/internal|^/private|^/debug|^/dev/" endpoint-catalog-raw.txt > catalog-internal.txt
grep -E "^/v[0-9]|^/[0-9]+\." endpoint-catalog-raw.txt > catalog-versioned.txt

# Mark auth candidates: paths likely requiring auth
grep -E "user|account|profile|dashboard|settings|manage|order|payment|billing|admin|config" \
  endpoint-catalog-raw.txt > catalog-auth-candidates.txt

echo "[JS-PIPELINE] Endpoints cataloged:"
echo "  API paths:      $(wc -l < catalog-api.txt)"
echo "  Admin paths:    $(wc -l < catalog-admin.txt)"
echo "  Internal paths: $(wc -l < catalog-internal.txt)"
echo "  Auth candidates:$(wc -l < catalog-auth-candidates.txt)"

# Write final catalog
{
  echo "# Endpoint Catalog — $(date +%Y-%m-%d) — ${TARGET}"
  echo "## API Paths"; cat catalog-api.txt
  echo "## Admin Paths"; cat catalog-admin.txt
  echo "## Internal Paths"; cat catalog-internal.txt
  echo "## Auth Candidates"; cat catalog-auth-candidates.txt
} > "out/js-endpoints-${TARGET}.json"
```

---

## STEP 5 — Live Probe (Zero-Auth Status Check)

```bash
BASE_URL="${TARGET_URL}"

while IFS= read -r endpoint; do
  # Skip obviously relative paths without leading slash
  [[ "$endpoint" != /* ]] && endpoint="/$endpoint"
  
  status=$(curl -s -o /dev/null -w "%{http_code}" \
    -m 5 --max-redirs 3 \
    "${BASE_URL}${endpoint}")
  
  case $status in
    200|201)
      echo "HIGH_CANDIDATE: ${endpoint} (${status})" >> probe-results.txt ;;
    401|403)
      echo "AUTH_REQUIRED: ${endpoint} (${status})" >> probe-results.txt ;;
    301|302)
      echo "REDIRECT: ${endpoint} (${status})" >> probe-results.txt ;;
    404)
      ;; # Skip 404s
    *)
      echo "OTHER: ${endpoint} (${status})" >> probe-results.txt ;;
  esac

done < catalog-internal.txt

# High-value: 200 unauthed on admin/internal paths
grep "^HIGH_CANDIDATE" probe-results.txt | head -20
echo "[JS-PIPELINE] Zero-auth 200s found: $(grep -c HIGH_CANDIDATE probe-results.txt 2>/dev/null || echo 0)"
```

---

## OUTPUT SCHEMA

Saved to `out/js-endpoints-{target}.json` and passed to Tier 2 overseers.

```json
{
  "target": "example.com",
  "bundles_analyzed": 12,
  "source_maps_found": 2,
  "endpoints_extracted": 347,
  "secrets_found": {
    "aws_keys": 0,
    "jwts": 1,
    "api_keys_generic": 3,
    "total": 4
  },
  "catalog": {
    "api_paths": ["..."],
    "admin_paths": ["..."],
    "internal_paths": ["..."],
    "auth_candidates": ["..."]
  },
  "zero_auth_200s": ["..."],
  "auth_required_403s": ["..."]
}
```

---

## DELIVERY FORMAT

```
JS PIPELINE COMPLETE — {TARGET}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Bundles analyzed:       {N}
Source maps found:      {N} → delegating to a source-map recon step
Endpoints extracted:    {N}
Admin paths discovered: {N}
Secrets detected:       {N} ({types})
Zero-auth 200s:         {N} (HIGH PRIORITY)

→ Endpoint catalog saved to: out/js-endpoints-{target}.json
→ Passing catalog to a parameter-fuzzing step
→ Passing auth-candidates to Tier 2 Auth Track Overseer
→ Passing secrets to Tier 3 CFO for immediate EV assessment
```

---

## Step 4 — Git History Secret Scan (CONDITIONAL — run if GitHub repo found)

**Precondition:** Tier 1 GitHub dorks found a public repo for this org/target.

```bash
# Install trufflehog (one-time):
# Windows: winget install trufflesecurity.trufflehog
# Linux/Mac: curl -sSfL https://raw.githubusercontent.com/trufflesecurity/trufflehog/main/scripts/install.sh | sh

# Scan public GitHub repo (git history — catches deleted secrets):
trufflehog git https://github.com/{org}/{repo} --only-verified --json \
  > out/trufflehog-{target}.json

# Scan local clone (if repo was cloned for source analysis):
trufflehog filesystem /path/to/cloned/repo --only-verified --json \
  >> out/trufflehog-{target}.json

# --only-verified: CRITICAL FLAG — only outputs secrets that are confirmed live
# Without this flag: high false positive rate (noise)
# With this flag: every result is a real, active credential
```

**Results routing:**
```
trufflehog output per verified secret:
  → AWS credentials (AKIA...) → Overseer 4 Cloud Track (immediate, high EV)
  → GitHub tokens (ghp_/ghs_/gho_) → Overseer 4 Cloud Track
  → Stripe/payment keys → Overseer 1 Web Track + Tier 3 CFO (Critical EV)
  → Database connection strings → Overseer 4 Cloud Track
  → JWT secrets → Overseer 2 Auth Track (enables JWT forge attacks)
  → Slack/Telegram/SendGrid API keys → Tier 3 CFO (data exfil vector)

Route to: out/trufflehog-{target}.json
Status line: "Git secrets: {N} verified ({credential_types})"
```

**Rate and scope law:**
```
NEVER scan private repos — public only.
NEVER scan all-of-GitHub (no org-wide crawling).
Scope: only the repos explicitly found in GitHub dorks for this program's org.
Depth: full git history (trufflehog handles this — no depth flag needed).
```
