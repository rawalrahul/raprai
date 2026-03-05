---
name: excel-financial-modeler
description: "Build three-statement financial models (P&L, balance sheet, cash flow) linked by formulas. Use when asked to model revenue, expenses, profit margins, or forecast cash flow."
category: office
difficulty: advanced
model_boost: "Fixes weak models with broken formula links, hardcoded numbers, or balance sheets that don't actually balance."
---

# Excel Financial Modeler

## Purpose
Construct professional three-statement financial models where P&L flows to balance sheet, balance sheet to cash flow, all linked by formulas. This skill ensures models are auditable, scenario-ready, and mathematically sound. A proper model separates inputs (assumptions) from calculations (formulas) from outputs (dashboard), making it easy to change one number and see cascading impacts.

## When to Use
- "Build me a financial forecast" (needs full three-statement model)
- "Model the impact of [pricing change/cost reduction/revenue scenario]"
- "I need a sensitivity analysis" (data tables on assumptions)
- "What's our cash runway?" (cash flow projection)
- **Do NOT use when**: Just creating a simple budget tracker; use 113-excel-budget-template instead

## Instructions

### Step 1: Model Architecture—Inputs, Calculations, Outputs
Every professional financial model has three distinct sheets (can be tabs):

**Inputs Sheet** (all assumptions live here)
- Revenue drivers: Growth rate, units sold, price per unit, mix by segment
- COGS drivers: % of revenue, or per-unit cost
- OpEx drivers: Headcount salaries, rent, G&A as % of revenue
- Working capital: Days sales outstanding (DSO), days inventory outstanding (DIO), days payable outstanding (DPO)
- Capital: capex % of revenue, depreciation assumptions
- Other: Tax rate, discount rate, interest rates
- Color code inputs in BLUE so it's obvious what can be changed

**Calculations Sheet** (all formulas here, linked to inputs)
- P&L: Revenue → COGS → Gross profit → OpEx → EBIT → Interest → Taxes → Net income
- Balance sheet: Assets (cash, AR, inventory, PPE) = Liabilities (AP, debt) + Equity
- Cash flow: Net income + depreciation + change in working capital + capex − debt repayment = change in cash

**Outputs Sheet** (dashboard view, no formulas except references)
- Key metrics: Revenue, gross margin %, net margin %, ROIC
- Charts: Waterfall of income, cash flow bridge, trend lines
- Ratio analysis: Current ratio, debt-to-equity, quick ratio

### Step 2: Build the Income Statement (P&L)
Start with revenue drivers, then expense structure.

**Revenue Calculation**
```
Inputs: Annual growth rate (B2), prior year revenue (B3), Units (B4), Price (B5)

Year 1 Revenue = Prior Year Revenue × (1 + Growth Rate)
OR
Year 1 Revenue = Units × Price per Unit

Example (3-year forecast):
         | Year 1    | Year 2         | Year 3
Revenue  | 10,000,000 | =B2*(1+$B$5) | =C2*(1+$B$5)

Use absolute reference ($B$5) for growth rate so it doesn't shift when copied.
```

**Cost of Goods Sold (COGS)**
Method 1: % of revenue (simpler, less detailed)
```
COGS = Revenue × COGS % of Revenue
Year 1 COGS = $B$2 * B2 (where B2 is revenue, $B$2 is COGS % input)
```

Method 2: Per-unit cost (more detailed)
```
COGS = Units × Cost per Unit
Year 1 COGS = B4 * $B$10 (units × cost per unit)
```

**Gross Profit & Margin**
```
Gross Profit = Revenue − COGS
Gross Margin % = Gross Profit / Revenue
=B2/(B2−B3) formatted as percentage
```

**Operating Expenses (OpEx)**
Break into categories:
- Salaries: Headcount × average salary (more auditable than a lump sum)
  ```
  Salaries = Headcount × Avg Salary per Role
  =(B$12 + B$13 + B$14) × $B$20 (sum of headcount by role, multiply by avg salary)
  ```
- Facilities: Rent + utilities (often fixed, or % of revenue)
- G&A: General & admin, marketing (% of revenue common)
- R&D: Product development (% of revenue or fixed)

```
Total OpEx = Salaries + Facilities + G&A + R&D
```

**EBIT (Earnings Before Interest & Taxes)**
```
EBIT = Gross Profit − Total OpEx
```

**Interest Expense**
```
Interest = Beginning Debt Balance × Interest Rate
=(C2 from balance sheet) × $B$30
```

**Taxes**
```
Taxable Income = EBIT − Interest
Taxes = Taxable Income × Tax Rate
=(B2−B3) × $B$32
```

**Net Income**
```
Net Income = Taxable Income − Taxes
=(B2−B3) × (1 − Tax Rate)
```

### Step 3: Build the Balance Sheet
Link to P&L and maintain the accounting equation: Assets = Liabilities + Equity

**Assets Section**
- **Cash**: Calculated in cash flow, linked here
  ```
  Cash (Year 1) = Prior Year Cash + Operating Cash Flow − Investing CF − Financing CF
  ```
- **Accounts Receivable (AR)**: Days sales outstanding assumption
  ```
  AR = (Revenue / 365) × DSO
  =(B2/365) × $B$35 (DSO from inputs)
  ```
- **Inventory**: Days inventory outstanding assumption
  ```
  Inventory = (COGS / 365) × DIO
  =(B3/365) × $B$36
  ```
- **Fixed Assets (PP&E, net)**: Prior year + capex − depreciation
  ```
  PP&E Net = Prior Year PP&E + CapEx − Depreciation
  =(D2 + B5 − B6) from P&L
  ```

**Liabilities Section**
- **Accounts Payable (AP)**: Days payable outstanding assumption
  ```
  AP = (COGS / 365) × DPO
  =(B3/365) × $B$37
  ```
- **Debt**: Prior year debt + new borrowing − repayment
  ```
  Debt (Year 1) = Prior Year Debt + New Debt Issued − Principal Repayment
  ```
- **Other liabilities**: Accrued expenses, deferred revenue (if applicable)

**Equity Section**
- **Beginning Equity**: Prior year closing equity
- **+ Net Income**: From P&L
- **− Dividends Paid**: If applicable (often $0 in growth model)
- **= Ending Equity**

**Balance Check Formula**
```
In a helper cell: =IF(Total Assets = Total Liabilities + Equity, "BALANCED", "ERROR")
```
This must show "BALANCED" or your model is broken.

### Step 4: Build the Cash Flow Statement
Three sections: Operating, Investing, Financing.

**Operating Cash Flow (Direct Method)**
```
Net Income (from P&L)
+ Depreciation & Amortization (non-cash expense)
+ Change in Working Capital:
  − (Increase in AR) = −(AR Year 1 − AR Year 0)
  − (Increase in Inventory)
  + (Increase in AP)
= Operating Cash Flow
```

Example:
```
         | Year 1
Net Income | 1,500,000
+ Depreciation | 250,000
− Δ AR | −(120,000 − 100,000) = −20,000
− Δ Inventory | −(80,000 − 75,000) = −5,000
+ Δ AP | (90,000 − 80,000) = 10,000
= Operating CF | 1,735,000
```

**Investing Cash Flow**
```
− CapEx (capital expenditure)
− Other investments (acquisitions, if any)
= Investing Cash Flow (always negative or zero)
```

**Financing Cash Flow**
```
+ Debt issued
− Debt repaid
− Dividends paid
= Financing Cash Flow
```

**Ending Cash**
```
Beginning Cash + Operating CF + Investing CF + Financing CF = Ending Cash
(This Ending Cash ties to balance sheet cash line)
```

### Step 5: Create Named Ranges for Auditing
Named ranges make formulas readable and prevent errors.

In Excel: Formulas → Define Name
```
Input_GrowthRate = $B$5
Input_COGS_Pct = $B$7
Year1_Revenue = $C$2
Year1_NetIncome = $C$8
```

Then write formulas as:
```
=Year1_Revenue * Input_COGS_Pct (instead of =C2*$B$7)
```

This is self-documenting and easier to audit.

### Step 6: Formula Auditing Checklist
Before declaring a model done:

**Formula Hygiene**
- [ ] No hardcoded numbers except in Inputs sheet
- [ ] All assumptions are in one Inputs sheet (nothing scattered)
- [ ] Formulas use absolute references ($B$5) for inputs, relative for calculations
- [ ] Test: Change one input; all outputs should update

**Cross-Sheet Integrity**
- [ ] P&L revenue flows to balance sheet
- [ ] Balance sheet ending cash = cash flow ending cash
- [ ] Balance sheet MUST balance (Assets = Liabilities + Equity)
- [ ] Cash flow ties: Ending cash = Beginning cash + net cash change

**Reasonability Checks**
- [ ] Margins are realistic (not 95% gross margin for a service biz unless verified)
- [ ] Growth rate matches industry (50% growth means explaining competitive advantage)
- [ ] Headcount growth makes sense with revenue growth
- [ ] No negative cash balance unless financing is planned

### Step 7: Scenario & Sensitivity Analysis
Build flexibility into the model for "what-if" analysis.

**Scenario Method: Data Tables**
Create a sensitivity table for two variables (e.g., growth rate vs COGS %)

```
         | Growth 5% | Growth 10% | Growth 15%
COGS 50% | Net Inc $X | Net Inc $Y | Net Inc $Z
COGS 55% |     $    |     $      |     $
COGS 60% |     $    |     $      |     $
```

In Excel Data Table:
1. Create this table structure
2. Set top row to: =Reference to output cell (e.g., Year 1 Net Income)
3. Select the entire table
4. Data → What-If Analysis → Data Table
5. Row input cell: growth rate assumption cell
6. Column input cell: COGS % assumption cell

**Goal Seek: Reverse Calculation**
Find what growth rate is needed to reach a target net income:
1. Tools → Goal Seek
2. Set cell: Net Income cell
3. To value: Target (e.g., 2,000,000)
4. By changing cell: Growth rate assumption
5. Excel solves for the growth rate needed

### Step 8: Dashboard & Key Metrics
On Outputs sheet, create summary metrics:

```
METRIC                    | YEAR 1      | YEAR 2      | YEAR 3
Revenue                   | =P&L!C2     | =P&L!D2     | =P&L!E2
Gross Margin %            | =P&L!C4/C2  | =P&L!D4/D2  | =P&L!E4/E2
EBIT Margin %             | =P&L!C8/C2  | =P&L!D8/D2  | =P&L!E8/E2
Net Income                | =P&L!C12    | =P&L!D12    | =P&L!E12
Free Cash Flow            | =CF!C15     | =CF!D15     | =CF!E15
Ending Cash               | =BS!C50     | =BS!D50     | =BS!E50
Debt-to-Equity Ratio      | =BS!C45/C48 | =BS!D45/D48 | =BS!E45/E48
```

Add conditional formatting: Green for healthy margins, red for low cash.

## Output Template
```
# {{COMPANY}} Financial Model

## Model Period
{{3-year | 5-year | 10-year}} forecast, Years {{YYYY}}–{{YYYY}}

## Assumptions (Inputs Sheet)
| Assumption | Year 1 | Year 2 | Year 3 | Notes |
|---|---|---|---|---|
| Revenue Growth | {{X}}% | {{X}}% | {{X}}% | Based on {{market research/historical/conservative}} |
| COGS % of Revenue | {{X}}% | {{X}}% | {{X}}% | Declining due to {{scale/automation}} |
| Headcount | {{N}} | {{N}} | {{N}} | {{N}} engineers, {{N}} sales, {{N}} ops |
| Tax Rate | {{X}}% | {{X}}% | {{X}}% | {{jurisdiction}} corporate tax |
| DSO (Days Sales Outstanding) | {{N}} | {{N}} | {{N}} | {{explanation}} |
| Capex % of Revenue | {{X}}% | {{X}}% | {{X}}% | {{explanation}} |

## Model Outputs (Outputs Sheet)
| Metric | Year 1 | Year 2 | Year 3 |
|---|---|---|---|
| Revenue | ${{X}}M | ${{X}}M | ${{X}}M |
| Gross Margin % | {{X}}% | {{X}}% | {{X}}% |
| Net Income | ${{X}}M | ${{X}}M | ${{X}}M |
| Operating Cash Flow | ${{X}}M | ${{X}}M | ${{X}}M |
| Free Cash Flow | ${{X}}M | ${{X}}M | ${{X}}M |
| Ending Cash | ${{X}}M | ${{X}}M | ${{X}}M |
| Debt-to-Equity | {{X}}x | {{X}}x | {{X}}x |

## Sensitivity Analysis
Impact on Year 3 Net Income of changes in revenue growth and COGS %:
| | Growth +5% | Growth +10% | Growth +15% |
|---|---|---|---|
| COGS 50% | ${{X}}M | ${{X}}M | ${{X}}M |
| COGS 55% | ${{X}}M | ${{X}}M | ${{X}}M |
| COGS 60% | ${{X}}M | ${{X}}M | ${{X}}M |

## Model Integrity Checks
- [ ] Balance sheet balances (Assets = Liabilities + Equity)
- [ ] Cash flow ending cash = balance sheet ending cash
- [ ] All inputs on single Inputs sheet, hardcoded nowhere else
- [ ] All formulas use absolute ($) for inputs, relative for calculations
- [ ] Change one assumption, all outputs update (no broken links)
- [ ] Margins realistic for industry {{industry}}
```

## Quality Gates
- [ ] Balance sheet BALANCES (no #N/A or formula errors)
- [ ] Cash flow reconciles to balance sheet ending cash
- [ ] All assumptions are in one Inputs sheet (zero hardcoded numbers elsewhere)
- [ ] P&L, balance sheet, cash flow are linked (not separate calculations)
- [ ] Sensitivity table shows impact of 2+ variables on outcome
- [ ] Margins pass reasonability test (e.g., SaaS 70%+ gross margin, not 30%)
- [ ] Model can be updated with one year of new data without restructuring
- [ ] Debt is modeled (either fixed or calculated based on EBITDA covenant)

## Examples

### Good Output (excerpt)
```
# TechStartup Inc. 3-Year Financial Model

Inputs Sheet (rows 1-40, all cells colored blue):
B5:  Revenue Growth (Yr 1 to 2): 35%
B7:  COGS % of Revenue: 32%
B10: Total Headcount (Year 1): 24
B32: Tax Rate: 21%
B35: DSO: 45 days

Calculations Sheet P&L:
C2 (Year 1 Revenue): 5,000,000
C3 (Year 1 COGS): =C2 * $B$7 → 1,600,000
C4 (Gross Profit): =C2 − C3 → 3,400,000
C8 (EBIT): 1,800,000
C12 (Net Income): 1,421,000

Balance Sheet:
C20 (AR): =(C2/365)*$B$35 → 616,438
C45 (Total Debt): 2,000,000
C48 (Equity): 3,421,000
Check: C50 (Total Assets) = C48+C49 → BALANCED ✓

Cash Flow:
C2: Net Income 1,421,000
C3: + Depreciation 200,000
C4: − Δ AR −(616−550) → −66,000
C15: = Operating CF 1,555,000

Outputs Sheet:
Debt-to-Equity Ratio: =BS!C45/BS!C48 → 0.58x (healthy)
Year 3 Ending Cash: =CF!E15 → 4,200,000 (positive runway)
```

### Bad Output (what to avoid)
```
"Model" with hardcoded numbers everywhere:
Row 5: Revenue 5,000,000 (hardcoded)
Row 6: COGS 1,600,000 (hardcoded)
No inputs sheet, assumptions scattered across sheets
Balance sheet shows Assets = $8M, Liabilities+Equity = $7.5M (doesn't balance, error ignored)
Cash flow ending cash $4M doesn't match balance sheet ending cash $3.5M
Sensitivity analysis with only ONE variable changed
Margins: Gross 92%, COGS 5% (unrealistic, no explanation)
Formula: =5000000*0.32 instead of =Revenue * $COGS_Pct (not auditable)
No named ranges, model breaks if columns shift
```

## Common Mistakes

1. **Mistake**: Hardcoding assumptions in calculation cells.
   → **Fix**: Create Inputs sheet. Reference inputs with absolute cell references ($B$5). Change one cell, model updates everywhere.

2. **Mistake**: P&L doesn't link to balance sheet; balance sheet doesn't link to cash flow.
   → **Fix**: Balance sheet AR = P&L revenue−based calculation. Cash flow ending cash = balance sheet cash. Test: change revenue assumption, all three statements should update.

3. **Mistake**: Balance sheet doesn't balance (Assets ≠ Liabilities + Equity).
   → **Fix**: Create a check formula: =IF(Total Assets = Total Liab + Equity, "OK", "ERROR"). Fix the error before sharing.

4. **Mistake**: Using hardcoded percentages instead of calculation-based formulas.
   → **Fix**: Net Income Year 2 should be =Year2_Revenue − Year2_COGS − Year2_OpEx, not a typed number.

5. **Mistake**: Not modeling working capital changes (AR, inventory, AP).
   → **Fix**: Calculate AR = (Revenue/365)*DSO. Inventory = (COGS/365)*DIO. These drive cash flow timing.

## Anti-Patterns
- Never hardcode numbers outside Inputs sheet. (This breaks the model when assumptions change.)
- Never forget to link sheets. (P&L revenue should flow to BS AR calculation; BS ending cash should match CF.)
- Never assume balance sheets will balance "close enough." (Off by even $1 signals a broken formula.)
- Never omit the cash flow statement. (Revenue ≠ cash; a profitable company can run out of cash.)
- Never build a model with ONLY historical data and no forward assumptions. (Model means forecast, not just past numbers.)
- Never use hard references (C2) instead of named ranges when there are many assumptions. (You'll lose track of what depends on what.)
