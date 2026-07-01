---
title: Parameter Discovery & Fuzzing
version: 1.0
added: 2026-04-11
owner: cyber-operator
trigger: After js-pipeline.md delivers endpoint catalog; or "fuzz", "ffuf", "param discovery"
---

# Parameter Discovery & Fuzzing

> Automates endpoint and parameter discovery with ffuf. Runs after js-pipeline.md delivers
> the endpoint catalog. Expands attack surface before exploitation.

**Auto-load:** After js-pipeline.md completion. Input: `js-endpoints-{target}.json`

---

## RATE LIMIT LAW (ABSOLUTE — ZERO EXCEPTIONS ON BB TARGETS)

```
NEVER: -rate > 50 (requests per second)
NEVER: -t (threads) > 10
ALWAYS: Add User-Agent matching program expectations
ON 429: Pause 30s → reduce to -rate 10 → retry ONCE → if 429 again, STOP that workflow
ON 503: Stop immediately. Do not retry.
RESPECT: If program rules say no automated scanning, skip parameter-fuzzer entirely.
```

---

## WORKFLOW 1 — Directory & Endpoint Discovery

Discover hidden endpoints beyond what JS extraction found.

```bash
# Primary wordlists (use in order, stop when enough surface found)
WORDLIST_SMALL="/usr/share/seclists/Discovery/Web-Content/raft-small-directories.txt"
WORDLIST_API="/usr/share/seclists/Discovery/Web-Content/api/api-endpoints.txt"
WORDLIST_COMMON="/usr/share/seclists/Discovery/Web-Content/common.txt"

# Base discovery — filter 404 + size-based false positives
ffuf \
  -w $WORDLIST_SMALL \
  -u "${TARGET_URL}/FUZZ" \
  -fc 404 \
  -rate 50 \
  -t 10 \
  -mc 200,201,301,302,401,403 \
  -o ffuf-dirs.json \
  -of json \
  -H "User-Agent: Mozilla/5.0 (compatible; SecurityResearch/1.0)" \
  -timeout 10

# API-specific discovery (if /api/ exists)
if grep -q "^/api" js-endpoints-${TARGET}.json 2>/dev/null; then
  ffuf \
    -w $WORDLIST_API \
    -u "${TARGET_URL}/api/FUZZ" \
    -fc 404 \
    -rate 50 \
    -t 10 \
    -mc 200,201,301,302,401,403 \
    -o ffuf-api.json \
    -of json \
    -H "User-Agent: Mozilla/5.0 (compatible; SecurityResearch/1.0)"
fi

# Parse results
cat ffuf-dirs.json | jq -r '.results[] | "\(.status) \(.url)"' | sort -k1 -n
echo "[FUZZER] Endpoints discovered: $(cat ffuf-dirs.json | jq '.results | length')"
```

---

## WORKFLOW 2 — Parameter Discovery on Known Endpoints

For each cataloged endpoint from js-pipeline, fuzz for hidden parameters.

```bash
# Common parameter wordlist
PARAMS_LIST="/usr/share/seclists/Discovery/Web-Content/burp-parameter-names.txt"

# Process endpoints from JS catalog
jq -r '.catalog.api_paths[]' "js-endpoints-${TARGET}.json" 2>/dev/null | \
while IFS= read -r endpoint; do
  
  # Skip obviously wrong endpoints
  [[ ${#endpoint} -gt 100 ]] && continue
  [[ "$endpoint" == *"{{"* ]] && continue

  # GET parameter fuzzing
  ffuf \
    -w $PARAMS_LIST \
    -u "${TARGET_URL}${endpoint}?FUZZ=test" \
    -fc 404,400 \
    -rate 30 \
    -t 5 \
    -mc 200,201,302,500 \
    -fw 0 \
    -o "ffuf-params-$(echo $endpoint | tr '/' '_').json" \
    -of json \
    -H "User-Agent: Mozilla/5.0 (compatible; SecurityResearch/1.0)" \
    -timeout 8 2>/dev/null

done

# Collect all discovered parameters
find . -name "ffuf-params-*.json" -exec jq -r '.results[] | .input.FUZZ' {} \; | \
  sort -u > discovered-params.txt
echo "[FUZZER] New parameters found: $(wc -l < discovered-params.txt)"
```

---

## WORKFLOW 3 — API Version Discovery

Find undocumented API versions. Legacy versions often lack security controls.

```bash
# Version wordlist
VERSIONS="v1 v2 v3 v4 v5 v6 v7 v8 v9 v10 v1.0 v1.1 v2.0 v3.0 beta dev staging internal legacy old deprecated"
echo "$VERSIONS" | tr ' ' '\n' > version-wordlist.txt

# Test both /api/VERSION/ and /VERSION/api/ patterns
ffuf \
  -w version-wordlist.txt \
  -u "${TARGET_URL}/api/FUZZ/users" \
  -fc 404 \
  -rate 20 \
  -t 5 \
  -mc 200,201,401,403 \
  -o ffuf-versions.json \
  -of json

ffuf \
  -w version-wordlist.txt \
  -u "${TARGET_URL}/FUZZ/api/users" \
  -fc 404 \
  -rate 20 \
  -t 5 \
  -mc 200,201,401,403 \
  -o ffuf-versions-alt.json \
  -of json

# Merge and display
cat ffuf-versions.json ffuf-versions-alt.json | \
  jq -r '.results[] | "\(.status) \(.url)"'
echo "[FUZZER] API versions found: $(cat ffuf-versions*.json | jq '.results | length' | paste -sd+ | bc)"
```

---

## WORKFLOW 4 — Recursive Discovery on Interesting Paths

When admin, dashboard, or internal paths found, go one level deeper.

```bash
# Run only on interesting paths (admin, internal, debug, config, etc.)
for interesting_path in $(grep -E "admin|internal|debug|config|management|console" \
    ffuf-dirs.json | jq -r '.results[].url' 2>/dev/null); do
  
  ffuf \
    -w $WORDLIST_COMMON \
    -u "${interesting_path}/FUZZ" \
    -fc 404 \
    -rate 20 \
    -t 5 \
    -mc 200,201,301,302,401,403 \
    -o "ffuf-recursive-$(echo $interesting_path | md5sum | cut -c1-8).json" \
    -of json \
    -timeout 10 2>/dev/null
done

echo "[FUZZER] Recursive discovery complete"
```

---

## WORKFLOW 5 — HTTP Method Fuzzing on 405 Responses

405 Method Not Allowed means the endpoint exists — try other methods.

```bash
METHODS="GET POST PUT PATCH DELETE HEAD OPTIONS TRACE CONNECT"
echo "$METHODS" | tr ' ' '\n' > methods-wordlist.txt

# Find 405 responses from directory discovery
cat ffuf-dirs.json | jq -r '.results[] | select(.status == 405) | .url' | \
while IFS= read -r url; do
  ffuf \
    -w methods-wordlist.txt \
    -u "$url" \
    -X FUZZ \
    -fc 405,404 \
    -rate 10 \
    -t 3 \
    -mc 200,201,301,302,401,403 \
    -o "ffuf-methods-$(echo $url | md5sum | cut -c1-8).json" \
    -of json 2>/dev/null
  echo "[FUZZER] Method fuzz on: $url"
done
```

---

## FALSE POSITIVE FILTERING

```bash
# Get baseline response size for 404
baseline_size=$(curl -s -o /dev/null -w "%{size_download}" \
  "${TARGET_URL}/definitely-does-not-exist-12345678")

# Filter results where response size matches 404 baseline (soft 404)
cat ffuf-dirs.json | jq --argjson baseline "$baseline_size" \
  '.results[] | select(.length != $baseline) | .url'
```

---

## OUTPUT SCHEMA

```json
{
  "target": "example.com",
  "discovered_endpoints": [
    {"url": "/api/v2/admin/users", "status": 403, "source": "dir_discovery"},
    {"url": "/api/v1/debug", "status": 200, "source": "api_discovery"}
  ],
  "new_parameters": ["_debug", "test", "admin", "bypass"],
  "api_versions": ["v1", "v2", "v3"],
  "auth_candidates": ["/api/v2/admin/users", "/api/v1/profile"],
  "error_patterns": [],
  "method_bypasses": [
    {"url": "/api/v1/user/delete", "method": "DELETE", "status": 200}
  ]
}
```

---

## DELIVERY FORMAT

```
PARAMETER FUZZER COMPLETE — {TARGET}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Endpoints discovered:  {N}
New parameters found:  {N}
API versions found:    {versions}
Method bypasses:       {N}
Auth-required (403):   {N} → queued for authenticated testing
Zero-auth (200):       {N} → HIGH PRIORITY

→ Expanded endpoint catalog → exploitation phase
→ Auth candidates → authenticated testing
→ Zero-auth 200s → immediate exploitation
```
