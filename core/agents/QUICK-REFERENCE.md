# Agent Org Chart - Quick Reference

**Version:** 1.0

---

## 🎯 Core Principle

**C-suite delegates, workers execute. Period.**

---

## 5-Tier Hierarchy

```
Tier 1: C-Suite         → Coordination ONLY (NO Edit/Write)
Tier 2: VP Level        → Oversight ONLY (NO Edit/Write)
Tier 3: Management      → Limited Edit/Write (domain-specific)
Tier 4: Specialists     → Full Edit/Write (implementation)
Tier 5: Support         → Read-only (monitoring/research)
```

---

## ✅ Who Can Write Code?

| Agent | Can Edit/Write? | Domain |
|-------|----------------|--------|
| **builder** | ✅ YES | Production code, tests, config |
| **designer** | ✅ YES | Design systems, UI components |
| **forge** | ✅ YES | Data operations, ETL, large-scale |
| **professor** | ✅ YES | Educational content, domain instruction |
| **guardian** | ✅ YES | QC audits, pre-commit validation |
| **legal** | ✅ YES | Contracts, legal docs |
| **janitor** | ✅ YES | Cleanup, maintenance |
| **proposal-writer** | ✅ YES | Sales proposals, presentations |

---

## ❌ Who CANNOT Write Code?

| Agent | Tool Access | Why |
|-------|------------|-----|
| **conductor** (COO) | Coordination only | Delegates to builder/designer/forge |
| **cto** | Coordination only | Sets architecture, builder implements |
| **vp-engineering** | Coordination only | Reviews code, builder writes it |
| **chief-of-staff** | Reports only | Tracks timelines, doesn't implement |
| **scout** | Read-only | Observes patterns, doesn't modify |
| **planner** | Read-only | Tracks tasks, doesn't execute |

---

## 🚨 Red Flags (Violations)

### Critical Violations
- ❌ C-suite uses Edit/Write tools
- ❌ C-suite uses >15 tools per task
- ❌ VP uses Edit/Write tools
- ❌ Implementation work not delegated

### How to Spot Violations
```
conductor (Design workflow) · 44 tool uses · 65.3k tokens
                                ^^^^^^^^^^
                        RED FLAG: Should have delegated!
```

**What should happen instead:**
```
conductor (Coordinate workflow) · 8 tool uses
  ├─ builder (Implement workflow) · 28 tool uses
  └─ guardian (Review workflow) · 12 tool uses
```

---

## 📋 Correct Delegation Patterns

### Pattern 1: Small Task (1-2 packets)
```
User: "Add logging to auth module"
Main → conductor (coordinate)
       conductor → builder (implement logging)
                   builder → uses Edit/Write (25 tools)
       conductor → guardian (review changes)
                   guardian → uses Read (10 tools)
       conductor → reports back (total: 8 tools)
```

### Pattern 2: Medium Task (4-6 packets) - DEPLOY TEAM
```
User: "Refactor authentication system"
Main → conductor (coordinate)
       conductor → builder-1 (API layer - 3 packets)
                   builder-1 → Edit/Write (30 tools)
       conductor → builder-2 (Database - 2 packets)
                   builder-2 → Edit/Write (25 tools)
       conductor → designer (UI updates - 1 packet)
                   designer → Edit/Write (20 tools)
       conductor → guardian (review all changes)
                   guardian → Read (15 tools)
       conductor → reports back (total: 8 tools)

Total: 3 specialists working in PARALLEL
```

### Pattern 3: Large Task (8-12 packets) - DEPLOY TEAM + MANAGER
```
User: "Build new reporting system with dashboard"
Main → conductor (coordinate)
       conductor → vp-engineering (manage team - 8 packets)
                   vp-engineering → builder-1 (API endpoints - 3 packets)
                                    builder-1 → Edit/Write (35 tools)
                   vp-engineering → builder-2 (Data queries - 2 packets)
                                    builder-2 → Edit/Write (28 tools)
                   vp-engineering → builder-3 (Export logic - 2 packets)
                                    builder-3 → Edit/Write (22 tools)
                   vp-engineering → builder-4 (Tests - 1 packet)
                                    builder-4 → Edit/Write (18 tools)
       conductor → designer-1 (Report UI - 2 packets)
                   designer-1 → Edit/Write (25 tools)
       conductor → designer-2 (Dashboard - 2 packets)
                   designer-2 → Edit/Write (28 tools)
       conductor → forge (Data pipeline - 2 packets)
                   forge → Edit/Write (40 tools)
       conductor → guardian (review all changes)
                   guardian → Read (20 tools)
       conductor → reports back (total: 10 tools)

Total: 7 specialists + 1 manager = 8 agents working in PARALLEL
```

### Pattern 4: Massive Task (15+ packets) - FULL ORG DEPLOYMENT
```
User: "Cross-product release with 3 features per product"
Main → conductor (coordinate)
       conductor → cto (architecture oversight)
       conductor → vp-engineering (Coding Department - 9 packets)
                   vp-engineering → builder-1 (Product A feature 1)
                   vp-engineering → builder-2 (Product A feature 2)
                   vp-engineering → builder-3 (Product B feature 1)
                   vp-engineering → builder-4 (Product B feature 2)
                   vp-engineering → builder-5 (Product C feature 1)
                   vp-engineering → designer-1 (Product A UI)
                   vp-engineering → designer-2 (Product B UI)
                   vp-engineering → professor (domain validation)
                   vp-engineering → forge (Data migrations)
       conductor → tech-lead (Infrastructure - 4 packets)
                   tech-lead → builder-6 (CI/CD updates)
                   tech-lead → builder-7 (Deployment scripts)
                   tech-lead → builder-8 (Monitoring setup)
                   tech-lead → janitor (Cleanup old code)
       conductor → scrum-leader (Documentation - 2 packets)
                   scrum-leader → builder-9 (API docs)
                   scrum-leader → builder-10 (Release notes)
       conductor → guardian (review all changes)
       conductor → reports back

Total: 14 specialists + 4 managers = 18 agents in PARALLEL

This is how you leverage a multi-position org chart!
```

---

## 🚀 Scaling Guidelines for COO

**YOU ARE AUTHORIZED AND ENCOURAGED TO DEPLOY LARGE TEAMS**

| Work Packets | Team Size | Manager? | Example |
|--------------|-----------|----------|---------|
| 1-3 | 1-2 specialists | No | Small bug fix |
| 4-6 | 3-5 specialists | Optional | Feature development |
| 7-12 | 5-10 specialists | Required | Multi-component refactor |
| 13-20 | 10-15 specialists | Multiple | Cross-product release |
| 21+ | 15+ specialists | Department-level | Major platform upgrade |

**Remember:**
- Each position (builder, designer, forge) can have MULTIPLE workers
- Deploy to CAPACITY, not minimum
- Use managers (VP Engineering, Tech Lead) for 7+ packets
- Parallelize everything possible
- You have a full org chart available - USE IT

---

## 📊 Tool Count Expectations

| Tier | Typical | Red Flag | Max |
|------|---------|----------|-----|
| C-Suite | 5-8 | >15 | 15 |
| VP | 6-10 | >12 | 12 |
| Management | 8-12 | >15 | 15 |
| Specialists | 20-40 | N/A | Unlimited |
| Support | 5-10 | >15 | 15 |

---

## 🔧 Reference Documents

| Document | Purpose |
|----------|---------|
| `agents/org-governance.md` | Complete 5-tier hierarchy, tool access rules |
| `agents/c-suite-tool-constraints.md` | C-suite specific constraints |
| `skills/meta/agent-tool-validator.md` | Validation system, enforcement |
| `CLAUDE.md` | Agent deployment table with tool access |

---

## ⚡ Quick Checks

### Before Spawning Agent
- [ ] Is this agent appropriate for the task?
- [ ] Does the agent have the right tools?
- [ ] If C-suite, are they coordinating or implementing?
- [ ] If implementing, should spawn builder/designer/forge instead?

### After Agent Completes
- [ ] Tool count within expected range?
- [ ] C-suite used <15 tools?
- [ ] C-suite didn't use Edit/Write?
- [ ] Proper delegation occurred?

---

## 🎓 Training Examples

### ✅ CORRECT: C-Suite Delegates
```
Request: "Refactor auth system"
Main spawns conductor
Conductor:
  1. Reads current auth system (3 tools)
  2. Spawns builder → "Refactor auth system"
  3. Spawns designer → "Update auth UI"
  4. Spawns guardian → "Review refactoring"
  5. Monitors progress (2 tools)
  6. Reports back
Total: 8 tools ✅
```

### ❌ INCORRECT: C-Suite Implements
```
Request: "Refactor auth system"
Main spawns conductor
Conductor:
  1. Reads current auth system
  2. Edits auth files directly
  3. Writes new auth module
  4. Updates UI components
  5. Edits tests
  6. Reports back
Total: 44 tools ❌ VIOLATION
```

---

## 💡 When in Doubt

**Ask yourself:**
1. Is this agent a coordinator (C-suite/VP)?
2. Is the task implementation work (code, design, data)?
3. If YES to both → **DELEGATE to builder/designer/forge**

**Rule of thumb:** If the agent is using Edit/Write tools, they should be Tier 4 (Specialist) or have explicit domain restriction (Tier 3 Management).

---

**Remember:** A full org chart with proper delegation is how we scale. C-suite runs the company, workers build the product.

---

**Owner:** the user
**Status:** MANDATORY - Zero tolerance for violations
