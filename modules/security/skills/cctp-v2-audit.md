---
name: cctp-v2-audit
description: "CCTP V2 cross-chain transfer protocol security audit skill. Use when: auditing Circle CCTP, analyzing cross-chain message replay, checking burn-and-mint nonce security, testing finality attack vectors, reviewing attestation verification. Target: Circle CCTP V2."
trigger_keywords: "cctp, cross chain transfer protocol, circle cctp, usdc bridge, burn and mint, cctp v2, cctp replay, message transmitter, token messenger, attestation service, usdc cross chain, cctp nonce, cctp finality, cctp replay attack, circle bridge, native usdc, message replay, cctp audit"
version: 1.0
created: 2026-02-26
owner: cyber-operator
pattern_note: "a technique-reference note"
program_targets:
  - "Circle CCTP V2 (Immunefi/HackerOne) — $5K–$25K ceiling"
  - "Coinbase (an example contract uses CCTP)"
---

# CCTP V2 Audit Skill

> **Target:** Circle CCTP V2 — native USDC burn-and-mint cross-chain bridge
> **Bounty ceiling:** $5K–$25K
> **Critical finding:** Any path to mint USDC without a corresponding burn = unlimited USDC
> **Reference pattern:** a technique-reference note

---

## Phase 1: Contract Discovery

```bash
# CCTP V2 contract addresses (verify on Circle's docs):
# Source: https://developers.circle.com/stablecoins/docs/cctp-protocol-contract

# Ethereum mainnet:
MSG_TRANSMITTER_ETH="0x0a992d191DEeC32aFe36203Ad87D7d289a738F81"
TOKEN_MESSENGER_ETH="0xBd3fa81B58Ba92a82136038B25aDec7066af3155"

# Base mainnet (an OP-Stack L2):
MSG_TRANSMITTER_BASE="0xAD09780d193884d503182aD4588450C416D6F9D4"
TOKEN_MESSENGER_BASE="0x1682Ae6375C4E4A97e4B583BC394c861A46D8962"

# Verify these and find V2 contracts via Circle docs / Etherscan

# Read key state:
RPC="https://eth.llamarpc.com"
cast call $MSG_TRANSMITTER "localDomain()" --rpc-url $RPC
cast call $MSG_TRANSMITTER "nextAvailableNonce()" --rpc-url $RPC
cast call $MSG_TRANSMITTER "signatureThreshold()" --rpc-url $RPC
cast call $MSG_TRANSMITTER "attesterManager()" --rpc-url $RPC
```

## Phase 2: Version Confusion Check

```bash
# V1 message format vs V2:
# Decode the message to understand field layout

# V1 message (version=0):
# bytes4 version + bytes4 sourceDomain + bytes4 destinationDomain +
# bytes8 nonce + bytes32 sender + bytes32 recipient + bytes messageBody

# V2 message (version=1): [check docs for exact format]
# May have additional fields, hooks, fee data

# Can a V1 message be accepted by V2 MessageTransmitter?
# 1. Capture a valid V1 (message, attestation) pair
# 2. Submit to V2 MessageTransmitter.receiveMessage()
# 3. Expected: revert "Invalid version"
# 4. If accepted: does the parsing produce correct fields?
#    (Wrong nonce? Wrong amount? Wrong recipient?)

# Can a V2 message's version byte be changed to 0?
# 1. Create a valid V2 message
# 2. Change bytes 0-3 from version=1 to version=0
# 3. Submit → does V2 contract parse it as V1?
# 4. If yes: field misalignment → can manipulate amount/recipient

# Test: submit message with version=255 (unknown version)
# Expected: revert; actual: if accepted with wrong field parsing → vulnerability
```

## Phase 3: Nonce Security Analysis

```bash
# Check nonce type:
cast call $MSG_TRANSMITTER "nextAvailableNonce()" --rpc-url $RPC
# Note: uint64 is safe (18.4Q); uint32 (4.3B) is exhaustible

# Check nonce hash computation:
# Read contract source, find usedNonces mapping and how key is computed
# CORRECT: keccak256(abi.encodePacked(sourceDomain, nonce))
# ABI-encoded ensures no collision between (1, 23) and (12, 3)
# STRING-concat would be vulnerable: "1" + "23" = "123" = "12" + "3"

# Check nonce marked before vs after external calls:
# Find receiveMessage() in source
# Order must be: [verify attestation] → [check nonce] → [MARK nonce used] → [external mint call]
# If nonce marked AFTER mint: reentrancy possible → replay within same tx

# Test same-chain replay:
# 1. Execute a legitimate receiveMessage()
# 2. Immediately call receiveMessage() with same (message, attestation)
# Expected: revert "Nonce already used"

# Test cross-chain replay:
# 1. Capture valid (message, attestation) for destination = domain 0 (Ethereum)
# 2. Submit to domain 6 (Base) MessageTransmitter
# Expected: revert "Invalid destination domain"
```

## Phase 4: Attestation Verification Analysis

```bash
# Read signatureThreshold:
cast call $MSG_TRANSMITTER "signatureThreshold()" --rpc-url $RPC

# List all enabled attesters:
# Need to find the event logs for AttesterEnabled/AttesterDisabled
cast logs \
  --from-block 0 \
  --to-block latest \
  --address $MSG_TRANSMITTER \
  "AttesterEnabled(address)" \
  --rpc-url $RPC

# Check: is signatureThreshold() set to require multiple attesters?
# If threshold=1 but multiple attesters exist → single attester compromise = critical

# Signature malleability check:
# In ECDSA, for every valid (r, s) signature, (r, -s mod n) is also valid
# Does the contract check s <= n/2 (low-s)?
# Search for: ecrecover, SignatureChecker, ECDSA.recover
grep -n "ecrecover\|ECDSA\|SignatureChecker" source.sol

# Attester rotation attack:
# During rotation, old attester still valid?
# 1. When was the last attester rotation? (logs)
# 2. Can an old (pre-rotation) attestation still be used?
# 3. Does the rotation atomically invalidate all old attestations?
cast logs \
  --from-block 0 \
  --to-block latest \
  --address $MSG_TRANSMITTER \
  "AttesterManagerUpdated(address,address)" \
  --rpc-url $RPC
```

## Phase 5: Finality Window Attack (L2 Focus)

```bash
# Check which finality level Circle waits for on Base/Arbitrum:
# This is OFF-CHAIN in Circle's attestation service
# Look for: Circle's developer docs, any public commitments on confirmation depth

# For Base (Optimistic Rollup):
# L2 has 3 finality levels:
#   1. Sequencer confirmation (~2s) ← RISKY if attested here
#   2. L1 batch submission (~minutes)
#   3. Challenge period completion (7 days) ← TRUE finality

# Test: Can you construct a scenario where:
# 1. Burn in L2 block N
# 2. Attestation service attests based on L2 confirmation
# 3. Destination mints
# 4. L2 state is challenged + rolled back
# → burn reversed, mint stands

# Practical test (on testnets):
# 1. Use Sepolia + Base Sepolia
# 2. Submit burn on Base Sepolia
# 3. Get attestation ASAP (before L1 batch)
# 4. Check if mint succeeds on Sepolia
# 5. Force rollback on Base Sepolia (requires fault proof mechanism)
# OR: Check if attestation is even issued before L1 confirmation (read Circle API docs)

# Find Circle's attestation API:
# https://iris-api.circle.com/attestations/{messageHash}
# Check: when does this return a signature? At L2 soft finality or L1 batch?
```

## Phase 6: Reorg Double-Spend Test

```bash
# Monitor source chain for reorg conditions:
# Use eth_subscribe newHeads or block polling to detect competing blocks

# Test scenario (on testnets only):
# 1. Submit burn on testnet source chain
# 2. Claim attestation immediately
# 3. Submit mint on destination (valid attestation, nonce consumed)
# 4. Submit SECOND burn on source chain (gets a NEW nonce)
# 5. Wait for Circle to attest second burn
# 6. Claim SECOND mint (different nonce → different hash → passes nonce check)
# Result: 2x mints for 1 effective burn (first burn may be in canonical chain too)

# This is the "timing race" version (not requiring actual reorg)
# True reorg variant requires:
# 1. Burn in block N (fork A)
# 2. Circle attests based on fork A
# 3. Fork A abandoned → fork B wins → burn not in canonical chain
# 4. Mint claimed on destination
# 5. User got USDC for free (burn was on abandoned fork)
```

## Phase 7: Hook Reentrancy (CCTP V2 Specific)

```bash
# If V2 introduces pre/post hooks on receive:
grep -n "hook\|callback\|beforeReceive\|afterMint\|onReceive" source.sol

# Reentrancy check:
# Does the hook execute BEFORE or AFTER nonce is marked used?
# If hook executes → hook calls receiveMessage() → nonce not yet marked → double-mint

# Check for reentrancy guard:
grep -n "nonReentrant\|ReentrancyGuard\|_status\|ENTERED\|NOT_ENTERED" source.sol
# If missing on functions that execute hooks → test reentrancy

# Foundry reentrancy test:
# Deploy a malicious hook that calls receiveMessage() with same message
# Submit it as the hook for a CCTP V2 transfer
# Check if second call succeeds before first nonce marking
```

## Phase 8: Upgrade Vector (Proxy Analysis)

```bash
# If CCTP contracts are upgradeable (UUPS or Transparent):
# → Run full UUPS audit (see uups-proxy-audit.md skill)

# Quick check:
cast storage $MSG_TRANSMITTER \
  0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc \
  --rpc-url $RPC
# If non-zero → UUPS proxy (implementation is at that address)

cast call $MSG_TRANSMITTER "implementation()" --rpc-url $RPC 2>/dev/null
# If returns address → TransparentUpgradeableProxy
```

## Phase 9: PoC Template for Replay Finding

```bash
# Title: Same-Chain Replay: CCTP MessageTransmitter Allows Double-Mint of USDC

# Steps:
# 1. Monitor source chain for MessageSent events
# 2. Capture: (message_bytes, attestation) for any transfer
# 3. Submit receiveMessage(message, attestation) on destination → success
# 4. Immediately submit same receiveMessage(message, attestation) →

# Expected: revert "Nonce already used"
# Actual: (if vulnerable) second tx succeeds

# Evidence:
# - Source chain tx hash (burn)
# - Destination chain tx #1 (first mint)
# - Destination chain tx #2 (second mint — should fail, but succeeds)
# - USDC balance change showing 2x minting for 1x burn

# Severity: Critical — unlimited USDC minting
```

## Severity Guide

| Finding | Severity | Bounty Range |
|---------|---------|-------------|
| Same-chain replay (double-mint) | Critical | $25K+ |
| Reorg double-spend (2x mint for 1 burn) | Critical | $15K–$25K |
| Cross-chain replay | Critical | $15K–$25K |
| Version confusion causing field misalignment | Critical | $10K–$25K |
| Reentrancy in hook execution before nonce mark | Critical | $10K–$25K |
| Nonce encoding collision | High | $5K–$15K |
| Attestation threshold bypass | Critical | $25K+ |
| Single attester (threshold=1) | Medium | $2K–$5K |
| Finality window too short for L2 | High | $5K–$15K |

---

## Full Pattern Reference

**Deep methodology:** `a technique-reference note`
**Architecture:** Burn → Attest (off-chain) → Mint
**Related:** `skills/domains/cyber/uups-proxy-audit.md` | `skills/domains/cyber/l2-bridge-security.md`

---

*CCTP V2 Audit Skill v1.0 | Owner: cyber-operator | Created 2026-02-26*
