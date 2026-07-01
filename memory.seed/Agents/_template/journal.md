---
agent: "{agent-name}"
type: agent-journal
created: 2026-01-01
entries: 1
---

# {agent-name} — Journal

> Append-only cross-agent memory for the `{agent-name}` agent. Newest entries at the bottom.
> Written by the conductor via the IMPACT protocol (see `memory/Agents/index.md`). Never
> overwrite an existing entry; add a new dated one.

---

## 2026-01-01 — Example entry (delete when real entries arrive)

- **What changed:** A shared reference the conductor decided this agent depends on was modified.
- **Who changed it:** {origin-agent} (via `[A2A:IMPACT]`).
- **Why it matters here:** Next time `{agent-name}` runs on related work, it should account for
  this change rather than assuming the old state.
- **Connections:** none yet — this is the first entry. As the store grows, related entries get
  cross-referenced here.
