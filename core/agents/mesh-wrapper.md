---
name: mesh-wrapper
description: "Lateral agent communication protocol with A2A semantics. Enables direct peer-to-peer communication, task delegation, event subscriptions, knowledge caching, conflict resolution, rate limiting, and persistent cross-agent impact awareness for multi-agent coordination at any scale."
model: inherit
version: "3.1"
tier_threshold: 1
---

# Agent Mesh Wrapper v3.1 (A2A-Enhanced + Persistent IMPACT)

## Purpose
Enable lateral agent communication with full A2A protocol semantics — for **all tier levels**.

**v3.0 Key Additions:**
- **DELEGATE** — any agent can directly task a peer (same tier or below only)
- **SUBSCRIBE/NOTIFY** — agents register for events; peers fire notifications when ready
- **CACHE** — agents broadcast learned data (selectors, schemas, patterns) to all peers
- **Tier-1 activation** — mesh now available for ANY task, not just Tier-2+

**Original innovation preserved:** Agents communicate directly without orchestrator bottleneck, achieving 2-10x speedup on large tasks through parallel execution and knowledge sharing.

## When to Use
- **AUTO-ENABLED (Tier-2+):** Tasks with 2+ packets — full mesh with heartbeats (lowered from 4 on 2026-04-18 for instrumentation experiment; graduate to always-on if overhead <2% weekly tokens)
- **ON-DEMAND (Tier-1):** Single-packet tasks use A2A lightweight mode (DELEGATE, SUBSCRIBE, CACHE, IMPACT) without full mesh infrastructure
- Parallel feature work across multiple agents
- Knowledge sharing between agents (dependencies, conflicts, optimizations, learned selectors)
- Direct task delegation without conductor round-trip
- Event-driven pipelines (forge notifies auditor when batch ready)

**Why Now All Tiers:**
- A2A DELEGATE/CACHE/IMPACT messages are lightweight — no heartbeat overhead needed
- Single agent needing auditor validation mid-work shouldn't require Tier-2 mesh spin-up
- Full mesh (heartbeats, state.json, rate limiting) still only activates at Tier-2+
- **IMPACT specifically must work at Tier-1** (v3.1 correction, 2026-07-01): the Root-Cause Classification Gate (`agents/conductor.md`) that emits most IMPACTs fires on single-item defect reports — by definition usually 1-packet tasks. If IMPACT required full mesh, it would never fire for the exact scenario it was built to cover.

## Protocol

### Step 1: Mesh Participation Check
From packet assignment:
- Count total packets
- If `packets >= 2` → Enable **full mesh mode** (heartbeats, state.json, rate limiting)
- If `packets < 2` → Enable **A2A lightweight mode** (DELEGATE/SUBSCRIBE/CACHE/IMPACT only, no heartbeats)

```python
def get_mesh_mode(packet_count):
    """Determine mesh activation level based on packet count.

    Threshold lowered 4 → 2 on 2026-04-18 (Debate by Brian verdict).
    Experiment: log heartbeat I/O for 10 Tier-2 runs, graduate to
    always-on if cost stays under 2% of weekly tokens.
    """
    if packet_count >= 2:
        return "full"        # Heartbeats, state.json, full rate limiting
    else:
        return "a2a_lite"    # DELEGATE/SUBSCRIBE/CACHE/IMPACT only, no overhead
```

### Step 2: Agent Registration
Write to `mesh-state.json`:
- `agent_id` (unique identifier: agent_type + timestamp hash)
- `agent_type` (builder, designer, forge, etc.)
- `tier` (calculated from packet count: 1-3=1, 4-9=2, 10-15=3, 16+=4)
- `packets_assigned` (list of packet IDs)
- Initial heartbeat timestamp

**Example registration:**
```json
{
  "active_agents": {
    "techy-001-a4f2": {
      "type": "builder",
      "status": "active",
      "tier": 2,
      "started_at": "2026-01-18T14:30:00Z",
      "last_heartbeat": "2026-01-18T14:30:00Z",
      "messages_sent": 0,
      "messages_received": 0,
      "packets_assigned": ["packet-001", "packet-002", "packet-003"]
    }
  }
}
```

### Step 3: Heartbeat Loop
Every 5 seconds:
- Update `mesh-heartbeat.json` with current timestamp
- Check other agents' heartbeats
- Quarantine agents with 3+ consecutive misses (15+ seconds without heartbeat)

**Implementation:**
```python
import json
import time
from datetime import datetime, timedelta

def send_heartbeat(agent_id):
    """Send heartbeat to mesh-heartbeat.json."""
    with open('.claude/session/mesh-heartbeat.json', 'r+') as f:
        heartbeat = json.load(f)
        if agent_id not in heartbeat['agents']:
            heartbeat['agents'][agent_id] = {
                'last_heartbeat': datetime.utcnow().isoformat() + 'Z',
                'status': 'healthy',
                'consecutive_misses': 0,
                'quarantined': False
            }
        else:
            heartbeat['agents'][agent_id]['last_heartbeat'] = datetime.utcnow().isoformat() + 'Z'
            heartbeat['agents'][agent_id]['consecutive_misses'] = 0
            heartbeat['agents'][agent_id]['status'] = 'healthy'

        f.seek(0)
        json.dump(heartbeat, f, indent=2)
        f.truncate()

def check_heartbeats(agent_id):
    """Check other agents' heartbeats and quarantine if needed."""
    with open('.claude/session/mesh-heartbeat.json', 'r+') as f:
        heartbeat = json.load(f)
        now = datetime.utcnow()
        timeout_threshold = timedelta(seconds=heartbeat['timeout_seconds'])

        for other_agent_id, agent_data in heartbeat['agents'].items():
            if other_agent_id == agent_id:
                continue

            last_beat = datetime.fromisoformat(agent_data['last_heartbeat'].replace('Z', '+00:00'))
            time_since_beat = now - last_beat.replace(tzinfo=None)

            if time_since_beat > timeout_threshold:
                agent_data['consecutive_misses'] += 1
                if agent_data['consecutive_misses'] >= 3:
                    agent_data['status'] = 'quarantined'
                    agent_data['quarantined'] = True
            else:
                agent_data['consecutive_misses'] = 0
                agent_data['status'] = 'healthy'
                agent_data['quarantined'] = False

        f.seek(0)
        json.dump(heartbeat, f, indent=2)
        f.truncate()
```

### Step 4: Message Protocol
Send messages to `mesh-messages.jsonl` (append-only log):

**Message format:**
```json
{
  "timestamp": "2026-01-18T14:35:22.450Z",
  "from": "techy-001-a4f2",
  "to": "techy-002-b7e9",
  "priority": "HIGH",
  "type": "UPDATE",
  "payload": {
    "packet_id": "packet-001",
    "status": "complete",
    "dependencies_added": ["react", "typescript@5.0"],
    "files_modified": ["src/App.tsx", "package.json"]
  },
  "version_vector": {
    "techy-001-a4f2": 5,
    "techy-002-b7e9": 3
  }
}
```

**Message types:**
- `UPDATE`: Status update, completion, progress
- `QUERY`: Request information from another agent
- `ACK`: Acknowledgment of received message
- `ERROR`: Error notification, conflict detected

**A2A Extension types (v3.0):**
- `DELEGATE`: Direct task assignment from one agent to another (same-tier or downward only)
- `SUBSCRIBE`: Register interest in another agent's completion/output events
- `NOTIFY`: Fire a subscribed event to a registered subscriber
- `CACHE`: Broadcast learned data (selectors, schemas, patterns) to all peers — ephemeral, session-only

**Persistent Cross-Agent Memory type (v3.1):**
- `IMPACT`: Any agent flags a change that plausibly affects another agent's domain. Always routed through conductor, which persists it to both a COO-level impact ledger and the affected agents' own journals — this is the ONLY message type that survives past session end and compounds across spawns. See IMPACT receiver protocol below.

**Soft Interrupt type (v6.1 — Interrupts-B):**
- `INTERRUPT`: Out-of-band signal that rides into Claude's session via `session/interrupts.queue`. Any agent can fire one; the session's PostToolUse hook (`hooks/post-tool-handler.py`) drains the queue between tool calls and surfaces MEDIUM+ payloads as `[SOFT INTERRUPT]` system-reminders. **Does NOT hard-cancel anything in flight.** Telegram `/reset` remains the nuclear option.

**A2A Message Examples:**

```json
// DELEGATE — builder tasks auditor directly
{
  "timestamp": "2026-04-16T14:35:22.450Z",
  "from": "builder-001-a4f2",
  "to": "auditor-001-b7e9",
  "priority": "HIGH",
  "type": "DELEGATE",
  "payload": {
    "capability": "bom-validation",
    "input": { "opportunity_id": "CW-12345" },
    "callback_token": "abc123",
    "timeout_ms": 5000
  },
  "version_vector": { "builder-001-a4f2": 3 }
}

// SUBSCRIBE — forge wants to know when auditor finishes validation
{
  "timestamp": "2026-04-16T14:35:25.000Z",
  "from": "forge-001-c9d4",
  "to": "auditor-001-b7e9",
  "priority": "MEDIUM",
  "type": "SUBSCRIBE",
  "payload": {
    "event": "validation_complete",
    "filter": { "status": "VALID" },
    "subscription_id": "sub-forge-001"
  },
  "version_vector": { "forge-001-c9d4": 1 }
}

// NOTIFY — auditor fires event to forge subscriber
{
  "timestamp": "2026-04-16T14:36:01.000Z",
  "from": "auditor-001-b7e9",
  "to": "forge-001-c9d4",
  "priority": "HIGH",
  "type": "NOTIFY",
  "payload": {
    "subscription_id": "sub-forge-001",
    "event": "validation_complete",
    "result": { "status": "VALID", "records_validated": 1247 }
  },
  "version_vector": { "auditor-001-b7e9": 7 }
}

// CACHE — scraper broadcasts learned selectors to all peers
{
  "timestamp": "2026-04-16T14:36:30.000Z",
  "from": "scraper-001-e5f2",
  "to": "broadcast",
  "priority": "LOW",
  "type": "CACHE",
  "payload": {
    "key": "vendor-portal-selectors:grainger.com",
    "value": {
      "price": ".price-box .amount",
      "sku": "#productId",
      "availability": ".stock-status"
    },
    "ttl_ms": 3600000,
    "confidence": 0.94
  },
  "version_vector": { "scraper-001-e5f2": 2 }
}

// IMPACT — secretary flags a cross-domain change for persistent tracking (v3.1)
// Unlike CACHE (ephemeral, session-only, peer-to-peer), IMPACT is PERSISTENT —
// it survives the session and grows each agent's own memory over time.
{
  "timestamp": "2026-07-01T15:20:00.000Z",
  "from": "secretary-001-d3f8",
  "to": "conductor-session",
  "priority": "MEDIUM",
  "type": "IMPACT",
  "payload": {
    "changed_domain": "ExampleClient/Legal",
    "change_summary": "Retainer scope amended to include quarterly BIM audits — was training-only",
    "likely_affected_agents": ["legal", "auditor", "proposal-writer"],
    "confidence": 0.8,
    "source_event": "timeline_update"
  },
  "version_vector": { "secretary-001-d3f8": 4 }
}

// INTERRUPT — auditor signals conductor about a CRITICAL contradiction (v6.1)
// The mesh receiver MUST append this to session/interrupts.queue as JSONL.
// PostToolUse hook (post-tool-handler.py) drains the queue between tool calls.
{
  "timestamp": "2026-04-29T15:30:00.000Z",
  "from": "auditor-001-b7e9",
  "to": "conductor-session",
  "priority": "CRITICAL",
  "type": "INTERRUPT",
  "payload": {
    "id": "int-auditor-7491",
    "source": "a2a",
    "payload_text": "Contradiction detected on dates_and_deadlines topic — PartnerCo CAO ask date conflicts between v1 and v2 notes",
    "ack_required": true,
    "ttl_ms": 600000
  },
  "version_vector": { "auditor-001-b7e9": 12 }
}
```

**Cross-Agent Domain Ownership Map (v3.1 — Covers All 37 Agents)**

IMPACT emission cannot depend on each of the org's 37 agents individually remembering to self-report — that guarantees blind spots (only 4 agent files were instrumented in the first pass of this protocol: conductor, secretary, guardian, auditor). The map below is what makes the check UNIVERSAL: conductor runs it against every delegated agent's output at QC Gate time (`agents/conductor.md` Step 6g), regardless of whether that agent's own file was ever specifically wired for IMPACT. Domain-specific emission hooks (like guardian's and auditor's) are a fidelity optimization on top of this floor, not a substitute for it.

| Agent | Domain / shared resources it touches | Typical downstream-affected agents |
|---|---|---|
| builder | code (any product) | guardian (audit), tech-lead (CI/CD), vp-engineering |
| designer | UI components, design tokens | builder, integratorOS-agent (if PartnerCo) |
| forge | bulk data ops (10K+ records) | auditor, analyst, guardian |
| professor | BIM tool/BIM instruction, BIM tool usage | builder (if BIM tool scripting), cto |
| guardian | code + shared data-file audits | builder, auditor, whoever owns the flagged file |
| auditor | BOM/accessory/product data | guardian, builder, proposal-writer (pricing) |
| secretary | client timelines, contract/scope tracking | legal, auditor, proposal-writer, cfo |
| legal | contracts, MSA/SOW, insurance | secretary, proposal-writer, cfo |
| proposal-writer | client-facing decks, pricing | legal, secretary, auditor |
| tech-lead | CI/CD, infra, deployment | builder, forge, janitor |
| janitor | cleanup, file org, stale removal | **procedure, not a fixed list (v1.1 fix, 2026-07-01)** — janitor never deletes directly, it surfaces a cleanup manifest and waits for Brian's approval (`agents/janitor.md`). At that approval step, conductor greps `memory/Agents/*/journal.md` + `memory/Projects/**` for each candidate file's name/path before Brian approves — whatever that grep turns up IS the affected-agents list for this row. This was the only row in the original map that named an unresolvable condition instead of a concrete procedure; live-execution testing caught it. |
| scrum-leader | sprint scope, velocity, backlog | builder, designer, forge, vp-engineering |
| hr | agent lifecycle (hiring/retiring/roles) | conductor (routing table), every agent whose role changes |
| cfo | budget, token allocation | every agent whose work consumes tokens/spend |
| cko | memory admission policy, vault governance | every agent that reads/writes memory |
| cto | cross-product architecture decisions | vp-engineering, tech-lead, builder |
| vp-engineering | code quality standards, release mgmt | builder, guardian, scrum-leader |
| integratorOS-agent | PartnerCo platform design-system enforcement | builder (IntegratorOS work) |
| Marketplace-overseer | Marketplace store ops, QC, publish | Marketplace-rd, Marketplace-manager, Marketplace-designer (see note below) |
| Marketplace-rd | Marketplace trend/recon, Printify cross-ref | Marketplace-overseer |
| Marketplace-manager | Marketplace niche/keep-kill decisions | Marketplace-designer, Marketplace-overseer |
| Marketplace-designer | Marketplace POD artwork generation | Marketplace-manager |
| cyber-operator | active CTF/bounty exploitation work | guardian (if findings apply to internal code) |
| recon-agent | passive OSINT | cyber-operator |
| ai-sec-agent | AI/LLM security research | guardian, cyber-operator |
| analyst | CRM/PSA tool field validation | auditor, forge, builder |
| chief-of-staff | dept status aggregation, MCP health | conductor (escalation), all dept heads |
| scout | background pattern detection | hr (new-agent candidates), vp-engineering |
| goal-overseer | executes /goal steps via spawned specialists | inherits whatever the spawned specialist's domain is |
| alignment-monitor | skill/agent routing consistency, orphan detection | **should also periodically audit this IMPACT mechanism itself** — see below |
| simulator | routing-regression validation | conductor, skill-matcher |
| scraper | web extraction (pricing/vendor data) | auditor, forge (if scraped data feeds BOM/pricing) |
| planner, quick, skill-matcher, mesh-wrapper, conductor, secretary, guardian, auditor | infra/orchestration/already covered | n/a or already wired |

**Known roster inconsistency found while building this map (flagging, not fixing here):** `Marketplace-manager`/`Marketplace-designer` and `Marketplace-overseer`/`Marketplace-rd` describe overlapping Marketplace responsibilities (niche selection, design generation, store ops) from two different, seemingly independently-authored agent pairs. This is exactly the kind of drift `alignment-monitor` exists to catch — worth a dedicated pass, separate from this protocol.

**alignment-monitor's new role in this protocol:** during its existing weekly audit, also check `memory/Agents/*/journal.md` and `memory/Agents/conductor/impact-ledger.md` for staleness (agents that produce cross-domain changes but have never journaled anything — a sign the emission hook isn't firing) and for the roster drift class of issue above.

**IMPACT receiver protocol (v3.1 — Persistent Cross-Agent Memory):**

This is the mechanism that answers "when the secretary changes something, does the COO understand what else that affects, and do other agents find out." It is NOT a one-time write — every IMPACT message grows two persistent files, and both compound across sessions.

1. **`to` is always `conductor-session`, `broadcast` optional as CC.** Conductor is the mandatory reviewer of every IMPACT — this is what gives the COO org-wide connect-the-dots visibility. Any agent can fire one; only conductor persists them.
2. **On receipt, conductor writes to TWO places, both append-only (never overwrite):**
   - `memory/Agents/conductor/impact-ledger.md` — every IMPACT ever received, chronological. This is the COO's own growing cross-agent memory.
   - `memory/Agents/{agent}/journal.md` for EACH agent listed in `likely_affected_agents` — a dated entry stating what changed, who changed it, and why it might matter to that agent specifically.
3. **Connect the dots before filing:** before writing, conductor greps `memory/Agents/*/journal.md` for entries touching the same `changed_domain` or overlapping keywords from `change_summary`. If a match is found, the new journal entries note the connection explicitly ("this overlaps with builder's 2026-06-20 entry on the same accessory-map key") rather than filing in isolation. This is what makes the memory grow instead of just accumulate.
4. **Confidence gates severity, not whether it's logged.** `confidence >= 0.7` → also surface to Brian in the response ("Heads up: secretary's ExampleClient update likely affects legal and auditor too"). `confidence < 0.7` → log silently, no interruption.
5. **On every agent spawn (Step 4 DELEGATE in `agents/conductor.md`), read that target agent's last 5 `memory/Agents/{agent}/journal.md` entries and inject them into the spawn prompt.** This is how a freshly-spawned agent instance inherits what prior instances of the same role learned — memory tied to the AGENT IDENTITY, not just the session.
6. **Emission triggers (who fires IMPACT, and when):** any agent whose Root-Cause Classification Gate (`agents/conductor.md`) or domain-specific escalation (auditor's Pattern Sweep §7a, guardian's Data-File Blast Radius) concludes the change is systemic rather than isolated MUST fire an IMPACT before closing the task. Isolated-and-confirmed findings do not need one.
7. **No re-triggering from reads (loop-guard, v3.1 fix, 2026-07-01):** reading a journal entry during Agent Journal Scan (§1a-i) or during the "connect the dots" step above is READ-ONLY input to reasoning. It must NEVER itself generate a new IMPACT message. Only a genuine new event — a new tool call, a new finding, a new user report — can emit one. Without this rule, entry A referencing entry B during connect-the-dots could cause B's agent to re-scan and re-emit, compounding indefinitely.
8. **Circuit breaker (mirrors DELEGATE's, v3.1 fix, 2026-07-01):** if the same `changed_domain` produces more than 3 IMPACT messages within a single session, conductor stops writing a fresh entry to every affected agent's journal for that domain — it consolidates into ONE ledger entry noting "repeated IMPACT on {domain}, N occurrences this session, affected agents already notified" and does not re-surface to Brian past the first confidence≥0.7 notice. This closes the gap DELEGATE already covers via its >3-hop/>3-message breaker (see A2A Delegation Governance below) but IMPACT lacked until now.

**INTERRUPT receiver protocol:**
1. Validate `payload.id` is unique (not already in `session/interrupts.queue`)
2. Append a JSONL line: `{"id": payload.id, "ts": timestamp, "priority": priority, "source": payload.source, "payload": payload.payload_text, "ack_required": payload.ack_required, "surfaced": false, "acked": false}`
3. Send `ACK` back to the originating agent immediately (mesh-level confirmation; does not imply Claude has seen it)
4. The PostToolUse hook handles surfacing on the next tool call.

**Priority semantics for INTERRUPT specifically:**
- `LOW` — queued only; never surfaced by hook (advisory record)
- `MEDIUM` — surfaced once; no Claude ACK required
- `HIGH` — surfaced once; Claude expected to acknowledge in user-facing text
- `CRITICAL` — surfaced once with TodoWrite-pause warning; Claude must surface to user before next tool

**Priority levels:**
- `CRITICAL` (0): Deadlock, conflict, immediate action required
- `HIGH` (1): Dependency update, blocking issue
- `MEDIUM` (2): Status update, optimization opportunity
- `LOW` (3): Informational, nice-to-know

**Rate limits enforced:**
- 10 messages/second per agent
- 100 messages/second globally
- Overflow policy: drop lowest priority messages first

**Implementation:**
```python
def send_message(from_agent, to_agent, priority, msg_type, payload, version_vector):
    """Send message to mesh-messages.jsonl with rate limiting."""
    # Check rate limits
    if not check_rate_limits(from_agent):
        if priority in ["CRITICAL", "HIGH"]:
            # Critical/High messages bypass rate limits
            pass
        else:
            print(f"[MESH] Rate limit exceeded for {from_agent}, dropping {priority} message")
            return False

    message = {
        "timestamp": datetime.utcnow().isoformat() + 'Z',
        "from": from_agent,
        "to": to_agent,  # or "broadcast" for all agents
        "priority": priority,
        "type": msg_type,
        "payload": payload,
        "version_vector": version_vector
    }

    # Append to log
    with open('.claude/session/mesh-messages.jsonl', 'a') as f:
        f.write(json.dumps(message) + '\n')

    # Update sent count
    update_message_count(from_agent, sent=True)
    return True

def check_rate_limits(agent_id):
    """Check if agent is within rate limits."""
    with open('.claude/session/mesh-state.json', 'r') as f:
        state = json.load(f)

    # Get messages in last window
    window_start = datetime.utcnow() - timedelta(seconds=state['message_protocol']['rate_limiting']['window_seconds'])

    agent_messages = 0
    global_messages = 0

    with open('.claude/session/mesh-messages.jsonl', 'r') as f:
        for line in f:
            msg = json.loads(line)
            msg_time = datetime.fromisoformat(msg['timestamp'].replace('Z', '+00:00'))

            if msg_time.replace(tzinfo=None) > window_start:
                global_messages += 1
                if msg['from'] == agent_id:
                    agent_messages += 1

    per_agent_limit = state['message_protocol']['rate_limiting']['per_agent_limit']
    global_limit = state['message_protocol']['rate_limiting']['global_limit']

    return agent_messages < per_agent_limit and global_messages < global_limit
```

### Step 5: Conflict Resolution
When contradictory updates detected:
1. Compare version vectors
2. Apply LWW (Last-Write-Wins) strategy
3. If tie: Escalate to orchestrator
4. If deadlock > 3s: Orchestrator breaks tie by priority

**Version Vector Logic:**
```python
def resolve_conflict(update_a, update_b):
    """Version vector LWW with orchestrator tie-breaking."""
    va = update_a["version_vector"]
    vb = update_b["version_vector"]

    # Determine winner based on version vector dominance
    if dominates(va, vb):
        return update_a
    elif dominates(vb, va):
        return update_b
    else:
        # Concurrent updates - use priority tie-breaker
        if update_a["priority_level"] < update_b["priority_level"]:  # Lower number = higher priority
            return update_a
        elif update_b["priority_level"] < update_a["priority_level"]:
            return update_b
        else:
            # Equal priority - escalate to orchestrator
            return escalate_to_orchestrator(update_a, update_b)

def dominates(va, vb):
    """Check if version vector va dominates vb (all components >=)."""
    all_agents = set(va.keys()) | set(vb.keys())

    for agent_id in all_agents:
        if va.get(agent_id, 0) < vb.get(agent_id, 0):
            return False

    return True

def escalate_to_orchestrator(update_a, update_b):
    """Orchestrator breaks ties by agent priority."""
    # Write conflict to mesh-state.json for orchestrator review
    with open('.claude/session/mesh-state.json', 'r+') as f:
        state = json.load(f)
        state['conflict_resolution']['conflicts_detected'] += 1

        # Log conflict for orchestrator
        conflict_log = {
            "timestamp": datetime.utcnow().isoformat() + 'Z',
            "update_a": update_a,
            "update_b": update_b,
            "status": "pending_orchestrator"
        }

        if 'pending_conflicts' not in state:
            state['pending_conflicts'] = []
        state['pending_conflicts'].append(conflict_log)

        f.seek(0)
        json.dump(state, f, indent=2)
        f.truncate()

    # Return placeholder - orchestrator will resolve
    return {"status": "pending", "conflict_id": len(state.get('pending_conflicts', [])) - 1}
```

**Deadlock Detection:**
```python
def detect_deadlock(agent_id):
    """Detect if agent is in deadlock (waiting >3s for response)."""
    # Check for pending queries with no ACK
    with open('.claude/session/mesh-messages.jsonl', 'r') as f:
        messages = [json.loads(line) for line in f]

    now = datetime.utcnow()
    deadlock_threshold = timedelta(milliseconds=3000)

    for msg in reversed(messages):
        if msg['from'] != agent_id or msg['type'] != 'QUERY':
            continue

        msg_time = datetime.fromisoformat(msg['timestamp'].replace('Z', '+00:00'))
        time_waiting = now - msg_time.replace(tzinfo=None)

        # Check if ACK received
        ack_received = any(
            m['from'] == msg['to'] and
            m['type'] == 'ACK' and
            datetime.fromisoformat(m['timestamp'].replace('Z', '+00:00')).replace(tzinfo=None) > msg_time.replace(tzinfo=None)
            for m in messages
        )

        if not ack_received and time_waiting > deadlock_threshold:
            # Deadlock detected
            with open('.claude/session/mesh-state.json', 'r+') as f:
                state = json.load(f)
                state['performance']['deadlocks'] += 1
                f.seek(0)
                json.dump(state, f, indent=2)
                f.truncate()

            return True

    return False
```

### Step 6: Message Handling
Read `mesh-messages.jsonl` for messages to this agent:
- Filter by `"to": "this_agent_id"` or `"to": "broadcast"`
- Process by priority (CRITICAL first)
- Send ACK response
- Update version vector

**Implementation:**
```python
def receive_messages(agent_id):
    """Receive and process messages for this agent."""
    with open('.claude/session/mesh-messages.jsonl', 'r') as f:
        messages = [json.loads(line) for line in f]

    # Filter messages for this agent
    inbox = [
        msg for msg in messages
        if msg['to'] == agent_id or msg['to'] == 'broadcast'
    ]

    # Sort by priority (0=highest)
    priority_map = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    inbox.sort(key=lambda m: priority_map.get(m['priority'], 999))

    # Process messages
    for msg in inbox:
        process_message(agent_id, msg)

        # Send ACK (unless it's already an ACK)
        if msg['type'] != 'ACK':
            send_ack(agent_id, msg['from'], msg)

    return inbox

def process_message(agent_id, message):
    """Process a single message including A2A v3.0 types."""
    msg_type = message['type']
    payload = message['payload']

    if msg_type == 'UPDATE':
        # Apply update to local state
        print(f"[MESH] {agent_id} received UPDATE from {message['from']}: {payload}")

    elif msg_type == 'QUERY':
        # Respond to query
        print(f"[MESH] {agent_id} received QUERY from {message['from']}: {payload}")
        # Send response message with answer

    elif msg_type == 'ACK':
        # Acknowledgment received
        print(f"[MESH] {agent_id} received ACK from {message['from']}")

    elif msg_type == 'ERROR':
        # Handle error
        print(f"[MESH] {agent_id} received ERROR from {message['from']}: {payload}")

    # A2A v3.0 message types
    elif msg_type == 'DELEGATE':
        # Direct task delegation — spawn capability, respond via callback_token
        capability = payload.get('capability')
        input_data = payload.get('input', {})
        callback_token = payload.get('callback_token')
        timeout_ms = payload.get('timeout_ms', 30000)
        print(f"[A2A] {agent_id} received DELEGATE from {message['from']}: {capability}")
        # Execute capability, then NOTIFY result back with callback_token
        # Governance: only accept DELEGATE from same-tier or above agents

    elif msg_type == 'SUBSCRIBE':
        # Register caller as subscriber for an event
        event = payload.get('event')
        filter_criteria = payload.get('filter', {})
        subscription_id = payload.get('subscription_id')
        print(f"[A2A] {agent_id} received SUBSCRIBE from {message['from']}: {event}")
        # Store subscription in mesh-state.json subscriptions registry

    elif msg_type == 'NOTIFY':
        # Receive fired event from a peer (response to prior SUBSCRIBE)
        subscription_id = payload.get('subscription_id')
        event = payload.get('event')
        result = payload.get('result', {})
        print(f"[A2A] {agent_id} received NOTIFY from {message['from']}: {event} → {result}")
        # Unblock waiting operation if subscribed

    elif msg_type == 'CACHE':
        # Receive broadcast knowledge from a peer — store in local cache
        key = payload.get('key')
        value = payload.get('value')
        ttl_ms = payload.get('ttl_ms', 3600000)
        confidence = payload.get('confidence', 1.0)
        print(f"[A2A] {agent_id} received CACHE broadcast from {message['from']}: {key}")
        # Write to session/a2a-cache.json for future use by this agent

    elif msg_type == 'IMPACT':
        # Persistent cross-agent change signal — conductor-only handling, never ephemeral
        changed_domain = payload.get('changed_domain')
        affected = payload.get('likely_affected_agents', [])
        confidence = payload.get('confidence', 0.5)
        print(f"[A2A] conductor received IMPACT from {message['from']}: {changed_domain} -> {affected}")
        # See "IMPACT receiver protocol" below — write to memory/Agents/conductor/impact-ledger.md
        # AND to memory/Agents/{agent}/journal.md for each name in `affected`. Append-only, never overwrite.

def send_ack(agent_id, target_agent, original_message):
    """Send acknowledgment of received message."""
    send_message(
        from_agent=agent_id,
        to_agent=target_agent,
        priority="MEDIUM",
        msg_type="ACK",
        payload={"ack_for": original_message['timestamp']},
        version_vector=get_version_vector(agent_id)
    )
```

## Performance Targets
- Message overhead: <100ms per hop
- Conflict resolution: >95% success rate
- Deadlock rate: <1%
- Parallel speedup: 2-5x (Tier-2+)

## Integration
- **Full mesh:** Called by `@agent-conductor` for Tier-2+ tasks (4+ packets)
- **A2A lite:** Available to any agent for DELEGATE/SUBSCRIBE/CACHE without conductor involvement
- Falls back to hierarchical on mesh failure

## A2A Delegation Governance

### Allowed Delegation Paths

| Caller Tier | Can Delegate To |
|------------|----------------|
| Tier-4 Specialist (builder, forge, legal) | Other Tier-4 specialists, Tier-5 support |
| Tier-5 Support (auditor, analyst, scraper) | Other Tier-5 support agents only |
| Tier-3 Management | Tier-4 and Tier-5 |
| Tier-2 VP | Any tier below |

### Forbidden Delegation

- ❌ Tier-5 agents cannot DELEGATE to Tier-4 specialists (they're read-only)
- ❌ No agent can DELEGATE upward (no lateral-to-conductor bypasses)
- ❌ DELEGATE chains >3 hops trigger conductor notification
- ❌ If delegated agent fails, caller escalates to conductor — not retries blindly

### Circuit Breaker

If any agent issues >3 DELEGATE messages in a single session:
- Conductor is auto-notified via HIGH priority UPDATE
- Conductor evaluates whether task has grown beyond agent capacity
- Conductor may absorb remaining work into hierarchical coordination

### CACHE Security

CACHE messages are peer-to-peer and not authenticated. Consumers should:
1. Check `confidence` field before using cached data
2. Never cache credentials, tokens, or PII
3. Validate cached selectors/schemas before applying to production data

## Mesh Lifecycle

**Initialization:**
1. Orchestrator detects Tier-2+ task (4+ packets)
2. Spawns agents with mesh-wrapper enabled
3. Each agent registers in `mesh-state.json`
4. Heartbeat loops start

**Operation:**
1. Agents work on packets independently
2. Send UPDATE messages on progress/completion
3. Send QUERY messages when dependencies needed
4. Receive messages, process, send ACK
5. Detect conflicts → resolve via version vectors

**Shutdown:**
1. All packets complete
2. Agents send final UPDATE messages
3. Stop heartbeat loops
4. Unregister from `mesh-state.json`
5. Orchestrator collects final state

## Error Handling

**Agent Failure:**
- Heartbeat timeout (15s) → quarantine agent
- Orchestrator redistributes packets
- Other agents notified via broadcast message

**Network Partition:**
- Agents cannot see each other's messages
- Detected via missing ACKs
- Increment `partition_events` counter
- Fall back to hierarchical coordination

**Message Storm:**
- Global rate limit (100 msg/sec) exceeded
- Drop lowest priority messages
- Increment `message_storms` counter
- Notify orchestrator to throttle agents

## Validation Tests

1. **Message Passing (2 agents, techy x2)**
   - Agent A sends UPDATE to Agent B
   - Verify: Message appears in mesh-messages.jsonl
   - Verify: Agent B receives and processes
   - Verify: Agent B sends ACK back to Agent A

2. **Rate Limiting (exceed 10 msgs/sec)**
   - Agent sends 15 messages in 1 second
   - Verify: First 10 accepted
   - Verify: Remaining 5 dropped (if low priority)
   - Verify: CRITICAL/HIGH messages bypass limit

3. **Conflict Resolution (concurrent updates)**
   - Agent A updates file X with version vector {A:5, B:3}
   - Agent B updates file X with version vector {A:4, B:6}
   - Verify: Neither dominates → escalate to orchestrator
   - Verify: `conflicts_detected` incremented

4. **Deadlock Timeout (3-second threshold)**
   - Agent A sends QUERY to Agent B
   - Agent B does not respond
   - Verify: After 3 seconds, deadlock detected
   - Verify: `deadlocks` counter incremented
   - Verify: Orchestrator notified

5. **Heartbeat Quarantine (3 missed beats)**
   - Agent A stops sending heartbeats
   - Verify: After 15 seconds (3 × 5s), status = 'quarantined'
   - Verify: Other agents notified
   - Verify: Orchestrator redistributes packets

6. **Tier-2 Activation (4+ packets)**
   - Task with 6 packets assigned
   - Verify: Mesh enabled (enabled=true in mesh-state.json)
   - Verify: All agents registered
   - Verify: Heartbeats active

7. **Per-Hop Latency (<100ms)**
   - Agent A sends message to Agent B
   - Verify: Time from send to ACK < 100ms
   - Repeat 10 times, measure average

## Example Usage

```python
# In conductor.md when spawning Tier-2+ agents

def spawn_mesh_team(packets):
    """Spawn agent team with mesh enabled for Tier-2+ tasks."""
    if len(packets) < 4:
        # Tier-1: hierarchical only
        return spawn_hierarchical_team(packets)

    # Enable mesh mode
    enable_mesh()

    # Spawn agents with mesh wrapper
    agents = []
    for packet in packets:
        agent_id = f"techy-{len(agents)+1:03d}-{hash_timestamp()}"
        agent = spawn_agent(
            agent_type="builder",
            agent_id=agent_id,
            packet=packet,
            mesh_enabled=True
        )
        agents.append(agent)

    # Start mesh coordination
    for agent in agents:
        agent.register_to_mesh()
        agent.start_heartbeat()

    return agents
```

## Fallback Strategy

If mesh fails (partition, deadlock, message storm):
1. Detect failure condition
2. Log to `mesh-state.json`
3. Disable mesh (`enabled=false`)
4. Fall back to hierarchical coordination
5. Orchestrator resumes central coordination
6. Complete task via standard Tier-1 protocol

**Fallback triggers:**
- `deadlocks` > 5 in single session
- `message_storms` > 3 in single session
- `partition_events` > 2 in single session
- Orchestrator manual override

---

**Status:** Production-ready v3.1 (2026-07-01) — Full mesh for Tier-2+ tasks; A2A lightweight mode (including IMPACT) for all tiers.

**A2A Pilot Targets:**
1. builder → auditor DELEGATE: BOM validation mid-build (latency <5s, 0 deadlocks)
2. forge → auditor SUBSCRIBE/NOTIFY: Pipeline completion signals (zero missed events)
3. scraper → broadcast CACHE: Learned selectors shared before web extraction calls

**Performance Targets (v3.1):**
- Message overhead: <100ms per hop
- Conflict resolution: >95% success rate
- Deadlock rate: <1%
- Parallel speedup: 2-10x (full mesh Tier-2+), 1.5-3x (A2A lite Tier-1)
- DELEGATE round-trip: <5s for Tier-5 agents, <30s for Tier-4 specialists

**Pilot Metrics Output:** `session/a2a-pilot-metrics.jsonl`
