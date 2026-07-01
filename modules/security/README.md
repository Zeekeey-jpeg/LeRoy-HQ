# LeRoy Security Module (opt-in · authorized-testing only)

An optional, **authorization-gated** add-on: a library of offensive-security **techniques and
methodology** — web/API exploitation, recon, CTF, cloud, mobile, LLM red-teaming, and
smart-contract audit patterns — for **authorized testing only**.

> ⚠️ **Not installed by default.** Installing requires you to accept the authorized-use terms
> (see [ACKNOWLEDGMENT.md](ACKNOWLEDGMENT.md)) — you must type `I AGREE`.

## Install
```bash
leroy add security      # prints the acknowledgment; requires "I AGREE"
# or directly:
sh modules/security/install.sh          # macOS/Linux
pwsh modules/security/install.ps1       # Windows
```

## What's inside
Generic technique playbooks + methodology — **no targets, no engagement data, no credentials.**
Pattern-recognition for whole classes of bugs: SSRF, IDOR, XSS, SQLi, SSTI, XXE, JWT attacks,
auth bypass, prototype pollution, HTTP request smuggling, GraphQL abuse, OAuth/OIDC, and more —
plus recon (passive/active), reporting methodology, CVSS scoring, and CTF guides.

## Ethics & scope
For your own systems, engagements where you have **explicit written permission**, bug-bounty
programs **within their stated scope**, and CTF / lab environments. Unauthorized use is illegal
and against this project's intent. Provided for education, defensive research, and authorized
work only — **no warranty**; you are responsible for staying in scope and within the law.
