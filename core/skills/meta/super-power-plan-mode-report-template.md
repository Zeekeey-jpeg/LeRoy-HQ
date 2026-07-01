# Plan Mode Comparison Report Template

**Version:** 1.0
**Purpose:** Standard template for Plan Mode comparative analysis reports
**Used By:** `super-power-plan-mode.md` Phase 3
**Last Updated:** 2026-01-23

---

## Report Structure

**File Name:** `plan-comparison.md`
**Location:** `session/super_power/{YYYY-MM-DD}/`

---

## Template

```markdown
# Plan Mode Comparison Report

**Date:** {YYYY-MM-DD}T{HH:MM:SS}Z
**Problem:** {Original user request}
**Approaches Evaluated:** {N}
**Runtime:** {MM:SS}

---

## RECOMMENDED APPROACH

**Approach {ID}: {Name}**
- **Score:** {Score}/100 (Grade: {A/B/C/D/F})
- **Timeline:** {Duration}
- **Complexity:** {Low/Medium/High}
- **Risk:** {Low/Medium/High}
- **Resources:** {Summary}

**Why this approach wins:**
1. {Reason 1 - most compelling advantage}
2. {Reason 2 - quantified benefit if possible}
3. {Reason 3 - risk mitigation or future value}
4. {Reason 4 - technical merit}
5. {Reason 5 - alignment with constraints}

**Runner-Up:** {Approach name} scored {Score}/100
- Use if: {Condition when runner-up is better}
- Trade-off: {What you sacrifice}

---

## HEAD-TO-HEAD COMPARISON

| Approach | Timeline | Complexity | Risk | Resources | Extensibility | Score | Grade |
|----------|----------|------------|------|-----------|---------------|-------|-------|
| **{ID}. {Name}** | {Dur} | {L/M/H} | {L/M/H} | {Count} | {Score} | **{Total}** | {Grade} ✅ |
| {ID}. {Name} | {Dur} | {L/M/H} | {L/M/H} | {Count} | {Score} | {Total} | {Grade} ✅/⚠️/❌ |
| {ID}. {Name} | {Dur} | {L/M/H} | {L/M/H} | {Count} | {Score} | {Total} | {Grade} ✅/⚠️/❌ |
| {ID}. {Name} | {Dur} | {L/M/H} | {L/M/H} | {Count} | {Score} | {Total} | {Grade} ✅/⚠️/❌ |
| {ID}. {Name} | {Dur} | {L/M/H} | {L/M/H} | {Count} | {Score} | {Total} | {Grade} ✅/⚠️/❌ |

**Scoring Legend:**
- **Timeline:** Shorter = higher score (25% weight)
- **Complexity:** Lower = higher score (20% weight)
- **Risk:** Lower = higher score (30% weight)
- **Resources:** Fewer = higher score (15% weight)
- **Extensibility:** More extensible = higher score (10% weight)

**Grade Thresholds:**
| Score | Grade | Status |
|-------|-------|--------|
| 90-100 | A | Excellent - highly recommended ✅ |
| 80-89 | B | Good - solid choice ✅ |
| 70-79 | C | Acceptable - consider trade-offs ⚠️ |
| 60-69 | D | Risky - needs careful evaluation ⚠️ |
| <60 | F | Not recommended ❌ |

---

## KEY DIFFERENCES

### {Winner} vs {Runner-Up} (Top 2)
**{Winner} advantages:**
- {Advantage 1}
- {Advantage 2}
- {Advantage 3}

**{Runner-Up} advantages:**
- {Advantage 1}
- {Advantage 2}

**Decision point:** Choose {winner} if {condition}; choose {runner-up} if {condition}.

**Trade-off summary:**
{Winner} is {X}% faster but {Y}% more complex. Choose based on priority: speed vs simplicity.

---

### {Winner} vs {Approach 3}
**{Winner} advantages:**
- {Advantage 1}
- {Advantage 2}

**{Approach 3} limitations:**
- {Limitation 1}
- {Limitation 2}

**Decision point:** {Approach 3} only makes sense if {rare condition}.

---

### Why {Lowest Scoring Approach} Failed
- **Timeline:** {Duration} ({X}x longer than winner)
- **Complexity:** {High/Very High} ({specific complexity source})
- **Risk:** {High/Very High} ({specific risk factor})
- **Score:** {Score}/100 (Grade: {Grade})

**Critical issues:**
1. {Issue 1 - deal-breaker}
2. {Issue 2 - major concern}
3. {Issue 3 - compounding factor}

**Verdict:** Not recommended unless {extremely rare condition}.

---

## DETAILED BREAKDOWN

### Approach {Winner_ID}: {Winner_Name}

#### Implementation Phases

**Phase 1: {Phase Name} ({Duration})**
**Objective:** {What gets accomplished}

**Tasks:**
1. {Task 1}
   - Files: {files to create/modify}
   - Dependencies: {packages}
2. {Task 2}
   ...

**Deliverables:**
- {Deliverable 1}
- {Deliverable 2}

**Dependencies:** {What must complete first}

---

**Phase 2: {Phase Name} ({Duration})**
*(Repeat structure for each phase)*

---

**Phase N: {Phase Name} ({Duration})**
*(Repeat structure for each phase)*

---

**Total Timeline:** {Sum of all phases}

---

#### Resource Requirements

**Team:**
- {Role 1}: {Availability} (e.g., "1 developer, full-time for 2 weeks")
- {Role 2}: {Availability}

**Infrastructure:**
- {Service 1}: {Requirement} (e.g., "Supabase Pro tier")
- {Service 2}: {Requirement}

**Dependencies:**
| Package | Version | Purpose | Impact if Unavailable |
|---------|---------|---------|----------------------|
| {pkg1} | {ver} | {why} | {alternative or blocker} |
| {pkg2} | {ver} | {why} | {alternative or blocker} |

**Total Cost Estimate:** {If applicable}

---

#### Risk Assessment

| Risk | Likelihood | Impact | Mitigation | Owner |
|------|-----------|--------|------------|-------|
| {Risk 1} | High/Med/Low | High/Med/Low | {How to address} | {Role} |
| {Risk 2} | High/Med/Low | High/Med/Low | {How to address} | {Role} |

**Overall Risk Level:** {Low/Medium/High}

**Risk Score Calculation:**
```
Risk Score = (High_Impact_Risks × 3) + (Med_Impact_Risks × 2) + (Low_Impact_Risks × 1)
{Winner} Risk Score: {Score}
{Runner-Up} Risk Score: {Score}
```

---

#### Trade-offs

**Advantages:**
- {Pro 1 - quantified if possible}
- {Pro 2 - quantified if possible}
- {Pro 3 - quantified if possible}

**Disadvantages:**
- {Con 1 - quantified if possible}
- {Con 2 - quantified if possible}
- {Con 3 - quantified if possible}

**Net Benefit:** {Summary - e.g., "18% faster but 15% more complex"}

---

#### Success Metrics

| Metric | Target | Measurement Method | Threshold for Success |
|--------|--------|-------------------|----------------------|
| {Metric 1} | {Value} | {How to measure} | {Pass/fail criteria} |
| {Metric 2} | {Value} | {How to measure} | {Pass/fail criteria} |

**Monitoring Plan:**
- {How to track progress during implementation}
- {How to validate completion}

---

#### Testing Strategy

**Unit Tests:**
- {Component 1}: {Test count} tests ({scenarios})
- {Component 2}: {Test count} tests ({scenarios})

**Integration Tests:**
- {Integration point 1}: {Test count} tests ({scenarios})
- {Integration point 2}: {Test count} tests ({scenarios})

**E2E Tests:**
- {User flow 1}: {Test count} scenarios
- {User flow 2}: {Test count} scenarios

**Test Coverage Target:** {Percentage}

**Testing Timeline:** {Duration} (included in total timeline)

---

#### Rollback Plan

**If implementation fails:**
1. {Rollback step 1} (Time: {Duration})
2. {Rollback step 2} (Time: {Duration})
3. {Rollback step 3} (Time: {Duration})

**Total Rollback Time:** {Sum}

**Rollback Triggers:**
- {Condition 1 that triggers rollback}
- {Condition 2 that triggers rollback}

**Data Recovery:**
- {How to recover data if needed}
- {Backup requirements}

---

#### Future Extensibility

**This approach enables:**
- {Future enhancement 1} (Effort: {Low/Med/High})
- {Future enhancement 2} (Effort: {Low/Med/High})
- {Future enhancement 3} (Effort: {Low/Med/High})

**This approach blocks/complicates:**
- {Future limitation 1} (Workaround: {description})
- {Future limitation 2} (Workaround: {description})

**Extensibility Score:** {Score}/10

**Explanation:** {Why this score? What makes it extensible or not?}

---

#### Recommendation Confidence

**Confidence Level:** {Low/Medium/High} ({Percentage if quantifiable})

**Rationale:**
- {Factor supporting confidence}
- {Factor lowering confidence}
- {Unknowns that exist}

**Validation Needed:**
- [ ] {Unknown 1 - how to validate}
- [ ] {Unknown 2 - how to validate}

---

## RISKS & MITIGATION

### Shared Risks (All Approaches)

| Risk | Likelihood | Impact | Mitigation | Applies To |
|------|-----------|--------|------------|-----------|
| {Risk 1} | High/Med/Low | High/Med/Low | {How to address} | All approaches |
| {Risk 2} | High/Med/Low | High/Med/Low | {How to address} | All approaches |

---

### Approach-Specific Risks

#### {Winner}: Unique Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| {Risk 1} | High/Med/Low | High/Med/Low | {How to address} |
| {Risk 2} | High/Med/Low | High/Med/Low | {How to address} |

---

#### {Runner-Up}: Unique Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| {Risk 1} | High/Med/Low | High/Med/Low | {How to address} |
| {Risk 2} | High/Med/Low | High/Med/Low | {How to address} |

---

### Risk Comparison (Winner vs Runner-Up)

| Risk Category | {Winner} | {Runner-Up} | Advantage |
|--------------|---------|------------|-----------|
| Technical | {Score} | {Score} | {Who wins} |
| Resource | {Score} | {Score} | {Who wins} |
| Timeline | {Score} | {Score} | {Who wins} |
| External Dependencies | {Score} | {Score} | {Who wins} |

---

## EXECUTION SUMMARY

**Planning Completed:**
- Approaches evaluated: {N}
- Plans generated: {N}
- Planner agents spawned: {N}
- Runtime: {MM:SS}

**Safety Validation:**
- Safety violations: 0 ✅
- Blocked operations: {List if any}
- All operations: Read-only ✅

**Data Sources Used:**
- Internal code: {files read}
- External research: {WebSearch/WebFetch calls}
- MCP data: {if any}

---

## RECOMMENDATIONS

### Primary Recommendation: {Winner}

**Implement this approach if:**
- {Condition 1}
- {Condition 2}
- {Condition 3}

**Priority:** {High/Medium/Low}

**Timeline:** {Duration}

**Owner:** {Role/team}

**Next Steps:**
1. {First action to take}
2. {Second action to take}
3. {Third action to take}

---

### Alternative: {Runner-Up}

**Switch to this approach if:**
- {Condition 1 that changes decision}
- {Condition 2 that changes decision}

**What you sacrifice:**
- {Trade-off 1}
- {Trade-off 2}

**What you gain:**
- {Benefit 1}
- {Benefit 2}

---

### Not Recommended: {Failing Approach}

**Do NOT use this approach unless:**
- {Extremely rare condition}

**Why it failed:**
- {Critical issue 1}
- {Critical issue 2}

---

## DECISION MATRIX

Use this matrix to make final decision:

| Priority | Choose {Winner} if... | Choose {Runner-Up} if... |
|----------|---------------------|------------------------|
| **Speed** | You have {duration} | You need done in {shorter duration} |
| **Simplicity** | Team is experienced with {tech} | Team prefers simpler solution |
| **Risk Tolerance** | You can handle {risk level} | You need lowest risk |
| **Extensibility** | Future {feature} is planned | No future plans known |
| **Cost** | Budget allows {cost} | Budget is tight |

---

## MEMORY IMPACT

**Learnings Consolidated:**
- **Note 1:** {Pattern/Decision/Skill title}
  - Path: `memory/{folder}/{note-name}.md`
  - Tags: `{tag1}`, `{tag2}`, `{tag3}`
- **Note 2:** {Pattern/Decision/Skill title}
  - Path: `memory/{folder}/{note-name}.md`
  - Tags: `{tag1}`, `{tag2}`, `{tag3}`

**Wikilinks Created:** {Count} connections

**Knowledge Graph Hubs:**
- Connected to [[{Hub 1}]]
- Connected to [[{Hub 2}]]

**Email Notification:** Sent to {email} ✅

---

## NEXT STEPS

### If Proceeding with {Winner}

**Immediate Actions (Today):**
1. {Action 1}
2. {Action 2}

**Short Term (This Week):**
1. {Action 1}
2. {Action 2}

**Medium Term (This Sprint/Month):**
1. {Action 1}
2. {Action 2}

**Validation Points:**
- After Phase 1: {What to check}
- After Phase 2: {What to check}
- After Phase N: {What to check}

---

### If Switching to {Runner-Up}

**Why you might switch:**
- {Condition 1}
- {Condition 2}

**Adjustments needed:**
- {Change 1}
- {Change 2}

**New timeline:** {Duration}

---

### If Rejecting All Approaches

**Why you might reject all:**
- {Reason 1 - e.g., "Constraints changed"}
- {Reason 2 - e.g., "Problem redefined"}

**Next steps:**
1. Re-run Plan Mode with revised problem statement
2. Add more constraints or relax existing ones
3. Consult with stakeholders for priority clarification

---

## APPENDIX

### Plan Files
- Approach {ID}: `session/super_power/{date}/plan-{ID}.md`
- Approach {ID}: `session/super_power/{date}/plan-{ID}.md`
- *(Repeat for all approaches)*

### Approaches Manifest
- `session/super_power/{date}/approaches.jsonl`

### Execution Status
- `session/super_power/{date}/status.json`

### Safety Audit
- `session/super_power/{date}/audit.log` (0 violations ✅)

---

*Generated by Plan Mode v1.0 | Compare before committing | Informed decisions > blind implementation*
```

---

## Usage Notes

**When to use this template:**
- Phase 3 of Plan Mode (Comparative Analysis)
- After all planner agents complete
- Before presenting results to user

**Required sections:**
1. **Recommended Approach** - MUST identify clear winner
2. **Head-to-Head Comparison** - MUST include scoring table
3. **Key Differences** - MUST explain top 2-3 approaches
4. **Detailed Breakdown** - MUST provide full implementation plan for winner
5. **Risks & Mitigation** - MUST document risks for winner + runner-up
6. **Execution Summary** - MUST show planning metadata
7. **Recommendations** - MUST provide next steps

**Optional sections:**
- Decision Matrix (helpful for complex trade-offs)
- Appendix (useful for traceability)

**Formatting rules:**
- Use **bold** for approach names in comparisons
- Use ✅/⚠️/❌ icons for grades
- Use tables for structured data
- Use bullet lists for advantages/disadvantages
- Include quantified data whenever possible

---

## Scoring Calculation (Reference)

**Formula:**
```javascript
score = (timeline_score × 25%) +      // Faster = better
        (simplicity_score × 20%) +    // Simpler = better
        (risk_score × 30%) +          // Lower risk = better
        (resource_score × 15%) +      // Fewer resources = better
        (extensibility_score × 10%)   // More extensible = better
```

**Component Calculations:**
```javascript
// Timeline score (inverse - shorter is better)
timeline_score = (100 / duration_in_days) * 10

// Simplicity score (ordinal)
simplicity_score = {
  'low': 30,
  'medium': 20,
  'high': 10
}

// Risk score (ordinal - lower is better)
risk_score = {
  'low': 30,
  'medium': 20,
  'high': 10
}

// Resource score (inverse - fewer is better)
resource_score = (100 / resource_count) * 5

// Extensibility score (0-10 scale)
extensibility_score = count_future_enhancements * 10 / max_enhancements
```

---

## Quality Checklist

**Before presenting report, verify:**
- [ ] Recommended approach clearly identified
- [ ] Score calculations correct (verify math)
- [ ] Grade thresholds applied correctly
- [ ] Runner-up documented (if exists)
- [ ] Key differences section compares top 2-3
- [ ] Detailed breakdown includes ALL phases
- [ ] Risk assessment covers unique risks
- [ ] Next steps are actionable (not vague)
- [ ] Memory impact documented
- [ ] File paths in appendix are correct

---

*Report Template v1.0 | Structured analysis | Informed decision-making*
