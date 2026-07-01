---
name: bft-consensus-audit
description: "BFT consensus implementation security audit skill. Use when: auditing Tendermint/Malachite implementations, analyzing consensus safety/liveness violations, reviewing BFT state machine code, finding spec-to-code gaps in Rust consensus engines. Target: an example organization Malachite (new unpriced program)."
trigger_keywords: "bft consensus, tendermint, malachite, an example organization, consensus safety, consensus liveness, prevote, precommit, polka, proposer, validator set, quorum threshold, 2/3 threshold, vote counting, lock mechanism, wal consensus, consensus state machine, cosmos consensus, cometbft, consensus equivocation, amnesia attack, consensus audit, consensus fuzzing"
version: 1.0
created: 2026-02-26
owner: cyber-operator
pattern_note: "a technique-reference note"
program_targets:
  - "an example organization Malachite (new — unpriced, high research value)"
  - "an example program (consensus-adjacent infrastructure)"
---

# BFT Consensus Audit Skill

> **Target:** an example organization Malachite — new Rust BFT consensus engine (formally specified, freshly implemented)
> **Why valuable:** Brand new codebase, TLA+ spec exists (comparison target), unaudited
> **Reference pattern:** a technique-reference note

---

## Phase 1: Repository Exploration

```bash
# Clone Malachite:
git clone https://github.com/informalsystems/malachite.git
cd malachite
ls -la

# Understand structure:
find . -name "*.rs" | head -50
# Look for: consensus/, engine/, vote/, round/, state_machine/

# Find TLA+ specifications:
find . -name "*.tla" -o -name "*.cfg"
# These are the ground truth — everything must match these

# Identify all state machine files:
grep -rln "State\|Transition\|Phase\|Round\|Height" src/ --include="*.rs"

# Find quorum calculations:
grep -rn "quorum\|2/3\|threshold\|voting_power\|n_validators" src/ --include="*.rs"

# Find unsafe blocks:
grep -rn "unsafe {" src/ --include="*.rs"
```

## Phase 2: Quorum Threshold Verification (Critical Check)

Off-by-one in quorum = safety violation.

```bash
# Find all threshold calculations:
grep -rn "quorum\|threshold\|*2/3\|*2 /\|weight\|voting_power" src/ --include="*.rs" -A 3

# CORRECT threshold: (2 * n / 3) + 1 for simple majority
# Tendermint CORRECT: 2f+1 where n = 3f+1
# WRONG: 2 * n / 3 (integer division rounds down → effectively 2f instead of 2f+1)
# WRONG: (2 * n) / 3 (same issue with integer division order)

# For n=4 (f=1):
# Correct quorum = 3 (prevents Byzantine f=1 from splitting 2+2)
# Wrong quorum = 2 (Byzantine can forge commit with 2 votes)

# Verify: each quorum type (prevote quorum, precommit quorum, nil quorum)
# All must use the same correct formula
```

## Phase 3: Spec-to-Code Tracing

For each major algorithm in the TLA+ spec, find the Rust implementation and verify:

```bash
# Map: TLA+ clause → Rust function

# TLA+ "upon receives 2f+1 <PREVOTE, h, r, v>":
grep -rn "on_prevote\|handle_prevote\|process_prevote" src/ --include="*.rs" -A 20
# Check: does it count correctly? Does it check valid(v)?

# TLA+ "set lockedValue = v":
grep -rn "locked_value\|lock\|set_lock" src/ --include="*.rs" -A 5
# Check: is this persisted to WAL BEFORE proceeding? Race condition?

# TLA+ "schedule timeout(prevote, h, r)":
grep -rn "timeout\|schedule_timeout\|set_timer" src/ --include="*.rs" -A 5
# Check: can timeout duration overflow? Is escalation bounded?

# TLA+ "a validator MUST NOT prevote for different value if locked":
grep -rn "fn.*prevote\|produce_prevote\|create_prevote" src/ --include="*.rs" -A 20
# Check: is the lock state checked before producing prevote?
```

## Phase 4: Vote Deduplication Analysis

```bash
# Find vote storage/tracking:
grep -rn "votes\|vote_set\|vote_count\|seen_votes\|HashMap.*Vote" src/ --include="*.rs" -A 10

# Deduplication key MUST include ALL of:
# (validator_id, height, round, step/phase)
# Missing any component → double-counting possible

# Check for duplicate vote handling:
grep -rn "duplicate\|already_seen\|insert.*return\|contains.*vote" src/ --include="*.rs" -A 5

# Check for equivocation detection:
grep -rn "equivoc\|conflicting\|double_sign" src/ --include="*.rs"
# If missing: equivocation goes undetected/uncounted
```

## Phase 5: Lock/Unlock State Machine

```bash
# Find lock state:
grep -rn "locked\|lock_value\|lock_round\|locked_round" src/ --include="*.rs" -A 5

# Verify unlock condition:
# CORRECT: unlock only when seeing valid polka for DIFFERENT value in LATER round
# Validator can also prevote nil if locked (not required to unlock)
grep -rn "unlock\|clear_lock\|reset_lock" src/ --include="*.rs" -A 10

# Check: lock persisted to WAL before acting:
grep -rn "wal\|write_ahead\|persist\|log_entry" src/ --include="*.rs" -A 10
# Is the sequence: [acquire lock] → [write WAL] → [proceed]?
# Or: [proceed] → [write WAL]? (wrong → crash loses lock)

# Test: lock state after crash recovery
# If WAL incomplete → does validator restart WITHOUT lock? → amnesia
```

## Phase 6: WAL (Write-Ahead Log) Analysis

```bash
# Find WAL implementation:
find . -name "*wal*" -o -name "*write_ahead*" -o -name "*log*" | grep -v ".git"

# Read WAL code:
grep -rn "fn.*wal\|WAL\|WriteAhead" src/ --include="*.rs" -A 15

# Critical checks:
# 1. Is state written to WAL BEFORE acting on it?
# 2. What happens if WAL write fails? (panic? continue anyway?)
# 3. WAL replay on startup: does it correctly restore lock state?
# 4. Corrupted WAL entry: parse error causes consensus violation?

# Check WAL replay:
grep -rn "replay\|recover\|restore.*wal\|wal.*load" src/ --include="*.rs" -A 20
```

## Phase 7: Message Serialization Fuzzing

```bash
# Find message deserialization:
grep -rn "deserialize\|from_bytes\|decode\|parse_message" src/ --include="*.rs" -A 10

# Check for panics on malformed input:
grep -rn "unwrap()\|expect(\|panic!(" src/ --include="*.rs"
# Each unwrap() on network input is a potential panic-DoS

# Set up fuzzing:
cargo install cargo-fuzz
cargo fuzz init

# Create fuzz target for message parsing:
# tests/fuzz/message_parser.rs — deserializes random bytes
cargo fuzz add message_parser
# Edit: call the message parsing function with fuzz input
cargo fuzz run message_parser

# Also fuzz: proposal messages, vote messages, timeout messages
# Check: integer overflow in message size fields (len > allocated buffer)
```

## Phase 8: Timeout Arithmetic Check

```bash
# Find timeout calculations:
grep -rn "timeout\|Duration\|Instant\|sleep\|delay" src/ --include="*.rs" -A 5

# Check for overflow:
# If timeout = base + round * factor:
# At round 1000 → very large timeout (acceptable but slow)
# At round 65535 → potential overflow if u16 arithmetic
# At max round → undefined behavior?

# Check escalation bound:
# Is there a max timeout cap? (prevents infinite wait)
grep -rn "max.*timeout\|timeout.*max\|clamp\|min(.*timeout" src/ --include="*.rs"

# Integer overflow risk (Rust panics in debug, wraps in release):
grep -rn "round.*\*\|timeout.*\*\|height.*\*" src/ --include="*.rs" | grep -v "//.*\*"
# Look for multiplication on round numbers without overflow protection
```

## Phase 9: Property-Based Testing

```rust
// Add to Malachite test suite:
use proptest::prelude::*;

// Property: Safety — two validators can never commit different blocks at same height
proptest! {
    #[test]
    fn safety_no_conflicting_commits(
        messages in generate_message_sequence(4, 1) // n=4, f=1
    ) {
        let (commits_v1, commits_v2) = simulate_two_validators(messages);
        // No honest validator should commit two different blocks at same height
        for height in commits_v1.keys() {
            if let (Some(c1), Some(c2)) = (commits_v1.get(height), commits_v2.get(height)) {
                assert_eq!(c1, c2, "Safety violation at height {}", height);
            }
        }
    }
}

// Property: Lock consistency — locked validator only prevotes for locked block or nil
proptest! {
    #[test]
    fn lock_consistency(messages in generate_message_sequence(4, 1)) {
        let state = simulate_validator(messages);
        // If locked on value V at round R:
        // Then in round R+1: prevote must be V or nil (not a different value)
        // Unless: valid polka for different value seen in R+1
        for prevote in &state.prevotes {
            if state.is_locked_at(prevote.round - 1) {
                let locked = state.locked_value_at(prevote.round - 1);
                let has_polka = state.has_polka_for(prevote.round, &prevote.value);
                assert!(
                    prevote.value == locked || prevote.value.is_nil() || has_polka,
                    "Lock consistency violation"
                );
            }
        }
    }
}
```

## Phase 10: Reporting a Consensus Vulnerability

```markdown
**Title:** [Safety|Liveness|Accountability] violation via [exact mechanism]

**Component:** [vote counting | lock state | WAL | timeout | message parsing]

**TLA+ Spec Reference:**
- Clause: "upon receives 2f+1 <PREVOTE, h, r, v>"
- Expected behavior: [exact description from spec]
- Actual behavior: [what the code does instead]

**Message Sequence to Trigger:**
1. Height H=1, Round R=0
2. Validator V1 (Byzantine) sends <PREVOTE, 1, 0, block_A> to nodes {1,2}
3. Validator V1 (Byzantine) sends <PREVOTE, 1, 0, block_B> to nodes {3,4}
4. [etc.]

**Impact:**
- Two honest validators commit different blocks at height 1
- Safety invariant violated — blockchain fork

**Severity:** Critical (safety violation) / High (liveness) / Medium (DoS)
```

---

## Full Pattern Reference

**Deep methodology:** `a technique-reference note`
**Attack classes:** Equivocation | Amnesia | Timing | Governance/Stake
**Related:** `skills/domains/cyber/l2-bridge-security.md` (bridge consumers of consensus)

---

*BFT Consensus Audit Skill v1.0 | Owner: cyber-operator | Created 2026-02-26*
