---
name: swot-analysis-generator
description: "Generate structured SWOT analyses with actionable strategies derived from each quadrant (SO/WO/ST/WT). Includes strategic implications, prioritization, and tactical initiatives tied to business objectives."
category: business
difficulty: intermediate
model_boost: "Prevents generic SWOT lists that lack actionable strategy; produces instead specific, prioritized initiatives tied to competitive positioning."
---

# SWOT Analysis Generator

## Purpose
A SWOT analysis maps Strengths, Weaknesses, Opportunities, and Threats to reveal strategic positioning. This skill generates structured SWOTs with strategic implications: offensive strategies (Strengths + Opportunities), defensive strategies (Weaknesses + Threats), leverage strategies (Strengths vs. Threats), and correction strategies (Weaknesses vs. Opportunities). Output is a living document that guides 12-month strategic priorities and resource allocation.

## When to Use
- Annual strategic planning or board-level strategic reviews
- Before entering a new market or launching a major product
- Competitive positioning analysis during market shifts
- M&A decision-making (acquire or merge)
- **Do NOT use when**: You lack market data or customer research (gather first); analysis is surface-level (requires deeper investigation); you're avoiding strategic decisions (SWOT informs choice, doesn't make it).

## Instructions

### Step 1: Identify Internal Strengths (Facts, Not Aspirations)
Strengths are comparative advantages that are real and defensible. Document evidence:
- **Team expertise**: Prior exits, relevant domain experience, customer relationships
- **Proprietary assets**: Data, patents, regulatory approvals, exclusive partnerships
- **Financial position**: Cash runway, profitability, unit economics (CAC, LTV)
- **Product advantages**: NPS score, feature set unmatched by competitors, speed-to-market
- **Distribution**: Sales channel, brand, partner network
- **Cost structure**: Lower CAC, higher gross margin than competitors

For each strength, ask: "Can a competitor replicate this in 12 months?" If yes, it's not a strength—it's a feature. Rank by defensibility (10-year durability).

### Step 2: Identify Internal Weaknesses (Honesty Required)
Weaknesses are gaps relative to competitors or market requirements. Be specific:
- **Team gaps**: Sector inexperience, no prior fundraising experience, weak sales background
- **Product gaps**: Missing features customers explicitly request, poor mobile experience, slow onboarding
- **Financial constraints**: Limited runway, low margins, high CAC payback period
- **Operational**: No documented processes, poor data infrastructure, weak analytics
- **Market position**: Low brand awareness, small customer base, low NPS (< 40)
- **Technical debt**: Legacy code, scalability issues, security vulnerabilities

For each weakness, assess: "How long to fix?" (weeks vs. months vs. quarters). Distinguish fixable weaknesses from fundamental gaps.

### Step 3: Identify External Opportunities (Macro + Micro)
Opportunities are external changes you can exploit via your strengths or capability building.
- **Market trends**: Growing customer segment (AI adoption, regulatory shift, demographic), TAM expansion
- **Competitive gaps**: Incumbent weakness (high pricing, poor UX, no mobile), competitor exit
- **Channel expansion**: New sales channel (partnerships, vertical integration, geographic expansion)
- **Adjacent markets**: Customers requesting similar problems, vertical-specific variants
- **Technology shifts**: New integration possibilities, API availability, infrastructure improvement
- **Regulatory**: Compliance shift opening new segments, reduced barriers to entry

For each opportunity, estimate: market size, time window (is this open for 2 years or 6 months?), required investment.

### Step 4: Identify External Threats (Realistic, Not Paranoid)
Threats are external changes that could harm your business if left unaddressed.
- **Competitive threats**: Well-funded competitors entering market, pricing pressure, feature parity
- **Market threats**: Demand destruction (regulatory change, economic downturn), market consolidation
- **Customer concentration**: Top customer represents >20% of revenue; if they churn, revenue drops
- **Technology threats**: Emerging alternative (blockchain replacing databases), commoditization
- **Economic**: Recession, interest rate changes affecting customer budgets
- **Key person risk**: Founder departure, key customer relationship held by one person

For each threat, estimate: probability (low/medium/high) and impact if realized.

### Step 5: Generate SO Strategies (Offensive: Strengths + Opportunities)
These are "attack" strategies where you use your strengths to capture opportunities.

Example: Strength (strong product NPS), Opportunity (SMB market growing 25% CAGR)
→ **Strategy**: "Launch SMB vertical, invest sales team focused on <100-person companies where our ease-of-use (high NPS) is defensible advantage vs. incumbents chasing enterprises."

For each SO pair, define:
- **Initiative**: What you'll do (specific, measurable)
- **Timeline**: Quarter launched
- **Required investment**: Team, budget
- **Expected outcome**: Revenue, market share, positioning
- **Success metric**: NPS retention, customer acquisition rate, market penetration

### Step 6: Generate ST Strategies (Defensive: Strengths vs. Threats)
These are defensive strategies where you use strengths to neutralize threats.

Example: Strength (high product quality, strong brand), Threat (well-funded competitor entering)
→ **Strategy**: "Invest in brand/community moat. If competitors enter, we've built switching costs (engaged user community, network effects). Incumbent competitors compete on price; we compete on loyalty."

### Step 7: Generate WO Strategies (Correction: Weaknesses into Opportunities)
These are capability-building strategies where you fix weaknesses to capture opportunities.

Example: Weakness (weak sales team), Opportunity (enterprise segment has 3x larger ACV)
→ **Strategy**: "Hire VP Sales from Salesforce (brought similar SMB-to-enterprise playbook). Build enterprise sales team over Q1-Q2. By Q3, pursue enterprise customers willing to pay $5K+/month for custom integrations."

### Step 8: Generate WT Strategies (Mitigation: Weaknesses × Threats)
These are survival strategies where you mitigate or exit threats amplified by weaknesses.

Example: Weakness (high churn 8%), Threat (competitor offers free trial)
→ **Strategy**: "Competitor's free trial will poach low-intent users (high churn anyway). Focus on retention of high-intent customers (NPS > 50). Improve onboarding to reduce first-month churn from 8% to 5%, making payback period 4 months instead of 5 (more defensible)."

### Step 9: Prioritize and Sequence Strategies
Rank SO, ST, WO, WT strategies by: (1) Expected impact on revenue, (2) Ease of execution (low, medium, high), (3) Time window (urgency). Create a 12-month roadmap:

**Q1**: Launch {{SO initiative}} (offensive priority) + {{WO initiative}} (fix critical weakness before pursuing opportunity)
**Q2**: {{Continue}} + {{ST initiative}} (begin defensive positioning)
**Q3-Q4**: {{WT mitigation}} (ongoing), {{scale winners}}

Flag which strategies are kill-or-be-killed (must do) vs. nice-to-have.

### Step 10: Document Strategic Implications and Trade-offs
SWOT doesn't just identify strategies; it clarifies where to focus and where to accept risk.

Example implications:
- "We're optimizing for SMB (SO strategy). This means we won't pursue enterprise segment aggressively even though margins are higher—we lack sales team strength (weakness). By Q3 2025, revisit this decision if we hire enterprise VP Sales."
- "Our threat is competitor pricing. Our defense is product quality + community. This requires higher R&D spend, accepting lower short-term margins. We're betting that brand loyalty beats price competition."
- "We're weak in analytics. This threatens our ability to optimize CAC. Q1-Q2 action: build data infrastructure. By Q3, measure CAC by channel and kill low-ROI channels."

## Output Template

```markdown
# SWOT Analysis: {{Company/Product Name}}
**Analysis Date**: {{Date}}
**Scope**: {{Business unit, market segment, or time period}}
**Prepared By**: {{Team}}

---

## STRENGTHS (Internal Advantages)
### Financial & Operational
- **Strength 1**: {{Description}} (Evidence: {{metric or validation}}) | Defensibility: {{}} | Duration: {{}}
- **Strength 2**: {{}} | Defensibility: {{}} | Duration: {{}}

### Product & Technology
- **Strength 3**: {{}} | Evidence: {{}} | Defensibility: {{}} | Duration: {{}}
- **Strength 4**: {{}} | Evidence: {{}} | Defensibility: {{}} | Duration: {{}}

### Market & Distribution
- **Strength 5**: {{}} | Evidence: {{}} | Defensibility: {{}} | Duration: {{}}

**Rank by Defensibility** (10-year durability):
1. {{Most defensible strength}}
2. {{}}
3. {{}}

---

## WEAKNESSES (Internal Gaps)
### Financial & Operational
- **Weakness 1**: {{Description}} (Gap vs. competitor: {{metric}}) | Time to Fix: {{}} | Impact if Not Fixed: {{}}
- **Weakness 2**: {{}} | Time to Fix: {{}} | Impact: {{}}

### Product & Technology
- **Weakness 3**: {{}} | Time to Fix: {{}} | Impact: {{}}
- **Weakness 4**: {{}} | Time to Fix: {{}} | Impact: {{}}

### Market & Team
- **Weakness 5**: {{}} | Time to Fix: {{}} | Impact: {{}}

**Critical Weaknesses** (Must fix in next 12 months):
1. {{Most urgent}}
2. {{}}

---

## OPPORTUNITIES (External Advantages to Exploit)
### Market Trends
- **Opportunity 1**: {{Description}} (Market size: {{$}}, Timeline: {{months}} open) | Required investment: {{}} | Potential revenue: {{$}}
- **Opportunity 2**: {{}} | Market size: {{}} | Timeline: {{}} | Investment: {{}} | Revenue: {{}}

### Competitive Gaps
- **Opportunity 3**: {{}} (Competitor weakness: {{}}; our advantage: {{}}) | Window: {{}}

### Channel & Partnership
- **Opportunity 4**: {{}} | Potential impact: {{}}

### Technology & Data
- **Opportunity 5**: {{}} | Window: {{}}

**Biggest Opportunities** (Ranked by size × timing):
1. {{}}
2. {{}}

---

## THREATS (External Risks)
### Competitive Threats
- **Threat 1**: {{Description}} (Competitor: {{name}}, funded: {{$}}, weakness: {{}}}) | Probability: {{High/Med/Low}} | Impact: {{}}
- **Threat 2**: {{}} | Probability: {{}} | Impact: {{}}

### Market Threats
- **Threat 3**: {{}} (Regulatory/economic shift) | Probability: {{}} | Impact: {{}}

### Customer Concentration
- **Threat 4**: {{}} (Top customer % of revenue: {{}}, churn risk if lost) | Probability: {{}} | Impact: {{}}

### Operational Risks
- **Threat 5**: {{}} | Probability: {{}} | Impact: {{}}

**Highest-Probability Threats**:
1. {{}}
2. {{}}

---

## STRATEGIC INITIATIVES

### SO Strategies: Offensive (Strengths + Opportunities)
**Strategy 1**: {{Name}}
- **Strengths Leveraged**: {{Strength A}}, {{Strength B}}
- **Opportunities Exploited**: {{Opportunity X}}
- **Initiative**: {{Specific action: launch {{product}}, expand {{market}}, hire {{role}}}}
- **Timeline**: {{Quarter}}
- **Investment Required**: {{Team, budget}}
- **Expected Outcome**: {{Revenue target, market position, customer count}}
- **Success Metrics**: {{NPS/churn/CAC/revenue growth}}
- **Priority**: {{Kill-or-be-killed / High / Medium}}

**Strategy 2**: {{}}
...

### ST Strategies: Defensive (Strengths vs. Threats)
**Strategy 1**: {{Name}}
- **Strengths Leveraged**: {{}}
- **Threats Neutralized**: {{}}
- **Initiative**: {{Specific action}}
- **Timeline**: {{}}
- **Investment**: {{}}
- **Expected Outcome**: {{Competitive moat, reduced threat impact}}
- **Success Metrics**: {{}}
- **Priority**: {{}}

**Strategy 2**: {{}}
...

### WO Strategies: Correction (Weaknesses into Opportunities)
**Strategy 1**: {{Name}}
- **Weaknesses Addressed**: {{}}
- **Opportunities Enabled**: {{}}
- **Initiative**: {{Build capability: hire {{}}, invest in {{}}}}
- **Timeline**: {{}}
- **Investment**: {{}}
- **Expected Outcome**: {{Become competitive, capture market}}
- **Success Metrics**: {{}}
- **Priority**: {{}}

**Strategy 2**: {{}}
...

### WT Strategies: Mitigation (Weaknesses + Threats)
**Strategy 1**: {{Name}}
- **Weaknesses Mitigated**: {{}}
- **Threats Addressed**: {{}}
- **Initiative**: {{Action to reduce exposure}}
- **Timeline**: {{}}
- **Investment**: {{}}
- **Expected Outcome**: {{Reduced threat impact, survival}}
- **Success Metrics**: {{}}
- **Priority**: {{}}

**Strategy 2**: {{}}
...

---

## 12-Month Strategic Roadmap

| Quarter | SO Initiative | ST Initiative | WO Initiative | WT Initiative | Budget | Key Result |
|---|---|---|---|---|---|---|
| **Q1** | {{SO1 launch}} | {{ST1 planning}} | {{WO1: hire {{}}}} | {{WT1: {{}}}} | ${{}} | {{Metric}} |
| **Q2** | {{SO1 scale}} | {{ST1 launch}} | {{WO1: build}} | {{WT1: monitor}} | ${{}} | {{Metric}} |
| **Q3** | {{SO2 launch}} | {{ST1 scale}} | {{WO1 measure}} | {{WT2 launch}} | ${{}} | {{Metric}} |
| **Q4** | {{Scale winners}} | {{ST2 planning}} | {{WO2 planning}} | {{Scale results}} | ${{}} | {{Metric}} |

**Contingency**: If {{threat}} materializes (e.g., competitor enters), shift focus to {{ST strategy}} and deprioritize {{SO strategy}}.

---

## Resource Allocation & Trade-offs

**Allocation**:
- {{Team size}}: {{ % to SO}}, {{ % to ST}}, {{ % to WO}}, {{ % to WT}}
- **Budget**: ${{ total}}, allocated: {{ % SO}}, {{ % ST}}, {{ % WO}}, {{ % WT}}

**Trade-offs & Constraints**:
1. **Opportunity Cost**: We're betting on {{SO priority}}. This means we're NOT pursuing {{rejected opportunity}} even though {{reasoning}}. Revisit by {{date}} if conditions change.
2. **Weakness Acceptance**: We're not fixing {{weakness}} because {{reasoning: too costly, not critical path}}. Risk: {{threat}} could exploit this. Mitigation: {{}}
3. **Competitive**: If {{competitor}} launches {{move}}, we'll shift to {{contingency strategy}} and reprioritize.

---

## Success Metrics & Monitoring

**Leading Indicators** (measure monthly):
- {{Strategic initiative 1}}: {{Metric}} (Target: {{value}}, Current: {{value}})
- {{Initiative 2}}: {{Metric}} (Target: {{value}}, Current: {{value}})

**Lagging Indicators** (measure quarterly):
- {{Revenue growth rate}} (Target: {{}}% MoM, Current: {{}}%)
- {{Market share}} in {{segment}} (Target: {{}}%, Current: {{}}%)
- {{Customer retention}} (Target: {{}}%, Current: {{}}%)
- {{Competitive positioning}} (vs. {{competitor}}: {{position}})

**Decision Triggers** (When to pivot strategy):
- If {{threat metric}} exceeds {{threshold}}, execute {{contingency}}.
- If {{SO initiative}} misses {{metric}} by {{}}%, reduce investment and shift resources to {{alternative}}.
- If {{WO capability}} reaches {{milestone}}, launch {{next phase}}.

---

## Appendix: Detailed Evidence

### Strength Validation
- {{Strength 1}}: {{Supporting data—customer testimonials, NPS scores, benchmark comparison}}
- {{Strength 2}}: {{}}

### Weakness Impact Assessment
- {{Weakness 1}}: {{Evidence of gap—customer complaints, lost deals, market research}}
- {{Weakness 2}}: {{}}

### Opportunity Market Sizing
- {{Opportunity 1}}: {{TAM/SAM/SOM, growth rate, customer research}}
- {{Opportunity 2}}: {{}}

### Threat Probability & Impact
- {{Threat 1}}: {{Competitor funding, historical precedent, customer feedback}}
- {{Threat 2}}: {{}}
```

## Quality Gates
- [ ] Each Strength has defensibility assessment (can competitor replicate in 12 months?) and evidence
- [ ] Each Weakness has time-to-fix and impact assessment (what happens if not fixed?)
- [ ] Opportunities are sized with TAM/SAM, time window, and required investment
- [ ] Threats include probability (high/med/low) and impact on revenue/operations
- [ ] 4 strategy categories (SO/ST/WO/WT) have specific, measurable initiatives, not generic advice
- [ ] 12-month roadmap sequences strategies with clear prioritization (kill-or-be-killed vs. nice-to-have)
- [ ] Strategic implications acknowledge trade-offs and constraints (what we're NOT doing and why)
- [ ] Success metrics are leading (monthly) and lagging (quarterly) with decision triggers

## Examples

### Good Output (excerpt)
```
## STRENGTHS
### Product & Technology
- **Strength**: NPS of 58 (benchmark: 45 for SaaS) | Evidence: Customer survey Q4 2024, 50+ responses | Defensibility: 18 months (competitor can copy features but not loyalty) | Duration: 3+ years if we maintain engagement

### Market & Distribution
- **Strength**: 12 customers, 3 are Fortune 500, willing to be references | Evidence: Customer list, NPS by account | Defensibility: High (switching costs, integrated workflows) | Duration: 5+ years if we maintain support

## OPPORTUNITIES
- **Opportunity**: Vertical SaaS market growing 28% CAGR (vs. horizontal 15%) | Market size: $18B SAM in our segment | Timeline: 24-month window (before competitors saturate) | Required investment: Vertical-specific features ($500K), vertical GTM hire ($300K/year)

## SO STRATEGIES
**Strategy**: Launch vertical variant for {{specific industry}} within 6 months
- Strengths Leveraged: High NPS (enables word-of-mouth), Fortune 500 customers (references for enterprise)
- Opportunity: Vertical market growing 28% CAGR, our generic product has 50% lower ACV in this segment
- Initiative: Hire product manager (vertical expertise), build 4 vertical features, land 2 customers in pilot
- Timeline: Q2 launch
- Investment: $150K product + $200K sales + $100K marketing = $450K
- Expected Outcome: $200K ARR in vertical by Q4 (2-3 customers × $75K ACV)
- Success Metrics: NPS remains > 50, churn in vertical < 5%, ACV grows to $75K
- Priority: Kill-or-be-killed (enables 3x revenue growth trajectory)
```

### Bad Output (what to avoid)
```
## STRENGTHS
- Good product
- Strong team
- Growing market

## OPPORTUNITIES
- Enter new markets
- Build more features
- Grow sales

(Why this fails: No evidence, no defensibility assessment, no quantification, no connection to business impact. Doesn't inform strategy.)
```

## Common Mistakes

1. **Listing Strengths That Are Industry Table Stakes**: "We have a mobile app" or "We use AWS." These aren't strengths—they're baseline requirements. Real strengths are comparative. Ask: "Does this advantage last 10 years? Would a competitor want to copy it?" If no, it's not a strength. Focus on: defensible competitive advantages, unique data, network effects, regulatory moats.

2. **Vague WO Strategies Without Capability Roadmap**: "We'll fix our sales weakness and pursue enterprise." But fixing sales takes 6-12 months (hiring, ramp, pipeline building). If you lack enterprise sales expertise, this is a 1-2 year transformation. Be honest about timeline and investment. "Q1-Q2: Hire VP Sales (enterprise background, $300K). Q2-Q3: Build enterprise sales team (2 AEs, $600K). Q4: Begin enterprise pilots. Q1 2025: Land first enterprise customer. By Q3 2025, enterprise is 20% of revenue." This is credible and sequenced.

3. **Ignoring Trade-offs Between Strategies**: You identify SO (pursue SMB) and ST (build enterprise moat) strategies, but your team is small. You can't do both simultaneously. Which takes priority? Be explicit: "We're pursuing SMB (SO) because it scales faster and plays to our strength (high NPS, ease-of-use). We're deferring enterprise (ST) until Q3 when we hire VP Sales. This risks that competitor enters enterprise segment first, but we've chosen market share (SMB) over defensibility (enterprise moat)." This clarity enables team alignment.

4. **Confusing Threats with Weaknesses**: "Our threat is we don't have a sales team." That's a weakness. Threats are external (competitor with sales team entering market). Correct: "Threat: Competitor with $50M funding and enterprise sales team is entering our SMB segment. Our weakness: We have 1 AE. Our response: Invest in SMB GTM channels that don't require enterprise sales (self-serve, product-led growth, partnerships). This plays to our strength (product quality) and sidesteps the threat."

5. **No Probability or Severity Assessment on Threats**: "Threat: Cloud migration." Okay, but how likely? If 10% of customers migrate annually, that's a slow burn (addressable). If 50% are considering migration, it's existential. Add probability and impact: "Threat: Competitor launches at 50% lower price. Probability: 70% (well-funded, market shift). Impact: 25-40% customer churn if we don't respond. Mitigation: Bundle features competitors can't match, focus on retention (NPS investment). Timeline: Implement within 90 days."

## Anti-Patterns

1. **The "Everything is a Strength" SWOT**: You list generic items (team is hardworking, product is useful, market is growing). None of these are distinctive. Strengths are comparative. Instead: "Our founder led 3 exits (comparative to first-time founders), our NPS is 65 (vs. 45 industry benchmark), our CAC is 30% lower than competitors because of SMB GTM efficiency." These are real, defensible, and backed by evidence.

2. **Strategic Initiatives Disconnected from Strengths/Weaknesses**: You list "Launch mobile app" as an SO initiative, but your mobile strength/weakness and opportunity aren't clarified. Why mobile? What opportunity does it unlock? Is mobile a strength or weakness? Be explicit: "Mobile is a weakness (customers request iPad experience, 3 lost deals). Opportunity: Mobile-native verticalslike field service are growing 35% CAGR. Initiative: Build mobile experience, target field service vertical, hire mobile engineer ($150K), launch in Q2, land 2 customers by Q4."

3. **Threat Mitigation That Ignores Root Cause**: "Threat: Customer churn is rising. Mitigation: Invest in support." Maybe churn is rising because the product lacks features, not because support is bad. Dig deeper: "Root cause analysis: 60% of churning customers cite missing integration (technical gap). 40% cite poor onboarding (operational weakness). Mitigation: (1) Build #1 integration request (12-week project), (2) Hire onboarding specialist ($80K/year) to reduce first-month churn by 50%." Now mitigation targets actual cause.

4. **No Contingency or Pivot Plan**: "If {{Threat}} happens, we'll execute {{Strategy}}." But strategies take time. Better: "If competitor launches free tier (probability 60%), we detect churn uptick > 8% (trigger). Response: Within 2 weeks, launch freemium with feature limits (low-effort). Within 6 weeks, hire growth PM to optimize conversion funnel (medium-effort). This keeps us competitive while we execute long-term differentiation (ST strategy)." This shows you've game-planned the response.

5. **Treating SWOT as a Document Instead of Living Strategy**: SWOT is created, filed, forgotten. Better: Review quarterly. "Q1: We launched SO initiative (mobile). Result: {{Metric}}. Should we continue? Threat landscape shifted: Competitor raised $50M (raised ST priority). Reallocating team from WO (sales training) to ST (build moat) starting Q2. Updated roadmap: {{}}." This keeps strategy current.

