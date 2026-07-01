# Workflows — Index

Multi-step procedures LeRoy runs for you. Route by the trigger table, or drop a new
markdown file into any folder and it becomes discoverable.

## Trigger → Workflow

| If the request is about… | Folder | File |
|---|---|---|
| PR, pull request, merge, commit review | git/ | pr-workflow.md |
| push, commit, git push | git/ | git-pushing.md |
| review, feedback, code review, implementing feedback | git/ | review-implementing.md |
| git safety, destructive git, force push, git protocol | git/ | git-safety-protocol.md |
| planning, substantial task, build planning | planning/ | planning-phase.md |
| scope, scope creep, feature creep | planning/ | scope-control.md |
| version management, version bump, version increment | | version-management.md |
| scenario matrix, test matrix, variable combinations, edge cases | | scenario-matrix-design.md |

---

## Available Workflows

### git/
- **pr-workflow.md** — Full PR creation and review process
- **git-pushing.md** — Commit and push conventions
- **review-implementing.md** — Responding to code review feedback
- **git-safety-protocol.md** — Guardrails for destructive git operations

### planning/
- **planning-phase.md** — Mandatory planning for substantial tasks
- **scope-control.md** — Preventing scope creep mid-task

### (top level)
- **version-management.md** — Version increment before commits
- **scenario-matrix-design.md** — Systematic scenario generation from variable dimensions

---

*More workflows ship as opt-in modules, or write your own — LeRoy discovers new files on the
next index build.*
