---
name: topology-selection
description: Explains how LeRoy selects agent communication topology (hierarchy/mesh/hybrid) per task shape. Descriptive metadata — Sprint 2 #6.
tags: [topology, agents, scaling, meta]
trigger: "topology" | "what topology" | "log schema"
---

# Topology Selection (Sprint 2 — Descriptive)

Topology is **descriptive metadata** in the Sprint 2 implementation. It describes what communication shape a task uses. Prescriptive routing (agents actually behaving differently) is gated behind Sprint 8 / Q3 telemetry work.

---

## Purpose

Different tasks have different natural communication shapes:

| Topology | Shape | When |
|---|---|---|
| `hierarchy` | COO → specialists → guardian (strict chain) | Commit workflows, releases, contracts, signed emails, deploys |
| `mesh` | Agents communicate laterally + report to COO | Debate, research, recon, parallel hunts, brainstorming |
| `hybrid` | COO conducts but agents can communicate laterally for sub-decisions | Most general tasks (default) |

---

## Rule Semantics

Rules live in `session/topology-rules.json` (hot-reloadable — edit the file, next gate picks it up):

```json
{
  "version": 1,
  "default": "hybrid",
  "trivial_skip": true,
  "rules": [...]
}
```

**Matching algorithm: first-match-wins**

1. Gate-enforcer scans the prompt for keywords from each rule's `any_keyword` list.
2. First rule whose keywords match wins.
3. If no rule matches, `default` applies (`"hybrid"`).
4. If `trivial_skip: true` AND the prompt is trivial (<20 chars, no substantial task active), topology is skipped entirely — no log event, no banner line.

**Conflict resolution:** rules are evaluated in JSON order. Put more specific rules first.

---

## Auto-Detection vs Declared Topology

**Auto (default):** gate-enforcer runs `_select_topology(prompt)` — keyword scan → first-match-wins.

**Declared override:** Claude can override in its gate output by stating a different topology. The engine reads the declared value and logs both:
```
topology_selected payload: {auto: "hybrid", declared: "mesh", override: true, rule: "...", prompt_keywords: [...]}
```

---

## When to Override

Override auto-selection when task shape is ambiguous or prompt keywords don't match the actual structure:

| Scenario | Auto would pick | Override to | Why |
|---|---|---|---|
| "commit this research summary" | hierarchy (commit keyword) | mesh | It's a research doc, not a code release |
| "brainstorm then send email" | mesh (brainstorm keyword) | hybrid | Needs both lateral thinking and strict send chain |
| "debate the commit strategy" | hierarchy or mesh | mesh | Debate wins — peer communication needed |

Declare topology in the gate header block, not in the body. Keep it one line.

---

## Display

Topology is NOT in the 200-character gate header line (space constraint). It appears:
1. In the gate banner footer, next to `COST_TODAY`: `TOPOLOGY: hybrid (auto, rule="default")`
2. In the Deployment Manifest box.

---

## Modifying the Rules

Edit `session/topology-rules.json` directly — changes take effect at the next gate emission (hot-reload). No hook restart required.

To add a new topology keyword (example: route "threat model" to mesh):
```json
{"topology": "mesh", "any_keyword": [..., "threat model"]}
```

---

## Future: Sprint 8 Prescriptive Routing (deferred)

In Q3, once 3+ months of `topology_selected` telemetry exist in `session/leroy.log`, topology will become **prescriptive**: agents will actually route differently based on it (mesh agents skip COO mediation for sub-decisions; hierarchy agents gate all comms through COO). That work is tracked as Sprint 8. Do NOT ship prescriptive behavior in Sprint 2.

---

## Disable Path

To stop topology selection entirely (falls back to no display):
```
touch session/leroy-logger.disabled
```
(The topology telemetry event writes through the same leroy_log module.)

Or remove the `_select_topology` / `_get_or_create_trace_id` calls from gate-enforcer.py if the feature needs to be fully removed.
