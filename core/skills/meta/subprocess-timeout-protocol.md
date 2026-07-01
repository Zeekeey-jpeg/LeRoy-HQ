---
name: subprocess-timeout-protocol
type: autonomous
agent: builder
trigger: event-driven
user-invocable: false
disable-model-invocation: true
tags: [meta]
version: "1.0"
extracted_from: tools/telegram-bot.py (6 subprocess call sites)
---

# Subprocess Timeout Protocol

## Purpose

Standard protocol for all subprocess calls in the your org codebase. Enforces consistent timeout tiers, error surfacing, Windows-safe encoding, and structured return values. Agent enforces this whenever new subprocess calls are written.

## Firing Mechanism

Fire when:
- Builder writes a new `subprocess.run()` or `subprocess.Popen()` call
- Existing subprocess call lacks timeout or error handling
- A script is hanging and the cause is an unguarded subprocess

## Timeout Tiers

| Operation Type | Timeout | Rationale |
|----------------|---------|-----------|
| Quick check (process list, PID lookup) | 8–10s | Should be instant; hung = something wrong |
| API call / status fetch | 15–20s | Network latency + response |
| Git operations | 30–60s | Push/pull on slow connection |
| Claude CLI `-p` (simple prompt) | 120s | Short question, non-agentic |
| Claude CLI `-p` (complex / multi-agent) | 1800s | Full agentic run with subagents |
| Dream agent script | 180s | Capped scan window |

## Canonical Patterns

### Pattern A — Short sync call (subprocess.run)

Use for operations expected to finish in <60s:

```python
def run_quick(cmd: list, timeout: int = 20, label: str = "") -> str:
    """Standard short subprocess — returns stdout or error string."""
    try:
        r = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            shell=False,          # NEVER shell=True — injection risk
            timeout=timeout,
        )
        if r.returncode != 0:
            log(f"[subprocess] {label} exit {r.returncode}: {r.stderr[:200]}")
            return f"Error (code {r.returncode}): {r.stderr[:200]}"
        return r.stdout.strip() or "(empty)"
    except subprocess.TimeoutExpired:
        return f"Timed out after {timeout}s."
    except Exception as e:
        return f"Error: {e}"
```

### Pattern B — Long async call (Popen + poll loop)

Use for operations that take >60s or need progress signals. See `daemon-task-dispatcher.md → run_with_progress()`.

```python
def run_long(cmd: list, timeout: int = 1800, label: str = "") -> str:
    """Long subprocess with polling. Call from a daemon thread."""
    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        shell=False,
    )
    proc.stdin.close()
    elapsed = 0

    while proc.poll() is None:
        time.sleep(20)
        elapsed += 20
        if elapsed >= timeout:
            proc.kill()
            log(f"[subprocess] {label} killed after {timeout}s")
            return f"Timed out after {timeout}s."

    stdout = proc.stdout.read().strip()
    stderr = proc.stderr.read().strip()

    if proc.returncode != 0:
        log(f"[subprocess] {label} exit {proc.returncode}: {stderr[:200]}")
        return f"Error (code {proc.returncode}): {stderr[:200]}"

    return stdout or "(empty)"
```

### Pattern C — Detached process (fire-and-forget)

Use for launching background processes that must survive the parent (trading bot, Telegram bot restart):

```python
def launch_detached(cmd: list) -> None:
    """Spawn a process that outlives the current script."""
    subprocess.Popen(
        cmd,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.DETACHED_PROCESS,   # Windows only
    )
```

## Windows-Specific Rules

| Rule | Why |
|------|-----|
| `shell=False` always | Prevents command injection via shell metacharacters |
| `encoding="utf-8"` always | Windows default (cp1252) breaks Unicode in output |
| `capture_output=True` on subprocess.run | Equivalent to `stdout=PIPE, stderr=PIPE` |
| Avoid `2>&1` in cmd args | In PowerShell, redirecting native stderr wraps in ErrorRecord |
| Use `creationflags=DETACHED_PROCESS` for background | On Windows, not `&` or `nohup` |

## Error Handling Contract

Every subprocess call MUST handle these three cases:

```python
try:
    r = subprocess.run(cmd, ..., timeout=T)
except subprocess.TimeoutExpired:
    return f"Timed out after {T}s."    # ← always inform user
except Exception as e:
    return f"Error: {e}"               # ← always catch generic errors
# After run:
if r.returncode != 0:
    log(...)
    return f"Error (code {r.returncode}): ..."
```

Never silently swallow a non-zero returncode.

## Anti-Patterns (Never Do)

```python
# ❌ No timeout — can hang forever
subprocess.run(["git", "push"])

# ❌ shell=True — injection risk
subprocess.run(f"Start-Process '{user_path}'", shell=True)

# ❌ No error check — silently fails
r = subprocess.run(cmd, capture_output=True)
return r.stdout.strip()  # ignores r.returncode

# ❌ subprocess.run for long tasks — blocks the caller thread
r = subprocess.run(["claude", "-p", prompt], timeout=1800)  # blocks 30 min
```

## Enforcement Checklist

When reviewing new subprocess calls:

- [ ] `timeout=` set to appropriate tier (see table above)
- [ ] `TimeoutExpired` caught and user-informed
- [ ] Generic `Exception` caught
- [ ] `returncode != 0` checked and logged
- [ ] `shell=False` (no string commands)
- [ ] `encoding="utf-8"` on text mode
- [ ] Long calls (>60s) use Popen + poll, not subprocess.run

## Files Using This Pattern

- `tools/telegram-bot.py` — 6 call sites: `action_status` (20s), `action_heartbeat` (10s), `action_morning_brief` (15s), `action_backup` (30–60s), `action_kill_trading` (10s), `run_claude_with_progress` (1800s)
- `memory/Projects/StockTrading/BtcTrader/src/check_positions.py` — position check
- Any future scripts added to `tools/` or `scripts/`

---
*Subprocess Timeout Protocol v1.0 | Extracted 2026-05-09 | Autonomous enforcement*
