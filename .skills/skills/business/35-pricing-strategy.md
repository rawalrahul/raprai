---
name: pricing-strategy-generator
description: "Generate pricing strategies (cost-plus, value-based, tiered, freemium, usage-based) with Van Westendorp analysis, willingness-to-pay research, and competitive benchmarking. Optimizes revenue while maintaining market competitiveness."
category: business
difficulty: intermediate
model_boost: "Prevents pricing by guesswork; produces instead data-driven pricing with willingness-to-pay validation and defensible positioning."
---

# Pricing Strategy Generator

## Purpose
Pricing is the most powerful profit lever but often set via gut feeling or competitor matching. This skill generates pricing strategies grounded in customer research (Van Westendorp method, willingness-to-pay), cost structure analysis, and competitive benchmarking. Output includes multiple pricing models (tiered, freemium, usage-based, value-based) with go-to-market mechanics and revenue impact modeling.

## When to Use
- Launching a new product or pricing structure
- Scaling a business and questioning pricing efficiency
- Entering a new customer segment (may require different pricing)
- Competitive pricing pressure (defensibility analysis)
- Freemium or trial strategy design
- **Do NOT use when**: You're early-stage with <10 paying customers (gather more data); pricing is locked by contract; you're in pre-revenue mode (focus on product-market fit first).

## Instructions

### Step 1: Analyze Cost Structure
Understand your unit economics to set floor price.

**Cost Categories**:
- **Cost of Goods Sold (COGS)**: Direct costs per customer (infrastructure, third-party APIs, payment processing)
- **Gross Margin Target**: {{%}} (SaaS: 70-80%, Professional Services: 50-60%)
- **Fixed Costs**: Team, ops, facilities (don't factor into per-unit pricing, but inform break-even analysis)
- **Contribution Margin**: Revenue - COGS - Variable Marketing. This is profit per customer after acquisition cost.

**Example**:
- Revenue: $300/month per customer
- COGS (infrastructure, payment processing): $30/month (10%)
- Gross Margin: 90% ($270/month)
- Sales Commission: $30 (10% of revenue)
- Contribution Margin: 73% ($220/month)

**Pricing Floor**: Price must cover COGS + leave room for gross margin targets. If COGS is $30 and you want 70% margin, minimum price is $100 (to cover $30 COGS and leave $70 margin).

### Step 2: Conduct Willingness-to-Pay Research (Van Westendorp)
Van Westendorp Price Sensitivity Meter quantifies customer willingness-to-pay across a price range.

**Survey Questions** (ask 100-500 target customers):
1. "At what price would this product be too **cheap** to be good?" ({{price}})
2. "At what price would this product be **good value** for money?" ({{price}})
3. "At what price would this product be **too expensive**?" ({{price}})
4. "At what price would you **definitely not buy** this product?" ({{price}})

**Analysis**:
- Plot responses on a chart (X-axis = price, Y-axis = % of respondents)
- Identify price bands:
  - {{Optimal price}}: Where "good value" line crosses "too expensive" line (sweet spot)
  - {{Range}}: Where lines converge (defensible pricing band)
  - {{Caution zone}}: Where "too cheap" creeps high (signals quality concerns)

**Example Output**:
- Too cheap: $200 (people worried it's not good)
- Good value: $350
- Too expensive: $500
- Avoid: Below $150 (too cheap) or above $600 (too expensive)
- Optimal: $350-450

### Step 3: Benchmark Competitors & Reference Pricing
Research what competitors charge for similar value. Not to match, but to understand market expectations.

**Data Collection**:
- List 3-5 competitors, document their pricing
- Identify which tier matches your product (feature depth, support level)
- Assess price-to-value ratio:
  - Competitor A: $500/month @ 50 features = $10 per feature
  - Competitor B: $300/month @ 30 features = $10 per feature
  - Us: $350/month @ 30 features = $11.67 per feature ({{%}} premium)

**Benchmarking Insights**:
- If all competitors are $300-500, pricing $800 requires strong differentiation (defensibility)
- If you're targeting different segment (SMB vs. enterprise), different pricing is defensible

### Step 4: Choose Pricing Model
**Pricing Model Options**:

**Tiered** (Good for: Scalable SaaS, feature-gated segments)
- Starter: $99/month (SMB, 5 projects, 1 user)
- Professional: $299/month (Mid-market, 25 projects, 5 users)
- Enterprise: $999+/month (Large orgs, unlimited, custom integrations)

**Freemium** (Good for: Network effects, high customer acquisition, expansion revenue model)
- Free: {{Features}} (limited, conversion goal: get users hooked)
- Paid: $99/month ({{premium features}}, conversion rate target: 2-5%)

**Usage-Based** (Good for: Infrastructure, APIs, variable value)
- Base: $50/month (platform access)
- Per-invoice: $0.50 per invoice processed (pays as they grow)
- Cap: $1,000/month max (budget predictability)

**Value-Based** (Good for: High ROI products, B2B complex sales)
- Price = % of customer value generated
- Example: Invoice automation saves customer $500/month → charge 30% of savings = $150/month
- Requires proving ROI before selling

**Hybrid** (Good for: Balancing simplicity with flexibility)
- Base tier: $100/month (core features)
- Professional: $300/month (SMB-optimized, support)
- Enterprise: Custom (sales negotiation)

### Step 5: Model Revenue Impact of Different Strategies
Project revenue under each pricing scenario to quantify trade-offs.

**Scenario A: Current Pricing ($250/month, 100 customers)**
- Monthly Revenue: $25,000
- Annual: $300,000

**Scenario B: Increase Price ($350/month, assuming 15% churn from price elasticity)**
- Customers: 85 (100 × 85% retention)
- Monthly Revenue: $29,750
- Annual: $357,000 (+19% vs. Scenario A)

**Scenario C: Introduce Freemium ($150/month paid, 300 free users, 5% conversion)**
- Paid customers: 100 + (300 × 5%) = 115 customers
- Revenue: $17,250 (115 × $150)
- But: Expansion potential, higher NPS, viral growth
- Year 2 projection: 500+ customers, $75K+/month

Trade-offs: Scenario B increases near-term revenue but may slow customer acquisition. Scenario C sacrifices near-term revenue for growth and market penetration.

### Step 6: Develop Go-to-Market Mechanics
How will you price and package offerings to customers?

**Mechanics**:
- **Billing frequency**: Monthly (lower commitment), Annual (2-3 discount for cash flow)
- **Trial or freemium**: Yes/no, duration, feature limits
- **Discounts**: Annual prepay (10-20% discount)? Volume discounts? Not typically for SaaS (erodes margins)
- **Seat-based vs. consumption**: Per-user or per-usage?
- **Contract terms**: Month-to-month (flexibility), annual (commitment + discount), multi-year (predictability)

**Example**:
- Monthly: $350/month, cancel anytime (for price-sensitive customers)
- Annual: $350/month × 12 months prepay = $4,200/year = $350/month effective (standard)
- 2-year: $4,200 × 2 = $8,400 prepay = $350/month effective, 10% discount = $315/month effective = $7,560 total (5% cash discount for commitment)

### Step 7: Create Tiered Feature Matrix
If using tiered pricing, define what's included in each tier.

**Matrix Example**:
| Feature | Starter ($99) | Professional ($299) | Enterprise (Custom) |
|---|---|---|---|
| Invoice processing | ✓ (50/mo) | ✓ (500/mo) | Unlimited |
| Approvers | 1 | 5 | Unlimited |
| Integrations | 2 | 15 | Unlimited + custom |
| API access | ✗ | ✓ | ✓ |
| Support | Email | Email + chat | Dedicated |
| SLA | None | 99.5% | 99.99% |

**Rule of Thumb**:
- Make Starter attractive (lure customers)
- Make Professional 2-3x the value of Starter (justify 3x price increase)
- Enterprise is custom (flexibility for high-value customers)

### Step 8: Plan Launch & Optimization
- **Launch**: Implement pricing with 90-day monitoring window
- **Monitor**: Track conversion rates (free → paid), CAC, LTV, churn by pricing tier
- **Optimize**: If churn is high, quality issues (not price). If conversion is low, value not communicated (not price).
- **Iteration**: Quarterly pricing review (not constant changes, which confuse market)

## Output Template

```markdown
# Pricing Strategy: {{Product/Company Name}}
**Strategy Date**: {{Date}}
**Review Cycle**: Quarterly
**Decision Authority**: {{CFO / CEO}}

---

## EXECUTIVE SUMMARY

**Recommended Pricing Model**: {{Tiered / Freemium / Usage-based / Value-based}}
**Price Point(s)**: {{$X/month Starter, $Y/month Professional, $Z/month Enterprise}}
**Go-to-Market**: {{Annual discount offer, 14-day free trial, freemium conversion target {{%}}}}
**Expected Impact**: {{Revenue increase {{%}}}}, {{Customer acquisition change {{%}}}}, {{Churn impact {{-% expected}}}

---

## COST STRUCTURE ANALYSIS

### Variable Costs per Customer
| Cost Category | Amount | {{%}} of Price |
|---|---|---|
| Infrastructure (compute, storage, bandwidth) | ${{}} | {{}} |
| Third-party APIs (payment processing, integrations) | ${{}} | {{}} |
| Payment processing fees ({{%}} × revenue) | ${{}} | {{}} |
| Support & operations | ${{}} | {{}} |
| **Total COGS per Customer** | **${{}}** | **{{%}}** |

### Margin Structure
- **Revenue per Customer (target)**: ${{}}
- **COGS**: ${{}} ({{% of revenue}})
- **Gross Margin**: {{%}} (target: {{%}})
- **Contribution Margin** (Gross Margin - Sales Commission - Variable Marketing): {{%}}

### Pricing Floor
Minimum viable price to maintain {{%}} gross margin: **${{}}**
(Any price below this is unprofitable without cost reduction)

---

## WILLINGNESS-TO-PAY RESEARCH (Van Westendorp Analysis)

### Survey Methodology
- **Sample size**: {{# respondents}} target customers
- **Sample characteristics**: {{Segment (SMB {{-# employees}}), {{verticals}}, geography}}
- **Confidence level**: {{%}}
- **Margin of error**: {{%}}

### Survey Results

**Van Westendorp Chart Data**:
| Price Point | {{Too Cheap (%)}} | {{Good Value (%)}} | {{Too Expensive (%)}} | {{Avoid (%)}} |
|---|---|---|---|---|
| ${{50}} | {{%}} | {{%}} | {{%}} | {{%}} |
| ${{100}} | {{%}} | {{%}} | {{%}} | {{%}} |
| ${{150}} | {{%}} | {{%}} | {{%}} | {{%}} |
| ${{200}} | {{%}} | {{%}} | {{%}} | {{%}} |
| ${{250}} | {{%}} | {{%}} | {{%}} | {{%}} |
| ${{300}} | {{%}} | {{%}} | {{%}} | {{%}} |
| ${{400}} | {{%}} | {{%}} | {{%}} | {{%}} |
| ${{500}} | {{%}} | {{%}} | {{%}} | {{%}} |

### Analysis & Interpretation
- **Optimal Price Point**: {{${{}}}} (intersection of "good value" and "too expensive" curves)
- **Acceptable Range**: ${{}} - ${{}} (where curves converge)
- **Caution Zone**: Below ${{}} ("too cheap" signals quality concerns) or above ${{}} ("too expensive" signals poor affordability)

**Customer Quote** (validating): "{{At {{$}}}, I'd wonder if this is really as good as {{competitor]]. At {{$}}, it feels like a steal. At {{$}}, I'd look for alternatives."

### Segment Variation
- **{{Segment A}}** (e.g., SMB): Optimal ${{}} (price-sensitive)
- **{{Segment B}}** (e.g., Enterprise): Optimal ${{}} (value-focused, less price-sensitive)
- **Implication**: {{Different pricing tiers per segment may be justified}}

---

## COMPETITIVE BENCHMARKING

### Competitor Pricing Comparison
| Competitor | Positioning | Price | Feature Count | Price per Feature | Target Segment |
|---|---|---|---|---|---|
| {{Competitor A}} | Premium, feature-rich | ${{}} | {{#}} | ${{}} | Enterprise |
| {{Competitor B}} | Mid-market balanced | ${{}} | {{#}} | ${{}} | Mid-market |
| {{Competitor C}} | SMB budget-friendly | ${{}} | {{#}} | ${{}} | SMB |
| **{{Our Product}}** | **{{Our positioning}}** | **${{}}** | **{{#}}** | **${{}}** | **{{Segment}}** |

### Competitive Positioning Analysis
- **Price Premium Justification**: We're {{%}} higher than {{Competitor}}. Justified by:
  - {{Faster onboarding (days vs. weeks)}}
  - {{Unique feature: {{}}}}
  - {{Better support / brand}}
  - (Or: {{Not justified; recommend price reduction to ${{}}}}})

- **Price Discount Opportunity**: We're {{%}} lower than {{Competitor}}. Reason:
  - {{Leaner go-to-market (self-serve vs. sales team)}}
  - {{Fewer features (acceptable for SMB segment)}}
  - {{Newer market entrant (gaining share)}}

---

## PRICING MODELS EVALUATED

### Option 1: Tiered Pricing (Recommended: YES / NO)

**Structure**:
| Tier | Price | Users | Features | Support | Target Segment |
|---|---|---|---|---|---|
| **Starter** | ${{}} | {{#}} | {{List}} | {{Email}} | SMB |
| **Professional** | ${{}} | {{#}} | {{List}} | {{Email + Chat}} | Mid-market |
| **Enterprise** | Custom | Unlimited | {{List}} + Custom | {{Dedicated}} | Enterprise |

**Revenue Impact** (assuming customer distribution SMB {{%}}, Mid-market {{%}}, Enterprise {{%}}):
- Year 1 MRR: ${{}}
- Customer composition: {{# SMB}}, {{# Mid-market}}, {{# Enterprise}}
- ARPU: ${{}} (blended)

**Pros**:
- {{Clear tier progression (customers self-select)}}
- {{Feature gating drives upsells}}

**Cons**:
- {{Feature boundaries can feel arbitrary}}
- {{Customers may choose lower tier if not clear on value}}

---

### Option 2: Freemium Model (Recommended: YES / NO)

**Structure**:
- **Free Tier**: {{Features}}, {{Limit: X invoices/month}}, conversion target: {{%}}
- **Paid Tier**: ${{}} (all features, unlimited), or tiered ($99 Professional, $299 Enterprise)
- **Mechanics**: Free users see upgrade prompt after hitting limit or feature use

**Revenue Impact** (assuming 10K free users, {{%}} conversion to paid):
- Year 1 Paid Customers: {{#}} (10K × {{%}})
- Year 1 MRR: ${{}}
- Year 2 (with viral growth): {{# customers}}, MRR ${{}}

**Pros**:
- {{Low friction customer acquisition}}
- {{Network effects (free users engage friends)}}
- {{Expansion revenue (free → paid expansion)}}

**Cons**:
- {{Freemium users consume infrastructure (cost)}}
- {{Conversion rate must be {{%}}+ to be viable}}

---

### Option 3: Usage-Based Pricing (Recommended: YES / NO)

**Structure**:
- **Base Fee**: ${{}} / month (platform access)
- **Usage**: ${{}} per {{unit}} (e.g., per invoice)
- **Cap**: {{$}} / month (budget predictability)

**Revenue Impact**:
- Low-volume customers: ${{}} / month (base only)
- Medium-volume: ${{}} / month (base + usage)
- High-volume: ${{}} / month (capped)

**Pros**:
- {{Aligns price with customer value (they pay for usage)}}
- {{Low barrier to entry (pay-as-you-grow)}}

**Cons**:
- {{Revenue unpredictability (usage varies)}}
- {{Requires sophisticated billing system}}

---

## RECOMMENDED STRATEGY

### Pricing Model: {{Tiered / Freemium / Hybrid}}

**Rationale**:
- {{Willingness-to-pay research shows customers willing to pay ${{}} for value}}
- {{Competitors charge ${{}} - ${{}}; our {{%}} {{premium / discount}} is justified by {{differentiation}}}}
- {{Our customer segments vary in {{willingness-to-pay / feature need}}; tiered model captures value across segments}}

### Pricing Tiers (Recommended)

| Tier | **Starter** | **Professional** | **Enterprise** |
|---|---|---|---|
| **Price** | **${{}}** | **${{}}** | **Custom** |
| **Target Segment** | SMB (<50 emp) | Mid-market (50-500) | Enterprise (500+) |
| **Users/Licenses** | {{#}} | {{#}} | Unlimited |
| **Invoices/Month** | {{#}} | {{#}} | Unlimited |
| **Integrations** | {{#}} | {{#}} | {{#}} + custom |
| **Support** | Email (24hr) | Chat + Email (4hr) | Dedicated AM (1hr) |
| **SLA** | None | 99.5% | 99.99% |
| **Contract Term** | Month-to-month | Annual recommended | Annual / Multi-year |

### Go-to-Market Mechanics

**Trial & Conversion**:
- **Free Trial**: 14 days, full Starter features ({{reason: enough time to see value, matches sales cycle}})
- **Conversion Path**: Trial user sees upgrade prompt after {{milestone (e.g., "processed 25 invoices")}}
- **Target Conversion Rate**: {{%}} of trial to Starter, {{%}} of Starter → Professional within 6 months

**Discounts & Incentives**:
- **Annual Prepay**: 15% discount (e.g., ${{}} × 12 × 85% = ${{}} annual)
- **Multi-year** ({{2+ years}}): Additional 10% discount
- **Volume**: No per-seat volume discounts (cannibalizes revenue)
- **Promo**: Limited-time (new year, new customer acquisition period) {{%}} discount

**Pricing Announcement**:
- {{Current customers}} at {{grandfather price}} for {{duration}} (shows good faith, retains customers)
- {{New customers}} at {{new price}} starting {{date}}

### Revenue Projections ({{Planning Horizon}})

| Metric | Year 1 | Year 2 | Year 3 |
|---|---|---|---|
| Starter Customers | {{#}} | {{#}} | {{#}} |
| Professional Customers | {{#}} | {{#}} | {{#}} |
| Enterprise Customers | {{#}} | {{#}} | {{#}} |
| **Total Customers** | **{{#}}** | **{{#}}** | **{{#}}** |
| **Blended ARPU** | **${{}}** | **${{}}** | **${{}}** |
| **MRR** | ${{}} | ${{}} | ${{}} |
| **Annual Revenue** | ${{}} | ${{}} | ${{}} |
| **Gross Margin** | {{%}} | {{%}} | {{%}} |

### Key Assumptions
- Starter → Professional upgrade rate: {{%}} within 12 months
- Enterprise sales cycle: {{# months}}, {{%}} win rate
- Churn: Starter {{%}}, Professional {{%}}, Enterprise {{%}} (lower for lock-in)
- COGS grows at {{%}} annually (economies of scale)

---

## OPTIMIZATION & MONITORING PLAN

### Metrics to Track (Monthly)
| Metric | Target | Current | Status |
|---|---|---|---|
| Trial → Paid Conversion | {{%}} | {{%}} | {{On Track / At Risk}} |
| Starter → Professional Upgrade | {{%}} | {{%}} | {{}} |
| Blended ARPU | ${{}} | ${{}} | {{}} |
| Gross Margin | {{%}} | {{%}} | {{}} |
| Churn Rate (all tiers) | {{%}} | {{%}} | {{}} |

### Optimization Triggers
- **If Trial Conversion < {{%}}**: Issue is value communication (not price). Action: Improve onboarding.
- **If Churn > {{%}}**: Quality or fit issue (not price). Action: Product improvements.
- **If {{competitor}} drops price {{%}}**: Monitor. If we lose {{# deals}}, evaluate price response. Don't react immediately (price wars erode margins).
- **If ARPU is rising**: Upsell is working (professional is {{%}} of new customers). Can afford to invest more in acquisition.

### Review Cadence
- **Monthly**: Track conversion, churn, ARPU
- **Quarterly**: Pricing review against competitive landscape, customer feedback
- **Annually**: Full pricing strategy refresh (willingness-to-pay research, cost reanalysis, market shift assessment)

---

## PRICING COMMUNICATION & FAQ

### Customer Messaging
**"Why This Pricing?"**
"We price based on {{value delivered to you}} ({{metric: X hours saved, $Y revenue gained}}). {{Starter}} suits {{SMB}}. {{Professional}} is built for {{mid-market}}. {{Enterprise}} is {{custom for }}."

### Objection Handling
**Objection**: "{{Competitor}} is {{%}} cheaper."
**Response**: "{{Competitor}} targets {{enterprise}} with {{extended sales cycle / custom support}}, which drives costs up. We focus on {{SMB / fast deployment}} which lets us charge less. Also compare total cost of ownership: we have {{faster onboarding / lower implementation cost}}."

**Objection**: "Can you discount to {{$}}?"
**Response**: "We're transparent on pricing to keep costs low for everyone. One-off discounts create unfairness. What we can do: {{annual prepay discount ({{%}})}}, {{trial period}} to prove value, {{free integration}} if you commit to annual."

```

## Quality Gates
- [ ] Cost structure analyzed (COGS identified, gross margin target set, pricing floor calculated)
- [ ] Willingness-to-pay research conducted (Van Westendorp with 100+ respondents, price range identified)
- [ ] Competitors benchmarked (3-5 competitors, price positioning justified)
- [ ] Multiple pricing models evaluated (tiered, freemium, usage-based, value-based comparison)
- [ ] Revenue impact modeled for each option (unit count, ARPU, annual revenue projections)
- [ ] Tiered feature matrix defines what's included in each tier (clear progression, no feature redundancy)
- [ ] Go-to-market mechanics specified (trial length, conversion target, discount policy)
- [ ] Monitoring plan includes conversion, churn, and ARPU tracking
- [ ] Optimization triggers defined (when to adjust price or model)

## Examples

### Good Output (excerpt)
```
WILLINGNESS-TO-PAY RESEARCH:
Sample: 200 SMB finance directors, $X- $X revenue companies
Optimal Price Point: $350/month (intersection of "good value" and "too expensive" curves)
Acceptable Range: $250-$450
Too Cheap Threshold: Below $150 (signals low quality)
Too Expensive Threshold: Above $600 (too high relative to alternatives)

Customer Quote: "At $350/month with the features you offer, it feels fair. At $250, I'd worry it's not reliable. At $500, I'd definitely look for something cheaper."

---

COMPETITIVE BENCHMARKING:
| Competitor | Price | Positioning | Our Price | Premium/Discount |
|---|---|---|---|---|
| Competitor A | $499/month | Enterprise-focused | $350 | 30% discount |
| Competitor B | $299/month | SMB budget | $350 | 17% premium |
| Competitor C | $199/month | Bare-minimum | $350 | 76% premium |

Our Positioning: Balanced (Professional features without enterprise overhead). We charge 17% more than {{competitor B}} because we include {{2 integrations}}, {{chat support}}, which they don't. Justified.

---

RECOMMENDED STRATEGY: Tiered Pricing

| Tier | Price | Invoices/Month | Users | Support |
|---|---|---|---|---|
| Starter | $99 | 50 | 1 | Email |
| Professional | $349 | 500 | 5 | Chat + Email |
| Enterprise | Custom | Unlimited | Unlimited | Dedicated |

Year 1 Projection (assuming {{customer mix}}):
- 50 Starter @ $99 = $4,950/month
- 30 Professional @ $349 = $10,470/month
- 2 Enterprise @ $2,000 avg = $4,000/month
- Total: $19,420/month ($233K/year)

Willingness-to-pay research validated {{Professional}} tier at $349 is optimal for mid-market.
```

### Bad Output (what to avoid)
```
Pricing Strategy: $299/month per customer

Rationale: This feels like a good price, and competitors charge around this amount.

(Why this fails: No cost structure analysis, no willingness-to-pay validation, no tiering or segmentation, no revenue modeling, no go-to-market mechanics)
```

## Common Mistakes

1. **Pricing Based on Competitor Matching, Not Customer Value**: "Competitor charges $300, so we charge $300." Result: You may be leaving money on the table (customers willing to pay $500) or pricing too high (losing deals). Better: Van Westendorp research shows willingness-to-pay independently, then compare to competitors for positioning.

2. **No Distinction Between List Price and Realized Price**: You offer discounts, volume deals, annual prepay discounts, but your models don't account for this. Result: Revenue projections miss actual realized price. Better: Track "list price" vs. "realized average price" separately. "We list at $300, but {{%}} of customers get annual discount, bringing realized ARPU to $250."

3. **Tiering That Doesn't Create Progression**: Starter has 50 invoices, Professional has 75 invoices (not enough difference to justify 3x price increase). Better: Starter = 50 invoices + basic support. Professional = 500 invoices + chat support + integrations. Clear progression justifies 3x price.

4. **Freemium Conversion Target Too Aggressive**: "We'll convert 20% of free users to paid." Industry benchmark: 2-5%. Better: Plan for 3-5% initially, track monthly. If you hit 3% and scale to 10K free users, that's 300 paid customers (reasonable).

5. **No Discounting Policy**: You say "no discounts," but first enterprise customer demanding {{%}} off. Inconsistent. Better: Policy upfront. "We offer {{%}} annual prepay discount, {{%}} multi-year discount, no per-seat volume discounts. For enterprise, pricing is {{flexible within bounds}}."

## Anti-Patterns

1. **Constant Price Changes**: You change prices every quarter based on "new insight." Customers hate surprises. Better: Quarterly review, but change prices annually max (with grandfathering for existing customers).

2. **Feature Gating That Frustrates**: Professional tier charges for "API access," but customers need API immediately (not "someday"). You lose deals. Better: Understand which features drive value. Gate premium features (integrations, support), not essential ones (API, basic reporting).

3. **Usage-Based Billing Without Usage Limits**: Customers see bill spike 10x one month (surprise). They churn. Better: Usage-based with monthly cap (e.g., "$50 + $0.10 per invoice, capped at $500/month"). Customers know max spend.

4. **Ignoring Gross Margin Trend**: As you scale, COGS increases (more infrastructure). You don't adjust pricing, margin compresses from 80% → 50% by Year 3. Better: Annual pricing review includes cost reanalysis. If COGS rises {{%}}, reprice to maintain {{%}} gross margin.

5. **Not Testing Price Elasticity**: You raise price 20%, assume {{%}} of customers will churn, but never validated elasticity empirically. Better: A/B test. {{%}} of new sign-ups see old price, {{%}} see new price. Measure conversion difference. Real data beats assumptions.

