# Risk Classification Framework

**Version:** 1.0
**Type:** Meta-Skill (Classification Pattern)
**Purpose:** 3-tier risk assessment model (HIGH/MEDIUM/LOW) for consistent decision-making
**Last Updated:** 2026-01-18

---

## Framework Overview

**The Rule:** ALL risks are classified as HIGH, MEDIUM, or LOW using standardized criteria.

This ensures:
- Consistent risk assessment across domains
- Clear prioritization (HIGH risks first)
- Objective severity scoring
- Comparable risk levels across projects
- Actionable mitigation strategies

---

## 3-Tier Classification

### HIGH Risk
**Definition:** Immediate threat to system integrity, data safety, or business operations

**Characteristics:**
- **Impact:** System failure, data loss, security breach, significant financial loss
- **Likelihood:** Likely to occur without intervention
- **Urgency:** Requires immediate action (within hours/days)
- **Scope:** Affects multiple systems or users

**Examples:**
- Hardcoded credentials in production code
- No backup strategy for critical data
- Single point of failure in production pipeline
- Unpatched security vulnerabilities (CVSS ≥9.0)
- No rollback mechanism for deployments

**Response:**
- **Priority:** P0 - Drop everything
- **Timeline:** Fix within 24-48 hours
- **Owner:** Senior engineer + manager approval
- **Validation:** Must test fix before deployment

### MEDIUM Risk
**Definition:** Potential threat that could escalate if unaddressed

**Characteristics:**
- **Impact:** Degraded performance, user friction, moderate financial impact
- **Likelihood:** Possible but not certain
- **Urgency:** Should address within weeks
- **Scope:** Affects specific workflows or user segments

**Examples:**
- Missing pagination on large datasets (data loss risk)
- No error handling on critical paths
- Incomplete test coverage (<70%)
- Manual deployment process (automation gap)
- Security vulnerabilities (CVSS 4.0-8.9)

**Response:**
- **Priority:** P1-P2 - Schedule in sprint
- **Timeline:** Fix within 1-4 weeks
- **Owner:** Team lead assigns to engineer
- **Validation:** Test in staging environment

### LOW Risk
**Definition:** Minor issue with minimal immediate impact

**Characteristics:**
- **Impact:** Cosmetic issues, minor inconvenience, technical debt
- **Likelihood:** Unlikely or rare
- **Urgency:** Can defer to future sprints
- **Scope:** Isolated to specific edge cases

**Examples:**
- Suboptimal code patterns (no functional impact)
- Missing documentation for internal tools
- Minor UI inconsistencies
- Logging verbosity issues
- Security vulnerabilities (CVSS <4.0)

**Response:**
- **Priority:** P3-P4 - Backlog item
- **Timeline:** Fix when convenient (1-3 months)
- **Owner:** Junior engineer for learning
- **Validation:** Code review sufficient

---

## Classification Criteria

### Severity Matrix

| Impact | Likelihood | Classification |
|--------|-----------|----------------|
| **Critical** (System down, data loss) | High | **HIGH** |
| **Critical** | Medium | **HIGH** |
| **Critical** | Low | **MEDIUM** |
| **Major** (Degraded performance) | High | **HIGH** |
| **Major** | Medium | **MEDIUM** |
| **Major** | Low | **MEDIUM** |
| **Minor** (Cosmetic, edge case) | High | **MEDIUM** |
| **Minor** | Medium | **LOW** |
| **Minor** | Low | **LOW** |

### Impact Assessment

**Critical Impact:**
- System unavailable to users
- Data corruption or permanent loss
- Security breach or credential exposure
- Regulatory compliance violation
- Revenue loss >$10K

**Major Impact:**
- Feature unavailable but system functional
- Incomplete data (missing records)
- Performance degradation >50%
- User workflow blocked
- Revenue loss $1K-$10K

**Minor Impact:**
- Cosmetic issues (UI/UX)
- Edge case failures (<1% of users)
- Internal tools affected (not user-facing)
- Performance degradation <50%
- Revenue loss <$1K

### Likelihood Assessment

**High Likelihood:**
- Occurs frequently (daily/weekly)
- Reproducible 100% of the time
- Affects all users or environments
- No mitigation in place

**Medium Likelihood:**
- Occurs occasionally (monthly)
- Reproducible 50-99% of the time
- Affects subset of users or specific conditions
- Partial mitigation exists

**Low Likelihood:**
- Occurs rarely (yearly or less)
- Hard to reproduce (<50%)
- Affects edge cases only
- Mitigation exists but imperfect

---

## Domain-Specific Classifications

### Security Risks

**HIGH:**
- CVSS score ≥9.0
- Remote code execution (RCE)
- Privilege escalation
- Hardcoded credentials
- SQL injection vulnerabilities
- No authentication on sensitive endpoints

**MEDIUM:**
- CVSS score 4.0-8.9
- Cross-site scripting (XSS)
- CSRF vulnerabilities
- Weak password policies
- Missing encryption on transit
- Insufficient logging for security events

**LOW:**
- CVSS score <4.0
- Information disclosure (non-sensitive)
- Clickjacking vulnerabilities
- Missing security headers (non-critical)
- Verbose error messages

### Data Integrity Risks

**HIGH:**
- No backup strategy
- No data validation on write operations
- Concurrent write conflicts without locking
- No rollback mechanism for data changes
- Missing foreign key constraints

**MEDIUM:**
- Incomplete backup strategy (missing recent changes)
- Pagination gaps (missing data in queries)
- No data retention policy
- Missing audit trail for sensitive operations
- Weak data validation (allows some invalid data)

**LOW:**
- Redundant data storage (no normalization)
- Missing indexes (performance only)
- Stale cache data (non-critical)
- Missing documentation for data schema

### Performance Risks

**HIGH:**
- N+1 query patterns on critical paths (>100 queries per request)
- No query timeout (infinite loops possible)
- Memory leaks in production
- Unbounded result sets (OOM risk)
- Single-threaded blocking operations on critical path

**MEDIUM:**
- Suboptimal query patterns (10-100 queries per request)
- Missing database indexes (slow queries >5s)
- Large file uploads without streaming
- Synchronous operations that could be async
- No caching on expensive operations

**LOW:**
- Unoptimized algorithms (negligible impact <100ms)
- Extra network calls (redundant but fast)
- Verbose logging (minimal overhead)
- Missing connection pooling (low traffic)

### Operational Risks

**HIGH:**
- No deployment rollback mechanism
- Manual production deployments (human error risk)
- Single point of failure (no redundancy)
- No monitoring/alerting for critical services
- No disaster recovery plan

**MEDIUM:**
- Partial automation (some manual steps)
- Limited redundancy (single region)
- Basic monitoring (no proactive alerts)
- Incomplete documentation for runbooks
- No load testing before major releases

**LOW:**
- Missing CI/CD for non-critical projects
- Suboptimal deployment frequency
- Missing metrics for non-critical services
- Incomplete logging for debugging

---

## Gap Analysis Integration

**When analyzing gaps, classify severity:**

```markdown
#### Gap 1: {Title of Gap}
- **Severity:** {HIGH/MEDIUM/LOW}
- **Root Cause:** {Why gap exists}
- **Fix Complexity:** {Simple/Moderate/Complex}
- **Affected Scenarios:** {list}
- **Recommendation:** {How to fix}
```

**Severity guides priority:**
- HIGH severity → Fix immediately (P0)
- MEDIUM severity → Fix in current sprint (P1-P2)
- LOW severity → Backlog item (P3-P4)

---

## Risks & Rewards Integration

**When presenting risks, use classification:**

```markdown
### Risks

| Risk | Severity | Likelihood | Impact | Mitigation |
|------|----------|-----------|--------|------------|
| {Risk description} | {HIGH/MED/LOW} | {High/Med/Low} | {Impact description} | {Mitigation plan} |
```

**Risk prioritization:**
1. HIGH severity, High likelihood → Address first
2. HIGH severity, Medium likelihood → Address second
3. MEDIUM severity, High likelihood → Address third
4. All other combinations → Backlog

---

## Mitigation Strategies by Tier

### HIGH Risk Mitigation
**Approach:** Eliminate or transfer risk

**Strategies:**
1. **Eliminate:** Remove the risk entirely (e.g., delete hardcoded credentials)
2. **Implement safeguards:** Add validation, encryption, rollback mechanisms
3. **Transfer:** Use managed service (e.g., AWS handles infrastructure security)
4. **Immediate monitoring:** Alert on risk conditions

**Validation:** Must verify mitigation worked (test, audit, monitor)

### MEDIUM Risk Mitigation
**Approach:** Reduce likelihood or impact

**Strategies:**
1. **Reduce likelihood:** Add error handling, improve test coverage
2. **Reduce impact:** Graceful degradation, fallback mechanisms
3. **Monitor and alert:** Detect when risk manifests
4. **Document workarounds:** Interim solution while fix is developed

**Validation:** Test in staging, monitor in production

### LOW Risk Mitigation
**Approach:** Accept or defer

**Strategies:**
1. **Accept:** Document risk, monitor for escalation
2. **Defer:** Add to backlog, revisit quarterly
3. **Quick wins:** Fix if effort is minimal (<1 hour)
4. **Automated detection:** Linter rules, static analysis

**Validation:** Code review sufficient

---

## Examples

### Example 1: Security Audit
**Finding:** API endpoints have no authentication

**Classification:**
- **Impact:** Critical (any user can access sensitive data)
- **Likelihood:** High (publicly accessible, easily exploited)
- **Severity:** **HIGH**

**Response:**
- Priority: P0
- Timeline: 24 hours
- Mitigation: Add OAuth2 authentication to all endpoints
- Validation: Penetration test before re-deploying

---

### Example 2: Performance Issue
**Finding:** Database queries missing indexes

**Classification:**
- **Impact:** Major (queries take 8s instead of 0.5s)
- **Likelihood:** Medium (only affects reports, not critical path)
- **Severity:** **MEDIUM**

**Response:**
- Priority: P1
- Timeline: 1 week
- Mitigation: Add indexes on frequently queried columns
- Validation: Test query performance in staging

---

### Example 3: Code Quality
**Finding:** Inconsistent variable naming

**Classification:**
- **Impact:** Minor (cosmetic, no functional impact)
- **Likelihood:** Low (doesn't affect users, internal only)
- **Severity:** **LOW**

**Response:**
- Priority: P3
- Timeline: Next quarter
- Mitigation: Linter rules enforcing naming conventions
- Validation: Code review

---

## Integration with Simulation Reports

**In Highlights section:**
```markdown
### Finding 1: {Title}
- **Impact:** {Quantified consequence}
- **Evidence:** {Data}
- **Recommendation:** {Action}
- **Confidence:** {High/Med/Low}
- **Risk Severity:** {HIGH/MEDIUM/LOW}  ← Add this
```

**In Gap Analysis section:**
```markdown
#### Gap 1: {Title}
- **Severity:** {HIGH/MEDIUM/LOW}  ← Already present
- **Root Cause:** {Why}
- **Fix Complexity:** {Simple/Moderate/Complex}
```

**In Risks & Rewards section:**
```markdown
| Risk | Severity | Likelihood | Impact | Mitigation |
|------|----------|-----------|--------|------------|
| {Risk} | {HIGH/MED/LOW} | {High/Med/Low} | {Impact} | {Plan} |
```

---

## Decision Tree

**Use this flowchart to classify risks:**

```
START
  |
  ├─ Could this cause system downtime or data loss?
  |    └─ YES → HIGH
  |    └─ NO  → Continue
  |
  ├─ Could this affect user workflows significantly?
  |    └─ YES → Is it likely to occur frequently?
  |         └─ YES → HIGH
  |         └─ NO  → MEDIUM
  |    └─ NO  → Continue
  |
  ├─ Is this a cosmetic or edge case issue?
  |    └─ YES → LOW
  |    └─ NO  → MEDIUM (default to higher tier if uncertain)
```

---

## Validation Checklist

**Before assigning risk classification:**

- [ ] Impact assessed (Critical/Major/Minor)
- [ ] Likelihood assessed (High/Medium/Low)
- [ ] Severity matrix consulted
- [ ] Domain-specific criteria reviewed (security, data, performance, ops)
- [ ] Mitigation strategy identified
- [ ] Priority assigned (P0-P4)
- [ ] Timeline estimated
- [ ] Owner assigned

---

## Success Metrics

**How to measure classification effectiveness:**

| Metric | Target | Measurement |
|--------|--------|-------------|
| HIGH risks addressed | 100% within 48h | Audit of HIGH risk tickets |
| MEDIUM risks addressed | >80% within 4 weeks | Sprint velocity tracking |
| LOW risks deferred | >50% to backlog | Backlog grooming sessions |
| Escalations (LOW → MEDIUM → HIGH) | <10% | Track risk re-classifications |

---

## Common Pitfalls

### ❌ Pitfall 1: Over-classifying everything as HIGH
**Problem:** If everything is HIGH, nothing is HIGH

**Impact:** Real emergencies get lost in noise

**Solution:** Use severity matrix objectively, not emotionally

### ❌ Pitfall 2: Under-classifying due to optimism bias
**Problem:** "It probably won't happen" → classify as LOW

**Impact:** HIGH risks slip through, cause outages

**Solution:** Assess likelihood realistically based on data, not hope

### ❌ Pitfall 3: Inconsistent criteria across domains
**Problem:** Security uses different criteria than performance

**Impact:** Incomparable risk levels, confusing prioritization

**Solution:** Use standardized matrix across all domains

---

## Related Patterns

**Combines well with:**
- **Simulation Report Template** - Risks & Rewards section uses classifications
- **Gap Analysis** - Severity field maps directly to risk tiers
- **Mandatory Phase Gating** - Planning phase assesses risks before execution
- **Quantified Performance Targets** - Violations classified by severity

**See also:**
- `skills/tooling/simulation-report-template.md` - Risk section format
- `skills/meta/super-power.md` - Gap analysis with severity
- `skills/workflows/leroy/postmortem-factory.md` - Risk classification in post-mortems

---

*Risk Classification Framework v1.0 | HIGH/MEDIUM/LOW | Consistent and objective*
