---
name: business-plan-generator
description: "Generate comprehensive business plans or lean canvases with problem-solution fit, market sizing (TAM/SAM/SOM), competitive analysis, financial projections, and go-to-market strategy. Validates business viability and identifies execution risks."
category: business
difficulty: intermediate
model_boost: "Prevents shallow market analysis and unrealistic financial projections common in weak business plan outputs."
---

# Business Plan Generator

## Purpose
A business plan articulates your company's strategy, market opportunity, competitive position, and financial model. This skill generates either a lean canvas (1-page overview) or a comprehensive business plan with validated assumptions, realistic financial modeling, and actionable go-to-market strategies. Output helps secure funding, align teams, and identify execution risks before investing capital.

## When to Use
- Launching a new company or product line
- Seeking venture capital or bank financing
- Entering a new market segment
- Pivoting business model or target customer
- **Do NOT use when**: Market validation is incomplete (conduct customer interviews first); you lack basic financial records or projections; pivoting is exploratory (use design sprints first).

## Instructions

### Step 1: Validate Problem-Solution Fit
Interview 5-10 target customers about their current solution and pain level. Document the specific problem, frequency of occurrence, and costs they incur. Quantify: "How much does this problem cost you annually?" Validate that customers have already attempted solving the problem (strong signal). Record customer quotes and evidence. Red flag: If customers haven't tried solving the problem themselves, demand is speculative.

### Step 2: Size the Market (TAM/SAM/SOM)
**TAM (Total Addressable Market)**: Use top-down (industry reports) and bottom-up (price × potential users) methods. Cross-check with analyst reports (Gartner, IDC, CB Insights). Example: If 50M businesses globally need payroll software at $500/year, TAM = $25B.

**SAM (Serviceable Available Market)**: Define your serviceable subset (e.g., SMBs under 500 employees in North America). Apply realistic geographic and segment constraints. SAM should be 5-15% of TAM initially.

**SOM (Serviceable Obtainable Market)**: Year 3-5 realistic capture based on sales capacity and market saturation. Assume 1-3% market share unless you have proven channel dominance. SOM = SAM × realistic share.

### Step 3: Conduct Competitive Analysis
Map competitors on 2x2 grids: Price vs. Feature, Ease-of-Use vs. Depth, etc. Document each competitor's: pricing model, key features, GTM strategy, funding raised, recent product launches. Identify "white space" (unserved customer needs) and differentiation vectors (not just feature lists). Assess switching costs—lower costs = harder moat.

### Step 4: Define Business Model
Specify revenue streams: B2B SaaS (tiered), B2C direct-to-consumer, marketplace take-rate, licensing, professional services. For SaaS: unit economics (CAC, LTV, payback period, churn). For retail: margin structure, inventory model, return rate. Validate model with 3-5 comparable companies' public filings (10-Ks) or analyst reports.

### Step 5: Project Financial Model
Build 3-year P&L with bottom-up logic:
- **Year 1**: Conservative customer acquisition (5-50 customers), blended CAC, monthly recurring revenue (MRR), churn assumptions (5-10% monthly for early SaaS).
- **Year 2-3**: Scale revenue at 15-30% MoM growth early, 3-5% MoM later. Model unit economics improving (CAC payback < 12 months by Year 2).
- **Operating costs**: Salaries (largest line item), software subscriptions, marketing, infrastructure. Sanity check: Can you reach breakeven with realistic growth?

Include balance sheet (cash runway) and cash flow statement (critical: when do you run out of cash?). Flag funding requirements.

### Step 6: Outline Go-to-Market Strategy
Define target customer segment (beachhead market, not everyone). Specify sales motion: direct sales, self-serve, partnership. Document customer acquisition channels: organic, paid ads, partnerships, referrals (assign budget). Plan for 6-12 month sales cycle in B2B. For B2C, plan content/community building. Identify unfair advantage: network effects, exclusive data, regulatory moat, etc.

### Step 7: Identify Risks and Milestones
List top 5 execution risks (market adoption, competitive entry, regulatory, technical). For each, specify detection trigger and mitigation. Define 6-month milestones: product-market fit signals (NPS > 40), retention benchmarks (< 5% monthly churn), revenue targets, team hires. These prove assumptions, not vanity metrics.

## Output Template

```markdown
# Business Plan: {{Company Name}}

## Executive Summary
{{1-2 paragraph overview: what we do, why now, market opportunity in $, competitive advantage}}

## Problem & Solution
**Problem**: {{Specific, quantified customer problem from interviews}}
- Customer quote: "{{Direct quote from customer}}
- Pain points: {{List 3-4}}

**Solution**: {{How you solve it, unique angle}}

## Market Opportunity
**TAM**: ${{amount}} ({{calculation method}})
**SAM**: ${{amount}} ({{geographic/segment scope}})
**SOM Year 3**: ${{amount}} ({{% market share assumption}})

## Competitive Landscape
| Competitor | Price | Key Features | Weakness |
|---|---|---|---|
| {{Name}} | ${{}} | {{}} | {{}} |
| {{Name}} | ${{}} | {{}} | {{}} |

**Our Differentiation**: {{Why we win (not just features)}}

## Business Model
- Revenue stream: {{Pricing model, e.g., "SaaS @ $99-499/month"}}
- Unit economics: CAC ${{amount}}, LTV ${{amount}}, Payback {{months}}
- Gross margin: {{%}}

## Financial Projections (3-Year)
| Metric | Year 1 | Year 2 | Year 3 |
|---|---|---|---|
| Revenue | ${{}} | ${{}} | ${{}} |
| Customers | {{}} | {{}} | {{}} |
| Churn | {{}}% | {{}}% | {{}}% |
| Operating Expenses | ${{}} | ${{}} | ${{}} |
| EBITDA | ${{}} | ${{}} | ${{}} |

## Go-to-Market Strategy
**Beachhead**: {{Specific initial customer segment}}
**Sales motion**: {{Direct/self-serve/hybrid}}
**Channels**: {{Acquisition strategy with budget split}}
**Timeline to revenue**: {{Weeks to first customer}}

## Key Milestones & Success Criteria
- {{Month}}: {{Milestone (product-market fit signal, revenue target, team)}}
- {{Month}}: {{}}

## Risks & Mitigation
| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| {{}} | {{}} | {{}} | {{}} |

## Funding Ask
**Amount**: ${{}}
**Use of funds**: {{Breakdown: team {{}}%, product {{}}%, sales {{}}%}}
**Runway**: {{# of months}}
```

## Quality Gates
- [ ] TAM/SAM/SOM calculated via multiple methods (top-down and bottom-up), not speculation
- [ ] At least 5 competitive comparisons with documented feature/pricing/GTM analysis
- [ ] Financial model includes realistic CAC, LTV, churn, and cash runway—not just hockey stick growth
- [ ] Problem validated via 5+ customer interviews with specific pain quantification
- [ ] Go-to-market strategy includes specific channels, budget, and timeline to first customer
- [ ] Risk register identifies top 5 execution risks with detection triggers and mitigation steps
- [ ] Executive summary is <200 words, entire plan fits 20-30 pages

## Examples

### Good Output (excerpt)
```
## Market Opportunity
**TAM**: $18.5B (US payroll processing market: 330K companies × $500K avg spend on payroll platforms/services, verified via Gartner 2025 report)
**SAM**: $4.2B (Mid-market SMBs, 50-500 employees, US only, representing 23% of TAM)
**SOM Year 3**: $210M (5% market share capture, achievable given $2M/year sales capacity)

**Problem Validation**: "We currently pay $80K/year to our old payroll provider and they still can't handle our contractor management. It's killing us in compliance." — CFO, 200-person manufacturing company. Interviewed 8 companies; 100% spend 1-2 hours/week on manual payroll admin.
```

### Bad Output (what to avoid)
```
TAM: "The addressable market is huge, potentially $100B globally." (No calculation, no sources)
Competitors: "We have no direct competitors; the space is wide open." (False—always has competitors)
Churn: Not mentioned. (Critical metric for SaaS viability)
Go-to-market: "We'll sell through partnerships and word-of-mouth." (Too vague; no partners identified, no CAC model)
```

## Common Mistakes

1. **TAM Overestimation**: Defining TAM as "everyone who could possibly benefit" rather than realistic serviceable market. Check: Is your TAM > $1B? If targeting ultra-niche, it should be $10M+. Benchmark against comparable company Series A rounds ($10-20M raises for $100M+ SAM plays).

2. **Ignoring Churn & Retention**: SaaS plans that assume 0-2% monthly churn are unrealistic. Industry benchmarks: B2B SaaS average 5% monthly, SMB cohorts 8-12%. If your model doesn't improve churn to <5% by Year 2, profitability is impossible.

3. **Weak Go-to-Market Detail**: "Direct sales" without specifying: How many sales reps? At what cost? How many meetings convert? What's the sales cycle? Without this, execution is chaotic. Detail: "2 AEs in Year 1, $120K OTE each, $10K CAC, 20% conversion on qualified leads, 6-month sales cycle."

4. **Missing Unit Economics**: Presenting revenue growth without CAC, LTV, or payback period. Investors immediately see the gap. Calculate precisely: CAC = (Sales salary + commission + overhead) / new customers acquired in period.

5. **No Risk Mitigation Plan**: Listing "competition" as a risk but offering no mitigation. Every risk needs a detection trigger (e.g., "We'll know we have a product-market fit problem if NPS < 20 or churn > 10% by Q3") and action (e.g., "Pivot to SMB segment if enterprise adoption lags").

## Anti-Patterns

1. **Assuming Willingness-to-Pay Without Research**: You've estimated customers will pay $500/month but never validated pricing. Run Van Westendorp pricing study: ask customers "At what price is this too cheap to be good?" and "At what price is this too expensive?" Intersection gives realistic price band. Skip this and you'll either price too high (no customers) or too low (unsustainable unit economics).

2. **Competitive Analysis as Feature Checklist**: Listing "Competitor A has feature X, we have X+Y" doesn't explain why you win. Real analysis: "Competitor A owns enterprise accounts ($10K+ deals, 18-month sales cycles), we own SMB self-serve segment ($50-500/month, 2-week decisions). We can't win on enterprise support, so we differentiate on ease-of-use and quick ROI for lean teams."

3. **Funding Ask Without Clear Use**: "We're raising $5M" without allocating it. Investors demand: "What % goes to team, product, sales, operations?" and "How does this funding change your trajectory?" Vague: "We'll hire engineers and do marketing." Specific: "We'll hire 3 engineers (build mobile app), 2 AEs (launch West Coast), 1 marketing ops hire (measure CAC). This lets us reach $2M ARR by Year 2."

