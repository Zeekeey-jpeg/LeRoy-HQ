#!/usr/bin/env python3
"""
monitor-daemon.py -- the unified Monitor daemon for YourCo.

ONE detached loop that replaces FOUR separate watchdog scheduled tasks
(Leroy-PWA-Watchdog, HMBRagWatchdog, YourCo-ProcessGuard, YourCo-Boardroom-Watchdog)
AND hosts the event-driven monitors (reply-radar, health-monitor). It does NOT
reimplement any restart logic -- it invokes the existing, battle-tested .ps1
watchdog scripts as repair actions, just on ONE schedule with one log.

Design principle (per Brian 2026-06-14): prefer event-driven MONITORS over
clocks or manual triggers. Process supervisors run at a cadence; signal
monitors fire on a SIGNAL (a restart happened, mail arrived) with a debounce
and a slow fallback -- not a rigid daily clock.

Reliability rules learned on first boot (2026-06-14):
  - Heartbeat is written at the START of every tick, so a slow signal action
    never makes the daemon look dead.
  - Signal actions (claude -p) are spawned DETACHED (fire-and-forget) so a long
    or hung run can never stall the supervisor loop.
  - On first ever start, signal monitors are stamped 'just ran' so they fire
    after their interval instead of all firing at once on startup (no burst).

Config: session/automation-registry.json  -> "monitor_daemon" block.
Kill switch: New-Item session/monitor.disabled  (loop idles, stays alive).
Stop:        kill the PID in session/monitor-daemon.pid

Usage:
    python tools/monitor-daemon.py              # run forever (detached via pythonw in prod)
    python tools/monitor-daemon.py --once        # single tick, then exit
    python tools/monitor-daemon.py --dry-run     # decide + log, never execute (safe test)
    python tools/monitor-daemon.py --once --dry-run
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

CLAUDE_ROOT = Path(r"~/.claude")
REGISTRY = CLAUDE_ROOT / "session" / "automation-registry.json"

# ─── Native (zero-PowerShell) backend repair, 2026-07-02 ──────────────────────
# Added after PowerShell process launches were found hung machine-wide (first
# evidence: this daemon's own log, 02:35:11 that morning, a watchdog-sidecar.ps1
# call that never returned). The daemon itself died 6 minutes later because
# _run()'s old PIPE-based capture blocks forever when a hung grandchild keeps
# the pipe open after its direct child is killed on timeout -- see _run() below.
# These constants back the leroy-pwa supervisor's native backend repair path,
# which never shells to PowerShell so it keeps working even while the .ps1
# watchdog can't run at all.
BACKEND_DIR = CLAUDE_ROOT / "memory" / "Projects" / "leroy-pwa-app" / "backend"
BACKEND_PORT = 8848
BACKEND_LOG = CLAUDE_ROOT / "session" / "leroy-backend.log"

CIRCUIT_BREAKER_THRESHOLD = 3
CIRCUIT_BREAKER_COOLDOWN_SECONDS = 1800

# Wake-storm guards (2026-06-26): on wake-from-sleep every monitor looks overdue
# and ~60 claude -p fire at once. Two caps keep monitoring functional but burst-proof:
MAX_SPAWNS_PER_TICK = 2        # at most N detached spawns per tick; rest defer to next tick
SPAWN_STAGGER_SECONDS = 1.5    # small sleep between spawns within a tick (no simultaneous burst)
WAKE_GAP_TICK_MULTIPLIER = 3   # a gap > 3x the tick interval (or the floor) counts as a wake
WAKE_GAP_FLOOR_SECONDS = 1800  # ...or > 30 min -- whichever is larger -- triggers coalesce


def now() -> float:
    return time.time()


def iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Daemon:
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.cfg = self._load_cfg()
        d = self.cfg
        self.tick = int(d.get("tick_seconds", 60))
        self.kill_switch = CLAUDE_ROOT / d.get("kill_switch", "session/monitor.disabled")
        self.heartbeat = CLAUDE_ROOT / d.get("heartbeat_file", "session/monitor-daemon-heartbeat.txt")
        self.log_file = CLAUDE_ROOT / d.get("log_file", "session/monitor-daemon.log")
        self.state_file = CLAUDE_ROOT / d.get("state_file", "session/monitor-daemon-state.json")
        self.pid_file = CLAUDE_ROOT / "session" / "monitor-daemon.pid"
        self.supervisors = d.get("process_supervisors", [])
        self.signals = d.get("signal_monitors", [])
        self.state = self._load_state()
        self._spawns_this_tick = 0  # per-tick spawn budget (reset each tick)
        self._seed_signal_baseline()
        self._coalesce_on_wake()  # 2026-06-26 wake-storm: catch a sleep gap at startup

    # -- config / state ----------------------------------------------------------
    def _load_cfg(self) -> dict:
        reg = json.loads(REGISTRY.read_text(encoding="utf-8"))
        cfg = reg.get("monitor_daemon")
        if not cfg:
            raise SystemExit("monitor_daemon block missing from automation-registry.json")
        return cfg

    def _load_state(self) -> dict:
        if self.state_file.exists():
            try:
                return json.loads(self.state_file.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {"last_run": {}, "signals": {}}

    def _save_state(self) -> None:
        if self.dry_run:
            return
        try:
            self.state_file.write_text(json.dumps(self.state, indent=1), encoding="utf-8")
        except Exception:
            pass

    def _seed_signal_baseline(self) -> None:
        """First ever start: stamp each signal monitor as just-run so it fires
        after its interval, not instantly. Prevents a claude-call burst at boot."""
        changed = False
        for sig in self.signals:
            if sig["name"] not in self.state.get("last_run", {}):
                self.state.setdefault("last_run", {})[sig["name"]] = now()
                changed = True
        if changed:
            self._save_state()

    def _coalesce_on_wake(self) -> None:
        """Wake-gap coalesce (2026-06-26 wake-storm fix): if the wall clock jumped
        far beyond a normal tick (the machine slept), every monitor looks overdue
        and would fire at once (~60 claude -p). Re-stamp every monitor's last_run
        = now so a SINGLE catch-up pass runs over the next ticks instead of a burst.
        Same idea as _seed_signal_baseline, but applied on EVERY wake, not just
        first-ever start. Runs at startup and at the top of each tick."""
        last_tick = self.state.get("last_tick", 0)
        if not last_tick:
            return  # first-ever start: handled by _seed_signal_baseline
        gap = now() - last_tick
        threshold = max(self.tick * WAKE_GAP_TICK_MULTIPLIER, WAKE_GAP_FLOOR_SECONDS)
        if gap <= threshold:
            return
        stamp = now()
        names = [s["name"] for s in self.supervisors] + [s["name"] for s in self.signals]
        lr = self.state.setdefault("last_run", {})
        for nm in names:
            lr[nm] = stamp
        self.log(f"WAKE GAP {int(gap)}s > {int(threshold)}s - coalesced: re-stamped "
                 f"{len(names)} monitors (single catch-up pass, no wake-storm)")
        self._save_state()

    def log(self, msg: str) -> None:
        line = f"[{iso()}] {'DRY ' if self.dry_run else ''}{msg}"
        print(line)
        if self.dry_run:
            return
        try:
            with self.log_file.open("a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:
            pass

    # -- helpers -----------------------------------------------------------------
    def _due(self, name: str, interval: float) -> bool:
        last = self.state["last_run"].get(name, 0)
        return (now() - last) >= interval

    def _mark(self, name: str) -> None:
        self.state["last_run"][name] = now()

    def _run(self, cmd: str, label: str) -> int:
        """Run a shell command and WAIT (used for fast process-supervisor scripts).

        2026-07-02 fix: the old subprocess.run(capture_output=True, timeout=120)
        used PIPE for stdout/stderr. When the invoked .ps1 hangs (PowerShell host
        wedged), subprocess.run kills the DIRECT child (cmd.exe) on timeout, but
        an orphaned powershell.exe grandchild can keep the pipe's write end open
        -- communicate() then blocks FOREVER waiting for EOF that never comes.
        That is exactly how this daemon died on 2026-06-27 (log stops mid-tick,
        heartbeat stops, process never exits, never gets relaunched). Temp files
        have no such handle-inheritance deadlock: Popen redirects the OS-level
        file descriptor directly, so a hung grandchild holding it open doesn't
        block OUR read (we just seek/read after the process is confirmed dead).
        On an actual timeout, taskkill's /T flag kills the WHOLE process tree
        (cmd.exe + every descendant, including the hung powershell.exe) instead
        of leaving an orphan to leak into the zombie pile."""
        if self.dry_run:
            self.log(f"WOULD RUN [{label}]: {cmd}")
            return 0
        with tempfile.TemporaryFile(mode="w+b") as out_f:
            try:
                proc = subprocess.Popen(cmd, shell=True, stdout=out_f,
                                        stderr=subprocess.STDOUT, cwd=str(CLAUDE_ROOT))
            except Exception as exc:
                self.log(f"ERROR [{label}]: {exc}")
                self._trip_breaker(label)
                return 1
            try:
                rc = proc.wait(timeout=120)
            except subprocess.TimeoutExpired:
                self._killtree(proc.pid)
                try:
                    proc.wait(timeout=10)
                except Exception:
                    pass
                self.log(f"TIMEOUT [{label}] - killed process tree (pid {proc.pid})")
                self._trip_breaker(label)
                return 1
            out_f.seek(0)
            out = out_f.read().decode("utf-8", errors="replace")
            self.log(f"ran [{label}] rc={rc} {out.strip()[:120]}")
            if rc == 0:
                self._reset_breaker(label)
            else:
                self._trip_breaker(label)
            return rc

    def _killtree(self, pid: int) -> bool:
        """Kill a process and its entire descendant tree. Native taskkill, never
        PowerShell -- this must work even while the PowerShell host is wedged."""
        try:
            r = subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"],
                               capture_output=True, text=True, timeout=15)
            return r.returncode == 0
        except Exception as exc:
            self.log(f"_killtree pid={pid} error: {exc}")
            return False

    # -- circuit breaker (2026-07-02) --------------------------------------------
    # A supervisor action that fails or times out 3 ticks in a row gets skipped
    # for 30 minutes instead of retried every cadence. Without this, a broken
    # .ps1 (or a still-wedged PowerShell host) crashloops every 120-900s forever,
    # which is exactly how ~985 zombie powershell.exe processes accumulated over
    # the 5 days this daemon was dead -- each failed tick's hung grandchild never
    # got reaped. The breaker doesn't fix a broken action, it just stops it from
    # leaking resources while broken; it self-clears after cooldown to retry.
    def _trip_breaker(self, label: str) -> None:
        cb = self.state.setdefault("circuit_breakers", {})
        entry = cb.setdefault(label, {"fails": 0, "until": 0})
        entry["fails"] = entry.get("fails", 0) + 1
        if entry["fails"] >= CIRCUIT_BREAKER_THRESHOLD:
            entry["until"] = now() + CIRCUIT_BREAKER_COOLDOWN_SECONDS
            self.log(f"[{label}] circuit breaker TRIPPED after {entry['fails']} consecutive "
                     f"failures - skipping for {CIRCUIT_BREAKER_COOLDOWN_SECONDS}s")
        self._save_state()

    def _reset_breaker(self, label: str) -> None:
        cb = self.state.get("circuit_breakers", {})
        if label in cb and (cb[label].get("fails") or cb[label].get("until")):
            cb[label] = {"fails": 0, "until": 0}
            self._save_state()

    def _breaker_open(self, label: str) -> bool:
        """True if this label's circuit breaker is currently tripped (skip it)."""
        entry = self.state.get("circuit_breakers", {}).get(label)
        if not entry:
            return False
        return now() < entry.get("until", 0)

    def _run_detached(self, cmd: str, label: str) -> None:
        """Spawn a command fire-and-forget (used for signal actions / claude -p),
        so a long or hung run can never stall the supervisor loop."""
        if self.dry_run:
            self.log(f"WOULD SPAWN (detached) [{label}]: {cmd}")
            return
        try:
            subprocess.Popen(cmd, shell=True, cwd=str(CLAUDE_ROOT),
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.log(f"spawned (detached) [{label}]")
        except Exception as exc:
            self.log(f"ERROR spawn [{label}]: {exc}")

    def _spawn_capped(self, cmd: str, label: str) -> bool:
        """Detached spawn that respects MAX_SPAWNS_PER_TICK with a stagger between
        spawns (2026-06-26 wake-storm fix). Returns True if it spawned (caller marks
        run); False if the per-tick budget is spent -- caller must NOT mark run so the
        monitor is retried next tick. Nothing is skipped permanently, just spread out."""
        if self._spawns_this_tick >= MAX_SPAWNS_PER_TICK:
            self.log(f"[{label}] per-tick spawn cap ({MAX_SPAWNS_PER_TICK}) reached - deferring to next tick")
            return False
        if self._spawns_this_tick > 0 and not self.dry_run:
            time.sleep(SPAWN_STAGGER_SECONDS)  # stagger so spawns never fire simultaneously
        self._run_detached(cmd, label)
        self._spawns_this_tick += 1
        return True

    def _proc_alive(self, substr: str) -> bool:
        """True if a process whose command line contains `substr` is running.

        2026-07-02 fix: this used to shell to `powershell -Command Get-CimInstance
        Win32_Process`, with a fail-safe True on any error/timeout ("assume alive,
        never spawn a duplicate"). Once the PowerShell host wedged, EVERY call
        timed out and fail-safe-True fired every time -- so a genuinely-dead
        boardroom-loop.py was reported "alive" on every tick for 5+ days and
        never respawned, with no error in the log to say why. NEVER shells to
        PowerShell now: psutil first (the system Python 3.12 running this daemon
        has it), tasklist as a fallback if psutil is somehow unavailable."""
        try:
            import psutil
            for p in psutil.process_iter(["cmdline"]):
                try:
                    cmdline = " ".join(p.info.get("cmdline") or [])
                except Exception:
                    continue
                if substr in cmdline:
                    return True
            return False
        except ImportError:
            pass
        except Exception as exc:
            self.log(f"_proc_alive psutil error for {substr!r}: {exc}")
            return True  # fail-safe only for a genuine psutil runtime error
        # No psutil: tasklist /V gives image name + window title, not the full
        # command line, so this only catches substr matches against those two
        # fields -- weaker than psutil but still native (no PowerShell).
        try:
            out = subprocess.run(["tasklist", "/V", "/FO", "CSV"],
                                 capture_output=True, text=True, timeout=15)
            return substr.lower() in (out.stdout or "").lower()
        except Exception:
            return True  # last-resort fail-safe: never spawn a duplicate on error

    def _set_signal(self, name: str) -> None:
        self.state.setdefault("signals", {})[name] = now()

    def _has_pending_signal(self, triggers: list, since: float) -> bool:
        sigs = self.state.get("signals", {})
        return any(sigs.get(t, 0) > since for t in triggers)

    def _clear_signals(self, triggers: list) -> None:
        for t in triggers:
            self.state.get("signals", {}).pop(t, None)

    def _touch_heartbeat(self, status: str) -> None:
        if self.dry_run:
            return
        try:
            self.heartbeat.write_text(f"{iso()} {status}", encoding="utf-8")
        except Exception:
            pass

    # -- native (zero-PowerShell) backend repair, 2026-07-02 ---------------------
    # The leroy-pwa-watchdog.ps1 action covers frontend :5173 + backend :8848 +
    # Tailscale funnel; while the PowerShell host is wedged, none of that runs.
    # This is a native-Python fallback for JUST the backend half -- port lookup
    # via netstat, kill via taskkill, relaunch via a plain python.exe Popen -- so
    # a restart.flag or a dead backend still gets fixed with zero PowerShell.
    # Runs BEFORE the .ps1 action each leroy-pwa tick (see tick_once); the .ps1
    # still runs after for frontend/funnel and stays the primary path once
    # PowerShell recovers.
    def _find_port_owner(self, port: int) -> list[int]:
        """Native (netstat, no PowerShell) port -> listening PID lookup."""
        pids: set[int] = set()
        try:
            out = subprocess.run(["netstat", "-ano"], capture_output=True, text=True, timeout=15)
            for line in (out.stdout or "").splitlines():
                parts = line.split()
                if len(parts) >= 4 and parts[0] == "TCP" and "LISTENING" in line:
                    local = parts[1]
                    if local.endswith(f":{port}") and parts[-1].isdigit():
                        pids.add(int(parts[-1]))
        except Exception as exc:
            self.log(f"_find_port_owner({port}) error: {exc}")
        return list(pids)

    def _resolve_backend_python(self) -> str:
        """Prefer the canonical .venv; fall back to venv (no-dot) if absent.
        Mirrors leroy-pwa-watchdog.ps1's ResolveBackendPython."""
        venv_py = BACKEND_DIR / ".venv" / "Scripts" / "python.exe"
        if venv_py.exists():
            return str(venv_py)
        alt = BACKEND_DIR / "venv" / "Scripts" / "python.exe"
        return str(alt) if alt.exists() else str(venv_py)

    def _backend_healthy(self) -> bool:
        try:
            req = urllib.request.Request(f"http://127.0.0.1:{BACKEND_PORT}/health", method="GET")
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status == 200
        except Exception:
            return False

    def _native_pwa_backend_repair(self) -> None:
        """Zero-PowerShell backend repair. Triggers on an explicit restart.flag
        OR sustained health-probe failure -- NOT stale-code detection (no version
        endpoint exists to check that from outside the process, so a stale-but-
        healthy backend is caught on the NEXT restart.flag write, not here)."""
        restart_flag = BACKEND_DIR / "data" / "restart.flag"
        flagged = restart_flag.exists()
        if not flagged:
            if self._backend_healthy():
                self._health_misses = 0
                return  # nothing to do
            # 3-STRIKE RULE (2026-07-02): one missed probe is NOT death. A heavy
            # claude -p run can pin the box hard enough that a single probe times
            # out while the backend is perfectly alive — the old single-miss kill
            # murdered the backend MID-CHAT-RUN and ate the in-flight reply
            # (Brian's "sessions not landing"). Require 3 consecutive misses
            # (~3 supervisor passes) before declaring it dead.
            self._health_misses = getattr(self, "_health_misses", 0) + 1
            if self._health_misses < 3:
                self.log(f"[leroy-pwa-native] health miss {self._health_misses}/3 - tolerating (no kill)")
                return
            self._health_misses = 0

        reason = "restart.flag present" if flagged else "health probe failed"
        if self.dry_run:
            self.log(f"WOULD repair [leroy-pwa-native]: {reason}")
            return
        self.log(f"[leroy-pwa-native] backend repair triggered ({reason})")

        for pid in self._find_port_owner(BACKEND_PORT):
            ok = self._killtree(pid)
            self.log(f"[leroy-pwa-native] killed PID {pid} on :{BACKEND_PORT} - {'ok' if ok else 'FAILED'}")

        try:
            restart_flag.unlink(missing_ok=True)
        except Exception:
            pass

        py = self._resolve_backend_python()
        child_env = os.environ.copy()
        # Never inherit a stale disable -- a restart must come back auth-enforced.
        # Matches leroy-pwa-watchdog.ps1 StartBackend's belt-and-suspenders comment.
        child_env.pop("LEROY_AUTH_DISABLED", None)
        try:
            BACKEND_LOG.parent.mkdir(parents=True, exist_ok=True)
            with BACKEND_LOG.open("a", encoding="utf-8") as log_f:
                log_f.write(f"\n[{iso()}] --- relaunched by monitor-daemon (native repair: {reason}) ---\n")
                subprocess.Popen(
                    [py, "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", str(BACKEND_PORT)],
                    cwd=str(BACKEND_DIR), env=child_env,
                    stdout=log_f, stderr=log_f,
                    creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
                )
            self.log(f"[leroy-pwa-native] relaunched backend via {py}")
        except Exception as exc:
            self.log(f"[leroy-pwa-native] relaunch FAILED: {exc}")

    # -- one tick ----------------------------------------------------------------
    def tick_once(self) -> None:
        if self.kill_switch.exists():
            self._touch_heartbeat("disabled")
            self.log("kill switch present - idling")
            return

        # Liveness FIRST, before any (possibly slow) work.
        self._touch_heartbeat("ok")

        # Wake-storm guards (2026-06-26): coalesce a sleep gap, then reset the
        # per-tick spawn budget so at most MAX_SPAWNS_PER_TICK fire this tick.
        self._coalesce_on_wake()
        self._spawns_this_tick = 0

        # 1) Process supervisors (reuse existing watchdog scripts) ---------------
        for sup in self.supervisors:
            name = sup["name"]
            cadence = int(sup.get("cadence_seconds", 300))
            if not self._due(name, cadence):
                continue
            if name == "leroy-pwa":
                # Native-first backend repair (works even while PowerShell is
                # wedged). Does NOT replace the .ps1 below, which still covers
                # frontend :5173 + the Tailscale funnel. Deliberately runs
                # BEFORE the breaker check below: that breaker tracks the
                # .ps1 action's own PowerShell failures and must never block
                # this zero-PowerShell repair path (2026-07-02 fix -- the
                # first version gated this on the same breaker, so once the
                # .ps1 tripped it after 3 timeouts, restart.flag stopped
                # getting picked up too, for the full 30-minute cooldown).
                try:
                    self._native_pwa_backend_repair()
                except Exception as exc:
                    self.log(f"[leroy-pwa-native] unexpected error: {exc}")
            if self._breaker_open(name):
                self.log(f"[{name}] circuit breaker open - skipping .ps1 fallback this tick")
                self._mark(name)
                continue
            if sup.get("type") == "respawn":
                ks = sup.get("respect_kill_switch")
                if ks and (CLAUDE_ROOT / ks).exists():
                    self.log(f"[{name}] target kill-switch present - not respawning")
                    self._mark(name)
                    continue
                if self._proc_alive(sup["match_cmdline"]):
                    self._mark(name)
                    continue
                self.log(f"[{name}] DOWN - respawning")
                self._run_detached(sup["start_action"], name)
                self._set_signal("process_restart")  # feeds health-monitor
            else:
                self._run(sup["action"], name)  # proven .ps1, self-decides, fast
            self._mark(name)

        # 2) Signal monitors (event-driven, debounced, fired DETACHED) ----------
        for sig in self.signals:
            name = sig["name"]
            stype = sig.get("type", "interval")
            min_int = int(sig.get("min_interval_seconds", 14400))

            if stype == "interval":
                if self._due(name, min_int):
                    self.log(f"[{name}] interval elapsed - firing")
                    # Capped spawn: if budget spent, leave UN-marked so it retries next tick.
                    if self._spawn_capped(sig["action"], name):
                        self._mark(name)

            elif stype == "health-signal":
                fired_pending = self._has_pending_signal(
                    sig.get("triggers", []), since=self.state["last_run"].get(name, 0))
                debounce_ok = self._due(name, min_int)
                fallback = int(sig.get("fallback_interval_seconds", 86400))
                if fired_pending and debounce_ok:
                    self.log(f"[{name}] signal {sig.get('triggers')} + debounce ok - firing")
                    if self._spawn_capped(sig["action"], name):
                        self._mark(name)
                        self._clear_signals(sig.get("triggers", []))
                elif self._due(name, fallback):
                    self.log(f"[{name}] fallback interval reached - firing")
                    if self._spawn_capped(sig["action"], name):
                        self._mark(name)

        # Stamp last_tick AFTER the tick so the next tick/startup can detect a wake gap.
        self.state["last_tick"] = now()
        self._save_state()

    # -- loop --------------------------------------------------------------------
    def run_forever(self) -> None:
        if not self.dry_run:
            try:
                self.pid_file.write_text(str(os.getpid()), encoding="utf-8")
            except Exception:
                pass
        self.log(f"monitor-daemon started (pid {os.getpid()}, tick {self.tick}s, "
                 f"{len(self.supervisors)} supervisors, {len(self.signals)} signal monitors)")
        while True:
            try:
                self.tick_once()
            except Exception as exc:
                self.log(f"tick error: {exc}")
            time.sleep(self.tick)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true", help="single tick then exit")
    ap.add_argument("--dry-run", action="store_true", help="decide + log, never execute")
    args = ap.parse_args()

    d = Daemon(dry_run=args.dry_run)
    if args.once:
        d.tick_once()
    else:
        d.run_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main())
