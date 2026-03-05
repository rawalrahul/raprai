---
name: real-estate-analysis
description: "Analyze real estate investments using comparable market analysis (CMA), cash flow projections, cap rate and IRR calculations, DSCR, renovation ROI, neighborhood scoring, and investment memo format. Includes return benchmarks."
category: professional
difficulty: advanced
model_boost: "Weak models lack financial rigor on cash flow assumptions, DSCR calculations, or neighborhood risk assessment"
---

# Real Estate Analysis

## Purpose
Real estate investing requires rigorous financial analysis to avoid overleveraged deals and poor location choices. This skill combines market research (comparable sales, neighborhood trends), financial modeling (cash flows, returns), and risk assessment (interest rate sensitivity, vacancy assumptions). A strong property analysis answers: Is this deal worth the capital deployed? What's the downside if assumptions miss? The analysis becomes the decision document—do you bid on this property or walk away?

## When to Use
- **Evaluating a potential property acquisition** (before making an offer)
- **Analyzing a portfolio** (which properties to hold, sell, or refinance)
- **Assessing a renovation project** (understanding ROI and cost overrun risk)
- **Comparing investment options** (property A vs. property B; cash vs. leverage)
- **Do NOT use when**: Quick comps for insurance purposes (simpler requirement), appraising for refinance (use a licensed appraiser), or managing an operating property (use different operational dashboards)

## Instructions

### Step 1: Conduct Comparable Market Analysis (CMA)
Find comparable sales in the same neighborhood to establish market value. CMA is your anchor for all subsequent analysis.

**CMA Components**:

1. **Property Selection** (Choose 3-5 comparable sales):
   - Sold in last 6 months (more recent = more relevant)
   - Same neighborhood or within 0.5 miles
   - Similar property type (single-family, duplex, etc.)
   - Similar size (within 500 sq ft and 0.25 acres for land)
   - Similar condition (avoid distressed sales or gut rehabs)

2. **Price Adjustment**:

   | Comparable | Price | Sq Ft | $/Sq Ft | Beds/Baths | Sold Date | Condition Adjustment |
   |-----------|-------|-------|---------|-----------|-----------|-------------------|
   | Comp 1 | $450K | 2100 | $214 | 3/2 | 6 mo ago | -$15K (older roof) |
   | Comp 2 | $465K | 2150 | $216 | 3/2 | 4 mo ago | $0 (similar condition) |
   | Comp 3 | $480K | 2200 | $218 | 3/2 | 2 mo ago | +$10K (updated kitchen) |

   **Adjusted Average**: ($435K + $465K + $490K) / 3 = **$463K estimated market value**

3. **Market Metrics** to extract from comps:
   - **Days on market**: Average time to sell (fast market = 14 days; slow market = 90 days)
   - **List-to-sale ratio**: Asking price vs. actual sale price (hot market = 100%+; soft market = 95%)
   - **Price per square foot trend**: Is it rising or declining month-over-month?

**CMA Conclusion**:
"Subject property in this neighborhood is trading at $214-218 per square foot. Recent comparables support a market value of $463K-475K. The market is balanced (45-day DOM average), suggesting moderate competition."

### Step 2: Build Annual Cash Flow Projection
Project income and expenses to understand what cash the property will generate annually.

**Income Side**:

| Item | Amount | Notes |
|------|--------|-------|
| Gross Rental Income | $24,000 | Based on $2,000/mo; market rent per comps/listings |
| Vacancy Rate | -$1,200 | -5% (conservative; market average 3-5%) |
| **Effective Gross Income** | **$22,800** | |

**Expense Side**:

| Expense Category | Annual Amount | Notes |
|---|---|---|
| Property Tax | $3,600 | From county assessor; no major reassessment expected |
| Insurance | $1,200 | Homeowners; updated to current market rates |
| Maintenance & Repairs | $1,440 | 6% of EGI (industry standard for residential) |
| HOA or Common Area Fees | $0 | N/A for this property |
| Utilities (if applicable) | $0 | Tenant-paid under lease |
| Management Fee | $912 | 4% of EGI (if hiring property manager) |
| Vacancy / Turnover | $1,200 | Already deducted above in vacancy rate |
| **Total Operating Expenses** | **$8,352** | |

**Net Operating Income (NOI)**:
$22,800 (EGI) - $8,352 (OpEx) = **$14,448 annual NOI**

**Key Insight**: This property generates $14,448/year in net cash before debt service (mortgage payments). If you purchase with 20% down ($95K) and finance the rest, you'll owe that mortgage payment first, and the remainder is your cash flow.

### Step 3: Calculate Capitalization Rate (Cap Rate)
Cap rate shows the return on your cash invested, assuming no mortgage.

**Formula**: Cap Rate = Net Operating Income / Property Value

**Example**: $14,448 NOI / $465,000 (market value from CMA) = **3.1% cap rate**

**What it means**: If you paid all-cash for this property, you'd earn a 3.1% annual return. Compared to:
- Treasury bonds: 4-5% risk-free
- Stock market: 7-10% historical average
- This property: 3.1% return

**Verdict**: 3.1% is low unless you expect appreciation or are in a slow-growth market where cash-on-cash returns matter more.

**Cap Rate Context** (varies by market and property type):
- Strong rental markets: 5-8% cap rate
- Average suburban markets: 4-6% cap rate
- Weak markets or trophy properties: 2-4% cap rate
- Development/speculation plays: Lower cap rate is acceptable if appreciation expected

### Step 4: Model Financing & Calculate Cash-on-Cash Return
Most real estate is purchased with debt. This calculation shows the cash return on your invested equity.

**Loan Assumptions**:
- Loan amount: 80% of $465K = $372K
- Down payment (your cash): 20% of $465K = $93K
- Interest rate: 6.5% (current market)
- Loan term: 30 years
- Monthly payment: $2,373

**Annual Debt Service**: $2,373/mo × 12 = **$28,476/year**

**Cash Flow After Debt Service**:
- NOI: $14,448
- Debt service: -$28,476
- **Annual cash flow: -$14,028** (negative! This deal doesn't work.)

**Cash-on-Cash Return**:
Annual cash flow / Cash invested = -$14,028 / $93,000 = **-15.1%**

**Verdict**: This property is cash-flow negative. You'd lose money monthly. This only works if:
1. You expect significant appreciation (gambling, not investing)
2. You can raise rents 30%+ (unlikely in stable market)
3. You're buying for a different reason (tax shelter, portfolio diversification)

**Decision**: Pass on this deal, or renegotiate the purchase price down 15-20%.

### Step 5: Analyze Debt Service Coverage Ratio (DSCR)
Lenders use DSCR to decide if they'll finance the deal. DSCR = NOI / Debt Service.

**Formula**: DSCR = NOI / Annual Debt Service

**Example**: $14,448 / $28,476 = **0.51 DSCR**

**Lender Perspective**:
- DSCR above 1.25: Property generates 25% more income than needed to pay debt. Lender comfortable.
- DSCR 1.0 - 1.25: Break-even to modest coverage. Lender requires strong guarantor or larger down payment.
- DSCR below 1.0: Property doesn't generate enough to cover debt. **Most lenders won't finance.** You'd need 30%+ down and strong personal credit.

**For this property at 0.51**: You'd need 40%+ down payment to get traditional financing. This is why the deal is weak.

### Step 6: Project Internal Rate of Return (IRR)
IRR shows the annualized return you'd earn over your hold period, including appreciation and cash flow.

**Assumptions**:
- Holding period: 10 years
- Annual appreciation: 3% (historical average for neighborhood)
- Cash flow, year 1: -$14,028 (negative, from previous calculation)
- Annual cash flow growth: 3% (rents rise with inflation)
- Sale price, year 10: Current price × 1.03^10 = $465K × 1.34 = **$623K**
- Loan balance at sale (year 10): $330K (remaining debt after 10 years of payments)
- Net proceeds at sale: $623K - $330K (payoff) - $32K (closing costs) = **$261K**

**Cash Flow Timeline**:
- Year 0 (today): -$93,000 (your down payment; negative outflow)
- Years 1-10: -$14,028 annually (negative cash flow; you subsidize property)
- Year 10: +$261,000 (net proceeds from sale)

**IRR Calculation**: Using a financial calculator or spreadsheet (IRR function):
Inputs: -93K, -14K, -14K, -14K, -14K, -14K, -14K, -14K, -14K, -14K, +247K
**IRR: 4.2%**

**Verdict**: 4.2% IRR over 10 years is poor. You could get 5%+ in bonds with zero effort and no negative cash flow. **This deal is a pass.**

### Step 7: Estimate Renovation ROI
If the property needs work, model the cost and return separately.

**Renovation Scenario**: Assume $50K in renovations (new kitchen, bathroom updates, flooring).

**Approach 1: Direct ROI (How much will rents rise?)**

- Current rent: $2,000/mo ($24K/year)
- Post-renovation rent (market): $2,200/mo ($26.4K/year)
- Rent increase: $200/mo ($2,400/year)
- Annual ROI on $50K: $2,400 / $50,000 = **4.8% annual return**
- Payback period: $50,000 / $2,400 = **20.8 years** (very long)

**Verdict**: This renovation doesn't make financial sense unless you're also improving the property's resale value.

**Approach 2: Appreciation Lift (Does renovation increase sale value?)**

- Current market value: $465K
- Post-renovation value: $515K (expected market value after updates)
- Renovation cost: $50K
- Value created: $515K - $465K = $50K
- **Net lift: $0** (cost equals value creation)

**Verdict**: Renovation is break-even on appreciation. Only do it if it improves cash flow or stabilizes tenancy.

**Renovation Cost Caution**:
- Contractors often underestimate by 15-30%
- Unexpected structural issues (found during renovation) add 20%+
- Budget $50K → assume $60-65K actual cost

### Step 8: Develop Neighborhood Scoring
Location is critical. Analyze the neighborhood's fundamentals: demographics, employment, crime, schools.

**Neighborhood Scoring Matrix** (Rate 1-5 per category):

| Factor | Score | Notes | Weight |
|--------|-------|-------|--------|
| **Employment Growth** | 3 | Local job growth 1-2% annually; stable | 25% |
| **Income Levels** | 3 | Median $65K; moderate; sustainable rents | 20% |
| **Crime Rate** | 4 | Below city average; safe for renters | 15% |
| **Schools** | 3 | Average public schools; not a strong draw | 10% |
| **Population Growth** | 2 | Declining 0.5% annually; not growing | 15% |
| **Walkability / Amenities** | 3 | Some retail/parks; average walkability | 10% |
| **Property Appreciation Trend** | 3 | Historical 2-3% appreciation | 5% |

**Weighted Score**: (3×0.25) + (3×0.20) + (4×0.15) + (3×0.10) + (2×0.15) + (3×0.10) + (3×0.05) = **3.1 / 5.0**

**Verdict**: 3.1/5 is average. This is a stable, slow-growth neighborhood. Good for cash flow but limited appreciation upside. Risk: if job losses occur, rents could decline.

**Neighborhood Red Flags** (Avoid):
- Crime rate rising (renters leaving)
- Major employer leaving town (job base shrinking)
- School quality declining (families moving out)
- Population declining 5%+ annually (no demand)

### Step 9: Create Investment Memo Format
Synthesize all analysis into a decision memo.

**Investment Memo Structure**:

```
INVESTMENT MEMO
Property: [Address]
Analysis date: [Date]
Analyst: [Name]
Decision: [PASS / HOLD / ACQUIRE]

EXECUTIVE SUMMARY
[1 paragraph: property overview, location, asking price, recommendation]

MARKET ANALYSIS
- Comparable sales show market value of $463K-475K
- Market is [hot/balanced/soft]; DOM [X] days
- Price/sq ft trend: [rising/flat/declining]
- Overall market: [favorable/neutral/unfavorable]

PROPERTY OVERVIEW
- Address: [Full address]
- Type: [Single-family, duplex, etc.]
- Age: [Year built]
- Condition: [Good/Fair/Poor; needed repairs]
- Rental history: [Stable/Vacant/Problem tenant]

FINANCIAL ANALYSIS
| Metric | Value | Benchmark |
| NOI | $14,448 | Target: $18K+ |
| Cap rate | 3.1% | Target: 4%+ |
| DSCR (80% LTV) | 0.51 | Target: 1.25+ |
| Cash-on-cash | -15.1% | Target: 8%+ |
| 10-yr IRR | 4.2% | Target: 10%+ |

**Verdict on metrics**: Property underperforms on all key metrics. Would require significant price reduction or rent increase to be viable.

NEIGHBORHOOD ANALYSIS
- Score: 3.1/5 (average)
- Strengths: Safe, stable
- Weaknesses: Slow growth, declining population
- Risk assessment: Low execution risk; low upside risk

SCENARIOS & SENSITIVITY
If purchase price reduced to $420K:
- New cap rate: 3.4%
- New DSCR: 0.56
- New IRR (10yr): 5.1%
→ Still below target; requires further price reduction

If rents increase 10% over 2 years (market shift):
- New NOI: $16,000
- New DSCR: 0.56
- IRR improves, but still below target
→ Relies on uncertain market shift

RECOMMENDATION
**PASS** on this property at asking price ($465K).

Viable scenarios:
1. Negotiate price down to $380K (below market) → More realistic DSCR
2. Find a commercial value-add opportunity (rezoning, adaptive reuse) → Different analysis needed
3. Wait for market conditions to improve or seller distress

Current deal terms do not meet investment return requirements.

APPENDIX
[Detailed cash flow model, comps, neighborhood data, loan calculations]
```

### Step 10: Establish Return Benchmarks & Decision Framework
Know what "good" looks like before analyzing a deal.

**Return Benchmarks** (by investor type and market):

| Investor Type | Cap Rate Target | Cash-on-Cash Target | 10-Yr IRR Target |
|---|---|---|---|
| Buy & Hold (Appreciation Market) | 3.5-4.5% | 8-12% | 10-12% |
| Buy & Hold (Cash Flow Market) | 5-7% | 12-18% | 12-15% |
| Value-Add / Renovation | 4-5% | 10-15% | 15-20% |
| Development / Spec | Variable | Variable | 20%+ |

**Decision Framework**:

```
DEAL EVALUATION DECISION TREE

Does property meet minimum criteria?
├─ Is cap rate above 3.5% for your market?
│  └─ NO: PASS (too expensive)
│  └─ YES: Continue to next check
├─ Is DSCR above 1.25 (or can you put 30%+ down)?
│  └─ NO: PASS (can't get financing)
│  └─ YES: Continue to next check
├─ Is neighborhood score 3+/5?
│  └─ NO: PASS (too much risk)
│  └─ YES: Continue to next check
├─ Is projected IRR above your target (e.g., 10%)?
│  └─ NO: PASS or renegotiate price
│  └─ YES: PROCEED to detailed due diligence
│  └─ Maybe: Enter negotiations for price reduction

Renegotiation Point:
If property is "almost there" but misses one metric, calculate the required price cut to hit targets. Use that in negotiations.
```

## Output Template

```
---
REAL ESTATE INVESTMENT ANALYSIS
Property: [Address]
Date: [MM/DD/YYYY]
Analyst: [Name]
Status: [Analysis complete / Pending due diligence]
---

# Property Investment Analysis

## Executive Summary
[1-2 paragraphs: property, price, market, recommendation]

## 1. Comparable Market Analysis (CMA)

### Comparable Sales

| Property | Price | Sq Ft | $/SF | Sold | Adjustments | Adjusted Price |
|----------|-------|-------|------|------|-------------|-----------------|
| Comp 1 | $X | X | $X | Date | +/-$X | $X |
| Comp 2 | $X | X | $X | Date | +/-$X | $X |
| Comp 3 | $X | X | $X | Date | +/-$X | $X |

**Estimated market value**: $[Range]
**Market metrics**: DOM [X] days; List/sale ratio [X%]

## 2. Annual Cash Flow Projection

### Income
- Gross rental income: $X
- Vacancy rate (-X%): -$X
- **Effective gross income**: $X

### Operating Expenses
- Property tax: $X
- Insurance: $X
- Maintenance (6% EGI): $X
- Management (4% EGI): $X
- **Total operating expenses**: $X

**Net Operating Income (NOI)**: $X

## 3. Cap Rate Analysis
Cap rate = NOI / Property Value = $X / $X = **X.X%**

Market comparison: [X% is [above/below/at] market]

## 4. Financing & Cash-on-Cash Return

### Loan Terms
- Purchase price: $X
- Down payment (20%): $X
- Loan amount: $X
- Rate: X.X% | Term: X years
- Monthly payment: $X | Annual debt service: $X

### Cash-on-Cash Return
- NOI: $X
- Annual debt service: -$X
- Annual cash flow: $X
- **Cash-on-cash return**: X.X% (or X% for negative)

## 5. Debt Service Coverage Ratio (DSCR)
DSCR = NOI / Annual debt service = $X / $X = **X.XX**

Lender interpretation: [Above 1.25 / Acceptable / Below 1.0 - difficulty financing]

## 6. Internal Rate of Return (10-Year Hold)

### Assumptions
- Holding period: 10 years
- Annual appreciation: X%
- Loan payoff at sale: $X
- Closing costs (5%): $X

### Projected Returns
- **Year 10 net proceeds from sale**: $X
- **10-year IRR**: X.X%

## 7. Renovation Analysis (if applicable)

### Costs & Returns
- Renovation budget: $X
- Expected rent increase: $X/mo
- Annual return on investment: X.X%
- Expected value lift: $X
- Break-even period: X years

## 8. Neighborhood Scoring

| Factor | Score (1-5) | Notes | Weight |
|--------|---|---|---|
| Employment growth | X | [Note] | X% |
| Income levels | X | [Note] | X% |
| Crime rate | X | [Note] | X% |
| Schools | X | [Note] | X% |
| Population growth | X | [Note] | X% |
| Walkability | X | [Note] | X% |
| Appreciation trend | X | [Note] | X% |

**Weighted score**: X.X / 5.0

**Assessment**: [Neighborhood strengths, weaknesses, risks]

## 9. Financial Summary & Benchmarking

| Metric | Result | Target | Pass/Fail |
|--------|--------|--------|-----------|
| Cap rate | X.X% | 3.5%+ | X |
| DSCR | X.XX | 1.25+ | X |
| Cash-on-cash | X.X% | 8%+ | X |
| 10-yr IRR | X.X% | 10%+ | X |
| Neighborhood score | X.X/5 | 3+/5 | X |

## 10. Recommendation

**Decision**: [PASS / HOLD / ACQUIRE]

**Rationale**: [Summary of why; key metrics that pass/fail]

**If considering renegotiation**:
- Required price to hit targets: $X
- Price reduction needed: X%
- Negotiation strategy: [Approach]

## Appendix
[Detailed assumptions, neighborhood data, loan amortization schedule]
```

## Quality Gates

1. **Comparable Rigor**: Are all three comps truly comparable (sold within 6 months, same neighborhood, similar condition)? If not, CMA is unreliable; find better comps.

2. **Cash Flow Reality Check**: Interview current tenants or property manager. Is your rent assumption realistic? Does maintenance assumption match actual history?

3. **Loan Stress Test**: Run analysis at +1% interest rate. Does DSCR still work? If deal only works at 5% rates and we're at 7%, it's not resilient.

4. **Neighborhood Data Verification**: Is your neighborhood score based on actual data (crime statistics, employment data, school ratings) or assumptions? Use third-party sources (FBI crime data, Census Bureau, Zillow, GreatSchools).

5. **Downside Scenario**: What if rents decline 10% or vacancy rises to 15%? Does deal still make sense? If not, acknowledge the risk.

6. **Appraiser Alignment**: Do your CMA value and assumptions align with what an appraiser would conclude? Lenders will require an appraisal; if it comes in 10% lower than your analysis, financing falls apart.

## Examples

### Good Real Estate Analysis

Property: 3BR/2BA single-family home, $450K purchase price, 5% cap rate, 1.3 DSCR (with 20% down, 6% loan), $3,600/year positive cash flow, 10-year IRR 9.5%.

Neighborhood: Suburban, growing suburb of major metro, job growth 3%/year, median income $75K, schools rated 4/5, population growing 2%/year.

**Verdict**: Deal meets target thresholds. Strong neighborhood fundamentals. Financing is comfortable. Recommend acquisition at asking price or better.

### Bad Real Estate Analysis

Property: $465K asking price, 3.1% cap rate, 0.51 DSCR (negative cash flow), cannot get traditional financing without 40%+ down, IRR 4.2% over 10 years.

Neighborhood: Declining population (-0.5%/year), average school quality, limited job growth.

**Verdict**: Pass. Does not meet return targets. Would require 15% price reduction to become viable. Wait for distressed opportunity or look for different property.

## Common Mistakes

1. **Using list price instead of market value**: Comps sold at $450K; you use asking price of $475K. This inflates value and crushes returns. Use CMA market value, not asking price.

2. **Optimistic rent assumptions**: Market rents are $1,800; you project $2,000 because "you'll manage it well." Stick to market rents or document why yours will be higher.

3. **Ignoring vacancy in cash flow model**: Assume 100% occupancy. Real properties have 5-10% vacancy. Budget it.

4. **Underestimating maintenance and repairs**: Budget 3%; industry standard is 6% of effective gross income. Maintenance is cheaper for new construction (maybe 4%) but older buildings need 8%+.

5. **Failing to stress-test the deal**: All assumptions go perfectly; rents rise, expenses stay flat. Reality is messier. Model scenarios: What if rents stay flat? What if interest rates rise 2%?

6. **Not doing due diligence on tenant**: Financial analysis assumes stable tenant paying on time. If tenant is unreliable, cash flow is at risk. Verify tenant credit, payment history, employment.

## Anti-Patterns

1. **The appreciation gamble**: Property has negative cash flow (red flag), but you're banking on 5% annual appreciation to justify the purchase. Too risky. Cash-flowing properties can appreciate, but appreciation-dependent deals are speculative.

2. **Forced appreciation fantasy**: You plan to do a $50K renovation to add $75K in value. In reality, reno costs $65K and adds $45K. Renovation returns are often disappointing. Be conservative.

3. **Ignoring neighborhood trends**: Buying in a declining area because the property is cheap. If population is dropping 3%/year, rents will follow. Low price is low for a reason.

4. **Overleveraging because interest rates are low**: Financing at 80% LTV with 0.8 DSCR because rates are 3%. If rates rise to 5%, you can't refinance. Use conservative financing assumptions.

5. **Single-scenario analysis**: You model one case (appreciation, stable rents, no vacancy). Model at least 3 cases: conservative, base, optimistic. See if deal works in conservative case; if not, too risky.
