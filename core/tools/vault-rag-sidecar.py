"""
vault-rag-sidecar.py - LeRoy Swarm v2 RAG Sidecar
===================================================
HTTP sidecar that indexes the YourCo memory vault using sentence-transformers
and serves semantic search queries to LeRoy agents.

Dependencies:
    pip install sentence-transformers flask watchdog

Model: sentence-transformers/all-MiniLM-L6-v2 (~90MB download on first run)
Port:  7742 (localhost only)
DB:    ~/.claude\\memory\\vault-index.db

Ported from UniBOT Rust implementation (embeddings.rs + memory.rs).
"""

import atexit
import os
import re
import sys
import json
import time
import struct
import sqlite3
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import numpy as np

from flask import Flask, request, jsonify

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

VAULT_PATH = Path(r"~/.claude\memory")
DB_PATH    = VAULT_PATH / "vault-index.db"

# Second indexed root (Track B, System 101 KB) — deliberately narrow: only this
# one skills/domains/ subdirectory, NOT a blanket "index all of skills/" change.
# Kept separate from VAULT_PATH so the memory vault's Decisions/Patterns/tag-whitelist
# schema is never touched; distinguished at query time by file_path prefix rather
# than a new DB column (chunks table stays the same across both roots).
SYSTEM101_PATH = Path(r"~/.claude\skills\domains\system-101")
LOG_PATH   = Path(r"~/.claude\session\rag-sidecar.log")

MODEL_NAME       = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIM    = 384
PORT             = 7742
HOST             = "127.0.0.1"
PID_PATH         = Path(r"~/.claude\session\rag-sidecar.pid")

# Scoring — threshold disabled by default (pure top-k ranking is more accurate)
# Set SIMILARITY_THRESHOLD_ENABLED=true + SIMILARITY_THRESHOLD=0.35 to restore hard cutoff
THRESHOLD_ENABLED    = os.environ.get("SIMILARITY_THRESHOLD_ENABLED", "false").lower() == "true"
SIMILARITY_THRESHOLD = float(os.environ.get("SIMILARITY_THRESHOLD", "0.35"))
CONTENT_BOOST        = 0.15
FILENAME_BOOST       = 0.10
TOP_K_DEFAULT        = 5

# Query embedding LRU cache (avoids re-embedding identical queries)
EMBED_CACHE_MAX      = int(os.environ.get("EMBED_CACHE_MAX", "256"))

# Batch embedding during indexing (sentence-transformers native batching)
EMBED_BATCH_SIZE     = int(os.environ.get("EMBED_BATCH_SIZE", "32"))

# Real-time dedup guard (Phase 8)
DEDUP_ENABLED    = os.environ.get("DEDUP_ENABLED",   "false").lower() == "true"
DEDUP_THRESHOLD  = float(os.environ.get("DEDUP_THRESHOLD", "0.95"))

# Query rewriting (Phase 9) — LLM expands query before vector search
QUERY_REWRITE    = os.environ.get("QUERY_REWRITE", "false").lower() == "true"

# ---------------------------------------------------------------------------
# Single-instance guard (PID lock)
# ---------------------------------------------------------------------------

def _pid_is_live(pid: int) -> bool:
    """Return True if a process with this PID is currently running."""
    try:
        import psutil
        return psutil.pid_exists(pid)
    except ImportError:
        pass
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def acquire_pid_lock() -> None:
    """
    Enforce single-instance startup. Writes PID_PATH at launch.
    If a live PID file already exists, exits immediately — prevents
    duplicate instances from all callers (Task Scheduler, watchdog,
    memory-organizer, manual runs, etc.).
    Stale PID files (dead process) are cleared automatically.
    """
    if PID_PATH.exists():
        try:
            old_pid = int(PID_PATH.read_text().strip())
        except (ValueError, OSError):
            old_pid = None

        if old_pid is not None and old_pid != os.getpid():
            if _pid_is_live(old_pid):
                # Real duplicate — bail out cleanly
                # Use print here because logging isn't initialised yet
                print(
                    f"[vault-rag-sidecar] DUPLICATE BLOCKED: another instance is already "
                    f"running (PID {old_pid}). Exiting. "
                    f"To force a restart, delete: {PID_PATH}",
                    flush=True,
                )
                sys.exit(0)
            else:
                print(
                    f"[vault-rag-sidecar] Stale PID file found (PID {old_pid} is dead) — "
                    f"clearing and continuing.",
                    flush=True,
                )

    PID_PATH.parent.mkdir(parents=True, exist_ok=True)
    PID_PATH.write_text(str(os.getpid()))
    atexit.register(_release_pid_lock)


def _release_pid_lock() -> None:
    """Remove PID file on clean shutdown (registered via atexit)."""
    try:
        if PID_PATH.exists() and PID_PATH.read_text().strip() == str(os.getpid()):
            PID_PATH.unlink()
    except OSError:
        pass


# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("rag-sidecar")

# ---------------------------------------------------------------------------
# Enhanced module imports (config-gated, all degrade gracefully if missing)
# ---------------------------------------------------------------------------

sys.path.insert(0, str(Path(__file__).parent))

try:
    from rag_chunker import chunk_text as _chunk_text_v2
    _CHUNKER_AVAILABLE = True
except ImportError:
    _CHUNKER_AVAILABLE = False

try:
    from rag_llm import get_llm_backend as _get_llm_backend
    _LLM_MODULE_AVAILABLE = True
except ImportError:
    _LLM_MODULE_AVAILABLE = False

try:
    from rag_reranker import rerank_results as _rerank_results, RERANKER_CANDIDATES
    _RERANKER_MODULE_AVAILABLE = True
except ImportError:
    _RERANKER_MODULE_AVAILABLE = False
    RERANKER_CANDIDATES = int(os.environ.get("RERANKER_CANDIDATES", "20"))

try:
    from rag_graph import (
        process_chunk_graph as _process_chunk_graph,
        expand_query as _expand_query,
        get_graph as _get_graph,
    )
    _GRAPH_MODULE_AVAILABLE = True
except ImportError:
    _GRAPH_MODULE_AVAILABLE = False

try:
    from rag_modal import (
        extract_content as _extract_content,
        collect_modal_files as _collect_modal_files,
        is_any_modal_enabled as _is_any_modal_enabled,
    )
    _MODAL_MODULE_AVAILABLE = True
except ImportError:
    _MODAL_MODULE_AVAILABLE = False

# ---------------------------------------------------------------------------
# Global state
# ---------------------------------------------------------------------------

# Protected by _state_lock
_state_lock   = threading.Lock()
_status       = "starting"    # "starting" | "indexing" | "ready" | "error"
_indexed_count = 0
_last_run: Optional[str] = None
_error_message: Optional[str] = None

# The sentence-transformers model (loaded once at startup)
_model = None
_model_lock = threading.Lock()

# LLM backend for async graph enrichment (None = NullBackend / disabled)
_llm_backend = None

# ---------------------------------------------------------------------------
# In-memory embedding matrix (numpy fast-path for search)
# ---------------------------------------------------------------------------
# Rebuilt by _rebuild_matrix() after every successful reindex.
# When populated, search() uses a single matrix multiply instead of a Python loop.
# Falls back to Python loop during startup race or if numpy unavailable.

_matrix_lock        = threading.RLock()
_embeddings_matrix: Optional[np.ndarray] = None   # shape (N, 384), float32
_matrix_norms:      Optional[np.ndarray] = None   # shape (N,), precomputed row norms
_chunk_meta:        list[dict]            = []     # parallel list: {content, file, path}

# Query embedding LRU cache — avoids re-embedding identical queries
_embed_cache:       dict[str, list[float]] = {}
_embed_cache_order: list[str]              = []
_embed_cache_lock   = threading.Lock()

# ---------------------------------------------------------------------------
# Model loading
# ---------------------------------------------------------------------------

def load_model() -> bool:
    """
    Load sentence-transformers model into global _model.
    Returns True on success, False on failure.
    NOTE: First run downloads ~90MB from HuggingFace - this is expected.
    """
    global _model, _status, _error_message

    try:
        # Import here so the server starts before the slow import resolves
        from sentence_transformers import SentenceTransformer

        log.info("Loading model: %s (first run downloads ~90MB)", MODEL_NAME)
        model = SentenceTransformer(MODEL_NAME)

        with _model_lock:
            _model = model

        log.info("Model loaded successfully (dim=%d)", EMBEDDING_DIM)
        return True

    except Exception as exc:
        msg = f"Model load failed: {exc}"
        log.error(msg)
        with _state_lock:
            _status = "error"
            _error_message = msg
        return False


def embed(text: str) -> list[float]:
    """Generate a 384-dim embedding for text using the loaded model."""
    with _model_lock:
        if _model is None:
            raise RuntimeError("Model not loaded")
        return _model.encode(text, convert_to_numpy=True).tolist()


def embed_with_cache(text: str) -> list[float]:
    """
    embed() with LRU caching (EMBED_CACHE_MAX entries).
    Repeated identical queries skip the 500ms encode call entirely.
    """
    with _embed_cache_lock:
        if text in _embed_cache:
            _embed_cache_order.remove(text)
            _embed_cache_order.append(text)
            return _embed_cache[text]

    vec = embed(text)

    with _embed_cache_lock:
        _embed_cache[text] = vec
        _embed_cache_order.append(text)
        if len(_embed_cache_order) > EMBED_CACHE_MAX:
            evict = _embed_cache_order.pop(0)
            _embed_cache.pop(evict, None)

    return vec


def embed_batch(texts: list[str]) -> list[list[float]]:
    """
    Batch embed a list of texts — sentence-transformers native batching is
    4-8x faster than sequential embed() calls.
    Returns list of 384-dim float lists in the same order as input.
    """
    with _model_lock:
        if _model is None:
            raise RuntimeError("Model not loaded")
        vecs = _model.encode(
            texts,
            batch_size=EMBED_BATCH_SIZE,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
    return [v.tolist() for v in vecs]


def _rebuild_matrix() -> None:
    """
    Load all chunk embeddings from SQLite into a (N, 384) float32 numpy array.
    Called after every successful reindex. Replaces Python-loop cosine search
    with a single matrix multiply — 10-50x faster for 5,000+ chunks.
    Runs in the indexing thread; protected by _matrix_lock for safe swap.
    """
    global _embeddings_matrix, _matrix_norms, _chunk_meta

    try:
        conn = open_db()
        rows = conn.execute(
            "SELECT content, file_name, file_path, embedding, "
            "COALESCE(recall, 1), doc_id FROM chunks "
            "WHERE embedding IS NOT NULL"
        ).fetchall()
        conn.close()
    except Exception as exc:
        log.warning("_rebuild_matrix: DB read failed: %s", exc)
        return

    if not rows:
        return

    contents, file_names, file_paths, blobs, recalls, doc_ids = zip(*rows)

    # Decode all blobs to numpy in one pass
    dim = EMBEDDING_DIM
    matrix = np.empty((len(rows), dim), dtype=np.float32)
    for i, blob in enumerate(blobs):
        count = len(blob) // 4
        matrix[i] = struct.unpack(f"<{count}f", blob)[:dim]

    # Precompute row norms for cosine similarity (avoids division inside query loop)
    norms = np.linalg.norm(matrix, axis=1)
    norms[norms == 0] = 1e-9  # guard against zero vectors

    meta = [
        {"content": c, "file": f, "path": p, "recall": int(r), "doc_id": d}
        for c, f, p, r, d in zip(contents, file_names, file_paths, recalls, doc_ids)
    ]

    with _matrix_lock:
        _embeddings_matrix = matrix
        _matrix_norms      = norms
        _chunk_meta        = meta

    log.info("Embedding matrix rebuilt: %d chunks (%d MB)", len(rows),
             matrix.nbytes // (1024 * 1024))


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two equal-length vectors (matches UniBOT)."""
    if len(a) != len(b):
        return 0.0
    dot   = sum(x * y for x, y in zip(a, b))
    mag_a = sum(x * x for x in a) ** 0.5
    mag_b = sum(x * x for x in b) ** 0.5
    if mag_a == 0.0 or mag_b == 0.0:
        return 0.0
    return dot / (mag_a * mag_b)


# ---------------------------------------------------------------------------
# SQLite helpers
# ---------------------------------------------------------------------------

DB_SCHEMA = """
CREATE TABLE IF NOT EXISTS chunks (
    id          INTEGER PRIMARY KEY,
    file_path   TEXT    NOT NULL,
    file_name   TEXT    NOT NULL,
    chunk_index INTEGER,
    content     TEXT    NOT NULL,
    token_count INTEGER,
    embedding   BLOB,
    file_mtime  REAL,
    recall      INTEGER DEFAULT 1,
    doc_id      TEXT,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_file_path ON chunks(file_path);
CREATE INDEX IF NOT EXISTS idx_file_name ON chunks(file_name);
-- idx_doc_id is created in _migrate_doc_columns (after the doc_id column exists
-- on pre-existing tables), so it is intentionally NOT in this schema script.

CREATE TABLE IF NOT EXISTS model_registry (
    id          INTEGER PRIMARY KEY,
    model_name  TEXT    NOT NULL,
    dim         INTEGER NOT NULL,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


def open_db() -> sqlite3.Connection:
    """Open the vault index database with WAL mode for concurrent reads."""
    conn = sqlite3.connect(str(DB_PATH), timeout=30.0, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def _migrate_doc_columns(conn: sqlite3.Connection) -> None:
    """
    Doc-RAG firewall (2026-06): add recall/doc_id columns to a pre-existing
    chunks table. Existing rows default to recall=1 (recall-eligible, no
    behavior change) and doc_id=NULL. Idempotent — skips columns already present.
    """
    try:
        cols = {row[1] for row in conn.execute("PRAGMA table_info(chunks)").fetchall()}
        if "recall" not in cols:
            conn.execute("ALTER TABLE chunks ADD COLUMN recall INTEGER DEFAULT 1")
        if "doc_id" not in cols:
            conn.execute("ALTER TABLE chunks ADD COLUMN doc_id TEXT")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_doc_id ON chunks(doc_id)")
        conn.commit()
    except Exception as exc:
        log.warning("doc-column migration skipped: %s", exc)


def init_db() -> None:
    """Create tables and indexes if they don't exist."""
    with open_db() as conn:
        conn.executescript(DB_SCHEMA)
        _migrate_doc_columns(conn)


def embedding_to_blob(embedding: list[float]) -> bytes:
    """Pack list[float] into little-endian IEEE 754 bytes (matches UniBOT)."""
    return struct.pack(f"<{len(embedding)}f", *embedding)


def blob_to_embedding(blob: bytes) -> list[float]:
    """Unpack little-endian bytes back to list[float] (matches UniBOT)."""
    count = len(blob) // 4
    return list(struct.unpack(f"<{count}f", blob))


def get_indexed_mtimes(conn: sqlite3.Connection) -> dict[str, float]:
    """
    Return a dict of {file_path: max(file_mtime)} for all indexed files.
    Used to detect which files need re-indexing.
    """
    rows = conn.execute(
        "SELECT file_path, MAX(file_mtime) FROM chunks GROUP BY file_path"
    ).fetchall()
    return {row[0]: row[1] for row in rows}


# ---------------------------------------------------------------------------
# Markdown preprocessing
# ---------------------------------------------------------------------------

_FRONTMATTER_RE = re.compile(r"^---\s*\n.*?\n---\s*\n", re.DOTALL)
_HTML_TAG_RE    = re.compile(r"<[^>]+>")
_FM_BLOCK_RE    = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_FM_RECALL_RE   = re.compile(r"^\s*recall\s*:\s*(\S+)", re.IGNORECASE | re.MULTILINE)
_FM_DOCID_RE    = re.compile(r"^\s*doc_id\s*:\s*(\S+)", re.IGNORECASE | re.MULTILINE)


def parse_doc_meta(raw: str) -> tuple[int, Optional[str]]:
    """
    Read the doc-RAG firewall fields from a note's YAML frontmatter.
    Returns (recall, doc_id):
      recall=1 (default, recall-eligible) unless frontmatter says `recall: false`.
      doc_id = the bound document id (str) or None for ordinary vault notes.
    Cheap regex parse — avoids a YAML dependency in the hot index path.
    """
    m = _FM_BLOCK_RE.match(raw)
    if not m:
        return 1, None
    block = m.group(1)
    recall = 1
    rm = _FM_RECALL_RE.search(block)
    if rm and rm.group(1).strip().strip('"\'').lower() in ("false", "no", "0"):
        recall = 0
    dm = _FM_DOCID_RE.search(block)
    doc_id = dm.group(1).strip().strip('"\'') if dm else None
    return recall, doc_id


def preprocess_markdown(text: str, filename: str) -> str:
    """
    Strip YAML frontmatter and HTML tags from markdown content.
    Prepend filename as context so retrieval links back to source.
    """
    # Strip frontmatter block (--- ... ---)
    text = _FRONTMATTER_RE.sub("", text, count=1)

    # Strip HTML tags
    text = _HTML_TAG_RE.sub(" ", text)

    # Collapse excessive whitespace
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = text.strip()

    # Prepend filename as document-level context (improves retrieval accuracy)
    stem = Path(filename).stem.replace("-", " ").replace("_", " ")
    return f"Document: {stem}\n\n{text}"


# ---------------------------------------------------------------------------
# Chunking (mirrors UniBOT chunk_text word-based algorithm)
# ---------------------------------------------------------------------------

def chunk_text(text: str) -> list[str]:
    """
    Delegates to rag_chunker (Phase 1 — semantic paragraph chunking) when available.
    Falls back to original word-count algorithm (UniBOT-compatible) on ImportError.
    Strategy controlled by CHUNKING_STRATEGY env var (default: "paragraph").
    """
    if _CHUNKER_AVAILABLE:
        return _chunk_text_v2(text, embed_fn=embed if _model is not None else None)
    # Original word-count fallback
    words_per = 384
    overlap   = 48
    words     = text.split()
    if not words:
        return []
    chunks, start = [], 0
    while start < len(words):
        end = min(start + words_per, len(words))
        chunks.append(" ".join(words[start:end]))
        if end >= len(words):
            break
        start += words_per - overlap
    return chunks


def estimate_tokens(text: str) -> int:
    """Rough token estimate: words / 0.75 (same formula as UniBOT)."""
    return int(len(text.split()) / 0.75)


# ---------------------------------------------------------------------------
# Indexing
# ---------------------------------------------------------------------------

def index_file(conn: sqlite3.Connection, md_path: Path, mtime: float) -> int:
    """
    Index a single markdown file. Deletes any existing chunks for that file
    first to handle edits cleanly.
    Returns number of chunks inserted.
    """
    try:
        raw = md_path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        log.warning("Cannot read %s: %s", md_path, exc)
        return 0

    text   = preprocess_markdown(raw, md_path.name)
    chunks = chunk_text(text)
    if not chunks:
        return 0

    # Doc-RAG firewall: a note tagged `recall: false` (raw document text) is
    # indexed but excluded from default recall; a `doc_id` binds its chunks to a
    # session document so they can be retrieved on demand. Ordinary notes →
    # recall=1, doc_id=NULL (unchanged behavior).
    recall, doc_id = parse_doc_meta(raw)

    file_path_str = str(md_path)
    file_name_str = md_path.name

    # Remove stale chunks for this file before inserting updated ones
    conn.execute("DELETE FROM chunks WHERE file_path = ?", (file_path_str,))

    # Batch embed all chunks at once (4-8x faster than sequential embed())
    try:
        vecs = embed_batch(chunks)
    except Exception as exc:
        log.warning("Batch embed failed for %s, trying sequential: %s", md_path.name, exc)
        vecs = []
        for chunk in chunks:
            try:
                vecs.append(embed(chunk))
            except Exception as exc2:
                log.warning("Embed failed for chunk in %s: %s", md_path.name, exc2)
                vecs.append(None)

    # Dedup guard: compare all new vecs against recent index in one numpy pass
    dedup_matrix: Optional[np.ndarray] = None
    if DEDUP_ENABLED:
        try:
            sample = conn.execute(
                "SELECT embedding FROM chunks WHERE embedding IS NOT NULL ORDER BY ROWID DESC LIMIT 500"
            ).fetchall()
            if sample:
                dedup_matrix = np.array(
                    [struct.unpack(f"<{len(b[0])//4}f", b[0]) for b in sample],
                    dtype=np.float32,
                )
                dedup_norms = np.linalg.norm(dedup_matrix, axis=1)
                dedup_norms[dedup_norms == 0] = 1e-9
        except Exception:
            pass

    inserted = 0
    for idx, (chunk, vec) in enumerate(zip(chunks, vecs)):
        if vec is None:
            continue
        try:
            blob = embedding_to_blob(vec)

            # Vectorized dedup check
            if DEDUP_ENABLED and dedup_matrix is not None:
                v = np.array(vec, dtype=np.float32)
                v_norm = np.linalg.norm(v)
                if v_norm > 0:
                    sims = (dedup_matrix @ v) / (dedup_norms * v_norm)
                    if float(sims.max()) > DEDUP_THRESHOLD:
                        log.debug("Dedup: %s chunk %d skipped", md_path.name, idx)
                        continue

            conn.execute(
                """INSERT INTO chunks
                   (file_path, file_name, chunk_index, content, token_count, embedding, file_mtime, recall, doc_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (file_path_str, file_name_str, idx, chunk, estimate_tokens(chunk), blob, mtime, recall, doc_id),
            )
            inserted += 1
        except Exception as exc:
            log.warning("Insert failed for %s chunk %d: %s", md_path.name, idx, exc)

    # Knowledge graph entity extraction (Phase 2 — non-critical, GRAPH_ENABLED gates internally)
    if _GRAPH_MODULE_AVAILABLE:
        try:
            _process_chunk_graph(text, file_path_str, str(DB_PATH), _llm_backend)
        except Exception as exc:
            log.debug("Graph processing skipped for %s: %s", md_path.name, exc)

    return inserted


def _check_model_registry() -> None:
    """
    Log a warning if the embedding model changed since the last run.
    Records each startup model in model_registry for mismatch detection.
    No-op on any DB error (called before indexing thread starts).
    """
    try:
        conn = open_db()
        prev = conn.execute(
            "SELECT model_name FROM model_registry ORDER BY id DESC LIMIT 1"
        ).fetchone()
        if prev and prev[0] != MODEL_NAME:
            log.warning(
                "Embedding model changed: %s → %s. "
                "Run POST /reindex with {\"full\": true} to rebuild the index.",
                prev[0], MODEL_NAME,
            )
        conn.execute(
            "INSERT INTO model_registry (model_name, dim) VALUES (?, ?)",
            (MODEL_NAME, EMBEDDING_DIM),
        )
        conn.commit()
        conn.close()
    except Exception as exc:
        log.debug("Model registry check skipped: %s", exc)


def index_modal_file(conn: sqlite3.Connection, file_path: Path, mtime: float) -> int:
    """
    Index a non-markdown file (PDF, image, CSV/XLSX) via rag_modal extractors.
    Reuses same chunks table as markdown files — fully searchable via /query.
    Returns number of chunks inserted.
    """
    if not _MODAL_MODULE_AVAILABLE:
        return 0
    try:
        segments = _extract_content(str(file_path), _llm_backend)
    except Exception as exc:
        log.warning("Modal extraction failed for %s: %s", file_path.name, exc)
        return 0

    if not segments:
        return 0

    file_path_str = str(file_path)
    file_name_str = file_path.name
    conn.execute("DELETE FROM chunks WHERE file_path = ?", (file_path_str,))

    inserted = 0
    for idx, seg in enumerate(segments):
        text = seg.get("text", "").strip()
        if not text:
            continue
        chunk = f"Document: {file_path.stem}\nType: {seg.get('type', 'text')}\n\n{text}"
        try:
            vec  = embed(chunk)
            blob = embedding_to_blob(vec)
            conn.execute(
                """INSERT INTO chunks
                   (file_path, file_name, chunk_index, content, token_count, embedding, file_mtime)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (file_path_str, file_name_str, idx, chunk, estimate_tokens(chunk), blob, mtime),
            )
            inserted += 1
        except Exception as exc:
            log.warning("Embedding failed for %s segment %d: %s", file_path.name, idx, exc)

    return inserted


_EXCLUDED_DIRS = {
    "node_modules", ".git", "__pycache__", ".pytest_cache",
    "dist", "build", ".next", ".venv", "venv", "env",
    "worktrees",  # Claude git worktree artifacts
    "quarantine",  # session transcript dumps — not vault knowledge
}

def collect_vault_files(root: Path = VAULT_PATH) -> list[Path]:
    """Walk `root` and return all .md files, skipping hidden and junk directories.
    Defaults to VAULT_PATH; also called with SYSTEM101_PATH for the Track B index root."""
    md_files = []
    for root_dir, dirs, files in os.walk(root):
        # Skip hidden dirs and explicitly excluded dirs (node_modules, worktrees, etc.)
        dirs[:] = [
            d for d in dirs
            if not d.startswith(".") and d not in _EXCLUDED_DIRS
        ]
        for fname in files:
            if fname.lower().endswith(".md"):
                md_files.append(Path(root_dir) / fname)
    return md_files


def run_index(full: bool = False) -> None:
    """
    Background indexing worker.
    full=True  → delete all existing chunks, re-index everything
    full=False → only re-index files whose mtime has changed (incremental)
    """
    global _status, _indexed_count, _last_run, _error_message

    with _state_lock:
        _status = "indexing"

    try:
        conn = open_db()
        conn.execute("PRAGMA busy_timeout = 30000")  # 30s retry window for write lock

        if full:
            log.info("Full re-index requested — clearing existing chunks")
            conn.execute("DELETE FROM chunks")
            conn.commit()
            known_mtimes: dict[str, float] = {}
        else:
            known_mtimes = get_indexed_mtimes(conn)
            log.info("Incremental index — %d files already tracked", len(known_mtimes))

        md_files     = collect_vault_files(VAULT_PATH) + collect_vault_files(SYSTEM101_PATH)
        total_files  = len(md_files)
        new_or_changed = [
            p for p in md_files
            if str(p) not in known_mtimes
            or p.stat().st_mtime > known_mtimes[str(p)]
        ]

        log.info(
            "Vault scan: %d total .md files, %d need indexing",
            total_files, len(new_or_changed),
        )

        total_chunks = 0
        for i, md_path in enumerate(new_or_changed, 1):
            mtime = md_path.stat().st_mtime
            n     = index_file(conn, md_path, mtime)
            total_chunks += n
            if i % 50 == 0:
                conn.commit()
                log.info("  Progress: %d / %d files indexed", i, len(new_or_changed))

        conn.commit()

        # Modal file indexing (Phase 7 — PDF/image/table, gated by feature flags)
        if _MODAL_MODULE_AVAILABLE and _is_any_modal_enabled():
            modal_files = _collect_modal_files(str(VAULT_PATH))
            modal_new = [
                p for p in modal_files
                if str(p) not in known_mtimes
                or p.stat().st_mtime > known_mtimes.get(str(p), 0)
            ]
            log.info(
                "Modal files: %d total, %d need indexing",
                len(modal_files), len(modal_new),
            )
            for mp in modal_new:
                try:
                    n = index_modal_file(conn, mp, mp.stat().st_mtime)
                    total_chunks += n
                except Exception as exc:
                    log.warning("Modal index failed for %s: %s", mp.name, exc)
            if modal_new:
                conn.commit()

        # Count unique indexed files for status
        row = conn.execute(
            "SELECT COUNT(DISTINCT file_path) FROM chunks"
        ).fetchone()
        indexed = row[0] if row else 0
        conn.close()

        ts = datetime.now(timezone.utc).isoformat()

        with _state_lock:
            _indexed_count = indexed
            _last_run      = ts
            _status        = "ready"
            _error_message = None

        log.info(
            "Indexing complete: %d unique files, %d chunks, %d newly processed",
            indexed, total_chunks, len(new_or_changed),
        )

        # Rebuild in-memory numpy matrix for fast-path search
        _rebuild_matrix()

    except Exception as exc:
        msg = f"Indexing error: {exc}"
        log.exception(msg)
        with _state_lock:
            _status        = "error"
            _error_message = msg


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

def _meta_passes_filter(m: dict, doc_filter: Optional[str]) -> bool:
    """
    Doc-RAG firewall gate applied per chunk.
      doc_filter set   → return only chunks bound to that doc_id (full-fidelity
                         retrieval for a session-attached document; recall flag
                         ignored so raw source.md chunks are reachable).
      doc_filter None  → default global recall: only recall-eligible chunks
                         (summaries + ordinary notes); raw document text excluded.
    """
    if doc_filter:
        return m.get("doc_id") == doc_filter
    return int(m.get("recall", 1)) == 1


def search(query: str, top_k: int = TOP_K_DEFAULT,
           filter: Optional[dict] = None) -> list[dict]:
    """
    Semantic search over indexed chunks.
    Fast path: numpy matrix multiply (10-50x) when _embeddings_matrix is ready.
    Fallback: pure-Python loop (original) during startup race.
    Applies UniBOT hybrid scoring: cosine similarity + keyword boosts.
    `filter` (doc-RAG firewall): {"doc_id": "..."} retrieves one document's
    chunks; absent/None retrieves only recall-eligible chunks (see
    _meta_passes_filter). Backward-compatible — no filter = prior behavior
    once existing rows are migrated to recall=1.
    Returns list of {content, file, score} dicts sorted by score descending.
    """
    doc_filter  = (filter or {}).get("doc_id")
    query_vec   = embed_with_cache(query)
    query_lower = query.lower()

    # --- Fast path: numpy matrix multiply ---
    with _matrix_lock:
        matrix = _embeddings_matrix
        norms  = _matrix_norms
        meta   = _chunk_meta

    if matrix is not None and len(meta) > 0:
        q = np.array(query_vec, dtype=np.float32)
        q_norm = np.linalg.norm(q)
        if q_norm > 0:
            q /= q_norm

        # Cosine similarity: (N,384) @ (384,) / (N,) → (N,)
        scores = (matrix @ q) / norms

        # Optional hard threshold (disabled by default)
        if THRESHOLD_ENABLED:
            mask = scores >= SIMILARITY_THRESHOLD
        else:
            mask = np.ones(len(scores), dtype=bool)

        # Doc-RAG firewall: knock out chunks this query isn't allowed to see
        # BEFORE candidate selection, so a small doc_id set isn't crowded out
        # of the top-score partition by recall-eligible noise.
        fw = np.fromiter(
            (_meta_passes_filter(m, doc_filter) for m in meta),
            dtype=bool, count=len(meta),
        )
        scores = np.where(mask & fw, scores, -np.inf)

        # Keyword boosts (vectorized where possible)
        candidate_k = min(top_k * 4, len(meta))  # evaluate more before boosting
        top_idx = np.argpartition(scores, -candidate_k)[-candidate_k:]

        results = []
        for i in top_idx:
            if not np.isfinite(scores[i]):
                continue
            s = float(scores[i])
            c = meta[i]["content"]
            f = meta[i]["file"]
            if query_lower in c.lower():
                s += CONTENT_BOOST
            if query_lower in f.lower():
                s += FILENAME_BOOST
            results.append({
                "content": c,
                "file":    f,
                "path":    meta[i]["path"],
                "score":   round(s, 4),
            })

        results.sort(key=lambda r: r["score"], reverse=True)
        return results[:top_k]

    # --- Fallback: original Python loop (used during startup before matrix is built) ---
    log.debug("search(): matrix not ready, falling back to Python loop")
    try:
        conn = open_db()
    except sqlite3.OperationalError as exc:
        log.error("DB locked or unavailable: %s", exc)
        raise

    rows = conn.execute(
        "SELECT content, file_name, file_path, embedding, COALESCE(recall, 1), doc_id FROM chunks"
    ).fetchall()
    conn.close()

    results = []
    for content, file_name, file_path, blob, recall, doc_id in rows:
        if blob is None:
            continue

        # Doc-RAG firewall (same gate as the fast path)
        if not _meta_passes_filter({"recall": recall, "doc_id": doc_id}, doc_filter):
            continue

        chunk_vec  = blob_to_embedding(blob)
        similarity = cosine_similarity(query_vec, chunk_vec)

        if THRESHOLD_ENABLED and similarity < SIMILARITY_THRESHOLD:
            continue

        score = similarity
        if query_lower in content.lower():
            score += CONTENT_BOOST
        if query_lower in file_name.lower():
            score += FILENAME_BOOST

        results.append({
            "content": content,
            "file":    file_name,
            "path":    file_path,
            "score":   round(score, 4),
        })

    results.sort(key=lambda r: r["score"], reverse=True)
    return results[:top_k]


# ---------------------------------------------------------------------------
# File watcher (optional, auto-reindex on vault changes)
# ---------------------------------------------------------------------------

def _start_file_watcher() -> None:
    """
    Start a watchdog observer to auto-reindex .md files when they change.
    Imported lazily so the server still starts if watchdog is not installed.
    """
    try:
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler, FileModifiedEvent, FileCreatedEvent

        class VaultHandler(FileSystemEventHandler):
            # Debounce window: coalesce bursts of changes into ONE matrix rebuild.
            _DEBOUNCE_SECONDS = 8.0

            def __init__(self):
                self._pending      = set()
                self._lock         = threading.Lock()
                self._rebuild_timer = None

            @staticmethod
            def _is_excluded(md_path: Path) -> bool:
                """Mirror collect_vault_files(): skip hidden dirs and _EXCLUDED_DIRS
                (node_modules, worktrees, .git, ...) anywhere in the path. Without
                this the watcher storms on vendored repos and holds the DB lock,
                starving full /reindex (the 'database is locked' failure)."""
                for part in md_path.parts:
                    if part.startswith(".") or part in _EXCLUDED_DIRS:
                        return True
                return False

            def _schedule_rebuild(self) -> None:
                """Coalesce rapid changes: (re)arm a single timer that rebuilds the
                embedding matrix once the vault has been quiet for _DEBOUNCE_SECONDS."""
                with self._lock:
                    if self._rebuild_timer is not None:
                        self._rebuild_timer.cancel()
                    self._rebuild_timer = threading.Timer(
                        self._DEBOUNCE_SECONDS, _rebuild_matrix
                    )
                    self._rebuild_timer.daemon = True
                    self._rebuild_timer.start()

            def _handle(self, path: str) -> None:
                if not path.lower().endswith(".md"):
                    return
                md_path = Path(path)
                # Skip vendored/junk paths — keeps the index to real memories and
                # frees the SQLite lock for full reindex.
                if self._is_excluded(md_path):
                    return
                if not md_path.is_file():
                    return

                log.info("Vault change detected: %s", md_path.name)
                try:
                    conn  = open_db()
                    mtime = md_path.stat().st_mtime
                    index_file(conn, md_path, mtime)
                    conn.commit()

                    row = conn.execute(
                        "SELECT COUNT(DISTINCT file_path) FROM chunks"
                    ).fetchone()
                    conn.close()

                    with _state_lock:
                        global _indexed_count
                        _indexed_count = row[0] if row else _indexed_count

                    # Debounced: one rebuild after the burst settles, not per file.
                    self._schedule_rebuild()

                except Exception as exc:
                    log.warning("Auto-reindex failed for %s: %s", path, exc)

            def on_modified(self, event):
                if not event.is_directory:
                    self._handle(event.src_path)

            def on_created(self, event):
                if not event.is_directory:
                    self._handle(event.src_path)

        handler  = VaultHandler()
        observer = Observer()
        observer.schedule(handler, str(VAULT_PATH), recursive=True)
        observer.schedule(handler, str(SYSTEM101_PATH), recursive=True)
        observer.daemon = True
        observer.start()
        log.info("File watcher active on: %s, %s", VAULT_PATH, SYSTEM101_PATH)

    except ImportError:
        log.info("watchdog not installed — file watching disabled (pip install watchdog to enable)")
    except Exception as exc:
        log.warning("File watcher could not start: %s", exc)


# ---------------------------------------------------------------------------
# Query helpers
# ---------------------------------------------------------------------------

def _rewrite_query(original_q: str) -> str:
    """
    Optionally rewrite query via LLM for improved recall (Phase 9).
    Returns original_q unchanged if QUERY_REWRITE=false or LLM unavailable.
    Never raises.
    """
    if not QUERY_REWRITE or not _LLM_MODULE_AVAILABLE or _llm_backend is None:
        return original_q
    try:
        if not _llm_backend.is_available():
            return original_q
        prompt = (
            "Rewrite this search query to improve recall in a technical knowledge base. "
            "Return ONLY the rewritten query, no explanation:\n\n" + original_q
        )
        rewritten = _llm_backend.complete(prompt, max_tokens=100).strip()
        if rewritten and rewritten != original_q:
            log.debug("Query rewritten: %r → %r", original_q, rewritten)
            return rewritten
    except Exception as exc:
        log.debug("Query rewrite failed: %s", exc)
    return original_q


# ---------------------------------------------------------------------------
# Flask API
# ---------------------------------------------------------------------------

app = Flask(__name__)


@app.route("/health", methods=["GET"])
def health():
    """Simple liveness probe."""
    return jsonify({"ok": True})


@app.route("/status", methods=["GET"])
def status():
    """
    Returns current indexer state.
    status values: "starting" | "indexing" | "ready" | "error"
    indexed_files = number of unique source files in the DB
    indexed_chunks = total embedded chunks (multi-chunk files produce many rows)
    """
    with _state_lock:
        files_count = _indexed_count
        status_val  = _status
        last_run    = _last_run
        err         = _error_message

    # Live chunk count from DB (fast — COUNT(*) on indexed table)
    chunk_count = 0
    try:
        conn = open_db()
        row  = conn.execute("SELECT COUNT(*) FROM chunks WHERE embedding IS NOT NULL").fetchone()
        conn.close()
        chunk_count = row[0] if row else 0
    except Exception:
        pass

    payload = {
        "indexed_files":  files_count,
        "indexed_chunks": chunk_count,
        "indexed":        files_count,   # kept for backward compat
        "last_run": last_run,
        "model":    MODEL_NAME,
        "status":   status_val,
    }
    if err:
        payload["error"] = err
    return jsonify(payload)


@app.route("/query", methods=["POST"])
def query():
    """
    Semantic search endpoint.
    Body:    {"q": "query text", "k": 5}
    Returns: {"results": [{"content": "...", "file": "name.md", "score": 0.82}, ...]}
    """
    with _state_lock:
        current_status = _status

    if current_status == "error":
        return jsonify({"error": _error_message or "Sidecar in error state"}), 503

    if current_status in ("starting", "indexing"):
        # Still indexing — return partial results if any chunks exist,
        # otherwise return a 202 so callers know to retry
        pass  # fall through and attempt search anyway

    body = request.get_json(silent=True) or {}
    q    = body.get("q", "").strip()
    k    = int(body.get("k", TOP_K_DEFAULT))
    # Doc-RAG firewall: {"filter": {"doc_id": "..."}} retrieves one document's
    # chunks; absent → recall-eligible chunks only (raw doc text excluded).
    filt = body.get("filter") if isinstance(body.get("filter"), dict) else None

    if not q:
        return jsonify({"error": "Missing required field: q"}), 400

    if k < 1 or k > 50:
        return jsonify({"error": "k must be between 1 and 50"}), 400

    with _model_lock:
        model_ready = _model is not None

    if not model_ready:
        return jsonify({"error": "Model not yet loaded — try again in a few seconds"}), 503

    try:
        # Phase 0: query rewriting (no-op if QUERY_REWRITE=false or LLM unavailable)
        effective_q = _rewrite_query(q)

        # Phase 1: retrieve candidates (RERANKER_CANDIDATES headroom for re-ranking)
        candidate_k = RERANKER_CANDIDATES if _RERANKER_MODULE_AVAILABLE else k
        candidates  = search(effective_q, top_k=candidate_k, filter=filt)

        # Phase 2: multi-hop graph query expansion (no-op if MULTIHOP_ENABLED=false)
        if _GRAPH_MODULE_AVAILABLE and candidates:
            expanded_q = _expand_query(effective_q, candidates, str(DB_PATH))
            if expanded_q != effective_q:
                extra = search(expanded_q, top_k=candidate_k, filter=filt)
                seen  = {r["path"] for r in candidates}
                candidates += [r for r in extra if r["path"] not in seen]

        # Phase 3: cross-encoder re-rank (no-op if RERANKER_ENABLED=false)
        if _RERANKER_MODULE_AVAILABLE:
            results = _rerank_results(effective_q, candidates, top_k=k)
        else:
            results = candidates[:k]

        return jsonify({"results": results})
    except sqlite3.OperationalError as exc:
        log.error("DB error during query: %s", exc)
        return jsonify({"error": "Database temporarily unavailable"}), 503
    except Exception as exc:
        log.exception("Query failed")
        return jsonify({"error": str(exc)}), 500


@app.route("/query_synthesized", methods=["POST"])
def query_synthesized():
    """
    Semantic search with optional LLM answer synthesis (Phase 10).
    Body:    {"q": "query text", "k": 5, "synthesize": true}
    Returns: {"results": [...], "synthesis": "direct answer"}
             synthesis key present only when synthesize=true AND LLM_BACKEND configured.

    Runs the full /query pipeline (Phase 0-3), then optionally asks the LLM
    to answer the question directly from the retrieved context.
    """
    with _state_lock:
        current_status = _status
    if current_status == "error":
        return jsonify({"error": _error_message or "Sidecar in error state"}), 503

    body      = request.get_json(silent=True) or {}
    q         = body.get("q", "").strip()
    k         = int(body.get("k", TOP_K_DEFAULT))
    synthesize = bool(body.get("synthesize", False))

    if not q:
        return jsonify({"error": "Missing required field: q"}), 400
    if k < 1 or k > 50:
        return jsonify({"error": "k must be between 1 and 50"}), 400

    with _model_lock:
        if _model is None:
            return jsonify({"error": "Model not yet loaded — try again in a few seconds"}), 503

    try:
        # Full retrieval pipeline (mirrors /query)
        effective_q = _rewrite_query(q)
        candidate_k = RERANKER_CANDIDATES if _RERANKER_MODULE_AVAILABLE else k
        candidates  = search(effective_q, top_k=candidate_k)

        if _GRAPH_MODULE_AVAILABLE and candidates:
            expanded_q = _expand_query(effective_q, candidates, str(DB_PATH))
            if expanded_q != effective_q:
                extra = search(expanded_q, top_k=candidate_k)
                seen  = {r["path"] for r in candidates}
                candidates += [r for r in extra if r["path"] not in seen]

        if _RERANKER_MODULE_AVAILABLE:
            results = _rerank_results(effective_q, candidates, top_k=k)
        else:
            results = candidates[:k]

        payload: dict = {"results": results}

        # Answer synthesis (Phase 10 — no-op if synthesize=false or LLM unavailable)
        if synthesize and _LLM_MODULE_AVAILABLE and _llm_backend is not None:
            try:
                if _llm_backend.is_available() and results:
                    context = "\n\n---\n\n".join(
                        f"[{r['file']}]\n{r['content']}" for r in results
                    )
                    prompt = (
                        f"Based ONLY on the following excerpts from a technical knowledge base, "
                        f"answer this question: {q}\n\n"
                        f"Excerpts:\n{context}\n\n"
                        f"Answer concisely in 1-3 sentences."
                    )
                    synthesis = _llm_backend.complete(prompt, max_tokens=300).strip()
                    if synthesis:
                        payload["synthesis"] = synthesis
            except Exception as exc:
                log.debug("Synthesis failed: %s", exc)
                payload["synthesis_error"] = "LLM synthesis unavailable"

        return jsonify(payload)

    except sqlite3.OperationalError as exc:
        log.error("DB error during /query_synthesized: %s", exc)
        return jsonify({"error": "Database temporarily unavailable"}), 503
    except Exception as exc:
        log.exception("/query_synthesized failed")
        return jsonify({"error": str(exc)}), 500


@app.route("/reindex", methods=["POST"])
def reindex():
    """
    Trigger a full re-index of the vault in the background.
    Returns immediately with {"status": "started"}.
    """
    body = request.get_json(silent=True) or {}
    full = body.get("full", True)

    t = threading.Thread(target=run_index, args=(full,), daemon=True, name="reindex")
    t.start()
    return jsonify({"status": "started", "full": full})


@app.route("/duplicates", methods=["POST"])
def duplicates():
    """
    Find near-duplicate vault chunks (cosine similarity > threshold).
    Body:    {"threshold": 0.92, "max_pairs": 100}
    Returns: {"pairs": [{"file_a": "...", "file_b": "...", "score": 0.95}, ...]}

    Used by daily-scheduler.py weekly deduplication check.
    Enhancement 7a: Near-duplicate vault detector.
    """
    with _model_lock:
        model_ready = _model is not None
    if not model_ready:
        return jsonify({"error": "Model not yet loaded"}), 503

    if _status in ("starting", "indexing"):
        return jsonify({"error": "Indexing in progress — retry when status is ready"}), 503

    body = request.get_json(silent=True) or {}
    threshold = float(body.get("threshold", 0.92))
    max_pairs = int(body.get("max_pairs", 100))

    try:
        conn = open_db()
        rows = conn.execute(
            "SELECT DISTINCT file_name, file_path, embedding FROM chunks WHERE embedding IS NOT NULL"
        ).fetchall()
        conn.close()
    except Exception as exc:
        log.error("DB error during /duplicates: %s", exc)
        return jsonify({"error": "Database unavailable"}), 503

    # Build per-file average embedding (one vector per file)
    from collections import defaultdict
    import struct

    file_vecs: dict[str, tuple[str, list]] = {}  # file_name → (file_path, avg_vec)
    file_blobs: dict[str, list] = defaultdict(list)

    for file_name, file_path, blob in rows:
        if blob is None:
            continue
        vec = blob_to_embedding(blob)
        file_blobs[file_name].append(vec)

    for fname, vecs in file_blobs.items():
        import numpy as np
        avg = np.mean(vecs, axis=0)
        norm = float(np.linalg.norm(avg))
        if norm > 0:
            avg = avg / norm
        # Find file_path from rows
        fp = next((r[1] for r in rows if r[0] == fname), fname)
        file_vecs[fname] = (fp, avg)

    # Compare all pairs — O(n²) but vault is small (<2000 files)
    pairs = []
    file_names = list(file_vecs.keys())
    import numpy as np

    for i in range(len(file_names)):
        for j in range(i + 1, len(file_names)):
            a, b = file_names[i], file_names[j]
            if a == b:
                continue
            _, vec_a = file_vecs[a]
            _, vec_b = file_vecs[b]
            sim = float(np.dot(vec_a, vec_b))
            if sim >= threshold:
                pairs.append({
                    "file_a": a,
                    "file_b": b,
                    "score": round(sim, 4),
                })
        if len(pairs) >= max_pairs:
            break

    pairs.sort(key=lambda p: p["score"], reverse=True)
    return jsonify({"pairs": pairs[:max_pairs], "total_files_compared": len(file_names)})


# ---------------------------------------------------------------------------
# Knowledge Graph endpoints (Phase 2 — require rag_graph module)
# ---------------------------------------------------------------------------

@app.route("/graph/status", methods=["GET"])
def graph_status():
    """Returns knowledge graph statistics: node count, edge count, enabled state."""
    if not _GRAPH_MODULE_AVAILABLE:
        return jsonify({"error": "rag_graph module not available", "enabled": False}), 503
    try:
        return jsonify(_get_graph(str(DB_PATH)).status())
    except Exception as exc:
        log.error("Graph status error: %s", exc)
        return jsonify({"error": str(exc)}), 500


@app.route("/graph/neighbors", methods=["POST"])
def graph_neighbors():
    """
    Return N-hop graph neighbors for an entity.
    Body: {"entity": "OutreachBot", "hops": 1}
    Returns: {"entity": ..., "hops": ..., "neighbors": [...]}
    """
    if not _GRAPH_MODULE_AVAILABLE:
        return jsonify({"error": "rag_graph module not available"}), 503
    body   = request.get_json(silent=True) or {}
    entity = body.get("entity", "").strip()
    hops   = int(body.get("hops", 1))
    if not entity:
        return jsonify({"error": "Missing required field: entity"}), 400
    try:
        neighbors = _get_graph(str(DB_PATH)).get_neighbors(entity, hops=hops)
        return jsonify({"entity": entity, "hops": hops, "neighbors": neighbors})
    except Exception as exc:
        log.error("Graph neighbors error: %s", exc)
        return jsonify({"error": str(exc)}), 500


@app.route("/graph/path", methods=["POST"])
def graph_path():
    """
    Return shortest relationship path between two entities.
    Body: {"from": "OutreachBot", "to": "CRM"}
    Returns: {"from": ..., "to": ..., "path": [...entity names...]}
    """
    if not _GRAPH_MODULE_AVAILABLE:
        return jsonify({"error": "rag_graph module not available"}), 503
    body = request.get_json(silent=True) or {}
    src  = body.get("from", "").strip()
    dst  = body.get("to", "").strip()
    if not src or not dst:
        return jsonify({"error": "Missing required fields: from, to"}), 400
    try:
        path = _get_graph(str(DB_PATH)).get_path(src, dst)
        return jsonify({"from": src, "to": dst, "path": path})
    except Exception as exc:
        log.error("Graph path error: %s", exc)
        return jsonify({"error": str(exc)}), 500


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------

def startup() -> None:
    """
    Bootstrap sequence:
    1. Load model (blocks until ready or fails)
    2. Start incremental or full index in background thread
    3. Start file watcher
    HTTP server starts in parallel — returns 'indexing' status until complete.
    """
    log.info("=" * 60)
    log.info("vault-rag-sidecar starting on %s:%d", HOST, PORT)
    log.info("Vault:  %s", VAULT_PATH)
    log.info("DB:     %s", DB_PATH)
    log.info("=" * 60)

    # Step 1: Load model (synchronous — must complete before queries work)
    if not load_model():
        log.error("Model failed to load — server will start but /query returns 503")
        return

    # Step 2: Initialize DB schema (once at startup — avoids exclusive lock during reindex)
    # Must run before _check_model_registry and run_index so they never need to call init_db().
    init_db()

    # Step 1b: Model registry check (Phase 6) — warn if model changed since last run
    _check_model_registry()

    # Step 2b: Choose indexing mode based on DB existence
    db_exists = DB_PATH.exists()
    full_index = not db_exists

    if full_index:
        log.info("No existing index found — running full vault index")
    else:
        log.info("Existing index found — running incremental update")

    index_thread = threading.Thread(
        target=run_index,
        args=(full_index,),
        daemon=True,
        name="initial-index",
    )
    index_thread.start()

    # Step 3: File watcher (optional)
    _start_file_watcher()

    # Step 4: Initialize LLM backend (used by rag_graph async enrichment thread)
    global _llm_backend
    if _LLM_MODULE_AVAILABLE:
        _llm_backend = _get_llm_backend()
        log.info(
            "LLM backend: %s (available=%s)",
            type(_llm_backend).__name__,
            _llm_backend.is_available(),
        )
    else:
        log.info("rag_llm not found — LLM graph enrichment disabled")

    # Log which enhancement modules loaded
    log.info(
        "Enhancements: chunker=%s reranker=%s graph=%s llm=%s modal=%s dedup=%s",
        _CHUNKER_AVAILABLE,
        _RERANKER_MODULE_AVAILABLE,
        _GRAPH_MODULE_AVAILABLE,
        _LLM_MODULE_AVAILABLE,
        _MODAL_MODULE_AVAILABLE,
        DEDUP_ENABLED,
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    acquire_pid_lock()   # exits immediately if another instance is alive
    startup()

    # Flask development server with threading enabled for concurrent requests.
    # For production use: gunicorn vault-rag-sidecar:app --bind 127.0.0.1:7742 --workers 2
    app.run(host=HOST, port=PORT, threaded=True, debug=False)
