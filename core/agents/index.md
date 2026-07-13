---
name: agents-index
description: "Agent routing table and deployment rules. Not an executable agent - serves as documentation and reference for the agent system."
---

# Agents Index

Autonomous agents for complex, multi-step task handling.

## Routing Table

| Keywords | Agent | Auto-Spawn |
|----------|-------|------------|
| coordinate, plan, delegate, orchestrate, substantial task | conductor | Yes (substantial tasks) |
| code, implement, build, develop, fix, feature | builder | Via conductor |
| UI, design, styling, components, frontend look | designer | Via conductor |
| diagram, draw, sketch, excalidraw, flowchart, architecture diagram, visualize | designer | Via conductor |
| large data, 10K+, ETL, batch, bulk operations | forge | Via conductor |
| commit, PR, merge, scope check, audit | guardian | Yes (before commits) |
| BIM tool, BIM, families, schedules, model | professor | Via conductor |
| growth, patterns, opportunities, what did you learn | scout | Yes (substantial tasks) |
| todo, tasks, checklist, line items, 3+ steps | planner | Yes (3+ line items) |
| validate, verify, check fields, report validation | analyst | Via conductor |
| validate bom, check accessories, missing parts, quote completeness | auditor | Via conductor |
| cleanup, clean, optimize, monday cleanup | janitor | Via schedule (Monday) |
| browser extract, API docs, CW dev page, web scrape | builder | Via conductor (+ scout) |
| scrape, extract web, crawl site, web data, firecrawl | scraper | Via conductor |
| ok, yes, status, trivial queries, quick triggers | quick | Yes (ALL trivial requests) |
| contract, agreement, NDA, MSA, SOW, legal, liability, insurance, E&O, clause | legal | Via conductor |
| timeline, tracking, records, coordination, status summary | secretary | Yes (ALL substantial tasks) |
| proposal, pitch, presentation, deck, gamma, quote presentation | proposal-writer | Via conductor |
| technical strategy, architecture, platform decisions, tech stack, infra | cto | Via CEO/COO |
| hiring, performance, onboarding, team capacity, agent utilization | hr | Via CEO/COO |
| sprint planning, velocity, backlog, standup, impediments, agile | scrum-leader | Via VP Engineering |
| code quality, standards, tech debt, release, sprint approval | vp-engineering | Via CTO |
| infrastructure, CI/CD, deployment, devops, build pipeline, monitoring | tech-lead | Via VP Engineering |
| morning briefing, department status, ops report, MCP health | chief-of-staff | Yes (morning trigger) |
| research, development, R&D, simulation, protocol testing, validation | simulator | Via CEO/CTO |
| alignment, orphan skills, dead references, routing gaps, check alignment | alignment-monitor | Via CKO (Monday) / on-demand |
| memory quality, approve vault note, token allocation, strategic memory audit, knowledge governance | cko | Yes (weekly - Monday) |
| token budget, memory cost, financial oversight, budget veto, approve large allocation | cfo | Yes (daily - morning) |
| ctf, challenge, flag, tryhackme, hackthebox, burp, bug bounty, web exploitation, portswigger | cyber-operator | Via conductor |
| osint, passive recon, subdomain, crt.sh, attack surface, github dork | recon-agent | Via conductor |
| gandalf, prompt injection, jailbreak, llm attack, ai red team, owasp llm, ai security | ai-sec-agent | Via conductor |
| IntegratorOS, IOS, PartnerCo platform, Supabase spatial, CesiumJS, security integrator SaaS | integratorOS-agent | Via conductor |
| Marketplace, print on demand, POD, printify, store QC, publish listing, Marketplace store | Marketplace-overseer | Via CTO (autonomous Marketplace loop) |
| Marketplace R&D, Marketplace trends, niche research, Marketplace recon, printify catalog | Marketplace-rd | Via Marketplace-overseer (6 AM daily) |
| routing fallback, no match, dynamic routing | skill-matcher | Via COO (conductor.md Dynamic Routing) |
| goal execution, autonomous goal, /goal high-effort | goal-overseer | Via /goal engine (background) |

**Tie-break:** on keyword collision, a task-type keyword (e.g. Gamma/deck/proposal) beats a subject-matter keyword (e.g. a project name).

---

## Agent Types

This folder contains **production agents** - fully specified, routable agents with auto-spawn rules. Related documentation exists elsewhere:

### 1. Production Agents (This Folder)
Standalone agents with complete specifications, routing keywords, auto-spawn triggers, and defined responsibilities.

**37 registered agents (executable)** — corrected from 35 on 2026-07-01 (live-execution testing caught the count was stale and cross-checked it against an actual `agents/*.md` glob):
- conductor, builder, designer, forge
- guardian, professor, scout, planner, analyst, auditor, janitor
- legal, quick, secretary, mesh-wrapper (infrastructure)
- skill-matcher (COO no-match routing fallback — infrastructure)
- goal-overseer (autonomous /goal step executor — background)
- proposal-writer (Gamma MCP integration)
- scraper (Firecrawl web extraction)
- cto, cfo, cko, hr, scrum-leader, vp-engineering (YourCo Office leadership)
- tech-lead (infra / CI-CD / DevOps manager — under VP Engineering)
- chief-of-staff (morning briefing coordination, department status)
- simulator (protocol testing, validation — R&D/simulation only; NOT Marketplace R&D)
- alignment-monitor (Skill-agent alignment guardian - orphan detection, routing audits)
- integratorOS-agent (IntegratorOS / PartnerCo platform specialist)
- **cyber-operator** (CTF solving, web exploitation, bug bounty — YourCo Cyber Dept)
- **recon-agent** (Passive OSINT only — YourCo Cyber Dept)
- **ai-sec-agent** (AI/LLM security, Gandalf, OWASP LLM — YourCo Cyber Dept)
- **Marketplace-overseer** (Marketplace POD store orchestrator + QC — reports to CTO)
- **Marketplace-rd** (Marketplace daily trend/recon scout — reports to Marketplace-overseer)
- **Marketplace-manager** (Marketplace niche/keep-kill decisions — reports to COO) ⚠️ added 2026-07-01, was missing from this index entirely
- **Marketplace-designer** (Marketplace POD artwork generation — reports to Marketplace-manager) ⚠️ added 2026-07-01, was missing from this index entirely

⚠️ **Known overlap, not yet resolved:** `Marketplace-manager`/`Marketplace-designer` and `Marketplace-overseer`/`Marketplace-rd` describe overlapping Marketplace responsibilities (niche selection, design generation, store ops) — look like two independently-built agent pairs. Flagged for `alignment-monitor`'s roster-drift cleanup, not fixed here.

**4 reference docs (not executable agents — read by COO/CTO for governance):**
- `QUICK-REFERENCE.md` — quick agent lookup card
- `audit-agent-tools.md` — agent tool capability auditor checklist
- `c-suite-tool-constraints.md` — C-suite write-tool restrictions
- `org-governance.md` — full 5-tier org hierarchy & role rules

**How to use:** Reference by name in CLAUDE.md quick triggers or route via keywords in the Routing Table above.

### 2. Dynamic Templates (skills/workflows/leroy/)
Prompt templates for spawning temporary agents in specific workflows.

- `scraper-agent.md` - LeRoy data collector template (Phase 1A)
- `generator-agent.md` - LeRoy report generator template (Phase 2)

**How to use:** Spawned dynamically by factory agents. Not directly routable; context-specific to LeRoy workflow.

### 3. Infrastructure Docs (skills/meta/)
Guides and reference documentation for the agent system.

- `agent-creator.md` - Guide for creating new production agents
- `sub-agent-spawning.md` - Infrastructure for background agent execution

**How to use:** Read for understanding system design, agent patterns, and best practices. Not agents themselves.

---

## Agent Roster

### Core Team

| Agent | Role | Color | Model |
|-------|------|-------|-------|
| **conductor** | Master coordinator, planning, QC, delegation | blue | inherit |
| **builder** | Code implementation, features, fixes | cyan | inherit |
| **designer** | UI/UX design, components, styling | magenta | inherit |
| **forge** | Large data operations (10K+ records) | yellow | inherit |
| **guardian** | Commit QA, scope validation, auditing | red | inherit |
| **professor** | BIM expertise, BIM tool operations | green | inherit |

### Leadership Team (C-Suite & VPs)

| Agent | Role | Color | Model |
|-------|------|-------|-------|
| **cto** | Technical strategy, architecture, platform decisions | blue | inherit |
| **cfo** | Token budget oversight, memory financial controls | green | inherit |
| **cko** | Vault governance, quality gate, knowledge strategy | teal | inherit |
| **hr** | Hiring, performance, team capacity, agent utilization | purple | inherit |
| **scrum-leader** | Sprint planning, velocity, backlog, agile coaching | orange | inherit |
| **vp-engineering** | Code quality, standards, tech debt, release management | indigo | inherit |
| **tech-lead** | Infrastructure, CI/CD, deployment, DevOps, build pipeline, monitoring (under VP Engineering) | indigo | inherit |
| **simulator** | R&D department - Protocol testing, validation framework | cyan | haiku |
| **alignment-monitor** | Skill-agent alignment guardian, orphan detection | orange | haiku |

### Cyber Department

| Agent | Role | Color | Model |
|-------|------|-------|-------|
| **cyber-operator** | CTF solving, web exploitation, bug bounty, Burp coordination | red | sonnet |
| **recon-agent** | Passive OSINT only (WebFetch + WebSearch, no active packets) | orange | haiku |
| **ai-sec-agent** | AI/LLM security, Gandalf challenges, OWASP LLM Top 10 | purple | sonnet |

### Marketplace Department (Autonomous)

| Agent | Role | Color | Model |
|-------|------|-------|-------|
| **Marketplace-overseer** | Marketplace POD store orchestrator — QC, publish, pricing, holiday ramp, IP guardrails, management report | orange | sonnet |
| **Marketplace-rd** | Daily R&D / recon scout — trend crawl, Printify cross-ref, ranked opportunity feed | cyan | sonnet |

> **Legacy files (superseded):** `agents/Marketplace-manager.md` and `agents/Marketplace-designer.md` reflect the v1 crew architecture. The current architecture uses Marketplace-overseer + Marketplace-rd. The legacy files are archived in place.

### Background Agents

| Agent | Role | Color | Model |
|-------|------|-------|-------|
| **scout** | Silent pattern detection, growth opportunities | green | haiku |
| **planner** | Background task tracking, auto-completion detection | orange | haiku |
| **analyst** | Report specification validation | orange | haiku |
| **janitor** | Monday cleanup orchestrator, 11-category parallel scan | orange | haiku |
| **auditor** | BOM validation, accessory detection, catalog cross-reference | orange | haiku |
| **legal** | Contract drafting, review, insurance alignment, clause library | teal | inherit |
| **secretary** | Background timeline tracking, legal coordination, status summaries | purple | haiku |
| **quick** | Trivial query handler, quick trigger router, 100% coverage | gray | haiku |
| **proposal-writer** | YourCo-branded proposals via Gamma.app, sales decks | cyan | inherit |
| **scraper** | Intelligent web extraction via Firecrawl with learning | orange | inherit |
| **chief-of-staff** | Morning briefing coordination, department status, MCP health | gold | haiku |
| **skill-matcher** | COO no-match routing fallback, dynamic routing (spawned by conductor.md) | gray | haiku |
| **goal-overseer** | Autonomous /goal step executor, high-effort goal execution (background) | gray | haiku |

---

## Deployment Rules

### Rule 1: Overseer Always Required

**Every substantial task requires conductor as overseer.**

```yaml
Minimum team: Overseer + 1 Helper

No task executes with just a helper agent.
No helper agent works without overseer coordination.
```

### Rule 2: Auto-Spawn Agents

| Agent | Auto-Spawns When |
|-------|------------------|
| conductor | Substantial task detected (3+ steps, multi-file) |
| guardian | Commit or PR preparation |
| scout | Substantial task (background, via Task tool) |
| planner | 3+ line items detected OR todo keywords (background, via Task tool) |
| secretary | ALL substantial tasks (Priority 0/1) - background timeline tracking |
| chief-of-staff | Morning trigger - department status collection and briefing coordination |
| quick | Trivial request or quick trigger (100% coverage goal) |

### Rule 3: Helper Assignment

| Task Type | Overseer | Helper(s) |
|-----------|----------|-----------|
| Code implementation | conductor | builder |
| UI/design work | conductor | designer + builder |
| Large data operations | conductor | forge |
| BIM/BIM tool work | conductor | professor |
| Before any commit | conductor | guardian |
| Complex feature | conductor | builder + designer + guardian |
| **Legal/Contract Work** | | |
| Contract drafting | conductor | legal |
| Contract review | conductor | legal |
| Pre-signing verification | conductor | legal |
| Negotiation support | conductor | legal |
| **Browser Workflows** | | |
| API doc extraction | conductor | builder |
| Price comparison → catalog | conductor | forge |
| Multi-page crawl | conductor | builder (coordinate) |
| Form/UI analysis | conductor | designer |
| Browser pattern detection | (background) | scout |
| **Web Extraction** | | |
| Single page scrape | conductor | scraper |
| Structured data extraction | conductor | scraper |
| Multi-page crawl | conductor | scraper |
| Batch URL extraction | conductor | scraper + forge |

---

## Agent Scaling Tiers

### Tier Definitions

| Tier | Work Packets | Structure | Max Agents | Capacity |
|------|--------------|-----------|------------|----------|
| **Tier-1** | 1-3 | 1 arch + helpers | 5 | Entry level |
| **Tier-2** | 4-9 | 1 arch + 2-3 sub-arch + helpers | 12 | Standard |
| **Tier-3** | 10-15 | 1 arch + 5 sub-arch + helpers | 18 | Large |
| **Tier-4** | 16+ | 1 arch + ceil(packets/3) sub-arch + helpers | 20+ | Enterprise |

### Maximize Rule (CRITICAL)

```yaml
ALWAYS spawn to tier capacity, not minimum.

Example - Tier 2 task (6 work packets):
  WRONG: [1] arch [1] techy              # Minimum - slow, sequential
  RIGHT: [1] arch [2] sub-arch [6] techy [1] sentinel  # Maximize - parallel

Rationale:
  - Parallel execution
  - Faster completion
  - Better quality (more review)
  - Utilize available capacity
```

### Agent Count Notation

```yaml
Format: [N] type

Types:
  arch     = conductor
  sub-arch = sub-architect (tier 2+)
  techy    = builder
  uiux     = designer
  data     = forge
  sentinel = guardian
  BIM tool    = professor
  growth   = scout
  micro    = quick

Examples:
  [1] arch [3] techy [1] sentinel           # Tier-1
  [1] arch [2] sub-arch [5] techy [1] uiux  # Tier-2
  [1] micro                                  # Trivial (100% coverage)
```

### Sub-Architect Hierarchy

```yaml
When to use sub-architects:
  - Tier-2 or higher (4+ work packets)
  - Need parallel execution streams
  - Multiple domains in single task

Structure:
  Main Architect (overseer)
  ├── Sub-Arch 1 → [techy, uiux] → packets 1-3
  ├── Sub-Arch 2 → [techy, data] → packets 4-6
  └── Sub-Arch 3 → [techy, sentinel] → packets 7-9

Rules:
  - Each sub-arch handles max 3 packets
  - Sub-arch reports to main conductor
  - Sub-arch can spawn own helpers
  - Main conductor coordinates all streams
```

### Capacity Planning

```yaml
Calculate tier:
  packets = count distinct work items
  if packets <= 3:  tier = 1, max = 5
  if packets <= 9:  tier = 2, max = 12
  if packets <= 15: tier = 3, max = 18
  if packets > 15:  tier = 4, max = 20+

Spawn formula:
  arch = 1 (always)
  sub-arch = ceil(packets / 3) - 1 (tier 2+)
  techy = packets (one per work packet)
  uiux = 1 per UI-related packet
  sentinel = 1 (if commit involved)
  growth = 1 (background, always on substantial)
```

**Rule:** No single team handles more than 3 work packets.

---

## Agent Responsibilities

### conductor
```yaml
DOES:
  - Break complex tasks into work packets
  - Assign packets to appropriate agents
  - Monitor progress and quality
  - Coordinate Git operations
  - Enforce scope adherence
  - Spawn scout for substantial tasks

DOES NOT:
  - Write implementation code
  - Design UI/UX
  - Handle data operations directly
  - Skip planning phase
```

### builder
```yaml
DOES:
  - Write React/TypeScript code
  - Implement features and fixes
  - Create API integrations
  - Write tests

DOES NOT:
  - Make architectural decisions alone
  - Design UI without @designer
  - Commit without @guardian review
```

### designer
```yaml
DOES:
  - Design UI components
  - Create design tokens
  - Style with Tailwind/shadcn
  - Ensure accessibility

DOES NOT:
  - Write backend code
  - Make architecture decisions
  - Handle data operations
```

### forge
```yaml
DOES:
  - Large dataset operations (10K+ records)
  - ETL processes
  - Batch transformations
  - Data analysis

DOES NOT:
  - Small data tasks (use inline)
  - UI work
  - Code architecture
```

### guardian
```yaml
DOES:
  - Validate scope adherence
  - Audit changes before commit
  - Check for security issues
  - Verify quality standards

DOES NOT:
  - Write code
  - Make changes
  - Skip any commit
```

### professor
```yaml
DOES:
  - BIM tool operations via BIM tool
  - BIM expertise and guidance
  - Family/type management
  - Schedule/quantity takeoffs

DOES NOT:
  - Non-BIM development
  - General coding tasks
```

### scout
```yaml
DOES:
  - Monitor conversations silently (background)
  - Track patterns and gaps
  - Surface suggestions at breakpoints
  - Propose new skills/agents

DOES NOT:
  - Interrupt active work
  - Create files directly
  - Surface for every observation
```

### planner
```yaml
DOES:
  - Parse prompts for line items (5 patterns: numbered, bullets, sequential, imperative, work packets)
  - Assign priorities using multi-factor scoring (0-100 scale)
  - Track dependencies (blocks/blocked_by relationships)
  - Auto-close tasks with multi-signal completion detection (≥0.75 confidence)
  - Coordinate with conductor (accept work packets), guardian (pre-commit checks), scout (pattern detection), memory (consolidation)
  - Write progress to todo-output.md for checkpoint surfacing
  - Update state.json silently in background
  - Recalculate priorities dynamically on task completion

DOES NOT:
  - Execute todos (main session does actual work)
  - Interrupt active work (checkpoint-only surfacing)
  - Make architectural decisions (conductor's job)
  - Overlap with scout (separate concerns: todos vs patterns)
  - Auto-close guardian tasks (require manual approval)
  - Skip verification before auto-close
```

### analyst
```yaml
DOES:
  - Validate report fields exist in data sources
  - Check CRM/PSA tool property availability
  - Confirm calculation feasibility
  - Provide validation reports

DOES NOT:
  - Create or modify reports
  - Change data in source systems
  - Block report creation (advisory)
  - Make business decisions
```

---

## Handoff Protocols

### Standard Handoffs

| From | To | Trigger |
|------|----|---------|
| conductor | builder | Code implementation needed |
| conductor | designer | UI/design decisions needed |
| conductor | forge | Large data operation needed |
| conductor | guardian | Before any commit |
| conductor | professor | BIM/BIM tool work needed |
| conductor | legal | Contract drafting or review needed |
| builder | conductor | Implementation complete, needs QC |
| designer | conductor | Design complete, needs QC |
| guardian | conductor | Audit complete, ready for merge |
| scout | conductor | Patterns ready to surface |
| conductor | analyst | Report validation needed |
| analyst | conductor | Validation complete |
| legal | conductor | Contract review complete, ready for decision |
| legal | secretary | Contract action complete, needs tracking |
| secretary | chief-of-staff | Morning routine - provide 24h event summary |
| chief-of-staff | conductor | Briefing complete, critical items flagged |
| chief-of-staff | secretary | MCP failure creates one-off reminder |

### Growth Monitor Handoff

```yaml
When scout has suggestions:
  1. scout accumulates patterns
  2. At breakpoint: outputs [GROWTH] block
  3. Main conversation checks output
  4. If user selects "Review":
     - Load skill-creator.md or agent-creator.md
     - Present draft for approval
```

---

## Creating New Agents

See `meta/agent-creator.md` for complete guide.

### Quick Checklist

```yaml
Before creating:
  - [ ] Check this index for role overlap
  - [ ] Read similar agents
  - [ ] Confirm gap is real

When creating:
  - [ ] Use Claude Code frontmatter format
  - [ ] Include 2-4 <example> blocks
  - [ ] Define clear boundaries
  - [ ] Get user approval

After creating:
  - [ ] Add to this index
  - [ ] Update CLAUDE.md if frequently triggered
```

---

## Agent File Locations

```
agents/
├── index.md                         ← This file
├── quick.md
├── conductor.md
├── janitor.md
├── forge.md
├── scout.md
├── mesh-wrapper.md                  ← Lateral communication (A2A-enhanced, all tiers)
├── auditor.md
├── guardian.md
├── analyst.md
├── professor.md
├── builder.md
├── designer.md
├── legal.md                         ← Contract drafting, review, insurance alignment
├── secretary.md                     ← Background timeline tracking, legal coordination
├── proposal-writer.md               ← YourCo-branded proposals via Gamma.app
├── scraper.md                       ← Firecrawl web extraction with learning
├── cto.md                           ← Technical strategy, architecture, platform decisions
├── hr.md                            ← Hiring, performance, team capacity, utilization
├── scrum-leader.md                  ← Sprint planning, velocity, backlog, agile coaching
├── vp-engineering.md                ← Code quality, standards, tech debt, releases
├── chief-of-staff.md               ← Morning briefing coordination, department status, MCP health
├── simulator.md                     ← R&D department - Protocol testing, validation
├── cyber-operator.md               ← CTF solving, web exploitation, bug bounty (YourCo Cyber Dept)
├── recon-agent.md                  ← Passive OSINT only (YourCo Cyber Dept)
└── ai-sec-agent.md                 ← AI/LLM security, Gandalf, OWASP LLM (YourCo Cyber Dept)
├── alignment-monitor.md            ← Skill-agent alignment guardian
├── Marketplace-overseer.md                ← Marketplace POD store orchestrator (active)
├── Marketplace-rd.md                      ← Marketplace R&D / recon scout (active)
├── Marketplace-manager.md                 ← [LEGACY — superseded by Marketplace-overseer]
├── Marketplace-designer.md                ← [LEGACY — superseded by Marketplace-overseer workflow]
└── agent-cards/                    ← A2A Protocol capability registry (agent-cards/README.md)
    ├── README.md
    ├── auditor.agent.json           ← external_safe: true
    ├── analyst.agent.json           ← external_safe: true
    ├── proposal-writer.agent.json   ← external_safe: true
    ├── professor.agent.json         ← external_safe: true
    ├── scraper.agent.json           ← external_safe: true
    ├── forge.agent.json             ← internal only (write access)
    ├── builder.agent.json           ← internal only (write access)
    └── legal.agent.json             ← internal only (confidential data)
```

---

### auditor
```yaml
DOES:
  - Validate PSA tool opportunity product lists
  - Cross-reference product catalog tool and PSA tool catalogs
  - Detect missing accessories using accessory map
  - Generate validation reports with revenue impact
  - Send email notifications for findings

DOES NOT:
  - Modify PSA tool opportunities
  - Add items to quotes automatically
  - Make pricing decisions
  - Override sales engineer judgment
```

### secretary
```yaml
DOES:
  - Auto-spawn on ALL substantial tasks (background)
  - Track timeline events (emails, meetings, documents)
  - Update Projects/{Client}/index.md records automatically
  - Coordinate with legal agent via state.json
  - Generate 24h status summaries for morning routine
  - Detect trackable actions from tool results

DOES NOT:
  - Interrupt active work (background only)
  - Send emails or make external calls
  - Modify contract content (legal agent owns that)
  - Skip deduplication checks
  - Create binding commitments
```

### legal
```yaml
DOES:
  - Draft contracts from approved templates (UniCast, DESCCO, ExampleClient patterns)
  - Review incoming contracts against insurance coverage
  - Cross-check clauses against approved clause library
  - Run pre-signing checklists for engagement types
  - Provide risk assessments and red flag warnings
  - Coordinate with secretary for client context
  - Recommend negotiation positions within approved boundaries
  - Generate redline suggestions for problematic clauses

DOES NOT:
  - Execute or sign contracts (Brian only)
  - Provide legal advice (provides risk assessment only)
  - Modify insurance policy terms
  - Approve contracts containing deal breakers
  - Override Brian's negotiation decisions
  - Share confidential contract terms externally
  - Create binding commitments
```

### quick
```yaml
DOES:
  - Handle trivial queries (ok, yes, status)
  - Route quick triggers to skills
  - Provide git status checks
  - Acknowledge confirmations
  - Check file existence
  - Triage requests and escalate when needed

DOES NOT:
  - Write code or implement features
  - Make architectural decisions
  - Handle multi-step tasks
  - Process large data
  - Commit code or create PRs
  - Skip escalation for complex requests
```

### mesh-wrapper
```yaml
DOES:
  - Enable lateral agent communication (ALL tiers — A2A-enhanced)
  - Route A2A message types: UPDATE, QUERY, ACK, ERROR, DELEGATE, SUBSCRIBE, NOTIFY, CACHE
  - Allow direct peer-to-peer task delegation (DELEGATE messages)
  - Manage event subscriptions and notifications (SUBSCRIBE/NOTIFY)
  - Broadcast learned data to all peers (CACHE messages)
  - Enforce rate limiting (10 msg/sec per agent, 100 global)
  - Resolve conflicts via version vectors (LWW)
  - Detect and handle deadlocks (3s timeout)
  - Monitor heartbeats and quarantine failed agents
  - Provide 2-10x parallel speedup vs hierarchical-only

DOES NOT:
  - Replace hierarchical coordination (conductor still owns orchestration)
  - Allow upward delegation (Tier-N cannot delegate to Tier-N-1 or above)
  - Guarantee message delivery without orchestrator fallback
  - Operate without mesh-state.json infrastructure
  - Allow Tier-5 support agents to spawn Tier-4 specialists
```

### proposal-writer
```yaml
DOES:
  - Generate YourCo-branded proposals via Gamma.app API
  - Apply consistent visual identity (colors, fonts, tone)
  - Structure content for executive audiences
  - Export to PDF/PPTX for client delivery
  - Poll generation status until complete
  - Integrate with CRM deal context

DOES NOT:
  - Create proposals without deal context
  - Skip branding guidelines
  - Generate without user approval of outline
  - Modify pricing or scope independently
  - Share proposals externally (user step)
```

---

### scraper
```yaml
DOES:
  - Extract web content via Firecrawl MCP
  - Check fingerprints for structure changes
  - Use learned selectors with fallback ordering
  - Route through batch queue for bulk operations
  - Record success/failure to learning system
  - Adapt to website changes automatically

DOES NOT:
  - Make architectural decisions
  - Skip fingerprint checks
  - Ignore rate limits
  - Store credentials (uses session/credentials.json)
  - Bypass learning system feedback
```

### chief-of-staff
```yaml
DOES:
  - Coordinate morning briefing data collection from all departments
  - Format briefing output in department-based structure
  - Track MCP health status across morning briefings
  - Escalate critical items to Executive Summary
  - Auto-create one-off reminders for persistent MCP failures
  - Collect status from 7 department heads
  - Map raw tool data to business-relevant department sections

DOES NOT:
  - Send emails or make external calls
  - Make business decisions (reports only)
  - Modify agent specifications or system config
  - Skip department sections (all departments reported every day)
  - Override department head assessments
  - Run outside morning briefing context
```

### simulator
```yaml
DOES:
  - Execute protocol compliance testing batches (25-250 questions)
  - Validate gate output, memory recall, agent spawn, response time, answer correctness
  - Export results in validation framework JSON format
  - Run regression tests after protocol changes
  - Track compliance metrics across 5 validation dimensions

DOES NOT:
  - Write to production databases (PSA tool, CRM, product catalog tool, Supabase)
  - Modify memory vault files
  - Create commits or PRs
  - Send emails or make external API calls
  - Update user-facing state (except test metrics)
  - Run destructive operations on any system
```

### alignment-monitor
```yaml
DOES:
  - Weekly orphan detection (skills not in any index)
  - Dead reference detection (index entries pointing to deleted files)
  - Routing gap analysis (skills with no or weak keywords)
  - Archive candidate flagging (test stubs, empty files)
  - New skill/agent index validation
  - Report alignment % to CKO and morning briefing

DOES NOT:
  - Modify index files (reports only, builder executes fixes)
  - Delete or archive files (escalates to conductor)
  - Create skills or agents
  - Override existing routing decisions
  - Run outside Monday audit or on-demand trigger
```

---

## Skill Assignments (KB Ingestion 2026-02-15)

**5 new backend skills assigned:**

| Skill | Path | Owner | Domain |
|-------|------|-------|--------|
| supabase-rls-implementation.md | `skills/stacks/` | builder | Supabase RLS SQL templates, policy patterns |
| supabase-vector-search-implementation.md | `skills/stacks/` | builder | pgvector setup, HNSW indexing, similarity queries |
| openai-pdf-extraction.md | `skills/integrations/` | builder | Structured Outputs API, PDF ingestion, embeddings |
| anthropic-claude-coaching.md | `skills/integrations/` | builder | Claude Messages API, streaming, system prompts |
| backend-agent-conventions.md | `skills/workflows/` | vp-engineering | Code organization, naming, security, performance rules |

**Orphan Status:** 0 of 5 new skills orphaned (100% coverage)

---

*Agents Index v5.4 | 37 executable agents + 4 reference docs | 4-tier scaling | 20+ capacity | 100% agent coverage | Mesh v3.1 (A2A-enhanced + persistent IMPACT) | Agent Cards v1.0 (13/37 agents have cards) | Gamma v1.0 | Firecrawl v1.0 | YourCo Office v1.2 (tech-lead under VP-Eng) | Cyber Dept v1.0 | Marketplace Dept v2.0 (Marketplace-overseer + Marketplace-rd + Marketplace-manager + Marketplace-designer, overlap unresolved) | +skill-matcher +goal-overseer registered | Tie-break rule v1.0*
