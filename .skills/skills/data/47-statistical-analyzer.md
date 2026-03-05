---
name: statistical-analyzer
description: "Conduct rigorous statistical analysis: descriptive stats, hypothesis testing, regression, correlation. Validate assumptions, report effect sizes and confidence intervals."
category: data
difficulty: advanced
model_boost: "Weak model performs statistics incorrectly or misinterprets results"
---

# Statistical Analyzer

## Purpose
Statistical analysis translates raw data into defensible conclusions about populations, relationships, and causal effects. This skill systematizes the analysis process from descriptive statistics through hypothesis testing and regression, ensuring assumptions are checked, effect sizes are reported, and conclusions are justified. The output is statistically valid analysis with clearly interpreted results.

## When to Use
- Testing whether differences between groups are real or random chance
- Measuring strength of relationships between variables
- Predicting outcomes from input variables
- Validating A/B test results
- **Do NOT use when**: Purely descriptive analysis (tables, charts), or causal inference needed (use experiments)

## Instructions

### Step 1: Describe Data with Appropriate Statistics
Choose summary statistics that match data distribution and audience:

**Descriptive statistics selection:**

```
CONTINUOUS DATA (e.g., revenue, age, duration)

Normally distributed:
├─ Central tendency: Mean (μ)
├─ Spread: Standard deviation (σ)
├─ Range: Min, max, 95% confidence interval
└─ Visualization: Histogram with normal curve overlay

Skewed data (right-skewed: many small values, few large):
├─ Central tendency: Median (less affected by outliers)
├─ Spread: IQR (Q3 - Q1, robust to outliers)
├─ Range: 5th and 95th percentiles
└─ Visualization: Box plot or violin plot

Example:
Revenue: Mean=$2,450, Median=$1,800, SD=$6,200, IQR=$850-$3,400
Interpretation: Median more representative than mean (skewed by large orders)

CATEGORICAL DATA (e.g., status, country, segment)

Counts and proportions:
├─ Most common category (mode)
├─ Proportion in each category (%)
├─ Total unique categories
└─ Visualization: Bar chart or mosaic plot

Example:
Order Status Distribution:
  Completed: 85,420 (82.1%)
  Pending: 12,300 (11.8%)
  Cancelled: 6,280 (6.0%)
  Total: 104,000

CORRELATION / ASSOCIATION (between two variables)

Continuous-Continuous (Pearson correlation):
r = 0.72, p < 0.001, 95% CI [0.68, 0.76]
Interpretation: Strong positive correlation (r close to 1)
                High confidence (p < 0.001), small confidence interval

Categorical-Categorical (Cramér's V):
V = 0.15, p = 0.002
Interpretation: Weak but significant association

Continuous-Categorical (correlation ratio):
η = 0.38, p < 0.001
Interpretation: Moderate association (customer segment explains 14% of variance)
```

### Step 2: Check Statistical Assumptions
Verify conditions for tests are met:

**Assumption checking process:**

```python
import scipy.stats as stats
import numpy as np

# DATA: Customer ages
ages = [25, 32, 28, 45, 52, 41, 38, 55, 33, 29, ...]

# ASSUMPTION 1: Normality (required for t-test, ANOVA)
# Visual check
import matplotlib.pyplot as plt
plt.hist(ages, bins=20)
plt.show()  # Does distribution look bell-shaped?

# Statistical test
statistic, p_value = stats.shapiro(ages)
print(f"Shapiro-Wilk test p-value: {p_value}")
if p_value > 0.05:
    print("Data appears normally distributed")
else:
    print("Data significantly non-normal; use non-parametric test instead")

# ASSUMPTION 2: Homogeneity of variance (equal variance between groups)
# For comparing two groups (control vs. treatment)
control_revenue = [1000, 1200, 950, 1100, ...]
treatment_revenue = [1150, 1400, 1050, 1350, ...]

# Levene's test (robust to non-normality)
stat, p = stats.levene(control_revenue, treatment_revenue)
if p > 0.05:
    use_equal_var = True  # Use standard t-test
else:
    use_equal_var = False  # Use Welch's t-test (doesn't assume equal variance)

# ASSUMPTION 3: Independence (observations not related)
# Check: Each user counted once? No temporal autocorrelation?
# Durbin-Watson test for time series
from statsmodels.stats.stattools import durbin_watson
dw_statistic = durbin_watson(residuals)
# DW ~ 2: No autocorrelation
# DW < 2: Positive autocorrelation (concerning)

# INTERPRETATION:
# If assumptions violated:
# - Non-normal: Use Mann-Whitney U test instead of t-test
# - Unequal variance: Use Welch's t-test
# - Autocorrelated: Use time-series methods or cluster standard errors
```

### Step 3: Conduct Hypothesis Testing
Formalize tests with proper null hypotheses and significance levels:

**Hypothesis test design:**

```
QUESTION: "Did our price increase reduce orders?"

Step 1: Formalize hypothesis
Null hypothesis (H0): Price increase has no effect on order volume
Alternative hypothesis (H1): Price increase reduced order volume (one-tailed)

Step 2: Choose appropriate test
Data: Order volume before/after price change
Test: Paired t-test (same population, before/after)
Alternative: Wilcoxon signed-rank test (if data non-normal)

Step 3: Set significance level (α)
α = 0.05 (5% false positive rate acceptable)
Two-tailed vs. one-tailed: One-tailed (we predict direction: reduction)

Step 4: Calculate test statistic
Before price increase: mean order volume = 450/day, SD=45
After price increase: mean order volume = 425/day, SD=52
Difference: -25 orders/day
Test: t = (mean1 - mean2) / SE = -25 / 8.5 = -2.94

Step 5: Calculate p-value
p-value = 0.004 (probability of observing ≥2.94 SD difference by chance if H0 true)

Step 6: Interpret result
p = 0.004 < 0.05 → Reject null hypothesis
Conclusion: Price increase significantly reduced order volume (p=0.004)

Step 7: Report effect size
Cohen's d = (450 - 425) / 48 = 0.52 (medium effect size)
Interpretation: Order volume decreased by ~0.5 standard deviations
95% CI: [-38, -12] orders/day
Translation: We're 95% confident true effect is between -38 and -12 orders/day

CRITICAL: Don't report only p-value
Report: p-value + effect size + confidence interval
Wrong: "p = 0.004, so price increase hurt orders"
Right: "Price increase reduced orders by 25/day (95% CI: -38 to -12, p=0.004)"
```

### Step 4: Analyze Relationships with Correlation and Regression
Quantify and predict relationships between variables:

**Correlation analysis:**

```python
# QUESTION: "Does customer engagement predict retention?"

import pandas as pd
from scipy.stats import pearsonr, spearmanr

# Data
df = pd.read_csv('customers.csv')
# Columns: engagement_score (0-100), retained (0/1 at 12 months)

# METHOD 1: Pearson correlation (for linear relationships)
r, p = pearsonr(df['engagement_score'], df['retained'])
print(f"Pearson r = {r:.3f}, p-value = {p:.4f}")

# Output: r = 0.42, p < 0.001
# Interpretation: Moderate positive correlation (engagement → retention)
#                 Statistically significant (p < 0.001)

# METHOD 2: Spearman correlation (non-parametric, for ranks)
rho, p = spearmanr(df['engagement_score'], df['retained'])
# Use if data non-normal or relationship non-linear

# Visualization
import matplotlib.pyplot as plt
plt.scatter(df['engagement_score'], df['retained'], alpha=0.3)
plt.xlabel('Engagement Score')
plt.ylabel('Retained (1) vs. Churned (0)')
plt.title(f'Correlation: r = {r:.2f}, p < 0.001')
plt.show()

# INTERPRETATION GUIDE:
# r = 0.0-0.3: Weak correlation
# r = 0.3-0.7: Moderate correlation
# r = 0.7-1.0: Strong correlation
```

**Regression analysis:**

```python
# QUESTION: "How much does engagement increase retention probability?"

from sklearn.linear_model import LogisticRegression
from statsmodels.api import Logit, add_constant

# Data preparation
X = add_constant(df[['engagement_score']])  # Add intercept
y = df['retained']

# Fit logistic regression
model = Logit(y, X).fit()
print(model.summary())

# Output:
#                 coef    std err      z    P>|z|    [0.025    0.975]
# const          -2.456    0.187   -13.13   0.000   -2.822   -2.090
# engagement_score 0.0432  0.0021    20.57   0.000    0.0391   0.0473

# INTERPRETATION:
# Intercept (-2.456): Log-odds of retention when engagement=0
# Engagement coef (0.0432): Each 1-point increase in engagement
#                           increases log-odds by 0.0432
#                           → Odds ratio = exp(0.0432) = 1.044
#                           → 4.4% increase in odds of retention per point

# PRACTICAL TRANSLATION:
# Engagement 50 → 60: Odds of retention increase 4.4% * 10 = 44%
# If retention at engagement=50 is 60%, then at 60 it's ~87%

# Model quality
# Pseudo R-squared: 0.285 (engagement explains 28.5% of retention variance)
# McFadden's R² ≈ 0.1-0.4: Good fit for logistic regression

# Assumptions check
# ✓ No multicollinearity (VIF = 1.0, single predictor)
# ✓ Linear in log-odds (plot residuals vs. engagement score)
# ✓ Independence (each customer counted once)
```

### Step 5: Report Effect Sizes and Confidence Intervals
Quantify practical significance alongside statistical significance:

**Effect size interpretation:**

```
STATISTICAL SIGNIFICANCE: p-value (is effect real or random chance?)
PRACTICAL SIGNIFICANCE: Effect size (how big is the effect?)

Both matter. Example:

SCENARIO 1: Large sample, small effect
- Price increase decreases orders by 1/day (p = 0.02, significant)
- Effect size: Cohen's d = 0.1 (negligible)
- Decision: Statistically significant but practically trivial
         (engineering cost > revenue benefit)

SCENARIO 2: Small sample, large effect
- Training program increases productivity by 25% (p = 0.08, not significant)
- Effect size: Cohen's d = 1.2 (very large)
- Decision: Not statistically significant (need larger sample) but huge effect
         (run larger trial, likely to reach significance)

SCENARIO 3: Large sample, large effect
- Feature increases retention by 15 percentage points (p < 0.001, significant)
- Effect size: Cohen's h = 0.34 (medium)
- Decision: Ship! Both statistically and practically significant

EFFECT SIZE INTERPRETATION:

For proportions (e.g., conversion rate):
├─ Cohen's h (for 2 proportions)
│  ├─ h = 0.2: Small effect
│  ├─ h = 0.5: Medium effect
│  └─ h = 0.8: Large effect
└─ 1pp conversion uplift (from 5% to 6%) = 20% relative increase

For means (e.g., revenue):
├─ Cohen's d (standardized difference)
│  ├─ d = 0.2: Small effect
│  ├─ d = 0.5: Medium effect
│  └─ d = 0.8: Large effect
└─ Example: AOV increase $20 with SD=$50 → d = 0.4 (small-medium)

ALWAYS REPORT:
✓ Point estimate (mean difference)
✓ Effect size (Cohen's d, correlation r, etc.)
✓ 95% confidence interval
✓ P-value (optional if CI provided)

Example report (good):
"Revenue increased by $245 per customer (95% CI: $180-$310, Cohen's d=0.52,
p<0.001). This represents a medium-sized effect."

Example report (poor):
"Revenue increase is significant (p=0.001)."
→ Omits magnitude, direction, effect size, confidence interval
```

### Step 6: Validate and Present Findings
Document assumptions, limitations, and sensitivity to ensure valid inference:

```python
# VALIDATION CHECKLIST:

# 1. Assumptions satisfied?
✓ Normality: Shapiro-Wilk p = 0.15 (satisfied)
✓ Homogeneity: Levene's p = 0.42 (satisfied)
✓ Independence: Durbin-Watson = 2.1 (satisfied)

# 2. Sample size adequate?
Sample size: n = 5,000
Power analysis: Can detect 1pp effect at 90% power (good)
Risk: If true effect is 0.5pp, only 65% power (moderate)

# 3. Data quality checked?
✓ Missing values: <1% (acceptable)
✓ Outliers: 0.2% flagged, analyzed separately (minimal impact)
✓ Duplicates: None found (clean dataset)

# 4. Alternative explanations considered?
Finding: Engagement predicts retention (r = 0.42, p < 0.001)
Confound: Tenure might drive both (engaged users are tenure veterans)
Analysis: Partial correlation controlling for tenure = 0.38 (still strong)
Conclusion: Engagement effect remains after accounting for tenure

# 5. Generalizability assessed?
Sample: 10K U.S. customers, 2025 data
Limitation: Results may not generalize to non-U.S., or future periods
Recommendation: Validate findings on independent Q2 2026 data

# 6. Sensitivity analysis?
Base case: Engagement coefficient = 0.043
Sensitivity: If we exclude top 10% engagement (outliers), coef = 0.038 (robust)
Conclusion: Findings not driven by outliers
```

## Output Template

**Statistical Analysis Report:**

```markdown
# Analysis: Impact of Customer Engagement on Retention

## Hypothesis
Customer engagement (session frequency, feature adoption) predicts retention.

## Data
- Sample: 50,000 customers, 2025 data
- Engagement metric: Sessions/week in first 30 days
- Retention: Active after 12 months (1) or churned (0)

## Descriptive Statistics
Engagement: Mean=3.2 sessions/week, SD=1.8, IQR=[1.8, 4.5]
Retention: 72% retained, 28% churned

## Assumption Checks
- Normality: Shapiro-Wilk p = 0.08 (satisfied)
- Homogeneity: Levene's p = 0.34 (satisfied)

## Correlation
Pearson r = 0.42, p < 0.001, 95% CI [0.38, 0.46]
Interpretation: Moderate positive correlation, highly significant

## Regression
Logistic regression: Each additional session/week increases odds of
retention by 18% (OR = 1.18, p < 0.001)

## Effect Size
Cohen's h = 0.52 (medium effect)

## Sensitivity
Excluding top 10% engagement: r = 0.39 (robust to outliers)

## Conclusion
Engagement strongly predicts retention. Effect is statistically and
practically significant, and robust to alternative specifications.
```

## Quality Gates

1. **Assumptions validated**: Normality, homogeneity, independence checked explicitly
2. **Effect size reported**: Not just p-value; magnitude and direction clear
3. **Confidence intervals provided**: Range of plausible values documented
4. **Sample size adequate**: Power to detect effect of interest
5. **Sensitivity analysis conducted**: Results robust to specification changes
6. **Limitations acknowledged**: Generalizability, confounders discussed

## Examples

**Good: Rigorous, transparent**
```
A/B test results: Conversion 10.2% → 11.8% (+1.6pp, p=0.02)
Effect size: Cohen's h = 0.08 (small)
95% CI: [0.3pp, 2.9pp]
Power: 85% to detect 1.5pp effect
Assumption checks: ✓ All satisfied
Interpretation: Significant uplift, but smaller than target (target: 2pp).
Recommend: Continue to 1M samples to confirm or declare inconclusive.
```

**Bad: Opaque, incomplete**
```
"The test showed a significant improvement (p=0.02)."
Missing: Effect size, confidence interval, assumption checks,
sample size rationale, decision guidance
```

## Common Mistakes

1. **P-value only**: Reporting p=0.05 without effect size or CI; can't assess magnitude
2. **Wrong test selection**: Using t-test on non-normal data; should use Mann-Whitney U
3. **Ignoring assumptions**: Assuming normality without checking; test unreliable
4. **Multiple comparisons**: Testing 20 hypotheses with α=0.05; false positive rate 64%
5. **Confounding unmeasured**: Finding correlation but not controlling for confounders
6. **Reverse causality**: Finding correlation without establishing direction

## Anti-Patterns

1. **"Statistical significance = important"**: Ignoring that p<0.05 with large n is noise
2. **Hypothesis after seeing results**: Testing what data suggests, not what theory predicts
3. **Cherry-picking subgroups**: Finding segment where effect appears, reporting only that
4. **Ignoring violations**: Using t-test on severely skewed data anyway
5. **Extrapolating beyond data**: Sample is U.S., claiming results worldwide