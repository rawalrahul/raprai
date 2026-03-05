---
name: dashboard-designer
description: "Design executive dashboards with metric hierarchy, optimal visualization selection, and data-driven alert thresholds. Align KPI selection to business strategy."
category: data
difficulty: intermediate
model_boost: "Weak model creates dashboards without strategic intent or poor visualization choices"
---

# Dashboard Designer

## Purpose
Effective dashboards translate strategy into actionable insights by carefully selecting metrics, organizing them hierarchically, and visualizing them appropriately for the target audience. This skill systematizes dashboard design from business strategy through KPI selection, metric hierarchy, visualization selection, and alert threshold definition. The output is a dashboard specification ready for implementation.

## When to Use
- Creating executive dashboards for stakeholder reporting
- Designing operational dashboards for team monitoring
- Building self-service analytics for business users
- Establishing metric frameworks and hierarchies
- **Do NOT use when**: Ad-hoc exploratory analysis, or metrics not yet defined

## Instructions

### Step 1: Define Business Context and Audience
Align dashboard strategy with business objectives before selecting metrics:

**Audience analysis:**
```
Executive Dashboard (C-suite, Board)
- Frequency: Weekly/monthly
- Time spent: 5-10 minutes
- Questions: "Are we on track to goal?"
- Metrics: 4-6 high-level KPIs (revenue, margin, growth, churn)
- Depth: Avoid drilldown; support quick decision-making

Operational Dashboard (Team leads)
- Frequency: Daily
- Time spent: 15-30 minutes
- Questions: "What's broken? What needs action today?"
- Metrics: 15-25 operational metrics (funnel stages, queue lengths, error rates)
- Depth: Substantial drilldown, daily monitoring

Product Analytics (Product managers)
- Frequency: Continuous monitoring
- Time spent: 30+ minutes
- Questions: "How are users engaging? Is feature adoption on track?"
- Metrics: 30+ metrics (DAU, retention, feature adoption, cohort trends)
- Depth: Extensive drilldown, comparative analysis
```

**Business context mapping:**
```
Strategy: Increase revenue while maintaining unit economics
→ KPIs: Annual Recurring Revenue (ARR), Customer Acquisition Cost (CAC),
         Customer Lifetime Value (LTV), LTV/CAC ratio
→ Supporting metrics: New customers, churn rate, average contract value

Strategy: Improve customer retention
→ KPIs: Churn rate, retention cohort curves, NPS score
→ Supporting metrics: Engagement frequency, feature adoption, support ticket sentiment
```

### Step 2: Build Metric Hierarchy
Organize metrics from strategic to operational using a pyramid:

```
TIER 1: STRATEGIC KPIs (1-5 metrics)
- Annual Recurring Revenue (ARR): $50M
- Customer Churn Rate: 5% monthly
- Net Promoter Score: 42
- Unit Economics LTV/CAC: 3.2x
- Market Share: 12% (vs. competitors)

TIER 2: LEADING INDICATORS (5-10 metrics)
Show early signals of future performance
- Monthly Active Users: 500K
- Feature Adoption Rate: 68% (new feature adoption in 30 days)
- Free-to-Paid Conversion: 8.2%
- Support Ticket Resolution Time: 18 hours avg
- Sales Pipeline Stage Progression: $120M in stage 3/4

TIER 3: OPERATIONAL METRICS (10-20 metrics)
Enable daily monitoring and tactical decisions
- Daily Active Users: 125K
- Average Session Duration: 12 minutes
- Error Rate: 0.3%
- API Response Time: 150ms (p95)
- Sales team activity: 45 calls/day, 8 demos/day

TIER 4: DIAGNOSTIC METRICS (support tier 1-3)
Available via drilldown, not on main dashboard
- Revenue by customer segment
- Churn reasons (text feedback)
- Feature usage breakdown
- Geographic distribution
```

**Principle: MECE (Mutually Exclusive, Collectively Exhaustive)**
- Each metric measures something distinct (no overlap)
- Together they comprehensively cover the business
- Avoid duplicate reporting (don't show both "Revenue" and "ARR" simultaneously)

### Step 3: Select Visualization Types
Match visualization to the data story and audience cognitive load:

```
DATA STORY → VISUALIZATION CHOICE

"Is revenue growing?"
→ Line chart with trend (time series)
  Clear upward/downward trajectory
  Shows volatility vs. trend direction
  [AVOID: pie chart - can't show change over time]

"How is revenue distributed by segment?"
→ Stacked bar chart or grouped bar
  Segment comparison clear
  Stacking shows total while revealing parts
  [AVOID: donut chart - hard to compare segment sizes]

"Are we hitting weekly growth targets?"
→ Progress bar or bullet chart
  Shows completion % toward goal
  Visual metaphor intuitive for everyone
  [AVOID: gauge - too much whitespace]

"What's the funnel from signup to paying customer?"
→ Waterfall or funnel chart
  Shows drop-off at each stage
  Identifies conversion bottleneck
  [AVOID: line chart - can't show sequential loss]

"How does Q4 compare to Q1-Q3?"
→ Bar chart (grouped, not stacked)
  Direct numeric comparison easy
  Audience can rapidly estimate ratios
  [AVOID: area chart - stacking distorts comparison]

"Is this metric seasonal or growing?"
→ Line chart with same-period-last-year overlay
  Separates trend from seasonality
  [AVOID: simple line - can't distinguish]

"How does our metric compare to industry benchmark?"
→ Reference line + bar
  Audience sees gap instantly
  Benchmark provides context
  [AVOID: table - requires mental math]

"What percentage of users fall into each category?"
→ Pie chart (only if 3-4 slices) or horizontal bar
  [AVOID: pie charts entirely - humans poor at angle comparison]
```

**Visualization quality checklist:**
- Minimalist: No decoration, chartjunk, or ornamental 3D
- Accessible: High contrast, no red-green combos, readable font size
- Intuitive: Audience understands insight within 5 seconds
- Comparable: Similar metrics use same scale/color scheme

### Step 4: Define Alert Thresholds
Establish data-driven thresholds that trigger action:

```
TYPE 1: ABSOLUTE THRESHOLD (metric crosses boundary)

Daily Active Users
- Alert if: DAU < 100K (10% drop)
- Owner: Product lead
- Action: Investigate spike in errors or login issues
- Frequency: Real-time (automated alert)
- Severity: Critical (revenue impact)

Example threshold setting:
Baseline: 110K DAU (7-day average)
Threshold: 99K (10% below recent baseline)
→ Avoids noise from normal daily volatility
→ Detects real degradation

TYPE 2: TREND THRESHOLD (metric violates expected trend)

Revenue Growth Rate
- Expected: 4% month-over-month
- Alert if: Actual < 2% (missing half of expected growth)
- Owner: CFO
- Action: Revenue forecast review, pipeline analysis
- Frequency: Monthly
- Severity: High (business health)

TYPE 3: RATIO THRESHOLD (metric relationship breaks)

LTV/CAC Ratio
- Target: ≥3.0x (payback within 12 months)
- Alert if: <2.5x (headed below acceptable range)
- Owner: Finance + Sales
- Action: CAC reduction initiatives or LTV improvement projects
- Frequency: Quarterly
- Severity: High (long-term viability)

TYPE 4: TRAFFIC-LIGHT THRESHOLDS (multi-level)

Churn Rate
- Green: <4% monthly (healthy)
- Yellow: 4-5% (monitor, possible issues emerging)
- Red: >5% (critical investigation required)

NPS Score
- Green: ≥50 (excellent)
- Yellow: 40-49 (needs improvement)
- Red: <40 (crisis, customer satisfaction declining)
```

**Threshold calibration process:**

```python
# Historical analysis informs thresholds
# Don't guess; use data

import numpy as np

daily_active_users = [105000, 108000, 109000, 107000, 106000, 110000, 108000]
baseline_mean = np.mean(daily_active_users)  # 107,571
baseline_std = np.std(daily_active_users)     # 1,669

# Alert at -1.5 standard deviations (unusual but not rare)
threshold = baseline_mean - 1.5 * baseline_std  # 104,075

# Interpretation: Flag if DAU drops below 97th percentile of normal variation
```

### Step 5: Design Layout and Information Architecture
Organize dashboard for cognitive flow and quick scanning:

```
GRID-BASED LAYOUT (12-column grid, common in design tools)

Row 1 (Strategic Summary - 12 columns)
[ARR]     [Churn Rate]     [Retention %]     [NPS]     [LTV/CAC]

Row 2 (Monthly Performance - 12 columns)
[Revenue Chart (6)]     [Customer Breakdown (3)]     [Pipeline (3)]

Row 3 (Operational Trends - 12 columns)
[DAU Trend (4)]     [Conversion Funnel (4)]     [Error Rate (4)]

Row 4 (Deep Dives - Optional expandable section)
[Customer Cohort Analysis (6)]     [Feature Adoption (6)]

DESIGN PRINCIPLES:
- Top-left (highest attention): Most critical metric (ARR)
- Reading path: Left → Right, Top → Bottom
- Grouping: Related metrics adjacent (churn + retention together)
- Visual weight: Largest charts for most important stories
- White space: Breathing room, not cramped
- Consistency: Same color = same meaning across dashboard
```

**Color coding strategy:**
```
Primary metric: Brand color (blue) - identity
Positive trend: Green (#00B81C)
Negative trend: Red (#FF4444)
Neutral/baseline: Gray (#999999)
Target/benchmark: Black line or reference

Avoid:
- More than 4 colors in any single chart
- Red/green together (colorblind-unfriendly)
- Chart complexity requiring legend study
```

### Step 6: Add Interactivity and Filtering
Enable exploration while preventing confusion:

```
APPROPRIATE INTERACTIVITY:

Time Range Selector
- Default: Last 90 days (balances recency + trend visibility)
- Options: YTD, last 12 months, custom date range
- Applies to: All time-series charts simultaneously
- Benefit: Users see consistent view across dashboard

Segment Filter
- Options: Customer segment, geography, product, plan type
- Default: "All" (no filter) with count shown
- Multi-select or single-select?
  Single-select if segments are mutually exclusive
  Multi-select if analytical (want to compare)
- Applies to: Metrics sensitive to segment
- Benefit: Isolate performance for specific segments

AVOID OVER-INTERACTIVITY:

- Metric selector (hides KPI, confusing)
- Drill-through navigation (goes to detail dashboard instead)
- Drill-down within charts that changes the aggregation level
  (users lose context)
- Hover-to-reveal (hidden data seen only on hover; doesn't scale)
- Too many filter options (causes decision paralysis)

RULE: Every interactive element should have clear, specific purpose
```

## Output Template

**Dashboard Specification Document:**

```markdown
# Executive Revenue Dashboard
**Audience**: C-suite, Board of Directors
**Refresh Cadence**: Daily (updated 6am each day)
**Typical View Duration**: 5-10 minutes

## Metric Definitions

| Metric | Definition | Formula | Target | Owner |
|--------|-----------|---------|--------|-------|
| ARR | Annual Recurring Revenue from active contracts | SUM(contract_value) where status='active' | $50M | CFO |
| Churn Rate | % of customers lost month-over-month | Lost / Start of Period | <4% | VP Customer Success |
| NPS | Net Promoter Score (quarterly survey) | Promoters% - Detractors% | ≥50 | VP Product |

## Layout Specification

- Total Size: 1200px × 800px (2 screens of scrolling)
- Grid: 12-column, responsive to mobile
- Top row: 5 KPI cards (each 2.4 columns), high-level summary
- Middle rows: 2-3 charts, each 4-6 columns wide
- Bottom section: Expandable drilldown panels

## Alert Configuration

| Metric | Alert Condition | Action | Owner |
|--------|-----------------|--------|-------|
| ARR | <$47M (3% below target) | Review forecast, check large account risks | CFO |
| Churn | >5% monthly | Customer success intervention, call customers | VP CS |

## Visualization List

1. ARR: Line chart with rolling 12-month trend
2. Churn Rate: Line with min/max bands (normal variation)
3. Customer Cohort: Retention table (months since cohort acquisition)
4. Revenue by Segment: Stacked bar (YoY comparison)
```

## Quality Gates

1. **Audience alignment**: Every metric directly supports business strategy or decision-making
2. **Metric clarity**: Definitions documented, formulas testable, no ambiguity
3. **Visualization fit**: Each chart matches its data story (not decorative)
4. **Cognitive load**: <1 minute to extract key insights for primary audience
5. **Drill-down support**: Every summary metric linked to diagnostic detail
6. **Alert calibration**: All thresholds based on historical data or business rules

## Examples

**Good: Strategic alignment with clear thresholds**
```
Audience: VP Sales
Primary KPI: Monthly Recurring Revenue (MRR)
Supporting: Sales pipeline, conversion rate, average deal size, churn

Alert: MRR < 2% of monthly growth target
Action: Review sales cycle, investigate lost deals, coaching calls with reps

Design: MRR as primary card (top-left), pipeline chart (center),
segment breakdown (right), conversion funnel (bottom)
```

**Bad: Metrics without strategy, visual clutter**
```
20 metrics crammed into 4x5 grid of sparklines
Metrics: Page views, sessions, bounce rate, click-through, engagement,
SQL load time, database size, error count, ...
No clear audience or decision enabled
Colors inconsistent, some charts redundant
Thresholds arbitrary (0-100 scale) with no business meaning
```

## Common Mistakes

1. **Vanity metrics over impact metrics**: Tracking "users" instead of "paying users"; ignores revenue reality
2. **Too many metrics**: 50+ metrics on dashboard; audience picks wrong few to focus on
3. **No baseline for alerts**: Threshold set to "round number" (100K, 5%) not data-driven
4. **Inverted metric logic**: Showing "churn" on upward metric when "retention" is clearer
5. **Inconsistent refresh**: Some metrics daily, some weekly; confusing for stakeholders
6. **Hiding bad news**: Using color schemes that de-emphasize red metrics; prevents action

## Anti-Patterns

1. **"Show me everything"**: Combining strategic + operational on same dashboard; audiences can't agree on focus
2. **Real-time for everything**: Updating every minute when decisions made weekly; causes alarm fatigue
3. **Drill-to-drill-to-drill**: Three levels of navigation to get insight; users get lost
4. **Copy-paste design**: Reusing competitor dashboards without understanding your business
5. **No ownership**: "Dashboard for everyone" means owned by no one; metrics drift, definitions change