# Quick Trigger Registry — Complete Table
*Full registry of all triggers. Top 15 high-frequency triggers are also kept inline in CLAUDE.md.*
*See `skills/meta/quick-trigger-maintenance.md` to add/modify entries.*

---

## your org Operations

| Trigger | Action | Skill |
|---------|--------|-------|
| "hs report", "crm report", "sales report" | Sales performance report | `skills/routines/crm-report.md` |
| "bim-tool mcp", "connect bim-tool", "start bim-tool" | Connect to your BIM connector/your BIM tool | `skills/routines/bim-connect.md` |
| "catalog", "what's in", "show catalog", "catalog for [mark]" | Assembly catalog extraction from your BIM tool via your product | `skills/integrations/assembly-catalog-query.md` |
| "product backup", "backup product", "push product" | Execute full mirror backup of your product your BIM tool plugin to GitHub | `skills/routines/product-backup.md` |
| "product dev mode", "switch to dev", "product dev" | Remove installer manifest → dev build active (fixes Duplicate AddInId) | `skills/routines/product-dev-mode.md` → MODE A |
| "product release mode", "switch to release", "product installer mode" | Remove dev files → ready for installer (fixes Duplicate AddInId) | `skills/routines/product-dev-mode.md` → MODE B |
| "product mode check", "which product is loaded", "product mode" | Report which addin manifests are present and which mode is active | `skills/routines/product-dev-mode.md` |
| "weekly report", "token burn report", "efficiency report" | Token burn WoW trends report | `skills/routines/token-burn-report.md` |
| "sync crm", "crm sync", "update crm", "pull crm" | your CRM background sync (LEROY Phase 3) | `skills/domains/your-org/crm-sync.md` |
| "create bundle", "weekly bundle", "friday bundle" | LEROY weekly export bundle (Phase 7) | `skills/routines/friday-bundle.md` |
| "export to excel", "accountant bundle", "leroy export" | Generate Excel + summary from memory | `skills/routines/friday-bundle.md` |
| "register payment", "record payment", "payment received", "log payment" | Register payment with automatic 25% tax withholding calculation and YTD tracking | `skills/routines/register-payment.md` |
| "gc jumper", "jumper ledger", "keith jumper", "jumper update", "jumper payment" | Load Keith Jumper GC ledger — basement labor ($800 remaining) + materials tracker | `memory/Projects/Contractor/index.md` |
| "leroy status", "swarm status" | Check RAG sidecar health + active sessions | `skills/integrations/leroy-swarm-v2.md` |
| "rag status", "vault index status" | Check RAG sidecar at localhost:7742/status | `skills/integrations/leroy-swarm-v2.md` |
| "reindex vault", "rebuild vault index" | POST to localhost:7742/reindex to rebuild semantic index | `skills/integrations/leroy-swarm-v2.md` |

---

## Tools & Automation

| Trigger | Action | Skill |
|---------|--------|-------|
| "scrape", "crawl", "extract from web", "firecrawl" | Web extraction via Firecrawl with fingerprinting and learning | `skills/integrations/web-extraction.md` |
| "draw diagram", "create diagram", "excalidraw", "architecture diagram", "flowchart", "sketch" | Excalidraw diagram creation and export | `skills/integrations/excalidraw/` |
| "postmortem", "project analysis", "what happened", "why over budget" | Project post-mortem analysis | `skills/workflows/postmortem/factory.md` |
| "use your superpower", "superpower", "run superpower", "simulate" | Simulation framework for scenario studies | `skills/meta/super-power.md` |
| "hil gate", "approve action", "policy check", "hil approve" | Human-in-the-loop approval gate — surface high-risk action for explicit operator approval before execution | `skills/meta/hil-gate.md` |
| "create skill", "new skill", "generate skill", "automate" | Auto-generate simple skill (<60s) | `skills/meta/skill-composer.md` |
| "skill guide", "how to create skill", "manual skill" | Manual skill creation guide | `skills/meta/skill-creator.md` |
| "data dump", "kb upgrade", "integrate docs", "parse knowledge" | **AUTO KB INGESTION:** 7-stage pipeline (CKO deployed, vault integration, skill assignment, index updates, orphan prevention) | `skills/meta/kb-auto-ingestion-protocol.md` |
| "everything on [client]", "full context [client]", "client context [name]" | Multi-source client context aggregation (your CRM + Gmail + Calendar + Drive) | `skills/integrations/client-context-aggregator.md` |

---

## Email Intelligence

| Trigger | Action | Skill |
|---------|--------|-------|
| "baseline email scan", "scan all emails", "email history scan" | One-time historical email scan (60-90 days) - builds conversation database | `skills/integrations/email-intelligence.md` |
| "scan emails", "email scan", "update email intel" | Manual daily email scan (last 24 hours) | `skills/integrations/email-intelligence.md` |
| "email intel [client]", "email context [client]", "emails with [client]" | Show full email intelligence for specific client | `skills/integrations/email-intelligence.md` |
| "outstanding emails", "email action items", "email todos" | List all pending email items across clients | `skills/integrations/email-intelligence.md` |
| "unanswered questions", "email questions" | List all unanswered questions from emails | `skills/integrations/email-intelligence.md` |

---

## Legal

| Trigger | Action | Skill |
|---------|--------|-------|
| "draft contract", "new agreement", "create MSA", "write SOW" | Draft new contract using templates | `agents/legal.md` via conductor |
| "review contract", "check agreement", "contract red flags", "is this safe" | Review contract against insurance coverage | `agents/legal.md` via conductor |
| "pre-signing checklist", "ready to sign", "contract checklist" | Run engagement-specific pre-signing verification | `agents/legal.md` via conductor |

---

## Teaching / an LMS

| Trigger | Action | Skill |
|---------|--------|-------|
| "an LMS status", "teaching status", "module release", "grading queue" | an LMS teaching assistant - course tracking, deadlines, recording status | `skills/domains/lms/teaching-assistant.md` |

---

## IntegratorOS (your organization Platform)

| Trigger | Action | Skill |
|---------|--------|-------|
| "integrator os", "integratorOS", "IOS project", "your organization platform" | Load index, fetch repo, show collab log, display status card, prompt for work | `skills/domains/integratorOS-context-load.md` |
| "start integrator", "integrator dev", "ios dev", "start ios" | Launch Vite dev server in detached PowerShell window (v5-source dir) | Direct PowerShell |
| "ios status", "integrator status", "ios check" | Read IntegratorOS/index.md + secretary-state.json → Phase + last build + next action | Direct Read |

---

## Career

| Trigger | Action | Skill |
|---------|--------|-------|
| "scrape jobs", "find jobs", "job search", "search linkedin jobs", "search indeed" | Playwright scrape LinkedIn + Indeed for Director+ jobs ($160k+, remote/hybrid) | `skills/domains/career/job-scraper.md` |
| "tailor resume", "apply for job", "job match", "match this job" | JD → update resume file + generate .docx + title/headline/summary block | `skills/domains/career/job-application-tailor.md` |
| "interview prep", "practice interview", "interview for" | 15 STAR-format answers using the user's real experience | `skills/domains/career/interview-prep.md` |
| "cover letter", "write cover letter", "cover letter for" | the user's-voice cover letter (hook/proof/ask) | `skills/domains/career/cover-letter-generator.md` |
| "role gap", "am I qualified", "gap analysis" | JD vs profile → gaps, framing, quick wins, apply/hold rec | `skills/domains/career/role-gap-analysis.md` |
| "research company", "company brief", "prep for interview at" | Company research brief + smart questions to ask | `skills/domains/career/company-research-brief.md` |
| "linkedin optimizer", "update linkedin", "linkedin headline" | Director-level headline variants, summary rewrites, post ideas | `skills/domains/career/linkedin-optimizer.md` |

---

## Cyber Security

| Trigger | Action | Skill |
|---------|--------|-------|
| "whitehat bounty aws", "aws bounty", "h1 aws", "aws bug bounty" | AWS-specific bounty session — SSRF→IMDS, IAM escalation, S3, Lambda. POC-first. | `skills/domains/cyber/whitehat-protocol.md` → TRACK A |
| "whitehat bounty source code", "source code bounty", "h1 source code", "code review bounty" | Source code bounty session — Semgrep taint, secrets, SQLi, deserialization. POC-first. | `skills/domains/cyber/whitehat-protocol.md` → TRACK B |
| "ctf", "solve this ctf", "challenge help" | CTF session via cyber-operator | `skills/domains/cyber/ctf-methodology.md` |
| "tryhackme", "THM room", "hackthebox", "HTB" | Platform CTF session | `agents/cyber-operator.md` |
| "portswigger", "web academy", "burp lab" | PortSwigger lab session | `skills/domains/cyber/portswigger-labs.md` |
| "burp suite", "intercept traffic", "burp proxy" | Burp workflow — CLI drives browser, Burp MCP reads HTTP history programmatically | `skills/domains/cyber/burp-suite-workflow.md` |
| "burp mcp", "burp history", "read proxy history", "send to repeater" | Burp MCP integration — auto-launch + programmatic HTTP history access | `skills/integrations/burp-mcp.md` |
| "Gandalf", "beat the AI", "AI guard" | Gandalf challenge session | `agents/ai-sec-agent.md` |
| "jailbreak", "LLM attack", "prompt injection", "AI red team" | LLM security research | `skills/domains/cyber/llm-security-framework.md` |
| "passive recon", "OSINT", "subdomain enum", "attack surface" | Recon session via recon-agent | `skills/domains/cyber/passive-recon.md` |
| "hacker101", "free hacker ctf" | Hacker101 CTF progression | `skills/domains/cyber/hacker101-guide.md` |
| "arcanum", "arcanum-sec", "security study" | Study resource navigation | `skills/domains/cyber/study-resources.md` |
| "cyber writeup", "document this finding", "save writeup" | Writeup generation + vault storage | `skills/domains/cyber/writeup-generator.md` |
| "score my report", "report score", "rate my report", "report quality", "ready to submit" | H1 pre-submission quality gate — scores 0-100, blocks low-quality reports, returns gap analysis | `skills/domains/cyber/report-score.md` |
| "easy wins", "quick wins", "what should I file", "what to file", "best findings to submit" | Easy win classification — confirms POC + win rate ≥65% + low dup risk = file immediately | `skills/domains/cyber/easy-wins-classifier.md` |
| "api audit", "api security", "api checklist", "audit this api", "rest audit", "graphql audit" | REST & GraphQL security audit — OWASP API Top 10:2023, priority finding table, evidence templates | `skills/domains/cyber/api-audit.md` |
| "cyber progress", "ctf progress", "what have I solved" | Show learning path tracker | `memory/Projects/Cyber/LearningPath/progress.md` |
| "cyber notes", "my hacking notes", "ctf vault" | Browse cyber memory vault | `memory/Projects/Cyber/index.md` |
| "ai security", "OWASP LLM", "LLM Top 10" | OWASP LLM reference | `skills/domains/cyber/llm-security-framework.md` |
| "cyber browser", "ctf browser", "watch me hack" | Playwright headed CTF assist | `skills/domains/cyber/playwright-ctf-assist.md` |
| "index this pattern", "save this technique", "log this workflow" | **Tool Discovery Indexing Protocol (3-step):** Step 1: capture inline. Step 2: update `memory/Patterns/Cyber-BurpSuite-Reference.md`. Step 3: update skill file + version bump + log in growth-engine.md | `memory/Patterns/Cyber-BurpSuite-Reference.md` |
| "parallel scan", "pool status", "pause pool", "resume pool", "headed pool", "close pool" | Playwright multi-session pool — N isolated contexts simultaneously | `skills/integrations/playwright/session-pool.md` |
| "ctf pool", "parallel labs", "pool [N] contexts" | CTF multi-lab parallel workflow | `skills/integrations/playwright/parallel-workflows.md` |
| "growth report", "vault growth", "cyber growth" | Show vault growth report (techniques added this week) | `memory/Projects/Cyber/growth-log.md` |
| "sweep [program url]", "full sweep", "autonomous sweep" | Launch 30-agent parallel sweep — arsenal classify → sweep → C-suite report → brief | `skills/domains/cyber/sweep-engine.md` |
| "arsenal classify", "classify scope" | Classify program scope into Zero-Auth/Auth-Creatable/Auth-Gated tracks | `skills/domains/cyber/arsenal-index.md` |
