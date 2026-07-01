---
name: skill-shopping
description: |
  Classify and integrate new skills into the system.

  Use when:
  - User requests new capability
  - Evaluating skill additions
  - Reorganizing skill library

  Includes: Classification rules, integration checklist, skill inventory.
---

# Skill Shopping Guide

Evaluate, classify, and integrate new skills.

## Current Skill Inventory

### Agents (6 skills) - `skills/agents/`
| Skill | File | Purpose | Keywords |
|-------|------|---------|----------|
| conductor | `agents/conductor.md` | Task coordination, QC, Git | orchestrate, plan, delegate |
| builder | `agents/builder.md` | Code implementation | build, implement, code |
| designer | `agents/designer.md` | Interface design | design, UI, UX, layout |
| forge | `agents/forge.md` | Data operations | ETL, sync, delta, migrate |
| guardian | `agents/guardian.md` | QA, hygiene | PR, commit, cleanup, scope |
| professor | `agents/professor.md` | BIM training | a course, your BIM tool, teaching |

**Agent File Requirement:** Every agent listed MUST have a corresponding skill file in `skills/agents/`.

### Stacks (4 skills)
| Skill | Purpose | Keywords |
|-------|---------|----------|
| supabase-netlify | Stack A: Modern SaaS | Supabase, Netlify, RLS |
| google-apps-script | Stack B: Internal tools | GAS, Sheets, Apps Script |
| web-frameworks | Next.js, Turborepo | Next, monorepo, Turbo |
| mcp-builder | MCP server development | MCP, Model Context Protocol, FastMCP |

### Integrations (5 skills)
| Skill | Purpose | Keywords |
|-------|---------|----------|
| ticketing-api | ticketing Manage API | your CRM, ticketing, PSA |
| crm-api | your CRM | your CRM, deals, CRM |
| catalog-tool | your catalog service SI | your catalog service, catalog, catalog |
| n8n-workflows | Workflow automation | n8n, automation, workflow |
| n8n-workflow-builder | Conversational n8n builder | build n8n, create automation, n8n agent |

### Domains (3 skills)
| Skill | Purpose | Keywords |
|-------|---------|----------|
| domain-dev | your app's API development | your BIM tool, C#, .NET 4.8 |
| android-kotlin | Android development | Android, Kotlin, Compose |
| education-LMS | LMS LMS | LMS, LMS, course |

### Workflows (5 skills)
| Skill | Purpose | Keywords |
|-------|---------|----------|
| pr-workflow | PR creation process | PR, pull request, merge |
| scope-control | Scope validation | scope, creep, validation |
| project-selection | Project routing | project, which, folder |
| git-pushing | Commit workflow | commit, push, git |
| review-implementing | Review feedback | review, feedback, implement |

### Tooling (4 skills)
| Skill | Purpose | Keywords |
|-------|---------|----------|
| xlsx | Excel operations | Excel, spreadsheet, xlsx |
| docx | Word documents | Word, docx, document |
| webapp-testing | Playwright testing | test, Playwright, browser |
| pdf | PDF manipulation | PDF, extract, merge |

### Design (3 skills)
| Skill | Purpose | Keywords |
|-------|---------|----------|
| frontend-design | Design philosophy | design, aesthetic, visual |
| ui-styling | Tailwind/shadcn | Tailwind, shadcn, styling |
| frontend-development | React patterns | React, TypeScript, component |

### Meta (2 skills)
| Skill | Purpose | Keywords |
|-------|---------|----------|
| skill-creator | Create new skills | create skill, new skill |
| skill-shopping | Skill inventory | which skill, find skill |

**Total: 32 skills across 8 categories**

## Classification Decision Tree

```
New capability requested
│
├─ Is it about an agent persona/role?
│   └─ YES → agents/
│
├─ Is it a technology stack or framework?
│   └─ YES → stacks/
│
├─ Is it a third-party API integration?
│   └─ YES → integrations/
│
├─ Is it domain-specific knowledge?
│   └─ YES → domains/
│
├─ Is it a process or workflow?
│   └─ YES → workflows/
│
├─ Is it about a specific tool/file type?
│   └─ YES → tooling/
│
├─ Is it about UI/UX/design?
│   └─ YES → design/
│
└─ Is it about the skill system itself?
    └─ YES → meta/
```

## Skill Gap Analysis

### Currently Missing (Potential Additions)

```yaml
High Priority:
  - Database migrations (SQL patterns)
  - Docker/containerization
  - Testing patterns (unit, integration)
  - Error handling patterns

Medium Priority:
  - AWS/cloud services
  - GraphQL patterns
  - WebSocket/realtime
  - Authentication patterns

Low Priority:
  - Mobile web (PWA)
  - Email templates
  - Logging/monitoring
  - Performance profiling
```

## Integration Checklist

### Before Adding a Skill

```yaml
Evaluate:
  - [ ] Is this capability used frequently?
  - [ ] Does it fit an existing category?
  - [ ] Would it duplicate existing content?
  - [ ] Is it specific enough to be useful?
  - [ ] Is it general enough to reuse?

Decide:
  - ADD: Frequent use, clear category, no duplication
  - EXTEND: Partial coverage exists, add to existing skill
  - SKIP: Rarely needed, too specific, already covered
```

### After Creating a Skill

```yaml
Integration Steps:
  - [ ] File created in correct category folder
  - [ ] Frontmatter includes valid triggers
  - [ ] Content follows skill template
  - [ ] CLAUDE.md router updated with keywords
  - [ ] Skill-shopping inventory updated
  - [ ] Related skills cross-referenced
  - [ ] CREDENTIALS ADDED TO creds.md (if applicable)
```

### Credential Handling (MANDATORY for integrations/MCPs)

**If the skill involves API keys, tokens, or secrets:**

```yaml
Credential Checklist:
  - [ ] Add credentials to skills/memory/config/credentials.md
  - [ ] Include actual token value (not placeholder)
  - [ ] Include MCP config JSON if applicable
  - [ ] Document how to obtain/rotate credential
  - [ ] Add reference in skill: "> **CREDENTIALS:** See skills/memory/config/credentials.md > {Section}"

NEVER:
  - Store credentials only in MCP config files
  - Use placeholders like "your-token-here" in creds.md
  - Skip this step "for later"
```

**Skills that typically need credential updates:**
- `integrations/*` - All API integrations
- `stacks/mcp-builder.md` - MCP server builds
- `stacks/supabase-netlify.md` - Supabase projects
- `stacks/google-apps-script.md` - GAS deployments

## Router Keyword Rules

### Adding Keywords to CLAUDE.md

```markdown
| Keyword Pattern | Skill |
|-----------------|-------|
| Primary term | skills/category/skill.md |
| Alternate term | skills/category/skill.md |
| Product name | skills/category/skill.md |
```

### Keyword Best Practices

```yaml
Good Keywords:
  - Unique to the skill
  - Commonly used by user
  - Product/tool names
  - Action + context pairs

Bad Keywords:
  - Too generic (build, create, make)
  - Overlapping with other skills
  - Rarely mentioned
  - Internal jargon
```

## Skill Maintenance

### Quarterly Review

```yaml
Check Each Skill:
  - Is content still accurate?
  - Are examples still working?
  - Has the API/tool changed?
  - Is it being loaded (usage metrics)?
  - Should it be split or merged?
```

### Deprecation Process

```
1. Mark skill as deprecated in frontmatter
2. Add migration note pointing to replacement
3. Keep for 2 quarters
4. Move to .cleanup/skills/
5. Remove from router after 30 days
```

## Skill Request Template

When user requests new capability:

```markdown
## New Skill Request

**Capability:** [What the user needs]
**Frequency:** [How often needed: daily/weekly/monthly/rare]
**Category:** [Proposed category]
**Keywords:** [Suggested router keywords]

### Content Outline
1. Quick reference
2. Core patterns
3. Examples
4. Best practices

### Related Skills
- [Existing skill that might overlap]
- [Skill that would complement this]

### Recommendation
- [ ] CREATE new skill
- [ ] EXTEND existing skill: [which one]
- [ ] SKIP (reason: )
```

## Cross-Reference Map

### Skills That Work Together

```yaml
Frontend Work:
  - frontend-development + ui-styling + frontend-design
  - designer (agent) oversees all three

Data Operations:
  - forge (agent) + xlsx + pdf
  - For large datasets, add appropriate integration skill

Full Stack Features:
  - supabase-netlify + frontend-development
  - builder (agent) executes

Integration Projects:
  - ticketing-api | crm-api | catalog-tool
  - n8n-workflow-builder for building automations
  - n8n-workflows for patterns/reference
  - forge for large syncs
```

## Quick Lookup

### "I need to work with..."

| Topic | Load These Skills |
|-------|-------------------|
| React components | frontend-development, ui-styling |
| API integrations | [specific]-api, n8n-workflows |
| n8n automations | n8n-workflow-builder, n8n-workflows |
| MCP servers | mcp-builder |
| Data sync | forge, relevant API skill |
| your BIM tool add-ins | domain-dev, professor |
| Android apps | android-kotlin |
| Course content | education-LMS |
| PR/commits | pr-workflow, git-pushing |
| File processing | xlsx, docx, pdf |
| Testing | webapp-testing |

---

## Growth Monitoring

### Active Monitoring Triggers

```yaml
Monitor During Every Session:
  - Folder file counts (warn at >15 files)
  - Naming conflicts (file.md + file/)
  - Agent coverage gaps
  - Repeated manual patterns (→ new agent candidate)
  - Cross-cutting concerns across agents
```

### Quarterly Expansion Review

```yaml
Review Checklist:
  - [ ] Skills added since last review
  - [ ] Skills loaded but never used (remove?)
  - [ ] New patterns that need skills
  - [ ] Agent responsibilities grown beyond scope
  - [ ] Folder structure depth (max 4 levels)
  - [ ] Files per folder (optimal 5-10)

Growth Metrics:
  - Total skills: [count]
  - New this quarter: [count]
  - Deprecated: [count]
  - Agent count: [count]
  - Coverage gaps identified: [list]
```

### Agent Factory Triggers

When to suggest new agent creation:

```yaml
Automatic Triggers:
  - Same pattern appears 3+ times in session
  - Manual monitoring required that could be automated
  - Cross-cutting concern spans 2+ existing agents
  - Specialized domain knowledge needed repeatedly
  - Pre/post processing always needed for certain tasks

Suggestion Format:
  Agent Name: [proposed-name]
  Purpose: [one-line description]
  Triggers: [when deployed]
  Responsibilities: [what it does]
  Why Needed: [specific evidence from current work]
  Related Agents: [which existing agents it works with]
```

### Folder Organization Thresholds

```yaml
Action Thresholds:
  5-10 files: Optimal - no action needed
  11-15 files: Monitor - consider subfolder
  16-20 files: Plan - create subfolder structure
  21+ files: Critical - must reorganize immediately

Subfolder Creation Rules:
  1. Group by function/purpose
  2. Create index.md for navigation
  3. Update all skill references
  4. Update CLAUDE.md router table
```

### Inventory Health Check

Run before major skill work:

```bash
# Check skill inventory health
- Total skills vs documented count match?
- All agent files exist?
- No orphaned files (not in router)?
- No naming conflicts?
- Folder depths within limits?
```

---

*Skill Shopping Guide v2.1 - With Growth Monitoring*
