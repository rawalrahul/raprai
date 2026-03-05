---
name: ab-test-designer
description: "Design rigorous A/B experiments with hypothesis definition, sample size calculation, randomization strategy, success metrics, guardrail metrics, and analysis plan."
category: data
difficulty: advanced
model_boost: "Weak model designs statistically flawed experiments or misinterprets results"
---

# A/B Test Designer

## Purpose
A/B testing is how modern companies validate decisions with statistical rigor before full rollout. This skill systematizes experiment design from hypothesis through analysis, ensuring tests are powered appropriately, metrics are well-chosen, and results are interpreted correctly. The output is a test specification that enables valid causal inference.

## When to Use
- Validating feature changes before full deployment
- Testing pricing strategies, UI changes, or algorithm modifications
- Measuring impact of marketing campaigns
- Optimizing conversion funnels
- **Do NOT use when**: Making changes with clear business rule logic, or past similar tests validated the change

## Instructions

### Step 1: Define Clear Hypothesis
Frame the test as a falsifiable prediction with mechanism:

**Good hypothesis structure:**
```
If we [change], then [users will do X] because [mechanism].

Example:
If we reduce checkout steps from 5 to 3,
then conversion rate will increase by ≥2 percentage points
because users won't abandon due to form fatigue.

Mechanism: Fewer steps = less cognitive load = higher completion.
Null hypothesis (H0): No difference in conversion rate
Alternative hypothesis (H1): Conversion rate increases ≥2 percentage points
```

**Poor vs. good hypotheses:**
```
POOR: "We want to increase revenue"
→ Not falsifiable, mechanism unclear, no success criterion

GOOD: "Personalizing product recommendations will increase AOV by $5+
because users will add related high-margin items to cart"
→ Falsifiable, mechanism clear, specific success criterion
```

**Consider unintended consequences:**
```
Hypothesis: Removing confirmation on checkout speeds completion
Intended effect: More orders (higher conversion)
Potential downside: More accidental orders, more refunds (lower profit)
→ Track both: conversion AND refund rate as guardrails
```

### Step 2: Select Primary and Guardrail Metrics
Choose metrics that demonstrate both intent and avoid harm:

**Primary metric criteria:**
- Directly measures hypothesis (if you don't move this, test failed)
- Causal link to business impact (not just a proxy)
- Moves relatively frequently (enough power in reasonable time)
- Not subject to seasonal effects (or controlled for seasonality)

```
Good primary metrics for various contexts:

Product feature:
- Engagement (DAU, session length, feature adoption)
- Retention (30-day retention rate)

Pricing change:
- Revenue per user (not raw volume, which may decrease)
- Conversion from free to paid

Marketing campaign:
- Click-through rate → Traffic (immediate)
- 30-day retention rate → Engagement (delayed, more meaningful)

Recommendation system:
- Click-through rate on recommendations
- Time to purchase from recommendation
- Return rate (quality proxy)
```

**Guardrail metrics (prevent shooting yourself):**
```
Changes to monitor for harm (even if primary metric improves):
- Server load / latency (feature change breaks performance)
- Error rate (new code introduces bugs)
- Cost (new feature drains resources)
- User satisfaction (even if metric increased, satisfaction dropped)
- Churn / retention (increase in one metric, loss of customers)

Example test:
Primary: Increase revenue per user
Guardrails:
  - Churn rate (ensure we didn't lose customers)
  - Support tickets (ensure frustration didn't spike)
  - Session time (ensure feature didn't break engagement)
```

**Avoid these metric mistakes:**
- Multiple primary metrics without clear weighting (increases false positives)
- Metrics with high natural variance (require very large sample sizes)
- Lagging metrics (7-day retention) mixed with immediate metrics (clickthrough)
  (If testing for user satisfaction, measure immediately; don't wait)

### Step 3: Calculate Sample Size
Determine how many users needed for statistical power:

**Sample size factors:**
```
n = 2 * [(z_α/2 + z_β) / (effect_size)]²

Where:
- z_α/2: Critical value for significance level (α=0.05 → z=1.96)
- z_β: Critical value for power level (β=0.2 → z=0.84 for 80% power)
- effect_size: (Δ / σ), difference in metric divided by standard deviation

Practical formula for comparing two proportions:
n = (1.96 + 0.84)² * [p1*(1-p1) + p2*(1-p2)] / (p1 - p2)²

For p1=0.15 (control), p2=0.17 (treatment, +2pp), 80% power:
n ≈ 8,000 users per group (16,000 total)
```

**Example calculation:**
```
Baseline conversion rate: 10%
Desired uplift: +1.5 percentage points (to 11.5%)
Statistical power: 80% (β=0.2)
Significance level: 5% (α=0.05)
Two-tailed test: Yes

Using online calculator or formula:
Sample size needed per group: 12,500 users
Total sample: 25,000 users

Interpretation:
With 25K users, 80% chance of detecting ≥1.5pp uplift if it exists.
If traffic is 10K/day: Test duration ≈ 2.5 days
If traffic is 1K/day: Test duration ≈ 25 days
```

**Sensitivity analysis:**
```
What if we only have 7 days to test?

Traffic: 10K/day → 70K users total
Hypothesis power calculation: What uplift can we detect?

With 70K users (35K per group) and 10% baseline:
Detectable effect: 0.7 percentage points (±0.7pp)
If true effect is 1.5pp, only 45% chance we'll detect it (underpowered)

Options:
1. Extend test to 10 days (capture 1.5pp with 80% power)
2. Roll out to high-traffic segment, test there (more users = more power)
3. Accept lower power (risk missing real effect)
4. Lower success threshold to 0.8pp (what can we detect with confidence)
```

### Step 4: Design Randomization and Assignment Strategy
Ensure unbiased, reproducible assignment:

```
RANDOMIZATION APPROACHES:

1. Simple Random Assigment (most common)
user_id HASH → random number [0, 1]
if hash < 0.5: Control group
else: Treatment group

Pros: Unbiased, independent
Cons: Slight imbalance possible (1000 users, might get 502/498 split)

2. Stratified Randomization
Users grouped by attribute (country, signup_cohort, device)
Within each stratum, randomly assign control/treatment
Result: Balanced on known variables, reduces variance

Pros: Increased power by controlling for strata
Cons: More complex, requires pre-specification

3. Block Randomization
Ensure exact balance: every Nth user gets control, then treatment
user_id mod 2: 0→Control, 1→Treatment

Pros: Perfect balance
Cons: Predictable (biased if assignment can be gamed)

4. Time-based Randomization (timestamp-based)
NOT RECOMMENDED: Sunday→Control, Monday→Treatment
Risk: Day-of-week effects confound treatment effect
Use case-by-case basis only when randomization impossible

RANDOMIZATION QUALITY CHECKS:
- Balance test: Control vs. treatment on key variables
  (age, geography, prior spending) - should show no significant difference
- Stability: Same user_id always gets same assignment (deterministic hash)
- Coverage: All users eligible for test get assigned
```

**Randomization unit strategy:**
```
What is your randomization unit?

By user (most common):
- Each user in test assigned control or treatment
- Appropriate for: Individual feature changes, UI updates
- Risk: User sees both versions during test (if test spans sessions)

By session:
- User could be in control session 1, treatment session 2
- Appropriate for: Testing banner copy, temporary changes
- Risk: Learning effects, user adaptation across sessions

By device:
- User on desktop gets control, mobile gets treatment
- Appropriate for: Mobile vs. desktop specific features
- Risk: Confounds device effects with treatment

CRITICAL: Declare unit before test starts
Changing unit mid-test biases results
```

### Step 5: Define Success Criteria and Decision Rules
Specify exactly when you'll call the test:

```
TEST STOPPING RULES:

Statistical Significance (primary):
- If p-value < 0.05 for primary metric AND
- All guardrail metrics show no harm (p > 0.05 or effect aligns with business)
- DECISION: Ship treatment

Practical Significance:
- If effect size < business threshold (e.g., <0.5pp revenue uplift)
- Even if statistically significant
- DECISION: Not worth shipping (engineering cost > benefit)

Guardrail Breach:
- If any guardrail metric worsens significantly (p < 0.05)
- DECISION: Ship control (revert treatment)
- Example: Conversion up +1.5pp but churn up +0.8pp → Reject

Time-based cutoff:
- Pre-specified test duration (e.g., 7 days, 2 weeks)
- Stop if: Duration reached AND sufficient statistical power
- DECISION: Call results, don't extend for "better" numbers

Sample size reached:
- Stop when calculated n is achieved (don't peek!)
- Reduces false positive rate
- DECISION: Analyze final results

DECISION EXAMPLES:

Test Results: Conversion +1.8pp (p=0.03), Churn +0.5pp (p=0.12)
Decision: Ship
Rationale: Primary uplift significant and practical, guardrail not harmed

Test Results: Conversion +0.3pp (p=0.04), Load time +200ms (p<0.01)
Decision: Reject/revert
Rationale: Practical lift too small, guardrail (performance) breached

Test Results: AOV +$2.15 (p=0.15, not significant), 7-day test complete
Decision: Continue or reject
→ If 80% power was 10 days: Continue 3 more days
→ If test was powered at 7 days: Reject (not enough evidence)
```

### Step 6: Plan Statistical Analysis and Interpretation
Design the analysis approach to prevent errors:

```
ANALYSIS APPROACH:

1. Intention-to-Treat (ITT):
Analyze all users as assigned, regardless of whether they saw treatment
Pro: Reflects real-world impact (some users don't get exposed)
Con: Dilutes effect if exposure isn't universal

2. Per-Protocol:
Analyze only users who actually received treatment
Pro: Measures treatment effect for exposed users
Con: Selection bias if non-compliance correlated with outcome

RECOMMENDATION: Report both, highlight ITT for policy decisions

STATISTICAL TEST SELECTION:

Metric Type → Statistical Test
Conversion rate (binomial) → Chi-square test or logistic regression
Revenue (continuous) → T-test or Mann-Whitney U (non-parametric)
Time-to-event → Survival analysis (Kaplan-Meier curves)
Count data → Poisson regression

For revenue (often right-skewed):
Test assumption: Normality
If violated: Use bootstrapped t-test or quantile regression

MULTIPLE COMPARISON CORRECTION:

If testing multiple metrics, false positive rate increases.
Bonferroni correction: Divide significance level by number of tests
(1 primary + 4 guardrails = 5 tests, α=0.05 → use α=0.01 per test)

OR
Pre-rank metrics by importance:
Primary: α=0.05
Guardrails: α=0.05 (stop if any breached)

SEGMENT ANALYSIS:

After detecting overall effect, analyze by segment:
Desktop vs. mobile (feature rendering differs)
New vs. existing users (onboarding effects)
High vs. low engagement (feature usage varies)

But DON'T:
- Hunt for segments post-hoc to justify shipping treatment
- Report the one segment where it worked, ignore where it failed
- Increase false positives

RULE: Segment analysis is exploratory, needs confirmation in next test
```

## Output Template

**Test Specification Document:**

```markdown
# A/B Test Specification: Checkout Button Color
**Hypothesis**: Changing primary button from blue to green will increase
conversion rate by 1.5pp because green conveys "go" / "approve" in Western cultures.

**Test Duration**: 7 days (sufficient for 80% power with 10K/day traffic)
**Sample Size**: 35,000 users per group (70,000 total)
**Launch Date**: 2026-03-10

## Randomization
Unit: User ID
Method: User ID hash mod 2 (control=0, treatment=1)
Balance check: Run t-test on user demographics (age, geography, signup_date)

## Metrics

| Metric | Type | Baseline | Target Change | Why |
|--------|------|----------|----------------|-----|
| Conversion Rate | Primary | 10.2% | +1.5pp (11.7%) | Measures checkout completion |
| Refund Rate | Guardrail | 3.1% | No change (±0.5pp) | Ensure no increase in buyer's remorse |
| Page Load Time | Guardrail | 1.2s | <1.5s | Ensure visual change didn't break performance |

## Statistical Power
Power: 80%
Significance: 5% two-tailed
Test: Chi-square for proportions
Sample size formula: n = 2 * [(1.96 + 0.84) / 0.03]² * 0.10 * 0.90 ≈ 17,500 per group

## Success Criteria
- SHIP if: Conversion ≥11.7% (1.5pp uplift) with p<0.05 AND refund rate unchanged
- REJECT if: Refund rate >3.6% (guardrail breach) OR conversion uplift <1.5pp
- EXTEND if: Reached time limit, inconclusive results

## Analysis Plan
1. ITT analysis on all assigned users
2. Chi-square test for conversion rate
3. Report 95% confidence intervals for all metrics
4. Segment analysis: Desktop vs. mobile (exploratory)
5. Timeline: Results ready 7 days after start
```

## Quality Gates

1. **Powered appropriately**: Sample size calculated for specified effect size and power
2. **Metric clarity**: Primary and guardrails clearly defined with no ambiguity
3. **Randomization validity**: Stratified or simple random, unit declared upfront
4. **No peeking**: Analysis plan specifies single stopping rule (not multiple interim looks)
5. **Decision rules explicit**: Exactly what results trigger ship/reject/extend decisions
6. **Conflict of interest acknowledged**: Who wins if treatment ships? (builds in bias awareness)

## Examples

**Good: Well-powered, clear hypothesis**
```
Hypothesis: Offer free shipping threshold of $50 will increase AOV
by $12+ because users will add items to reach threshold.

N=50K (25K per group), 90% power to detect $12 uplift
Primary: AOV (expected: $150 control, $162+ treatment)
Guardrails: Margin per order, customer satisfaction
Duration: 10 days (sufficient traffic)
Decision rule: Ship if AOV uplift >$12 (p<0.05) and margin held
```

**Bad: Underpowered, vague hypothesis**
```
Hypothesis: "Improve user engagement"

Metrics: Session length, DAU, clicks (too many)
Sample: "Run for one week and see"
Decision: "If any metric improves, ship"
Issues: Underpowered, multiple comparisons inflate false positives,
no guardrails, vague success criterion
```

## Common Mistakes

1. **Peeking and stopping early**: Checking results daily, stopping when "significant"; inflates false positive rate to 25%+
2. **Chasing statistical significance**: Shipping 0.2pp uplift just because p<0.05; business impact too small
3. **Ignoring guardrails**: Conversion up 3pp but churn up 1pp; shipped anyway
4. **Wrong sample size**: Calculating n=500 per group when effect size is small; 10% power instead of 80%
5. **Post-hoc metrics**: Creating metric after test to justify shipping; guaranteed cherry-picking
6. **Asymmetric test design**: Control carefully monitored, treatment gets one measurement

## Anti-Patterns

1. **"Continuous A/B tests"**: Treating tests as ongoing monitoring; can't ship/revert, conflates time effects
2. **Multivariate testing without framework**: Testing 10 variations simultaneously; underpowered on each
3. **Local optimum trap**: Running 50 tests, shipping the winner; most are false positives
4. **Network effects ignored**: Testing feature that depends on network adoption; results don't generalize
5. **Cannibalization not measured**: Testing new feature, conversion up but cannibalizes existing revenue