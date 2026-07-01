---
context: fork
---

# CTF Methodology

**Owner:** cyber-operator
**Purpose:** CTF category taxonomy, per-category approach checklists, challenge intake protocol

---

## Challenge Intake Protocol

0. **RECALL — Do this FIRST, every time:**
   - Check `notes/ctf/techniques-learned.md` — what worked/failed on same category?
   - Check `notes/ctf/{Platform}/` — any prior writeup for this challenge?
   - Check `a technique-reference note` — relevant patterns?
   - **"What failed before" is as valuable as "what worked."** Don't repeat rabbit holes.
1. **READ** the challenge description fully before touching anything
2. **CONFIRM** platform is authorized (TryHackMe, HackTheBox, PortSwigger, published CTF)
3. **CLASSIFY** into one of the 7 categories below
4. **LOAD** the category-specific approach section
5. **ENUMERATE** before exploiting — understand before attacking
6. **DOCUMENT** as you go (flag, technique, learning)

> **⛔ HINT RULE (PERMANENT — NO EXCEPTIONS):**
> NEVER purchase, reveal, or load CTF hints without explicit user instruction.
> Default mode is always **blind hunt**. If stuck, surface the dead-end analysis
> and ASK: *"Want me to check the hints?"* — do not act unilaterally.
> This applies to all platforms: Hacker101, TryHackMe, HackTheBox, PortSwigger.

---

## CTF Categories

### 1. Web (Most Common in Bug Bounty Overlap)

**Step 0 — Burp Startup (MANDATORY for ALL web challenges):**
```
1. curl -s http://localhost:9876/ --max-time 2 → check for "event: endpoint"
   → Silent? Auto-launch Burp (permission granted)
2. Set .playwright/cli.config.json proxy → "server": "http://127.0.0.1:8080"
3. Add challenge target to Burp Target → Scope
4. Confirm Intercept = OFF (passive mode)
5. All Playwright browser traffic now captured in Burp HTTP History
```

**Initial Recon:**
- View page source (Ctrl+U)
- Check robots.txt, sitemap.xml
- Inspect DevTools Network tab for API calls (also visible in Burp HTTP History)
- Check cookies (httpOnly? Secure? sameSite?)
- Check HTML comments for hints
- Try common paths: /admin, /dashboard, /api, /login, /backup

**Common Vulnerability Classes:**
- XSS → see `web-exploitation.md`
- SQLi → see `web-exploitation.md`
- IDOR → parameter tampering with sequential IDs
- SSRF → URL parameters that make server-side requests
- SSTI → template injection via input fields
- File Upload → bypass filters to upload shell
- JWT → weak secret, algorithm confusion (alg: none, RS256→HS256)
- CSRF → missing token, SameSite=None without Secure

**Tools Used (in CTF labs):**
- Burp Suite (auto-launched via burp-mcp.md protocol) → HTTP History, Repeater, Decoder
- Playwright headed browser (routed through Burp proxy 127.0.0.1:8080) → interactive testing
- Burp MCP (auto-approved) → Claude reads HTTP History programmatically post-session
- curl (in CTF VMs only)

**HTTP-layer challenges (Repeater focus):**
- Request manipulation: send to Repeater (Ctrl+R), modify headers/body, observe diff
- WebSocket challenges: Burp WebSocket History tab → capture frames → replay/modify in Repeater

**Skip Burp for:** Cryptography, binary exploitation/pwn, forensics, reverse engineering, OSINT, Misc.

---

### 2. Cryptography

**Initial Analysis:**
- Identify cipher type from ciphertext characteristics
- Check for base64, hex, rot13 (CyberChef)
- Look for repeated patterns → classical cipher
- Check key length hints in challenge description

**Common Vulnerability Classes:**
- Frequency analysis (substitution ciphers)
- XOR with known plaintext
- RSA weak keys (small n, e=3, common factor)
- Hash length extension attacks
- ECB mode block shuffling
- Padding oracle attacks (CBC mode)

**Tools:**
- CyberChef (online) → multi-step transforms
- RsaCtfTool (in CTF environments)
- SageMath for math-heavy challenges

---

### 3. Binary Exploitation (Pwn)

**Initial Analysis:**
- `file` command to identify binary type
- `checksec` to see protections (NX, PIE, canary, RELRO)
- `strings` to find interesting strings
- Look for obvious vulnerabilities: gets(), strcpy(), scanf()

**Common Vulnerability Classes:**
- Buffer overflow → overwrite return address
- Format string vulnerability → %n, %x, %p
- Use-after-free
- Heap exploitation
- ROP chain (when NX enabled)

**Note:** Pwn challenges run in provided Docker containers or remote netcat connections. Never on real systems.

---

### 4. Reverse Engineering

**Initial Analysis:**
- `file` command → ELF, PE, WASM, Python bytecode?
- Run first (in sandbox): observe input/output behavior
- `strings` → look for flag format hints
- Static analysis: Ghidra or IDA (in CTF environment)

**Common Approaches:**
- Find the comparison function → patch or replicate logic
- Decompile and read: look for password checks
- Dynamic analysis: trace execution with input variations
- Anti-reversing → detect obfuscation, unpack if needed

---

### 5. Forensics

**Initial Analysis:**
- `file` command on all provided files
- `exiftool` for metadata (may contain flag)
- `binwalk` for embedded files
- `strings` for ASCII content

**Common Techniques:**
- Steganography: LSB extraction, pixel manipulation
- Network capture: Wireshark .pcap analysis → follow TCP streams
- Memory forensics: Volatility for .vmem files
- File carving: recover deleted files
- Hidden partitions in disk images

---

### 6. OSINT

**Initial Analysis:**
- Read challenge for name, location, username, image hints
- Google reverse image search
- Username → social media platforms
- Check EXIF data of provided images

**Common Sources:**
- Google (site: dorks, image search)
- Wayback Machine (historical pages)
- crt.sh (certificate transparency for subdomains)
- GitHub (code history, commits, issues)
- LinkedIn (professional profiles)
- Twitter/X archives

**Note:** Only use public, passive sources. No account creation required for CTF OSINT.

---

### 7. Miscellaneous (Misc)

**Common Types:**
- Encoding challenges (multi-layer encode/decode)
- QR codes, barcodes
- Programming challenges (solve algorithmic problem)
- Trivia / research questions
- Audio spectrogram (Sonic Visualizer)
- Image steganography

**Approach:** Enumerate all file types provided → apply appropriate tool → look for flag format `CTF{...}` or as specified.

---

## Flag Formats by Platform

| Platform | Common Format |
|----------|--------------|
| TryHackMe | `THM{...}` |
| HackTheBox | `HTB{...}` |
| PortSwigger | Lab completed = success |
| Generic CTF | `FLAG{...}`, `ctf{...}`, `picoCTF{...}` |

---

## Writeup Protocol (Post-Flag)

1. Note: challenge name, platform, category, flag value
2. Document: vulnerability class, payload used, key insight
3. Run writeup generator: `skills/domains/cyber/writeup-generator.md`
4. Store: `notes/ctf/{Platform}/{challenge-name}.md`
5. Update: `notes/research/LearningPath/progress.md`

---

*CTF Methodology v1.0 | cyber-operator | Cyber Domain | 2026-02-23*
