---
name: l2-bridge-security
description: "Base L2 / OP Stack bridge security audit methodology for authorized research. Covers: OP Stack architecture (OptimismPortal, L2OutputOracle, L1/L2 CrossDomainMessenger, L1/L2StandardBridge, L2ToL1MessagePasser, sequencer, op-proposer, op-challenger), security model and trust assumptions (sequencer can censor but not steal, 7-day withdrawal challenge window), deposit flow attack surface (gas limit manipulation, reentrancy, message replay), withdrawal flow attack surface (forged outputRoot, Merkle proof forgery, withdrawal replay, timestamp manipulation, cross-domain message integrity), bridge contract audit checklist (14 points), sequencer role and limitations (MEV/censorship vs fund theft boundary), fault proof system (bisection game, op-challenger, bond economics), L2 predeploy contracts (0x4200...0007/0010/0015/0016), Foundry/Slither/Mythril/Echidna toolchain."
trigger_keywords: "l2 bridge, op stack, optimism bridge, base l2, optimistic rollup, l2 withdrawal, withdrawal proof, optimismportal, l2outputoracle, crossdomainmessenger, l2standardbridge, l2tol1messagepasser, sequencer, op-proposer, op-challenger, fault proof, dispute game, bisection game, outputroot, merkle proof withdrawal, l2 security, bridge contract, base bridge, base hack, rollup security, predeploy contract, l1 l2 message, deposit flow, finalize withdrawal, prove withdrawal"
version: 1.0
created: 2026-02-25
owner: cyber-operator
---

# Base L2 / OP Stack Bridge Security

## Purpose

Audit methodology for OP Stack bridge contracts and sequencer infrastructure. Applies to OP-Stack based bridges.

---

## OP Stack Architecture

```
L1 (Ethereum):
├── OptimismPortal.sol — Entry/exit for L1↔L2 messages
│   ├── depositTransaction() — L1→L2 deposits
│   └── proveWithdrawal() / finalizeWithdrawal() — L2→L1 exits
├── L1CrossDomainMessenger.sol — Higher-level messaging
├── L1StandardBridge.sol — ETH + ERC20 bridge
├── L2OutputOracle.sol — Accepts L2 state root proposals
└── DisputeGameFactory.sol — Fault proof dispute games

L2 (Base):
├── Sequencer — Orders txs, produces blocks, submits batches to L1
├── L2CrossDomainMessenger — Predeploy: 0x4200000000000000000000000000000000000007
├── L2StandardBridge        — Predeploy: 0x4200000000000000000000000000000000000010
├── L1Block                 — Predeploy: 0x4200000000000000000000000000000000000015
└── L2ToL1MessagePasser     — Predeploy: 0x4200000000000000000000000000000000000016
    └── initiateWithdrawal() — start L2→L1 withdrawal

Off-chain:
├── op-node — derives L2 chain from L1 data
├── op-batcher — batches + submits L2 tx data to L1
├── op-proposer — proposes L2 state outputs to L1
└── op-challenger — challenges invalid proposals
```

---

## Security Model (Trust Assumptions)

```
Sequencer CAN:  order txs, censor, extract MEV, cause temporary downtime
Sequencer CANNOT: forge txs (needs user sig), steal funds (bridge is L1)

User bypass for censorship:
  → Submit directly to L1 via depositTransaction() — sequencer cannot block

At least one honest verifier must exist and actively challenge
Challenge window: 7 days (time to identify and challenge invalid state)
Bridge contracts on L1 = ultimate security boundary
```

---

## Deposit Flow (L1 → L2)

```
User calls L1StandardBridge.depositETH() →
  → messenger.sendMessage(l2Bridge.finalizeBridgeETH) →
  → OptimismPortal.depositTransaction() →
  → Emits TransactionDeposited event →
  → L2 sequencer includes deposit tx in next block
```

**Deposit attack vectors:**

```
1. Gas limit manipulation:
   _minGasLimit too low → deposit reverts on L2
   → Funds locked in L1 bridge but not credited on L2
   → Check: is there a recovery mechanism for failed L2 execution?

2. Reentrancy:
   → Does bridge call external contracts before updating state?
   → Is msg.value processed before or after the cross-domain message?

3. Message replay:
   → Can the same deposit nonce be processed twice on L2?
   → Check: nonce management in CrossDomainMessenger
```

---

## Withdrawal Flow (L2 → L1) — Highest Value Attack Surface

```
Step 1 — Initiate (on L2):
  User → L2StandardBridge.withdraw()
  → L2ToL1MessagePasser.initiateWithdrawal()
  → Emits MessagePassed with withdrawal hash

Step 2 — Proposer submits output (on L1):
  op-proposer → L2OutputOracle.proposeL2Output(outputRoot, l2BlockNumber)
  outputRoot = keccak256(version, stateRoot, messagePasserStorageRoot, l2BlockHash)

Step 3 — Prove withdrawal (on L1):
  User → OptimismPortal.proveWithdrawal(withdrawalTx, l2OutputIndex, outputRootProof)
  → Verifies Merkle proof: withdrawal hash ∈ L2ToL1MessagePasser storage
  → Starts 7-day challenge period

Step 4 — Finalize (on L1, after 7 days):
  User → OptimismPortal.finalizeWithdrawal(withdrawalTx)
  → Checks: challenge period elapsed, no successful challenge
  → Executes: sends ETH/tokens to user
```

**Withdrawal attack vectors:**

```
1. Forged outputRoot:
   → Malicious proposer submits outputRoot committing to fake L2 state
   → Attacker proves withdrawal against this fake state → drains bridge
   → Mitigation: fault proof system
   → Vulnerability: if challenger is offline during 7-day window
   → Or: if fault proof VM has execution divergence from L2

2. Merkle Proof Forgery:
   → Can the proof verification be tricked with a crafted proof?
   → Check: is Merkle Patricia Trie verification correct?
   → Check: is the storage layout assumption correct?
   → Check: hash collision exploitation

3. Withdrawal Replay:
   → Can the same withdrawal be finalized twice?
   → Check: finalizedWithdrawals mapping updated ATOMICALLY before funds transfer
   → Check: reentrancy during finalization

4. Timestamp Manipulation:
   → Challenge period uses block.timestamp
   → L1 miners: ±15 second window
   → Check: challenge period strictly > 7 days (boundary conditions)

5. Cross-domain message encoding:
   → Type confusion: ETH vs ERC20 withdrawal
   → Integer overflow in withdrawal amount
   → Decoding mismatch between L2 encoding and L1 decoding
```

---

## Bridge Contract Audit Checklist

```
For each bridge contract:
  □ Reentrancy guards on all state-changing external functions
  □ Access control on admin functions (pause, upgrade) — who and timelock?
  □ Integer overflow/underflow in amount calculations
  □ Merkle proof verification correctness (Patricia Trie implementation)
  □ Nonce management prevents message replay
  □ Upgrade proxy: who can upgrade? timelock? storage collision check?
  □ Initialization: can contracts be re-initialized?
  □ Cross-domain message encoding/decoding consistency (L1 ↔ L2)
  □ Gas limit handling for cross-domain messages (failed L2 execution recovery)
  □ ETH value: msg.value vs parameter amount (one should match the other)
  □ ERC20: approval before transfer, return value checked
  □ finalizedWithdrawals mapping updated before external call (reentrancy)
  □ Challenge period boundary: strictly >, not >=
  □ L1Block predeploy: setL1BlockValues() — who can call? Spoofable?
```

---

## Fault Proof System

```
Flow:
  1. Proposer submits outputRoot for L2 block N
  2. Challenger disagrees → creates dispute game (DisputeGameFactory)
  3. Bisection game: narrow disagreement to a single L2 instruction
  4. On-chain execution: single instruction executed in fault proof VM
     (op-program running on MIPS/RISC-V)
  5. Result determines winner; loser loses bond

Attack surfaces on fault proof:
  □ Fault proof VM divergence from actual L2 execution
    → VM produces different result → honest challenger cannot win
  □ Bisection game edge cases at block boundaries
  □ Bond economics: cost to challenge large withdrawal vs bond size
    → If bond > attacker's steal amount, rational challengers won't challenge
  □ Time constraints: can a challenge complete within 7 days?
    → Deliberate delay tactics by malicious proposer
```

---

## Sequencer Testing

```
Public endpoints:
  https://mainnet.base.org (public)
  https://goerli.base.org (testnet)

OP Stack specific RPC methods:
  curl -X POST https://mainnet.base.org -d '{"jsonrpc":"2.0","method":"optimism_outputAtBlock","params":["latest"],"id":1}'
  curl -X POST https://mainnet.base.org -d '{"jsonrpc":"2.0","method":"optimism_syncStatus","params":[],"id":1}'
  curl -X POST https://mainnet.base.org -d '{"jsonrpc":"2.0","method":"optimism_rollupConfig","params":[],"id":1}'

Admin method check (should be disabled):
  → See ethereum-json-rpc.md for full enumeration script

Rate limiting test:
  for i in $(seq 1 100); do
    curl -s -o /dev/null -w "%{http_code} %{time_total}s\n" -X POST \
      https://mainnet.base.org -d '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":'$i'}'
  done
```

---

## Toolchain

```bash
# Read bridge contract state:
cast call 0xOPTIMISM_PORTAL "l2OutputOracle()" --rpc-url https://eth.llamarpc.com
cast rpc optimism_outputAtBlock 0x1 --rpc-url https://mainnet.base.org
cast storage 0xCONTRACT 0xSLOT --rpc-url https://mainnet.base.org

# Static analysis:
slither contracts/OptimismPortal.sol --detect reentrancy-eth,arbitrary-send-eth
# Symbolic execution:
myth analyze contracts/L1StandardBridge.sol --solv 0.8.15
# Fuzzing:
echidna contracts/L1Bridge.sol --config echidna.yaml
```

| Tool | Purpose |
|------|---------|
| Foundry (forge, cast, anvil) | Contract dev, testing, RPC interaction |
| Slither | Solidity static analysis |
| Mythril | EVM symbolic execution |
| Echidna | Property-based fuzzing |
| Etherscan / Basescan | On-chain contract + tx analysis |

*Crypto-Native Batch CN-3 | ingested 2026-02-25 | Target: OP-Stack bridges*
