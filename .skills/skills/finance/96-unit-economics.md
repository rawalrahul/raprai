---
name: unit-economics
description: "Analyze per-unit profitability through CAC, LTV, payback period, contribution margin, breakeven analysis, and cohort analysis to identify sustainable growth and optimize pricing."
category: finance
difficulty: advanced
model_boost: "Fixes focus on vanity metrics while ignoring unit profitability and cash burn"
---

# Unit Economics

## Purpose

"We're growing 50% year-over-year!" sounds great until you realize you're losing money on every customer. Unit economics answers: "For every dollar of customer acquisition cost, how much lifetime value do I generate?" and "What's my payback period?" A business with poor unit economics is a wealth destruction machine, no matter how fast it grows. This skill provides frameworks to calculate unit economics, identify breakeven points, and optimize pricing and retention.

## When to Use

- You're a founder evaluating if your business model is sustainable
- You're in a B2B SaaS business and need to monitor key metrics
- You're considering a pricing change or customer acquisition strategy shift
- You're evaluating a potential acquisition or investment
- You want to understand which customer cohorts are profitable
- You're managing a marketplace and need to optimize both sides
- **Do NOT use when**: You're a one-time transaction business (less applicable), or you're pre-product-market fit (too early for precision; focus on traction first)

## Instructions

### Step 1: Calculate Customer Acquisition Cost (CAC)

CAC is the average cost to acquire one customer.

**Formula**: Total sales & marketing spend / Number of new customers acquired

```
Year 1:
Sales & marketing spend:  $500,000
New customers acquired:   50
CAC:                      $500,000 / 50 = $10,000 per customer
```

**Detailed breakdown** (if you have the data):

```
Spend by channel (Year 1):
- Paid ads (Google, Facebook):       $200,000 / 20 customers = $10,000 CAC
- Sales team (2 people × $60k):      $120,000 / 15 customers = $8,000 CAC
- Content marketing:                 $100,000 / 10 customers = $10,000 CAC
- Conferences/partnerships:          $80,000 / 5 customers = $16,000 CAC

Blended CAC:                         $500,000 / 50 = $10,000
```

**This matters because**: Different channels have different CAC. Optimize by shifting budget from high-CAC to low-CAC channels.

### Step 2: Calculate Average Revenue Per User (ARPU)

ARPU is the average revenue you earn per customer per month (or year).

**For subscription businesses**:
```
Total monthly recurring revenue (MRR):  $50,000
Number of customers:                   100
ARPU:                                  $50,000 / 100 = $500/month per customer
```

**For transaction businesses**:
```
Total annual revenue:        $1,000,000
Number of customers:         5,000
ARPU (annual):              $1,000,000 / 5,000 = $200/customer/year
ARPU (monthly):             $200 / 12 = $16.67/month average
```

**Tiered pricing** (if you have different customer tiers):
```
100 customers × $100/month:       $10,000
50 customers × $250/month:        $12,500
10 customers × $1,000/month:      $10,000

Total MRR:                        $32,500
Total customers:                  160
ARPU:                            $32,500 / 160 = $203.13/month
```

### Step 3: Determine Churn Rate

Churn is the percentage of customers you lose per month.

**Formula**: (Customers lost in month) / (Customers at start of month) × 100%

```
Month 1: 100 customers
Month 2: 95 customers (5 churned)
Churn: 5 / 100 = 5%

Month 2: 95 customers
Month 3: 89 customers (6 churned)
Churn: 6 / 95 = 6.3%

Average monthly churn: ~5-6%
```

**Annual churn from monthly**:
- If monthly churn is 5%, annual churn is: (1 - 0.95)^12 = 54% (lose more than half customers per year)
- Industry benchmark: SaaS churn is 2-5% monthly for SMB, 1-2% for Enterprise

**Why this matters**: High churn means you're acquiring customers just to replace lost ones. Reduce churn by improving product, support, or pricing.

### Step 4: Calculate Lifetime Value (LTV)

LTV is the total profit you earn from a customer over their entire relationship.

**Formula**: (Monthly ARPU × Gross Margin %) / Churn Rate × 12

```
ARPU:           $500/month
Gross Margin:   80% (COGS is 20%)
Monthly profit: $500 × 0.80 = $400
Monthly churn:  5% (customer lasts ~20 months on average: 1/0.05 = 20)

LTV:            $400 × 20 = $8,000
```

Or with the formula:
```
LTV = (Monthly profit / Monthly churn rate) × 12
    = ($400 / 0.05) × 12
    = $8,000 × 12
    = Wait, this is confusing. Let me recalculate.

Actually, LTV = Monthly profit × (1 / Churn rate)
            = $400 × (1 / 0.05)
            = $400 × 20
            = $8,000
```

**This means**: On average, a customer is worth $8,000 in lifetime profit (assuming 5% monthly churn).

### Step 5: Calculate LTV/CAC Ratio (The North Star)

This ratio is the key metric. It tells you if unit economics work.

**Formula**: LTV / CAC

```
LTV:     $8,000
CAC:     $10,000
LTV/CAC: $8,000 / $10,000 = 0.8x

This is bad. You're losing money on every customer.

For unit economics to work:
- LTV/CAC should be ≥ 3x (you earn $3 for every $1 spent acquiring)
- Ideal: LTV/CAC > 5x (more profitable)
- Minimum: LTV/CAC > 1x (at least break even)
```

**Common benchmarks**:
- SaaS B2B: 3-5x is healthy; >10x is exceptional
- SaaS B2C: 2-3x is healthy; very hard to achieve >3x
- E-commerce: 1.5-2x is healthy (lower margins, higher churn)

**Improving LTV/CAC**:
- Increase ARPU (raise prices, upsell, cross-sell)
- Decrease churn (improve product, retention programs)
- Decrease CAC (optimize marketing, referral programs, content)

### Step 6: Calculate Payback Period

Payback period: How long until a customer's cumulative profit equals the CAC?

**Formula**: CAC / (Monthly profit) = months to payback

```
CAC:             $10,000
Monthly profit:  $400
Payback period:  $10,000 / $400 = 25 months (just over 2 years)

This is long. You're funding customer acquisition 25 months ahead of payback.
Ideal payback: <12 months for SaaS.
```

**Why this matters**: If payback is 25 months but you're running out of cash in 12 months, you have a problem. Payback period also affects funding needs. Lower payback = less capital required to scale.

### Step 7: Calculate Contribution Margin

Contribution margin is the profit remaining after direct costs (COGS), before fixed operating expenses.

**Formula**: (Revenue - COGS) / Revenue = Contribution Margin %

```
ARPU:                  $500/month
COGS (hosting, payment processing, support):  $100/month
Contribution:          $500 - $100 = $400
Contribution Margin:   $400 / $500 = 80%

For every $1 of revenue, you keep $0.80 after direct costs.
This $0.80 goes toward fixed costs (salaries, marketing, R&D) and profit.
```

**Benchmarks**:
- SaaS: 70-85% is healthy
- E-commerce: 30-50% is common (higher COGS)
- Marketplace: 20-40% (you take a cut, but don't cover all costs)

### Step 8: Breakeven Analysis (When Do Fixed Costs Get Covered?)

Fixed costs (salaries, rent, etc.) must be covered by contribution margin.

**Formula**: Fixed costs / (ARPU × (1 - churn rate) × # customers)

```
Monthly fixed costs:    $100,000 (salaries + rent + overhead)
Contribution margin:    $400 per customer
Customers needed to break even:  $100,000 / $400 = 250 customers

If you have 100 customers, you lose $60,000/month.
If you have 250 customers, you break even (no profit, no loss).
If you have 300 customers, you profit $40,000/month.
```

**This tells you**: "I need 250 customers to sustain my operation without additional funding."

### Step 9: Cohort Analysis (Which Customer Groups Are Profitable?)

Different customer cohorts (groups) have different LTV, CAC, and churn.

**Example cohort analysis** (by acquisition month):

```
Cohort: Customers acquired in Jan 2025

Age (months)  | Customers | Cumulative Spent  | Cumulative Revenue | Cohort LTV
1             | 100       | $500k (CAC)       | $50k               | -$450k
2             | 100       | $500k             | $100k              | -$400k
3             | 95        | $500k             | $150k              | -$350k
4             | 90        | $500k             | $200k              | -$300k
6             | 85        | $500k             | $300k              | -$200k
12            | 70        | $500k             | $600k              | +$100k
24            | 60        | $500k             | $1.2M              | +$700k

Cohort LTV: ~$700k total (split across 60 remaining customers ≈ $11.7k per customer)
```

**Insights**:
- Early cohort churn is high (100 → 60 over 2 years)
- Revenue doesn't exceed CAC until month 12
- Late-cohort customers are most profitable (lower churn)
- If this cohort's churn rate and ARPU are typical, new cohorts will follow same pattern

**Optimize**: Which cohorts have lowest churn? What did you do differently with them? (E.g., better onboarding, different customer segment.) Double down on that.

### Step 10: Sensitivity Analysis (What If?)

Test how changes affect unit economics.

```
BASE CASE:
ARPU:        $500
CAC:         $10,000
Churn:       5%/month
LTV:         $8,000
LTV/CAC:     0.8x (BROKEN)

SCENARIO 1: Improve retention (churn to 3%)
LTV:         (400 / 0.03) = $13,333
LTV/CAC:     1.33x (Better, but still tough)

SCENARIO 2: Increase ARPU (to $750, 50% increase)
Monthly profit: $600 (assuming same COGS)
LTV:         (600 / 0.05) = $12,000
LTV/CAC:     1.2x (Still marginal)

SCENARIO 3: Decrease CAC (to $5,000 through optimization)
LTV/CAC:     1.6x (Much better)

SCENARIO 4: All three (ARPU $750 + 3% churn + $5k CAC)
LTV:         (600 / 0.03) = $20,000
LTV/CAC:     4x (HEALTHY!)
```

**Key learning**: Small improvements in churn and ARPU compound. Reducing CAC also helps, but is harder.

## Output Template

```
# Unit Economics Analysis

## Basic Metrics

### Customer Acquisition Cost (CAC)
- Total sales & marketing spend (period): $[X]
- New customers acquired: [N]
- CAC: $[X/N]

### Average Revenue Per User (ARPU)
- Total revenue (period): $[X]
- Total customers: [N]
- ARPU: $[X/N] per [month/year]

### Churn Rate
- Customers at start of period: [N]
- Customers at end of period: [M]
- Monthly churn: [%]

### Lifetime Value (LTV)
- Monthly profit per customer: $[X]
- LTV = $[X] / [churn %]
- LTV: $[X]

## Key Ratios

### LTV/CAC Ratio
- LTV: $[X]
- CAC: $[Y]
- LTV/CAC: [X/Y]x
- Status: [ ] Healthy (≥3x) | [ ] Marginal (1-3x) | [ ] Broken (<1x)

### Payback Period
- CAC: $[X]
- Monthly profit: $[Y]
- Payback: [X/Y] months

### Contribution Margin
- ARPU: $[X]
- COGS: $[Y]
- Contribution: $[X-Y] ([% of revenue])

## Breakeven Analysis
- Fixed monthly costs: $[X]
- Contribution per customer: $[Y]
- Customers needed to break even: [X/Y]
- Current customer base: [N]
- Status: [ ] Pre-breakeven (gap: [#]) | [ ] At breakeven | [ ] Profitable

## Cohort Analysis
[Table: Acquisition month, cohort size, revenue, churn, cohort LTV]

## Improvement Roadmap
- [ ] Reduce CAC to $[target] (via: [method])
- [ ] Increase ARPU to $[target] (via: [method])
- [ ] Reduce churn to [target]% (via: [method])
- [ ] Target LTV/CAC: [ratio]x

## Sensitivity: Best Case Scenario
[If all improvements hit, what's the new LTV/CAC?]
```

## Quality Gates (5+)

1. **Data Accurate**: Are your CAC, ARPU, and churn based on actual business data, not estimates?
2. **Benchmarks Known**: Do you know your industry benchmarks for LTV/CAC and payback period?
3. **Cohorts Tracked**: Are you measuring at least acquisition month cohorts, if not others?
4. **Improvement Path Clear**: Can you identify 1-2 levers that would most improve unit economics?
5. **Monitoring Regular**: Will you review these metrics monthly or quarterly?

## Examples

### Good Unit Economics (SaaS Company)

**CAC**: $2,500 (via content marketing + sales)
**ARPU**: $500/month
**Churn**: 3%/month
**LTV**: $16,667
**LTV/CAC**: 6.67x
**Payback**: 5 months

**Assessment**: Healthy. Every $1 spent acquiring customers returns $6.67 over lifetime. Payback in 5 months means you can reinvest quickly.

---

### Poor Unit Economics (E-commerce Company)

**CAC**: $50 (via Google Ads)
**ARPU**: $75 (first purchase)
**Repeat purchase rate**: 20% (most customers buy once)
**Churn**: 95%/month (high)
**LTV**: $75 × 0.20 = $15 (only repeat buyers matter)
**LTV/CAC**: 0.3x

**Assessment**: Broken. You lose $35 on every customer. Must reduce CAC (optimize ads) or increase repeat purchases (loyalty program). As-is, not viable without external funding.

## Common Mistakes (3+)

1. **Wrong Churn Calculation**: You calculate annual churn as (customers lost / starting customers) but this doesn't compound. Use monthly churn; it's more accurate.

2. **CAC Amortization Ignored**: You spend $100k on marketing in month 1, acquire 10 customers. CAC is $10k. But customers last 24 months. Some analyses spread CAC over lifetime (more complex but accurate).

3. **LTV Without Time Value of Money**: You assume $400 profit today equals $400 profit 2 years from now. In reality, money today is worth more. Advanced LTV discounts future cash flows. For startups, simple LTV (no discount) is okay to start.

4. **Cohort Analysis Not Done**: You track aggregate LTV/CAC, but don't break down by cohort. Early cohorts might look great; later ones break even. Without cohort analysis, you miss this divergence.

5. **Ignoring Gross Margin Degradation**: As you scale, COGS might increase (you're less efficient, competition, supply constraints). Update COGS regularly; don't assume it stays constant.

## Anti-Patterns (3+)

1. **Vanity Metric Focus**: "We're growing 100%/month!" but LTV/CAC is 0.5x. You're destroying wealth. Growth for growth's sake is not strategy.

2. **CAC Obsession, Churn Neglect**: You optimize CAC to $5k (great!) but ignore 8% monthly churn (terrible). Churn reduction often has better ROI than CAC reduction.

3. **Analysis Paralysis**: You spend 3 months perfecting unit economics models but never act on findings. Unit economics is a tool for decisions. Once you know LTV/CAC < 1x, act: reduce CAC, increase ARPU, or pivot.

4. **Industry Benchmark Denial**: Your LTV/CAC is 1.5x, but industry benchmark is 3.5x. You tell yourself "we're different" and spend years chasing growth. You're not different; your model is broken. Face it and fix it.

---

**Next Steps**: Calculate your current CAC, ARPU, churn, and LTV. Is your LTV/CAC above 3x? If not, identify which lever to pull (reduce CAC, increase ARPU, reduce churn) and build a 90-day improvement plan.
