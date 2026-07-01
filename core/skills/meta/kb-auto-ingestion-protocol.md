---
name: kb-auto-ingestion-protocol
description: "Automated knowledge base ingestion workflow for bulk data dumps. Handles triage, parsing, vault integration, skill assignment, index updates, and orphan prevention. Use when: (1) User provides new knowledge files (backend docs, architecture guides, API references), (2) Multi-file KB upgrades (2+ documents, 1000+ lines), (3) Agent capability expansion requiring new skills/patterns. Triggers: 'data dump', 'kb upgrade', 'new knowledge base', 'integrate these docs', 'parse this knowledge'."
trigger_keywords: "data dump, kb upgrade, knowledge base, integrate docs, parse knowledge, bulk ingestion"
version: 1.0
created: 2026-02-15
disable-model-invocation: true
context: fork
---

# KB Auto-Ingestion Protocol v1.0

> **Purpose:** Fully automated knowledge base ingestion for bulk data dumps
> **Scope:** 7-stage pipeline from file delivery → vault integration → agent deployment
> **Zero-Touch Goal:** CKO deployed, skills assigned, memory updated, wiki linked, 0% orphans

---

## When to Trigger

**Explicit User Requests:**
- "Here's a data dump to ingest"
- "Integrate these backend docs into the vault"
- "Parse this knowledge for the coding department"
- "New KB upgrade for [project/domain]"

**Automatic Detection:**
- User provides 2+ knowledge files (>1000 lines combined)
- File types: `.md`, `.txt`, architectural specs, API references
- Context mentions: "upgrade", "knowledge base", "documentation", "reference material"

**NOT for:**
- Single-file quick reference (<500 lines)
- Session-specific context (temporary info)
- User preferences or settings (goes to USER.md)
- Code implementation files (goes to projects folder)

---

## 7-Stage Auto-Ingestion Pipeline

### Stage 1: RECEIVE & VALIDATE (Auto)

**Actions:**
1. Count files provided by user
2. Calculate total line count
3. Detect file types and formats
4. Identify target project/domain from context
5. Check for existing vault knowledge (dedup scan)

**Output:**
```
📦 KB INGESTION INITIATED

Files: 2 files, 2,974 lines total
Format: Markdown (architectural specs)
Project: ExampleProject (a client project)
Existing Knowledge: 9 vault docs found (1,300 lines)
Dedup Risk: Medium (checking for overlap)
```

**Automation:** Read all files using chunked Read (offset/limit for large files), extract metadata, scan `memory/Projects/` for existing notes.

---

### Stage 2: TRIAGE & CLASSIFY (CKO Auto-Deploy)

**CKO Agent Spawned Automatically** when Stage 1 completes.

**CKO Actions:**
1. Classify content type: Patterns | Skills | Projects | Preferences
2. Map to vault structure: `memory/Patterns/`, `memory/Skills-Learned/`, `memory/Projects/`
3. Identify skill extraction candidates (implementation guides vs conceptual patterns)
4. Detect agent capability gaps (which agents need this knowledge?)
5. Flag deduplication targets (consolidate vs new file?)

**Output:**
```
🔍 CKO CLASSIFICATION

Content Breakdown:
- 6 architectural patterns (→ Patterns/)
- 2 implementation skills (→ Skills-Learned/)
- 5 skill guides (→ skills/ folders)
- 0 user preferences (skip USER.md)

Agent Impact:
- builder: 4 new skills needed (Supabase, OpenAI, Claude)
- vp-engineering: 1 new skill (coding conventions)
- forge: 0 (no data-specific patterns)

Dedup Targets:
- ExampleProject backend-architecture.md: CONSOLIDATE (add cross-refs)
```

**Automation:** CKO uses pattern matching on content structure, keyword extraction, and existing vault scan to classify. No human input required.

---

### Stage 3: PARSE & EXTRACT (Parallel Processing)

**Actions (parallelized across 3 work streams):**

**Stream A: Vault Pattern Extraction**
- Extract architectural patterns (6 files)
- Generate frontmatter (tags, project, type)
- Apply tag governance (MAX 4 TAGS, folder tag required)
- Write to `memory/Patterns/` with wiki-link format
- **Tag Whitelist Check:** Ensure all tags match `skills/meta/memory-tag-governance.md`

**Stream B: Vault Skills Extraction**
- Extract implementation skills (2 files)
- Document step-by-step procedures
- Write to `memory/Skills-Learned/`
- Cross-reference to Pattern notes

**Stream C: Skill Guide Creation**
- Extract executable skill guides (5 files)
- Determine skill folder: `stacks/` | `integrations/` | `workflows/`
- Format with Purpose, Owner, Key Content, Routing Keywords
- Write to appropriate `skills/` subfolder

**Output:**
```
🔧 PARSING COMPLETE

Vault Patterns: 6 files created (843 lines)
  ✅ Supabase-RLS-Architecture.md
  ✅ Job-Based-Backend-Pattern.md
  ✅ Immutable-Document-Pattern.md
  ✅ RAG-Correction-Feedback-Loop.md
  ✅ OpenAI-Structured-Outputs.md
  ✅ Next-JS-App-Router-API-Patterns.md

Vault Skills: 2 files created (302 lines)
  ✅ Supabase-Vector-Search.md
  ✅ Zod-JSON-Schema-Pipeline.md

Skill Guides: 5 files created (888 lines)
  ✅ skills/stacks/supabase-rls-implementation.md
  ✅ skills/stacks/supabase-vector-search-implementation.md
  ✅ skills/integrations/openai-pdf-extraction.md
  ✅ skills/integrations/anthropic-claude-coaching.md
  ✅ skills/workflows/backend-agent-conventions.md

Tag Compliance: 100% (all tags whitelisted)
```

**Automation:** Multi-threaded Write operations, frontmatter auto-generation using templates, tag validation against `memory-tag-governance.md`.

---

### Stage 4: SKILL ASSIGNMENT (Agent Routing)

**Actions:**
1. For each skill guide created in Stage 3, assign owner agent
2. Use decision tree:
   - Implementation code → builder
   - UI/UX specs → designer
   - Data operations → forge
   - BIM/your BIM tool → professor
   - Process/standards → vp-engineering
   - Security/review → guardian
3. Update `agents/index.md` with explicit assignment table
4. Verify 0% orphan rate (every skill has owner)

**Output:**
```
👥 SKILL ASSIGNMENT

5 skills assigned:
  builder (4 skills):
    - supabase-rls-implementation.md
    - supabase-vector-search-implementation.md
    - openai-pdf-extraction.md
    - anthropic-claude-coaching.md

  vp-engineering (1 skill):
    - backend-agent-conventions.md

Orphan Rate: 0% (5/5 assigned)
agents/index.md: UPDATED (assignment table appended)
```

**Automation:** Pattern matching on skill content (keywords: "SQL", "API", "code", "conventions"), auto-append to `agents/index.md` using Edit tool.

---

### Stage 5: INDEX UPDATES (Wiki Integration)

**Actions:**
1. Update skill folder indexes: `skills/stacks/index.md`, `skills/integrations/index.md`, `skills/workflows/index.md`
2. Add routing keywords to each index entry
3. Update project index: `memory/Projects/{Project}/index.md`
4. Create cross-reference section in project notes (wiki links)
5. Update `memory/Projects/{Project}/backend-architecture.md` with KB references

**Output:**
```
📚 INDEX INTEGRATION

Skill Indexes Updated (3):
  ✅ skills/stacks/index.md (+2 entries)
  ✅ skills/integrations/index.md (+2 entries)
  ✅ skills/workflows/index.md (+1 entry)

Project Indexes Updated (2):
  ✅ memory/Projects/ExampleProject/index.md (+13 references)
  ✅ memory/Projects/ExampleProject/backend-architecture.md (wiki links added)

Routing Chain Verified:
  CLAUDE.md → skills/stacks/index.md → supabase-rls-implementation.md ✅
  CLAUDE.md → skills/integrations/index.md → openai-pdf-extraction.md ✅
  CLAUDE.md → skills/workflows/index.md → backend-agent-conventions.md ✅
```

**Automation:** Use Edit tool to append to existing index.md files, verify routing keywords match CLAUDE.md trigger patterns.

---

### Stage 6: AGENT INTEGRATION VERIFICATION (CKO Quality Gate)

**CKO Agent Performs:**
1. **Discoverability Test:** For each skill, simulate keyword search → index.md → skill file
2. **Invocation Path Test:** Verify agent can load skill when triggered
3. **Agent Awareness Test:** Check if assigned agent's description references domain
4. **Cross-Reference Test:** Verify all wiki links resolve (no broken [[links]])
5. **Orphan Prevention Test:** Scan for skills without agent assignment, patterns without project links

**Output:**
```
✅ CKO QUALITY GATE PASSED

Discoverability: 5/5 skills routable via index
Invocation Paths: 5/5 verified (keyword → index → skill)
Agent Awareness: 5/5 agents reference domain in description
Cross-References: 21/21 wiki links resolve
Orphan Prevention: 0 orphaned skills, 0 orphaned patterns

Non-Blocking Recommendations:
  - Consider adding "RAG system" keyword to builder description
  - Update vp-engineering KPIs to include backend conventions adherence
  - Create skill deprecation process for future schema evolution
```

**Automation:** CKO agent spawned in background, runs verification suite, outputs pass/fail + recommendations.

---

### Stage 7: MEMORY CONSOLIDATION (Background)

**Actions:**
1. Trigger memory consolidation for new vault notes
2. Generate embeddings for all 13 new files
3. Update `memory/index.json` with new note metadata
4. Run deduplication check (merge similar patterns if detected)
5. Update memory metrics (total notes, coverage %, tags distribution)

**Output:**
```
🧠 MEMORY CONSOLIDATION

Embeddings Generated: 13 files (384-dim MiniLM vectors)
Index Updated: memory/index.json (+13 entries)
Deduplication: 0 merges needed (all unique content)
Memory Metrics:
  - Total vault notes: 156 → 169 (+13)
  - Coverage: Backend architecture 54% → 78% (+24%)
  - Tag distribution: [projects: 42, patterns: 67, skills-learned: 35, org: 25]

Consolidation Time: 3.2 seconds
```

**Automation:** Background process, no blocking, uses `skills/meta/memory-consolidation.md` protocol.

---

## Auto-Trigger Configuration

**Add to CLAUDE.md Quick Triggers:**

| Trigger | Action | Skill |
|---------|--------|-------|
| "data dump", "kb upgrade", "integrate these docs" | Auto KB ingestion (7-stage pipeline) | `skills/meta/kb-auto-ingestion-protocol.md` |

**Enforcement:** When user provides 2+ knowledge files (>1000 lines), gate MUST auto-spawn CKO + execute pipeline without asking for permission.

---

## Orphan Prevention Rules

**Zero-Tolerance Policy:**

1. **Skill Orphans:** Every skill guide MUST have agent assignment in `agents/index.md`
2. **Pattern Orphans:** Every pattern note MUST link to project context in `memory/Projects/{Project}/index.md`
3. **Memory Orphans:** Every vault note MUST have valid tags (folder tag + max 3 software tags)
4. **Index Orphans:** Every skill file MUST appear in its folder's `index.md` with routing keywords

**Verification:** Stage 6 CKO quality gate blocks completion if orphan rate >0%.

---

## Performance Targets

| Metric | Target | Measurement |
|--------|--------|-------------|
| Total Pipeline Time | <30 seconds | Stage 1 start → Stage 7 completion |
| CKO Deployment | <5 seconds | Stage 2 spawn → first action |
| Skill Assignment Accuracy | 100% | All skills assigned to correct agent |
| Index Update Success | 100% | All routing keywords functional |
| Orphan Rate | 0% | No orphaned skills/patterns/notes |
| Wiki Link Integrity | 100% | All [[links]] resolve |
| Memory Consolidation | Background | No blocking, <200ms startup |

---

## Error Recovery

**Stage Failure Handling:**

| Stage | Failure Mode | Recovery Action |
|-------|-------------|-----------------|
| 1 | File read error | Retry with chunked Read (offset/limit) |
| 2 | CKO spawn failure | Fallback to conductor with CKO prompts |
| 3 | Tag governance violation | Auto-correct to nearest whitelisted tag |
| 4 | Skill assignment ambiguity | Flag for human review, default to builder |
| 5 | Index update conflict | Create new section, preserve existing content |
| 6 | Quality gate failure | Halt pipeline, report issues, require manual fix |
| 7 | Embedding generation error | Queue for retry, continue pipeline |

---

## Output Format (User-Facing)

**Final Report:**

```markdown
## ✅ KB INGESTION COMPLETE

**Pipeline Executed:** 2026-02-15 at 23:47:12
**Duration:** 18.3 seconds
**Files Processed:** 2 files, 2,974 lines

---

### 📊 Summary

| Category | Created | Updated | Orphaned |
|----------|---------|---------|----------|
| Vault Patterns | 6 | 0 | 0 |
| Vault Skills | 2 | 0 | 0 |
| Skill Guides | 5 | 0 | 0 |
| Index Files | 0 | 5 | 0 |
| Project Notes | 0 | 2 | 0 |

**Total Impact:** 13 files created, 5 indexes updated, 2 project notes enhanced
**Orphan Rate:** 0% (zero-tolerance policy enforced)

---

### 🎯 Agent Assignments

| Agent | New Skills | Domain |
|-------|-----------|--------|
| builder | 4 | Supabase, OpenAI, Claude API |
| vp-engineering | 1 | Backend coding conventions |

---

### 🔗 Project Integration

**Project:** ExampleProject (a client project)
**Cross-References Added:** 25 wiki links
**Deliverable Coverage:** 5/5 engagement deliverables enabled
**Vault Gap Coverage:** 54% → 78% (+24%)

---

### ✅ Quality Gates

- [x] CKO verification passed (5/5 skills routable)
- [x] All wiki links resolve (21/21 valid)
- [x] Tag governance compliance (100%)
- [x] Index routing functional (3/3 indexes updated)
- [x] Memory consolidation queued (background)

---

**Ready for Deployment:** All agents can now access new knowledge.
**Next Action:** Run `/backup` to commit 18 changed files to GitHub.
```

---

## Integration with Existing Protocols

**Memory System v6.0:**
- Uses hybrid search for deduplication detection
- Applies tag governance rules
- Triggers consolidation in background

**Secretary Auto-Tracking:**
- Does NOT spawn secretary for KB ingestion (no client-facing actions)
- Only spawns when deliverables tied to client timeline events

**Growth Monitor:**
- Captures "KB ingestion pattern" if >5 files processed
- Recommends skill composition opportunities

**Backup Automation:**
- KB ingestion does NOT auto-commit
- User must explicitly run `/backup` to push changes
- Prevents accidental commits of incomplete ingestion

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-15 | Initial protocol (7-stage pipeline, CKO auto-deploy, orphan prevention) |

---

*KB Auto-Ingestion Protocol v1.0 | Zero-Touch Knowledge Integration | Approved 2026-02-15*
