---
name: chart-recommender
description: "Analyze datasets and recommend optimal chart types for comparison, distribution, composition, relationship, and time-series visualization."
category: data
difficulty: intermediate
model_boost: "Weak model recommends inappropriate charts or creates confusing visualizations"
---

# Chart Recommender

## Purpose
The right chart type makes data story obvious; the wrong type obscures insight. This skill systematizes chart selection by analyzing data characteristics and communication intent, recommending the optimal visualization for clarity and impact. The output is a specific chart recommendation with justification.

## When to Use
- Selecting chart type for analysis or reporting
- Creating dashboards (need multiple chart decisions)
- Explaining data to non-technical audiences
- Identifying when data is better shown as table
- **Do NOT use when**: Chart type already mandated, or aesthetic choice (use design tool)

## Instructions

### Step 1: Classify Your Data
Determine what types of variables you're visualizing:

**Variable classification:**

```
CATEGORICAL (discrete, limited distinct values):
- Examples: Country, Status, Product Category, Customer Segment
- Characteristics: Usually string, fixed set of options
- Number of categories: Matters (5 categories vs. 100)
- Ordinal vs. Nominal:
  Nominal: No order (Red, Blue, Green)
  Ordinal: Ordered (Low, Medium, High)

NUMERIC (continuous or discrete, many possible values):
- Examples: Revenue, Age, Page Load Time, Number of Orders
- Characteristics: Numbers, can be fractional
- Distribution: Normal? Skewed? Bimodal?
- Range: Full spectrum vs. constrained?

TIME-SERIES (numeric or categorical, ordered by time):
- Examples: Daily revenue, Monthly active users, Quarterly churn
- Characteristics: Temporal ordering matters
- Frequency: Daily, weekly, monthly, annual?
- Seasonality: Does pattern repeat?

COMPARISON DATA (two or more groups):
- Examples: Q4 vs. Q3 revenue, Product A vs. Product B, Control vs. Treatment
- Characteristics: Same metric measured across groups
- Number of groups: 2 vs. 5 vs. 20?
- Time dimension: Same point in time vs. over time?
```

**Data analysis example:**

```
Question: "How does revenue compare across regions?"

Variables:
- X-axis: Region (categorical: North, South, East, West, Midwest)
- Y-axis: Revenue (numeric, continuous)

Analysis:
- Type of comparison: Group comparison (5 groups)
- Number of groups: 5 (manageable for bar chart)
- Secondary dimension? Possible (by product, by quarter)
- Rank order matter? Not inherently (regions are peers)
```

### Step 2: Match Question Type to Visualization
Select chart based on what you're answering:

**Question patterns and chart recommendations:**

```
QUESTION TYPE 1: "HOW MUCH?" (Single value or trend)
├─ Numeric comparison over time
├─ Best chart: Line chart, area chart
├─ Example: Monthly revenue trending 2024-2026
│
└─ Single snapshot
  └─ Best chart: Large number (KPI card), gauge chart
  └─ Example: Total revenue in Q1 2026 = $2.4M

QUESTION TYPE 2: "WHICH IS BIGGEST?" (Ranking, comparison)
├─ Rank items by magnitude
├─ Best chart: Horizontal bar chart (easier to read labels)
├─ Example: Top 10 products by revenue
│
├─ Answer: Which product? → Sorted descending bar chart
│
└─ Worst chart: Pie chart (hard to compare 80% vs. 75%)

QUESTION TYPE 3: "HOW ARE THEY DISTRIBUTED?" (Spread, shape)
├─ How are values spread? Are most concentrated or spread out?
├─ Best chart: Histogram, box plot, violin plot
├─ Example: Distribution of customer ages (20-70, mostly 25-35)
│
├─ Comparison: Compare distributions across groups
├─ Best chart: Box plot (shows quartiles, outliers, side-by-side)
├─ Example: Customer age distribution by segment
│
└─ Show percentiles/quartiles
  └─ Best chart: Box plot shows Q1, median, Q3, outliers clearly

QUESTION TYPE 4: "WHAT'S THE COMPOSITION?" (Parts of a whole)
├─ How does one segment break down?
├─ Best chart: Stacked bar chart, treemap
├─ Example: Website traffic by source (organic 60%, paid 30%, direct 10%)
│
├─ Multiple breakdowns
├─ Best chart: Stacked bar (compare compositions side-by-side)
├─ Example: Revenue by segment (Q1, Q2, Q3 stacked bars)
│
└─ Small number of categories (3-4)
  └─ Acceptable: Pie chart (familiar, but bar chart is better)

QUESTION TYPE 5: "ARE THEY RELATED?" (Correlation, association)
├─ Do two numeric variables move together?
├─ Best chart: Scatter plot with optional trend line
├─ Example: Does customer engagement predict retention?
│  Each dot = one customer (engagement score vs. retention 0/1)
│
├─ Many data points? Add density coloring (heatmap)
├─ Example: 100K+ customers in scatter → dense scatterplot
│
└─ Categorical relationship
  └─ Best chart: Mosaic plot or grouped bar chart
  └─ Example: Does customer segment relate to churn?

QUESTION TYPE 6: "WHAT'S THE TREND?" (Change over time)
├─ How does metric change over time?
├─ Best chart: Line chart (time on X-axis, metric on Y)
├─ Example: Monthly revenue, daily active users
│
├─ Multiple series (compare trends)
├─ Best chart: Multiple lines on same chart
├─ Example: Revenue trend by product (A, B, C as different colors)
│
├─ Seasonality or volatility?
├─ Best chart: Line with area fill (shows magnitude)
├─ Alternative: Line with reference line (e.g., 12-month moving average)
│
└─ Year-over-year comparison
  └─ Best chart: Two lines (this year vs. last year) or dual-axis
  └─ Alternative: Small multiples (separate panels per year)
```

### Step 3: Evaluate Data Characteristics
Check that recommended chart can handle your data:

**Data suitability checks:**

```
CHART: Bar Chart (vertical)
Best for: Comparing 5-20 categories, each with one value
Can handle: Any number of bars, but readability decreases >20
Data requirements:
  ✓ One categorical variable (X-axis)
  ✓ One numeric variable (Y-axis height)
  ✓ No missing values (gaps in bars look broken)
  ✓ Non-negative values (bars can't go below zero)

Problems & solutions:
  Issue: 50 categories → 50 bars, labels overlap
  Solution 1: Horizontal bar chart (easier to read long labels)
  Solution 2: Sort by value (identify top/bottom quickly)
  Solution 3: Show top 10 (less clutter, focus)
  Issue: Negative and positive values (e.g., profit/loss by region)
  Solution: Diverging bar chart (zero line in middle)
  Issue: Many decimal places (2.145 vs. 2.144)
  Solution: Round to 1 decimal place (precision beyond 2pp not visible in bar height)

Related charts:
  → Horizontal bar: Better for long category names
  → Stacked bar: Show composition (parts of whole)
  → Grouped bar: Compare categories across dimensions


CHART: Line Chart
Best for: Time series (trend over time)
Data requirements:
  ✓ Time variable (X-axis, ordered)
  ✓ Numeric variable (Y-axis)
  ✓ Multiple points (≥5 for visible trend)
  ✓ Temporal ordering (can't reorder time)

Problems & solutions:
  Issue: Too many lines (5+ lines = spaghetti chart, hard to read)
  Solution 1: Show top 3-4 lines, summarize others
  Solution 2: Small multiples (separate panels per line)
  Solution 3: Interactive legend (toggle lines on/off)
  Issue: Lines cross frequently (hard to track individual trend)
  Solution: Add markers (dots) at data points
  Issue: Huge spike (outlier dominates Y-axis)
  Solution 1: Remove outlier or cap at 95th percentile
  Solution 2: Log scale (Y-axis exponential)
  Issue: Sparse data (measurements 3 months apart)
  Solution: Show points but not connecting lines (visual breaks indicate gaps)

Related charts:
  → Area chart: Fill below line (emphasize magnitude)
  → Waterfall: Show cumulative change (sum of individual changes)
  → Step chart: Discrete changes (status changes, not continuous)


CHART: Scatter Plot
Best for: Showing relationship between two numeric variables
Data requirements:
  ✓ Two numeric variables (X-axis, Y-axis)
  ✓ Multiple data points (≥10 to see pattern)
  ✓ Can handle outliers (clearly visible as distant points)

Problems & solutions:
  Issue: Overplotting (points overlap, hide density)
  Solution 1: Transparency/alpha (see through overlapped points)
  Solution 2: Hexbin plot (aggregate overlapping points)
  Solution 3: Marginal histograms (show univariate distributions on sides)
  Issue: No visible trend despite strong correlation
  Solution: Add trend line (linear or LOWESS smoothing)
  Issue: Too many points (100K+ dots overwhelm)
  Solution: Heatmap (grid of colors showing density)
  Issue: Can't tell association direction (positive or negative)
  Solution: Add trend line or calculate correlation coefficient

Related charts:
  → Bubble chart: Add third numeric variable (bubble size)
  → Heatmap: Show density of overlapping points
  → Hexbin: Aggregate points into hexagons


CHART: Pie Chart
❌ AVOID EXCEPT WHEN:
  - Exactly 3-4 slices (larger, harder to compare)
  - Slices don't need precise comparison (approx. % acceptable)
  - Familiar to audience (common, no education needed)

Why pie is bad for most uses:
  ✗ Humans compare angles poorly (is 30% or 33% larger?)
  ✓ Humans compare bar heights well (instantly obvious which taller)
  ✗ Requires legend (can't label slices easily)
  ✓ Bar chart labels on axis (clear what each bar is)
  ✗ Hard to add second dimension (stacked bar beats pie)
  ✓ Stacked bar shows composition AND allows comparison

Better alternative: Horizontal bar chart
  Before: Pie chart with 5 slices (Chrome 25%, Firefox 20%, Safari 15%, Edge 25%, Other 15%)
  After: Horizontal bar (same data, easier comparison)

Acceptable pie use case:
  "What's the breakdown?" where answer is clear (3 slices, one very large)
  Example: "Market share: Our company 40%, Competitor A 35%, Competitor B 25%"
  But even here, bar chart is better for precise comparison
```

### Step 4: Consider Design and Accessibility
Ensure visualization is readable for all audiences:

**Design quality checklist:**

```
✓ AXIS LABELS: Clear, units specified
  Bad: Y-axis unlabeled (is it dollars or millions?)
  Good: Y-axis labeled "Revenue ($M)" or "Customer Count"

✓ LEGEND: Placed logically, color-blind safe
  Bad: Legend outside plot, unrelated to data (legend order ≠ bar order)
  Good: Legend above or integrated (order matches data)
  Bad: Red/green (colorblind users can't distinguish)
  Good: Blue/Orange (colorblind-safe palette)

✓ TITLE: Descriptive, shows insight
  Bad: "Q1 2026 Revenue"
  Good: "Q1 2026 Revenue Up 15% YoY" (insight in title)

✓ DATA LABELS: Show exact values or reduce
  Bad: Every bar labeled (cluttered)
  Good: Top 3 bars labeled (focus on important values)
  Good: Total sum labeled for stacked bar

✓ COLORS: Minimum, consistent meaning
  Bad: 10 different colors (no pattern)
  Good: 3-5 colors, reused across charts (blue=this year, orange=last year)

✓ GRIDLINES: Light, not distracting
  Bad: Bold gridlines (dominate chart, data secondary)
  Good: Light gridlines (help read values, data primary)

✓ 3D EFFECTS & DECORATION: Remove
  Bad: 3D pie chart (distorts angles further)
  Bad: Decorative icons (add no information)
  Good: Flat, minimal design (focus on data)

✓ ASPECT RATIO: Optimize for reading
  Bad: Very wide, very short (hard to read labels)
  Good: 16:9 or 4:3 ratio (natural reading)

ACCESSIBILITY:
  ✓ Color-blind safe palette: Use ColorBrewer or Accessible Colors plugin
  ✓ Text size: ≥12pt for presentations, ≥10pt for printed materials
  ✓ Contrast: Dark text on light background or vice versa
  ✓ Alternative text: For embedded images, describe chart in words
  ✓ Data table: Provide source data for accessibility

INTERACTIVE DASHBOARDS:
  ✓ Tooltip (hover): Show exact values
  ✓ Legend toggle: Click to show/hide series
  ✓ Zoom/pan: Explore time range or detail
  ✗ Auto-play: Automatically cycling through series (attention hog)
  ✗ Too many interactions: Overwhelming, fewer people explore
```

### Step 5: Create Recommendation with Justification
Document chart choice and explain rationale:

**Recommendation format:**

```
CHART RECOMMENDATION

Dataset: Customer Retention by Cohort (5K customers, 12 cohorts, 12 months)

Recommendation: Line chart (one line per cohort, color-coded)

Justification:
- Primary question: "How does retention vary by customer cohort?"
- Data structure: Retention % (numeric) × Month (time-series) × Cohort (5K groups)
- Chart type rationale:
  ✓ Time-series data (months on X-axis)
  ✓ Multiple series (cohorts as different colors)
  ✓ Shows trend for each cohort simultaneously
  ✓ Clear comparison: newer cohorts vs. older (different slopes)

Alternative considered and rejected:
  - Stacked area: Composition not the question (retention not "parts of whole")
  - Bar chart: Can't show 12 time points efficiently (too wide)
  - Heatmap: Possible, but loses trend visibility

Design specifications:
  - X-axis: Month 0-12 (since cohort acquisition)
  - Y-axis: Retention % (0-100%)
  - Color: Cohort-by-month (blue=older, red=newer, gradient)
  - Lines: Solid, medium thickness (distinct)
  - Legend: Top-right, 5 cohort labels
  - Tooltip: On hover, show cohort + month + retention %
  - Title: "Customer Retention by Acquisition Cohort"
  - Subtitle: "12-Month Cohort Analysis (5,000 customers)"

Insight enabled:
  This chart immediately reveals:
  - Steepest drop in month 1-2 (onboarding churn)
  - Stabilization after month 3 (engaged core emerges)
  - Differences between cohorts (newer vs. older adoption patterns)
  - Actionable: Month 1-2 is critical period for retention investment
```

## Output Template

**Chart Recommendation Report:**

```markdown
# Visualization Recommendation

**Question**: [What are you trying to communicate?]
**Data**: [Variables, row count, time range]

## Recommendation

**Chart Type**: [Specific chart: e.g., "Horizontal bar chart, sorted descending"]

**Justification**: [2-3 sentences explaining why this chart]

**Design Specifications**:
- Axes: [What's on X and Y]
- Colors: [How variables are encoded]
- Sorting: [Sorted by value? Date? Category?]
- Labels: [Which values are labeled]
- Title/Subtitle: [Suggested titles]

**Insights Enabled**: [What will be obvious to viewer]

**Why Not**: [Alternatives considered and rejected]

## Example

**Question**: Which product categories are growing fastest?
**Data**: Revenue by category (6 categories, quarterly data 2024-2026)

**Recommendation**: Grouped bar chart
- X-axis: Quarter
- Y-axis: Revenue ($M)
- Groups: 6 product categories (each color)
- Sorted: By 2026 revenue (largest left)

**Why**: Shows both absolute size (bar height) and trend (height across quarters)
Allows quick comparison of categories (same quarters side-by-side)
```

## Quality Gates

1. **Chart matches question type**: Visualization answers stated question
2. **Data characteristics supported**: Chart can properly render your data
3. **Readability confirmed**: Legend clear, axes labeled, font legible
4. **Color-blind accessible**: Palette works for colorblind viewers
5. **Insight enabled**: Key pattern/conclusion is obvious
6. **Justification provided**: Why this chart, not alternatives

## Examples

**Good: Clear recommendation with reasoning**
```
Question: "How does conversion rate differ between traffic sources?"
Data: Conversion % by source (5 sources, monthly 2025-2026)

Recommendation: Grouped bar chart
- Categories: Traffic sources on X-axis
- Bars: Monthly conversion rates grouped (Jan, Feb, Mar, etc.)
- Colors: By month (easier to track across sources)
- Insight: Instantly see which source has highest/lowest conversion
         and how consistency varies month-to-month

Justification: Bar chart compares categorical groups easily.
Grouping shows both source comparison AND time trends.
Alternative (line chart) would work but sources mix poorly (spaghetti).
```

**Bad: Inappropriate chart, poor reasoning**
```
Recommendation: Pie chart for 10 different regions' market share
Problem: 10 slices too many (angles hard to compare)
        Pie chart poor for ranking (which region #2?)
Better: Horizontal bar chart (easy label, easy comparison)
```

## Common Mistakes

1. **Question and chart mismatch**: Asking "what's the trend?" but choosing bar chart (not time-series)
2. **Pie chart for many slices**: 8+ categories in pie chart (unreadable, angles hard to compare)
3. **Too many lines**: 10+ lines on single chart (spaghetti, illegible)
4. **3D effects**: Distort perception (3D pie makes angles appear different than they are)
5. **Color overuse**: 15 different colors (no pattern, audience can't track)
6. **Decoration over data**: Chart looks pretty but insight unclear

## Anti-Patterns

1. **"Use what you're used to"**: Always bar charts regardless of question type
2. **"More dimensions = more colors"**: Color-coding 10 categorical variables (unreadable)
3. **"Bigger is better"**: Making chart fill entire screen (often wastes space)
4. **"Default chart type"**: Using whatever Excel/Tableau defaults to (often wrong)
5. **"Show all data"**: Including every data point, outliers, noise (obscures signal)