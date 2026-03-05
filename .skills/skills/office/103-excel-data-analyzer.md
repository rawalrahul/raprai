---
name: excel-data-analyzer
description: "Clean data, pivot tables, charts, and analysis in Excel. Use for data import, pivot table design, chart selection, and VLOOKUP/INDEX-MATCH analysis."
category: office
difficulty: intermediate
model_boost: "Fixes weak analysis with poorly formatted pivot tables, wrong chart types, and broken lookups."
---

# Excel Data Analyzer

## Purpose
Transform raw data into insights using Excel's core analytical tools: importing and cleaning messy data, designing pivot tables for summary views, selecting charts that match the analysis goal, and writing lookup formulas that don't break. This skill moves data from "pile of numbers" to "clear story" using professional techniques.

## When to Use
- "Clean this data and show me a summary" (needs data cleaning + pivot table)
- "Compare sales by region/product" (pivot table with slicers)
- "Find where this product is sold most" (VLOOKUP or INDEX/MATCH)
- "Make a chart showing trends" (chart selection by analysis type)
- **Do NOT use when**: Building a financial model (use 102-excel-financial-modeler); or creating a dashboard (use 107-excel-dashboard-builder)

## Instructions

### Step 1: Data Import and Initial Cleaning
Raw data is almost never analysis-ready. Establish discipline in the first sheet.

**Import Best Practices**
- Paste data into a sheet named "Raw Data" (never analyze the import sheet)
- Verify row 1 is headers: Date, Transaction ID, Product, Sales, Region, etc.
- If headers are missing, add them before any analysis
- Check for trailing spaces in headers (Excel treats "Region" and "Region " as different)

**Fix Trailing Spaces**
```
Formula: =TRIM(A1) removes leading/trailing spaces
Apply TRIM to any text column that will be used in a pivot or lookup
Create new column: =TRIM(B1), copy down, then paste values over original
Delete original, rename TRIM column back to original name
```

**Text to Columns (for badly formatted imports)**
When date or numeric columns are imported as text:
1. Select the column
2. Data → Text to Columns
3. Step 1: Choose delimiter (comma, tab, space) or Fixed width
4. Step 2: Verify column breaks
5. Step 3: Check data type (General = auto-detect, Text, Date)
6. Finish: Replaces original column with parsed data

**Remove Duplicates**
Data → Remove Duplicates
- Select all data
- Choose columns to consider (usually all)
- Excel removes exact duplicate rows

**Blank Row and Column Check**
- Filter the data (select all, Data → Filter)
- Sort by key column (e.g., Date) to expose blanks at bottom
- Delete blank rows
- Remove filter when clean

### Step 2: Data Type Verification
Pivot tables and formulas break if data types are wrong.

**Fix Text Numbers**
If a numeric column shows left-aligned in cells (sign it's text):
```
Formula: =VALUE(A1) converts text "123" to number 123
Or in Data → Text to Columns, ensure column is set to "General" or "Number"
```

**Date Format Standardization**
If dates are mixed (some "3/15/2024", some "15-Mar-24", some "2024-03-15"):
1. Create helper column: =TEXT(A1, "YYYY-MM-DD")
2. Copy results, paste as values
3. Delete original column

**Sort Test**
Sort a numeric column. If it sorts alphabetically (1, 10, 2, 3 order), it's text.
- Fix: Use Text to Columns or VALUE formula

### Step 3: Pivot Table Design
Pivot tables are the fastest way to summarize data by dimensions.

**Basic Structure**
- **Rows**: Dimension 1 (Product, Region, Date)
- **Columns**: Dimension 2 (optional; use when values are few, e.g., Yes/No, Jan/Feb/Mar)
- **Values**: Metric to aggregate (Sum of Sales, Count of transactions, Average price)
- **Filters**: Optional top-level filter (e.g., filter to a specific region first)

**Build Steps**
1. Select data range (including headers): A1:F1000
2. Insert → Pivot Table
3. Choose "New Worksheet" (so original data stays intact)
4. Drag fields to areas:
   - Product to Rows
   - Region to Columns
   - Sales to Values (auto-sums)
5. Click OK

**Calculated Fields (for derived metrics)**
Suppose you have Sales and Units, and want to add Price per Unit:
1. Right-click any value cell in pivot table
2. Insert → Calculated Field
3. Name: "Price per Unit"
4. Formula: =Sales/Units
5. Click OK (adds new column to values)

**Grouping by Date**
If a date field is in rows:
1. Right-click a date cell
2. Group → Choose grouping (by Month, Quarter, Year, or Days/Weeks)
3. Pivot table now shows rolled-up dates

**Slicers (Interactive Filters)**
Add clickable buttons to filter the pivot:
1. Click pivot table
2. Insert → Slicer
3. Choose field to slice (e.g., Region)
4. Check boxes you want visible
5. The pivot updates; click boxes to filter

### Step 4: Chart Selection by Analysis Type
Right chart type tells the story faster than raw numbers.

**Comparison (Which is bigger?)**
- **Bar chart** (horizontal) for comparing items with long labels
- **Column chart** (vertical) for comparing items with short labels
  ```
  Example: Sales by Region (East=$2M, West=$3.5M, South=$1.8M)
  Use column or bar; let the longer labels dictate orientation
  ```
- Avoid pie charts for comparison (bar is more accurate to the eye)

**Trend (Does it go up or down?)**
- **Line chart** for one metric over time
  ```
  Example: Monthly revenue trend (Jan–Dec)
  Shows peaks (holiday season), valleys (summer slow), direction
  ```
- **Area chart** for cumulative trend (don't use unless you have a reason)
- Never use pie charts for trends (pie is static, not temporal)

**Composition (What's the breakdown?)**
- **100% Stacked Bar** shows share of total over time
  ```
  Example: Revenue by product type (Product A 40%, Product B 35%, Product C 25%)
  Each bar = 100%; easier to compare slices than separate pie charts
  ```
- **Stacked Column** shows total AND composition
  ```
  Example: Quarterly revenue stacked by region (shows total growth AND regional shifts)
  ```
- Pie chart only if ≤3 slices and you really need the circle (avoid if possible)

**Relationship/Correlation**
- **Scatter plot** for correlation between two metrics
  ```
  Example: Sales vs. Marketing Spend (each point = 1 company/region)
  Upward trend = positive correlation; tight cluster = strong correlation
  ```
- Add a trendline: Right-click data series → Add Trendline

**Part-to-Whole Over Time**
- **Waterfall chart** shows contribution (starting balance + adds − subtracts = ending balance)
  ```
  Example: Net income bridge (Revenue − COGS − OpEx − Taxes = Net Income)
  Each bar = one component; stacked; clear where money goes
  ```

**Distribution (How spread out?)**
- **Histogram** (column chart with continuous bins) shows shape of data
  ```
  Example: Order values ($0–$100, $100–$200, $200+)
  Shows if most customers are small, medium, or high-value
  ```

### Step 5: Conditional Formatting
Apply colors, icons, or data bars to highlight patterns without a separate legend.

**Data Bars** (fill cell with bar proportional to value)
1. Select range (e.g., sales column)
2. Home → Conditional Formatting → Data Bars
3. Choose color (blue for increasing, red for problem areas)
4. Shows value + visual bar in one cell

**Color Scales** (gradient from low to high)
1. Select range
2. Conditional Formatting → Color Scales
3. Choose 2-color (red-green) or 3-color (red-yellow-green)
4. Min values = red, max = green (or custom)
   ```
   Example: Product margins (low margin red, high margin green)
   Instantly see which products are most profitable
   ```

**Icon Sets** (traffic light, up/down arrows)**
1. Select range
2. Conditional Formatting → Icon Sets
3. Choose set (3-Icon: Red-Yellow-Green traffic light)
4. Define thresholds: Red (bottom 33%), Yellow (middle 33%), Green (top 33%)
5. Use for status tracking (RAG analysis)

**Highlight Cells Rules** (static conditions)
1. Select range
2. Conditional Formatting → Highlight Cells Rules
3. Options: Greater Than, Less Than, Between, Duplicate Values, Text Contains
4. Example: Highlight cells > 100,000 in blue

### Step 6: VLOOKUP vs INDEX/MATCH Decision Tree
Both do lookups, but have trade-offs. Know when to use each.

**VLOOKUP (Simpler, but Fragile)**
```
=VLOOKUP(lookup_value, table_array, col_index_num, [range_lookup])

Example: Look up product code in column A, return price from column 3:
=VLOOKUP("PROD123", A:C, 3, FALSE)
                     ↑      ↑
              lookup table  return col 3

Pros: Simpler syntax, faster to write
Cons: Only looks RIGHT (if lookup column is on right, VLOOKUP fails)
      Column number is fragile (if columns shift, formula breaks)
```

**INDEX/MATCH (Flexible, More Robust)**
```
=INDEX(return_array, MATCH(lookup_value, lookup_array, 0))

Example: Look up product code in column A, return price from column C:
=INDEX(C:C, MATCH("PROD123", A:A, 0))
        ↑                       ↑
   what to return         what to find

Pros: Looks left or right, returns dynamic column, handles column shifts better
Cons: Slightly longer syntax
```

**Decision**
- **Use VLOOKUP** when lookup column is to the LEFT of return column and you need speed
- **Use INDEX/MATCH** when lookup column is to the RIGHT, or columns might shift
- **Use XLOOKUP** (Excel 365+) for simplest syntax: =XLOOKUP(lookup_value, lookup_array, return_array)

**Multiple Criteria Lookup**
When you need to match on TWO columns (e.g., Product AND Region):
```
=INDEX(return_array, MATCH(1, (lookup_array1 = criteria1) * (lookup_array2 = criteria2), 0))
Entered as array formula: Ctrl+Shift+Enter

Or simpler (Excel 365):
=XLOOKUP(1, (lookup_array1 = criteria1) * (lookup_array2 = criteria2), return_array)
```

### Step 7: Statistical Functions for Analysis
Summarize and understand data distributions.

**Descriptive Statistics**
```
=AVERAGE(range)          → Mean
=MEDIAN(range)           → Middle value (robust to outliers)
=MODE(range)             → Most frequent value
=STDEV(range)            → Standard deviation (spread from mean)
=MIN(range), =MAX(range) → Extremes
=QUARTILE(range, quart)  → Percentiles (quart 0=min, 1=25%, 2=50%, 3=75%, 4=max)
```

**Correlation**
```
=CORREL(array1, array2)  → How strong is the relationship? (−1 to +1)
  +1 = perfect positive correlation (both go up together)
   0 = no correlation
  −1 = perfect negative correlation (one up, one down)

Example: =CORREL(MarketingSpend, Sales) → 0.78 (strong correlation)
Interpret: For every $1M in marketing, sales tend to rise (but causation isn't proved)
```

**Percentile Rank**
```
=PERCENTRANK(array, value) → What % of values are below this one?
Example: =PERCENTRANK($C$2:$C$100, C5) → 0.85
Interpret: This value ranks in the 85th percentile (higher is better)
```

### Step 8: Power Query Basics (ETL for Excel)
For repetitive import/clean operations, Power Query automates the workflow.

**Create a Power Query**
1. Data → Get Data → From File → From Excel Workbook (or From CSV, etc.)
2. Select file and sheet
3. Power Query Editor opens (preview of data)
4. Applied Steps panel shows each transformation:
   - Source
   - Promoted Headers (if row 1 is headers)
   - Removed Blank Rows
   - Changed Type (text to number)
5. Add custom steps:
   - Right-click column → Replace Values (e.g., "N/A" → blank)
   - Select column → Transform → Trim (removes spaces)
   - Add Column → Custom Column (formula in Power Query language)
6. Close & Load: Creates table in Excel sheet

**Refresh Data**
Next time you get an updated file:
1. Right-click the data table
2. Refresh (re-runs all Power Query steps)
3. New data is cleaned automatically

## Output Template
```
# {{DATASET NAME}} Analysis

## Data Overview
- **Source**: {{origin, e.g., "exported from Salesforce"}}
- **Date Range**: {{start}}–{{end}}
- **Records**: {{N}} rows
- **Dimensions**: {{columns}}, e.g., "Product, Region, Quarter, Sales, Units"

## Data Cleaning Applied
- [ ] Removed {{N}} duplicate rows
- [ ] Trimmed spaces from {{columns}}
- [ ] Converted {{columns}} from text to numeric/date
- [ ] Removed {{N}} blank rows

## Pivot Table Analysis
| {{Dimension 1}} | {{Dimension 2}} | Sum of {{Metric}} | Count | Average |
|---|---|---|---|---|
| {{value}} | {{value}} | {{result}} | {{N}} | {{avg}} |

## Key Findings
1. **{{Title}}**: {{Quantified insight}}
2. **{{Title}}**: {{Quantified insight}}
3. **{{Title}}**: {{Quantified insight}}

## Charts
- Chart 1: {{Type}} of {{metric}} by {{dimension}} ({{insight}})
- Chart 2: {{Type}} of {{metric}} trend over time ({{insight}})

## Lookup/Join Results
(If analyzing multiple datasets combined)
- Matched {{N}} records from Dataset A to Dataset B
- {{N}} unmatched records in A; {{N}} unmatched in B
```

## Quality Gates
- [ ] Data is deduplicated and cleaned (no "Region " with trailing space)
- [ ] All columns have correct data type (dates are dates, not text)
- [ ] Pivot table sums to expected total (spot-check against raw data)
- [ ] Charts have axis labels and clear titles (e.g., "Sales by Product, 2024")
- [ ] VLOOKUP/INDEX-MATCH formulas reference correctly (test with one known value)
- [ ] Conditional formatting highlights the insight (don't just color for color's sake)
- [ ] Any calculated columns have formulas, not hardcoded values

## Examples

### Good Output (excerpt)
```
Raw Data Sheet: 5,000 sales transactions
After cleaning: 4,987 rows (13 duplicates removed)

Pivot: Sales by Product and Region
|        | East   | West   | South  | Total   |
|--------|--------|--------|--------|---------|
| Widget A | $450K  | $820K  | $320K  | $1.59M  |
| Widget B | $290K  | $410K  | $250K  | $950K   |
| Total    | $740K  | $1.23M | $570K  | $2.54M  |

Chart: Column chart showing Widget A dominates all regions
Conditional Formatting: West region highlighted in green (highest sales)

Lookup Formula: =INDEX($E$2:$E$5000, MATCH(B10, $A$2:$A$5000, 0))
Finds product code in B10 and returns price from column E
```

### Bad Output (what to avoid)
```
Pivot with inconsistent region names: "East", "east", "EAST" counted separately
Formula: =VLOOKUP(B1, C:E, 5, FALSE) → refers to column 5, but table is only C:E (3 cols) = #REF error
Chart titled "Sales" with no axis labels; unclear what the bars represent
Conditional formatting: Entire dataset colored rainbow (decorative, no insight)
Spaces in headers: "Product Name" vs "ProductName" creates two pivot categories
Text formatted as numbers: "$1,234" stays as text; SUM formulas count 0
```

## Common Mistakes

1. **Mistake**: Pivot table shows duplicate categories because data has inconsistent spelling/spacing.
   → **Fix**: TRIM text columns before pivot. Use Data → Remove Duplicates on raw data.

2. **Mistake**: VLOOKUP formula returns #REF because column count doesn't match table range.
   → **Fix**: Use INDEX/MATCH instead. Or count table columns carefully: If table is A:C, col 4 doesn't exist.

3. **Mistake**: Chart type is wrong for the analysis (pie chart to show trend over time).
   → **Fix**: Line chart for trends, bar for comparison, scatter for correlation, waterfall for composition.

4. **Mistake**: Pivot table looks aggregated but doesn't match raw data total.
   → **Fix**: Check for #N/A or errors in raw data. Filter pivot to verify a sample row-by-row.

5. **Mistake**: Conditional formatting is applied but doesn't highlight the insight (colors everything for no reason).
   → **Fix**: Use conditional formatting to flag the top 10%, outliers, or out-of-range values. Not just "make it colorful."

## Anti-Patterns
- Never analyze directly on the import sheet. (Create a clean copy first so you can re-import if needed.)
- Never skip TRIM when data has been copy-pasted from multiple sources. (Trailing spaces break pivot grouping.)
- Never hardcode results like "Total: 2,543" when a SUM formula should calculate it. (Numbers change, hard code doesn't.)
- Never use pie charts when bar charts exist. (Bar charts are more accurate to human perception; pies obscure details.)
- Never VLOOKUP when the lookup column is to the right of the return column. (Use INDEX/MATCH.)
- Never apply conditional formatting without a clear rule (e.g., "highlight all cells with the color red"). (Color should encode meaning: high/low, good/bad, etc.)
