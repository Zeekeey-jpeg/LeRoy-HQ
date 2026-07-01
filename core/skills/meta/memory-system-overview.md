---
user-invocable: false
---

# Long-Term Memory System v6.0 (Full Reference)

> **Extracted from:** CLAUDE.md - Memory System section
> **Version:** v6.0 (Hybrid Keyword+Vector Search)
> **Features:** 10K+ scaling, LRU cache (90%+ hit), tag intersection O(1), domain sharding, vector embeddings, privacy tags, causality tracking
> **Inspired by:** claude-mem.ai hybrid search pattern

---

## Overview

- **v6.0 UPDATE:** Hybrid keyword + vector search for semantic recall
- **NEW:** Privacy tags (`<private>`) stripped during consolidation
- **NEW:** Causality tracking (preceded_by, trigger, followed_by, outcome)
- **NEW:** Token cost awareness in recall output
- **NEW:** Vector embeddings via `all-MiniLM-L6-v2` (384-dim, <50ms per embedding)
- **HOOK-ENFORCED:** Session start (30+ min) triggers recall via enforcement queue
- **SESSION-ISOLATED:** Each chat window loads ONLY its own memories

**Memory Architecture:** See Memory vault -> `Patterns/Memory-System-Architecture.md` for complete data flow.

---

## STRICT TAG RULES v1.0 (HARD CONSTRAINTS)

**Tag Structure (MANDATORY):**
- **Tag 1 (REQUIRED):** Folder tag - `decisions` | `patterns` | `preferences` | `skills-learned` | `projects`
- **Tags 2-4 (OPTIONAL):** Software/integration tags ONLY

**Valid Software Tags:**
```
crm | bim | android | LMS
git | netlify | playwright | supabase | gas
python | memory-system | enforcement | leroy
```

**Valid Project Tags:**
```
org | lms | meta
```

**INVALID Tags (NEVER use):**
- Descriptive: bulletproof, successful, critical, important
- Action: automation, validation, workflow, implementation
- Version: v5, v5.1, v5.2
- Duplicate: hooks, patterns (use folder tag instead)

**MAX 4 TAGS** (1 folder + up to 3 software)

**Full Tag Governance:** See `skills/meta/memory-tag-governance.md` for rules, rationale, and enforcement.

---

## How It Works

**Write Path (Consolidation):**
- Checkpoints -> Consolidate -> Write notes to vault
- Updates index.json automatically
- 100% automatic, no user action

**Read Path (Recall):**
- Session start -> Hook detects -> Sets recall flag
- Claude loads top 5 relevant notes (<200ms)
- Tiered system caches next 10 for expansion
- Updates `last_recall` timestamp

**UX Pattern:** See Memory vault -> `Decisions/Silent-Memory-Loading.md` - Memory loads invisibly, citations appear naturally.

---

## Fixed Paths

| Purpose | Path |
|---------|------|
| **Obsidian Vault** | `~/.claude\memory\` |
| **Memory Index** | `.claude/session/memory-index.json` |
| **Session Cache** | `.claude/session/memory-cache.json` |
| **LRU Cache** | `.claude/session/memory-cache-lru.json` |
| **Domain Shards** | `.claude/session/shards/{project}-shard.json` |

---

## Performance

| Operation | Time | Notes |
|-----------|------|-------|
| Cold start recall | <200ms | First recall in session |
| Cache hit recall | <5ms | LRU cache (90%+ hit rate) |
| Tag intersection | O(1) | Pre-computed 2-3 tag combos |
| Expansion | <20ms | From LRU cache |
| Full search | 2-3 sec | Tier 3 only (rare) |
| **v6.0 New:** | | |
| Vector embedding | <50ms | Per note, local model |
| Semantic similarity | <10ms | 500 notes (NumPy optimized) |
| Embedding cache hit | <1ms | Pre-computed vectors |
| Hybrid search (full) | <200ms | Tag + vector combined |

**Scaling Details:** See Memory vault -> `Patterns/Memory-Scaling-10K.md` for 10,000+ note architecture.

**Smart Filtering:** See Memory vault -> `Patterns/Memory-Smart-Filtering.md` for 5-pass pipeline (O(1) tag intersection).

**Tiered Loading:** See Memory vault -> `Patterns/Memory-Tiered-Loading.md` for 3-tier progressive disclosure.

---

## Skills (See Full Specs)

- `meta/memory-consolidation.md` - Writes to Obsidian + updates index automatically (v6.0: privacy tags, causality)
- `meta/memory-recall.md` - Auto-trigger, smart filtering, tiered loading (v6.0: hybrid search, token cost)
- `meta/memory-organizer.md` - Cleans vault weekly (Monday morning, background)
- `meta/vector-embeddings.md` - Semantic search via vector embeddings (NEW in v6.0)

---

## RAG Sidecar (v6.0 Production Implementation)

The vector embedding system described in v6.0 is implemented as a persistent HTTP sidecar:

| Property | Value |
|----------|-------|
| Script | `~/.claude\tools\vault-rag-sidecar.py` |
| Port | `localhost:7742` |
| Index DB | `~/.claude\memory\vault-index.db` |
| Model | `all-MiniLM-L6-v2` (384-dim, local, <50ms per query) |

**Start:**
```bash
python ~/.claude\tools\vault-rag-sidecar.py
```

**Query endpoint:**
```bash
POST localhost:7742/query
{"q": "query text"}
```

**Reindex after vault changes:**
```bash
POST localhost:7742/reindex
```

**Health check:** `GET http://localhost:7742/status`

This replaces the "described but unconfirmed" embedding status from the pre-v2 audit. The sidecar is the single source of truth for semantic recall — it IS the v6.0 embedding system in production.

**Full documentation:** `skills/integrations/leroy-swarm-v2.md`

---

## Integration

**Auto-triggered by:**
- `hooks/gate-enforcer.py` - **PRIMARY:** Session start detection -> recall enforcement
- RAG Sidecar (`localhost:7742`) - **SEMANTIC RECALL:** Warm context injection at every LeRoy session start
- `routines/morning.md` - Recall at start, consolidate at end
- `@agent-scout` - Consolidates patterns detected
- `@agent-guardian` - Consolidates before commits
- `@agent-conductor` - Recalls before major decisions

---

## Bootstrap (First-Time Setup)

If index.json missing:
```bash
python scripts/build-memory-index.py
```

This scans vault and creates initial index (~5 sec for 100 notes).

---

*Extracted from CLAUDE.md to reduce hub file size. All routing pointers preserved.*
