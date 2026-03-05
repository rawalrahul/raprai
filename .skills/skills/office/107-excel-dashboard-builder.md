---
name: excel-dashboard-builder
description: "Build interactive Excel dashboards with KPI cards, sparklines, slicers, and drill-down tables. Use when asked to 'make a dashboard' or 'create an executive view'."
category: office
difficulty: intermediate
model_boost: "Fixes weak dashboards: random data visualizations without insight, cluttered layouts, non-functional slicers."
---

# Excel Dashboard Builder

## Purpose
Design dashboards that surface key metrics at a glance and allow executives to explore data without spreadsheet skills. This skill arranges KPI cards, trendlines, and detail tables in a scannable layout, adds interactive filters (slicers), and uses conditional formatting as visual encoding. A strong dashboard answers "How are we doing?" in 5 seconds.

## When to Use
- "Create an executive dashboard" for weekly/monthly review
- "Build a KPI view" for board presentations
- "I need an interactive report" with drill-down capability
- **Do NOT use when**: Analyzing data for discovery (use 103-excel-data-analyzer); or building a financial model (use 102-excel-financial-modeler)

## Instructions

### Step 1: Dashboard Layout and Grid Structure
Good dashboards are visually balanced and scannable top-to-bottom.

**Standard Grid Layout** (3-column, modular approach)
```
Row 1: KPI Cards (4-5 metrics, high-level snapshot)
────────────────────────────────────────────────────

Row 2: Trend Charts (revenue, margin, customer count over time)
────────────────────────────────────────────────────

Row 3: Performance Tables (by product, region, or segment; top 10)
────────────────────────────────────────────────────

Row 4: Supporting detail (drilldown, variance analysis)
```

**Grid Dimensions** (Optimize for standard screen)
- Width: 3 columns of equal width (A:D, E:H, I:L for a 12-column sheet)
- Height: Each section = 15–20 rows (fits on one screen without scrolling)
- Total: Fits on one page printed landscape, or viewable in Excel window at 100% zoom

**Margins**
- Top margin (rows 1–2): Title and filter area
- Leave gaps between sections (blank rows) for visual separation

### Step 2: KPI Card Design
KPI cards are the top-line metrics executives scan first.

**Standard KPI Card Layout** (per card: 3-4 rows, 3-4 columns)
```
┌─────────────────────────┐
│ METRIC NAME             │  ← Header (bold, 12pt, metric name)
├─────────────────────────┤
│         $2.4M           │  ← Value (huge font, 24–28pt, formatted with $ or %)
├─────────────────────────┤
│ ↑ 12% vs last month     │  ← Trend (green up arrow = good; red down = bad)
│ Target: $2.0M           │  ← vs Target (optional context)
└─────────────────────────┘
```

**Data Formulas**
```
KPI Value: =Dashboard!C5 (references a metric from data tab)
Trend: =IF(C5>C4, "↑ " & ROUND((C5/C4−1),1)*100 & "%", "↓ " & ROUND((C4/C5−1),1)*100 & "%")
        (compares current vs previous month; formats as percentage change)
Color-code: Conditional formatting (if actual > target, cell is green)
```

**Arrangement**
- Place 4–5 KPIs in top row, evenly spaced
- Left-to-right order: Revenue → Profit → Customer Count → (optional: Margin, NPS)
- Consistent card size (all same cell dimensions)

**Cell Formatting**
- Value cell: Font 24pt, bold, center alignment
- Background: Light color (light blue, gray, or white with border)
- Trend cell: Font 12pt, smaller, green for increases, red for decreases
- Border: Light gray line around entire card

### Step 3: Trend Charts (Line, Column, Sparklines)
Show how metrics move over time.

**Line Chart: Revenue Trend**
- X-axis: Month (Jan–Dec)
- Y-axis: Revenue ($)
- One line per major segment (if 2–3; if more, use small multiples)
- Title: "Monthly Revenue Trend (Current Year)"
- Add target line (optional) as reference

**Column Chart: Sales by Region**
- X-axis: Region (East, West, South, North)
- Y-axis: Sales value
- One column per region
- Title: "Sales by Region (YTD)"
- Optional: Overlay line showing "Plan" or "Prior Year"

**Sparklines** (mini charts inside cells)
Useful for compact trend views; especially for tables with many rows.

In Excel:
1. Select cell where sparkline should appear
2. Insert → Sparklines → Choose type (Line, Column, Win/Loss)
3. Select data range (12 monthly values for a line, for instance)
4. Sparkline appears as 1-inch chart in cell

Example:
```
Product        |  Q1   Q2   Q3   Q4  |  Trend
─────────────────────────────────────────────
Widget A       |  $100 $120 $150 $180| ▁▂▃▄  (upward trend sparkline)
Widget B       |  $200 $190 $170 $160| ▄▃▂▁  (downward trend sparkline)
Widget C       |  $80  $85  $82  $88 | ▁▂▁▂  (volatile trend sparkline)
```

### Step 4: Detail Tables with Formatting
Performance-by-product/region tables with visual encoding.

**Table Structure**
```
Product     | YTD Sales | vs Target | % of Total | Margin % | Status
──────────────────────────────────────────────────────────────────────
Widget A    | $450,000  |    +12%   |    28%     |  48%     | ✓ (green)
Widget B    | $380,000  |     −5%   |    24%     |  42%     | ⚠ (yellow)
Widget C    | $290,000  |    −12%   |    18%     |  35%     | ✗ (red)
Widget D    | $220,000  |    +18%   |    14%     |  52%     | ✓ (green)
Widget E    | $160,000  |     +3%   |     8%     |  29%     | ⚠ (yellow)
```

**Conditional Formatting Rules**

**Data Bars** (% of Total column)
- Select range (E5:E9)
- Home → Conditional Formatting → Data Bars
- Choose color (blue), gradient fill
- Result: Bars fill cells; visually shows relative size

**Color Scales** (Margin % column)
- Select range (F5:F9)
- Home → Conditional Formatting → Color Scales
- Choose 3-color (Red-Yellow-Green)
- Red = low margin, green = high margin
- Automatically assigns colors based on values

**Icon Sets** (Status column)
- Select range (G5:G9)
- Home → Conditional Formatting → Icon Sets
- Choose "3-Symbol" (Red circle-Yellow triangle-Green checkmark)
- Define thresholds: Green if > target, Yellow if within ±5%, Red if < target

**Cell Highlighting** (vs Target column, identify underperformers)
- Select range (D5:D9)
- Home → Conditional Formatting → Highlight Cells Rules
- Less than: Set threshold (−10%)
- Color: Light red fill
- Result: Cells with ≥−10% variance are highlighted; easy to spot problems

### Step 5: Interactive Slicers (Click to Filter)
Slicers allow executives to filter dashboard by region, product, or period without formulas.

**Add a Slicer**
1. Create a pivot table or structured data range (source for slicer)
2. In dashboard area, Insert → Slicer
3. Select field to slice (e.g., "Region", "Product", "Quarter")
4. Slicer panel appears in dashboard

**Slicer Usage**
```
┌─ Region Slicer ──────────┐
│ ☐ All  ☑ East  ☐ West  │
│ ☑ South ☑ North         │
└──────────────────────────┘

(Click checkboxes to filter; underlying dashboard updates instantly)
```

**Connect Slicer to Dashboard**
- Slicer controls a pivot table or data source
- Dashboard charts/tables reference that filtered source
- When slicer changes, all downstream data updates

**Multiple Slicers**
- Add slicers for Region, Product, Time Period
- Users can filter by any combination
- Example: "Show revenue for Widget A in the East region, YTD"

### Step 6: Dynamic Chart Ranges
Charts update automatically when data changes.

**Method 1: Structured References (Modern Excel)**
- Convert data range to table: Select range → Insert → Table
- Table has automatic expanding/contracting range
- Chart based on table automatically includes new data

**Method 2: OFFSET Formula** (Older Excel, more flexible)
```
=OFFSET($A$1, 0, 0, COUNTA($A:$A), COUNTA($1:$1))
(Returns a range that expands if you add rows/columns)

How to use:
1. Create named range using OFFSET formula
2. Chart references named range instead of static A1:C12
3. When data grows, named range expands, chart updates
```

Example:
1. Formulas → Define Name: "SalesData"
2. Refers to: =OFFSET(Sheet1!$A$1, 0, 0, COUNTA(Sheet1!$A:$A), 5)
3. Create chart based on SalesData
4. Add new rows to source data; chart automatically includes them

### Step 7: Drill-Down Tables and Links
Executives want to click a KPI and see detail.

**Hyperlinking to Detail Sheets**
```
Main Dashboard Sheet:
KPI "Revenue: $2.4M" (in cell C5)

Right-click C5 → Insert Hyperlink → Place in This Document
Link to: Sheet "Revenue Detail"
Display text: $2.4M

Click the $2.4M, jumps to Revenue Detail sheet with full breakdown
```

**Detail Sheet Example**
```
Revenue Detail Sheet:
Product | January | February | March | Total | % of Revenue
─────────────────────────────────────────────────────────────
Widget A | $100K  | $120K   | $150K | $370K | 28%
Widget B | $90K   | $85K    | $75K  | $250K | 19%
...

[Hyperlink back]: Click "Back to Dashboard" button → goes back to main sheet
```

**Buttons with Hyperlinks**
1. Insert → Shapes → Rectangle
2. Type text: "Details"
3. Right-click → Hyperlink → Sheet "Product Detail"
4. Click button jumps to detail

### Step 8: Print-Friendly Layout
Dashboards should be printable one page (landscape).

**Print Setup**
1. File → Print Layout
2. Page Layout → Orientation: Landscape (wider view)
3. Page Layout → Margins: Narrow (0.5" margins)
4. Page Layout → Scaling: Fit to 1 page wide × 1 page tall
5. Print Preview to verify fits

**Print Areas**
- Home → Print Area → Set Print Area (select only dashboard range, exclude extra columns)
- Print only what matters (not every cell on the sheet)

**Headers/Footers for Print**
1. Insert → Header & Footer
2. Header: {{Dashboard Title}} | {{Date Updated}}
3. Footer: Page {{Page}} of {{Pages}} | Confidential

### Step 9: Data Refresh and Update Workflow
Dashboards need current data to be useful.

**Automatic Refresh** (if data is in same workbook)
- Data in "Data" sheet, dashboard in "Dashboard" sheet
- All dashboard formulas reference data sheet
- Update data; dashboard refreshes automatically

**External Data Refresh** (if data is from SQL/database)
- Data → From Database → Refresh All (updates external queries)
- Schedule automatic refresh: Data → Queries & Connections → Refresh schedule
- OR manual: Right-click query → Refresh

**Update Notification**
- In dashboard header: "Data as of: {{TODAY()}}" (formula shows current date)
- Updates automatically each day

## Output Template
```
# {{COMPANY}} Executive Dashboard

## Dashboard Layout
- **Row 1**: KPI Cards (4 metrics: Revenue, Profit, Customer Count, Margin)
- **Row 2**: Trend Charts (Revenue by month; Margin % trend)
- **Row 3**: Performance Table (Sales by product/region, top 10)
- **Row 4**: Variance Analysis (vs Budget, vs Prior Year)

## KPI Definitions
| KPI | Formula | Frequency | Owner |
|---|---|---|---|
| Monthly Revenue | =SUM(Data!C:C) | Daily | Finance |
| Gross Margin % | =(Revenue−COGS)/Revenue | Daily | Finance |
| Customer Count | =COUNTA(Data!A:A) | Daily | Sales |
| NPS Score | =AVERAGE(Data!F:F) | Monthly | Product |

## Slicers
- Region (East, West, South, North)
- Product (Widget A–E)
- Time Period (Month, Quarter)

## Conditional Formatting
- Revenue bars: Data bars, blue gradient
- Margin %: Color scale, red-yellow-green
- Status: Icon sets (check/warning/X)
- Variance: Highlight cells <−10% in red

## Data Sources
- Data updated daily from {{system}}
- Last refresh: {{TODAY()}}
- Manual refresh available: Data → Refresh All

## Print Setup
- Landscape orientation
- Fits to 1 page
- Header: {{Title}} | Updated {{Date}}
```

## Quality Gates
- [ ] Dashboard fits on one screen without scrolling (or intentional drill-down)
- [ ] 4–5 KPI cards at top, values clearly readable (≥20pt font)
- [ ] Each chart has a clear title and axis labels
- [ ] Conditional formatting encodes meaning (not just random colors)
- [ ] Slicers are functional and connected to data source
- [ ] Charts update when underlying data changes
- [ ] Printed dashboard is readable on one page landscape
- [ ] Dashboard header shows last refresh date

## Examples

### Good Output (excerpt)
```
Excel Dashboard: Monthly Operational Review

[Row 1: KPI Cards]
┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
│ Revenue  │ │ Margin % │ │ Customer │ │   NPS    │
│ $2.4M    │ │   45%    │ │  1,247   │ │  72      │
│ ↑ 12%    │ │ ↑ 2%     │ │ ↑ 8%     │ │ ↑ 3pts   │
└──────────┘ └──────────┘ └──────────┘ └──────────┘

[Row 2: Trend Charts]
[Line chart: Revenue Jan-Dec, upward trend]
[Line chart: Margin % Jan-Dec, flat-to-up]

[Row 3: Performance Table]
Product | YTD Sales | vs Target | % of Total | Margin | Status
──────────────────────────────────────────────────────────────
Widget A | $520K    |    +8%    |    28%    |  48%  | ✓
Widget B | $410K    |   −2%    |    22%    |  41%  | ⚠
Widget C | $360K    |   −8%    |    19%    |  38%  | ✗

[Conditional formatting: Data bars for % of Total, colors for margins, icons for status]

[Slicer: Region filter]
Region: ☑All ☑East ☑West ☑South ☑North (click to filter)

Print output: Fits on one landscape page
```

### Bad Output (what to avoid)
```
Dashboard with 20 KPI cards crammed into one row (unreadable)
Charts with no titles or axis labels
Slicers present but not functional (don't filter anything)
Conditional formatting applied randomly (cells colored but no pattern)
Data doesn't update; shows stale numbers
Printed dashboard requires zooming out to 60% to read
Detail tables have too many columns (>10) and no sorting
No way to drill from KPI to detail (can't investigate problem)
```

## Common Mistakes

1. **Mistake**: Dashboard has 50+ metrics; executives can't decide what matters.
   → **Fix**: Limit to 4–5 KPI cards. Everything else is supporting detail. Don't put everything on the dashboard.

2. **Mistake**: Slicers are added but don't actually filter the dashboard.
   → **Fix**: Slicers must be connected to a data source (pivot table or external query). Check Slicer Settings to ensure they're linked.

3. **Mistake**: Charts update manually (formulas hardcoded); stale data.
   → **Fix**: Use structured references or OFFSET formulas for dynamic ranges. Charts auto-update when data changes.

4. **Mistake**: Printed dashboard doesn't fit on one page; requires scrolling.
   → **Fix**: Page Layout → Scaling → Fit to 1 page wide, 1 page tall. Test Print Preview.

5. **Mistake**: Conditional formatting is decorative (colors don't encode meaning).
   → **Fix**: Each color should mean something: Red = problem, Green = on target, Yellow = watch.

## Anti-Patterns
- Never put more than 5 KPI cards at the top. (More than 5 = too much at once.)
- Never create a chart without a title. (Executives won't know what they're looking at.)
- Never use pie charts on dashboards. (Bar charts communicate comparison better.)
- Never forget to format KPI values clearly (≥20pt). (If they can't read KPIs in 3 seconds, dashboard fails.)
- Never apply conditional formatting without a clear rule. (Colors should encode insight: red=bad, green=good.)
- Never assume data will update itself; always show refresh timestamp. (Stale dashboards are worse than no dashboard.)
