# Quantified Performance Targets

**Version:** 1.0
**Type:** Meta-Skill (Performance Pattern)
**Purpose:** Framework for specifying measurable objectives upfront
**Last Updated:** 2026-01-18

---

## Pattern Overview

**The Rule:** ALL performance-critical frameworks MUST specify quantified targets before implementation.

This ensures:
- Objective success/failure criteria
- Comparable performance across iterations
- Early detection of degradation
- Data-driven optimization priorities
- Clear communication of expectations

---

## Target Specification Format

### Standard Template

```markdown
## Performance Targets

| Metric | Target | Max | Current | Status |
|--------|--------|-----|---------|--------|
| {metric_name} | {target_value} | {max_acceptable} | {actual_value} | {✅/❌} |
```

**Field definitions:**
- **Metric:** What is being measured (execution time, throughput, accuracy, etc.)
- **Target:** Desired performance level
- **Max:** Maximum acceptable before considered failure
- **Current:** Actual measured performance
- **Status:** ✅ if current ≤ target, ❌ if current > max

### Example

```markdown
## Performance Targets

| Metric | Target | Max | Current | Status |
|--------|--------|-----|---------|--------|
| Scenarios (100) | <5 min | 10 min | 3.2 min | ✅ |
| Scenarios (1K) | <15 min | 30 min | 12.4 min | ✅ |
| Scenarios (10K) | <60 min | 90 min | - | - |
| Safety violations | 0 | 0 | 0 | ✅ |
| Memory usage | <500MB | 1GB | 320MB | ✅ |
```

---

## Metric Categories

### 1. Time-Based Metrics
**What to measure:** Execution duration, latency, response time

**Format:**
```markdown
| {Operation} | {target_time} | {max_time} | {actual} | {status} |
```

**Examples:**
- Planning phase: Target <5 min, Max 10 min
- Scenario generation: Target <5 min (100 scenarios), Max 10 min
- Full simulation: Target <60 min (10K scenarios), Max 90 min
- API response time: Target <500ms, Max 2s
- Database query: Target <100ms, Max 1s

**Units:** Use ms, seconds, minutes based on scale
- <1s: Use milliseconds (ms)
- 1s-60s: Use seconds
- >60s: Use minutes

### 2. Accuracy Metrics
**What to measure:** Success rate, precision, recall, correctness

**Format:**
```markdown
| {Operation} | {target_%} | {min_acceptable_%} | {actual_%} | {status} |
```

**Examples:**
- Success rate: Target >90%, Min 70%
- Test coverage: Target >80%, Min 60%
- Disambiguation accuracy: Target >95%, Min 85%
- Prediction accuracy: Target >80%, Min 60%

**Units:** Always use percentage (%) for accuracy metrics

### 3. Throughput Metrics
**What to measure:** Items processed per unit time

**Format:**
```markdown
| {Operation} | {target_rate} | {min_rate} | {actual_rate} | {status} |
```

**Examples:**
- Scenarios per minute: Target 200/min, Min 100/min
- API requests per second: Target 100/s, Min 50/s
- Records processed per hour: Target 10K/hr, Min 5K/hr

**Units:** Use appropriate time unit (per second, per minute, per hour)

### 4. Resource Metrics
**What to measure:** Memory, CPU, disk, network usage

**Format:**
```markdown
| {Resource} | {target_usage} | {max_usage} | {actual_usage} | {status} |
```

**Examples:**
- Memory usage: Target <500MB, Max 1GB
- CPU usage: Target <50%, Max 80%
- Disk space: Target <1GB, Max 5GB
- Network bandwidth: Target <10Mbps, Max 50Mbps

**Units:** Use MB/GB for memory/disk, % for CPU, Mbps for network

### 5. Quality Metrics
**What to measure:** Error rate, violation count, code quality

**Format:**
```markdown
| {Quality_measure} | {target} | {max_acceptable} | {actual} | {status} |
```

**Examples:**
- Safety violations: Target 0, Max 0 (zero tolerance)
- Critical bugs: Target 0, Max 2
- False positives: Target <1%, Max 5%
- Code coverage: Target >80%, Max N/A (higher is better)

---

## Setting Targets (How to Choose Values)

### Method 1: Baseline + Improvement
**Use when:** You have existing performance data

**Process:**
1. Measure current performance (baseline)
2. Set target = baseline × improvement_factor
3. Set max = baseline (don't regress)

**Example:**
- Current: Simulation takes 45 min for 10K scenarios
- Target: 45 min × 0.66 = 30 min (33% improvement)
- Max: 60 min (acceptable regression of 33%)

### Method 2: User Expectation
**Use when:** Users have specific requirements

**Process:**
1. Ask users: "How long is acceptable?"
2. Set target = user expectation × 0.8 (20% buffer)
3. Set max = user expectation

**Example:**
- User: "I need simulation results within 1 hour"
- Target: 60 min × 0.8 = 48 min
- Max: 60 min

### Method 3: Industry Benchmark
**Use when:** Standard benchmarks exist

**Process:**
1. Research industry standards
2. Set target = industry average
3. Set max = industry average × 1.5

**Example:**
- Industry: API response time averages 200ms
- Target: 200ms
- Max: 300ms (50% slower than average acceptable)

### Method 4: Technical Constraint
**Use when:** Hard limits exist (timeouts, SLAs, quotas)

**Process:**
1. Identify constraint (e.g., 1-hour timeout)
2. Set max = constraint
3. Set target = constraint × 0.75 (25% safety margin)

**Example:**
- Constraint: Claude conversation timeout = 60 min
- Max: 60 min
- Target: 45 min

---

## Target Ranges

### Tight Targets (High Precision Required)
**Use when:** Performance-critical path, user-facing

**Range:** Target = Max × 0.9

**Example:**
- API response time: Target 450ms, Max 500ms (10% range)

### Moderate Targets (Balanced)
**Use when:** Internal tools, non-critical paths

**Range:** Target = Max × 0.75

**Example:**
- Report generation: Target 3 min, Max 4 min (25% range)

### Loose Targets (Exploratory)
**Use when:** New features, uncertain performance

**Range:** Target = Max × 0.5

**Example:**
- New algorithm: Target 30 min, Max 60 min (50% range)

---

## Monitoring Targets

### Continuous Tracking
**Pattern:**
```python
def track_performance(metric_name, actual_value, targets):
    target = targets[metric_name]["target"]
    max_val = targets[metric_name]["max"]

    status = "✅" if actual_value <= target else "⚠️" if actual_value <= max_val else "❌"

    log_metric(metric_name, actual_value, target, max_val, status)

    if status == "❌":
        alert_performance_degradation(metric_name, actual_value, max_val)
```

### Alerting Thresholds
**Levels:**
1. **Green (✅):** actual ≤ target - No action
2. **Yellow (⚠️):** target < actual ≤ max - Monitor closely
3. **Red (❌):** actual > max - Alert immediately

**Alert template:**
```
[PERFORMANCE ALERT] {metric_name} exceeded maximum

Current: {actual_value}
Target: {target_value}
Max: {max_value}
Overage: {actual - max}

Action required: Investigate performance degradation
```

---

## Integration with Frameworks

### Super Power Framework
**File:** `skills/meta/super-power.md`

**Targets defined:**
```markdown
## Performance Targets

| Metric | Target | Max |
|--------|--------|-----|
| Scenarios (100) | <5 min | 10 min |
| Scenarios (1K) | <15 min | 30 min |
| Scenarios (10K) | <60 min | 90 min |
| Safety violations | 0 | 0 |
| Planning phase | <5 min | 10 min |
```

**Tracking location:** `session/super_power/{YYYY-MM-DD}/status.json`

### Skill Composer
**File:** `skills/meta/skill-composer.md`

**Targets defined:**
```markdown
## Success Metrics

**Targets (from simulation report):**
- Generation success rate: >90%
- Generation time: <60 seconds
- Disambiguation rate: <30% (baseline: 44%)
- User adoption: 3+ skills/week
```

**Tracking:** `session/skill-composer-metrics.json`

### Memory System
**File:** `skills/meta/memory-recall.md`

**Targets defined:**
```markdown
## Performance (v3.0 with Scaling)

| Operation | Time | Notes |
|-----------|------|-------|
| Cold start recall | <200ms | First recall in session |
| Cache hit recall | <5ms | LRU cache (90%+ hit rate) |
| Tag intersection | O(1) | Pre-computed |
| Expansion | <20ms | From LRU cache |
| Full search | 2-3 sec | Tier 3 only (rare) |
```

---

## Target Violation Response

### When Target Missed (Yellow ⚠️)
**Action:** Monitor and investigate

**Process:**
1. Log warning
2. Check recent changes (code, data, environment)
3. Profile to identify bottleneck
4. Create ticket for optimization (P2-P3)
5. Set deadline to return to green

### When Max Exceeded (Red ❌)
**Action:** Immediate investigation and fix

**Process:**
1. Alert team immediately
2. Rollback recent changes if applicable
3. Profile and identify root cause
4. Implement quick fix or workaround
5. Create ticket for permanent fix (P0-P1)
6. Post-mortem after resolution

---

## Examples

### Example 1: API Performance Targets
**Framework:** REST API for CRM integration

**Targets:**
```markdown
| Metric | Target | Max | Current | Status |
|--------|--------|-----|---------|--------|
| GET /deals (paginated) | 200ms | 500ms | 180ms | ✅ |
| POST /deal | 300ms | 1s | 450ms | ⚠️ |
| GET /deals (unpaginated) | N/A | N/A | BLOCKED | ❌ |
| Throughput | 100 req/s | 50 req/s | 85 req/s | ✅ |
```

**Actions:**
- POST /deal: Investigate 450ms (exceeds target, within max) - P2 ticket
- Unpaginated GET: BLOCKED by safety validator - Expected behavior ✅

### Example 2: Simulation Framework Targets
**Framework:** Super Power simulation

**Targets:**
```markdown
| Metric | Target | Max | Current | Status |
|--------|--------|-----|---------|--------|
| Planning phase | 5 min | 10 min | 3.2 min | ✅ |
| Scenario gen (1K) | 5 min | 10 min | 4.1 min | ✅ |
| Execution (1K, 12 agents) | 15 min | 30 min | 12.4 min | ✅ |
| Report generation | 5 min | 10 min | 2.8 min | ✅ |
| Total runtime (1K scenarios) | 30 min | 60 min | 22.5 min | ✅ |
| Safety violations | 0 | 0 | 0 | ✅ |
```

**Result:** All targets met ✅ - Framework performing within expectations

---

## Target Evolution

### Quarterly Review Process
**When:** Every 3 months or after major changes

**Process:**
1. **Collect data** - Actual performance over last quarter
2. **Analyze trends** - Improving, stable, or degrading?
3. **Adjust targets** - Tighten if consistently beating, loosen if unrealistic
4. **Document changes** - Update framework docs, communicate to team

**Example:**
```markdown
## Target Evolution

**Q1 2026:**
- Simulation (1K scenarios): Target 15 min → Actual 12 min (consistently)
- **Q2 2026 adjustment:** Target 12 min, Max 15 min (tightened by 20%)

**Q2 2026:**
- API response (GET /deals): Target 200ms → Actual 180ms (consistently)
- **Q3 2026 adjustment:** Target 150ms, Max 200ms (tightened by 25%)
```

---

## Checklist

**Before implementing framework:**
- [ ] Performance targets defined for all critical operations
- [ ] Target values justified (baseline, user expectation, benchmark, or constraint)
- [ ] Max values set (realistic failure threshold)
- [ ] Monitoring/tracking implemented
- [ ] Alerting configured for violations
- [ ] Team trained on target expectations

---

## Related Patterns

**See also:**
- `skills/meta/framework-documentation-standard.md` - Include performance targets in Part 5
- `skills/meta/four-week-framework-rollout-template.md` - Track targets throughout rollout
- `skills/tooling/simulation-report-template.md` - Report targets vs actuals
- `skills/meta/risk-classification-framework.md` - Classify target violations by severity

---

*Quantified Performance Targets v1.0 | Measurable objectives | Data-driven optimization*
