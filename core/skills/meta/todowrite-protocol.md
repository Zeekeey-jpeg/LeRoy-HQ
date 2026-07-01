# TodoWrite Mandatory Trigger Protocol

> **Extracted from:** CLAUDE.md - TodoWrite section
> **Purpose:** Defines when and how TodoWrite MUST be used

---

## CRITICAL Rule

Claude MUST use the TodoWrite tool for tasks meeting ANY of these criteria.

---

## Mandatory TodoWrite Triggers

TodoWrite is **REQUIRED** (not optional) when task involves:

1. **3+ Distinct Steps** - Task requires 3 or more separate actions
2. **Multi-File Changes** - Task touches 2 or more files
3. **Implementation Keywords** - Prompt contains: `implement`, `build`, `create`, `refactor`, `migrate`, `fix` (with investigation), `update` (substantial), `analyze`, `design`, `integrate`, `optimize`, `deploy`, `configure`, `setup`, `install`
4. **Architectural Decisions** - Task requires design or planning

---

## TodoWrite Protocol

When TodoWrite is mandatory:

1. **BEFORE first tool call:** Create todo list with all task steps
2. **Mark one item as in_progress** before starting work on it
3. **Mark completed immediately** when step finishes (don't batch)
4. **Keep list updated** throughout task execution
5. **Final item** should be "Test/verify implementation"

---

## Why This Matters

TodoWrite provides:
- **Visibility** - User sees progress in real-time
- **Organization** - Complex tasks broken into trackable steps
- **Quality Assurance** - Nothing gets skipped
- **Metrics Tracking** - Completion rates feed into efficiency reports

**Full Examples:** See Memory vault -> `Skills-Learned/TodoWrite-Examples.md`.

---

*Extracted from CLAUDE.md to reduce hub file size. All routing pointers preserved.*
