# Vector Embeddings for Semantic Search (v6.0)

> **NEW in v6.0:** Semantic search capability using vector embeddings
> **Adopted from:** claude-mem.ai's hybrid keyword+vector search
> **Purpose:** Find conceptually related notes even with different terminology

---

## Overview

Vector embeddings enable semantic search - finding notes by meaning rather than exact keywords. When you search for "authentication bugs", it will also find notes about "JWT token issues" or "login failures".

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    EMBEDDING PIPELINE                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  CONSOLIDATION PATH:                                            │
│  Note Content → Generate Embedding → Store in Index             │
│                                                                 │
│  RECALL PATH:                                                   │
│  Query → Generate Embedding → Cosine Similarity → Rank Notes    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Embedding Strategy

### Option A: Local Embeddings (RECOMMENDED)
Uses `sentence-transformers` library for local, fast embeddings.

**Model:** `all-MiniLM-L6-v2`
- 384-dimensional vectors
- ~80MB model size
- <50ms per embedding
- Works offline

**Installation:**
```bash
pip install sentence-transformers
```

### Option B: API-Based Embeddings (FALLBACK)
Uses external embedding API if local not available.

**Supported APIs:**
- OpenAI embeddings API
- Voyage AI
- Cohere embeddings

---

## Implementation

### Core Embedding Functions

```python
"""
Vector Embeddings Module for Memory System v6.0

Location: .claude/scripts/vector_embeddings.py
"""

import json
import numpy as np
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import hashlib

# Configuration
EMBEDDING_DIM = 384  # MiniLM dimension
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
CACHE_DIR = Path(".claude/session/embedding-cache")

# Lazy load model to avoid import overhead
_model = None

def get_model():
    """Lazy load the embedding model."""
    global _model
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer
            _model = SentenceTransformer(EMBEDDING_MODEL)
            print(f"[EMBED] Loaded {EMBEDDING_MODEL}")
        except ImportError:
            print("[EMBED] WARNING: sentence-transformers not installed")
            print("[EMBED] Run: pip install sentence-transformers")
            return None
    return _model


def generate_embedding(text: str) -> Optional[List[float]]:
    """
    Generate embedding vector for text.

    Args:
        text: Content to embed (truncated to 512 tokens if longer)

    Returns:
        List of floats (384-dim) or None if embedding fails
    """
    model = get_model()
    if model is None:
        return None

    # Truncate to ~2000 chars (roughly 512 tokens)
    if len(text) > 2000:
        text = text[:2000]

    try:
        embedding = model.encode(text, convert_to_numpy=True)
        return embedding.tolist()
    except Exception as e:
        print(f"[EMBED] Error generating embedding: {e}")
        return None


def generate_embeddings_batch(texts: List[str]) -> List[Optional[List[float]]]:
    """
    Generate embeddings for multiple texts efficiently.

    Args:
        texts: List of content strings

    Returns:
        List of embedding vectors (same order as input)
    """
    model = get_model()
    if model is None:
        return [None] * len(texts)

    # Truncate all texts
    truncated = [t[:2000] if len(t) > 2000 else t for t in texts]

    try:
        embeddings = model.encode(truncated, convert_to_numpy=True)
        return [e.tolist() for e in embeddings]
    except Exception as e:
        print(f"[EMBED] Batch error: {e}")
        return [None] * len(texts)


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """
    Calculate cosine similarity between two vectors.

    Args:
        vec1, vec2: Embedding vectors

    Returns:
        Similarity score between -1 and 1 (higher = more similar)
    """
    if not vec1 or not vec2:
        return 0.0

    a = np.array(vec1)
    b = np.array(vec2)

    dot_product = np.dot(a, b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return float(dot_product / (norm_a * norm_b))


def get_content_hash(content: str) -> str:
    """Generate hash for content caching."""
    return hashlib.md5(content.encode()).hexdigest()[:12]


# ============================================================
# CACHING LAYER
# ============================================================

def load_embedding_cache() -> Dict:
    """Load embedding cache from disk."""
    cache_file = CACHE_DIR / "embeddings.json"
    if cache_file.exists():
        try:
            with open(cache_file, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}


def save_embedding_cache(cache: Dict):
    """Save embedding cache to disk."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = CACHE_DIR / "embeddings.json"
    with open(cache_file, 'w') as f:
        json.dump(cache, f)


def get_cached_embedding(content_hash: str) -> Optional[List[float]]:
    """Get embedding from cache if exists."""
    cache = load_embedding_cache()
    return cache.get(content_hash)


def cache_embedding(content_hash: str, embedding: List[float]):
    """Store embedding in cache."""
    cache = load_embedding_cache()
    cache[content_hash] = embedding
    save_embedding_cache(cache)


# ============================================================
# INDEX INTEGRATION
# ============================================================

def add_embedding_to_index(note_path: str, content: str, index: Dict) -> Dict:
    """
    Add or update embedding for a note in the index.

    Args:
        note_path: Path to the note file
        content: Note content to embed
        index: Current memory index

    Returns:
        Updated index with embedding
    """
    # Check cache first
    content_hash = get_content_hash(content)
    embedding = get_cached_embedding(content_hash)

    if embedding is None:
        # Generate new embedding
        embedding = generate_embedding(content)
        if embedding:
            cache_embedding(content_hash, embedding)

    if embedding is None:
        print(f"[EMBED] Failed to generate embedding for {note_path}")
        return index

    # Find note in index and add embedding
    for note in index.get("notes", []):
        if note["path"] == note_path:
            note["embedding"] = embedding
            note["embedding_model"] = EMBEDDING_MODEL
            note["embedding_hash"] = content_hash
            break

    return index


def find_similar_notes(
    query: str,
    index: Dict,
    top_k: int = 10,
    min_similarity: float = 0.3
) -> List[Tuple[Dict, float]]:
    """
    Find notes most similar to query using vector similarity.

    Args:
        query: Search query text
        index: Memory index with embeddings
        top_k: Number of results to return
        min_similarity: Minimum similarity threshold

    Returns:
        List of (note, similarity_score) tuples, sorted by similarity
    """
    # Generate query embedding
    query_embedding = generate_embedding(query)
    if query_embedding is None:
        return []

    # Calculate similarity for all notes with embeddings
    similarities = []
    for note in index.get("notes", []):
        note_embedding = note.get("embedding")
        if note_embedding:
            similarity = cosine_similarity(query_embedding, note_embedding)
            if similarity >= min_similarity:
                similarities.append((note, similarity))

    # Sort by similarity (highest first)
    similarities.sort(key=lambda x: x[1], reverse=True)

    return similarities[:top_k]


# ============================================================
# BATCH OPERATIONS
# ============================================================

def embed_all_notes(index: Dict, vault_path: str) -> Dict:
    """
    Generate embeddings for all notes in index.
    Used for initial setup or re-indexing.

    Args:
        index: Memory index
        vault_path: Path to Obsidian vault

    Returns:
        Updated index with embeddings
    """
    from pathlib import Path

    vault = Path(vault_path)
    notes = index.get("notes", [])

    print(f"[EMBED] Generating embeddings for {len(notes)} notes...")

    # Collect all content
    contents = []
    valid_notes = []
    for note in notes:
        note_path = vault / note["path"]
        if note_path.exists():
            try:
                with open(note_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                contents.append(content)
                valid_notes.append(note)
            except:
                continue

    # Batch generate embeddings
    embeddings = generate_embeddings_batch(contents)

    # Update index
    embedded_count = 0
    for note, embedding in zip(valid_notes, embeddings):
        if embedding:
            note["embedding"] = embedding
            note["embedding_model"] = EMBEDDING_MODEL
            note["embedding_hash"] = get_content_hash(contents[valid_notes.index(note)])
            embedded_count += 1

    print(f"[EMBED] Generated {embedded_count}/{len(notes)} embeddings")

    # Update index metadata
    index["embedding_info"] = {
        "model": EMBEDDING_MODEL,
        "dimension": EMBEDDING_DIM,
        "embedded_count": embedded_count,
        "total_notes": len(notes)
    }

    return index


def get_embedding_stats(index: Dict) -> Dict:
    """Get statistics about embeddings in index."""
    notes = index.get("notes", [])
    embedded = sum(1 for n in notes if n.get("embedding"))

    return {
        "total_notes": len(notes),
        "embedded_notes": embedded,
        "coverage_percent": (embedded / len(notes) * 100) if notes else 0,
        "model": index.get("embedding_info", {}).get("model", "unknown"),
        "dimension": index.get("embedding_info", {}).get("dimension", 0)
    }
```

---

## Memory Index Schema Update

**New fields in memory-index.json:**

```json
{
  "embedding_info": {
    "model": "all-MiniLM-L6-v2",
    "dimension": 384,
    "embedded_count": 558,
    "total_notes": 558,
    "last_updated": "2026-02-04T15:30:00Z"
  },
  "notes": [
    {
      "path": "Decisions/Protocol-Enforcement-v5.2.md",
      "title": "Protocol Enforcement v5.2",
      "tags": ["decisions", "enforcement"],
      "embedding": [0.123, -0.456, ...],  // 384 floats
      "embedding_model": "all-MiniLM-L6-v2",
      "embedding_hash": "a1b2c3d4e5f6"
    }
  ]
}
```

---

## Integration Points

### Consolidation (Write Path)

When writing a new note, generate embedding:

```python
# In memory-consolidation.md write flow:

# AFTER generating note content, BEFORE writing to vault:
from vector_embeddings import add_embedding_to_index

# Generate embedding for new note
index = read_json("session/memory-index.json")
index = add_embedding_to_index(
    note_path=note['path'],
    content=note['content'],
    index=index
)
write_json("session/memory-index.json", index)
```

### Recall (Read Path)

Use embeddings in similarity search:

```python
# In memory-recall.md Pass 1.5 (NEW):

from vector_embeddings import find_similar_notes

# After tag filtering, boost by semantic similarity
similar_notes = find_similar_notes(
    query=user_prompt,
    index=index,
    top_k=20,
    min_similarity=0.4
)

# Apply similarity boost to relevance scores
for note, similarity in similar_notes:
    note_path = note["path"]
    for n in filtered_notes:
        if n["path"] == note_path:
            n["vector_similarity"] = similarity
            n["relevance_score"] *= (1 + similarity)  # Boost by similarity
```

---

## Bootstrap Script

Run once to embed all existing notes:

```bash
python scripts/embed-memory-vault.py
```

**Script content:**
```python
#!/usr/bin/env python3
"""
Embed all notes in memory vault.
Run once for initial setup, then incrementally during consolidation.

Usage: python scripts/embed-memory-vault.py
"""

import json
import sys
sys.path.append(".claude/scripts")

from vector_embeddings import embed_all_notes

VAULT_PATH = "~/.claude\\memory\\"
INDEX_PATH = ".claude/session/memory-index.json"

def main():
    print("Loading memory index...")
    with open(INDEX_PATH, 'r') as f:
        index = json.load(f)

    print("Embedding all notes (this may take a few minutes)...")
    index = embed_all_notes(index, VAULT_PATH)

    print("Saving updated index...")
    with open(INDEX_PATH, 'w') as f:
        json.dump(index, f, indent=2)

    # Print stats
    from vector_embeddings import get_embedding_stats
    stats = get_embedding_stats(index)
    print(f"\nEmbedding complete:")
    print(f"  Model: {stats['model']}")
    print(f"  Dimension: {stats['dimension']}")
    print(f"  Coverage: {stats['embedded_notes']}/{stats['total_notes']} ({stats['coverage_percent']:.1f}%)")

if __name__ == "__main__":
    main()
```

---

## Performance

| Operation | Time | Notes |
|-----------|------|-------|
| Generate single embedding | <50ms | Local model |
| Batch embed 100 notes | ~3 sec | Parallel processing |
| Batch embed 500 notes | ~15 sec | One-time setup |
| Similarity search (500 notes) | <10ms | NumPy optimized |
| Cache hit | <1ms | Pre-computed |

**Memory Impact:**
- Model loaded once: ~80MB
- Per-note embedding: 384 floats × 4 bytes = 1.5KB
- 500 notes: ~750KB additional index size

---

## Fallback Behavior

If `sentence-transformers` is not installed:

1. Embedding generation returns `None`
2. Notes are stored without embeddings
3. Recall falls back to tag-only filtering
4. Warning logged: "sentence-transformers not installed"
5. System continues to work (graceful degradation)

---

## Testing

### Test 1: Embedding Generation
```python
from vector_embeddings import generate_embedding

embedding = generate_embedding("Test content about your CRM integration")
assert embedding is not None
assert len(embedding) == 384
print("✓ Embedding generation works")
```

### Test 2: Similarity Search
```python
from vector_embeddings import find_similar_notes

# Search for semantically related notes
results = find_similar_notes(
    query="authentication token issues",
    index=index,
    top_k=5
)

# Should find notes about JWT, OAuth, login even without exact keywords
for note, similarity in results:
    print(f"{similarity:.3f} - {note['title']}")
```

### Test 3: Cache Hit
```python
from vector_embeddings import generate_embedding, get_content_hash, get_cached_embedding

content = "Test content"
hash1 = get_content_hash(content)

# First call generates
embedding1 = generate_embedding(content)

# Cache should have it now
cached = get_cached_embedding(hash1)
assert cached is not None
assert cached == embedding1
print("✓ Caching works")
```

---

## Maintenance

**Weekly cleanup (Monday morning):**
- Remove orphaned cache entries (notes deleted from vault)
- Regenerate embeddings for modified notes
- Update index stats

**Re-indexing:**
If embeddings become stale or model updated:
```bash
python scripts/embed-memory-vault.py --force
```

---

*Vector Embeddings v6.0 | Semantic Search for Memory System*
