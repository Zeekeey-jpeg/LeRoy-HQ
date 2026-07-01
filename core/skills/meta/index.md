# Meta Skills

Skills about managing skills, permissions, disambiguation, and universal patterns.

## Keyword Routing
| Keywords | File |
|----------|------|
| agent performance, KPIs, background metrics, agent health | background-agent-performance-kpis.md |
| agent scaling, team sizing, packet distribution, tier scaling | agent-scaling-reference.md |
| auto health, background monitoring, system patrol, self-healing | auto-health-monitor.md |
| context anchor, anchor auto, session anchor, compaction anchor | context-anchor-auto.md |
| context retention, original prompt, compaction, anchor, memory | context-retention.md |
| email branding, email voice, branded communication | email-branding-enforcement.md |
| enforcement queue, action queue, deferred actions | enforcement-queue-handler.md |
| fixed paths, path registry, standard locations | fixed-path-registry.md |
| hybrid recall, vector search, embedding recall | hybrid-recall-integration.md |
| hybrid quick ref, HYBRID RECALL QUICK REF | HYBRID_RECALL_QUICK_REF.md |
| hybrid rollout, embedding deployment, recall migration | hybrid-recall-rollout-guide.md |
| mcp health monitor, server health, mcp status tracking | mcp-health-monitor.md |
| memory hierarchy, tier system, priority loading | memory-hierarchy-implementation.md |
| memory overview, memory system, vault architecture | memory-system-overview.md |
| position zero, enforcement position, pre-gate execution | position-zero-enforcement.md |
| predictive todo, smart todo, context-aware tasks | predictive-todo-system.md |
| secretary auto, action tracking, timeline logging | secretary-auto-tracking.md |
| session gate, gate protocol, enforce routing, first action | session-gate.md |
| skill reference validator, dead links, skill verification | skill-reference-validator.md |
| subprocess timeout, process timeout, subprocess protocol, shell call | subprocess-timeout-protocol.md |
| system health, health check, diagnostic scan | system-health-check.md |
| token goals, efficiency targets, burn rate management | token-goal-management.md |
| vector embeddings, semantic search, embedding generation | vector-embeddings.md |
| working memory, memory manager, session memory | working-memory-manager.md |
| create agent, new agent, agent template, agent creator | agent-creator.md |
| sub-agent, background agent, spawn agent, parallel agent, Task tool | sub-agent-spawning.md |
| create skill, new skill, skill template, write skill | skill-creator.md |
| install skill, classify skill, skill shopping, skill inventory | skill-shopping.md |
| pagination, MCP pagination, fetch all pages, complete dataset | mcp-pagination.md |
| auto retry, exponential backoff, retry wrapper, transient errors | mcp-auto-retry.md |
| mcp registry, discover mcps, tool inventory, mcp capabilities | mcp-registry.md |
| fetch all, pagination wrapper, auto paginate, universal fetch | mcp-pagination-wrapper.md |
| mcp performance, analytics, latency tracking, mcp metrics | mcp-performance-analytics.md |
| mcp health, health dashboard, server status, mcp monitoring | mcp-health-dashboard.md |
| data integrity, complete data, verify count, COUNT FETCH VERIFY | data-integrity-protocol.md |
| permissions, can I delete, approval needed, autonomous | permissions.md |
| ambiguous request, which system, clarify system, incomplete | request-disambiguation.md |
| calendar, scheduling, day of week, date verification | calendar-handling.md |
| auto build, auto skill, context high, pattern detected, skill fork, folder growth | auto-builder.md |
| skill vs memory, what is skill, what is memory, knowledge management, graduation | skill-vs-memory.md |
| memory consolidate, write notes, checkpoint to vault | memory-consolidation.md |
| memory recall, load notes, auto-recall, session start | memory-recall.md |
| memory cleanup, organize vault, archive notes, weekly cleanup | memory-organizer.md |
| error recall, check errors, known failures, prevent errors | error-recall.md |
| workflow complexity, scoring, threshold, automation | workflow-complexity-classifier.md |
| suggestion, surface workflow, recommend, once per session | suggestion-surfacing.md |
| plan before execute, mandatory planning, phase gating, approve before run | mandatory-phase-gating.md |
| blocklist allowlist, safety validation, dual list, zero tolerance | dual-list-safety-pattern.md |
| scenario matrix, test matrix, variable combinations, edge cases | scenario-matrix-design.md |
| simulation report, structured output, highlights scoring gaps | simulation-report-template.md |
| framework docs, documentation standard, 7-part structure | framework-documentation-standard.md |
| risk classification, 3-tier risk, HIGH MEDIUM LOW, severity matrix | risk-classification-framework.md |
| rollout template, 4-week plan, implementation roadmap | four-week-framework-rollout-template.md |
| performance targets, measurable objectives, target max tracking | quantified-performance-targets.md |
| simulation testing, 4-phase testing, test methodology | simulation-testing-methodology.md |
| skill composition, combine skills, build frameworks, reuse patterns | skill-composition-for-frameworks.md |
| agent tools, tool validation, governance enforcement, pre-spawn | agent-tool-validator.md |
| agent org titles, position titles, title mapping | agent-org-titles.md |
| domain prediction, predictive loading, context prediction, shard loading | domain-predictor.md |
| memory concurrency, vault locking, concurrent writes, LeRoy memory | memory-concurrency.md |
| memory tag governance, tag rules, folder tags, software tags | memory-tag-governance.md |
| orphan detection, memory orphans, broken links, vault orphans | orphan-detection.md |
| protocol positions, execution flow, position architecture, 4-position | protocol-position-architecture.md |
| secretary memory, meeting context, pre-meeting prep, context aggregation | secretary-memory.md |
| silent memory, invisible loading, UX memory, context UX | silent-memory-design.md |
| smart todo, cross-reference todo, auto completion, todo tracking | smart-todo-tracking.md |
| super power plan, compare approaches, parallel plans, plan mode | super-power-plan-mode.md |
| plan mode report, comparison template, plan output | super-power-plan-mode-report-template.md |
| simulation report output, super power report, simulation template | super-power-report-template.md |
| simulation safety, read-only boundary, safety validator | super-power-safety.md |
| todowrite, todo protocol, mandatory todo, 3+ steps | todowrite-protocol.md |
| quick trigger maintenance, add trigger, modify trigger | quick-trigger-maintenance.md |
| deadline calendar, auto calendar, deadline to event | deadline-calendar-automation.md |
| skill composer, auto skill, simple skill, quick skill | skill-composer.md |
| kb ingestion, data dump, integrate docs, parse knowledge | kb-auto-ingestion-protocol.md |
| debate, council debate, decide, dilemma, torn between, should I | debate-by-council.md |

## Available Skills

### Core Infrastructure
- **context-retention.md** - Original prompt capture, context anchor, compaction survival
- **context-anchor-auto.md** - Automatic context anchor generation and recovery after compaction
- **session-gate.md** - Mandatory gate protocol enforcing routing before any action
- **position-zero-enforcement.md** - Pre-gate execution framework, enforcement.todo queue handler
- **enforcement-queue-handler.md** - Deferred action queue processing at Position #0
- **mandatory-phase-gating.md** - Plan-before-execute pattern for frameworks (no skipping)
- **agent-creator.md** - Complete guide for creating agents in Claude Code format
- **sub-agent-spawning.md** - Infrastructure for background sub-agents (Task tool patterns)
- **agent-scaling-reference.md** - Agent team sizing, tier scaling, packet distribution patterns
- **background-agent-performance-kpis.md** - Background agent performance metrics, KPI tracking
- **fixed-path-registry.md** - Standard path locations for all system files
- **working-memory-manager.md** - Session-level working memory management
- **agent-tool-validator.md** - Pre-spawn validation and post-execution monitoring for org governance
- **agent-org-titles.md** - Agent position title mappings for gate display
- **domain-predictor.md** - Pre-load context based on prompt-history pattern prediction
- **protocol-position-architecture.md** - Reference for 4-position execution flow system
- **todowrite-protocol.md** - Mandatory todo creation protocol for 3+ step tasks
- **quick-trigger-maintenance.md** - Process for adding and modifying quick triggers
- **deadline-calendar-automation.md** - Automatic calendar event creation from deadlines

### Skill Management
- **skill-creator.md** - Templates and guidelines for creating new skill files
- **skill-shopping.md** - Skill installation, classification, and inventory management
- **skill-vs-memory.md** - Decision criteria for skill vs memory, graduation pathway, edge cases
- **skill-reference-validator.md** - Dead link detection, skill verification, reference validation
- **auto-builder.md** - Automatic skill/agent generation, growth monitor integration
- **skill-composer.md** - Auto-generate simple skills in under 60 seconds
- **kb-auto-ingestion-protocol.md** - Automated 7-stage KB ingestion (CKO, vault, skills, indexes, orphan prevention)

### MCP Integration Ecosystem (v1.0)
- **mcp-pagination.md** - Universal MCP pagination patterns, page size reference, iteration logic
- **mcp-auto-retry.md** - Exponential backoff retry wrapper, transient error handling, Retry-After support
- **mcp-registry.md** - Auto-discovery of MCP servers, tool capability mapping, registry management
- **mcp-pagination-wrapper.md** - Universal fetch_all() function, auto-detect pagination style
- **mcp-performance-analytics.md** - Performance logging, latency tracking, WoW comparison reports
- **mcp-health-dashboard.md** - Server health monitoring, UP/DEGRADED/DOWN status, background daemon
- **mcp-health-monitor.md** - Background MCP server health monitoring and alerting

### Universal Patterns
- **data-integrity-protocol.md** - COUNT → FETCH → VERIFY pattern, verification checklists, red flags
- **dual-list-safety-pattern.md** - Blocklist + allowlist safety validation (zero tolerance)
- **risk-classification-framework.md** - 3-tier risk model (HIGH/MEDIUM/LOW) with severity matrix
- **quantified-performance-targets.md** - Framework for specifying measurable objectives (Target/Max)
- **permissions.md** - Autonomous permissions, external system permissions, deletion rules
- **request-disambiguation.md** - Ambiguous terms, clarification format, MCP availability
- **calendar-handling.md** - Date verification rules, 2026 reference table, day-of-week issues
- **email-branding-enforcement.md** - Branded email protocol, voice consistency, Step 3.5 enforcement
- **auto-health-monitor.md** - Background system health monitoring, self-healing protocols
- **system-health-check.md** - System diagnostic scans, health checks, component verification
- **token-goal-management.md** - Efficiency targets, burn rate tracking, token budget management
- **predictive-todo-system.md** - Context-aware todo generation, smart task tracking

### Memory System
- **memory-consolidation.md** - Checkpoint → Obsidian writes, auto-triggered consolidation, workflow_metadata support
- **memory-recall.md** - v5.1 auto-recall, smart filtering, tiered loading, suggestion surfacing integration
- **memory-organizer.md** - Weekly vault cleanup, archive old notes, consolidate duplicates
- **memory-system-overview.md** - Complete memory architecture overview, vault structure, integration patterns
- **memory-hierarchy-implementation.md** - Tier system for memory loading, priority-based recall
- **error-recall.md** - Proactive error prevention, check memory before execution
- **hybrid-recall-integration.md** - Vector + keyword hybrid search, semantic memory recall
- **HYBRID_RECALL_QUICK_REF.md** - Quick reference guide for hybrid recall system
- **hybrid-recall-rollout-guide.md** - Deployment guide for embedding-based recall
- **vector-embeddings.md** - Semantic search embeddings, all-MiniLM-L6-v2 integration
- **secretary-auto-tracking.md** - Automatic action tracking, timeline logging, legal coordination
- **memory-concurrency.md** - Concurrent write protocol for LeRoy memory vault
- **memory-tag-governance.md** - Tag rules enforcement, folder tags, max 4 tags
- **orphan-detection.md** - Weekly vault orphan detection and broken link scanning
- **secretary-memory.md** - Digital secretary context aggregation and pre-meeting prep
- **silent-memory-design.md** - UX pattern for invisible context loading at session start

### Self-Learning Suggestion Engine (v1.0)
- **workflow-complexity-classifier.md** - Scoring algorithm for workflow complexity (simple/medium/complex)
- **suggestion-surfacing.md** - Context-aware workflow suggestions, once per session per workflow
- **smart-todo-tracking.md** - Intelligent todo cross-referencing with auto-completion detection

### Framework Development
- **framework-documentation-standard.md** - 7-part structure for all framework docs (Header → Examples)
- **four-week-framework-rollout-template.md** - Reusable weekly breakdown (Foundation → Launch)
- **skill-composition-for-frameworks.md** - How to combine existing skills into new frameworks
- **simulation-testing-methodology.md** - 4-phase testing approach (Planning → Report)
- **super-power-plan-mode.md** - Plan mode variant: generate and compare multiple approaches in parallel
- **super-power-plan-mode-report-template.md** - Report template for plan mode comparative analysis
- **super-power-report-template.md** - Structured output format for simulation results
- **super-power-safety.md** - Read-only boundary enforcement for simulation framework

<!-- linked by alignment fix 2026-05-30 -->
## Additional Skills (linked 2026-05-30)
- [agent-feedback-loop.md](agent-feedback-loop.md) — Agent quality monitoring / schema registry
- [error-remediation.md](error-remediation.md) — Decision tree for Bash failures
- [fork-dispatch.md](fork-dispatch.md) — Fork dispatch pattern for parallel agent work
- [pii-pre-send.md](pii-pre-send.md) — PII detection guard for outbound Gmail/Telegram
- [quick-trigger-registry.md](quick-trigger-registry.md) — Complete quick-trigger table
