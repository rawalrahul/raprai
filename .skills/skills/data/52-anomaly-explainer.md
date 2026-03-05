---
name: anomaly-explainer
description: "Detect and explain data anomalies using statistical methods (Z-score, IQR, isolation forest). Generate root cause hypotheses and quantify business impact."
category: data
difficulty: advanced
model_boost: "Weak model flags spurious anomalies or misses real issues without investigation"
---

# Anomaly Explainer

## Purpose
Anomalies—unusual data points or trends—can signal real problems (data errors, system failures, user behavior changes) or measurement noise. This skill systematizes anomaly detection and investigation, distinguishing signal from noise and quantifying business impact. The output is a documented anomaly report with likely causes and recommended actions.

## When to Use
- Monitoring dashboards for unexpected changes
- Investigating unusual metric movements (revenue drop, spike in errors)
- Detecting data quality issues (sudden null rate increase, duplicate surge)
- Identifying user behavior shifts (traffic pattern changes, churn spikes)
- **Do NOT use when**: Expected seasonal variation, or changes are explained and acceptable

## Instructions

### Step 1: Define Baseline and Anomaly Thresholds
Establish normal behavior to detect deviations:

**Baseline calculation:**

```python
import numpy as np
from scipy import stats

def calculate_baseline(historical_data, window_days=30):
    """
    Calculate normal range for metric from historical data.
    Handles seasonality and trend.
    """
    # APPROACH 1: Simple statistics (quick, assumes normal distribution)
    baseline_mean = np.mean(historical_data)
    baseline_std = np.std(historical_data)

    # Define normal range (±1.96 SD = 95% of normal distribution)
    normal_min = baseline_mean - 1.96 * baseline_std
    normal_max = baseline_mean + 1.96 * baseline_std

    print(f"Baseline: {baseline_mean:.0f} (±{1.96*baseline_std:.0f}, 95% confidence)")
    return baseline_mean, normal_min, normal_max

    # APPROACH 2: Percentile-based (robust to outliers)
    baseline_median = np.percentile(historical_data, 50)
    baseline_q1 = np.percentile(historical_data, 25)
    baseline_q3 = np.percentile(historical_data, 75)
    iqr = baseline_q3 - baseline_q1

    # Define normal range (IQR ±1.5)
    normal_min = baseline_q1 - 1.5 * iqr
    normal_max = baseline_q3 + 1.5 * iqr

    print(f"Baseline: {baseline_median:.0f} (IQR={iqr:.0f})")
    return baseline_median, normal_min, normal_max

    # APPROACH 3: Accounting for seasonality (time-series)
    # If metric has weekly pattern (weekdays higher than weekends):
    from statsmodels.tsa.seasonal import seasonal_decompose

    decomposition = seasonal_decompose(historical_data, period=7)  # 7-day seasonality
    trend = decomposition.trend
    seasonal = decomposition.seasonal
    residual = decomposition.resid

    # Baseline = trend + seasonal component
    baseline = trend + seasonal

    # Normal range = ±2 SD of residual (what remains after trend/seasonality)
    residual_std = np.std(residual)
    normal_min = baseline - 2 * residual_std
    normal_max = baseline + 2 * residual_std

    return baseline, normal_min, normal_max

# EXAMPLE: Customer signups baseline
signup_history = [450, 485, 520, 510, 495,  # Week 1
                  460, 475, 510, 520, 530,  # Week 2
                  480, 495, 525, 535, 550]  # Week 3

baseline, normal_min, normal_max = calculate_baseline(signup_history)
# Baseline: 500, normal range: [330, 670] (±170)

# THRESHOLD SELECTION TIPS:
# ├─ Standard deviation ±1: Catches 68% of normal variation (too sensitive)
# ├─ Standard deviation ±2: Catches 95% (good balance)
# ├─ Standard deviation ±3: Catches 99.7% (misses only extreme)
# ├─ IQR ±1.5: Catches ~95% (robust to outliers)
# └─ Business threshold: Deviation that matters (e.g., 10% below baseline)
```

**Seasonality considerations:**

```python
# ISSUE: Metric has natural variation by day/week/season
# Example: Website traffic lower on weekends, higher on weekdays
# Problem: Simple baseline treats all days the same
# Solution: Adjust baseline by day-of-week or season

import pandas as pd

# Daily data with day of week
df = pd.DataFrame({
    'date': pd.date_range('2026-01-01', periods=90, freq='D'),
    'signups': [...]  # 90 days of signup data
})

df['day_of_week'] = df['date'].dt.day_name()

# Calculate baseline separately for each day of week
baseline_by_dow = df.groupby('day_of_week')['signups'].agg(['mean', 'std'])

# Monday baseline: 500±50
# Tuesday baseline: 520±45
# Saturday baseline: 350±40 (weekend lower)

# Compare today's signups to same day-of-week baseline
today = 360  # Saturday signup count
saturday_baseline = 350
saturday_std = 40
z_score = (today - saturday_baseline) / saturday_std  # (360-350)/40 = 0.25

# Interpretation: Saturday signup is 0.25 SD above normal (within expected variation)
# If Z-score < 2: Normal
# If Z-score 2-3: Unusual
# If Z-score > 3: Highly anomalous
```

### Step 2: Implement Statistical Detection Methods
Use appropriate algorithms to identify anomalies:

**Detection method comparison:**

```python
import numpy as np
from scipy import stats
from sklearn.ensemble import IsolationForest

# DATA: Daily metrics (30 days)
data = np.array([100, 102, 98, 105, 99, 101, 103, 97, 104, 100,
                 102, 99, 101, 98, 103, 100, 99, 102, 500, 101,  # Day 19: spike!
                 100, 98, 101, 99, 102, 100, 103, 99, 101, 100])

# METHOD 1: Z-SCORE (Statistical, assumes normal distribution)
z_scores = np.abs(stats.zscore(data))
anomalies_zscore = np.where(z_scores > 3)[0]  # Points > 3 SD away

print(f"Z-score anomalies: {anomalies_zscore}")
# Output: [18] (day 19 has value 500, extremely high)

# Interpretation:
# Z-score = (value - mean) / std
# For data point 500: z = (500 - 101.5) / 50 = 7.97 SD away!
# Highly anomalous (>3 SD indicates real outlier)

# METHOD 2: IQR (Interquartile Range, distribution-free)
Q1 = np.percentile(data, 25)
Q3 = np.percentile(data, 75)
IQR = Q3 - Q1
lower_bound = Q1 - 1.5 * IQR
upper_bound = Q3 + 1.5 * IQR

anomalies_iqr = np.where((data < lower_bound) | (data > upper_bound))[0]

print(f"IQR anomalies: {anomalies_iqr}")
# Output: [18] (day 19: value 500 exceeds upper bound)

# Advantage: Robust to outliers (doesn't assume normal distribution)
# Better than Z-score if data is skewed

# METHOD 3: Isolation Forest (Machine learning, multivariate)
iso_forest = IsolationForest(contamination=0.1)  # Expect 10% anomalies
anomaly_labels = iso_forest.fit_predict(data.reshape(-1, 1))
anomalies_if = np.where(anomaly_labels == -1)[0]

print(f"Isolation Forest anomalies: {anomalies_if}")
# Output: [18] (identifies 500 as anomaly)

# Advantage: Works on multivariate data (multiple metrics at once)
# Can detect complex patterns, not just extreme values

# RECOMMENDATION:
# ├─ For univariate (single metric): Use IQR
# ├─ For multivariate (multiple metrics): Use Isolation Forest
# └─ For time-series (metrics over time): Seasonal decomposition
```

### Step 3: Investigate Root Causes
Analyze context to explain anomalies:

**Root cause analysis framework:**

```
ANOMALY DETECTED: Daily revenue drops 45% on March 5, 2026

STEP 1: Confirm anomaly is real (not measurement error)
├─ Data quality check: Raw data vs. warehouse
├─ Data freshness: When was data last updated?
├─ Lookups: Revenue includes refunds? Discounts? Reversals?
└─ Confirmation: Multiple data sources agree on drop

STEP 2: Check system logs and events
├─ Website/app outage: Was service unavailable 3/5?
├─ Deployment: Was code pushed 3/5? (feature broken?)
├─ Infrastructure: Database down? API slow?
├─ Marketing: Campaign ended? Email bounce? Paid ads paused?
└─ External: Major competitor launch? Regulatory change?

STEP 3: Segment analysis (find what changed)
├─ By geography: Drop in all regions or just one?
├─ By product: Drop in all products or specific one?
├─ By customer segment: Drop for all or subset?
├─ By traffic source: Drop from organic or paid or both?

# EXAMPLE: If drop only in US but not EU → Likely US-specific issue
# EXAMPLE: If drop only in Product A → Feature-related, not system-wide

STEP 4: Temporal analysis (when did it start/end?)
├─ What time of day did drop begin? (morning, evening?)
├─ How long did it last? (hours, full day, multi-day?)
├─ Did it recover? (quickly or gradually?)
└─ Has it happened before? (recurring or isolated?)

# EXAMPLE: If drop started at 2pm and lasted 3 hours → Likely event at 2pm
# EXAMPLE: If no recovery after 24 hours → Structural change, not temporary issue

STEP 5: Correlate with known events
├─ Marketing calendar: Campaigns launched/paused?
├─ Sales calendar: Special promotions? Discounts?
├─ Product calendar: Feature launches? Deprecations?
├─ External events: Holiday? Competitor news? Regulatory news?

# EXAMPLE: If March 5 is day 1 of sale → Expected drop due to inventory
# EXAMPLE: If March 5 follows Black Friday → Expected customer fatigue

STEP 6: Quantify impact and urgency
├─ What's the business impact? ($revenue lost, customers affected)
├─ How many customers impacted? (1% or 50%?)
├─ Is it ongoing? (temporary dip or permanent drop?)
├─ Can we recover the lost revenue? (one-time loss or recurring)

# IMPACT CALCULATION:
# Normal daily revenue: $100K
# March 5 revenue: $55K (45% drop)
# Impact: $45K lost revenue for that day
# If issue was 3-hour outage: Lost revenue recoverable elsewhere
# If issue is structural (users switched to competitor): Permanent loss
```

**Investigation example with real data:**

```python
import pandas as pd

# Load revenue data with context
df = pd.read_csv('daily_revenue.csv')
# Columns: date, revenue, region, product, traffic_source, notes

df['date'] = pd.to_datetime(df['date'])
df['pct_change'] = df['revenue'].pct_change()

# FIND ANOMALY
anomaly_date = df[df['pct_change'] < -0.4]  # 40%+ drop
print(anomaly_date)
# Output: 2026-03-05, $55K (was $100K), -45%

# INVESTIGATE BY SEGMENT
print(df[df['date'] == '2026-03-05'].groupby('region')['revenue'].sum())
# US: $22K (-50%)
# EU: $25K (-10%)
# APAC: $8K (-20%)
# Insight: US most impacted (likely US-specific issue)

print(df[df['date'] == '2026-03-05'].groupby('product')['revenue'].sum())
# Product A: $35K (-50%)
# Product B: $20K (-25%)
# Insight: Product A hit hardest (feature-related?)

print(df[df['date'] == '2026-03-05'].groupby('traffic_source')['revenue'].sum())
# Organic: $28K (-60%)
# Paid: $20K (-20%)
# Direct: $7K (no change)
# Insight: Organic traffic dropped most (SEO issue? Search algorithm change?)

# TEMPORAL ANALYSIS
hourly_data = pd.read_csv('hourly_revenue.csv')
hourly_data['date'] = pd.to_datetime(hourly_data['date'])
hourly_on_3_5 = hourly_data[hourly_data['date'].dt.date == date(2026, 3, 5)]

print(hourly_on_3_5[['hour', 'revenue', 'hourly_pct_change']])
# 1am: $3.5K (normal)
# 2am: $4.1K (normal)
# ...
# 2pm: $1.8K (sudden drop!)
# 3pm: $2.0K (stays low)
# ...
# 11pm: $2.2K (no recovery)
# Insight: Drop started exactly at 2pm, never recovered

# ROOT CAUSE HYPOTHESIS
# Time: Drop started 2pm March 5
# Scope: Organic traffic, US region, Product A most impacted
# Pattern: No recovery through end of day

# Check deployment log around 2pm March 5
# → YES: Code deployment at 1:58pm
# Change: Product A search ranking algorithm updated
# Issue: Algorithm bugged, de-indexed Product A, dropped search visibility

# CONFIRMED ROOT CAUSE: Broken code deployment at 2pm, de-indexed Product A
```

### Step 4: Calculate Impact and Severity
Quantify business consequences:

**Impact assessment:**

```
ANOMALY: Revenue drop 45% on March 5, 2026 (3-hour outage)

IMMEDIATE IMPACT:
- Lost revenue: $45K (one-time, for March 5)
- Affected customers: 2,000 (those who would have converted)
- Recovery: Possible (customers may retry, make up lost revenue)

INTERMEDIATE IMPACT (next 7 days):
- Churn: 50 customers (those with bad experience) = $50K LTV loss
- Brand damage: Low (lasted only 3 hours)
- Reputation: Minimal (not publicly visible outage)

LONG-TERM IMPACT:
- If root cause not fixed: Recurring $45K/day loss (recurring pattern)
- If permanent damage to search ranking: $50K/month ongoing loss
- Customer satisfaction: NPS drop -2 points (estimated, from support tickets)

SEVERITY ASSESSMENT:
Severity = Impact × Probability × Duration

Probability: Outage confirmed (100%), root cause identified
Duration: 3-hour incident, now resolved
Impact: $45K one-time loss

Overall severity: Medium (recoverable, one-time loss, issue resolved)

ACTION: Monitor revenue for next 7 days to confirm recovery,
        check search rankings to confirm Product A visibility restored,
        implement monitoring to prevent future 2pm-initiated deployments
```

### Step 5: Create Anomaly Report
Document findings and actions for stakeholders:

**Anomaly report template:**

```markdown
# Anomaly Report: March 5, 2026 Revenue Drop

**Date Detected**: 2026-03-05 @ 2:15pm UTC
**Anomaly**: Daily revenue dropped 45% ($45K loss)
**Status**: RESOLVED (2:00pm-5:00pm UTC outage window)

## Summary
Revenue dropped from $100K (normal) to $55K on March 5.
Outage was 3 hours, limited to organic traffic searching for Product A.
Root cause: Code deployment bug at 2:00pm UTC.

## Timeline
- 2:00pm: Code deployed (Product A search ranking algorithm update)
- 2:15pm: Revenue monitoring alert triggered (threshold breach)
- 2:30pm: Investigation began, deployment identified
- 3:15pm: Rollback deployed, service recovered
- 5:00pm: Revenue returned to normal levels

## Impact
- Revenue loss: $45K (March 5 only)
- Customers affected: 2,000 (who didn't convert during outage)
- Churn: 50 customers (poor experience, switched to competitor)
- Search visibility: Product A de-indexed from Google (temporary)

## Root Cause
Code deployment at 2:00pm included bug in search algorithm that
caused Product A to be incorrectly ranked low. Resulted in:
- Organic search traffic dropped 60% (users couldn't find product)
- Product A revenue dropped 50% (most dependent on search)
- US region most impacted (largest search user base)

## Prevention
1. Add integration test for search algorithm ranking (catch bugs pre-deployment)
2. Implement canary deployment (roll out to 5% of users first)
3. Create search ranking monitoring (alert if rankings shift >10%)
4. Avoid 2pm UTC deployments (peak traffic time in US)

## Recovery
- Rollback completed at 3:15pm (automatic roll-forward)
- Product A search visibility restored by 5:00pm
- Expected recovery: 80% of lost revenue through next week
- Churn impact: Monitor NPS and support sentiment for 30 days

## Owner
VP Engineering (deployment process improvement)
VP Analytics (monitoring/alerting upgrades)

**Next Review**: March 12, 2026 (confirm full recovery)
```

## Output Template

**Anomaly Detection & Analysis Report:**
```
Metric: [Daily revenue, error rate, churn, etc.]
Anomaly detected: [Date, magnitude, direction (up/down)]
Anomaly type: [One-time spike, trend shift, recurring pattern]

Root cause: [What changed: deployment, event, external, unknown]
Business impact: [$revenue, # customers, time to recover]
Severity: [Critical/High/Medium/Low]

Detection method: [Z-score, IQR, Isolation Forest, statistical]
Confirmation: [Verified across multiple data sources]

Actions taken: [Rollback, alert, investigation, escalation]
Prevention: [Monitoring, testing, process improvements]
```

## Quality Gates

1. **Anomaly confirmed real**: Cross-checked against multiple data sources
2. **Root cause identified or hypothesized**: Plausible explanation with evidence
3. **Business impact quantified**: Monetary or customer impact calculated
4. **Severity assessed**: Relative importance for prioritization
5. **Action plan documented**: What happens next, who owns it, timeline
6. **False positives eliminated**: Explanation for why this seems anomalous

## Examples

**Good: Detected, investigated, root cause found**
```
Anomaly: Error rate spiked 10x (0.1% → 1%) at 3am UTC
Detection: Isolation Forest on 30-day history
Investigation: Check logs → Database query timeout at 2:59am
Root cause: Nightly batch job consuming 100% CPU, database locked
Impact: 0.5% of requests failed, 50 customers had degraded experience
Recovery: Job tuned to run in off-peak hours
Prevention: Add resource monitoring, alert on CPU usage >80%
```

**Bad: Anomaly flagged but not investigated**
```
"Revenue was lower than usual on March 5"
Issues: No magnitude stated, no root cause investigated,
        no action taken, could be seasonal/expected
```

## Common Mistakes

1. **False positives from expected seasonality**: Weekend traffic lower than weekday (not anomalous)
2. **Flagging every deviation**: Setting threshold so sensitive that noise triggers alerts
3. **No root cause investigation**: Calling something "anomalous" without explaining why
4. **Ignoring context**: Anomaly on day 1 of sale (expected drop due to inventory)
5. **Over-reaction to harmless spikes**: Single user spike interpreted as system issue
6. **Missing real anomalies**: Threshold set so high that actual problems go undetected

## Anti-Patterns

1. **"Alert on anything > 5% change"**: Generates so many false positives, alerts ignored
2. **"We'll investigate if it happens again"**: By then, days of damage accumulated
3. **Seasonal data treated as normal**: Winter sales 20% lower (normal, not anomaly)
4. **No automated detection**: Manual monitoring, misses anomalies outside working hours
5. **Reactive-only approach**: Always investigating after impact, never preventing