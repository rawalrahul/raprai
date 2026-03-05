---
name: competitor-analysis-generator
description: "Generate structured competitor analyses mapping features, pricing, positioning, go-to-market, strengths/weaknesses, market share, and strategic moves. Informs product roadmap and competitive positioning."
category: business
difficulty: intermediate
model_boost: "Prevents shallow competitive understanding and missed positioning opportunities; produces instead detailed, actionable competitive intelligence."
---

# Competitor Analysis Generator

## Purpose
A competitor analysis systematically maps competitive landscape to inform strategy. This skill generates structured analyses of 3-5 direct competitors, evaluating: feature sets, pricing models, GTM strategy, market positioning, customer segments, strengths/weaknesses, financial health, and recent strategic moves. Output informs product roadmap prioritization, pricing strategy, and differentiation positioning.

## When to Use
- Entering a new market or launching a new product
- Quarterly strategic planning (keep competitive understanding current)
- Product prioritization decisions (is feature X defensible or commoditizing?)
- Pricing strategy review (is our pricing aligned to market?)
- M&A evaluation (acquiring competitor or acquired by one?)
- **Do NOT use when**: Market is nascent (no competitors exist); competitive intelligence tools don't provide visibility; you're locked into strategy (analysis should inform, not paralyze decisions).

## Instructions

### Step 1: Identify Direct Competitors
Direct competitors are companies solving the same customer problem in the same way. Not: companies with overlapping features, but competitors targeting your same use case.

**Example**: If you're a B2B SMB invoice automation tool:
- **Direct competitors**: {{Vendor A}} (invoice automation, $200-500/month), {{Vendor B}} (same), {{Vendor C}} (same)
- **Indirect competitors**: ERP systems (larger feature set, higher price, enterprise focus), manual spreadsheet (free, effort-intensive), temp staffing (contractor doing invoicing)

Distinguish direct from indirect. Analyze top 3-5 direct competitors by estimated market share or funding raised.

### Step 2: Map Feature Sets & Product Positioning
For each competitor, document:
- **Core features**: What are the 5-10 features that define the product?
- **Differentiation**: What features are unique to this competitor? What's table-stakes (everyone has it)?
- **Positioning statement**: How does competitor describe their product? (e.g., "The easiest-to-use invoice automation for SMBs")
- **Product maturity**: Early stage (MVP), growth (feature-complete), mature (optimized), declining (losing users)

**Table-Stakes Features** (everyone has):
- Invoice data extraction
- Workflow approval
- Integration to accounting software

**Differentiators**:
- Competitor A: "Mobile-first, works offline"
- Competitor B: "AI-powered exception handling"
- Competitor C: "Lowest pricing for SMBs"

### Step 3: Analyze Pricing Model & Strategy
Document:
- **Pricing model**: Per-user, per-invoice, tiered, usage-based, freemium
- **Price points**: List specific pricing tiers and what customers each tier targets
- **Packaging**: What's included in each tier? What requires add-ons?
- **Price justification**: Why does competitor charge this price? What value does it claim?

**Pricing Positioning Matrix**:
- **Premium/Feature-Rich**: {{Vendor}} @ ${{}} per user, targets enterprises
- **Mid-Market/Balanced**: {{Vendor}} @ ${{}} per invoice, targets mid-market
- **Budget/Simple**: {{Vendor}} @ ${{}} per month, targets SMBs

### Step 4: Evaluate Go-to-Market Strategy
- **Sales motion**: Direct sales team, inside sales, self-serve, partnerships, channel
- **Customer acquisition channels**: Paid ads, organic, partnerships, integrations, marketplace
- **Sales cycle**: Enterprise (6-18 months), mid-market (1-3 months), SMB (2-4 weeks)
- **Customer success approach**: Named account managers, self-serve, community, content

**GTM Positioning**:
- Competitor A: Enterprise GTM (large sales team, 12-month sales cycle, custom integrations)
- Competitor B: SMB self-serve (product-led growth, free trial, self-service onboarding)
- Competitor C: Channel GTM (VAR partners, resellers)

### Step 5: Assess Market Share & Customer Base
- **Estimated customers**: Look at publicly available data (G2, Capterra), funding announcements, customer press releases
- **Market share**: Estimate % of target market (competitor customers / total addressable customers in segment)
- **Customer segments**: Who do they serve? Verticals, company sizes, geographies
- **Customer concentration**: Is growth from new customers or expansion of existing ones?

**Data Sources**:
- G2, Capterra reviews (customer count estimates)
- LinkedIn (employee count, hiring trends)
- Crunchbase (funding, investor list)
- Company announcements (customer wins, partnerships)
- Financial filings (if public: revenue, churn, CAC)

### Step 6: Document Strengths & Weaknesses
For each competitor:

**Strengths**:
- What are they doing well? What would customers miss if they switched?
- Defensible advantages (data, network effects, brand, regulatory)
- Example: "Competitor A has largest customer base (network effects), integrated payment processing (high switching cost)"

**Weaknesses**:
- What are they doing poorly? What do customers complain about?
- Feature gaps, UX issues, pricing, support
- Example: "Competitor B's SMB customers complain onboarding takes 3 weeks; poor mobile experience"

**How to Validate**: Customer interviews, G2 reviews, sales calls with prospects evaluating multiple solutions.

### Step 7: Analyze Recent Strategic Moves
- **Product launches**: What new features did competitor launch? What does this signal about roadmap?
- **Pricing changes**: Price increases, new tiers, packaging changes
- **M&A activity**: Did they acquire smaller company? Why (feature, team, customer base)?
- **Partnerships**: New integrations, reseller partnerships, technology partnerships
- **Funding**: Series A raised = scaling GTM; Acquihire = struggling; APE (acq-hire) = talent grab

**Example**: "Competitor A raised Series B ($50M) in Q1 2025 → signal they'll scale sales team, likely offer aggressive discounts Q2-Q3 to grab market share. Should prepare pricing defensibility."

### Step 8: Build Competitive Positioning Map
Create a 2x2 matrix to visualize competitive positioning:
- X-axis: Feature Richness vs. Simplicity
- Y-axis: Price (premium vs. budget)
- Or: Ease-of-Use vs. Feature Depth
- Or: Speed-to-Value vs. Customization Depth

Plot each competitor and yourself. Identify white space (unserved positioning).

### Step 9: Develop Response Strategy
For each competitor threat, articulate:
- **If they do X** (e.g., lower price), **we respond with Y** (e.g., emphasize ROI not price, expand feature set)
- **If they capture Y% of market**, at what point do we need to pivot?
- **How do we defensibly compete** (feature, price, GTM, positioning)?

Don't assume head-to-head competition on price (dangerous). Find your defensible positioning.

## Output Template

```markdown
# Competitive Analysis: {{Market/Segment}}
**Analysis Date**: {{Date}}
**Analyst**: {{Name}}
**Market Scope**: {{Target market (e.g., SMB invoice automation, US)}}

---

## EXECUTIVE SUMMARY

**Market Size**: {{TAM estimate, growth rate}}
**Competitive Intensity**: {{Fragmented / Moderate / Intense}}
**Market Leader**: {{Competitor with highest market share or funding}}
**Market Trends**: {{Consolidation, emergence of new player, commoditization}}

**Our Positioning**: {{Where we sit in competitive landscape}}
- {{Competitive advantage 1}}
- {{Competitive advantage 2}}
- {{Area of vulnerability (competitor advantage)}}

---

## COMPETITIVE LANDSCAPE

| Competitor | Est. Customers | Market Share (%) | Positioning | Funding Stage |
|---|---|---|---|---|
| {{Competitor A}} | {{#}} | {{%}} | {{Positioning}} | {{Series B / Public / Bootstrap}} |
| {{Competitor B}} | {{#}} | {{%}} | {{}} | {{}} |
| {{Competitor C}} | {{#}} | {{%}} | {{}} | {{}} |
| **{{Our Company}}** | **{{#}}** | **{{%}}** | **{{Our positioning}}** | **{{Our stage}}** |

---

## DETAILED COMPETITOR PROFILES

### Competitor 1: {{Name}}
**Overview**: {{1-sentence positioning}}
**Target Market**: {{Segment / verticals / company sizes / geographies}}
**Estimated Annual Revenue**: {{${{amount}}}} (based on {{# customers}} × {{avg ARR}})

#### Features & Product
**Core Features**:
- {{Feature 1}}: {{Description}}
- {{Feature 2}}: {{}}
- {{Feature 3}}: {{}}

**Differentiated Features** (Competitor A has, we don't):
- {{Feature A}}: {{Why it matters}}
- {{Feature B}}: {{}}

**Table-Stakes Features** (Everyone has):
- {{Feature X}}
- {{Feature Y}}

**Product Gaps** (What customers complain about):
- {{Gap 1}}: {{Evidence (G2 review, customer feedback)}}
- {{Gap 2}}: {{}}

**Product Roadmap** (Based on recent releases):
- {{Recent launch}}: Signals {{strategic direction}}
- {{Future direction}}: {{Rumored or inferred from hiring}}

#### Pricing & Packaging

| Tier | Price | Included | Target Segment |
|---|---|---|---|
| **{{Tier 1}}** | ${{}} {{/month or per X}} | {{Features}} | {{SMB / Mid-market / Enterprise}} |
| **{{Tier 2}}** | ${{}} | {{}} | {{}} |
| **{{Tier 3}}** | ${{}} | {{}} | {{}} |

**Pricing Positioning**: {{Premium / Mid-market / Budget}} vs. market
- **Justification**: Competitor A charges 2x market average because {{unique feature / brand / enterprise focus}}
- **Weakness**: Pricing is {{%}} higher than Competitor B, limiting SMB adoption

**Recent Pricing Changes**: {{Price increase / new tier / packaging change}} on {{date}} → signals {{strategic direction}}

#### Go-to-Market Strategy

**Sales Motion**:
- {{Direct sales / Inside sales / Self-serve / Channel}}
- **Sales team size**: {{# of AEs}} (estimated from LinkedIn)
- **Sales cycle**: {{Enterprise: 6-12 months / Mid-market: 1-2 months / SMB: 2-4 weeks}}
- **CAC estimate**: {{$amount}} (based on pricing and sales team size)

**Customer Acquisition Channels**:
- {{Channel 1}} (estimated {{%}} of customers): {{How it works, investment}}
- {{Channel 2}} (estimated {{%}}): {{}}
- {{Channel 3}} (estimated {{%}}): {{}}

**Marketing Positioning**:
- **Tagline**: "{{Company tagline}}"
- **Key messages**: {{Message 1}}, {{Message 2}}, {{Message 3}}
- **Content strategy**: {{Blog, webinars, case studies, integrations marketplace}}

**Customer Success**:
- {{Named account managers / Self-serve / Community / Hybrid}}
- **NPS estimate**: {{Based on public reviews}}: {{High / Medium / Low}}

#### Market Position & Customer Base

**Estimated Customer Count**: {{#}} customers (based on {{G2 reviews / funding / LinkedIn headcount}})
- **Growth trajectory**: {{Growing rapidly (Series B raised) / Stable / Declining}}
- **Growth channels**: {{New customers, expansion revenue, acquisitions}}

**Primary Customer Segments**:
| Segment | Est. % of Customers | Reason (Why Competitor Won) | Risk (When We Could Win) |
|---|---|---|---|
| {{Segment 1}} | {{%}} | {{Why they chose Competitor}} | {{Our positioning vs. theirs}} |
| {{Segment 2}} | {{%}} | {{}} | {{}} |

**Geographic Presence**: {{North America / Europe / Global}}
- **Concentration**: {{%}} of customers in {{region}} (limiting expansion)

**Customer Concentration**: {{Top {{#}} customers represent {{%}} of revenue}}
- **Risk**: If {{top customer}} churns, revenue drops {{%}} (vulnerable)

#### Strengths & Weaknesses

**Top 3 Strengths**:
1. {{Strength 1}}: {{Why defensible}} (Evidence: {{proof}})
   - How customers benefit: {{}}
   - Switching cost if lost: {{High / Medium / Low}}

2. {{Strength 2}}: {{}}

3. {{Strength 3}}: {{}}

**Top 3 Weaknesses**:
1. {{Weakness 1}}: {{Why it matters}} (Evidence: {{G2 complaints, lost deals, feature gap}})
   - Impact on customer: {{}}
   - Our opportunity: {{How we exploit this}}

2. {{Weakness 2}}: {{}}

3. {{Weakness 3}}: {{}}

#### Financial & Strategic Health

**Funding**: {{Series B, ${{amount}}, raised {{date}}, investor list}}
- **Runway**: {{Est. {{#}} years}} (based on burn rate estimate)
- **Valuation**: {{${{amount}}}} (Series B valuation)

**Recent Strategic Moves**:
- {{M&A}}: Acquired {{company}} for {{${{amount}}}} (talent / feature / customer base acquisition)
- {{Partnerships}}: Integrated with {{partner}} (expands TAM / increases switching cost)
- {{Product launches}}: Shipped {{feature}} (signals roadmap direction)
- {{Hiring}}: {{# of roles open}} (signals scaling focus: {{Sales / Product / Ops}})

**Trajectory**: {{Growing rapidly / Consolidating / Struggling}}
- **Next 12 months**: {{Likely to {{raise Series C / become acquisition target / expand geography}} }}

---

### Competitor 2: {{Name}}
[Same structure as above]

---

### Competitor 3: {{Name}}
[Same structure as above]

---

## COMPETITIVE POSITIONING ANALYSIS

### Feature Parity Matrix

| Feature | {{Our Company}} | {{Competitor A}} | {{Competitor B}} | {{Competitor C}} |
|---|---|---|---|---|
| {{Feature 1}} | ✓ | ✓ | ✓ | ✗ |
| {{Feature 2}} | ✓ | ✗ | ✓ | ✓ |
| {{Differentiated A}} | ✗ | ✓ | ✗ | ✗ |
| {{Differentiated B}} | ✓ | ✗ | ✗ | ✗ |

**Interpretation**:
- {{Feature 1-2}} are table-stakes (everyone has)
- {{Competitor A}} has {{unique feature}} we're missing; need to build or accept we won't win customers who prioritize this
- {{We have {{unique feature}} that {{Competitor A}} lacks; defensible advantage}}

### Positioning Map (2x2: Ease-of-Use vs. Feature Depth)

```
Feature Depth (High)
    |
    |  Competitor A (Complex, Feature-Rich)
    |  ○ Enterprise-focused
    |
    |              Competitor B (Balanced)
    |              ○ Mid-market sweet spot
    |
    ├────────────────────────> Ease-of-Use (High)
    |
    |              ✓ Us (Simple, Fast)
    |              ○ SMB self-serve focus
    |
    |  Competitor C (Simple, Limited)
    |  ○ Free tier, limited features
    |
```

**Our Positioning**: {{We own {{white space}} - positioning that no competitor dominates}}
- {{Competitor A}} can't compete here without {{sacrifice (e.g., supporting SMB pricing model breaks enterprise economics)}}
- {{Competitor B}} could compete but hasn't invested ({{reason}}: lower TAM, not strategic)

---

## WIN/LOSS ANALYSIS

### We Win Against {{Competitor A}} When:
- {{Customer prioritizes {{trait]]}} (e.g., ease-of-use) — {{our advantage}}
- {{Customer size / budget}}: SMB segment ({{Competitor A}} targets enterprise)
- {{Customer needs {{feature we have, they don't}}}}: {{example}}

**Key Wins**: {{# of recent wins}}, primarily in {{SMB segment / {{geo}}}}, displaced {{Competitor A}} {{ % of the time}}

### We Lose to {{Competitor A}} When:
- {{Customer prioritizes {{trait]]}} (e.g., feature completeness, enterprise support)
- {{Competitor A}} has {{advantage we lack}}: {{example}}
- {{Price sensitivity is low}} ({{Competitor A}} is premium; we can't compete on price without breaking unit economics)

**Key Losses**: {{# of recent losses}}, primarily {{reason}}, {{Competitor A}} chosen {{% of the time}}

### Win Rate by Segment:
| Segment | {{Our Win Rate}} | {{Strongest Competitor}} | Our Weakness |
|---|---|---|---|
| {{SMB}} | {{%}} | {{}} | {{}} |
| {{Mid-market}} | {{%}} | {{}} | {{}} |
| {{Enterprise}} | {{%}} | {{}} | {{}} |

---

## STRATEGIC IMPLICATIONS & RECOMMENDATIONS

### Threat Assessment

**High Threat**: {{Competitor A}}
- **Reason**: {{Well-funded, expanding into our SMB segment, feature parity in {{#}} months}}
- **Timeline**: {{6-month window}} before they're directly competitive in our beachhead
- **Response**: Invest in {{defensibility: network effects, switching cost, differentiation}}

**Medium Threat**: {{Competitor B}}
- **Reason**: {{Growing, adjacent segment, could expand into ours}}
- **Timeline**: {{12-18 months}} before direct competition
- **Response**: Monitor / prepare {{response}}

**Low Threat**: {{Competitor C}}
- **Reason**: {{Limited funding, small team, not innovating}}
- **Timeline**: {{Won't be credible threat in next 18 months}}
- **Response**: Monitor, but don't invest defensively

### Positioning Recommendation

**Defend**: {{Our positioning}}
- {{We own {{positioning]]} which {{Competitor}} can't attack without {{sacrifice}}
- {{To maintain defensibility}}:
  - {{Invest in {{feature / brand / community]]}}}
  - {{Avoid competing on {{axis]]}} where {{Competitor]] has advantage}}

**Expand**: {{Adjacent market}}
- {{{{ Competitor A}} dominates {{market}}, but hasn't captured {{adjacent segment}}}}
- {{We can win {{adjacent]] without direct competition}}

**Avoid**: {{Positioning where {{Competitor]] dominates}}
- {{Competing with {{Competitor A]] on {{axis]] means {{losing on unit economics / losing on feature depth}}}}
- {{Don't chase features {{Competitor]] has; differentiate instead}}

### Product Roadmap Implications

**Feature Priorities**:
1. {{Feature A}}: {{Invest}} ({{Competitor A]] lacks; defensible differentiation)
2. {{Feature B}}: {{Defer}} (Everyone has; commoditizing)
3. {{Feature C}}: {{Monitor}} ({{Competitor B]] will ship in Q2; we need by Q3 to stay competitive)

**Features NOT to Build**:
- {{Feature X}}: {{Competitor A]] has 2-year lead; can't catch up; accept market loss
- {{Feature Y}}: {{Doesn't fit our positioning}}

---

## COMPETITIVE MONITORING CADENCE

**Quarterly Review** (This Analysis): Update once per quarter
- {{New product launches}}
- {{Pricing changes}}
- {{Strategic moves (hiring, M&A, partnerships)}}

**Annual Deep Dive** (Next refresh): {{Date}}
- {{Update all sections}}
- {{Refresh customer/market data}}
- {{Reassess win/loss reasons}}

**Continuous Monitoring** (Weekly/Monthly):
- {{G2 reviews and ratings}}
- {{Company announcements and press releases}}
- {{Sales calls: "What other solutions did you evaluate?" "Why did you choose us?"}}
- {{Lost deal analysis: "What would have made us win?"}}

---

## APPENDIX

### A. Competitor Pricing Comparison
[Detailed pricing comparison table]

### B. Feature Comparison Matrix
[Feature-by-feature comparison]

### C. Win/Loss Data (Last {{#}} months)
[Summary of recent competitive wins/losses and reasons]

### D. Customer Interview Summaries
[Feedback on competitors from recent customer calls/interviews]

```

## Quality Gates
- [ ] 3-5 direct competitors identified (not indirect); ranked by market share or threat level
- [ ] For each competitor: features documented, pricing analyzed, GTM strategy identified
- [ ] Market share estimates supported by data (G2, funding, LinkedIn, customer count)
- [ ] Strengths/weaknesses assessed with evidence (G2 reviews, lost deals, customer feedback)
- [ ] Recent strategic moves (funding, M&A, partnerships) documented with implications
- [ ] Win/loss analysis shows where you win vs. each competitor and why
- [ ] Positioning map visualizes competitive landscape and identifies white space
- [ ] Product roadmap recommendations flow from competitive analysis (not isolated)
- [ ] Monitoring cadence established (quarterly review, continuous weak signals)

## Examples

### Good Output (excerpt)
```
COMPETITIVE LANDSCAPE:
| Competitor | Est. Customers | Market Share | Positioning | Funding |
|---|---|---|---|---|
| Competitor A | 15,000 | 45% | Enterprise-focused, premium pricing | Series C, $150M |
| Competitor B | 8,000 | 24% | Mid-market balanced | Series B, $50M |
| Competitor C | 5,000 | 15% | SMB budget-friendly | Series A, $15M |
| **Us** | **1,200** | **4%** | **SMB self-serve, fastest onboarding** | **Series A, $10M** |

---

COMPETITOR A STRENGTHS:
1. Largest customer base (15K) → network effects (partners integrate, customers use)
2. Enterprise sales team (200+ AEs) → can pursue $10K+/month deals we can't support
3. Feature completeness (50+ integrations) → enterprise customers want everything

COMPETITOR A WEAKNESSES:
1. Onboarding takes 4-6 weeks (customer complaint: "We needed this in 3 days") → opportunity for us (our onboarding: 1 day)
2. Pricing starts at $2K/month → SMBs price-sensitive; we're $200/month
3. Mobile experience poor (G2 review: "Desktop only, can't approve on phone")

---

WIN/LOSS ANALYSIS:
We Win Against Competitor A When:
- Customer is SMB (<50 employees, <$500/month budget)
- Customer wants to start in <1 week
- Customer prioritizes ease-of-use over features

We Lose to Competitor A When:
- Customer is enterprise (>500 employees)
- Customer needs 10+ integrations (we have 4)
- Customer willing to invest 6 weeks for perfect feature fit

Win Rate vs. Competitor A:
- SMB: 75% (our sweet spot)
- Mid-market: 25% (Competitor A's sweet spot)
- Enterprise: 5% (Competitor A's strong moat)

---

RECOMMENDATION:
Double-down on SMB positioning. Competitor A can't win SMB profitably (enterprise sales unit economics require $2K+ ACV). We own this segment defensibly for 18+ months. By Q3, prioritize: (1) Integration library (currently 4, competitors have 15+), (2) Mobile approval (quick win, removes customer complaint), (3) Customer success automation (reduce churn below Competitor A's 5%).
```

### Bad Output (what to avoid)
```
Competitors:
- Competitor A: Large, well-funded
- Competitor B: Growing fast
- Competitor C: Smaller player

Analysis: They have more features than us. We need to build more features to compete.

(Why this fails: No specific feature comparison, no market positioning, no win/loss data, no insight into why customers choose competitors, generic "build more features" recommendation isn't strategic)
```

## Common Mistakes

1. **Confusing Direct with Indirect Competitors**: You list ERP systems, spreadsheets, and other SaaS tools in same analysis. Better: Separate direct (solve same problem, same customer) from indirect (alternative solutions). Focus competitive analysis on direct; acknowledge indirect as alternatives but don't over-analyze.

2. **Assuming Competitor Data is Accurate**: "Competitor A has 50K customers" based on one source. Real data is estimated from multiple sources (G2, funding announcements, hiring, press releases, customer interviews). Cross-check. If you can't validate, flag as "estimated (low confidence)."

3. **Missing Recent Strategic Moves**: Analysis is 6 months old. Competitor A raised Series C 2 months ago, launched new pricing, hired 30 people, but your analysis doesn't reflect this. Better: Update quarterly. Subscribe to company newsletters, job boards, funding alerts.

4. **No Win/Loss Data**: Analysis says "Competitor A has feature X, we don't," but you have no evidence customers actually want feature X. Better: Interview 5-10 customers who chose Competitor A and ask "Why didn't you choose us?" Win/loss data is gold.

5. **Recommendations Disconnected from Competitive Analysis**: Analysis: "Competitor A is stronger in {{area}}." Recommendation: "Build feature Y" (which isn't related to area). Better: Recommendation flows from analysis. "Competitor A is stronger in {{area}} because {{reason}}. We should {{action}} to neutralize or {{action}} to avoid competing there."

## Anti-Patterns

1. **Feature Parity Racing**: Competitor launches Feature X, immediately we add Feature X. Problem: You're reactive, always behind. Better: Decide your positioning. "Competitor owns feature completeness. We own simplicity. We won't try to out-feature them; we'll out-simplify."

2. **Pricing Knee-Jerk**: Competitor lowers price 20%, immediately we follow. Problem: Price war erodes margins, neither company wins. Better: Analyze why they lowered price (consolidating market share, failing to sell at higher price, new customer segment). If they're targeting our segment, respond with value, not price (better unit economics, faster onboarding, stronger ROI story).

3. **Vertical Integration as Defensive Move**: Competitor integrates with payment processing, so we add it too. Problem: You're chasing features, not customer value. Better: Ask, "Do our customers ask for this? Is it in top {{#}} requests?" If no, defer.

4. **Ignoring Positioning Moat**: Competitor has network effects (more users = more value). Instead of trying to copy network, you build alternative moat (brand, data, switching cost). Better: Acknowledge you won't beat them on network effects; compete on different axis.

5. **No Contingency for Competitor Moves**: "If Competitor A lowers price 25%, we'll {{action}}." But no action is planned. When they move, chaos ensues. Better: War-game scenarios. "If they go freemium, we respond with {{}}. If they enter SMB segment, we respond with {{}}." You have playbook ready.

