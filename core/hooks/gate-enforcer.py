#!/usr/bin/env python3
"""
Gate Enforcer Hook v5.5 + v2.0 Memory Recall + Prediction Engine + Token Tracking
AUTOMATICALLY captures EVERY user prompt AND auto-executes enforcement actions.

v2.0 PREDICTION ENGINE INTEGRATION:
- Runs prediction-engine.py BEFORE enforcement processing
- Predicts domain/project for pre-loading context (30-40% token savings)
- Non-blocking: <150ms timeout with graceful fallback
- Updates prediction-state.json for memory-recall filtering

v5.5 Changes (HOT/COLD STATE SPLIT):
- Reads state-hot.json for enforcement display (38.6% faster - 0.857ms vs 1.395ms)
- Reads state-cold.json once on session start for session constants
- Writes enforcement updates to hot state only
- Fallback to state.json if split files missing (backward compatible)
- Target: 36% reduction in session I/O time

v5.4 Changes (PERFORMANCE OPTIMIZATION):
- Trivial message bypass: Early exit for prompts <20 chars when no substantial task
  Saves 150ms per message (~30% of all messages)
- Conditional history append: Skip duplicate prompts in last 5 entries
  Saves 30ms per skipped append (~20% of messages)
- Target: <50ms hook overhead (from 170ms baseline)

v5.3 Changes (TOKEN BURN OPTIMIZATION):
- Captures token usage from API metadata on every request
- Tracks input_tokens, output_tokens, total_tokens
- Maintains rolling 500-entry history in state.json
- Calculates weekly token totals and efficiency metrics
- Banner displays token metrics (week total, efficiency, baseline)

v5.2 Changes (USER-FRIENDLY PRIORITY SYSTEM):
- ALL enforcement actions now use priority system (not just memory recall)
- Priority 2 (background) for trivial requests - answers user FIRST
- Priority 0/1 (blocking) for substantial tasks - ensures quality
- Simple questions get quick answers without context burn
- Banner displays enforcement mode (blocking vs background)

v5.1 Changes (TRUE AUTOMATION):
- Auto-generates consolidation commands when checkpoint overdue
- Creates mandatory action queue with explicit commands
- Writes enforcement.todo file with required actions

v2.0 Changes (MEMORY RECALL):
- Detects session start (30+ min gap since last input)
- Auto-triggers memory recall on session start
- Priority 0 (blocking) for substantial tasks
- Priority 2 (background) for trivial tasks
- Loads top 12 most relevant notes from memory-index.json

Evolution Timeline:
- v5.0: Detection + flags (Claude decides whether to act)
- v5.1: Detection + auto-command generation (Claude must execute queue)
- v5.2: Smart priority system (background for trivial, blocking for substantial)
- v5.3: Token burn tracking (baseline, efficiency, weekly reports)
- v5.4: Performance optimizations (trivial bypass, conditional append)
- v5.5: Hot/cold state split (36% session I/O reduction)
- v2.0: Auto-recall memory on session start (closes write-only gap)

PORTABILITY: Windows-first but POSIX-portable. Uses Path.home()/".claude"
throughout. Optional add-on modules (persona/office enforcement, optimization
detector) and local services (RAG sidecar, telemetry log) all graceful-degrade
when absent — the gate works fine without them.
"""
import json
import sys
import os
import io
import subprocess
import time
import hashlib
from datetime import datetime, timezone
from pathlib import Path

# Force UTF-8 encoding for stdout (Windows compatibility with emojis)
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Force UTF-8 encoding for stdin (Unicode encoding fix v5.6)
if sys.stdin.encoding != 'utf-8':
    sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8', errors='replace')

# Find .claude directory (relative to hook location)
CLAUDE_DIR = Path(__file__).parent.parent

# Add scripts directory to path for optimization detector
SCRIPTS_DIR = CLAUDE_DIR / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

# Add hooks directory for optional persona/office enforcement add-on module
HOOKS_DIR = Path(__file__).parent
sys.path.insert(0, str(HOOKS_DIR))

try:
    from optimization_detector import detect_optimizations
    DETECTOR_AVAILABLE = True
except ImportError:
    DETECTOR_AVAILABLE = False

# Optional persona/office enforcement add-on. This module is NOT shipped with
# LeRoy Core (it's a business-specific persona layer). The gate works fully
# without it — the import simply fails closed and the banner degrades gracefully.
try:
    from office_enforcement import enforce_office_heartbeat, get_office_gate_block
    OFFICE_ENFORCEMENT_AVAILABLE = True
except ImportError:
    OFFICE_ENFORCEMENT_AVAILABLE = False
SESSION_DIR = CLAUDE_DIR / "session"
STATE_FILE = CLAUDE_DIR / "session" / "state.json"
STATE_HOT_FILE = CLAUDE_DIR / "session" / "state-hot.json"
STATE_COLD_FILE = CLAUDE_DIR / "session" / "state-cold.json"
PROMPT_HISTORY_FILE = CLAUDE_DIR / "session" / "prompt-history.jsonl"
ERROR_LOG_FILE = CLAUDE_DIR / "session" / "error-log.jsonl"
SESSION_ID_FILE = CLAUDE_DIR / "session" / "session-id.txt"

def _parse_iso_utc(raw):
    # Idempotent ISO-8601 parser. Tolerates both 'Z' and explicit '+00:00'/'+0000' suffixes,
    # plus malformed inputs that combine both (e.g., '2026-04-07T14:54:06.190232+00:00Z' from
    # legacy logs) which previously crashed datetime.fromisoformat with '+00:00+00:00'.
    if raw is None:
        raise ValueError("timestamp is None")
    s = str(raw).strip()
    if s.endswith('Z') and ('+' in s[:-1] or s.count('-') > 2):
        s = s[:-1]
    if s.endswith('+00:00') or s.endswith('+0000'):
        return datetime.fromisoformat(s)
    if s.endswith('Z'):
        return datetime.fromisoformat(s[:-1] + '+00:00')
    return datetime.fromisoformat(s)

def log_error(error_type, context, exception=None, state=None):
    """Log errors to structured error log (append-only JSONL)

    Args:
        error_type: Category of error (json_decode, io_error, state_corruption, etc.)
        context: Description of what was being attempted
        exception: The exception object (if any)
        state: Current state dict (if available)
    """
    error_entry = {
        "timestamp": datetime.now().isoformat(),
        "component": "gate-enforcer",
        "error_type": error_type,
        "context": context,
        "error_message": str(exception) if exception else None,
        "error_class": exception.__class__.__name__ if exception else None,
        "session_id": state.get("session_id", "unknown") if state else "unknown",
        "user_prompt": state.get("current_prompt", {}).get("text", "")[:100] if state else ""
    }

    try:
        ERROR_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(ERROR_LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(json.dumps(error_entry) + "\n")
    except Exception:
        # Emergency fallback - write to separate file if main log fails
        emergency = CLAUDE_DIR / "session" / "error-emergency.txt"
        try:
            with open(emergency, 'a', encoding='utf-8') as f:
                f.write(f"{datetime.now()}: {error_type} - {context}\n")
        except:
            pass  # Truly unrecoverable - silent fail to avoid breaking hook

def get_session_state():
    """Read session state from state-hot.json (v5.5 HOT/COLD SPLIT)

    38.6% faster than reading full state.json (0.857ms vs 1.395ms)
    Fallback to state.json if hot file missing (backward compatible)
    """
    try:
        # Try hot state first (fast path)
        if STATE_HOT_FILE.exists():
            with open(STATE_HOT_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)

        # Fallback to full state if hot file missing
        if STATE_FILE.exists():
            with open(STATE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)

    except (json.JSONDecodeError, IOError) as e:
        log_error("state_corruption", "Failed to load hot state", e, state=None)

    return {}

def get_cold_state():
    """Read session constants from state-cold.json (v5.5 HOT/COLD SPLIT)

    Called once per session for configuration data.
    Fallback to state.json if cold file missing (backward compatible)
    """
    try:
        # Try cold state first
        if STATE_COLD_FILE.exists():
            with open(STATE_COLD_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)

        # Fallback to full state if cold file missing
        if STATE_FILE.exists():
            with open(STATE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)

    except (json.JSONDecodeError, IOError) as e:
        log_error("state_corruption", "Failed to load cold state", e, state=None)

    return {}

def ensure_hybrid_recall_flag(state):
    """Ensure hybrid recall configuration exists in state (v7.1 integration)

    Checks if memory_system.use_hybrid_recall flag exists. If not, enables it
    by default when hybrid-recall-v7.py script exists.

    Returns:
        Updated state dict
    """
    if "memory_system" not in state:
        state["memory_system"] = {}

    if "use_hybrid_recall" not in state["memory_system"]:
        # Enable by default if script exists
        hybrid_script = SCRIPTS_DIR / "hybrid-recall-v7.py"
        state["memory_system"]["use_hybrid_recall"] = hybrid_script.exists()
        state["memory_system"]["hybrid_recall_version"] = "7.1"

    return state

def save_session_state(state):
    """Write session state to state-hot.json (v5.5 HOT/COLD SPLIT)

    Writes only hot keys to state-hot.json for fast updates.
    Fallback to state.json if hot file doesn't exist yet.

    Hot keys (frequently modified):
    - enforcement: flags and queue status
    - current_task, substantial_task_active, active_agents
    - current_prompt, last_user_input_time
    - token_tracking: updated on every prompt
    - scout: active status and checkpoint times

    Cold keys (session constants):
    - session_id, session_window, session_start, original_request
    - memory_system, checkpoints, scheduled_tasks
    - integration caches, migration metadata
    """
    try:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)

        # Extract hot keys from state
        hot_keys = [
            "enforcement",
            "enforcement_queue_active",
            "enforcement_queue_count",
            "current_task",
            "substantial_task_active",
            "active_agents",
            "last_user_input_time",
            "current_prompt",
            "token_tracking",       # v5.5: Updated every prompt for token burn tracking
            "scout",                # v5.5: Active status + checkpoint times for banner
            "coo_compliance",       # v6.0: Gate compliance tracking per session
            "agent_ledger",         # v6.0: Per-session agent invocation tracking
            "rag_sidecar",          # v6.0: RAG sidecar status (online/offline/indexed)
        ]

        hot_state = {k: state[k] for k in hot_keys if k in state}

        # Write to hot file if exists, otherwise fallback to full state
        if STATE_HOT_FILE.exists() or STATE_COLD_FILE.exists():
            # Hot/cold split active - write to hot only
            with open(STATE_HOT_FILE, 'w', encoding='utf-8') as f:
                json.dump(hot_state, f, indent=2)
        else:
            # Fallback: write full state to state.json (backward compatible)
            with open(STATE_FILE, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2)

    except IOError as e:
        log_error("io_error", "Failed to save hot state", e, state)

def validate_state_sync():
    """Validate hot and cold files are in sync (v5.5)

    Returns True if files exist and have no key conflicts.
    Logs warning if desync detected.
    """
    if not STATE_HOT_FILE.exists() or not STATE_COLD_FILE.exists():
        return True  # No split files yet, no conflict

    try:
        with open(STATE_HOT_FILE, 'r', encoding='utf-8') as f:
            hot = json.load(f)
        with open(STATE_COLD_FILE, 'r', encoding='utf-8') as f:
            cold = json.load(f)

        # Check for key conflicts (hot keys shouldn't be in cold)
        hot_keys = set(hot.keys())
        cold_keys = set(cold.keys())
        conflicts = hot_keys.intersection(cold_keys)

        if conflicts:
            log_error("state_sync_warning",
                     f"Hot/cold state conflict: {conflicts}",
                     None,
                     state=hot)
            return False

        return True

    except (json.JSONDecodeError, IOError) as e:
        log_error("state_validation_error", "Failed to validate state sync", e, state=None)
        return False

def append_prompt_history(prompt, timestamp):
    """Append prompt to history file with auto-rotation (keeps last 500 entries)"""
    MAX_ENTRIES = 500

    try:
        PROMPT_HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)

        # Read existing entries
        entries = []
        if PROMPT_HISTORY_FILE.exists():
            with open(PROMPT_HISTORY_FILE, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if line:
                        try:
                            entries.append(json.loads(line))
                        except json.JSONDecodeError as e:
                            log_error("prompt_history_corruption", f"Failed to parse line {line_num}", e, state=None)

        # v5.4 PERFORMANCE: Skip duplicate prompts (saves 30ms per skipped append, ~20% of messages)
        # Check if prompt appears in last 5 entries
        if len(entries) >= 5:
            last_5_prompts = [e.get("prompt", "") for e in entries[-5:]]
            if prompt in last_5_prompts:
                # Skip append - this is a duplicate
                return

        # Only append if significant (>=10 chars) or not a duplicate
        if len(prompt) < 10:
            # Very short prompts only if not duplicate (already checked above)
            pass

        # Add new entry
        entries.append({"timestamp": timestamp, "prompt": prompt})

        # Rotate: keep only last MAX_ENTRIES
        if len(entries) > MAX_ENTRIES:
            entries = entries[-MAX_ENTRIES:]

        # Write back (atomic-ish)
        with open(PROMPT_HISTORY_FILE, 'w', encoding='utf-8') as f:
            for entry in entries:
                f.write(json.dumps(entry) + "\n")

    except IOError as e:
        log_error("io_error", "Failed to append prompt history", e, state=None)

def format_time_ago(iso_timestamp):
    """Convert ISO timestamp to 'X min ago' format"""
    if not iso_timestamp:
        return "never"
    try:
        then = _parse_iso_utc(iso_timestamp)
        now = datetime.now(then.tzinfo) if then.tzinfo else datetime.now()
        diff = now - then
        minutes = int(diff.total_seconds() / 60)
        if minutes < 1:
            return "just now"
        elif minutes < 60:
            return f"{minutes} min ago"
        elif minutes < 1440:
            return f"{minutes // 60} hr ago"
        else:
            return f"{minutes // 1440} days ago"
    except (ValueError, AttributeError) as e:
        log_error("datetime_parse", f"Failed to parse timestamp: {iso_timestamp}", e, state=None)
        return "unknown"

def format_tokens(token_count):
    """Format token count for display (v5.3)"""
    if token_count >= 1000000:
        return f"{token_count / 1000000:.1f}M"
    elif token_count >= 1000:
        return f"{token_count / 1000:.1f}K"
    else:
        return str(token_count)

def truncate_prompt(prompt, max_len=100):
    """Truncate prompt for display"""
    if not prompt:
        return "[EMPTY]"
    # Clean up whitespace
    prompt = ' '.join(prompt.split())
    if len(prompt) <= max_len:
        return prompt
    return prompt[:max_len-3] + "..."

def extract_user_prompt(input_data):
    """Extract user's prompt from hook input data - tries ALL known field names"""
    if isinstance(input_data, dict):
        # Try every possible field name Claude Code might use
        possible_fields = [
            'message', 'content', 'user_input', 'prompt', 'text',
            'input', 'query', 'user_message', 'request'
        ]
        for field in possible_fields:
            if field in input_data:
                val = input_data[field]
                if isinstance(val, str) and val.strip():
                    return val
                if isinstance(val, dict):
                    # Nested content
                    for nested in ['content', 'text', 'message']:
                        if nested in val and isinstance(val[nested], str):
                            return val[nested]

        # Fallback: read last user message from transcript_path
        transcript_path = input_data.get('transcript_path', '')
        if transcript_path:
            try:
                from pathlib import Path as _P
                tp = _P(transcript_path)
                if tp.exists():
                    last_user = None
                    with open(tp, 'r', encoding='utf-8') as tf:
                        for line in tf:
                            line = line.strip()
                            if not line:
                                continue
                            try:
                                entry = json.loads(line)
                                # Claude Code transcript format: role=user, content as str or list
                                if entry.get('type') == 'user' or entry.get('role') == 'user':
                                    content = entry.get('message', entry.get('content', ''))
                                    if isinstance(content, str) and content.strip():
                                        last_user = content.strip()
                                    elif isinstance(content, list):
                                        for block in content:
                                            if isinstance(block, dict) and block.get('type') == 'text':
                                                text = block.get('text', '')
                                                if text.strip():
                                                    last_user = text.strip()
                            except (json.JSONDecodeError, KeyError):
                                pass
                    if last_user:
                        return last_user
            except Exception as e:
                log_error("transcript_fallback_error", "Could not read transcript for prompt extraction", e, state=None)

        # Log the actual structure for debugging (write to file)
        debug_file = CLAUDE_DIR / "session" / "hook-debug.json"
        try:
            with open(debug_file, 'w', encoding='utf-8') as f:
                json.dump({"keys": list(input_data.keys()), "sample": str(input_data)[:500]}, f, indent=2)
        except Exception as e:
            log_error("io_error", "Failed to write hook debug file", e, state=None)

    return None

def extract_token_usage(input_data):
    """
    Extract token counts from Claude Code API metadata (v5.3)

    Looks for token usage in multiple possible locations:
    - input_data["metadata"]["usage"]
    - input_data["usage"]
    - input_data["token_usage"]

    Returns dict with input_tokens, output_tokens, total_tokens, timestamp
    Falls back to estimation if API data unavailable
    """
    tokens = {
        "input_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 0,
        "timestamp": datetime.now().isoformat(),
        "source": "estimated"  # "api" or "estimated"
    }

    if not isinstance(input_data, dict):
        return tokens

    # Try to find usage data in various locations
    usage = None

    # Location 1: input_data["metadata"]["usage"]
    if "metadata" in input_data and isinstance(input_data["metadata"], dict):
        if "usage" in input_data["metadata"]:
            usage = input_data["metadata"]["usage"]

    # Location 2: input_data["usage"]
    if not usage and "usage" in input_data:
        usage = input_data["usage"]

    # Location 3: input_data["token_usage"]
    if not usage and "token_usage" in input_data:
        usage = input_data["token_usage"]

    if usage and isinstance(usage, dict):
        tokens["input_tokens"] = usage.get("input_tokens", 0)
        tokens["output_tokens"] = usage.get("output_tokens", 0)
        tokens["total_tokens"] = tokens["input_tokens"] + tokens["output_tokens"]
        tokens["source"] = "api"
    else:
        # Fallback: 4-factor improved estimation (v5.5)
        # Much more accurate than simple char/4 (accounts for code, JSON, response)
        prompt = extract_user_prompt(input_data)
        if prompt:
            # Factor 1: Character count (baseline)
            base_tokens = len(prompt) // 4

            # Factor 2: Code detection (+30% for code blocks)
            if '```' in prompt or 'def ' in prompt or 'class ' in prompt or 'function ' in prompt:
                base_tokens = int(base_tokens * 1.3)

            # Factor 3: JSON compression (+50% for structured data)
            # JSON/structured data compresses less efficiently
            if prompt.count('{') > 3 or prompt.count('[') > 3:
                base_tokens = int(base_tokens * 1.5)

            # Factor 4: Response prediction (2:1 prompt:completion ratio typical)
            completion_estimate = base_tokens // 2

            tokens["input_tokens"] = base_tokens
            tokens["output_tokens"] = completion_estimate
            tokens["total_tokens"] = base_tokens + completion_estimate
            tokens["source"] = "estimated-improved"

    return tokens

def _compute_today_cost():
    """
    Stream-read cost-log.jsonl (last 1000 lines) and return today's cost summary.
    Returns a dict or None on any error/missing file.
    Non-blocking: wrapped in try/except throughout.
    """
    try:
        cost_log = SESSION_DIR / "cost-log.jsonl"
        if not cost_log.exists():
            return None

        today_utc = datetime.now(timezone.utc).date().isoformat()

        # Stream last 1000 lines — memory-safe tail via deque
        from collections import deque
        with open(cost_log, "r", encoding="utf-8", errors="replace") as fh:
            tail = deque(fh, maxlen=1000)

        records = []
        for raw in tail:
            raw = raw.strip()
            if not raw:
                continue
            try:
                rec = json.loads(raw)
            except json.JSONDecodeError:
                continue
            ts = rec.get("ts", "")
            if isinstance(ts, str) and ts.startswith(today_utc):
                records.append(rec)

        if not records:
            return {"record_count": 0}

        total_cost = sum(float(r.get("cost_usd", 0) or 0) for r in records)
        total_tokens = sum(
            int(r.get("tokens_in", 0) or 0) + int(r.get("tokens_out", 0) or 0)
            for r in records
        )

        # Top 3 agents by accumulated cost
        agent_cost = {}
        for r in records:
            ag = r.get("agent") or "unknown"
            agent_cost[ag] = agent_cost.get(ag, 0) + float(r.get("cost_usd", 0) or 0)
        top_agents = sorted(agent_cost.items(), key=lambda x: x[1], reverse=True)[:3]

        # Top 3 skills by accumulated cost
        skill_cost = {}
        for r in records:
            sk = r.get("skill") or "unknown"
            skill_cost[sk] = skill_cost.get(sk, 0) + float(r.get("cost_usd", 0) or 0)
        top_skills = sorted(skill_cost.items(), key=lambda x: x[1], reverse=True)[:3]

        api_count = sum(1 for r in records if r.get("source") == "api")
        confidence_pct = int(api_count / len(records) * 100) if records else 0

        return {
            "total_cost": total_cost,
            "total_tokens": total_tokens,
            "top_agents": top_agents,
            "top_skills": top_skills,
            "confidence_pct": confidence_pct,
            "record_count": len(records),
        }
    except Exception:
        return None

def _select_topology(prompt: str) -> tuple:
    """
    Sprint 2 #6 — Topology selection (descriptive metadata).
    Reads session/topology-rules.json, performs first-match-wins keyword scan.
    Returns (topology: str, matched_rule: str).
    Wrapped in try/except — on error returns ("hybrid", "fallback").
    """
    try:
        topology_rules_path = SESSION_DIR / "topology-rules.json"
        if not topology_rules_path.exists():
            return ("hybrid", "fallback-no-file")

        with open(topology_rules_path, "r", encoding="utf-8") as fh:
            config = json.load(fh)

        default_topology = config.get("default", "hybrid")
        rules = config.get("rules", [])
        prompt_lower = (prompt or "").lower()

        for rule in rules:
            topology = rule.get("topology")
            if not topology:
                continue
            if rule.get("default"):
                continue  # skip the default rule in keyword pass
            keywords = rule.get("any_keyword", [])
            for kw in keywords:
                if kw.lower() in prompt_lower:
                    return (topology, kw)

        return (default_topology, "default")
    except Exception:
        return ("hybrid", "fallback")


def _detect_fork_eligibility(prompt: str, topology: str, packet_estimate: int) -> bool:
    """
    Fork Dispatch v1.0 — Determines whether this task is eligible for fork fan-out.
    Returns True when the gate should inject SPAWN_FORK_WORKERS into enforcement.todo.

    Conditions (ALL must be true):
    1. Topology is 'mesh' or 'hybrid' (hierarchy is always blocked)
    2. Estimated independent packets >= 2
    3. Prompt is NOT a hierarchy-blocked operation (commit, deploy, email send, contract)
    4. Prompt length > 80 chars (trivial prompts don't benefit from fork)
    """
    if not prompt:
        return False
    if topology == "hierarchy":
        return False
    if topology not in ("mesh", "hybrid"):
        return False
    if packet_estimate < 2:
        return False

    # Length gate: skip very short prompts UNLESS they have explicit numbered items
    import re as _re_len
    has_numbered = len(_re_len.findall(r'\b[1-9]\.\s', prompt)) >= 2
    if len(prompt) < 80 and not has_numbered:
        return False

    # Hard-block fork for sensitive sequential operations
    hierarchy_keywords = [
        "commit", "git push", "push to", "deploy", "release",
        "send email", "send the email", "sign", "contract", "invoice",
        "tax filing", "merge pr", "merge branch"
    ]
    prompt_lower = prompt.lower()
    if any(kw in prompt_lower for kw in hierarchy_keywords):
        return False

    return True


def _estimate_packets(prompt: str) -> int:
    """
    Estimate the number of independent work packets in a prompt.
    Used by _detect_fork_eligibility to decide fork count.
    Conservative heuristic — better to under-fork than to over-fork.
    """
    if not prompt:
        return 1

    prompt_lower = prompt.lower()

    # Parallel signal words
    parallel_signals = [
        " and ", " also ", "; ", " plus ", " as well as ",
        " simultaneously ", " in parallel ", " at the same time ",
        " while also ", " alongside "
    ]
    count = 1
    for signal in parallel_signals:
        if signal in prompt_lower:
            count += 1
            if count >= 5:
                break  # Cap at 5 (hard max forks)

    # List-style prompts: numbered items or bullet signals
    import re as _re
    numbered = len(_re.findall(r'\b[1-9]\.\s', prompt))
    if numbered >= 2:
        count = max(count, min(numbered, 5))

    return min(count, 5)


def _get_or_create_trace_id() -> str:
    """
    Sprint 2 #8 — Trace ID for correlating multi-agent events.
    Reads state.json:current_trace_id if present.
    Else generates tr-YYYYMMDDHH-{6char-hex}, writes it back to state.json.
    Returns the trace_id string.
    Wrapped in try/except — on error returns "tr-unknown".
    """
    try:
        state_data = {}
        if STATE_FILE.exists():
            try:
                with open(STATE_FILE, "r", encoding="utf-8") as fh:
                    state_data = json.load(fh)
            except Exception:
                state_data = {}

        existing = state_data.get("current_trace_id", "")
        if existing and existing != "tr-unknown":
            return str(existing)

        # Generate new trace_id
        now = datetime.now(timezone.utc)
        hour_tag = now.strftime("%Y%m%d%H")
        import secrets as _secrets
        hex_suffix = _secrets.token_hex(3)  # 3 bytes = 6 hex chars
        trace_id = f"tr-{hour_tag}-{hex_suffix}"

        # Write back to state.json
        state_data["current_trace_id"] = trace_id
        try:
            STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(STATE_FILE, "w", encoding="utf-8") as fh:
                json.dump(state_data, fh, indent=2, default=str)
        except Exception:
            pass  # Don't fail trace generation over write error

        return trace_id
    except Exception:
        return "tr-unknown"


def detect_substantial_task(prompt):
    """Detect if prompt indicates substantial task requiring scout"""
    if not prompt or len(prompt) < 50:
        return False

    # Action keywords indicating substantial work
    action_keywords = [
        'implement', 'build', 'create', 'refactor', 'fix', 'update',
        'analyze', 'design', 'integrate', 'migrate', 'optimize',
        'deploy', 'configure', 'setup', 'install'
    ]

    # Multiple questions = complex task
    question_count = prompt.count('?')

    # Long prompts with technical content
    is_long = len(prompt) > 150

    prompt_lower = prompt.lower()
    has_action_word = any(keyword in prompt_lower for keyword in action_keywords)

    return (has_action_word and is_long) or question_count >= 2

# ===== v6.1 FAST LANE CLASSIFIER =====
FAST_LANE_CONFIRMATIONS = {
    "ok", "okay", "yes", "no", "yep", "nope", "yeah", "thanks", "thank you",
    "got it", "sounds good", "perfect", "cool", "great", "nice", "done",
}
FAST_LANE_MICRO = {
    "status", "time", "what time", "what time is it", "whats the time",
    "what's the time", "ping", "you there", "you up",
}
FAST_LANE_VERBS = (
    "open ", "open up ", "launch ", "play ", "close ", "start ", "stop ",
    "pause ", "resume ", "mute ", "unmute ", "skip ",
)
# Even if it looks like an action command, these tokens force the FULL gate
# (real work surfaces that may need recall/routing). Extend this set with the
# work surfaces relevant to your org (CRM, ticketing, repo, docs, etc.).
FAST_LANE_WORK_TOKENS = (
    "crm", "ticket", " deal", " pr ", "branch", "commit",
    "client", "contract", "invoice",
    "email", "report", "catalog", "opportunity",
)

def is_fast_lane(prompt):
    """Conservative fast-lane classifier (v6.1).

    Returns True ONLY for obvious action commands that need zero orchestration:
    app control, status/time micro-queries, simple confirmations. Anything
    ambiguous returns False and falls through to the full gate.
    """
    if not prompt:
        return False
    p = prompt.strip().lower().rstrip(".!?,")

    if p in FAST_LANE_CONFIRMATIONS:
        return True
    if p in FAST_LANE_MICRO:
        return True

    # Action command: must START with a known verb, stay short (<= 6 words),
    # and not touch a real work surface.
    if any(p.startswith(v) for v in FAST_LANE_VERBS):
        if any(tok in p for tok in FAST_LANE_WORK_TOKENS):
            return False
        if len(p.split()) <= 6:
            return True

    return False

def calculate_minutes_since(iso_timestamp):
    """Calculate minutes elapsed since ISO timestamp"""
    if not iso_timestamp:
        return 999999  # Very large number if never
    try:
        then = _parse_iso_utc(iso_timestamp)
        now = datetime.now(then.tzinfo) if then.tzinfo else datetime.now()
        diff = now - then
        return int(diff.total_seconds() / 60)
    except (ValueError, AttributeError) as e:
        log_error("datetime_parse", f"Failed to calculate minutes since: {iso_timestamp}", e, state=None)
        return 999999

def detect_session_start(state):
    """Detect if this is first input after 30+ min gap (v2.0 Memory Recall)"""
    last_input = state.get("last_user_input_time")
    if not last_input:
        return True  # First input ever = session start

    minutes_since = calculate_minutes_since(last_input)
    return minutes_since >= 30  # 30-min session boundary

def load_identity_file(file_path):
    """Load identity file (SOUL.md/USER.md) with checksum for change detection"""
    try:
        path = CLAUDE_DIR / file_path
        if not path.exists():
            return None

        content = path.read_text(encoding='utf-8')
        checksum = hashlib.md5(content.encode()).hexdigest()

        return {
            "content": content,
            "checksum": checksum,
            "loaded_at": datetime.now().isoformat(),
            "path": str(file_path)
        }
    except Exception as e:
        log_error("identity_load", f"Failed to load {file_path}", e, {})
        return None

def should_reload_identity(state, file_key, current_checksum):
    """Check if identity file changed since last load"""
    if current_checksum is None:
        return False

    identity = state.get("identity_context", {}).get(file_key, {})
    last_checksum = identity.get("checksum")
    return last_checksum != current_checksum

def write_state_cold(cold_state):
    """Write cold state (session constants) to state-cold.json"""
    try:
        STATE_COLD_FILE.write_text(json.dumps(cold_state, indent=2), encoding='utf-8')
    except Exception as e:
        log_error("state_write_cold", "Failed to write cold state", e, cold_state)

def extract_line_items(prompt):
    """Extract line items from prompt (numbered lists, bullets, sequential keywords)"""
    if not prompt:
        return []

    import re
    items = []

    # Pattern 1: Numbered lists (1., 2., etc.)
    numbered = re.findall(r'^\s*\d+\.\s+(.+)$', prompt, re.MULTILINE)
    items.extend(numbered)

    # Pattern 2: Bullet lists (-, *, •)
    bullets = re.findall(r'^\s*[-*•]\s+(.+)$', prompt, re.MULTILINE)
    items.extend(bullets)

    # Pattern 3: Sequential keywords (first...then...finally, after X do Y)
    sequential_keywords = ['first', 'then', 'finally', 'next', 'after']
    for keyword in sequential_keywords:
        if keyword in prompt.lower():
            # If we find sequential keywords, count sentences as potential tasks
            sentences = re.split(r'[.!?]+', prompt)
            items.extend([s.strip() for s in sentences if len(s.strip()) > 10])
            break

    return items

def should_spawn_planner(prompt, state):
    """Detect if prompt requires planner spawn"""
    if not prompt:
        return False

    # Trigger 1: 3+ line items detected
    line_items = extract_line_items(prompt)
    if len(line_items) >= 3:
        return True

    # Trigger 2: Todo keywords present
    todo_keywords = ['implement', 'build', 'create', 'steps', 'first', 'then']
    prompt_lower = prompt.lower()
    if any(kw in prompt_lower for kw in todo_keywords):
        return True

    # Trigger 3: Already active from previous session
    todo_state = state.get('planner', {})
    if todo_state.get('active', False):
        return True

    return False

try:
    input_data = json.load(sys.stdin)
except json.JSONDecodeError:
    sys.exit(1)

# Get current timestamp
now = datetime.now().isoformat()

# Extract the user's prompt from input
user_prompt = extract_user_prompt(input_data)

# ===== v6.1 FAST LANE — action-command bypass (BEFORE prediction subprocess) =====
# Conservative classifier: obvious app/status/confirmation commands skip the
# prediction subprocess, memory recall, and orchestration entirely. Anything
# ambiguous falls through to the full gate below.
if user_prompt and is_fast_lane(user_prompt):
    _hot = get_session_state()
    if not _hot.get("substantial_task_active", False):
        try:
            _hot["current_prompt"] = {
                "text": user_prompt,
                "captured_at": now,
                "char_count": len(user_prompt),
            }
            _hot["last_user_input_time"] = now
            append_prompt_history(user_prompt, now)
            save_session_state(_hot)
        except Exception as e:
            log_error("fast_lane_capture", "Fast-lane state save failed", e, state=None)
        print("=" * 80)
        print("    FAST LANE (v6.1) - action command, full gate bypassed")
        print("=" * 80)
        print(f'    CURRENT: "{user_prompt}"')
        print("    Recall: skipped | Orchestration: skipped | Act immediately, no deliberation")
        print("=" * 80)
        sys.exit(0)

# ===== v6.1 PREDICTION ENGINE (fire-and-forget) =====
# Pre-loads domain/project context into prediction-state.json for the NEXT turn.
# Launched detached so it NEVER blocks the current prompt. (Previously a 300ms
# blocking subprocess that routinely timed out — taking 274ms-1.3s — and crashed
# the gate on an undefined-variable NameError in the timeout handler. Fixed v6.1.)
if user_prompt and len(user_prompt) >= 10:
    try:
        prediction_script = Path(__file__).parent / "prediction-engine.py"
        if prediction_script.exists():
            _pred_proc = subprocess.Popen(
                [sys.executable, str(prediction_script)],
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            try:
                _pred_proc.stdin.write(user_prompt.encode("utf-8"))
                _pred_proc.stdin.close()
            except Exception:
                pass
    except Exception as e:
        # Fully non-blocking: never let prediction break the gate
        log_error("prediction_error", "Prediction engine launch failed (non-blocking)", e, state=None)

# v5.5 HOT/COLD STATE SPLIT: Read hot + cold state
# Hot state: enforcement flags, current prompt (0.857ms - fast path)
# Cold state: session metadata for banner display (1.664ms - only when needed)

hot_state = get_session_state()  # Fast: 0.857ms

# For banner display, we need cold data (scout, memory_system, token_tracking, original_request)
# Only read cold if split files exist, otherwise hot_state already has everything from fallback
if STATE_COLD_FILE.exists():
    cold_state = get_cold_state()  # Slow: 1.664ms, but only session metadata
    state = {**cold_state, **hot_state}  # Hot overwrites cold on conflicts
else:
    # Fallback: hot_state already has full state from state.json
    state = hot_state

# ===== v7.1 HYBRID RECALL FLAG INITIALIZATION =====
# Ensure memory_system.use_hybrid_recall flag exists (enables hybrid-recall-v7.py)
state = ensure_hybrid_recall_flag(state)

# ===== v6.0 IDENTITY LOADING (SOUL.md / USER.md) =====
# Load identity files on session start or when checksums change
# Budget: <60ms (SOUL 30ms + USER 30ms + checksum 5ms)

is_session_start = detect_session_start(state)
identity_context = state.get("identity_context", {})

# Load SOUL.md and USER.md
soul_data = load_identity_file("SOUL.md")
user_data = load_identity_file("USER.md")

# Update state if session start or files changed
needs_cold_write = False

if is_session_start or (soul_data and should_reload_identity(state, "soul", soul_data.get("checksum"))):
    if soul_data:
        identity_context["soul"] = soul_data
        needs_cold_write = True

if is_session_start or (user_data and should_reload_identity(state, "user", user_data.get("checksum"))):
    if user_data:
        identity_context["user"] = user_data
        needs_cold_write = True

if needs_cold_write:
    state["identity_context"] = identity_context

# BULLETPROOF: Always capture the current prompt
if user_prompt:
    state["current_prompt"] = {
        "text": user_prompt,
        "captured_at": now,
        "char_count": len(user_prompt)
    }
    # Also append to history file
    append_prompt_history(user_prompt, now)
    # Update last input time for session detection
    state["last_user_input_time"] = now

# ===== v5.3 TOKEN TRACKING =====
# Extract token usage from API metadata
token_usage = extract_token_usage(input_data)

# Initialize token_tracking structure if missing
if "token_tracking" not in state:
    state["token_tracking"] = {
        "session_start": now,
        "baseline_week_tokens": 0,
        "baseline_established_at": None,
        "current_week_start": datetime.now().date().isoformat(),
        "current_week_tokens": 0,
        "weekly_budget": 1000000,
        "total_prompts": 0,
        "efficiency_score": 0,
        "goal_efficiency_improvement": 15,
        "last_weekly_report": None,
        "history": [],
        "weekly_summary": [],
        "optimizations_learned": []
    }

tt = state["token_tracking"]

# Migrate existing sessions to include weekly_budget
if "weekly_budget" not in tt:
    tt["weekly_budget"] = 1000000

# Update token metrics
tt["total_prompts"] += 1
tt["current_week_tokens"] += token_usage["total_tokens"]

# Detect optimization opportunities (v5.6)
optimization_opportunities = []
if DETECTOR_AVAILABLE and user_prompt:
    try:
        # Get context from last 3 prompts for cache detection
        context_window = tt["history"][-3:] if len(tt["history"]) >= 3 else []
        opportunities = detect_optimizations(user_prompt, context_window)
        if opportunities:
            optimization_opportunities = opportunities
    except Exception:
        # Silently skip if detector fails (hook must stay fast)
        pass

# Append to history (with 500-entry rotation like prompt history)
if user_prompt:
    tt["history"].append({
        "prompt_id": len(tt["history"]) + 1,
        "prompt_text": user_prompt[:50],  # Truncate to 50 chars
        "tokens": token_usage,
        "task_type": "substantial" if detect_substantial_task(user_prompt) else "trivial",
        "optimizations_applied": [],
        "optimizations_detected": optimization_opportunities
    })

    # Rotate: keep only last 500 entries
    if len(tt["history"]) > 500:
        tt["history"] = tt["history"][-500:]

state["token_tracking"] = tt

# ===== v5.4 PERFORMANCE: TRIVIAL MESSAGE BYPASS =====
# Early exit for very short prompts when no substantial task active
# Saves 150ms of enforcement overhead per message (30% of all messages)
if user_prompt and len(user_prompt) < 20:
    substantial_task_active = state.get("substantial_task_active", False)

    if not substantial_task_active:
        # Quick save (skip enforcement checks)
        save_session_state(state)

        # Minimal banner for trivial messages
        print("=" * 80)
        print(f"    PROMPT CAPTURED (v5.4 FAST PATH)")
        print("=" * 80)
        print(f"    CURRENT: \"{user_prompt}\"")
        print(f"    Captured: just now | Length: {len(user_prompt)} chars")
        print()
        print(f"    TOKENS: Week={format_tokens(tt['current_week_tokens'])}")
        try:
            _cd = _compute_today_cost()
            if _cd is None or _cd.get("record_count", 0) == 0:
                _cost_line = "COST_TODAY: no data yet (cost-log empty)"
            else:
                _pfx = "~" if _cd["confidence_pct"] < 70 else ""
                _atoks = format_tokens(_cd["total_tokens"])
                _agent_parts = [f"{a} ({int(c/_cd['total_cost']*100)}%)" for a, c in _cd["top_agents"] if _cd["total_cost"] > 0]
                _agent_str = ", ".join(_agent_parts) if _agent_parts else "n/a"
                _cost_line = f"COST_TODAY: {_pfx}${_cd['total_cost']:.2f} | {_atoks} tok | top: {_agent_str} | conf: {_cd['confidence_pct']}%"
            print(f"    {_cost_line[:100]}")
        except Exception:
            pass
        # Sprint 2: Topology selection + trace_id (fast-path path)
        try:
            _fp_topology, _fp_rule = _select_topology(user_prompt)
            _fp_trace_id = _get_or_create_trace_id()
            os.environ["CLAUDE_TRACE_ID"] = _fp_trace_id
            print(f"    TOPOLOGY: {_fp_topology} (auto, rule=\"{_fp_rule}\") | TRACE: {_fp_trace_id}")
            sys.path.insert(0, str(SCRIPTS_DIR))
            from leroy_log import write_event as _ll_write
            _fp_keywords = [w for w in user_prompt.lower().split() if len(w) > 3][:5]
            _fp_packets = _estimate_packets(user_prompt)
            _fp_fork_eligible = _detect_fork_eligibility(user_prompt, _fp_topology, _fp_packets)
            _ll_write("topology_selected", {"auto": _fp_topology, "rule": _fp_rule, "prompt_keywords": _fp_keywords, "fork_eligible": _fp_fork_eligible, "packet_estimate": _fp_packets}, level="info")
            _ll_write("gate_emitted", {"trivial_or_full": "trivial", "topology": _fp_topology, "fork_eligible": _fp_fork_eligible}, level="info")
        except Exception:
            pass
        print("=" * 80)

        # Exit early - skip all enforcement logic
        sys.exit(0)

# Preserve scout and other fields
if "scout" not in state:
    state["scout"] = {
        "active": False,
        "task_id": None,
        "output_path": "session/growth-output.md",
        "spawned_at": None,
        "last_checkpoint": None,
        "patterns_detected": 0
    }

# ===== v5.0 ENFORCEMENT LOGIC =====

# Initialize enforcement flags
if "enforcement" not in state:
    state["enforcement"] = {}

enforcement = state["enforcement"]

# Early assignment so is_substantial is defined before first use at secretary spawn check
is_substantial = user_prompt and detect_substantial_task(user_prompt) if user_prompt else False

# 1. AUTO-SPAWN SCOUT DETECTION
if user_prompt and detect_substantial_task(user_prompt):
    gm = state["scout"]
    if not gm.get("active", False):
        enforcement["must_spawn_scout"] = True
        enforcement["spawn_reason"] = "Substantial task detected"
    else:
        enforcement["must_spawn_scout"] = False
else:
    enforcement["must_spawn_scout"] = False

# 1b. AUTO-SPAWN PLANNER DETECTION
if user_prompt and should_spawn_planner(user_prompt, state):
    todo = state.get("planner", {})
    if not todo.get("active", False):
        enforcement["must_spawn_planner"] = True
        # Determine spawn reason based on detection trigger
        line_items = extract_line_items(user_prompt)
        if len(line_items) >= 3:
            enforcement["planner_spawn_reason"] = f"{len(line_items)} line items detected"
        else:
            enforcement["planner_spawn_reason"] = "Todo keywords detected"
    else:
        enforcement["must_spawn_planner"] = False
else:
    enforcement["must_spawn_planner"] = False

# 1c. AUTO-SPAWN LEGAL BACKGROUND DETECTION (v4.0)
# Read legal trigger from prediction-state.json (set by prediction-engine.py)
# Spawn legal agent in background when new client signals detected
legal_trigger_detected = False
legal_client_name = None
legal_trigger_reason = None

try:
    prediction_state_file = CLAUDE_DIR / "session" / "prediction-state.json"
    if prediction_state_file.exists():
        with open(prediction_state_file, 'r', encoding='utf-8') as f:
            prediction_state = json.load(f)

        current_pred = prediction_state.get("current_prediction", {})
        legal_trigger = current_pred.get("legal_trigger", {})

        if legal_trigger.get("detected", False) and legal_trigger.get("confidence", 0) >= 0.5:
            legal_trigger_detected = True
            legal_client_name = legal_trigger.get("client_name")
            legal_trigger_reason = legal_trigger.get("reason", "Legal trigger detected")

except (json.JSONDecodeError, IOError) as e:
    log_error("legal_trigger_read", "Failed to read legal trigger from prediction state", e, state)

# Initialize legal_background state if missing
if "legal_background" not in state:
    state["legal_background"] = {
        "active": False,
        "client": None,
        "spawned_at": None,
        "folder_created": False,
        "notes_created": [],
        "status": "idle"
    }

legal_bg = state["legal_background"]

if legal_trigger_detected and not legal_bg.get("active", False):
    enforcement["must_spawn_legal_background"] = True
    enforcement["legal_spawn_client"] = legal_client_name
    enforcement["legal_spawn_reason"] = legal_trigger_reason
else:
    enforcement["must_spawn_legal_background"] = False

# 1d. AUTO-SPAWN SECRETARY BACKGROUND (v5.7)
# Secretary spawns on ALL substantial calls to track timeline events
# Non-blocking - runs silently in background
if "secretary_background" not in state:
    state["secretary_background"] = {
        "active": False,
        "spawned_at": None,
        "events_tracked": [],
        "legal_coordinated": False,
        "last_summary_at": None,
        "status": "idle"
    }

secretary_bg = state["secretary_background"]

# Spawn on substantial tasks (priority <= 1)
if is_substantial and not secretary_bg.get("active", False):
    enforcement["must_spawn_secretary_background"] = True
    enforcement["secretary_spawn_reason"] = "Timeline tracking for substantial task"
else:
    enforcement["must_spawn_secretary_background"] = False

# 2. CHECKPOINT ENFORCEMENT (15-minute rule)
# Hook tracks time since last checkpoint and sets flags
# Claude reads these flags and runs consolidation to reset timer
# After consolidation: Claude sets checkpoint_overdue = false and updates last_checkpoint
gm = state["scout"]
if gm.get("active", False):
    last_checkpoint = gm.get("last_checkpoint")
    minutes_since_checkpoint = calculate_minutes_since(last_checkpoint)

    if minutes_since_checkpoint > 15:
        enforcement["checkpoint_overdue"] = True
        enforcement["checkpoint_overdue_minutes"] = minutes_since_checkpoint
    else:
        enforcement["checkpoint_overdue"] = False
        enforcement["checkpoint_overdue_minutes"] = minutes_since_checkpoint
else:
    enforcement["checkpoint_overdue"] = False
    enforcement["checkpoint_overdue_minutes"] = 0

# 3. MEMORY CONSOLIDATION FLAG
# Set flag if:
# - Scout active AND checkpoint overdue, OR
# - substantial_task_active is true (from previous work)
if enforcement.get("checkpoint_overdue", False) or state.get("substantial_task_active", False):
    enforcement["must_consolidate_memory"] = True
else:
    enforcement["must_consolidate_memory"] = False

# 4. CONTEXT RECOVERY DETECTION
# If we detect signs of context loss (very short prompt after long session)
# This is heuristic but helps
prompt_history_count = 0
if PROMPT_HISTORY_FILE.exists():
    try:
        with open(PROMPT_HISTORY_FILE, 'r', encoding='utf-8') as f:
            prompt_history_count = sum(1 for line in f if line.strip())
    except IOError as e:
        log_error("io_error", "Failed to count prompt history", e, state)

# If many prompts in history but state seems fresh, might be recovered
if prompt_history_count > 10 and not state.get("session_id"):
    enforcement["context_recovery_suggested"] = True
else:
    enforcement["context_recovery_suggested"] = False

# 5. MEMORY RECALL ENFORCEMENT (v2.1 - Periodic Trigger)
# Trigger auto-recall on:
# 1. Session start (30+ min gap since last input), OR
# 2. Periodic refresh (2+ hours since last recall, even if actively working)
ms = state.get("memory_system", {})
last_recall = ms.get("last_recall")
minutes_since_recall = calculate_minutes_since(last_recall) if last_recall else 999999

# Session start trigger
is_session_start = detect_session_start(state)

# Periodic trigger (every 2 hours of active work)
is_periodic_refresh = minutes_since_recall >= 120  # 2 hours

# v2.2 Context shift detection via working memory
# Trigger recall when user prompt mentions a project/client NOT in recent recall context
is_context_shift = False
context_shift_entity = None
if user_prompt and not is_session_start and not is_periodic_refresh:
    # Read working memory for active projects
    working_memory = state.get("secretary_background", {})
    active_projects = set()
    for key in working_memory:
        if isinstance(working_memory[key], dict) and working_memory[key].get("tracking_active"):
            proj = working_memory[key].get("project", "")
            client = working_memory[key].get("client", "")
            if proj:
                active_projects.add(proj.lower())
            if client:
                active_projects.add(client.lower())

    # Check if prompt mentions something NOT in active context.
    # NOTE: this is a user-configurable entity map — populate it with the
    # project/client/tool keywords relevant to your org so a context switch to
    # one of them forces a fresh recall. Left with generic placeholders here.
    prompt_lower = user_prompt.lower()
    context_keywords = {
        "acme": "Acme",
        "example": "Example",
        "oauth": "OAuth",
    }
    for keyword, entity in context_keywords.items():
        if keyword in prompt_lower and keyword not in str(active_projects).lower():
            # New entity mentioned that is NOT in active tracking
            is_context_shift = True
            context_shift_entity = entity
            break

    # Also check if 15+ minutes since last recall and substantial prompt
    if not is_context_shift and minutes_since_recall >= 15 and detect_substantial_task(user_prompt):
        is_context_shift = True
        context_shift_entity = "substantial_task_mid_session"

if is_session_start or is_periodic_refresh or is_context_shift:
    enforcement["must_recall_memory"] = True
    # Priority 0 (blocking) for substantial tasks, Priority 2 (background) for trivial
    is_substantial = user_prompt and detect_substantial_task(user_prompt)
    enforcement["recall_priority"] = 0 if is_substantial else 2

    if is_session_start:
        enforcement["recall_reason"] = "Session start (30+ min since last input)"
    elif is_context_shift:
        enforcement["recall_reason"] = f"Context shift: {context_shift_entity} (working memory directed)"
        enforcement["recall_priority"] = 1  # Mid-priority for context shifts
        enforcement["recall_context_entity"] = context_shift_entity
    else:
        enforcement["recall_reason"] = f"Periodic refresh ({minutes_since_recall} min since last recall)"
else:
    enforcement["must_recall_memory"] = False

state["enforcement"] = enforcement

# ===== AUTO-SYSTEMS TRACKING (v6.0 Bulletproof Protocol) =====
# Initialize auto_systems section with health tracking
if "auto_systems" not in state:
    state["auto_systems"] = {}

auto_sys = state["auto_systems"]

# Track each system's health
if "memory_recall" not in auto_sys:
    auto_sys["memory_recall"] = {"last_run": None, "status": "never_ran"}
if "memory_consolidation" not in auto_sys:
    auto_sys["memory_consolidation"] = {"last_run": None, "status": "never_ran"}
if "email_scan" not in auto_sys:
    auto_sys["email_scan"] = {"last_run": None, "status": "never_ran"}
if "voice_capture" not in auto_sys:
    auto_sys["voice_capture"] = {"last_run": None, "status": "never_ran", "corpus_size": 0}
if "voice_analysis" not in auto_sys:
    auto_sys["voice_analysis"] = {"last_run": None, "status": "never_ran"}
if "scout" not in auto_sys:
    auto_sys["scout"] = {"last_spawn": None, "status": "never_spawned"}
if "secretary" not in auto_sys:
    auto_sys["secretary"] = {"last_spawn": None, "status": "never_spawned", "events_tracked_24h": 0}
if "position_zero_compliance" not in auto_sys:
    auto_sys["position_zero_compliance"] = {
        "total_responses": 0,
        "compliant_responses": 0,
        "compliance_rate": 0.0,
        "last_24h_compliant": 0,
        "last_24h_total": 0
    }

state["auto_systems"] = auto_sys

# ===== v5.1 AUTO-COMMAND GENERATION =====

# Build enforcement queue (commands Claude MUST execute)
enforcement_queue = []

# Determine priority based on request type (v5.2 USER-FRIENDLY UPDATE)
# Priority 2 (background) for trivial requests - don't block user
# Priority 0/1 (blocking) for substantial tasks - ensure quality
is_substantial = user_prompt and detect_substantial_task(user_prompt)
enforcement_priority = 1 if is_substantial else 2

# ============================================================================
# PHASE 3: BACKGROUND OUTPUT SURFACING
# ============================================================================
# Check if secretary/scout/growth outputs were recently updated
# If yes, trigger surface-background-findings.py to update working memory

SECRETARY_OUTPUT = SESSION_DIR / "secretary-output.md"
GROWTH_OUTPUT = SESSION_DIR / "growth-output.md"
SURFACE_SCRIPT = CLAUDE_DIR / "scripts" / "surface-background-findings.py"

def should_surface_background_findings():
    """Check if background outputs were updated recently (last 5 min)."""
    current_time = time.time()
    five_minutes_ago = current_time - 300

    # Check secretary output
    if SECRETARY_OUTPUT.exists():
        secretary_mtime = SECRETARY_OUTPUT.stat().st_mtime
        if secretary_mtime > five_minutes_ago:
            return True

    # Check growth output
    if GROWTH_OUTPUT.exists():
        growth_mtime = GROWTH_OUTPUT.stat().st_mtime
        if growth_mtime > five_minutes_ago:
            return True

    return False

# Trigger background surfacing if outputs were updated
if should_surface_background_findings() and SURFACE_SCRIPT.exists():
    try:
        result = subprocess.run(
            [sys.executable, str(SURFACE_SCRIPT)],
            capture_output=True,
            text=True,
            timeout=2  # 2 second timeout
        )

        # Update state with last surfaced timestamp
        if result.returncode == 0:
            if "auto_systems" not in state:
                state["auto_systems"] = {}
            state["auto_systems"]["background_surfacing"] = {
                "last_surfaced_at": now,
                "last_surfaced_timestamp": time.time()
            }
    except Exception:
        pass  # Silent fail - don't block on surfacing error

if enforcement.get("must_spawn_scout", False):
    enforcement_queue.append({
        "priority": enforcement_priority,
        "action": "SPAWN_SCOUT",
        "reason": enforcement.get("spawn_reason", "Required"),
        "command": "Task tool: subagent_type=scout, run_in_background=true"
    })

if enforcement.get("must_spawn_planner", False):
    enforcement_queue.append({
        "priority": enforcement_priority,
        "action": "SPAWN_PLANNER",
        "reason": enforcement.get("planner_spawn_reason", "Required"),
        "command": "Task tool: subagent_type=planner, run_in_background=true"
    })

# v1.0 FORK DISPATCH: Inject SPAWN_FORK_WORKERS when topology is fork-eligible
try:
    _fork_topology, _fork_rule = _select_topology(user_prompt)
    _fork_packet_estimate = _estimate_packets(user_prompt)
    _fork_eligible = _detect_fork_eligibility(user_prompt, _fork_topology, _fork_packet_estimate)
    if _fork_eligible and enforcement_priority <= 1:  # Only for substantial tasks (P0/P1)
        enforcement_queue.append({
            "priority": 1,
            "action": f"SPAWN_FORK_WORKERS|packet_count={_fork_packet_estimate}|topology={_fork_topology}",
            "reason": f"Topology={_fork_topology}, ~{_fork_packet_estimate} independent packets detected — auto fan-out eligible",
            "command": (
                f"Read skills/meta/fork-dispatch.md. "
                f"Spawn {_fork_packet_estimate} parallel Agent calls with subagent_type OMITTED "
                f"(fork mode — inherits full context, shared cache prefix). "
                f"run_in_background=True on each. Max 5 forks. "
                f"Hierarchy ops (commit/deploy/email) are blocked from forking."
            )
        })
        # Write fork eligibility to hot state for manifest display
        try:
            hot_state = {}
            if STATE_HOT_FILE.exists():
                with open(STATE_HOT_FILE, "r", encoding="utf-8") as fh:
                    hot_state = json.load(fh)
            hot_state["fork_eligible"] = True
            hot_state["fork_packet_count"] = _fork_packet_estimate
            hot_state["fork_topology"] = _fork_topology
            with open(STATE_HOT_FILE, "w", encoding="utf-8") as fh:
                json.dump(hot_state, fh, indent=2, default=str)
        except Exception:
            pass
except Exception:
    pass  # Never block gate on fork detection failure

# v4.0: Legal background spawn for new client preparation
if enforcement.get("must_spawn_legal_background", False):
    legal_client = enforcement.get("legal_spawn_client", "Unknown")
    legal_reason = enforcement.get("legal_spawn_reason", "Legal trigger detected")
    enforcement_queue.append({
        "priority": 2,  # Always background - non-blocking
        "action": "SPAWN_LEGAL_BACKGROUND",
        "reason": legal_reason,
        "client": legal_client,
        "command": f"""Background legal preparation for client: {legal_client}
1. Read prediction-state.json for client context
2. Read email-intelligence.md for recent emails (if available)
3. Create: Legal/Clients/{legal_client}/Legal/Initial-Assessment.md
4. Write completion report to: session/legal-output.md
5. Update state.json legal_background status"""
    })

# v5.7: Secretary background spawn for timeline tracking
if enforcement.get("must_spawn_secretary_background", False):
    secretary_reason = enforcement.get("secretary_spawn_reason", "Timeline tracking")
    enforcement_queue.append({
        "priority": 2,  # Always background - non-blocking
        "action": "SPAWN_SECRETARY_BACKGROUND",
        "reason": secretary_reason,
        "command": """Background timeline tracking:
1. Read state.json for current context and legal_background status
2. Detect trackable events (emails sent, meetings scheduled, docs signed)
3. Update memory/Projects/{Client}/index.md timelines
4. Coordinate with legal agent if legal_background.active
5. Write summary to session/secretary-output.md
6. Update state.json secretary_background status"""
    })

    # Initialize secretary state when spawning
    state["secretary_background"] = {
        "active": True,
        "spawned_at": now,
        "events_tracked": [],
        "legal_coordinated": False,
        "last_summary_at": None,
        "status": "monitoring"
    }

if enforcement.get("checkpoint_overdue", False):
    mins = enforcement.get("checkpoint_overdue_minutes", 0)
    enforcement_queue.append({
        "priority": enforcement_priority,
        "action": "CHECKPOINT_NOW",
        "reason": f"{mins} minutes overdue (max: 15)",
        "command": "1. Read session/growth-output.md\n2. Output [GROWTH] block with findings\n3. Update state.json last_checkpoint to now"
    })

if enforcement.get("must_consolidate_memory", False):
    enforcement_queue.append({
        "priority": enforcement_priority,
        "action": "CONSOLIDATE_MEMORY",
        "reason": "Checkpoint overdue or substantial task complete",
        "command": "Write findings to the memory vault:\n- Decisions/*.md for choices made\n- Patterns/*.md for repeatable patterns\n- Preferences/*.md for user preferences\n- Skills-Learned/*.md for new capabilities"
    })

# ============================================================================
# EMAIL NOTIFICATION ENFORCEMENT (v5.8)
# ============================================================================
# Check for pending email request from memory consolidation script
PENDING_EMAIL_REQUEST = CLAUDE_DIR / "session" / "pending-email-request.json"

if PENDING_EMAIL_REQUEST.exists():
    try:
        with open(PENDING_EMAIL_REQUEST, 'r', encoding='utf-8') as f:
            email_request = json.load(f)

        notes_count = email_request.get('notes_count', 0)
        recipient = email_request.get('recipient', 'you@example.com')

        # Queue email send task (Priority 2 - background, non-blocking).
        # The concrete send tool is whatever gmail/email MCP you have configured;
        # discover it at runtime via ToolSearch rather than hardcoding a tenant
        # prefix. Replace <your-gmail> with your configured MCP server name.
        enforcement_queue.append({
            "priority": 2,
            "action": "SEND_MEMORY_NOTIFICATION_EMAIL",
            "reason": f"Memory consolidation completed - {notes_count} notes written",
            "command": f"Email notification for memory consolidation:\n\n"
                       f"1. Load your configured gmail/email send tool:\n"
                       f"   ToolSearch query: \"gmail send message\" (or \"select:mcp__<your-gmail>__send_message\")\n\n"
                       f"2. Read pending email request:\n"
                       f"   Read: session/pending-email-request.json\n\n"
                       f"3. Compose branded email:\n"
                       f"   Subject: \"Memory Vault Update - {notes_count} Notes Added\"\n\n"
                       f"4. Send email via your configured tool:\n"
                       f"   <your gmail send tool>(\n"
                       f"     to: \"{recipient}\",\n"
                       f"     subject: \"Memory Vault Update - {notes_count} Notes Added\",\n"
                       f"     body: <composed message>\n"
                       f"   )\n\n"
                       f"5. Update state.json:\n"
                       f"   memory_system.last_email_sent = <timestamp>\n"
                       f"   memory_system.email_send_count += 1\n"
                       f"   memory_system.last_email_status = \"success\"\n\n"
                       f"6. Delete pending request:\n"
                       f"   Delete: session/pending-email-request.json"
        })

        # Update state to track email queue
        state["enforcement"]["email_notification_queued"] = True
        state["enforcement"]["email_notes_count"] = notes_count

    except (json.JSONDecodeError, IOError) as e:
        log_error("email_queue_read", "Failed to read pending email request", e, state)

# End of v5.8 email enforcement addition

# ============================================================================
# SYSTEMIC ERROR PATTERN DETECTION (v5.9 — error-remediator.py integration)
# ============================================================================
# Reads error-log.jsonl entries from error-remediator.py (entries without
# "component": "gate-enforcer"). If same pattern appears 3+ times in 24h,
# surfaces as Priority 1 enforcement item for permanent fix.

def check_systemic_bash_errors():
    """Check error-log.jsonl for recurring error patterns from error-remediator."""
    error_log = CLAUDE_DIR / "session" / "error-log.jsonl"
    if not error_log.exists():
        return []
    cutoff = time.time() - (24 * 3600)
    pattern_counts = {}
    try:
        with open(error_log, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    # Only count entries from error-remediator (not gate-enforcer's own errors)
                    if entry.get("component") == "gate-enforcer":
                        continue
                    ts_str = entry.get("ts") or entry.get("timestamp") or ""
                    if ts_str:
                        try:
                            ts = _parse_iso_utc(ts_str).timestamp()
                            if ts < cutoff:
                                continue
                        except Exception:
                            continue
                    pattern = entry.get("pattern", "UnknownError")
                    if pattern not in ("None", "null", ""):
                        pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1
                except Exception:
                    continue
    except Exception:
        return []
    return [(p, c) for p, c in pattern_counts.items() if c >= 3]

systemic_errors = check_systemic_bash_errors()
for pattern, count in systemic_errors:
    enforcement_queue.append({
        "priority": 1,
        "action": "FIX_SYSTEMIC_ERROR",
        "reason": f"Error pattern '{pattern}' occurred {count}x in 24h — needs permanent fix",
        "command": f"Diagnose root cause of repeated '{pattern}' errors. Apply permanent fix (e.g., add to requirements.txt, fix path, add retry logic). See: error-remediation.md"
    })

if enforcement.get("context_recovery_suggested", False):
    # ===== HOOK-LEVEL CONTEXT RECOVERY (v8.0) =====
    # Inject state summary directly — do NOT delegate to Claude.
    try:
        recovery_lines = ["[CONTEXT RECOVERY — hook-injected]"]
        # Pull key fields from already-loaded state
        session_id = state.get("session_id", "unknown")
        last_project = state.get("current_project", "unknown")
        last_client = state.get("prediction", {}).get("client", "unknown")
        last_action = state.get("last_action", "unknown")
        next_action = state.get("next_action", "unknown")
        recovery_lines.append(f"Session: {session_id} | Project: {last_project} | Client: {last_client}")
        recovery_lines.append(f"Last action: {last_action} | Next: {next_action}")
        # Check context-anchor.md
        anchor_file = CLAUDE_DIR / "session" / "context-anchor.md"
        if anchor_file.exists():
            anchor_text = anchor_file.read_text(encoding="utf-8", errors="replace")[:400]
            recovery_lines.append(f"Context anchor:\n{anchor_text}")
        print("\n" + "\n".join(recovery_lines))
        # Mark as done — skip enforcement_queue entry
        enforcement["context_recovery_suggested"] = False
    except Exception:
        # Fallback: keep in enforcement_queue
        enforcement_queue.append({
            "priority": 2,
            "action": "RECOVER_CONTEXT",
            "reason": "Possible compaction detected (hook injection failed)",
            "command": "1. Read session/state.json\n2. Read session/prompt-history.jsonl (last 10 entries)\n3. Read session/context-anchor.md if exists"
        })

def _extract_recall_query(text, max_len=120):
    """Extract a safe, semantic keyword string from raw prompt text.

    Strips XML/task-notification blocks, task-id/tool-use-id noise, and
    truncates to max_len so enforcement.todo never embeds executable-looking
    instructions or multi-line content.
    """
    import re as _re
    # Remove XML tags and their content for known system blocks
    cleaned = _re.sub(r"<task-notification[\s\S]*?</task-notification>", "", text)
    cleaned = _re.sub(r"<[^>]+>", " ", cleaned)          # strip remaining tags
    cleaned = _re.sub(r"\s+", " ", cleaned).strip()       # collapse whitespace
    # If nothing left (pure XML input), return a safe fallback
    if not cleaned or len(cleaned) < 5:
        return "session context"
    return cleaned[:max_len]

if enforcement.get("must_recall_memory", False):
    recall_priority = enforcement.get("recall_priority", 2)
    recall_reason = enforcement.get("recall_reason", "Required")

    # Check if hybrid recall script exists and is enabled
    hybrid_script = SCRIPTS_DIR / "hybrid-recall-v7.py"
    # Note: state variable is already loaded at the top of the script
    memory_system = state.get("memory_system", {})
    use_hybrid = memory_system.get("use_hybrid_recall", True)
    testing_mode = memory_system.get("hybrid_recall_testing", False)
    confidence = memory_system.get("hybrid_recall_confidence", 1.0)
    rollout_phase = memory_system.get("rollout_phase", "pre-rollout")

    # ===== HOOK-LEVEL RECALL ENFORCEMENT (v8.1 — WARM SIDECAR FIRST) =====
    # Try the warm in-memory RAG sidecar first (<100ms when up). Fall back to the
    # cold hybrid-recall-v7.py subprocess (646-2947ms) ONLY if the sidecar is down.
    # A down sidecar returns connection-refused immediately, so it costs ~0ms — NOT
    # the timeout. Results are injected into hook stdout → become system-reminder.
    hook_recall_succeeded = False
    current_prompt = state.get("current_prompt", {}).get("text", user_prompt or "")
    _RECALL_SCORE_FLOOR = 0.35  # top hit below this is LABELED low-confidence (never suppressed)

    # --- Warm path: query the RAG sidecar over HTTP (graceful-degrade if absent) ---
    if current_prompt:
        try:
            import urllib.request as _ureq
            _qd = json.dumps({"q": current_prompt[:500], "top_k": 12}).encode("utf-8")
            _rq = _ureq.Request(
                "http://127.0.0.1:7742/query",
                data=_qd,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with _ureq.urlopen(_rq, timeout=1.5) as _rp:
                _rb = json.loads(_rp.read().decode("utf-8"))
            _results = _rb.get("results", [])
            if _results:
                _top = _results[0].get("score", 0)
                _conf = "" if _top >= _RECALL_SCORE_FLOOR else "; LOW confidence — may be off-topic"
                _lines = [
                    "\n[MEMORY] (warm sidecar)\n",
                    f"**Recalled:** {len(_results[:8])} notes (top score {_top:.2f}{_conf})\n",
                ]
                for _h in _results[:8]:
                    _lines.append(f"- [{_h.get('score', 0):.2f}] {_h.get('file', 'unknown')}\n")
                print("".join(_lines))
            else:
                print("\n[MEMORY] (warm sidecar) No notes returned for this query.")
            state.setdefault("memory_system", {})["last_recall"] = datetime.now(timezone.utc).isoformat()
            state["memory_system"]["recall_source"] = "sidecar-v8.1"
            enforcement["must_recall_memory"] = False
            hook_recall_succeeded = True
        except Exception:
            hook_recall_succeeded = False  # sidecar down/unreachable → cold fallback below

    # --- Cold fallback: ONLY if the warm sidecar didn't answer ---
    if not hook_recall_succeeded and hybrid_script.exists() and use_hybrid:
        try:
            recall_result = subprocess.run(
                [sys.executable, str(hybrid_script),
                 "--query", _extract_recall_query(current_prompt),
                 "--format", "memory-block",
                 "--update-state"],
                capture_output=True,
                text=True,
                timeout=5,
                encoding="utf-8"
            )
            if recall_result.returncode == 0 and recall_result.stdout.strip():
                print("\n" + recall_result.stdout.strip())
                state.setdefault("memory_system", {})["last_recall"] = datetime.now(timezone.utc).isoformat()
                state["memory_system"]["recall_source"] = "hook-cold-fallback"
                enforcement["must_recall_memory"] = False
                hook_recall_succeeded = True
        except Exception:
            pass  # Silent fail — enforcement_queue fallback below handles it
    hook_recall_succeeded = locals().get("hook_recall_succeeded", False)

    # WEEK 1: Parallel execution mode
    if not hook_recall_succeeded and testing_mode and hybrid_script.exists():
        current_prompt = state.get("current_prompt", {}).get("text", "")
        recall_query = _extract_recall_query(current_prompt)

        enforcement_queue.append({
            "priority": recall_priority,
            "action": "RECALL_MEMORY_PARALLEL",
            "reason": f"{recall_reason} (Week 1: Parallel Testing)",
            "command": (
                f"PARALLEL EXECUTION MODE (Week 1 Testing)\n\n"
                f"Execute BOTH recall methods and compare:\n\n"
                f"1. BASELINE (Markdown Spec):\n"
                f"   - Read session/memory-index.json\n"
                f"   - Filter notes by project + domain\n"
                f"   - Load top 12 most relevant notes\n"
                f"   - Track execution time\n"
                f"   - Output [MEMORY] block\n\n"
                f"2. HYBRID SCRIPT:\n"
                f"   - python {hybrid_script.as_posix()} --query \"{recall_query}\" --format memory-block --update-state\n"
                f"   - Track execution time\n\n"
                f"3. COMPARISON:\n"
                f"   - Compare note lists (expect >80% overlap)\n"
                f"   - Compare execution times (expect hybrid faster)\n"
                f"   - Log to parallel-execution-log.jsonl using:\n"
                f"     python scripts/parallel-execution-logger.py log \\\n"
                f"       --query \"<query>\" \\\n"
                f"       --markdown-results \"note1.md,note2.md,...\" \\\n"
                f"       --markdown-time <ms> \\\n"
                f"       --hybrid-results \"note1.md,note2.md,...\" \\\n"
                f"       --hybrid-time <ms>\n\n"
                f"4. USE MARKDOWN RESULTS:\n"
                f"   - For this session, use markdown spec results\n"
                f"   - Hybrid execution is for comparison only\n\n"
                f"Phase: {rollout_phase} | Confidence: {confidence*100:.0f}%"
            )
        })

    # WEEK 2-3: Gradual rollout with random selection
    elif not hook_recall_succeeded and hybrid_script.exists() and use_hybrid:
        import random
        random.seed()  # Use system time for randomness
        use_hybrid_this_time = random.random() < confidence

        current_prompt = state.get("current_prompt", {}).get("text", "")
        recall_query = _extract_recall_query(current_prompt)

        if use_hybrid_this_time:
            # Use hybrid recall
            enforcement_queue.append({
                "priority": recall_priority,
                "action": "RECALL_MEMORY_HYBRID",
                "reason": f"{recall_reason} (Hybrid v7.1 - {confidence*100:.0f}% rollout)",
                "command": (
                    f"Execute hybrid recall:\n\n"
                    f"python {hybrid_script.as_posix()} --query \"{recall_query}\" --format memory-block --update-state\n\n"
                    f"This will:\n"
                    f"1. Load memory index with pre-computed embeddings\n"
                    f"2. Execute 7-layer recall pipeline (<350ms)\n"
                    f"3. Return [MEMORY] block with top 5 notes\n"
                    f"4. Update state.json with recall timestamp\n\n"
                    f"Layers: Session Filter → Tag Filter → Vector Similarity → BM25 Ranking → Domain Scoring → Final Scoring → MMR Diversity\n\n"
                    f"Phase: {rollout_phase} | Confidence: {confidence*100:.0f}% (using hybrid)"
                )
            })
        else:
            # Use markdown spec
            enforcement_queue.append({
                "priority": recall_priority,
                "action": "RECALL_MEMORY",
                "reason": f"{recall_reason} (Markdown spec - {confidence*100:.0f}% rollout)",
                "command": (
                    f"1. Read session/memory-index.json\n"
                    f"2. Filter notes by project + domain\n"
                    f"3. Load top 12 most relevant notes\n"
                    f"4. Output [MEMORY] block with loaded notes\n"
                    f"5. Update state.json last_recall timestamp\n\n"
                    f"Phase: {rollout_phase} | Confidence: {confidence*100:.0f}% (using markdown spec)"
                )
            })
    elif not hook_recall_succeeded:
        # Fallback to markdown spec (hybrid disabled or script missing)
        enforcement_queue.append({
            "priority": recall_priority,
            "action": "RECALL_MEMORY",
            "reason": recall_reason,
            "command": "1. Read session/memory-index.json\n2. Filter notes by project + domain\n3. Load top 12 most relevant notes\n4. Output [MEMORY] block with loaded notes\n5. Update state.json last_recall timestamp"
        })

# ============================================================================
# SECURITY PRE-FLIGHT ENFORCEMENT (v5.9)
# Detects authorized security-testing / bug-bounty triggers and injects
# MANDATORY skill/protocol reads into enforcement.todo BEFORE any sweep runs.
# Prevents the failure mode where the agent claims to follow a protocol it
# never actually read. This is an OPTIONAL add-on: it only fires when the
# referenced skill/index files exist in your install.
# ============================================================================
BOUNTY_KEYWORDS = [
    'whitehat', 'white hat', 'bug bounty', 'bounty', 'hackerone', 'h1 ',
    'immunefi', 'intigriti', 'bugcrowd', 'sweep', 'pentest', 'ctf',
    'tryhackme', 'hackthebox', 'portswigger', 'burp lab', 'web academy',
    'assets in scope', 'impacts in scope', 'critical impact', 'bounty program',
    'start bounty', 'new bounty', 'hacker101', 'vulnerability report',
    'security finding', 'poc for', 'exploit chain'
]

_prompt_lower = user_prompt.lower() if user_prompt else ""
_is_bounty_trigger = any(kw in _prompt_lower for kw in BOUNTY_KEYWORDS)

if _is_bounty_trigger:
    enforcement_queue.insert(0, {  # Insert at front — this runs FIRST
        "priority": 0,  # Blocking — must complete before ANY sweep begins
        "action": "SECURITY_PREFLIGHT",
        "reason": "Authorized security-testing/bounty trigger detected — mandatory protocol verification required",
        "command": """MANDATORY — execute ALL steps before spawning any agent or sweep:

1. Read your security-testing protocol (REQUIRED, if present):
   Read: skills/domains/cyber/whitehat-protocol.md

2. Read your findings master index — duplicate check (REQUIRED, if present):
   Read: memory/Projects/Research/index.md

3. Confirm in DEPLOYMENT MANIFEST:
   • Both files listed under SKILLS LOADED
   • 'Dup check: CLEAR' or list any duplicate programs found
   • Coverage = EXHAUSTED (not PARTIAL) or explicitly state what was skipped and why

4. VIOLATION condition — if either Read was skipped:
   • Do NOT deliver the brief as complete
   • Flag: 'PRE-FLIGHT INCOMPLETE — [file] not read'
   • Do NOT agree with a protocol quote without having read the source

5. After sweep completes, deliver FINAL brief — no 'next steps' lists.
   If verification requires on-chain/live data, PULL IT before briefing.
   CAPTCHA is the only valid pause point."""
    })

    # Track that pre-flight was queued for this session
    if "bounty_preflight" not in state:
        state["bounty_preflight"] = {}
    state["bounty_preflight"]["triggered_at"] = now
    state["bounty_preflight"]["prompt_snippet"] = (user_prompt or "")[:80]

# ===== v8.0 EOD HEARTBEAT CHECK (hook-level — no delegation to Claude) =====
# Runs daily at 4PM local time Mon-Fri. Hook checks heartbeat file and flags
# state so a scheduled review can be created. The hook does the check so it
# can't be skipped.
try:
    from datetime import date as _date
    import platform as _platform
    _heartbeat_file = CLAUDE_DIR / "session" / "eod-review-heartbeat.txt"
    _today_str = _date.today().isoformat()
    _is_weekday = _date.today().weekday() < 5  # Mon=0 ... Fri=4
    _current_hour_utc = datetime.now(timezone.utc).hour
    # Only relevant Mon-Fri; check once per day (write today's date as guard)
    _heartbeat_stale = True
    if _heartbeat_file.exists():
        _hb_content = _heartbeat_file.read_text(encoding="utf-8").strip()
        _heartbeat_stale = (_hb_content != _today_str)
    if _is_weekday and _heartbeat_stale:
        # Write today's date to prevent re-triggering
        _heartbeat_file.write_text(_today_str, encoding="utf-8")
        # Flag in state so Claude knows the review cron must be created
        # (a hook can't create a scheduled task itself).
        state["eod_review"] = {
            "cron_needed": True,
            "scheduled_date": _today_str,
            "flagged_at": datetime.now(timezone.utc).isoformat()
        }
        print(f"\n[EOD REVIEW] Heartbeat updated for {_today_str}. EOD cron flag set in state — Claude will create cron on next response.")
except Exception:
    pass  # Silent fail — non-critical

# ===== v8.1 CONSOLIDATE_MEMORY — fire-and-forget (never block the gate) =====
# Consolidation is a WRITE; the model does not read its output this turn. Was a
# blocking subprocess.run(timeout=10) that could freeze the gate up to 10s when
# overdue. Now launched detached so it runs in the background.
try:
    _consolidate_script = SCRIPTS_DIR / "consolidate_memory.py"
    _must_consolidate = enforcement.get("must_consolidate_memory", False)
    if _must_consolidate and _consolidate_script.exists():
        subprocess.Popen(
            [sys.executable, str(_consolidate_script)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            start_new_session=True
        )
        enforcement["must_consolidate_memory"] = False  # now running detached; don't re-queue
except Exception:
    pass  # Silent fail — enforcement_queue fallback handles it

# ===== v6.0 OFFICE STATUS BLOCK for enforcement.todo (Enhancement 3) =====
# Build office status snapshot to prepend to EVERY enforcement.todo
try:
    _rag_icon = "✅" if state.get("rag_sidecar", {}).get("status") == "online" else "❌"
    _rag_idx = state.get("rag_sidecar", {}).get("indexed", 0)
    _rag_line = f"RAG: {_rag_icon} {'online (' + str(_rag_idx) + ' indexed)' if _rag_icon == '✅' else 'offline'}"
    _compliance = state.get("coo_compliance", {})
    _compliance_rate = _compliance.get("rate_pct", 100.0)
    _compliance_total = _compliance.get("total", 1)
    _ledger = state.get("agent_ledger", {})
    _scout_ran = "✅" if _ledger.get("scout", {}).get("ran") else "—"
    _sec_ran = "✅" if _ledger.get("secretary", {}).get("ran") else "—"
    _office_status_block = (
        f"## OFFICE STATUS\n"
        f"Coordinator: ✅ Active | Gate compliance: {_compliance_rate}% ({_compliance_total} total)\n"
        f"{_rag_line}\n"
        f"Agents last session — Scout: {_scout_ran} | Secretary: {_sec_ran}\n"
        f"\n---\n\n"
    )
except Exception as _oe:
    _office_status_block = f"## OFFICE STATUS\nStatus check failed: {_oe}\n\n---\n\n"

# === CONTEXT BRIDGE INJECT v1.0 ===
# If a hot-button result bridge file exists and is still fresh (<30 min),
# inject it into the enforcement queue for pickup by the next session.
try:
    _bridge_file = CLAUDE_DIR / "channels" / "telegram" / "context-bridge.json"
    if _bridge_file.exists():
        _bridge = json.loads(_bridge_file.read_text(encoding="utf-8"))
        _bridge_expires = datetime.fromisoformat(
            _bridge["expires_at"].replace("Z", "+00:00")
        )
        _bridge_now = datetime.now(timezone.utc)
        if _bridge_expires > _bridge_now:
            _bridge_topic = _bridge.get("topic", "previous session")
            _bridge_written = datetime.fromisoformat(
                _bridge["written_at"].replace("Z", "+00:00")
            )
            _bridge_elapsed = int((_bridge_now - _bridge_written).total_seconds() / 60)
            _bridge_remaining = int((_bridge_expires - _bridge_now).total_seconds() / 60)
            _bridge_content = _bridge.get("content", "")[:2000]
            enforcement_queue.append({
                "priority": 2,
                "action": "INJECT_CONTEXT",
                "reason": (
                    f"Context bridge active — {_bridge_topic} "
                    f"({_bridge_elapsed} min ago, expires in {_bridge_remaining} min)"
                ),
                "command": (
                    f"Incorporate this context from a previous session before responding.\n"
                    f"Topic: {_bridge_topic} | Captured: {_bridge_elapsed} min ago\n\n"
                    f"--- BEGIN PREVIOUS CONTEXT ---\n{_bridge_content}\n--- END PREVIOUS CONTEXT ---\n\n"
                    f"Use this context if it is relevant to the user's current question. "
                    f"If unrelated, note briefly 'Prior context available on {_bridge_topic}' and proceed."
                ),
            })
except Exception:
    pass  # Never block gate-enforcer on bridge read failure

# Write enforcement queue to file — ALWAYS write (office status is always present)
ENFORCEMENT_TODO_FILE = CLAUDE_DIR / "session" / "enforcement.todo"
if enforcement_queue:
    try:
        ENFORCEMENT_TODO_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(ENFORCEMENT_TODO_FILE, 'w', encoding='utf-8') as f:
            f.write("# MANDATORY ENFORCEMENT QUEUE\n")
            f.write("# Claude MUST complete these actions BEFORE processing user request\n")
            f.write(f"# Generated: {now}\n\n")
            f.write(_office_status_block)

            for i, task in enumerate(enforcement_queue, 1):
                f.write(f"## {i}. {task['action']} (Priority: {task['priority']})\n")
                f.write(f"**Reason:** {task['reason']}\n\n")
                f.write(f"**Commands:**\n{task['command']}\n\n")
                f.write("---\n\n")
    except IOError as e:
        log_error("io_error", "Failed to write enforcement.todo", e, state)
else:
    # No action queue — still write office status so the user sees system health every session
    try:
        ENFORCEMENT_TODO_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(ENFORCEMENT_TODO_FILE, 'w', encoding='utf-8') as f:
            f.write("# ENFORCEMENT STATUS\n")
            f.write(f"# Generated: {now}\n\n")
            f.write(_office_status_block)
            f.write("## All systems nominal — no required actions.\n")
    except IOError as e:
        log_error("io_error", "Failed to write enforcement.todo (status-only)", e, state)

# Write cold state if identity context changed (v6.0)
if needs_cold_write and state.get("identity_context"):
    cold_state = get_cold_state() if STATE_COLD_FILE.exists() else {}
    cold_state["identity_context"] = state["identity_context"]
    cold_state["session_id"] = state.get("session_id")
    cold_state["session_window"] = state.get("session_window")
    write_state_cold(cold_state)

# Force recall on new conversation (v4.0)
# Detect new conversation turn after long gap
last_input_time = state.get("last_user_input_time")
current_time = datetime.now(timezone.utc).isoformat()

if last_input_time:
    try:
        last_dt = _parse_iso_utc(last_input_time)
        if last_dt.tzinfo is None:
            last_dt = last_dt.replace(tzinfo=timezone.utc)
        current_dt = datetime.now(timezone.utc)
        gap_minutes = (current_dt - last_dt).total_seconds() / 60

        # If 30+ min gap and last_recall is stale
        last_recall = state.get("memory_system", {}).get("last_recall")
        recall_stale = True

        if last_recall:
            recall_dt = _parse_iso_utc(last_recall)
            recall_age_minutes = (current_dt - recall_dt).total_seconds() / 60
            recall_stale = recall_age_minutes > 30

        if gap_minutes >= 30 and recall_stale:
            # New conversation - force recall
            state["enforcement"]["must_recall_memory"] = True
            state["enforcement"]["recall_reason"] = f"New conversation after {gap_minutes:.0f}min gap"

            # Priority based on prompt type
            prompt_text = state.get("current_prompt", {}).get("text", "")
            is_substantial = len(prompt_text) > 50 or any(word in prompt_text.lower() for word in
                ["implement", "build", "create", "refactor", "fix", "analyze", "design"])

            state["enforcement"]["recall_priority"] = 0 if is_substantial else 2

            # Add to enforcement queue
            enforcement_queue.append({
                "action": "RECALL_MEMORY",
                "priority": state["enforcement"]["recall_priority"],
                "reason": state["enforcement"]["recall_reason"],
                "command": "Execute memory-recall.md skill with current prompt context"
            })
    except (ValueError, AttributeError):
        # Invalid timestamp format - skip recall check
        pass

# Track queue status
state["enforcement_queue_active"] = len(enforcement_queue) > 0
state["enforcement_queue_count"] = len(enforcement_queue)

# ===== v6.0 GATE COMPLIANCE TRACKING (Enhancement 2) =====
# Every gate-enforcer run = one gate generated. Track rate.
try:
    compliance = state.get("coo_compliance", {"total": 0, "gate_generated": 0})
    compliance["total"] = compliance.get("total", 0) + 1
    compliance["gate_generated"] = compliance.get("gate_generated", 0) + 1
    compliance["last_gate"] = now
    compliance["rate_pct"] = round(
        (compliance["gate_generated"] / max(compliance["total"], 1)) * 100, 1
    )
    state["coo_compliance"] = compliance
except Exception as _e:
    log_error("coo_compliance", "Failed to update gate compliance tracking", _e, state)

# ===== v6.0 RAG SIDECAR HEALTH CHECK (Enhancement 9) =====
# Check if the optional vault RAG sidecar is running at localhost:7742.
# Graceful-degrade: if the sidecar isn't running, status is simply "offline".
try:
    import urllib.request
    _rag_url = "http://127.0.0.1:7742/status"
    _req = urllib.request.Request(_rag_url, method="GET")
    with urllib.request.urlopen(_req, timeout=0.5) as _resp:
        _body = json.loads(_resp.read().decode("utf-8"))
        _rag_status = "online"
        _rag_indexed = _body.get("indexed", 0)
except Exception:
    _rag_status = "offline"
    _rag_indexed = 0

state["rag_sidecar"] = {
    "status": _rag_status,
    "indexed": _rag_indexed,
    "checked_at": now
}

# ===== v6.0 SEMANTIC PRE-FETCH → recall-queue.md (Enhancement 10) =====
# When sidecar is online, query it with the current prompt and write top-12 to recall-queue.md
if _rag_status == "online" and user_prompt:
    try:
        import urllib.request
        _query_data = json.dumps({"q": user_prompt[:500], "top_k": 12}).encode("utf-8")
        _qreq = urllib.request.Request(
            "http://127.0.0.1:7742/query",
            data=_query_data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(_qreq, timeout=2.0) as _qresp:
            _qbody = json.loads(_qresp.read().decode("utf-8"))
            _results = _qbody.get("results", [])
            _recall_lines = [
                f"# Semantic Recall Queue\n",
                f"_Generated: {now}_\n",
                f"_Query: {user_prompt[:80]}..._\n\n"
            ]
            for _r in _results:
                _score = _r.get("score", 0)
                _file = _r.get("file", "unknown")
                _content = _r.get("content", "")[:300]
                _recall_lines.append(f"## [{_score:.2f}] {_file}\n{_content}...\n\n")
            RECALL_QUEUE = CLAUDE_DIR / "session" / "recall-queue.md"
            RECALL_QUEUE.write_text("".join(_recall_lines), encoding="utf-8")
    except Exception:
        pass  # keyword fallback still works; sidecar may have gone offline

# ===== v6.0 AGENT INVOCATION LEDGER (Enhancement 4) =====
# Detect which background agents actually ran last session by checking file mtimes
try:
    _session_start_ts = state.get("session_start")
    if _session_start_ts:
        _session_start_dt = _parse_iso_utc(_session_start_ts)
    else:
        _session_start_dt = datetime.now(timezone.utc) - __import__("datetime").timedelta(hours=1)

    def _agent_ran(file_rel: str) -> dict:
        """Check if agent output file was written this session."""
        _fp = CLAUDE_DIR / file_rel
        if not _fp.exists():
            return {"ran": False, "reason": "no output file"}
        _mtime = datetime.fromtimestamp(_fp.stat().st_mtime, tz=timezone.utc)
        _ran = _mtime > _session_start_dt
        return {"ran": _ran, "output_written": _mtime.isoformat() if _ran else None}

    state["agent_ledger"] = {
        "session_id": state.get("session_id", "unknown"),
        "scout": _agent_ran("session/growth-output.md"),
        "secretary": _agent_ran("session/secretary-output.md"),
        "context_anchor": _agent_ran("session/context-anchor.md"),
        "guardian": {"ran": False, "reason": "no commit this session"},
        "checked_at": now,
    }
except Exception as _e:
    log_error("agent_ledger", "Failed to build agent invocation ledger", _e, state)

# Save updated state
save_session_state(state)

# Build display sections
gm = state.get("scout", {})
gm_active = gm.get("active", False)
gm_task_id = gm.get("task_id", "none")
gm_patterns = gm.get("patterns_detected", 0)
gm_checkpoint = format_time_ago(gm.get("last_checkpoint"))

# Memory system display (v3.0 - with vault metrics)
memory = state.get("memory_system", {})
memory_status = memory.get("status", "INACTIVE")
last_consolidation = format_time_ago(memory.get("last_consolidation"))
last_recall = format_time_ago(memory.get("last_recall"))

# Calculate "X loaded / Y total" metric
notes_loaded = memory.get("notes_loaded", 0)
try:
    # Load shard to count total (faster than full index)
    project = state.get("original_request", {}).get("project", "meta")
    shard_path = os.path.join(SESSION_DIR, "shards", f"{project}-shard.json")
    with open(shard_path, 'r', encoding='utf-8') as f:
        shard_data = json.load(f)
    total_notes = len(shard_data.get("notes", []))
except:
    # Fallback: Use last known count from state
    total_notes = memory.get("total_vault_notes", 0)

notes_display = f"{notes_loaded} loaded / {total_notes} total"

# Token tracking display (v5.3)
tt = state.get("token_tracking", {})
current_week = tt.get("current_week_tokens", 0)
efficiency = tt.get("efficiency_score", 0)
baseline = tt.get("baseline_week_tokens", 0)
tokens_display = f"Week={format_tokens(current_week)}"
if efficiency > 0:
    tokens_display += f" | Efficiency={efficiency:.1f}%"
if baseline > 0:
    tokens_display += f" | Baseline={format_tokens(baseline)}"

# Optimization opportunities display (v5.6)
optimizations_display = ""
if optimization_opportunities:
    opp_count = len(optimization_opportunities)
    top_opp = optimization_opportunities[0]  # Show top opportunity
    potential = int(top_opp['potential_savings'] * 100)
    optimizations_display = f"\n    OPTIMIZE: {opp_count} opportunity detected | Top: {top_opp['type']} (~{potential}% savings)"

# v3.0 Client Context Prediction Display (Predictive Client Context)
# v4.0 Legal Trigger Display
client_display = ""
legal_display = ""
try:
    prediction_state_file = CLAUDE_DIR / "session" / "prediction-state.json"
    if prediction_state_file.exists():
        prediction_state = json.loads(prediction_state_file.read_text(encoding='utf-8'))
        current_pred = prediction_state.get("current_prediction", {})

        # Check for client notes (from entity extraction)
        client_notes = current_pred.get("client_notes", [])
        entities = current_pred.get("entities", {})
        entity_confidence = entities.get("confidence", 0) if entities else 0
        whitelist_matches = entities.get("whitelist_matches", []) if entities else []

        if client_notes:
            # We have client context!
            client_name = whitelist_matches[0] if whitelist_matches else "detected"
            client_display = f"\n    CLIENT: {client_name} ({entity_confidence:.0%} confidence) | {len(client_notes)} notes pre-loaded"
        elif whitelist_matches and entity_confidence >= 0.3:
            # Client detected but not yet matched to notes
            client_name = whitelist_matches[0]
            client_display = f"\n    CLIENT: {client_name} ({entity_confidence:.0%} confidence) | ready for aggregation"

        # v4.0: Legal trigger display
        legal_trigger = current_pred.get("legal_trigger", {})
        if legal_trigger.get("detected", False):
            legal_conf = legal_trigger.get("confidence", 0)
            legal_type = legal_trigger.get("trigger_type", "unknown")
            legal_client = legal_trigger.get("client_name", "unknown")
            legal_display = f"\n    LEGAL: {legal_type} trigger ({legal_conf:.0%}) | client: {legal_client}"
except Exception:
    pass  # Silent fail - client display is informational only

# v5.7: Secretary status display
secretary_display = ""
secretary_bg = state.get("secretary_background", {})
if secretary_bg.get("active", False):
    events_count = len(secretary_bg.get("events_tracked", []))
    legal_coord = "yes" if secretary_bg.get("legal_coordinated", False) else "no"
    secretary_display = f"\n    SECRETARY: monitoring | events: {events_count} | legal-coord: {legal_coord}"

# v5.8: Skill surface display — contextual skill suggestions based on predicted domain
skills_display = ""
try:
    skill_sugg_file = CLAUDE_DIR / "session" / "skill-suggestions.json"
    if skill_sugg_file.exists():
        with open(skill_sugg_file, 'r', encoding='utf-8') as _sf:
            _sugg_data = json.load(_sf)
        _candidates = _sugg_data.get("current_suggestions", [])
        if _candidates:
            _domain = _candidates[0].get("domain", "")
            _labels = [s["label"] for s in _candidates[:2]]
            _top_trigger = _candidates[0].get("trigger_phrase", "")
            # Suppress if user already typed the top trigger phrase
            _prompt_lower = user_prompt.lower() if user_prompt else ""
            if _top_trigger and _top_trigger.lower() not in _prompt_lower:
                skills_display = f"\n    SKILLS: [{_domain}] {' | '.join(_labels)}  (say: \"{_top_trigger}\")"
except Exception:
    pass  # Silent fail — suggestions are informational only

# v5.8: Adoption detection — did user type a previously-suggested trigger phrase?
try:
    _hit_scores_file = CLAUDE_DIR / "session" / "skill-hit-scores.json"
    _sugg_check_file = CLAUDE_DIR / "session" / "skill-suggestions.json"
    if user_prompt and _sugg_check_file.exists():
        _prompt_lower_check = user_prompt.lower()
        with open(_sugg_check_file, 'r', encoding='utf-8') as _sc:
            _sugg_check = json.load(_sc)

        # Load hit scores (cross-session)
        _hit_scores = {}
        if _hit_scores_file.exists():
            try:
                with open(_hit_scores_file, 'r', encoding='utf-8') as _hf:
                    _hit_scores = json.load(_hf).get("scores", {})
            except (json.JSONDecodeError, IOError):
                _hit_scores = {}

        _adopted_any = False
        _today_entries = _sugg_check.get("suggested_today", [])
        for _entry in _today_entries:
            if not _entry.get("adopted", False):
                _tp = _entry.get("trigger_phrase", "").lower()
                if _tp and _tp in _prompt_lower_check:
                    _entry["adopted"] = True
                    _entry["adopted_at"] = datetime.now().isoformat()
                    _adopted_any = True
                    # Update hit scores
                    _sk = _entry.get("skill", "")
                    if _sk not in _hit_scores:
                        _hit_scores[_sk] = {"suggestion_count": 0, "adoption_count": 0,
                                            "adoption_rate": 0.0, "last_adopted": None,
                                            "last_suggested": None, "quick_trigger_promoted": False}
                    _hit_scores[_sk]["adoption_count"] += 1
                    _hit_scores[_sk]["last_adopted"] = datetime.now().isoformat()
                    _sc_val = _hit_scores[_sk]["suggestion_count"]
                    _ac_val = _hit_scores[_sk]["adoption_count"]
                    _hit_scores[_sk]["adoption_rate"] = round(_ac_val / max(_sc_val, 1), 3)

        if _adopted_any:
            # Write back updated suggestions
            _sugg_check["stats"]["total_adopted"] = sum(
                1 for e in _today_entries if e.get("adopted", False)
            )
            _sugg_check["suggested_today"] = _today_entries
            with open(_sugg_check_file, 'w', encoding='utf-8') as _sw:
                json.dump(_sugg_check, _sw, indent=2, ensure_ascii=False)
            # Write hit scores
            _hs_output = {"version": "1.0", "last_updated": datetime.now().isoformat(), "scores": _hit_scores}
            _temp_hs = _hit_scores_file.with_suffix('.tmp')
            with open(_temp_hs, 'w', encoding='utf-8') as _hw:
                json.dump(_hs_output, _hw, indent=2, ensure_ascii=False)
            _temp_hs.replace(_hit_scores_file)
        else:
            # Update suggestion_count even when not adopted
            if _today_entries and _hit_scores_file.exists():
                for _entry in _today_entries:
                    _sk = _entry.get("skill", "")
                    if _sk and _sk in _hit_scores:
                        _hit_scores[_sk]["last_suggested"] = _entry.get("suggested_at")
except Exception:
    pass  # Non-blocking

# Current prompt display
current = state.get("current_prompt", {})
prompt_display = truncate_prompt(current.get("text", "[NOT CAPTURED]"))
prompt_time = format_time_ago(current.get("captured_at"))

# Original request (for substantial tasks - kept separate)
original = state.get("original_request", {})
original_goal = original.get("interpreted_as", "")
original_project = original.get("project", "")

# Build banner with v5.0 ENFORCEMENT
if gm_active:
    gm_status = f"ACTIVE (task_id: {gm_task_id})"
else:
    gm_status = "INACTIVE"

# Build enforcement section for banner (v5.2 with priority system)
enforcement_section = ""
queue_count = state.get("enforcement_queue_count", 0)

if queue_count > 0:
    # Determine highest priority in queue
    max_priority = min([task["priority"] for task in enforcement_queue])

    if max_priority <= 1:
        # Priority 0 or 1: BLOCKING (substantial tasks)
        enforcement_section = "\n" + "="*80 + "\n"
        enforcement_section += "    [!!] ENFORCEMENT QUEUE ACTIVE - MUST PROCESS BEFORE USER REQUEST [!!]\n"
        enforcement_section += "="*80 + "\n"
        enforcement_section += f"    [--] {queue_count} MANDATORY ACTION(S) in session/enforcement.todo\n"
        enforcement_section += "="*80 + "\n"
        enforcement_section += "    [!!] READ session/enforcement.todo IMMEDIATELY\n"
        enforcement_section += "    [!!] COMPLETE ALL ACTIONS in order\n"
        enforcement_section += "    [!!] DELETE enforcement.todo when finished\n"
        enforcement_section += "    [!!] THEN (and only then) process user's request\n"
        enforcement_section += "="*80
    else:
        # Priority 2: BACKGROUND (trivial requests - user-friendly)
        enforcement_section = "\n" + "="*80 + "\n"
        enforcement_section += "    [--] ENFORCEMENT QUEUE ACTIVE (Background Processing)\n"
        enforcement_section += "="*80 + "\n"
        enforcement_section += f"    {queue_count} action(s) in session/enforcement.todo (Priority 2)\n"
        enforcement_section += "    [OK] ANSWER USER REQUEST FIRST\n"
        enforcement_section += "    [OK] Process enforcement actions AFTER response (non-blocking)\n"
        enforcement_section += "="*80

# ============================================================================
# WORKING MEMORY INJECTION (Phase 2 - v1.0)
# ============================================================================
# Load working memory index and inject into context
# Target: <50ms load time
working_memory_content = ""
working_memory_status = "NOT_LOADED"
working_memory_load_time = 0

WORKING_MEMORY_INDEX = CLAUDE_DIR / "session" / "working-memory" / "index.md"

if WORKING_MEMORY_INDEX.exists():
    try:
        wm_start = time.time()
        with open(WORKING_MEMORY_INDEX, 'r', encoding='utf-8') as f:
            working_memory_content = f.read()
        wm_end = time.time()
        working_memory_load_time = int((wm_end - wm_start) * 1000)
        working_memory_status = f"LOADED ({working_memory_load_time}ms)"
    except IOError as e:
        log_error("io_error", "Failed to load working memory index", e, state)
        working_memory_status = "ERROR"
else:
    working_memory_status = "NOT_FOUND (Phase 2 pending)"

# Optional office/persona enforcement (runs every prompt when the add-on is
# installed). This is a business-specific layer NOT shipped with LeRoy Core;
# the gate degrades gracefully when the module is absent.
office_banner = ""
if OFFICE_ENFORCEMENT_AVAILABLE:
    try:
        office_result = enforce_office_heartbeat()
        office_banner = get_office_gate_block()
    except Exception as e:
        office_banner = f"[Office enforcement error: {str(e)}]"
else:
    office_banner = ""  # add-on not installed — nothing to show

# Cost attribution line (W0.6 — additive, never blocks gate)
try:
    _cd = _compute_today_cost()
    if _cd is None or _cd.get("record_count", 0) == 0:
        cost_today_display = "COST_TODAY: no data yet (cost-log empty)"
    else:
        _pfx = "~" if _cd["confidence_pct"] < 70 else ""
        _atoks = format_tokens(_cd["total_tokens"])
        _agent_parts = [
            f"{a} ({int(c/_cd['total_cost']*100)}%)"
            for a, c in _cd["top_agents"]
            if _cd["total_cost"] > 0
        ]
        _agent_str = ", ".join(_agent_parts) if _agent_parts else "n/a"
        cost_today_display = (
            f"COST_TODAY: {_pfx}${_cd['total_cost']:.2f} | {_atoks} tok"
            f" | top: {_agent_str} | conf: {_cd['confidence_pct']}%"
        )
    cost_today_display = cost_today_display[:100]
except Exception:
    cost_today_display = "COST_TODAY: error reading cost-log"

# Sprint 2: Topology selection + trace_id (W2.3 / W2.4 — additive, never blocks gate)
topology_display = ""
try:
    _topology, _topology_rule = _select_topology(user_prompt)
    _trace_id = _get_or_create_trace_id()
    os.environ["CLAUDE_TRACE_ID"] = _trace_id
    topology_display = f"TOPOLOGY: {_topology} (auto, rule=\"{_topology_rule}\") | TRACE: {_trace_id}"
    # Emit telemetry to the local event log (optional; graceful-degrade if absent)
    try:
        sys.path.insert(0, str(SCRIPTS_DIR))
        from leroy_log import write_event as _ll_write
        _kws = [w for w in (user_prompt or "").lower().split() if len(w) > 3][:5]
        _full_packets = _estimate_packets(user_prompt)
        _full_fork_eligible = _detect_fork_eligibility(user_prompt, _topology, _full_packets)
        _ll_write("topology_selected", {"auto": _topology, "rule": _topology_rule, "prompt_keywords": _kws, "fork_eligible": _full_fork_eligible, "packet_estimate": _full_packets}, level="info")
        _ll_write("gate_emitted", {"trivial_or_full": "full", "topology": _topology, "fork_eligible": _full_fork_eligible}, level="info")
    except Exception:
        pass
except Exception:
    topology_display = "TOPOLOGY: hybrid (auto, rule=\"fallback\")"

# Main banner
gate_reminder = f"""
{office_banner}

================================================================================
    PROMPT CAPTURED (v5.8 SKILL SURFACE + v5.7 SECRETARY + v6.0 CLIENT + v5.6 OPT + v4.0 LEGAL)
================================================================================
    CURRENT: "{prompt_display}"
    Captured: {prompt_time} | Length: {current.get('char_count', 0)} chars

    GROWTH: {gm_status} | Patterns: {gm_patterns} | Checkpoint: {gm_checkpoint}
    MEMORY: {memory_status} | {notes_display} | Recall: {last_recall} | Consolidate: {last_consolidation}
    WORKING_MEMORY: {working_memory_status}
    TOKENS: {tokens_display}{optimizations_display}{client_display}{legal_display}{secretary_display}{skills_display}
    {cost_today_display}
    {topology_display}
{"    TASK CONTEXT: " + original_goal + " | " + original_project if original_goal else ""}
================================================================================
    [GATE] Output gate BEFORE any tool use (MANDATORY)
    [RECOVER] After compaction: READ session/state.json + session/prompt-history.jsonl
    [MEMORY] Auto-recall on session start (30+ min) - client notes pre-loaded when detected
    [LEGAL] Auto-spawn legal agent when contract/new client signals detected
    [SECRETARY] Auto-spawn on substantial tasks for timeline tracking
================================================================================
{enforcement_section}
"""

print(gate_reminder)

# Inject working memory content (Phase 2 - v1.0)
if working_memory_content:
    print("\n" + "=" * 80)
    print("    WORKING MEMORY - SESSION ACTIVE INTELLIGENCE (v1.0)")
    print("=" * 80)
    print(working_memory_content)
    print("=" * 80)

# ===== v6.0 TOKEN BURN ALERT (Enhancement 13) =====
# Send autonomous email alert when session burns 75K+ tokens
try:
    _tt = state.get("token_tracking", {})
    _week_tokens = _tt.get("current_week_tokens", 0)
    _alert_threshold = 75000
    _alert_sent_key = f"token_alert_sent_{_week_tokens // _alert_threshold}"
    # DEDUP (wake-storm fix): the in-memory state[_alert_sent_key] below never
    # persists because state is saved earlier in the hook (~line 2238), so the
    # guard re-fired send-email.py on EVERY prompt once over threshold. Back it
    # with a per-bucket, per-day sentinel file so the alert still fires once per
    # 75K bucket but can never repeat every prompt.
    _token_sentinel = SESSION_DIR / f".token-burn-alert-{_week_tokens // _alert_threshold}-{now[:10]}"
    if (
        _week_tokens >= _alert_threshold
        and not state.get(_alert_sent_key)
        and not _token_sentinel.exists()
    ):
        _send_email_script = SCRIPTS_DIR / "send-email.py"
        if _send_email_script.exists():
            _current_task = state.get("current_task", "unknown task")
            subprocess.Popen(
                [
                    sys.executable, str(_send_email_script),
                    "--subject", f"⚠️ Token Alert: {_week_tokens:,} tokens this week",
                    "--body", (
                        f"<p>Weekly token burn has reached <strong>{_week_tokens:,}</strong> tokens.</p>"
                        f"<p>Current task: {_current_task}</p>"
                        f"<p>Review session efficiency if this is unexpectedly high.</p>"
                    )
                ],
                start_new_session=True
            )
            state[_alert_sent_key] = now
            # Drop the sentinel only after a send is launched, so the alert
            # still fires once but is deduped across subsequent prompts.
            try:
                _token_sentinel.write_text(now, encoding="utf-8")
            except Exception:
                pass
except Exception:
    pass  # Non-blocking, never interrupt the session

# ===== v6.0 TASK COMPLETION NOTIFICATION (Enhancement 14) =====
# Detect completion signals and fire notification email
try:
    _completion_signals = ["done", "committed", "pushed", "deployed", "complete", "finished", "merged"]
    _substantial_was_active = state.get("substantial_task_active", False)
    _prompt_lower = user_prompt.lower() if user_prompt else ""
    _is_completion = any(sig in _prompt_lower for sig in _completion_signals)

    if _substantial_was_active and _is_completion:
        # DEDUP (wake-storm fix): previously this had NO guard, so it re-fired
        # send-email.py on EVERY prompt that mentioned a completion word while a
        # task stayed active — fanning out into a send storm. Cap to AT MOST ONCE
        # per day via a sentinel file. The alert still fires (once); it just can
        # never repeat every prompt.
        _completion_sentinel = SESSION_DIR / f".task-complete-alert-sent-{now[:10]}"
        if not _completion_sentinel.exists():
            _send_email_script = SCRIPTS_DIR / "send-email.py"
            if _send_email_script.exists():
                _task_summary = state.get("current_task", "substantial task")
                _tokens_used = state.get("token_tracking", {}).get("current_week_tokens", 0)
                subprocess.Popen(
                    [
                        sys.executable, str(_send_email_script),
                        "--subject", f"✅ Task Complete: {_task_summary[:60]}",
                        "--body", (
                            f"<h2>Task Completed</h2>"
                            f"<p><strong>Task:</strong> {_task_summary}</p>"
                            f"<p><strong>Token cost (week):</strong> {_tokens_used:,}</p>"
                            f"<p>Check session/context-anchor.md for next actions.</p>"
                        )
                    ],
                    start_new_session=True
                )
                # Drop the sentinel only after a send is launched, so the alert
                # still fires once but is deduped across subsequent prompts.
                try:
                    _completion_sentinel.write_text(now, encoding="utf-8")
                except Exception:
                    pass
except Exception:
    pass  # Non-blocking

# ===== v6.0 CONTEXT ANCHOR AUTO-WRITE (Enhancement 11) =====
# Fire update-context-anchor.py non-blocking after every gate
try:
    _anchor_script = SCRIPTS_DIR / "update-context-anchor.py"
    if _anchor_script.exists() and user_prompt:
        _current_task = state.get("current_task", "")
        _phase = "Implementation" if state.get("substantial_task_active") else "Planning"
        subprocess.Popen(
            [
                sys.executable, str(_anchor_script),
                "--prompt", user_prompt[:400],
                "--phase", _phase,
                "--next-action", "Check session/recall-queue.md for pre-fetched context",
            ],
            start_new_session=True
        )
except Exception:
    pass  # Non-blocking, never interrupt

sys.exit(0)
