# Scenario Matrix Design

**Version:** 1.0
**Type:** Workflow (Design Pattern)
**Purpose:** How to design comprehensive test scenarios from variable dimensions
**Last Updated:** 2026-01-18

---

## Pattern Overview

**What is a scenario matrix?**
A structured approach to generate test scenarios by combining variable dimensions systematically.

**Why use it?**
- Ensures comprehensive coverage (no gaps)
- Generates hundreds/thousands of scenarios automatically
- Makes edge cases visible upfront
- Enables parallel testing at scale
- Documents what was tested vs skipped

---

## Core Concept

### The Matrix

A scenario matrix has:
- **Variables (dimensions):** Factors that can change
- **Options (values):** Possible values for each variable
- **Scenarios (combinations):** Cross-product of all options

**Formula:**
```
Total Scenarios = Option1_count × Option2_count × ... × OptionN_count
```

**Example:**
```markdown
| Variable | Options |
|----------|---------|
| Deal Size | $0-50K, $50K-100K, $100K+ |
| Timeline | <30 days, >30 days |
| Source | Inbound, Outbound |

Total Scenarios: 3 × 2 × 2 = 12
```

**Generated scenarios:**
1. Deal Size: $0-50K, Timeline: <30d, Source: Inbound
2. Deal Size: $0-50K, Timeline: <30d, Source: Outbound
3. Deal Size: $0-50K, Timeline: >30d, Source: Inbound
4. Deal Size: $0-50K, Timeline: >30d, Source: Outbound
5. Deal Size: $50K-100K, Timeline: <30d, Source: Inbound
... (12 total)

---

## Design Process

### Step 1: Identify Variables
**Question:** What factors affect the system under test?

**Sources:**
- User stories ("As a user, I want to X when Y")
- System requirements ("System must handle A, B, C")
- Historical data (what varies in production?)
- Domain expertise (what's important in this domain?)

**Variable types:**
- **Input variables:** User inputs, API parameters, data attributes
- **State variables:** System state, configuration, environment
- **External variables:** Time, third-party APIs, user behavior

**Example (your CRM stage optimization):**
```markdown
Variables identified:
- Deal size (input variable)
- Deal timeline (state variable)
- Lead source (input variable)
- Stage configuration (system variable)
```

### Step 2: Define Options for Each Variable
**Question:** What are the meaningful values/ranges for each variable?

**Strategies:**
- **Boundary values:** Min, typical, max
- **Equivalence classes:** Group similar values
- **Historical distribution:** Values that appear in real data
- **Edge cases:** Null, empty, extreme values

**Example:**
```markdown
| Variable | Options | Rationale |
|----------|---------|-----------|
| Deal Size | $0-50K, $50K-100K, $100K+ | Boundary values from historical data |
| Timeline | <30 days, >30 days | Equivalence classes (short vs long) |
| Source | Inbound, Outbound | Complete enumeration (only 2 types) |
```

**Option count guidelines:**
- **2-3 options:** Binary choices or small enumerations
- **3-5 options:** Continuous ranges (split into classes)
- **>5 options:** Only if domain requires (e.g., US states = 50)

### Step 3: Calculate Scenario Count
**Question:** How many scenarios will this generate?

**Formula:**
```
Total = Var1_options × Var2_options × ... × VarN_options
```

**Scope check:**
| Total Scenarios | Feasibility | Agent Tier |
|-----------------|-------------|------------|
| 1-100 | Small - easily testable | Tier 1 (5 agents) |
| 101-1K | Medium - manageable | Tier 2 (12 agents) |
| 1K-10K | Large - needs optimization | Tier 3 (18 agents) |
| >10K | Very large - consider reducing | Tier 4 (20+ agents) |

**If too large (>10K):**
- Reduce options per variable
- Combine variables (e.g., "Deal Size + Timeline" → "Small Short", "Small Long", ...)
- Use sampling (test representative subset)
- Prioritize critical combinations

### Step 4: Add Edge Cases
**Question:** What unusual or extreme scenarios should we test?

**Edge case categories:**
1. **Boundary conditions:** Min/max values, limits, thresholds
2. **Null/empty values:** Missing data, optional fields unset
3. **Invalid inputs:** Malformed data, wrong types
4. **Rare combinations:** Unlikely but possible scenarios
5. **System limits:** Timeouts, quotas, concurrency

**Example:**
```markdown
Base scenarios: 12 (from matrix)

Edge cases to add:
1. Deal with $0 value (boundary)
2. Deal with no timeline set (null)
3. Deal from unknown source (invalid input)
4. Deal stuck >90 days (rare but critical)
5. Deal cycling between stages (rare pattern)

Total scenarios: 12 + 5 = 17
```

**Integration with prediction engine:**
```python
# Query prediction engine for edge cases
edge_cases = prediction_engine.suggest_edge_cases(
    simulation_type="stage_optimization",
    domain="crm",
    variables=["deal_size", "timeline", "source"]
)
# Returns: ["deals stuck >90 days", "cycling deals", ...]

# Add to scenario pool
scenarios.extend(edge_cases)
```

### Step 5: Validate Coverage
**Question:** Are we testing everything that matters?

**Coverage checklist:**
- [ ] All variable combinations represented
- [ ] All boundary values included
- [ ] All known edge cases included
- [ ] Critical paths prioritized (test first)
- [ ] Non-critical combinations documented as skipped (if scope reduced)

**Example coverage report:**
```markdown
## Coverage Analysis

**Matrix scenarios:** 12 of 12 (100%)
**Edge cases:** 5 identified, 5 included (100%)
**Skipped combinations:** 0

**Justification for skipped:** N/A (all combinations feasible)
```

---

## Advanced Techniques

### Technique 1: Combinatorial Reduction (Pairwise Testing)
**Use when:** Full matrix is too large (>10K scenarios)

**Concept:** Test all pairwise combinations of variables instead of full cross-product

**Reduction:**
```
Full matrix: N variables × M options each = M^N scenarios
Pairwise: ~M^2 × log(N) scenarios
```

**Example:**
```markdown
Full matrix: 5 variables × 4 options = 1024 scenarios
Pairwise: ~64 scenarios (94% reduction)
```

**Tools:**
- PICT (Pairwise Independent Combinatorial Testing)
- ACTS (Automated Combinatorial Testing for Software)

**Tradeoff:** Faster testing, but may miss bugs triggered by 3+ variable interactions

### Technique 2: Risk-Based Prioritization
**Use when:** Can't test all scenarios in time budget

**Process:**
1. Classify each scenario by risk (HIGH/MEDIUM/LOW)
2. Test HIGH risk scenarios first
3. Test MEDIUM if time permits
4. Skip LOW or defer to future tests

**Risk classification:**
```markdown
| Scenario ID | Variables | Risk | Justification |
|-------------|-----------|------|---------------|
| 1 | Large deal, short timeline, inbound | HIGH | High-value, time-sensitive |
| 2 | Small deal, long timeline, outbound | LOW | Low impact if fails |
```

### Technique 3: Sampling for Large Datasets
**Use when:** Testing with real data that has millions of records

**Strategies:**
- **Random sampling:** Select N records randomly (unbiased)
- **Stratified sampling:** Ensure each variable option represented proportionally
- **Systematic sampling:** Every Nth record (e.g., every 100th deal)

**Example:**
```markdown
Population: 50K deals in your CRM
Sample: 1K deals (2%)

Sampling strategy: Stratified
- $0-50K: 600 deals (60% of sample, matches 60% of population)
- $50K-100K: 300 deals (30%)
- $100K+: 100 deals (10%)
```

### Technique 4: Tiered Scenario Generation
**Use when:** Some scenarios are more important than others

**Tiers:**
1. **Tier 1 (Base):** Common workflows, happy path
2. **Tier 2 (Edge):** Boundary conditions, null values
3. **Tier 3 (Stress):** System limits, high concurrency

**Execution order:** Tier 1 → Tier 2 → Tier 3

**Example:**
```markdown
Tier 1 (Base): 12 scenarios - Test basic matrix combinations
Tier 2 (Edge): 5 scenarios - Test edge cases
Tier 3 (Stress): 3 scenarios - Test with 10K deals simultaneously

Total: 20 scenarios
```

---

## Integration with Super Power Framework

**Phase 0 (Planning):**
```markdown
## Scenario Matrix Design

**Step 1: Variables identified**
- Deal size
- Timeline
- Source

**Step 2: Options defined**
| Variable | Options |
|----------|---------|
| Deal Size | $0-50K, $50K-100K, $100K+ |
| Timeline | <30 days, >30 days |
| Source | Inbound, Outbound |

**Step 3: Scenario count**
Total: 3 × 2 × 2 = 12 base scenarios

**Step 4: Edge cases added**
- Deals stuck >90 days
- Cycling deals

Total scenarios: 14

**Step 5: Coverage validated**
- All matrix combinations: ✅
- Edge cases from prediction engine: ✅
- Feasibility: ✅ (Tier 1, 5 agents)
```

**Phase 1 (Scenario Generation):**
```python
import itertools

# Generate base scenarios from matrix
variables = {
    "deal_size": ["$0-50K", "$50K-100K", "$100K+"],
    "timeline": ["<30 days", ">30 days"],
    "source": ["Inbound", "Outbound"]
}

base_scenarios = []
for combination in itertools.product(*variables.values()):
    scenario = dict(zip(variables.keys(), combination))
    scenario["type"] = "base"
    base_scenarios.append(scenario)

# Add edge cases
edge_cases = [
    {"description": "Deals stuck >90 days", "type": "edge_case"},
    {"description": "Cycling deals", "type": "edge_case"}
]

all_scenarios = base_scenarios + edge_cases
# Total: 12 + 2 = 14 scenarios
```

---

## Examples

### Example 1: your CRM Stage Optimization
**Goal:** Test different stage configurations

**Matrix:**
```markdown
| Variable | Options |
|----------|---------|
| Stage Config | Current, Option A (3-split), Option B (2-split) |
| Deal Size Range | $0-50K, $50K-100K, $100K+ |

Total: 3 × 3 = 9 scenarios
```

**Edge cases:**
- Deals with no stage set (null)
- Deals stuck >90 days
- Deals cycling between stages

**Total scenarios:** 9 + 3 = 12

### Example 2: API Pagination Testing
**Goal:** Verify pagination works for all MCP tools

**Matrix:**
```markdown
| Variable | Options |
|----------|---------|
| MCP Tool | crm_tool, ticketing_tool, ... (10 tools) |
| Result Count | <max_page_size, =max_page_size, >max_page_size |
| Page Number | 1, 2, last |

Total: 10 × 3 × 3 = 90 scenarios
```

**Edge cases:**
- Empty result set (0 records)
- Exactly 1 record
- Max result set (quota limit)

**Total scenarios:** 90 + 3 = 93

**Reduction via pairwise:**
- Full matrix: 90 scenarios
- Pairwise: ~30 scenarios (67% reduction)
- Decision: Use pairwise, add edge cases manually

### Example 3: catalog Validation Testing
**Goal:** Test accessory detection logic

**Matrix:**
```markdown
| Variable | Options |
|----------|---------|
| Product Category | Cameras, Panels, Cables, Speakers, Misc |
| Accessory Type | Mounts, Power, Connectors, None |
| Quantity | 1, 5, 100 |

Total: 5 × 4 × 3 = 60 scenarios
```

**Edge cases:**
- Product with no category set
- Accessory quantity = 0
- Missing SKU in catalog

**Total scenarios:** 60 + 3 = 63

---

## Common Pitfalls

### ❌ Pitfall 1: Too Many Variables
**Problem:** 7+ variables create explosion of scenarios

**Example:**
```markdown
7 variables × 3 options each = 2,187 scenarios
```

**Impact:** Infeasible to test all combinations

**Solution:** Reduce to 3-5 critical variables, use pairwise for others

### ❌ Pitfall 2: Missing Edge Cases
**Problem:** Only testing matrix combinations, forgetting boundary/null/invalid

**Impact:** Bugs discovered in production at edge cases

**Solution:** Always add Step 4 (edge cases) to process

### ❌ Pitfall 3: All Combinations Equally Weighted
**Problem:** Testing rare scenarios same as common workflows

**Impact:** Wasted time on low-risk scenarios

**Solution:** Use risk-based prioritization (test HIGH risk first)

### ❌ Pitfall 4: No Coverage Validation
**Problem:** Skipping scenarios without documentation

**Impact:** Gaps in testing unknown

**Solution:** Always document skipped combinations with justification

---

## Checklist

**Before generating scenarios:**
- [ ] Variables identified (3-5 critical dimensions)
- [ ] Options defined for each variable (2-5 per variable)
- [ ] Scenario count calculated (feasible within time/agent budget?)
- [ ] Edge cases identified (prediction engine consulted)
- [ ] Coverage validated (all critical paths included)
- [ ] Risk prioritization applied (if needed)

---

## Related Patterns

**See also:**
- `skills/meta/super-power.md` - Phase 0 (Planning) uses scenario matrix design
- `skills/meta/simulation-testing-methodology.md` - Testing approach using matrices
- `skills/meta/risk-classification-framework.md` - Risk-based prioritization
- `skills/meta/mandatory-phase-gating.md` - Plan matrix during Phase 0

---

*Scenario Matrix Design v1.0 | Systematic coverage | No gaps*
