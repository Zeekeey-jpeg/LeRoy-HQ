# Background Agent Performance KPIs v1.0

**Purpose:** Standard metrics for measuring background agent effectiveness, quality, and value delivery.

**Applies to:** secretary, scout, planner, janitor, quick, and all future background agents

---

## KPI Framework

### Tier 1: Execution Metrics (Must-Have)

| KPI | Target | Measurement | Fail Threshold |
|-----|--------|-------------|----------------|
| **Response Time** | <5 min for simple tasks, <60 min for complex | Duration from spawn to completion | >2x target |
| **Task Completion** | 100% of assigned scope | All deliverables present | <100% |
| **Error Rate** | 0 unhandled exceptions | Errors in logs / total runs | >2% |
| **Coverage** | 100% of required events | Events tracked / events detected | <95% |
| **Deduplication** | 0 duplicate entries | Duplicates / total entries | >1% |

### Tier 2: Quality Metrics (Should-Have)

| KPI | Target | Measurement | Good Threshold |
|-----|--------|-------------|----------------|
| **Documentation Quality** | Complete, structured, actionable | Word count + structure score | >80/100 |
| **Cross-referencing** | 100% valid links | Valid refs / total refs | >95% |
| **Output Format** | Consistent with templates | Template adherence score | >90% |
| **Context Awareness** | Recognizes related work | Related items referenced / total related | >80% |
| **Actionability** | Clear next steps provided | Actionable items / total recommendations | >70% |

### Tier 3: Value-Add Metrics (Nice-to-Have)

| KPI | Target | Measurement | Exceptional Threshold |
|-----|--------|-------------|----------------------|
| **Proactive Enhancements** | 1+ beyond scope | Bonus deliverables created | 2+ |
| **Risk Identification** | Flags issues before they escalate | Issues flagged / issues that occurred | >80% |
| **Integration Quality** | Coordinates with other agents | Successful handoffs / total handoffs | >90% |
| **Executive Readiness** | Output usable without editing | Direct usage rate | >75% |
| **Efficiency Gains** | Saves manual work | Hours saved per run | >1 hour |

---

## Agent-Specific KPI Templates

### Secretary (Timeline Tracking, Legal Coordination)

**Primary KPIs:**
- **Event Coverage:** 100% of trackable events logged (emails sent, docs signed, meetings scheduled)
- **Timeline Accuracy:** 100% correct timestamps and event sequencing
- **Deduplication:** 0 duplicate timeline entries
- **Legal Coordination:** 100% of legal triggers detected and coordinated
- **Morning Briefing Quality:** Usable without editing (>90%)

**Secondary KPIs:**
- **Decision Record Quality:** Complete context, rationale, consequences (>80/100)
- **Cross-Agent Coordination:** Successful handoffs to legal agent (>95%)
- **Client Context Integration:** Client notes referenced when relevant (>80%)

**Value-Add KPIs:**
- **Proactive Documentation:** Creates decision records without being asked
- **Executive Summaries:** Morning briefing auto-generated
- **Risk Flags:** Identifies contract conflicts, deadline risks

**Measurement Example (Secretary 2026-02-07):**
```yaml
execution_metrics:
  response_time: 60min (complex task - ACCEPTABLE)
  task_completion: 100% (8/8 events tracked)
  error_rate: 0%
  coverage: 100% (8/8 events)
  deduplication: 100% (0 duplicates)

quality_metrics:
  documentation_quality: 95/100 (13,400 words, structured)
  cross_referencing: 100% (all links valid)
  output_format: 100% (template adherence)
  context_awareness: 100% (all related work referenced)
  actionability: 90% (clear next steps)

value_add_metrics:
  proactive_enhancements: 4 (CTO/VP HR docs + briefing summary + legal check)
  risk_identification: 100% (legal conflicts checked)
  integration_quality: 100% (legal standby maintained)
  executive_readiness: 95% (usable without editing)
  efficiency_gains: 3+ hours saved

overall_rating: A+ (98/100)
```

---

### Scout (Pattern Detection, Growth Opportunities)

**Primary KPIs:**
- **Pattern Detection Rate:** Patterns detected / sessions monitored (target: >10%)
- **False Positive Rate:** Invalid patterns / total patterns (target: <10%)
- **Checkpoint Surfacing:** Surfaces at correct breakpoints (target: 100%)
- **Cross-Reference Compliance:** Checks existing skills before suggesting (target: 100%)
- **Growth Output Quality:** Actionable patterns with evidence (target: >80/100)

**Secondary KPIs:**
- **Skill Opportunity Quality:** Suggested skills have 3+ use cases (>80%)
- **Agent Opportunity Quality:** Suggested agents have clear role boundaries (>80%)
- **Pattern Evidence Quality:** Code references, line numbers, frequency data (>90%)

**Value-Add KPIs:**
- **Automation Potential Scoring:** Identifies high-ROI automation opportunities
- **Token Optimization:** Flags inefficient patterns costing tokens
- **Workflow Improvement:** Suggests process enhancements

**Measurement Example (Scout Session):**
```yaml
execution_metrics:
  response_time: 15min (background - GOOD)
  pattern_detection_rate: 15% (7 patterns / 1 session)
  false_positive_rate: 0%
  checkpoint_surfacing: 100%
  cross_reference_compliance: 100%

quality_metrics:
  growth_output_quality: 90/100 (7 patterns, all with evidence)
  skill_opportunity_quality: 85% (5/7 have 3+ use cases)
  agent_opportunity_quality: 80% (clear roles for 2 agents)
  pattern_evidence_quality: 95% (line numbers, frequency, code refs)

value_add_metrics:
  automation_potential: 3 high-ROI opportunities identified
  token_optimization: 2 inefficient patterns flagged
  workflow_improvement: 1 process enhancement suggested

overall_rating: A (92/100)
```

---

### Planner (Task Tracking, Auto-Completion)

**Primary KPIs:**
- **Task Parsing Accuracy:** Correct line items / total line items (target: >95%)
- **Priority Accuracy:** Priorities match urgency/importance (target: >90%)
- **Auto-Close Accuracy:** Correct auto-closes / total auto-closes (target: >90%)
- **Dependency Tracking:** Correct blocks/blockedBy relationships (target: 100%)
- **False Auto-Close Rate:** Incorrect auto-closes / total auto-closes (target: <5%)

**Secondary KPIs:**
- **Response Time:** Task list updated within 30s of detection (target: >90%)
- **Todo Output Quality:** Clear status, progress bars, next actions (target: >85/100)
- **Coordination Quality:** Handoffs to conductor, guardian, scout (target: >90%)

**Value-Add KPIs:**
- **Proactive Task Creation:** Detects implicit todos from conversation
- **Dependency Optimization:** Identifies and resolves blocking chains
- **Progress Visualization:** Generates useful progress reports

**Measurement Example (Planner Session):**
```yaml
execution_metrics:
  response_time: 12s (EXCELLENT)
  task_parsing_accuracy: 100% (15/15 line items)
  priority_accuracy: 93% (14/15 priorities correct)
  auto_close_accuracy: 90% (9/10 auto-closes correct)
  dependency_tracking: 100%
  false_auto_close_rate: 10% (1/10 incorrect)

quality_metrics:
  todo_output_quality: 88/100 (clear status, good formatting)
  coordination_quality: 95% (19/20 handoffs successful)

value_add_metrics:
  proactive_task_creation: 3 implicit todos detected
  dependency_optimization: 2 blocking chains resolved
  progress_visualization: 1 useful progress report generated

overall_rating: A- (89/100)
```

---

### Janitor (Cleanup Orchestration, System Maintenance)

**Primary KPIs:**
- **Scan Completeness:** 11/11 categories scanned (target: 100%)
- **Cleanup Score Accuracy:** Score matches actual cleanup need (target: ±5 points)
- **False Positive Rate:** Invalid cleanup candidates / total candidates (target: <10%)
- **Monday Trigger Reliability:** Auto-spawns on Mondays (target: 100%)
- **Background Execution:** No interruptions to main work (target: 100%)

**Secondary KPIs:**
- **Cleanup Recommendations:** Actionable suggestions (target: >80%)
- **Parallel Efficiency:** All 11 scans complete in <5 min (target: >90%)
- **State File Accuracy:** State updates correct (target: 100%)

**Value-Add KPIs:**
- **Proactive Maintenance:** Identifies issues before they cause problems
- **Automation Suggestions:** Proposes recurring cleanup automation
- **System Health Trends:** Tracks cleanup score over time

**Measurement Example (Janitor Monday Run):**
```yaml
execution_metrics:
  scan_completeness: 100% (11/11 categories)
  cleanup_score_accuracy: 98% (score 42, actual need 40)
  false_positive_rate: 5% (2/40 invalid candidates)
  monday_trigger_reliability: 100%
  background_execution: 100% (no interruptions)

quality_metrics:
  cleanup_recommendations: 85% (34/40 actionable)
  parallel_efficiency: 95% (4.2 min for all scans)
  state_file_accuracy: 100%

value_add_metrics:
  proactive_maintenance: 6 issues flagged before impact
  automation_suggestions: 2 recurring cleanup patterns identified
  system_health_trends: Score decreased from 52 to 42 (improving)

overall_rating: A (93/100)
```

---

### Quick (Trivial Query Handler, 100% Coverage)

**Primary KPIs:**
- **Response Time:** <10s for trivial queries (target: >95%)
- **Escalation Accuracy:** Correctly routes complex queries (target: >95%)
- **Coverage Rate:** Handles 100% of trivial requests (target: 100%)
- **Error Rate:** 0 unhandled queries (target: 0%)

**Secondary KPIs:**
- **Skill Routing Accuracy:** Routes to correct skill (target: >90%)
- **Status Check Quality:** Git status, file checks accurate (target: 100%)

**Value-Add KPIs:**
- **Triage Quality:** Correctly identifies trivial vs substantial
- **Quick Trigger Detection:** Recognizes trigger keywords

**Measurement Example (Quick Session):**
```yaml
execution_metrics:
  response_time: 8s avg (EXCELLENT)
  escalation_accuracy: 100% (12/12 correct)
  coverage_rate: 100% (handled all trivial requests)
  error_rate: 0%

quality_metrics:
  skill_routing_accuracy: 92% (11/12 correct routes)
  status_check_quality: 100% (accurate git status)

value_add_metrics:
  triage_quality: 100% (correctly identified all trivial vs substantial)
  quick_trigger_detection: 95% (19/20 triggers recognized)

overall_rating: A (95/100)
```

---

## Scoring Methodology

### Overall Rating Calculation

```
execution_score = avg(execution_metrics) × 0.50  (50% weight)
quality_score = avg(quality_metrics) × 0.30      (30% weight)
value_add_score = avg(value_add_metrics) × 0.20  (20% weight)

overall_score = execution_score + quality_score + value_add_score

Letter Grade:
  A+: 95-100
  A:  90-94
  A-: 85-89
  B+: 80-84
  B:  75-79
  B-: 70-74
  C:  60-69
  F:  <60
```

### Rating Thresholds

| Grade | Meaning | Action Required |
|-------|---------|-----------------|
| **A+ (95-100)** | Exceptional - exceeds all expectations | Document best practices, consider promoting patterns |
| **A (90-94)** | Excellent - meets all targets with room for improvement | Continue monitoring, minor optimizations |
| **A- (85-89)** | Good - meets most targets, some gaps | Identify improvement areas, address in next iteration |
| **B+ (80-84)** | Acceptable - meets minimum standards | Review underperforming metrics, plan improvements |
| **B (75-79)** | Below expectations - multiple gaps | Investigate root causes, implement corrections |
| **C (60-74)** | Needs improvement - significant issues | Review agent design, consider refactoring |
| **F (<60)** | Failing - not meeting basic requirements | Agent redesign required or retire agent |

---

## Measurement Frequency

| Agent | Measurement Frequency | Report Destination |
|-------|----------------------|-------------------|
| **secretary** | Per substantial task | `session/secretary-performance-{date}.md` |
| **scout** | Per session with patterns detected | `session/scout-performance-{date}.md` |
| **planner** | Weekly rollup | `session/planner-weekly-performance.md` |
| **janitor** | Per Monday run | `session/janitor-performance-{date}.md` |
| **quick** | Daily rollup | `session/quick-daily-performance.md` |

---

## Performance Dashboard Template

```markdown
# Background Agent Performance Dashboard
**Period:** {start_date} to {end_date}

## Summary

| Agent | Sessions | Avg Score | Grade | Trend |
|-------|----------|-----------|-------|-------|
| secretary | 12 | 96/100 | A+ | ↑ |
| scout | 8 | 91/100 | A | → |
| planner | 45 | 87/100 | A- | ↑ |
| janitor | 4 | 93/100 | A | → |
| quick | 156 | 94/100 | A | ↑ |

## Top Performers (This Period)

1. **secretary** - 96/100 (A+) - Exceptional documentation quality, proactive enhancements
2. **quick** - 94/100 (A) - Fast response times, accurate escalation
3. **janitor** - 93/100 (A) - Complete scans, proactive maintenance

## Areas for Improvement

1. **planner** - False auto-close rate 8% (target: <5%)
   - Action: Improve completion detection confidence threshold
2. **scout** - Pattern detection rate 8% (target: >10%)
   - Action: Enhance pattern recognition rules

## Notable Achievements

- **secretary**: Created 13,400 words of documentation in single session
- **quick**: 100% coverage rate maintained for 30 consecutive days
- **janitor**: System health score improved 10 points in 4 weeks

## Recommendations

1. Document secretary's best practices for other agents
2. Increase planner's completion detection threshold from 0.75 to 0.80
3. Add 3 new pattern recognition rules to scout based on recent misses
```

---

## Usage

**For New Background Agents:**
1. Copy relevant KPI template sections
2. Customize agent-specific metrics
3. Set baseline targets from first 5 runs
4. Adjust thresholds based on agent complexity

**For Measuring Existing Agents:**
1. Run agent and capture outputs
2. Score against KPI framework
3. Calculate overall rating
4. Document in performance report
5. Track trends over time

**For Performance Reviews:**
1. Compare current score to baseline
2. Identify top 3 strengths
3. Identify top 3 improvement areas
4. Create action plan for gaps
5. Review in 30 days

---

## Related Documentation

- `skills/meta/sub-agent-spawning.md` - Background agent architecture
- `skills/meta/protocol-enforcement.md` - Auto-spawn rules and priorities
- `agents/secretary.md` - Secretary agent specification
- `agents/scout.md` - Scout agent specification
- `agents/agent-quick.md` - Quick agent specification

---

*Background Agent Performance KPIs v1.0 | Standard metrics framework | Approved 2026-02-07*
