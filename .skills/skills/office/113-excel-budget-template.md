---
name: excel-budget-template
description: "Build budget spreadsheets: income/expense categories, monthly rollups, variance analysis, YTD tracking, forecasts. Use for personal, project, or departmental budgets."
category: office
difficulty: beginner
model_boost: "Fixes weak budgets: no variance analysis, missing forecasts, hardcoded numbers that break when assumptions change."
---

# Excel Budget Template

## Purpose
Create budgets that stay current and show variance. This skill structures income and expense categories, calculates monthly and quarterly rollups, compares actual vs. budget, highlights variances with conditional formatting, tracks year-to-date, and forecasts remaining months. A strong budget answers "Are we on track?" at a glance.

## When to Use
- "Create a budget" for {{year}} (department, project, personal)
- "Build a tracking sheet" for spending
- "Show me variance" from budget vs. actual
- **Do NOT use when**: Complex financial modeling (use 102-excel-financial-modeler); or executive dashboard (use 107-excel-dashboard-builder)

## Instructions

### Step 1: Budget Structure and Column Layout
Organize by time period and comparison.

**Column Layout** (Standard 12-month budget)
```
Column A: Category
Column B: Fixed/Variable flag
Column C: Budget
Column D: Jan Actual
Column E: Jan Variance ($)
Column F: Jan Variance (%)
Column G: Feb Actual
Column H: Feb Variance ($)
Column I: Feb Variance (%)
... [Continue for Mar–Dec]
Column Y: Annual Budget Total
Column Z: Annual Actual Total
Column AA: Annual Variance ($)
Column AB: Annual Variance (%)
```

**Alternative (Compact Layout)** if space is tight
```
Column A: Category
Column B: Annual Budget
Column C: Q1 Budget | D: Q1 Actual | E: Q1 Variance
Column F: Q2 Budget | G: Q2 Actual | H: Q2 Variance
... [Quarterly instead of monthly]
```

**Row Organization**
```
Row 1: Header (Category | Jan Budget | Jan Actual | Jan Variance | ...)
Row 2: (Blank)
Row 3: INCOME SECTION
Row 4:   Product Sales
Row 5:   Service Revenue
Row 6:   Other Income
Row 7: TOTAL INCOME (SUM of rows 4–6)
Row 8: (Blank)
Row 9: COGS / DIRECT COSTS
Row 10:   Cost of Goods
Row 11:   Labor (COGS)
Row 12: TOTAL COGS (SUM rows 10–11)
Row 13: (Blank)
Row 14: GROSS PROFIT (Row 7 − Row 12)
Row 15: (Blank)
Row 16: OPERATING EXPENSES
Row 17:   Salaries
Row 18:   Rent
Row 19:   Utilities
Row 20:   Marketing
Row 21:   Office Supplies
Row 22: TOTAL OpEx (SUM rows 17–21)
Row 23: (Blank)
Row 24: NET INCOME (Row 14 − Row 22)
```

### Step 2: Budget Data Entry (Income and Expenses)
Build the categories.

**Income Categories** (customize to business)
```
Product Sales          [Budget for January: $50,000]
Service Revenue        [Budget: $20,000]
Licensing Fees         [Budget: $5,000]
Other                  [Budget: $2,000]
─────────────────────────────────────
TOTAL INCOME          [Formula: SUM of above = $77,000]
```

**Cost of Goods Sold (COGS)** (if applicable)
```
Raw Materials / Inventory
Labor (COGS)
Shipping / Fulfillment
Returns / Warranty
─────────────────────────────────────
TOTAL COGS            [Formula: SUM = $25,000]
Gross Profit          [Formula: Income − COGS = $52,000]
Gross Margin %        [Formula: Gross Profit / Income = 67.5%]
```

**Operating Expenses** (Fixed vs. Variable)
```
FIXED EXPENSES (same every month)
Salaries & Benefits        $30,000/mo
Rent/Facilities            $8,000/mo
Insurance                  $2,000/mo
─────────────────────────────────────

VARIABLE EXPENSES (may change)
Marketing                  $10,000/mo
Office Supplies            $1,500/mo
Consulting                 $5,000/mo
─────────────────────────────────────

TOTAL OpEx                 $56,500/mo
```

**Bottom Line**
```
OPERATING INCOME (Gross Profit − OpEx)
Interest Expense (if applicable)
Taxes (if applicable)
─────────────────────────────────────
NET INCOME
```

### Step 3: Monthly Actual Data and Formulas
Plug in actual numbers; formulas calculate comparisons.

**Variance Calculation**
```
Variance $ = Actual − Budget
Variance % = (Actual − Budget) / Budget × 100%

Example:
Product Sales:  Budget $50,000, Actual $48,500
Variance $:     $48,500 − $50,000 = −$1,500 (under budget)
Variance %:     (−$1,500) / $50,000 = −3% (3% under budget)

Formula in Excel:
Column D (Actual): =Enter value or formula
Column E (Variance $): =D4 − B4 (Actual − Budget)
Column F (Variance %): =E4 / B4 (formatted as percentage)
```

**YTD Tracking**
```
Column Y (YTD Budget): =SUM(B4:M4) for each row
Column Z (YTD Actual): =SUM(D4, G4, J4, M4, ..., AP4) sum of all month actuals
Column AA (YTD Variance $): =Z4 − Y4
Column AB (YTD Variance %): =AA4 / Y4
```

**Example (First 3 months)**
```
                     | JAN       | JAN       | JAN      | FEB       | FEB       | FEB      | MAR       | MAR       | MAR
Category             | Budget    | Actual    | Variance%| Budget    | Actual    | Variance%| Budget    | Actual    | Variance%
─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
Product Sales        | $50,000   | $48,500   | -3%      | $50,000   | $52,000   | +4%      | $50,000   | $51,200   | +2%
Service Revenue      | $20,000   | $21,000   | +5%      | $20,000   | $19,800   | -1%      | $20,000   | $20,500   | +3%
Other Income         | $7,000    | $6,200    | -11%     | $7,000    | $7,500    | +7%      | $7,000    | $7,100    | +1%
────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
TOTAL INCOME         | $77,000   | $75,700   | -2%      | $77,000   | $79,300   | +3%      | $77,000   | $78,800   | +2%
```

### Step 4: Conditional Formatting (Highlight Variances)
Color-code to show what's on/off track.

**Variance % Conditional Formatting**
```
Select variance % columns (F, I, L, O, ... for monthly; AB for YTD)

Conditional Formatting Rule 1 (Over budget):
  If: Value > 10% (or 5%, depends on tolerance)
  Format: Light red fill
  Example: Marketing actual $12,000 vs. budget $10,000 = +20% → RED

Conditional Formatting Rule 2 (On budget):
  If: Value between −5% and +5%
  Format: Light green fill
  Example: Rent actual $8,000 vs. budget $8,000 = 0% → GREEN

Conditional Formatting Rule 3 (Under budget):
  If: Value < −10%
  Format: Light orange fill (caution; under budget might mean missed opportunity)
  Example: Marketing actual $5,000 vs. budget $10,000 = −50% → ORANGE
```

**Alternative: Icon Sets**
```
Select variance columns
Conditional Formatting → Icon Sets → 3-Symbol (Red/Yellow/Green)
Define thresholds:
  Red:    < −15% or > +15% (significantly off)
  Yellow: −15% to +15% (acceptable variance)
  Green:  Within acceptable range
```

**Budget vs. Actual Dollar Amounts**
```
Select actual amount columns (D, G, J, M, ...)
Conditional Formatting → Data Bars
  Green gradient: 0 to max value
  Larger bars = higher spend (visual comparison)
```

### Step 5: Quarterly and Annual Rollups
Aggregate from months to quarters to year.

**Quarterly Totals** (add summary rows)
```
Q1 BUDGET (Sum of Jan, Feb, Mar):       =SUM(B4:B8) [Jan] + SUM(B9:B13) [Feb] + SUM(B14:B18) [Mar]
Q1 ACTUAL (Sum of Jan, Feb, Mar):       =SUM(D4:D8) + SUM(G4:G8) + SUM(J4:J8)
Q1 VARIANCE:                            =Q1 Actual − Q1 Budget

[Repeat for Q2, Q3, Q4]
```

**Annual Totals**
```
ANNUAL BUDGET:  =SUM(all monthly budgets) OR =Q1 Budget + Q2 Budget + Q3 Budget + Q4 Budget
ANNUAL ACTUAL:  =SUM(all monthly actuals)
ANNUAL VARIANCE:=ANNUAL ACTUAL − ANNUAL BUDGET
```

**Year-to-Date (YTD) Through Current Month**
```
If we're in March (3 months in):
YTD ACTUAL:     =SUM(Jan Actual, Feb Actual, Mar Actual)
YTD BUDGET:     =SUM(Jan Budget, Feb Budget, Mar Budget)
YTD VARIANCE %: (YTD Actual − YTD Budget) / YTD Budget
```

### Step 6: Forecast and Remaining Budget
Project out the year based on current run rate.

**Remaining Budget Calculation**
```
For April–December (remaining 9 months):

Option 1: Assume remaining months = first 3 months average
  March Actual YTD:     $75,000
  Average per month:    $75,000 / 3 = $25,000/mo
  Forecast Apr–Dec:     $25,000 × 9 months = $225,000
  Projected Year Total: $75,000 + $225,000 = $300,000
  Projected Annual Variance: Actual-to-date + Forecast vs. Annual Budget

Option 2: Assume remaining months = annual budget distribution
  Remaining Annual Budget:  $500,000 (annual budget)
  Spent to date (YTD):      $75,000
  Remaining budget:         $500,000 − $75,000 = $425,000
  For Apr–Dec (9 months):   $425,000 / 9 = $47,222/mo

Column AF (Forecast Apr–Dec):  =Remaining Budget × (12 − Current Month) / (12 − Current Month)
Column AG (Projected Year Total): =YTD Actual + Forecast
Column AH (Projected Variance %): =(Projected Year − Annual Budget) / Annual Budget
```

**Alert If Over Budget**
```
If Projected Year Total > Annual Budget:
  Display WARNING in red: "Projected $520K vs. Budget $500K — Over by $20K"
  Formula: =IF(AG > AE, "OVER", "ON TRACK")
```

### Step 7: Summary Dashboard Tab
Executive view of budget health.

**Dashboard Elements**

**Overall Budget Status**
```
BUDGET PERFORMANCE (through March)

Months Completed:           3 of 12
Overall Completion %:       25%
Overall Spend %:            22% (spending less than paced)

Budget:                     $500,000
YTD Actual:                 $75,000
Remaining Budget:           $425,000
Projected Year-End:         $450,000
Projected Variance:         −$50,000 (under budget ✓)
```

**Income vs. Expense Summary**
```
                 | YTD Budget | YTD Actual | Variance $ | Variance %
Income           | $231,000   | $234,000   | +$3,000    | +1.3%
COGS             | $75,000    | $73,000    | −$2,000    | −2.7%
Gross Profit     | $156,000   | $161,000   | +$5,000    | +3.2%
OpEx             | $169,000   | $171,000   | −$2,000    | −1.2%
Net Income       | −$13,000   | −$10,000   | +$3,000    | −23% (better than budgeted)
```

**Top 3 Variances** (largest over/under)
```
Variance Alert (this month):
1. Marketing spend: +$2,000 over budget (need to review campaign)
2. Utilities: −$500 under budget (mild winter ✓)
3. Office Supplies: +$300 over budget (minor)
```

**Trend Chart** (visual)
```
Monthly Budget vs. Actual (bar chart):
Jan:  Budget $50K, Actual $49K
Feb:  Budget $50K, Actual $52K
Mar:  Budget $50K, Actual $51K
(Shows trend; if actual consistently above budget, pattern is clear)
```

### Step 8: Budget Assumptions and Notes
Document what went into the budget.

**Assumptions Sheet** (separate tab or section)
```
BUDGET ASSUMPTIONS (for 2024)

Income Assumptions:
- Product sales growth:     5% vs. 2023
- Service revenue:          Stable (same as 2023)
- New product launch:       Q2 (projected $10K/mo)

COGS Assumptions:
- Material cost increase:   2% due to supplier pricing
- Labor:                    3% annual raise (Jan increase)
- Shipping:                 Stable; no rate increase expected

OpEx Assumptions:
- Salaries:                 3% raise + 2 new hires (mid-year) = +$60K annually
- Rent:                     Locked in contract; no increase
- Marketing:                Increase $5K/mo Q3–Q4 for holiday campaign
- Insurance:                Renewal in June; estimate 5% increase

Risks / Sensitivities:
- If material costs rise >5%, COGS could be $10K over budget
- If hiring delays, labor savings = $20K opportunity
- Economic downturn could reduce sales 10% = $77K impact
```

## Output Template
```
# {{COMPANY/DEPARTMENT}} 2024 Budget

## Budget Summary
- **Budget Owner**: {{Name}}
- **Fiscal Year**: Jan–Dec 2024
- **Total Budget**: ${{X}}
- **Current Month**: {{Mar}}
- **YTD Actual**: ${{X}} ({{%}} of budget paced)
- **Status**: 🟢 ON TRACK / 🟡 WATCH / 🔴 OVER BUDGET

## Budget Tracking Table
| Category | Budget | Jan Actual | Jan Var % | Feb | Feb Var | ... | YTD Budget | YTD Actual | YTD Var % |
|---|---|---|---|---|---|---|---|---|---|
| {{Income}} | ${{X}} | ... | | | | | | | |
| {{Expense}} | | | | | | | | | |

## Variance Analysis
- Largest variance (over): {{Category}} {{Amount}} {{Reason}}
- Largest variance (under): {{Category}} {{Amount}} {{Reason}}

## Forecast
- Projected year-end: ${{X}} (vs. budget ${{X}})
- Projected variance: {{+/−}} ${{X}}

## Assumptions & Notes
[Key assumptions, risks, scenarios]
```

## Quality Gates
- [ ] Income and expense categories are comprehensive (nothing left out)
- [ ] Monthly and YTD totals are calculated correctly (spot-check formulas)
- [ ] Variance is calculated (both $ and %) and color-coded
- [ ] Conditional formatting highlights variances >5% or >10% (configurable)
- [ ] Forecast is transparent (assumptions documented, not black-box)
- [ ] Budget can be updated without breaking formulas (inputs separated from calcs)
- [ ] Quarterly and annual rollups exist (easy to see trends)
- [ ] Assumptions are documented (why numbers were chosen; what changed)

## Examples

### Good Output (excerpt)
```
[Budget Table - First 3 months]
                         JAN        JAN        JAN       FEB        FEB       FEB       MAR       MAR        MAR
Category                 Budget     Actual     Var %     Budget     Actual    Var %     Budget    Actual     Var %
─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
INCOME
Product Sales            $50,000    $48,500    -3%       $50,000    $52,000   +4%       $50,000   $51,200    +2%
Service Revenue          $20,000    $21,000    +5%       $20,000    $19,800   -1%       $20,000   $20,500    +3%
─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
TOTAL INCOME             $70,000    $69,500    -1%       $70,000    $71,800   +3%       $70,000   $71,700    +2%

EXPENSES
Salaries                 $30,000    $30,000     0%       $30,000    $30,000    0%       $30,000   $30,000     0%
Rent                     $8,000     $8,000      0%       $8,000     $8,000     0%       $8,000    $8,000      0%
Marketing                $10,000    $12,000    +20%      $10,000    $9,200    -8%       $10,000   $11,500    +15%
─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
TOTAL OpEx               $48,000    $50,000    +4%       $48,000    $47,200   -2%       $48,000   $49,500    +3%

NET INCOME               $22,000    $19,500   -11%       $22,000    $24,600   +12%      $22,000   $22,200    +1%

YTD Summary:
YTD Budget: $216,000
YTD Actual: $218,500 (+$2,500, +1.2%)
Status: ON TRACK ✓

Forecast (Full Year):
Projected Year-End: $264,000 (based on YTD pace)
Annual Budget: $264,000
Projected Variance: $0 (dead-on budget!)
```

### Bad Output (what to avoid)
```
Budget with no monthly breakdown; annual total only
No actual data entered; just budgets
Variance calculated wrong (doesn't match budget − actual)
No variance highlighting; visually no signal of over/under
Hardcoded values everywhere; can't update assumptions
Missing categories (what about rent? utilities? etc.)
YTD calculations don't match monthly sums
No forecast; can't tell if on track for year-end
Assumptions not documented; why is marketing $10K/mo?
```

## Common Mistakes

1. **Mistake**: Variance is calculated as Actual − Variance instead of Actual − Budget.
   → **Fix**: Variance = Actual − Budget. If negative = under budget (good for expenses, bad for income). Format clearly.

2. **Mistake**: Budget is hardcoded; changing assumptions breaks everything.
   → **Fix**: Create Assumptions sheet; reference assumptions in budget formulas.

3. **Mistake**: Monthly data entered but no rollups; can't see quarterly/annual trends.
   → **Fix**: Add quarterly total rows and annual total row with SUM formulas.

4. **Mistake**: Variance highlighting is decorative; doesn't flag actionable issues.
   → **Fix**: Conditional format to highlight >5% variance in red (investigate why).

5. **Mistake**: YTD totals don't match; formulas are inconsistent.
   → **Fix**: YTD = SUM of months 1–current. Spot-check: Jan + Feb + Mar = YTD.

## Anti-Patterns
- Never hardcode budget values; always use a source/assumptions sheet. (Assumptions change; formulas reference should be dynamic.)
- Never skip variance analysis. (Variance $ tells what amount; variance % tells if it's significant.)
- Never assume budget will stay fixed. (Budgets are living documents; review/update quarterly.)
- Never hide assumptions. (Document why each budget number was chosen; future you will need context.)
- Never ignore variances >10%. (If marketing is 20% over, investigate why; is it a one-time or trend?)
- Never forecast without documenting methodology. (Why are you assuming remaining months = average? Be explicit.)
