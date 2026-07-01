#!/usr/bin/env python3
"""
Prediction Engine Hook v3.3 - Predictive Client Context (Unicode + Timeout Fix)
Runs BEFORE gate-enforcer.py to pre-load context based on prompt patterns.

CRITICAL REQUIREMENT: MUST complete in <100ms to avoid UX slowdown.

Performance Targets (v3.3):
- Domain prediction: <20ms
- Entity extraction: <15ms
- Client matching: <10ms
- Total hook overhead: <70ms (soft target)
- Hard timeout: 200ms (increased from 150ms for Windows disk I/O)

v3.3 FIXES:
- Fixed stdout encoding (UnicodeEncodeError on sys.stdout - belt+suspenders with stdin fix)
- Replaced emoji print() output with ASCII [WARN] prefix (belt+suspenders)
- Moved entity module imports to module level (load once, not per-call - reduces hook latency)

v3.1 FIXES:
- UTF-8 encoding on all file operations (UnicodeEncodeError fix)
- Increased timeout threshold from 150ms to 200ms (reduces false timeout errors)
- Added ensure_ascii=False to JSON dumps for proper Unicode handling

Architecture (v3.0):
1. Read prediction-state.json (hot state - fast)
2. Analyze prompt for domain prediction
3. Extract client entities (names, companies, deal IDs) [NEW]
4. Match entities to client notes [NEW]
5. Check multi-slot cache (instant if hit)
6. Load shard if cache miss (NOT full 889KB index)
7. Update prediction state with entities and client_notes [NEW]
8. Output prediction result

Integration:
- Called by Claude Code hook chain BEFORE gate-enforcer.py
- Non-blocking: Falls back to reactive loading on failure
- Async-friendly: Does not block user interaction
- Client notes injected into memory recall Tier 1 [NEW]
"""

import json
import sys
import io
import time
import re
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# Fix Unicode encoding on Windows (UnicodeEncodeError fix v3.2)
if sys.stdin.encoding != 'utf-8':
    sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8', errors='replace')
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Find .claude directory (relative to hook location)
CLAUDE_DIR = Path(__file__).parent.parent
SESSION_DIR = CLAUDE_DIR / "session"
SHARDS_DIR = SESSION_DIR / "shards"

# State files
PREDICTION_STATE = SESSION_DIR / "prediction-state.json"
SEED_PREDICTIONS = SESSION_DIR / "seed_predictions.json"
PROMPT_HISTORY = SESSION_DIR / "prompt-history.jsonl"
ERROR_LOG = SESSION_DIR / "error-log.jsonl"

# Performance tracking (v3.1 - timeout fix)
LATENCY_TARGET_MS = 70  # Target for warnings (not hard limit)
LATENCY_TIMEOUT_MS = 500  # Hard timeout threshold (raised from 300ms - Windows disk I/O is legitimately slow; 2026-06-03)
CACHE_HIT_TARGET = 0.80
ACCURACY_TARGET = 0.70
ENTITY_CONFIDENCE_THRESHOLD = 0.3  # Minimum confidence to include client notes (lowered to catch whitelist matches)

# Add scripts dir to path for entity extraction
SCRIPTS_DIR = CLAUDE_DIR / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

# Pre-import entity extraction modules (v3.3 - load once, not per-call)
try:
    from entity_extractor import extract_client_entities as _extract_client_entities
    from client_matcher import match_entities_to_notes as _match_entities_to_notes
    _ENTITY_MODULES_LOADED = True
except ImportError:
    _ENTITY_MODULES_LOADED = False

def log_error(error_type, context, exception=None):
    """Log errors to structured error log (non-blocking)"""
    error_entry = {
        "timestamp": datetime.now().isoformat(),
        "error_type": error_type,
        "context": context,
        "error_message": str(exception) if exception else None,
        "component": "prediction-engine"
    }
    try:
        ERROR_LOG.parent.mkdir(parents=True, exist_ok=True)
        # v3.1 FIX: Use UTF-8 encoding to prevent UnicodeEncodeError on Windows
        with open(ERROR_LOG, 'a', encoding='utf-8') as f:
            f.write(json.dumps(error_entry, ensure_ascii=False) + "\n")
    except Exception:
        pass  # Silent fail - hook must not crash


def retry_with_backoff(func, max_attempts=3, initial_delay_ms=10):
    """Retry wrapper for transient failures (v3.2 - state corruption fix).

    Args:
        func: Callable to retry
        max_attempts: Maximum retry attempts (default 3)
        initial_delay_ms: Initial delay in milliseconds (doubles each retry)

    Returns:
        Result of func() or None if all attempts fail
    """
    for attempt in range(max_attempts):
        try:
            return func()
        except (json.JSONDecodeError, IOError) as e:
            if attempt == max_attempts - 1:
                log_error("retry_exhausted", f"Failed after {max_attempts} attempts", e)
                return None
            else:
                delay_ms = initial_delay_ms * (2 ** attempt)
                time.sleep(delay_ms / 1000)
    return None

def load_prediction_state():
    """Load prediction state (or initialize if missing) with retry logic (v3.2)"""
    def _load():
        if PREDICTION_STATE.exists():
            # v3.1 FIX: Use UTF-8 encoding for cross-platform compatibility
            with open(PREDICTION_STATE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None

    # v3.2: Use retry wrapper for transient failures
    state = retry_with_backoff(_load)
    if state is not None:
        return state

    # Log if retry failed but file exists (indicates corruption)
    if PREDICTION_STATE.exists():
        log_error("state_load_error", "Failed to load prediction state after retries")

    # Initialize default state (v3.0 - added entities and client_notes)
    return {
        "version": "3.0",
        "current_prediction": {
            "domain": None,
            "project": None,
            "confidence": 0.0,
            "predicted_at": None,
            "source": None,
            "prediction_latency_ms": None,
            # v3.0: Entity extraction results
            "entities": {
                "names": [],
                "companies": [],
                "deal_ids": [],
                "crm_ids": [],
                "whitelist_matches": [],
                "confidence": 0.0,
                "extraction_time_ms": 0
            },
            # v3.0: Matched client notes to inject into memory recall
            "client_notes": [],
            "client_match_scores": {},
            "entity_match_time_ms": 0
        },
        "confirmation_window": {
            "enabled": True,
            "threshold": 3,
            "current_streak": 0,
            "pending_switch": None,
            "pending_domain": None,
            "pending_project": None,
            "pending_confidence": 0.0
        },
        "multi_slot_cache": {
            "enabled": True,
            "slot_count": 3,
            "slots": [
                {"domain": None, "project": None, "loaded_at": None, "hit_count": 0, "last_access": None},
                {"domain": None, "project": None, "loaded_at": None, "hit_count": 0, "last_access": None},
                {"domain": None, "project": None, "loaded_at": None, "hit_count": 0, "last_access": None}
            ],
            "performance": {
                "cache_hit_rate": 0.0,
                "total_accesses": 0,
                "cache_hits": 0,
                "cache_misses": 0
            }
        },
        "performance": {
            "prediction_latency_ms": 0,
            "cache_hit_rate": 0.0,
            "accuracy": 0.0,
            "total_predictions": 0,
            "correct_predictions": 0,
            "false_switches": 0,
            "last_calculated": None
        },
        "bootstrap": {
            "cold_start": True,
            "seed_loaded": False,
            "seeded_at": None
        }
    }

def save_prediction_state(state):
    """Save prediction state with atomic write (v3.2 - prevents corruption)"""
    temp_file = None
    try:
        PREDICTION_STATE.parent.mkdir(parents=True, exist_ok=True)

        # v3.2: Atomic write - write to temp file then rename
        temp_file = PREDICTION_STATE.with_suffix('.tmp')
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=2, ensure_ascii=False)

        # Atomic rename (prevents partial writes from corrupting state)
        temp_file.replace(PREDICTION_STATE)

    except IOError as e:
        log_error("state_save_error", "Failed to save prediction state", e)
        # Cleanup temp file if it exists
        if temp_file and temp_file.exists():
            try:
                temp_file.unlink()
            except Exception:
                pass  # Silent cleanup failure

def load_seed_predictions():
    """Load bootstrap seed predictions for cold start"""
    try:
        if SEED_PREDICTIONS.exists():
            # v3.1 FIX: Use UTF-8 encoding for cross-platform compatibility
            with open(SEED_PREDICTIONS, 'r', encoding='utf-8') as f:
                return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        log_error("seed_load_error", "Failed to load seed predictions", e)

    # Fallback: minimal defaults (keep in sync with session/seed_predictions.json)
    return {
        "cold_start_keywords": {
            "ticketing": ["cw", "ticketing", "opportunity", "ticket"],
            "crm": ["hs", "crm", "deal", "pipeline"],
            "cad-tool": ["cad", "cad-tool", "drawing", "model", "blueprint"],
            "finance": ["stock", "ticker", "rsi", "alpaca", "btc", "trading", "portfolio", "candlestick", "watchlist"],
            "cyber": ["ctf", "bounty", "h1", "burp", "xss", "sqli", "hack", "exploit"],
            "legal": ["contract", "nda", "msa", "sow", "agreement"],
            "leroy": ["leroy", "invoice", "payment", "billing"],
            "memory": ["recall", "consolidate", "memory", "note"]
        },
        "defaults_by_project": {
            "work": {"primary_domain": "ticketing", "weight": 0.6},
            "product": {"primary_domain": "cad-tool", "weight": 0.05},
            "teaching": {"primary_domain": "LMS", "weight": 0.05},
            "meta": {"primary_domain": "memory", "weight": 0.3}
        }
    }

def load_prompt_history(limit=50):
    """Load last N prompts from history"""
    entries = []
    try:
        if PROMPT_HISTORY.exists():
            # v3.1 FIX: Use UTF-8 encoding for cross-platform compatibility
            with open(PROMPT_HISTORY, 'r', encoding='utf-8', errors='replace') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            entries.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
    except IOError as e:
        log_error("history_load_error", "Failed to load prompt history", e)

    return entries[-limit:] if entries else []

def bootstrap_prediction(prompt_text, seeds):
    """Cold start prediction using seed keywords"""
    prompt_lower = prompt_text.lower()

    # Keyword matching
    domain_scores = {}
    for domain, keywords in seeds.get("cold_start_keywords", {}).items():
        score = sum(1 for kw in keywords if kw in prompt_lower)
        if score > 0:
            domain_scores[domain] = score

    # Get top domain
    if domain_scores:
        top_domain = max(domain_scores, key=domain_scores.get)
        confidence = 0.65  # Medium confidence for bootstrap
    else:
        # Fallback to the primary-project default
        top_domain = "ticketing"
        confidence = 0.50

    # Map domain to project
    project = map_domain_to_project(top_domain, seeds)

    return {
        "domain": top_domain,
        "project": project,
        "confidence": confidence,
        "source": "seed"
    }

def map_domain_to_project(domain, seeds=None):
    """Map domain to most likely project"""
    mapping = {
        "ticketing": "work",
        "crm": "work",
        "catalog": "work",
        "cad-tool": "product",
        "LMS": "teaching",
        "memory": "meta",
        "git": "meta",
        "playwright": "meta"
    }
    return mapping.get(domain, "meta")

def analyze_prompt_history(prompt_text, history, seeds):
    """Analyze last 50 prompts for domain patterns (weighted frequency)"""
    if not history:
        return bootstrap_prediction(prompt_text, seeds)

    # Extract keywords from history + current prompt
    all_prompts = [entry.get("prompt", "") for entry in history] + [prompt_text]

    domain_scores = defaultdict(float)
    keywords = seeds.get("cold_start_keywords", {})

    for i, prompt in enumerate(all_prompts):
        prompt_lower = prompt.lower()
        # Recency weight: Last 10 prompts = 1.0, older = 0.5
        recency_weight = 1.0 if i >= len(all_prompts) - 10 else 0.5

        for domain, kw_list in keywords.items():
            for kw in kw_list:
                if kw in prompt_lower:
                    domain_scores[domain] += recency_weight

    if not domain_scores:
        return bootstrap_prediction(prompt_text, seeds)

    # Get top domain
    top_domain = max(domain_scores, key=domain_scores.get)
    top_score = domain_scores[top_domain]
    total_score = sum(domain_scores.values())

    # Calculate confidence
    confidence = min(top_score / total_score, 0.95) if total_score > 0 else 0.50

    # Map to project
    project = map_domain_to_project(top_domain, seeds)

    return {
        "domain": top_domain,
        "project": project,
        "confidence": confidence,
        "source": "pattern"
    }

def check_confirmation_window(state, new_domain):
    """Check if domain switch requires confirmation (3-prompt threshold)"""
    window = state["confirmation_window"]
    current_domain = state["current_prediction"]["domain"]

    if not window["enabled"]:
        return False  # Confirmation disabled

    # If no current domain (initial state), allow first prediction
    if current_domain is None:
        return False

    if new_domain == current_domain:
        # Same domain - reset streak
        window["current_streak"] = 0
        window["pending_switch"] = None
        return False

    # Different domain - increment streak
    window["current_streak"] += 1
    window["pending_switch"] = new_domain
    window["pending_domain"] = new_domain

    # Check threshold
    if window["current_streak"] >= window["threshold"]:
        # Confirm switch
        window["current_streak"] = 0
        window["pending_switch"] = None
        return False  # Allow switch

    # Still in confirmation window - block switch
    return True

def check_cache(state, domain, project):
    """Check if domain is in multi-slot cache"""
    cache = state["multi_slot_cache"]
    now = datetime.now().isoformat()

    for slot in cache["slots"]:
        if slot["domain"] == domain and slot["project"] == project:
            # Cache hit
            slot["hit_count"] += 1
            slot["last_access"] = now
            cache["performance"]["cache_hits"] += 1
            cache["performance"]["total_accesses"] += 1
            return True, slot

    # Cache miss
    cache["performance"]["cache_misses"] += 1
    cache["performance"]["total_accesses"] += 1
    return False, None

def insert_cache(state, domain, project):
    """Insert domain into cache (evict LRU if full)"""
    cache = state["multi_slot_cache"]
    now = datetime.now().isoformat()

    # Find empty slot
    for slot in cache["slots"]:
        if slot["domain"] is None:
            slot["domain"] = domain
            slot["project"] = project
            slot["loaded_at"] = now
            slot["hit_count"] = 1
            slot["last_access"] = now
            return

    # No empty slots - evict LRU (lowest hit_count)
    lru_slot = min(cache["slots"], key=lambda s: s["hit_count"])
    lru_slot["domain"] = domain
    lru_slot["project"] = project
    lru_slot["loaded_at"] = now
    lru_slot["hit_count"] = 1
    lru_slot["last_access"] = now


def extract_and_match_entities(prompt_text):
    """
    v3.0: Extract client entities from prompt and match to notes.

    This is the core of the Predictive Client Context system.

    Args:
        prompt_text: User's prompt

    Returns:
        Dict with:
        - entities: Extracted entity data
        - client_notes: List of matched note paths
        - match_scores: Dict of {path: score}
        - confidence: Combined confidence score
        - total_time_ms: Processing time
    """
    try:
        if not _ENTITY_MODULES_LOADED:
            raise ImportError("Entity modules not available")

        # Use pre-imported module functions

        # Step 1: Extract entities (<15ms target)
        entities = _extract_client_entities(prompt_text)

        # Step 2: Match to notes if confidence meets threshold (<10ms target)
        client_notes = []
        match_scores = {}
        entity_match_time = 0

        if entities['confidence'] >= ENTITY_CONFIDENCE_THRESHOLD:
            matches = _match_entities_to_notes(entities, top_n=3)
            client_notes = matches['matched_notes']
            match_scores = matches['match_scores']
            entity_match_time = matches['match_time_ms']

        total_time = entities['extraction_time_ms'] + entity_match_time

        return {
            'entities': entities,
            'client_notes': client_notes,
            'match_scores': match_scores,
            'confidence': entities['confidence'],
            'total_time_ms': total_time
        }

    except ImportError as e:
        # Entity extraction not available - continue without it
        log_error("entity_import_error", "Entity extraction modules not found", e)
        return {
            'entities': {
                'names': [], 'companies': [], 'deal_ids': [],
                'crm_ids': [], 'whitelist_matches': [],
                'confidence': 0.0, 'extraction_time_ms': 0
            },
            'client_notes': [],
            'match_scores': {},
            'confidence': 0.0,
            'total_time_ms': 0
        }
    except Exception as e:
        # Any other error - log and continue
        log_error("entity_extraction_error", "Entity extraction failed", e)
        return {
            'entities': {
                'names': [], 'companies': [], 'deal_ids': [],
                'crm_ids': [], 'whitelist_matches': [],
                'confidence': 0.0, 'extraction_time_ms': 0
            },
            'client_notes': [],
            'match_scores': {},
            'confidence': 0.0,
            'total_time_ms': 0
        }


def detect_prompt_local_domain(prompt_lower, seed_keywords):
    """
    v5.1: Direct keyword scan on current prompt — ignores confirmation window.
    Returns (domain, score) for the best-matching domain, or (None, 0) if weak.
    Used to override cached domain when prompt has strong local signals.
    """
    domain_scores = {}
    for domain, keywords in seed_keywords.items():
        score = sum(1 for kw in keywords if kw in prompt_lower)
        if score > 0:
            domain_scores[domain] = score
    if not domain_scores:
        return None, 0
    best = max(domain_scores, key=domain_scores.get)
    return best, domain_scores[best]


def compute_skill_suggestions(domain, confidence, prompt_text):
    """
    v5.1: Predictive skill suggestion — maps detected domain + activity to top skills.
    Called after entity extraction, before state is saved.

    Uses prompt-local domain detection to override cached domain when current prompt
    has strong keyword signals (fixes confirmation_window lock on "memory").

    Scoring: domain_match(0.5) + keyword_overlap(0.3) + not_seen_today(0.2)
    Returns: list of up to 3 dicts with keys: skill, label, trigger_phrase, score, domain, activity
    """
    # v5.1: Confidence gating for suggestions vs domain prediction.
    # Domain prediction needs high confidence to avoid flickering (confirmation_window).
    # Suggestions use a lower bar: accept any non-trivial confidence, because
    # prompt-local override below can replace the domain with a stronger signal.
    # If confidence is very low (trivial/junk prompt), skip entirely.
    if confidence < 0.25:
        return []

    MATRIX_PATH = SESSION_DIR / "skill-surface-matrix.json"
    SUGGESTIONS_PATH = SESSION_DIR / "skill-suggestions.json"

    if not MATRIX_PATH.exists():
        return []

    try:
        with open(MATRIX_PATH, 'r', encoding='utf-8') as f:
            matrix_data = json.load(f)
    except (json.JSONDecodeError, IOError):
        return []

    # Detect activity type from prompt (single-pass keyword scan)
    prompt_lower = prompt_text.lower()

    # v5.1: Prompt-local domain override — if current prompt has strong signals
    # for a different domain than the cached one, use the prompt-local domain.
    # This prevents the confirmation_window from locking suggestions on stale domains.
    seed_keywords = matrix_data.get("activity_verbs", {})  # reuse for domain seeds too
    try:
        seed_file = SESSION_DIR / "seed_predictions.json"
        if seed_file.exists():
            with open(seed_file, 'r', encoding='utf-8') as sf:
                seed_data = json.load(sf)
            prompt_domain, prompt_score = detect_prompt_local_domain(
                prompt_lower, seed_data.get("cold_start_keywords", {})
            )
            # Override if: prompt has 2+ keyword hits AND different from cached domain
            if prompt_domain and prompt_score >= 2 and prompt_domain != domain:
                domain = prompt_domain
    except Exception:
        pass  # Non-blocking — fall back to cached domain
    activity_verbs = matrix_data.get("activity_verbs", {
        "audit":       ["review", "check", "scan", "assess", "score", "audit", "validate", "verify"],
        "build":       ["build", "implement", "create", "refactor", "migrate", "fix", "add", "write"],
        "report":      ["report", "summary", "weekly", "dashboard", "snapshot", "export", "bundle", "status"],
        "communicate": ["email", "draft", "proposal", "letter", "send", "message", "reply", "compose"],
        "analyze":     ["analyze", "research", "investigate", "postmortem", "why", "explain", "study", "query"],
        "automate":    ["automate", "trigger", "routine", "schedule", "every", "recurring", "loop"],
    })

    activity_scores = {}
    for act, verbs in activity_verbs.items():
        activity_scores[act] = sum(1 for v in verbs if v in prompt_lower)

    best_activity = max(activity_scores, key=activity_scores.get)
    if activity_scores[best_activity] == 0:
        best_activity = "default"

    # Get candidates from matrix
    domain_matrix = matrix_data.get("matrix", {}).get(domain, {})
    candidates = []
    seen_skills = set()

    for skill_entry in domain_matrix.get(best_activity, []):
        k = skill_entry.get("skill", "")
        if k not in seen_skills:
            candidates.append(skill_entry)
            seen_skills.add(k)

    # Also add default (avoid dupes)
    for skill_entry in domain_matrix.get("default", []):
        k = skill_entry.get("skill", "")
        if k not in seen_skills:
            candidates.append(skill_entry)
            seen_skills.add(k)

    # If no domain match, use fallback
    if not candidates:
        for skill_entry in matrix_data.get("fallback", []):
            k = skill_entry.get("skill", "")
            if k not in seen_skills:
                candidates.append(skill_entry)
                seen_skills.add(k)

    # Load today's seen list for dedup
    seen_today = set()
    try:
        if SUGGESTIONS_PATH.exists():
            with open(SUGGESTIONS_PATH, 'r', encoding='utf-8') as f:
                sess = json.load(f)
            for entry in sess.get("suggested_today", []):
                seen_today.add(entry.get("skill", ""))
    except (json.JSONDecodeError, IOError):
        pass

    # Score candidates
    scored = []
    for cand in candidates:
        skill_path = cand.get("skill", "")
        # domain_match: 0.5 (we're in the right domain matrix)
        domain_score = 0.5
        # keyword_overlap: check trigger phrase words against prompt
        trigger_words = cand.get("trigger_phrase", "").lower().split()
        if trigger_words:
            overlap = sum(1 for w in trigger_words if w in prompt_lower) / len(trigger_words)
        else:
            overlap = 0.0
        keyword_score = overlap * 0.3
        # novelty: not suggested today
        novelty_score = 0.2 if skill_path not in seen_today else 0.0
        total = domain_score + keyword_score + novelty_score
        scored.append({
            "skill": skill_path,
            "label": cand.get("label", ""),
            "trigger_phrase": cand.get("trigger_phrase", ""),
            "score": round(total, 3),
            "domain": domain,
            "activity": best_activity,
        })

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:3]


def save_skill_suggestions(suggestions, domain):
    """
    v5.0: Persist current suggestions to skill-suggestions.json.
    Uses append-log pattern (separate from prediction-state atomic writes).
    """
    SUGGESTIONS_PATH = SESSION_DIR / "skill-suggestions.json"
    try:
        existing = {}
        if SUGGESTIONS_PATH.exists():
            try:
                with open(SUGGESTIONS_PATH, 'r', encoding='utf-8') as f:
                    existing = json.load(f)
            except (json.JSONDecodeError, IOError):
                existing = {}

        # Build today's log entries for newly-surfaced suggestions
        suggested_today = existing.get("suggested_today", [])
        known_skills = {e["skill"] for e in suggested_today}
        for sugg in suggestions:
            if sugg["skill"] not in known_skills:
                suggested_today.append({
                    "skill": sugg["skill"],
                    "label": sugg.get("label", ""),
                    "trigger_phrase": sugg.get("trigger_phrase", ""),
                    "suggested_at": datetime.now().isoformat(),
                    "adopted": False,
                    "domain": domain,
                })

        stats = existing.get("stats", {"total_suggestions": 0, "total_adopted": 0})
        stats["total_suggestions"] = len(suggested_today)
        stats["total_adopted"] = sum(1 for e in suggested_today if e.get("adopted", False))

        output = {
            "version": "1.0",
            "last_updated": datetime.now().isoformat(),
            "current_suggestions": suggestions,
            "suggested_today": suggested_today,
            "stats": stats,
        }

        temp_path = SUGGESTIONS_PATH.with_suffix('.tmp')
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        temp_path.replace(SUGGESTIONS_PATH)

    except Exception:
        pass  # Non-blocking — skill suggestions are informational only


def detect_legal_trigger(prompt_text, entity_result):
    """
    v4.0: Detect if prompt indicates legal work needed.

    Detects:
    - Explicit legal keywords (contract, agreement, NDA)
    - New client signals (preliminary email, new deal)
    - Deal stage progression (send quote, proposal)

    Target: <5ms additional latency

    Args:
        prompt_text: User's prompt text
        entity_result: Entity extraction results (for client context)

    Returns:
        Dict with:
        - detected: bool - whether legal trigger found
        - confidence: float 0.0-1.0
        - reason: str - why triggered
        - client_name: str or None - extracted client if available
        - trigger_type: str - 'explicit', 'new_client', or 'deal_stage'
    """
    result = {
        'detected': False,
        'confidence': 0.0,
        'reason': None,
        'client_name': None,
        'trigger_type': None
    }

    if not prompt_text or len(prompt_text) < 10:
        return result

    prompt_lower = prompt_text.lower()

    # Trigger patterns by category
    trigger_patterns = {
        'explicit': [
            (r'\blegal\b', 0.7),
            (r'\bcontract\b', 0.8),
            (r'\bagreement\b', 0.8),
            (r'\bnda\b', 0.9),
            (r'\bsign(ing|ed)?\s+(the\s+)?(contract|agreement|nda)\b', 0.95),
            (r'\breview\s+(the\s+)?(contract|agreement)\b', 0.9),
            (r'\bdraft\s+(a\s+)?(contract|agreement|nda)\b', 0.95),
        ],
        'new_client': [
            (r'preliminary\s+email', 0.85),
            (r'new\s+(deal|client|prospect)', 0.75),
            (r'first\s+(contact|email|meeting)', 0.65),
            (r'onboard(ing)?\s+(new\s+)?client', 0.8),
        ],
        'deal_stage': [
            (r'send(ing)?\s+(the\s+)?(quote|proposal)', 0.7),
            (r'close\s+(the\s+)?deal', 0.75),
            (r'ready\s+to\s+sign', 0.9),
            (r'before\s+signing', 0.85),
            (r'insurance\s+(check|coverage|alignment)', 0.9),
        ]
    }

    max_confidence = 0.0
    matched_type = None
    matched_reason = None

    for trigger_type, patterns in trigger_patterns.items():
        for pattern, confidence in patterns:
            if re.search(pattern, prompt_lower):
                if confidence > max_confidence:
                    max_confidence = confidence
                    matched_type = trigger_type
                    matched_reason = f"Matched pattern: {pattern}"

    # Extract client name from entities if available
    client_name = None
    if entity_result and entity_result.get('entities'):
        entities = entity_result['entities']
        whitelist_matches = entities.get('whitelist_matches', [])
        companies = entities.get('companies', [])

        if whitelist_matches:
            client_name = whitelist_matches[0]
        elif companies:
            client_name = companies[0]

    # Set result if confidence meets threshold (0.5)
    if max_confidence >= 0.5:
        result['detected'] = True
        result['confidence'] = max_confidence
        result['reason'] = matched_reason
        result['client_name'] = client_name
        result['trigger_type'] = matched_type

    return result


def predict_domain(prompt_text):
    """Main prediction logic (v3.0 - with entity extraction)"""
    start_time = time.time()

    # Load state
    state = load_prediction_state()
    seeds = load_seed_predictions()

    # Step 1: Cold start check (use bootstrap for first 20 prompts)
    history = load_prompt_history(limit=50)
    total_predictions = state["performance"]["total_predictions"]

    if total_predictions < 20:
        # Bootstrap mode: Use seed keywords for first 20 prompts
        # This allows enough time for patterns to emerge before switching to history analysis
        prediction = bootstrap_prediction(prompt_text, seeds)
        if not state["bootstrap"]["seed_loaded"]:
            state["bootstrap"]["seed_loaded"] = True
            state["bootstrap"]["seeded_at"] = datetime.now().isoformat()
        if total_predictions >= 19:
            # Last bootstrap prediction - switch to pattern mode next time
            state["bootstrap"]["cold_start"] = False
    else:
        # Step 2: Analyze prompt history (after 10 prompts)
        prediction = analyze_prompt_history(prompt_text, history, seeds)

    # Step 3: v3.0 - Extract and match client entities
    entity_result = extract_and_match_entities(prompt_text)

    # Step 3.5: v4.0 - Detect legal triggers for background spawn
    legal_trigger = detect_legal_trigger(prompt_text, entity_result)

    # Step 4: Confirmation window check
    requires_confirmation = check_confirmation_window(state, prediction["domain"])
    if requires_confirmation:
        # Keep current domain, don't switch yet
        prediction = state["current_prediction"].copy()
        prediction["source"] = "confirmation_pending"

    # Step 5: Cache check
    cache_hit, cached_slot = check_cache(state, prediction["domain"], prediction["project"])
    if not cache_hit:
        # Cache miss - insert into cache
        insert_cache(state, prediction["domain"], prediction["project"])

    # Calculate latency (includes entity extraction time)
    latency_ms = (time.time() - start_time) * 1000

    # Step 5.5: v5.0 - Compute contextual skill suggestions
    skill_suggestions = compute_skill_suggestions(
        domain=prediction["domain"],
        confidence=prediction["confidence"],
        prompt_text=prompt_text,
    )
    if skill_suggestions:
        save_skill_suggestions(skill_suggestions, prediction["domain"])

    # Update state (v5.0 - includes entities, client_notes, legal_trigger, skill_suggestions)
    state["current_prediction"] = {
        "domain": prediction["domain"],
        "project": prediction["project"],
        "confidence": prediction["confidence"],
        "predicted_at": datetime.now().isoformat(),
        "source": prediction["source"],
        "prediction_latency_ms": latency_ms,
        # v3.0: Entity extraction results
        "entities": entity_result['entities'],
        # v3.0: Matched client notes for memory recall injection
        "client_notes": entity_result['client_notes'],
        "client_match_scores": entity_result['match_scores'],
        "entity_match_time_ms": entity_result['total_time_ms'],
        # v4.0: Legal trigger detection for background spawn
        "legal_trigger": legal_trigger,
        # v5.0: Predictive skill suggestions
        "skill_suggestions": skill_suggestions,
    }

    # Update performance metrics
    perf = state["performance"]
    perf["prediction_latency_ms"] = latency_ms
    perf["total_predictions"] += 1

    # Calculate cache hit rate
    cache_perf = state["multi_slot_cache"]["performance"]
    total = cache_perf["total_accesses"]
    if total > 0:
        cache_perf["cache_hit_rate"] = cache_perf["cache_hits"] / total
        perf["cache_hit_rate"] = cache_perf["cache_hit_rate"]

    # Save state
    save_prediction_state(state)

    return {
        "domain": prediction["domain"],
        "project": prediction["project"],
        "confidence": prediction["confidence"],
        "latency_ms": latency_ms,
        "cache_hit": cache_hit,
        "source": prediction["source"],
        # v3.0: Entity and client context
        "entities": entity_result['entities'],
        "client_notes": entity_result['client_notes'],
        "entity_confidence": entity_result['confidence'],
        "has_client_context": len(entity_result['client_notes']) > 0,
        # v4.0: Legal trigger detection
        "legal_trigger": legal_trigger
    }

def main():
    """Hook entry point"""
    try:
        # Read prompt from stdin (hook input)
        # v3.2 FIX: Handle binary input from subprocess for Unicode safety
        if not sys.stdin.isatty():
            if hasattr(sys.stdin, 'buffer'):
                raw_data = sys.stdin.buffer.read()
                input_data = raw_data.decode('utf-8', errors='replace')
            else:
                input_data = sys.stdin.read()
        else:
            # Test mode
            input_data = "Check ticketing opportunity 12345"

        # Extract prompt text (simple for now - just use full input)
        prompt_text = input_data.strip()

        if not prompt_text or len(prompt_text) < 5:
            # Skip prediction for trivial inputs
            sys.exit(0)

        # Run prediction
        result = predict_domain(prompt_text)

        # Output result (for debugging - not shown to user by default)
        # print(f"[PREDICTION] Domain: {result['domain']} | Project: {result['project']} | "
        #       f"Confidence: {result['confidence']:.0%} | Latency: {result['latency_ms']:.0f}ms | "
        #       f"Cache: {'HIT' if result['cache_hit'] else 'MISS'}")

        # Check performance warning (soft warning vs hard timeout)
        if result['latency_ms'] > LATENCY_TIMEOUT_MS:
            # Print only — do NOT log to error-log.jsonl (performance warnings flood enforcement queue)
            print(f"[WARN] Prediction TIMEOUT: {result['latency_ms']:.0f}ms (limit: {LATENCY_TIMEOUT_MS}ms)")
        elif result['latency_ms'] > LATENCY_TARGET_MS:
            print(f"[WARN] Prediction latency HIGH: {result['latency_ms']:.0f}ms (target: {LATENCY_TARGET_MS}ms)")

        # Exit success
        sys.exit(0)

    except Exception as e:
        # Graceful failure - log error but don't block hook chain
        log_error("prediction_error", "Prediction engine failed", e)
        # Continue without prediction (reactive loading fallback)
        sys.exit(0)

if __name__ == "__main__":
    main()
