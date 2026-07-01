# AI CTF Methodology

**Owner:** ai-sec-agent
**Purpose:** AI-themed CTF categories, challenge approaches, platform-specific guidance

---

## AI CTF Categories

### Category 1: Prompt Injection Challenges
**Description:** Extract hidden information from an LLM through prompt manipulation.

**Common Platforms:**
- gandalf.lakera.ai (progressive levels)
- CTF competitions with AI assistant challenges
- Hack The Box AI challenges

**Approach:**
```
1. Interact with the AI to understand its purpose and restrictions
2. Identify what it's protecting (password, flag, secret)
3. Apply injection taxonomy from ai-prompt-injection.md
4. Start simple → escalate complexity
5. Document successful technique
```

---

### Category 2: Jailbreak Challenges
**Description:** Cause an AI to violate its stated restrictions.

**Common Objectives:**
- Get AI to output prohibited content
- Cause AI to ignore specific rules
- Exploit system prompt weaknesses

**Approach:**
```
1. Map all restrictions (what it refuses)
2. Identify restriction mechanism (keyword filter? context-aware? output filter?)
3. Design bypass specific to mechanism type
4. Test and iterate
```

---

### Category 3: AI-Assisted Traditional CTF
**Description:** Standard CTF categories (crypto, forensics, rev) where AI/ML is the tool.

**Examples:**
- Cryptographic cipher breaking with frequency analysis
- Image steganography with ML detection
- Malware classification reversal

**Approach:**
```
1. Classify the underlying technique (crypto, forensics, etc.)
2. Identify AI/ML component and its role
3. Apply domain knowledge + AI manipulation
```

---

### Category 4: Model Extraction / Inversion
**Description:** Infer training data or model structure through black-box queries.

**Techniques:**
- Membership inference: "Was [data point] in training data?"
- Model inversion: Infer training data from model behavior
- Attribute inference: Infer properties of training data

**Only test on:** CTF lab models explicitly designed for this testing.

---

### Category 5: Adversarial Examples (Image/Text)
**Description:** Craft inputs that cause AI classifiers to misclassify.

**Examples:**
- Image perturbations invisible to human eye that fool classifier
- Text adversarial attacks that change sentiment classification
- Bypass AI content filters

**Tools (in CTF environments):**
- Crafted pixel modifications
- Text substitutions that preserve meaning but fool classifier

---

## Gandalf-Specific Strategy

See detailed protocol in `ai-prompt-injection.md`. Summary:

```
Level 1-2: Direct techniques (just ask)
Level 3-4: Rephrase + context shift
Level 5-6: Role-play + indirect approach
Level 7-8: Token manipulation + character-by-character extraction
```

---

## AI CTF Resource Map

| Resource | Type | What For |
|----------|------|---------|
| gandalf.lakera.ai | Live challenge | Prompt injection practice |
| Lakera's Guard blog | Educational | Injection defense context |
| OWASP LLM Top 10 | Reference | Vulnerability taxonomy |
| AI Village CTF (DEF CON) | Archive | Past AI CTF challenges |
| HackTheBox AI labs | Labs | AI-themed challenges |

---

## Writeup Storage

All AI CTF writeups → `notes/research/AI-Security/`

For Gandalf specifically:
```
notes/research/AI-Security/Gandalf/
├── level-1-writeup.md
├── level-2-writeup.md
├── ...
└── techniques-learned.md    ← Cumulative technique library
```

---

*AI CTF Methodology v1.0 | ai-sec-agent | Authorized platforms only | 2026-02-23*
