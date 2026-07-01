---
name: agent-feedback-loop
description: "Agent quality monitoring system. Schema registry maps each agent to expected output fields and minimum quality thresholds. Quality signals are written to session/agent-feedback.jsonl by agent-feedback-collector.py on session Stop. Agents with quality_score < 0.7 for 3 consecutive tasks get flagged in enforcement.todo for review."
version: 1.0
created: 2026-04-11
owner: meta
---

# Agent Feedback Loop System

## Purpose

Agents report unidirectionally — no quality signals cross agent boundaries. An agent can consistently produce incomplete outputs and no system detects it. This schema-based feedback system fills that gap.

**How it works:**
1. `gate-validator-trigger.py` calls `scripts/agent-feedback-collector.py` on every session Stop
2. Collector reads `session/growth-output.md` + `session/secretary-output.md`
3. Validates each against the schema registry below
4. Writes quality signals to `session/agent-feedback.jsonl`
5. If quality_score < 0.7 for 3 consecutive tasks → writes `LOW_QUALITY_AGENT` to enforcement.todo
6. gate-enforcer.py surfaces `LOW_QUALITY_AGENT` on next session start

---

## Schema Registry

Each agent has a contract: minimum required output fields and quality thresholds.

### scout
```json
{
  "agent": "scout",
  "output_file": "session/growth-output.md",
  "required_fields": ["[GROWTH]", "Last updated:", "Session:"],
  "quality_fields": {
    "has_patterns_section": ["Skill Opportunities", "Enhancement Opportunities", "Existing Documentation"],
    "has_timestamp": ["Last updated:"],
    "has_session_id": ["Session:"],
    "not_empty": "[GROWTH] No actionable patterns detected this session."
  },
  "minimum_quality_score": 0.7,
  "scoring": {
    "has_patterns_or_empty_valid": 0.4,
    "has_timestamp": 0.3,
    "has_session_id": 0.3
  }
}
```

### secretary
```json
{
  "agent": "secretary",
  "output_file": "session/secretary-output.md",
  "required_fields": ["timeline", "client", "last_contact"],
  "quality_fields": {
    "has_timeline_entries": ["timeline", "event", "updated"],
    "has_client_reference": ["client:", "ExampleClient", "ExampleClient", "LeRoy", "an LMS"],
    "has_last_contact": ["last_contact", "email sent", "meeting"]
  },
  "minimum_quality_score": 0.6,
  "notes": "Secretary output is optional — only required if secretary was spawned"
}
```

### cyber-operator (bug bounty reports)
```json
{
  "agent": "cyber-operator",
  "output_file": "memory/Projects/Research/{ProgramName}/findings.md",
  "required_fields": ["vector", "endpoint", "poc_confirmed", "evidence"],
  "quality_fields": {
    "has_vector": ["SSRF", "XSS", "IDOR", "SQLi", "vector:"],
    "has_endpoint": ["endpoint:", "GET ", "POST ", "https://"],
    "has_evidence": ["evidence:", "confirmed", "HTTP", "response"],
    "has_cvss": ["CVSS", "Critical", "High", "Medium"]
  },
  "minimum_quality_score": 0.75,
  "scoring": {
    "has_vector": 0.3,
    "has_endpoint": 0.2,
    "has_evidence": 0.3,
    "has_cvss": 0.2
  }
}
```

### recon-agent
```json
{
  "agent": "recon-agent",
  "output_file": "memory/Projects/Research/{ProgramName}/recon.md",
  "required_fields": ["subdomain_list", "source"],
  "quality_fields": {
    "has_subdomain_list": ["subdomains:", "subdomain_list", "*.target.com"],
    "has_cname_targets": ["cname_targets", "CNAME", "dangling"],
    "has_source": ["source:", "subfinder", "crt.sh", "amass"]
  },
  "minimum_quality_score": 0.6,
  "notes": "cname_targets is expected but not required — flag as warning if missing"
}
```

---

## Quality Scoring Algorithm

```python
def score_output(output_content: str, schema: dict) -> float:
    """Score agent output against schema. Returns 0.0-1.0."""
    score = 0.0
    scoring_weights = schema.get("scoring", {})
    quality_fields = schema.get("quality_fields", {})
    
    for field_name, indicators in quality_fields.items():
        weight = scoring_weights.get(field_name, 1.0 / len(quality_fields))
        if isinstance(indicators, list):
            if any(ind.lower() in output_content.lower() for ind in indicators):
                score += weight
        elif isinstance(indicators, str):
            # String comparison for special cases (e.g., empty valid output)
            if indicators in output_content:
                score += weight
    
    return min(score, 1.0)
```

---

## Agent Feedback Signal Format

`session/agent-feedback.jsonl` — one JSON per line:

```json
{
  "ts": "2026-04-11T14:30:00Z",
  "reporter": "agent-feedback-collector",
  "agent": "recon-agent",
  "signal_type": "quality_warning",
  "quality_score": 0.55,
  "missing_fields": ["cname_targets"],
  "recommendation": "CNAME targets missing — subdomain takeover check may be incomplete",
  "session_id": "abc123",
  "consecutive_low_score": 1
}
```

`signal_type` values:
- `quality_ok` — score ≥ threshold
- `quality_warning` — score < threshold (first or second occurrence)
- `low_quality_agent` — score < threshold for 3 consecutive sessions → triggers enforcement

---

## Enforcement Integration

When `low_quality_agent` signal fires, appended to `session/enforcement.todo`:

```
LOW_QUALITY_AGENT | agent=recon-agent | score=0.55 | missing=cname_targets | Priority: 1
```

gate-enforcer.py reads this and surfaces:
```
⚠️ LOW QUALITY AGENT: recon-agent scored 0.55/0.60 threshold for 3 sessions.
   Missing: cname_targets
   Action: Review recon-agent.md prompting — ensure CNAME enumeration is required output
```

---

## How to Add an Agent to the Registry

1. Identify the agent's primary output file
2. List 3-5 required fields that signal the output is complete
3. Define quality_fields with string indicators (partial match is fine)
4. Set minimum_quality_score (0.6-0.8 typical)
5. Add schema entry to this file's Schema Registry section
6. Update `scripts/agent-feedback-collector.py` SCHEMA_REGISTRY dict
