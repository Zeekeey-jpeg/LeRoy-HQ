---
user-invocable: false
---

# Hacker101 CTF Guide

**Owner:** cyber-operator
**Purpose:** Hacker101 CTF progression guide — HackerOne's free training platform

---

## About Hacker101

Hacker101 is HackerOne's free educational platform for bug bounty hunters. CTF challenges award points that unlock private bug bounty programs. Solving challenges = earning invitations to exclusive programs.

**URL:** hacker101.com
**Points system:** Each solved challenge awards points toward private program invitations

---

## Challenge Categories

| Category | Hacker101 Focus | Difficulty |
|----------|----------------|-----------|
| Web | IDOR, XSS, SQLi, Auth bypass | Easy → Hard |
| Android | APK reversing, insecure storage | Medium → Hard |
| Cryptography | Basic crypto, encoding | Easy → Medium |
| Miscellaneous | Steganography, encoding puzzles | Easy → Medium |

---

## Progression Strategy

### Stage 1: Warm Up (Easy Challenges)
**Target:** First 100 points
**Challenges to start with:**
- A Little Something to Get You Started (5 pts) — HTML source inspection
- Postbook (multiple flags, 20-50 pts) — IDOR walkthrough
- Micro-CMS v1 (flags 1-4) — XSS + SQLi

**Why these first:**
- Build confidence with simpler techniques
- Earn first private program invitations quickly
- Learn the Hacker101 platform layout

### Stage 2: Core Skills (Medium Challenges)
**Target:** 100-300 points
**Focus:** Master web fundamentals before moving to specialty areas
- Complete all Web challenges in Medium difficulty
- Attempt Petshop Pro for business logic
- Tackle Cody's First Blog for auth bypass

### Stage 3: Specialist Skills (Hard Challenges)
**Target:** 300+ points
**Focus:** Complex exploit chains and Android reversing
- Encrypted Pastebin — crypto + web chain
- Photo Gallery — file upload bypass
- H1 Thermostat — IoT / embedded

---

## Challenge Approach Protocol

### Session Team (ALWAYS — no solo work)

**CRITICAL: Spawn ALL three background agents as the FIRST action on any whitehat/hacker101 trigger — before browser, before reading challenge, before anything else. No exceptions.**

| Agent | Role | When |
|-------|------|------|
| `analyst` | Vault reads, strategy, technique selection | IMMEDIATE on trigger |
| `general-purpose` | Counter-hypotheses, alternate attack vectors | IMMEDIATE on trigger |
| `secretary` | Real-time vault updates, writeup capture | IMMEDIATE on trigger |
| Main convo | Playwright controller (sole browser operator) | IMMEDIATE on trigger |

**Spawn order:** All three background agents in a single parallel Task call → THEN open browser.

### Attack Loop
```
1. Spawn team → begin enumeration in parallel
2. READ challenge description carefully
3. CLICK through entire app before exploiting
4. IDENTIFY flag count
5. Receive team analysis → COO synthesizes → execute
6. FLAG CAPTURED → STOP → session summary → vault update → team for next flag
7. HINTS: absolute last resort only (see session-workflow.md for full policy)
8. DOCUMENT: every significant finding, not just flags
```

---

## Common Hacker101 Vulnerability Patterns

| Challenge Pattern | Vulnerability | Technique |
|------------------|--------------|-----------|
| Hidden page in source | Information disclosure | View source, check comments |
| Admin panel accessible | Auth bypass / missing auth | Try /admin directly |
| Sequential numeric IDs | IDOR | Change your ID to others |
| Input reflected back | XSS | Test `<script>alert(1)</script>` |
| Login form | SQLi | Try `' OR 1=1--` |
| File upload | Unrestricted upload | Try .php, .phtml extensions |
| Template output | SSTI | Try `{{7*7}}` |

---

## Flag Format

Hacker101 flags look like: `^FLAG^[hash]$FLAG$`

Some challenges produce multiple flags. Collect all before submitting.

---

## Point Thresholds for Private Programs

| Points | Access |
|--------|--------|
| 26 | First private program invitation |
| 50+ | More exclusive programs |
| 100+ | High-value programs |
| 200+ | Elite programs |

---

## Writeup Storage

`notes/ctf/` → create `Hacker101/` subfolder

```
notes/ctf/Hacker101/
├── {challenge-name}.md
└── progress.md
```

---

*Hacker101 Guide v1.0 | cyber-operator | hacker101.com authorized platform | 2026-02-23*
