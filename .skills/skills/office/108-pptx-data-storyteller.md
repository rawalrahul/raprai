---
name: pptx-data-storyteller
description: "Build data-driven presentations: chart selection, annotation, progressive reveal, headline conclusions. Use when you have data and need to communicate findings persuasively."
category: office
difficulty: intermediate
model_boost: "Fixes weak data presentations: raw charts with no interpretation, generic titles, data that doesn't support claims."
---

# PPTX Data Storyteller

## Purpose
Present data so the audience understands the conclusion immediately, not after staring at charts. This skill selects chart types by analysis goal, annotates to highlight the insight, uses headline titles that state the conclusion, and builds animations that reveal the story progressively. A strong data presentation teaches, not just shows.

## When to Use
- "I have this data and need to present it" (need to turn numbers into a story)
- "Make a presentation showing [metric] trends" (performance analysis)
- "Present the results of [analysis]" (research/study findings)
- **Do NOT use when**: Architecting overall presentation flow (use 101-pptx-deck-architect); or training audiences (use 111-pptx-training-deck)

## Instructions

### Step 1: Chart Type Selection by Analysis Goal
Match chart to the question the audience is asking.

**Comparison: "Which is bigger?"**
- **Bar Chart** (horizontal bars)
  - Use when: Comparing items; labels are long
  - Example: "Revenue by region (East $2M, West $3.5M, South $1.2M)"
  - Readers compare bar length; faster than reading numbers
  - Tip: Sort descending (tallest to shortest) to emphasize ranking

- **Column Chart** (vertical bars)
  - Use when: Short labels, 3–6 items to compare
  - Example: "Quarterly revenue (Q1 $1.5M, Q2 $2.1M, Q3 $1.8M, Q4 $2.4M)"
  - Matches x-axis (time) expectation

**Trend: "Does it go up or down?"**
- **Line Chart**
  - Use when: Showing change over time (months, quarters, years)
  - Example: "Customer growth Jan–Dec (started 100, ended 280, inflection in June)"
  - Readers instantly see upward/downward direction and rate of change
  - Mark inflection points: "Launch event June 15 drove 80% growth"
  - Avoid: 3D lines, dual axes (confusing)

**Composition: "What's the breakdown?"**
- **100% Stacked Bar** (shows share of total)
  - Use when: Showing proportion composition over time
  - Example: "Market share by competitor (Acme 35%, Rival 42%, Other 23%) across 3 years"
  - Each bar = 100%; see shift in proportions across time
  - More intuitive than pie charts

- **Stacked Column** (shows total AND breakdown)
  - Use when: Total matters AND composition matters
  - Example: "Revenue by product type, quarterly (total growing, but mix shifting)"
  - Height = total; color segments = breakdown

- **Pie Chart** (last resort)
  - Use when: Only 2–3 slices and a compelling reason for the circle shape
  - Example: Budget allocation (Revenue streams: Product 65%, Services 25%, Other 10%)
  - Honestly: Bar charts usually outperform pies for readability

**Relationship/Correlation: "Does X drive Y?"**
- **Scatter Plot**
  - Use when: Testing if two variables are related
  - Example: "Marketing spend vs. sales revenue across 20 companies"
  - X-axis: Marketing spend; Y-axis: Revenue
  - Upward trend = positive correlation; tight cluster = strong relationship
  - Add trendline: Right-click data → Add Trendline → Linear
  - Show R² value: Tells strength of relationship (0.85 = strong, 0.3 = weak)

**Contribution/Breakdown: "Where did the value come from?"**
- **Waterfall Chart**
  - Use when: Showing starting point → additions → subtractions → ending point
  - Example: Net income bridge (Revenue $10M − COGS $3M − OpEx $4M − Taxes $1M = Net $2M)
  - Each bar = one contribution; stacked horizontally
  - Readers see exactly where money goes or how value is created
  - No other chart communicates this as clearly

**Distribution: "Is it spread out or clustered?"**
- **Histogram** (column chart with continuous data)
  - Use when: Showing shape of distribution
  - Example: "Customer order values ($0–$100, $100–$200, $200+)"
  - Shows if most customers are small, mid, or high-value
  - X-axis: Bins (ranges); Y-axis: Count

### Step 2: Chart Annotation Strategy
Raw data doesn't tell a story; annotations do.

**Annotation Types**

**Callout Box** (text box with arrow)
- Points to the key insight on the chart
- Example: Chart shows revenue trend; callout says "↑ 40% growth in Q3"
- Place box near the insight; use arrow to point to specific data point
- Make text large enough to read (14pt minimum)

**Data Label on Chart**
- Value displayed directly on/above bar or point
- Use for highlighting top 3 items or outliers
- Don't label every data point (clutter)

**Reference Line** (mark expected value)
- Horizontal line showing "Target" or "Industry Average"
- Example: Sales chart with line at "$2M target"; bars show if above/below
- Readers instantly see performance vs. expectation

**Shading/Highlight** (draw attention to period)
- Shade one region of chart (e.g., "Recession period in gray")
- Explains anomaly without words

**Annotation Example**
```
[Line chart: Revenue Jan–Dec, upward trend]

Callout box with arrow pointing to June:
"↑ 80% spike: Product launch June 15"

Reference line at Y=$2M:
"Target: $2M (exceeded by Oct)"

Result: Reader sees trend, understands driver, knows about target
```

### Step 3: Headline Titles (State the Conclusion)
Bad title: "Sales Overview"
Good title: "Sales grew 23% YoY, driven by enterprise segment"

**Title Formula**
```
[Metric] {{Changed}} {{Magnitude}}, {{Reason}}

Examples:
- "Revenue grew 23% YoY, driven by enterprise segment acquisition"
- "Customer churn decreased to 6%, down from 8% via support program"
- "Gross margin expanded 4 points to 48%, reflecting scale benefits"
- "East region outperformed by 12%, best growth rate among all regions"
```

**Structure**
1. Start with metric: "Revenue"
2. State change: "grew" / "declined" / "held steady"
3. Quantify: "23%"
4. Add reason: "because of [driver]" OR context: "best in 3 years"

**Avoid These Titles**
- "Q3 Results" (generic; doesn't tell what happened)
- "Sales by Region" (descriptive, not insightful)
- "Revenue Comparison" (what comparison?)
- "Data" (basically useless)

**Good Slide Titles**
- "Revenue grew 23%, driven by enterprise migration"
- "Customer acquisition cost fell 15% via targeted marketing"
- "Operating margin improved despite 18% revenue growth"
- "Product D underperforms: churn 2x peer average"

### Step 4: Progressive Reveal (Build Animations)
Tell the story step-by-step; don't dump all data at once.

**Animation Types in PowerPoint**

**Appear** (simplest; data shows up)
- Use for: Bar charts, when you want to introduce one bar at a time
- Example: "Revenue by region" chart; one region bar appears per click
- Audience sees East, then West (reads each before moving on)

**Wipe** (data slides in from edge)
- Use for: Line charts; wipe from left to right shows time progression
- Effect: Line appears to draw itself left-to-right; mimics time flow
- Audience sees "January appears, then February, growth becomes obvious"

**Emphasis** (highlight existing element)
- Use to: Draw attention to a specific bar or point after chart appears
- Example: Chart appears fully, then outlier bar flashes in color

**How to Add Animations**
1. Select chart or shape
2. Animations tab → Click "Appear" or "Wipe"
3. Effect Options: "By Series" (one bar at a time)
4. Timing: "On Click" (you control reveal) or "With Previous" (auto-play)
5. Preview to test flow

**Story Flow Example**
```
Slide: "Revenue Trend 2024"

Build 1 (appear): Chart appears with grid only
Build 2 (appear): Line appears (shows progression Jan–Dec)
Build 3 (appear): Callout box appears: "Peak in Oct: $2.1M"
Build 4 (appear): Reference line appears: "Target: $2M average"

Audience sees: Trend → Notices peak → Compares to target → Gets the story
(vs. all appearing at once: Reader has to process everything at once)
```

### Step 5: Chart Design and Cleanliness
A clean chart is a credible chart.

**Avoid These Bad Practices**
- **3D effects**: Makes reading values harder; avoid unless mandatory
  - Don't: 3D pie chart (perspective distorts slices)
  - Do: 2D bar chart (height accurately represents value)

- **Dual axes**: Only use if absolutely necessary; always explain
  - If using: Label each axis clearly with units ($ on left, % on right)
  - Risk: Readers can be manipulated by scaling (shrink one axis = make data look larger)

- **Too many colors**: One color per series, unless segmenting
  - Do: All product revenue bars same color (blue)
  - Don't: Each bar a different color (looks chaotic, implies false categories)

- **Color blind issues**: Use colors that differentiate (not red-green together)
  - Use: Blue, orange, gray (easy for color-blind readers)
  - Avoid: Red-green contrast alone (7% of males are red-green color blind)

- **Data markers overlapping**: If points overlap, jitter slightly or use transparency
  - Scatter plot with 500 points = black blob; can't see density
  - Fix: Use transparency (alpha=0.3) so overlapping points show as darker areas

**Chart Cleanliness Checklist**
- Axis labels are readable (≥10pt, not rotated unless necessary)
- Grid lines exist but don't overwhelm data (light gray, not bold)
- Legend is minimal (only if >2 series; sort legend by magnitude)
- Chart title is present and states the conclusion
- Data source is cited (small text bottom-right: "Source: {{system}}, {{date}}")

### Step 6: Audience Calibration (Executive vs Technical)
Different audiences need different emphasis.

**Executive Audience** (C-suite, board)
- Show: Business outcome, not technical details
- Chart type: Simple (bar, line, column) not exotic
- Title example: "Revenue grew 23%, on track to reach $10M annual"
- Annotation: Outcome and why it matters
- Avoid: Methodology, statistical confidence intervals, error bars

**Technical Audience** (analysts, engineers)
- Show: Methodology, assumptions, confidence levels
- Chart type: More complex OK (scatter, distribution, control charts)
- Title example: "Correlation between marketing spend and revenue: R²=0.87, p<0.01"
- Annotation: Statistical significance, sample size, limitations
- Include: Methodology slide explaining how data was collected

**Board of Directors** (strategic focus)
- Show: Trend vs. competition, strategic implications
- Chart example: "Market share trend (Acme gaining vs. rivals, on pace to 40% by year-end)"
- Include: Risk/opportunity summary
- Avoid: Granular operational details; they care about strategy

**Sales Team** (action-oriented)**
- Show: Drivers of outcomes, what to do next
- Chart example: "Enterprise customers have 3x higher lifetime value; prioritize enterprise sales"
- Include: Action recommendations tied to data
- Avoid: Academic phrasing; they want clear next steps

### Step 7: Source Attribution and Credibility
Tell the audience where your data came from.

**Citation Format** (place at bottom-right of chart)
```
Source: Salesforce CRM, Data pulled March 5, 2024
```

**Include if credible:**
- Data system name (not just "our data")
- Date of pull (shows freshness)
- Sample size (for surveys): "n=1,247 respondents"
- Confidence level (for studies): "95% confidence interval"

**When Data is Sensitive**
- "Source: Acme company financials (confidential)"
- "Based on anonymized customer data"
- "Proprietary methodology developed internally"

### Step 8: Multi-Slide Data Analysis
Build argument from data across multiple slides.

**Progression** (how to structure multiple slides with related data)
1. **Headline finding slide**: One chart, one clear insight
   - Example: "Revenue grew 23% YoY"

2. **Breakdown slide**: Show what drove the headline
   - Example: "Growth driven by enterprise (↑40%) and mid-market (↑15%)"

3. **Trend slide**: Show this is part of a pattern
   - Example: "Enterprise growth accelerating for 3 consecutive years"

4. **Competitive context**: Show how you're doing vs. market
   - Example: "Our 23% growth vs. industry average of 12%"

5. **Recommendation slide**: What does this mean; what should we do?
   - Example: "Double down on enterprise sales; opportunity to reach 50% of revenue"

**Example: Product Performance Analysis**
```
Slide 1: "Product A revenue is our fastest-growing segment"
[Single line chart showing Product A revenue trend, steeply upward]

Slide 2: "Growth is driven by enterprise adoption and international expansion"
[Stacked bar chart: Product A revenue by customer segment and region]

Slide 3: "Margin is improving as we scale; manufacturing costs declining"
[Line chart: Product A gross margin trend over 3 years, upward]

Slide 4: "Product A now represents 28% of total revenue, up from 15%"
[Pie chart or 100% stacked bar: revenue composition by product, year-over-year]

Slide 5: "Recommendation: Increase investment in Product A sales team"
[Summarize findings and call-to-action]

(Reader follows: Headline → drivers → sustainable? → strategic importance → action)
```

## Output Template
```
# {{PRESENTATION TITLE}}: Data-Driven Analysis

## Slide-by-Slide Breakdown

### Slide 1: {{Headline Finding}}
**Chart Type**: {{Bar | Line | Scatter | Waterfall}}
**Title**: {{Conclusion, not generic (e.g., "Revenue grew 23% YoY")}}
**Data**: {{Source and date}}
**Annotation**: {{Key insight callout; what to notice}}
**Audience Calibration**: {{Executive | Technical | Board}}

### Slide 2: {{Supporting Detail / Breakdown}}
**Chart Type**: {{Stacked bar to show composition}}
**Title**: {{Explains what drove headline}}
**Audience**: {{See slide 1 audience}}

## Chart Design Specs
| Slide | Chart Type | Colors | Axis Labels | Grid | Data Labels |
|---|---|---|---|---|---|
| 1 | Line | Blue | X: Month, Y: $ | Light gray | On key points only |
| 2 | Stacked bar | Blue/orange | X: Region, Y: $ | None | On total only |

## Annotations & Callouts
- Slide 1: Callout box pointing to peak: "↑ 40% spike in June due to product launch"
- Slide 2: Reference line at $2M target
```

## Quality Gates
- [ ] Chart type matches analysis goal (line for trend, bar for comparison, etc.)
- [ ] Chart title states conclusion in plain language (not generic topic)
- [ ] Annotations highlight the insight (callout boxes, reference lines)
- [ ] Data source cited (bottom of chart: "Source: {{system}}, {{date}}")
- [ ] Slide builds progressively (each click reveals one element)
- [ ] Color scheme is readable for color-blind audiences (no red-green only)
- [ ] Audience calibration is clear (technical jargon if technical, simple if executive)
- [ ] Multiple data slides form a coherent argument (headline → drivers → context → action)

## Examples

### Good Output (excerpt)
```
Slide: "Enterprise Revenue Grew 40% YoY, Outpacing Market Growth"

[Line chart: Enterprise revenue trend Jan 2023–Jan 2024, steep upward slope]

Chart title: "Enterprise Revenue Trend (YoY +40%)"

Callout box with arrow pointing to Jan 2024:
"↑ 40% YoY growth: Largest segment acceleration in company history"

Reference line at Y=$4M:
"Target for Q1 2024: $4M (on track)"

Annotations:
- June 2023: Vertical shaded region labeled "Major deal: TechCorp $1.2M"
- December 2023: Arrow pointing up labeled "Christmas promo +$500K"

Source (small text, bottom right):
"Source: Salesforce revenue tracker, January 2024"

Audience calibration: Executive
(No statistical jargon; clear business outcome and drivers)

Next slide (build):
[Stacked bar: Enterprise revenue by customer size (Large/Medium/Small) across 4 quarters]
Title: "Growth spread across all customer sizes; Large accounts most promising"
(Shows breakdown; adds nuance)
```

### Bad Output (what to avoid)
```
"Revenue Analysis" (generic title; no insight)
[Pie chart with 8 slices, hard to compare, one labeled "Other 23%"]
No annotations; reader has to interpret
No axis labels; unclear if Y is revenue or units
Source not cited
3D effects make reading values difficult
Next slides unrelated; don't form argument
```

## Common Mistakes

1. **Mistake**: Chart has generic title ("Sales by Region") instead of insight.
   → **Fix**: Rewrite as insight: "East region underperforms by 15%; investigate customer concentration risk."

2. **Mistake**: Raw chart with no annotations; audience doesn't know what to notice.
   → **Fix**: Add callout box or reference line highlighting the insight.

3. **Mistake**: Dual axes that mislead (one axis scaled tiny, other large; makes data look more dramatic).
   → **Fix**: Use dual axes only if clearly labeled; better yet, use separate charts.

4. **Mistake**: Pie chart with 10 slices; impossible to compare visually.
   → **Fix**: Use 100% stacked bar chart instead; much clearer.

5. **Mistake**: Multiple data slides don't flow; audience lost on how findings connect.
   → **Fix**: Each slide should answer a question that leads to the next (headline → drivers → trend → action).

## Anti-Patterns
- Never show raw data without interpretation. (Charts are inert; annotations do the work.)
- Never use 3D effects in charts. (They distort values; 2D is more accurate.)
- Never title a chart with just the metric name. (The title should state your conclusion.)
- Never include more than 2–3 series in one chart. (More = confusing; use separate charts.)
- Never omit source attribution. (Credibility matters; tell where data came from.)
- Never assume executives want technical detail. (Simplify; save methodology for appendix.)
