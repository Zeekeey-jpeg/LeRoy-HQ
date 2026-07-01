---
name: mpc-cryptography
description: "MPC (Multi-Party Computation) cryptography audit methodology for authorized security research. Covers: threshold ECDSA fundamentals (t-of-n key distribution, why no single party holds the key), GG20 protocol (Paillier encryption, MtA sub-protocol, range proof attacks, abort-based extraction), CGGMP21 protocol (identifiable abort, Fiat-Shamir transcript binding, auxiliary parameter verification), nonce-related attacks (nonce reuse key recovery equations, nonce bias lattice attacks, 4-bit bias → 64 signatures for recovery), implementation vulnerabilities (big integer arithmetic, EC point validation, constant-time requirements, serialization), cb-mpc audit checklist (16-point), and vulnerability report structure for MPC findings (Critical severity ceiling)."
trigger_keywords: "mpc, multi-party computation, threshold ecdsa, threshold signature, tss, gg20, cggmp21, paillier, mta protocol, multiplicative to additive, nonce bias, nonce reuse, key share, key extraction, lattice attack, fiat-shamir transcript, range proof, zkp mpc, zero knowledge mpc, cb-mpc, mpc audit, alpha rays, nonce reuse ecdsa, hidden number problem, mpc cryptography"
version: 1.0
---

# MPC Cryptography — Audit Methodology

## Purpose

Audit methodology for threshold ECDSA implementations. High-value Critical ceiling on crypto-native bug bounty programs. Requires mathematical precision in reports.

---

## Threshold ECDSA Fundamentals

```
Standard ECDSA: Single private key x → single point of failure
  Sign(x, m) → (r, s)

Threshold ECDSA (t-of-n):
  Key shares x₁, x₂, ..., xₙ — distributed across n parties
  Any t parties cooperate → valid signature (r, s)
  Fewer than t parties → cannot sign, cannot reconstruct x
  No single party ever holds the full key x

Common: 2-of-3, 3-of-5, t-of-n
```

**ECDSA internals (key for understanding attacks):**

```
Sign(x, m):
  1. Choose random nonce k ∈ [1, n-1]
  2. R = k·G → r = R.x mod n
  3. s = k⁻¹ · (H(m) + r·x) mod n

CRITICAL: if you know k → x = (s·k - H(m)) · r⁻¹ mod n
CRITICAL: if k reused → two signatures with same r → full key recovery
```

---

## GG20 Protocol Attack Surface

**Attack 1 — Paillier Modulus Validation (missing/weak ZK proofs):**

```
Required verifications on each party's Paillier modulus N:
  □ N is a product of two safe primes (Πmod proof)
  □ N > 2^2048 (size check)
  □ gcd(N, φ(N)) = 1
  □ Factors p, q are safe (p = 2p' + 1)

If skipped → malicious party generates N with known factorization
           → MtA protocol leaks honest party's key share
```

**Attack 2 — MtA Range Proof (Alpha-Rays class):**

```
MtA protocol (converts multiplicative shares to additive):
  Alice has secret a, Bob has secret b
  Alice sends Enc(a), Bob computes Enc(a·b + β) homomorphically
  Without range proofs:
    → Bob sends β' outside expected range → overflow reveals bits of a
    → ~256 signing sessions → full key share recovery

  The Alpha-Rays attack (Fireblocks, 2023) demonstrated this exactly.
```

**Attack 3 — Abort Identification (information leakage per abort):**

```
GG20 lacks robust abort identification:
  Malicious party sends crafted invalid messages → protocol aborts
  Honest party's pre-abort response leaks ~1 bit per abort
  After O(n) aborts → enough information for key share recovery
  Aborts are not penalized → free repeated attempts
```

---

## CGGMP21 Protocol Attack Surface

**Attack 1 — Fiat-Shamir Transcript Binding:**

```
Correct FS challenge must include ALL of:
  Hash(session_id, party_id, public_parameters, statement, commitment)

Missing session_id → proofs replayable across sessions
Missing party_id  → proofs transferable between parties
Missing any param → proof malleability or forgery

Look in code for: Hash(N, s, t, ...) missing sid/pid
```

**Attack 2 — ZK Proof Implementation Errors:**

```
Πmod (proves N is a biprime):
  □ Verifier checks N > 2^2048 (size check)
  □ Proof elements in correct groups
  □ All public inputs in FS hash

Πfac (proves N has two large factors):
  □ Proof freshly generated (not replayed)
  □ Session-bound

Πaff-g (affine operation range proof in MtA):
  □ Range bounds tight (loose bounds → overflow attacks)
  □ All commitments in challenge
```

**Attack 3 — Auxiliary Parameter Verification:**

```
Ring-Pedersen parameters (N̂, s, t) — used for range proofs
Required verifications per party:
  □ N̂ is valid RSA modulus (Πmod)
  □ s, t are generators of Z*_N̂ (Πprm)
  □ N̂ ≠ N (must differ from Paillier modulus)
  □ N̂ > 2^2048

If skipped → malicious party with known N̂ factorization can forge
range proofs → MtA overflow → key share extraction
```

---

## Nonce-Related Attacks

### Nonce Reuse — Immediate Key Recovery

```
Two signatures with same k → same r value (detectable on-chain)

s₁ - s₂ = k⁻¹ · (H(m₁) - H(m₂)) mod n
k = (H(m₁) - H(m₂)) · (s₁ - s₂)⁻¹ mod n
x = (s₁·k - H(m₁)) · r⁻¹ mod n

Detection: Look for duplicate r values in signature history
```

### Nonce Bias — Lattice Attack

```
Hidden Number Problem: if top b bits of every nonce known/zero:

  4 bits of bias → ~64 signatures needed for key recovery
  2 bits of bias → ~128 signatures
  1 bit of bias  → ~256 signatures

Tools: Minerva, TPM-FAIL lattice attack framework

Sources of bias in MPC:
  □ Rejection sampling implemented incorrectly
  □ Modular reduction without bias correction
  □ PRNG seeded with insufficient entropy
  □ RFC 6979 deterministic nonce with implementation bug
```

### Nonce Generation Checks

```
Correct nonce generation (rejection sampling):
  WRONG: k = random_bytes(32) % n  ← biased toward low values
  RIGHT: loop { k = random_bytes(32); if k ∈ [1, n-1] return k; }

In MPC pre-signing:
  □ Pre-signing data is single-use (replay protection)
  □ Nonce freshness enforced (no reuse across sessions)
  □ Additive shares sum to uniformly random value
```

---

## Implementation Vulnerability Checklist

```
Big Integer Arithmetic:
  □ Modular reduction doesn't overflow integer types
  □ Leading zero handling consistent (fixed-length encoding)
  □ Modular inverse handles k=0, k=n edge cases
  □ All arithmetic in constant time (no secret-dependent branches)

EC Point Operations:
  □ Every received EC point validated: y² = x³ + ax + b (mod p) AND ≠ identity
  □ Small-subgroup attack prevention (point order check)
  □ Invalid curve attacks: checked with on-curve test

Serialization/Deserialization:
  □ Buffer overflow: message length vs actual data
  □ Type confusion: EC point vs big integer
  □ Malformed curve points rejected before use
  □ Duplicate message detection (prevents nonce reuse via replay)

Constant-Time Requirements:
  □ No branches on secret values
  □ No memory access patterns dependent on secrets
  □ Paillier decryption runs in constant time
```

---

## cb-mpc Specific Audit Checklist (16 points)

```
Source: an open-source C++ MPC library

ZK Proofs:
  □ Πmod verification complete (all checks present)
  □ Πfac verification complete
  □ Πaff-g range bounds tight (no overflow bypass)
  □ Πprm for auxiliary parameters

Paillier:
  □ Safe prime generation verified
  □ Modulus size ≥ 2048 bits
  □ N̂ ≠ N enforced

Nonce:
  □ CSPRNG used (not rand() or math/rand)
  □ Correct rejection sampling (not biased % n)
  □ Pre-signing data single-use (session binding)

EC Operations:
  □ Point on curve validated before use
  □ Identity point handled

Session Binding:
  □ session_id in ALL Fiat-Shamir hashes
  □ party_id in ALL Fiat-Shamir hashes

Memory (C++):
  □ Buffer sizes derived from message fields validated before allocation
  □ Error handling on malformed input (crash → DoS vector)
```

---

## MPC Vulnerability Report Structure

```
Title: [Protocol phase] [vulnerability type] in [component]
Example: "Missing session_id in Πaff-g Fiat-Shamir hash enables
range proof replay across signing sessions"

Severity:
  Full key extraction:              Critical
  Partial key share leakage:        High
  DoS via abort manipulation:       Medium
  Information disclosure (no key):  Medium

Required sections:
  1. Specification reference (line/equation in CGGMP21 paper)
  2. Implementation deviation (file:line in the target library)
  3. Exploit construction:
     - Bits leaked per session
     - Total bits to recover: 256 (secp256k1 key share)
     - Sessions required for full recovery
     - Practical exploitation assessment
  4. Concrete attack equations (mathematical precision required)

Example impact calculation:
  - 4 bits leaked per session (MtA overflow without range proof)
  - 256 total bits → 64 signing sessions needed
  - Active wallet: 64 signatures typical → PRACTICAL
```

---

## Phase-by-Phase Audit Approach

```
Phase 1 — Architecture mapping:
  spec → code: Key gen / Pre-signing / Signing / ZK proofs

Phase 2 — Critical path review (priority order):
  1. ZK proof verification functions
  2. MtA protocol + range proofs
  3. Nonce generation + replay protection
  4. Fiat-Shamir transcript completeness
  5. Big integer arithmetic edge cases
  6. Serialization / deserialization
  7. EC point operations + validation
  8. Paillier encryption/decryption

Phase 3 — Differential analysis:
  Compare against: tss-lib (Binance Go), multi-party-ecdsa (ZenGo Rust)
  Every deviation from spec = potential vulnerability

Phase 4 — Attack construction (for each finding):
  Mathematical proof → PoC equations → session count calculation
```

---

## Quick Commands

```bash
# Collect signatures for nonce analysis (from blockchain):
cast tx 0xTXHASH --rpc-url https://mainnet.base.org

# Check for duplicate r values (nonce reuse detection):
python3 -c "
import json, sys
sigs = [...]  # list of (r, s) tuples from blockchain
r_vals = [r for r,s in sigs]
if len(r_vals) != len(set(r_vals)):
    print('DUPLICATE R VALUES — NONCE REUSE DETECTED')
"

# Verify ECDSA signature:
python3 -c "
from ecdsa import SECP256k1, VerifyingKey, keys
# ... signature verification
"
```

*Crypto-Native reference | Threshold-signature audit methodology*
