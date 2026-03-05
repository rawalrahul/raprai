---
name: user-persona-generator
description: "Generate data-driven personas with demographics, psychographics, jobs-to-be-done (JTBD), pain points, buying triggers, objections, and success metrics. Informs product, marketing, and sales strategy."
category: business
difficulty: intermediate
model_boost: "Prevents generic personas based on assumptions; produces instead specific, research-backed personas tied to buying behavior and product decisions."
---

# User Persona Generator

## Purpose
A user persona is a semi-fictional archetype of your target customer, grounded in research. This skill generates detailed personas including: demographics, psychographics (values, motivations), job-to-be-done (the real task they're trying to accomplish), pain points, buying triggers, objections they'll raise, decision-making process, and success metrics. Output informs product roadmap prioritization, marketing messaging, and sales positioning.

## When to Use
- Launching a product without clear customer understanding
- Pivoting target customer segment
- Cross-functional alignment (product, sales, marketing need shared understanding of customer)
- Product roadmap prioritization (which features matter to which personas?)
- Go-to-market strategy design (messaging, pricing, channels vary by persona)
- **Do NOT use when**: You have 1 customer segment (simple product); personas are theoretical (conduct customer research first); personas haven't changed in 2+ years (refresh with current data).

## Instructions

### Step 1: Identify Primary & Secondary Personas
You likely have 2-3 primary personas (each worth distinct product, marketing, or sales motion) and 1-2 secondary personas (smaller segment or gating user).

**Example: B2B Invoice Automation Tool**
- **Primary 1: Finance Manager (Sarah)** — runs the invoice process, feels the pain daily, has budget authority
- **Primary 2: CFO (David)** — needs reporting/cash visibility, approves purchase, cares about ROI
- **Secondary: Accounts Payable Clerk (Maria)** — executes invoicing, uses product daily, but lacks budget authority

**Rule**: Only 2-3 primary personas. More dilutes focus.

### Step 2: Conduct Customer Research
Personas are only valid if grounded in data. Conduct:
- **Customer interviews** (10-15 per persona, open-ended, 30-45 min)
- **Surveys** (100+ respondents, validate interview findings)
- **Product usage data** (if you have existing customers: who uses most, how long they stay, which features drive engagement)
- **Sales data** (who buys, what's the buying process, who has final say?)

**Sample Interview Questions**:
- "Walk me through how you currently {{handle the problem}}. What tools do you use?"
- "What's the biggest frustration with {{current process}}? How often does it happen?"
- "How much time/money does {{problem}} cost you annually?"
- "What would success look like for you?"
- "Who else needs to approve the purchase decision?"
- "What could prevent you from buying a solution like this?"

### Step 3: Develop Demographics
Capture identifying characteristics:
- **Title & Role**: Exact job title (CFO, Controller, Finance Manager, AP Clerk)
- **Company Size**: How many employees, annual revenue (affects budget, buying process)
- **Industry/Vertical**: Manufacturing, tech, retail, professional services? (problems vary by industry)
- **Tenure**: How long in role? (new = more willing to try new solutions; established = risk-averse)
- **Experience**: Hands-on (uses product) vs. decision-maker (approves budget)?

**Example**:
- **Title**: Finance Manager
- **Company Size**: 50-200 employees, $5-25M revenue
- **Industry**: Professional services (law firms, consulting)
- **Tenure**: 3-5 years in role
- **Experience**: Hands-on, manages 2 APs, owns process

### Step 4: Identify Psychographics & Motivations
Psychographics are values, aspirations, fears, and personality traits.

**Motivations** (why they'd buy):
- Wants to reduce manual work (free time for strategic tasks)
- Needs cash position visibility (faster decision-making)
- Worried about errors/compliance (controls audit risk)

**Fears** (objections they'll raise):
- "It won't integrate with our existing system" (integration risk)
- "Implementation will take months" (disruption risk)
- "Support will be poor; we'll be stuck" (vendor lock-in risk)

**Values**:
- Efficiency (wants fast, reliable processes)
- Control (wants visibility and compliance)
- Risk mitigation (prefers proven solutions over experimental)

**Personality**:
- Analytical (data-driven)
- Conservative (risk-averse; existing tools feel safer)
- Pragmatic (cares about ROI, not features for features' sake)

### Step 5: Map Jobs-to-Be-Done (JTBD)
JTBD is the real problem the customer is solving. Not product features, but the outcome they want.

**Example**:
- **Surface Job** (feature-level): "Process invoices"
- **Real Job** (outcome-level): "Get accurate, timely cash position visibility to make informed decisions"
- **Emotional Job**: "Feel confident we're compliant and not at risk"

Understanding JTBD prevents building features nobody uses. If JTBD is "cash visibility," then invoice automation (feature) is valuable only if it enables faster visibility. If JTBD is "reduce manual work," then automation is the whole point (user would care less about visibility).

### Step 6: Quantify Pain Points
Paint problems are more compelling than theoretical ones. Quantify impact:

**Pain Point 1: Manual Invoice Processing**
- **Frequency**: 400 invoices/month
- **Time per invoice**: 5 minutes (manual data entry, approval coordination)
- **Total monthly time**: 33 hours (400 × 5 min)
- **Cost**: $3,300/month ($100/hour burden rate × 33 hours)
- **Impact on business**: Cash position visibility delayed 21 days (payment timing poor, float costs $50K annually)

### Step 7: Identify Buying Triggers & Decision Process
When and how does this persona buy?

**Buying Triggers**:
- Invoice volume growing (manual process breaks)
- New accountant hired (onboarding delays; need better process)
- Compliance audit (need controls/documentation)
- Competitor has the solution (FOMO)

**Decision Process** (typical for Finance Manager):
1. **Recognition**: "We need a better way" (trigger hits)
2. **Research**: Search online, ask peers (3 weeks)
3. **Shortlist**: 3-5 solutions evaluated (2 weeks)
4. **Pilot**: Trial with real data (2-4 weeks)
5. **Approval**: CFO approves purchase (1-2 weeks)
6. **Implementation**: Onboarding (2-4 weeks)

**Total Sales Cycle**: 8-16 weeks. Longer if CFO is skeptical or IT/security have requirements.

### Step 8: Document Objections & Rebuttals
Anticipate objections this persona will raise:

**Objection 1**: "We've tried 3 solutions already; they all failed."
- **Root Cause**: Previous solutions had poor onboarding or didn't integrate well.
- **Rebuttal**: "We've learned from this. Our {{time-to-value}} is 3 days (vs. their 4 weeks). We have {{integrations}} pre-built. Here's a reference from {{similar company}} who had same experience."

**Objection 2**: "How much will implementation cost?"
- **Root Cause**: Fear of hidden costs and disruption.
- **Rebuttal**: "{{Transparent pricing: $X setup fee}}. We handle migration. {{Average implementation: {{#}} weeks}}. You're {{on your own for training}} or {{we offer {{#}} days of support}}."

**Objection 3**: "We're locked into {{existing vendor}}'s contract for {{# years}}."
- **Root Cause**: Vendor lock-in, sunk costs, switching costs.
- **Rebuttal**: "You can keep using {{vendor}} for X. Our tool works alongside it. No rip-and-replace needed. {{Early adopters}}did this and saw {{benefit}} within {{timeframe}}."

### Step 9: Define Success Metrics for This Persona
How will this persona measure whether your solution was worth it?

**Success Metrics**:
- **Time saved**: Reduce invoice processing from 33 hours to 5 hours/month (85% reduction)
- **Accuracy**: Reduce manual data entry errors from {{current %}} to {{target %}} (audit-ready)
- **Cash visibility**: Real-time visibility instead of 21-day delay (enables better cash management)
- **Cost savings**: {{$3,300/month}} freed up for other projects

These metrics align to JTBD (cash visibility, reduced manual work) and should be measurable post-implementation. Use them in sales conversations: "Within {{timeframe}}, you'll have {{achieved these metrics}}."

## Output Template

```markdown
# User Personas: {{Product/Company}}
**Research Date**: {{Date}}
**Research Methods**: {{Interviews (n={{#}})}}, {{Surveys (n={{#}})}}, {{Usage Data}}, {{Sales Data}}
**Last Updated**: {{Date}}
**Next Review**: {{Date}} (annual refresh)

---

## PERSONAS OVERVIEW

**Primary Personas** (distinct product/sales/marketing motion):
1. {{Persona Name 1}} ({{%}} of target market)
2. {{Persona Name 2}} ({{%}} of target market)

**Secondary Personas** (gating user or smaller segment):
1. {{Persona Name 3}} ({{%}} of target market)

---

## PRIMARY PERSONA 1: {{Name}}

### Overview
{{1-2 sentence summary of who this person is}}
- **Segment**: {{Primary buyer / influencer / end user}}
- **Market Share**: {{%}} of target customers
- **Buying Power**: {{High / Medium / Low}} (budget authority {{Yes / No}})

### Demographics

| Attribute | Value | Notes |
|---|---|---|
| **Job Title** | {{Title}} | {{Context: part of {{department}}, reports to {{}} }} |
| **Company Size** | {{# employees}}, {{$}} revenue | {{Industry}} |
| **Industry** | {{Verticals}} | {{Why this vertical? (e.g., manual processes)}} |
| **Tenure in Role** | {{# years}} | {{Risk profile: tenured = risk-averse}} |
| **Direct Reports** | {{#}} | {{Team size/dynamics}} |
| **Education** | {{Degree / Background}} | {{Accounting, Finance, Tech, Business?}} |
| **Geographic** | {{Region}} | {{Location matters for support/sales cycle?}} |
| **Age/Experience** | {{Range}} | {{Experience level}} |

### Psychographics & Personality

**Core Values**:
- {{Value 1}}: {{Why this matters (e.g., "Efficiency because their time is stretched thin")}}
- {{Value 2}}: {{}}
- {{Value 3}}: {{}}

**Motivations**:
- {{Motivation 1}} (what drives them): {{Why important (e.g., "wants to free time for strategic planning")}}
- {{Motivation 2}}: {{}}

**Fears & Concerns**:
- {{Fear 1}}: {{Why it matters (e.g., "risk of integration failure breaks process")}}
- {{Fear 2}}: {{}}

**Personality Traits**:
- {{Trait 1}}: {{Analytical / Risk-averse / Pragmatic?}}
- {{Trait 2}}: {{}}

**Perceived Barriers to Change**:
- {{Barrier 1}}: {{Why they resist new tools (e.g., "implementation disruption")}}
- {{Barrier 2}}: {{}}

### Jobs-to-Be-Done (JTBD)

**Primary Job**: {{The real outcome they want}} (not feature-level)
- **Example**: "Get real-time visibility into cash position so I can make better payment decisions" (not just "process invoices")
- **Functional Outcome**: {{What they want to accomplish}}
- **Emotional Outcome**: {{How they want to feel}} (e.g., "confident, in control, proactive")

**Secondary Jobs**:
1. {{Job 2}}: {{Outcome}}
2. {{Job 3}}: {{Outcome}}

**Contexts Where JTBD is Most Acute**:
- {{Situation 1}}: {{When the job is most important}} (e.g., "during month-end close, when cash is critical")
- {{Situation 2}}: {{}}

### Pain Points (Current State)

| Pain Point | Frequency | Cost / Impact | Trigger | Evidence |
|---|---|---|---|---|
| **{{Pain 1}}** | {{Frequency}} | ${{/month or hours}} | {{When it's worst}} | {{Customer quote or data}} |
| {{}}| {{}} | {{}} | {{}} | {{}} |
| {{}} | {{}} | {{}} | {{}} | {{}} |

**Example**:
| Pain Point | Frequency | Cost | Trigger | Evidence |
|---|---|---|---|---|
| Manual invoice data entry | 400 invoices/month | $3,300/month (33 hrs @ $100/hr burden) | Month-end close | "I spend 2 days just entering data. It's mindless work." |
| Cash visibility delay | 21-day lag | $50K annual float cost | Quarterly forecasting | "By the time we see actuals, we've already made payment decisions." |
| Error risk & compliance | 1-2 errors/month | $500-2K per error (rework + audit) | Audit season | "We're terrified of reconciliation errors. One bad data point breaks the whole system." |

### Buying Triggers

**What Causes Them to Seek a Solution**:
1. {{Trigger 1}}: {{Description}} (e.g., "Invoice volume growing {{%}} YoY; manual process breaking")
   - **Timing**: {{When this happens (e.g., "Q1 when volume spikes")}}
   - **Likelihood**: {{High / Medium / Low}}

2. {{Trigger 2}}: {{}}
   - **Timing**: {{}}
   - **Likelihood**: {{}}

3. {{Trigger 3}}: {{}}

### Buying Process

**How This Persona Buys** (typical decision journey):

1. **Problem Recognition** (Week 1)
   - {{They realize current process is broken}}
   - **Catalyst**: {{{{trigger]]}} (e.g., invoice processing delays impact cash forecast)
   - **Initial Search**: Google "{{search term they'd use}}", ask peers

2. **Research & Shortlisting** (Weeks 2-4)
   - Reads {{# articles}}, watches {{# demos}}, talks to {{# vendors}} (informal)
   - **Evaluation Criteria**: {{What matters most}} (speed-to-value, ease-of-use, price, support)
   - Narrows to {{# candidates}} for deeper eval

3. **Requirements & RFP** (Weeks 5-7)
   - Documents requirements (if large company; SMB may skip)
   - {{May request references, case studies, technical specs}}

4. **Pilot / Trial** (Weeks 8-12)
   - Trial period: {{14-30 days}} (test with real data)
   - **Success Criteria**: {{Persona measures whether solution meets needs}}
   - **Typical Issues**: {{Onboarding difficulty / integrations / support}}, then {{decision: buy or next option}}

5. **Approval & Budget** (Weeks 13-16)
   - {{Persona presents to {{CFO / Finance Director}}, requests budget}}
   - **Approval Criteria**: {{ROI, risk, resource impact}}
   - **Stakeholder Input**: {{IT (security, integration), Procurement (vendor assessment), Users (feedback)}}

6. **Implementation** (Weeks 17-24+)
   - Contract negotiated ({{# days}})
   - Onboarded ({{# weeks}}) and training ({{# days}})

**Total Sales Cycle**: {{# weeks}} (range {{weeks}} - {{weeks}})

**Decision Authority**:
- **Person**: {{This persona {{proposes}} / approves / executes}} purchase
- **Others Involved**: {{Who else has input (CFO, IT, Procurement)?}}
- **Veto Power**: {{Who can kill the deal?}} (usually CFO if budget large, IT if integration complex)

### Objections & Concerns

| Objection | Root Cause | Severity | Rebuttal / How to Overcome |
|---|---|---|---|
| **"We've tried this before and it failed"** | Previous vendor had poor {{onboarding / support / integrations}} | High | Share {{case study}} from {{similar company}} who had same experience, switched, succeeded. Reference call. |
| **"Will this integrate with {{their ERP}}"** | Integration failure = broken process | High | Show pre-built integration. Demo with their ERP. Offer {{# days}} technical support for integration. |
| **"Implementation will disrupt our process"** | Switching costs, training burden, risk | Medium | "No rip-and-replace. You run old and new in parallel for {{#}} weeks. {{# hours}} of training. Most teams productive on day 3." |
| **"We're locked into {{vendor}} for {{# years}}"** | Sunk cost, switching costs | Medium | "Works alongside {{vendor}}. Our tool imports {{data type}}. Early adopters used this approach, saved ${{}} despite contract lock." |
| **"It's too expensive at ${{}}."** | Price sensitivity (budget constraint or ROI unclear) | Medium | "You're spending ${{}} on manual labor now. ROI is 6 months. Reference: {{similar company}} paid for itself in month 4." |
| **"How's your support?"** | Risk: stuck if something breaks | Medium | "Dedicated support {{during hours}}, {{response time}}. {{#}}% of questions answered via self-service (dashboard, documentation)." |

### Success Metrics (How They Measure Success)

**Post-Implementation, This Persona Wants**:

| Metric | Current State | Desired State | Time to Achieve | How Measured |
|---|---|---|---|---|
| **Time Spent on Invoicing** | {{33 hours/month}} | {{5 hours/month}} | {{By month 2}} | {{Time tracking or calendar block}} |
| **Data Accuracy** | {{{{X % errors}}}} | {{<0.5% errors}} | {{By month 3}} | {{Audit reconciliation}} |
| **Cash Position Visibility** | {{21-day lag}} | {{Real-time}} | {{By month 2}} | {{Dashboard; used in weekly forecast}} |
| **Compliance Confidence** | {{"Worried; manual errors hard to track"}} | {{High (auditable trail, controls)}} | {{By month 4}} | {{Audit results}} |
| **Cost Savings** | {{$0 (no solution)}} | {{$3,300/month}} | {{By month 3}} | {{Budget reallocation to strategic work}} |

**Key Success Factor**: {{Metric persona cares most about}} (e.g., time savings)

### Messaging & Positioning (For This Persona)

**Primary Message** (lead with): "Reduce invoice processing from 33 hours to 5 hours/month, freeing your team for strategic work."

**Secondary Messages**:
- "Real-time cash visibility—not 21 days late."
- "Audit-ready controls and compliance trail."
- "Integrates with {{their ERP}}; no rip-and-replace needed."

**Avoid**: {{Messaging that doesn't resonate}} (e.g., "advanced AI" if persona cares about reliability, not novelty)

### Engagement Channels & Content Preferences

**How to Reach Them**:
- **Channels**: {{LinkedIn}} (professional content), {{industry associations}} (conferences, webinars), {{peers/references}} (word-of-mouth)
- **Content**: {{Type they consume}} (case studies, ROI calculators, product tours, webinars)
- **Timing**: {{When they're most receptive}} (after budget spike, before audit, during scaling pain)

**Content They Value**:
- {{ROI calculator or cost-benefit analysis}}
- {{Reference calls with similar companies}}
- {{Case study: company like theirs, achieved {{metric}})}}
- {{Implementation guide: {{how to migrate data from {{ERP}}}}}}

---

## PRIMARY PERSONA 2: {{Name}}
[Repeat structure above]

---

## SECONDARY PERSONA: {{Name}}
[Abbreviated version of above structure]

---

## CROSS-PERSONA INSIGHTS

### Buying Influencers & Veto Players

| Role | Persona | Authority Level | Buying Influence | Key Concern |
|---|---|---|---|---|
| **Proposer** | {{Persona 1}} | Recommends | High | Does it solve the problem? |
| **Approver** | {{Persona 2 (CFO)}} | Approves budget | Very High | Is ROI defensible? |
| **Implementer** | {{Persona 3 (AP Clerk)}} | Executes | Medium | Is onboarding easy? Will I lose my job? |
| **IT Stakeholder** | {{IT Director}} | Veto (integration) | High | Is it secure? Does it break existing systems? |

**Selling Insight**: {{You need approval from {{Persona 2}}, but {{Persona 1}} is your champion. Give {{Persona 1}} materials to present to {{Persona 2}} (ROI, references).}}

### Alignment & Conflicts

**Where Personas Align**:
- {{All care about {{accuracy, time savings, compliance}}}}

**Where Personas Conflict**:
- {{Persona 1 wants ease-of-use; Persona 2 wants lowest price}} → message differently to each
- {{Persona 3 fears job displacement; others don't}} → address separately

---

## GO-TO-MARKET RECOMMENDATIONS

### Product Roadmap Priorities (By Persona)

| Feature | Persona 1 | Persona 2 | Persona 3 | Recommendation |
|---|---|---|---|---|
| **Real-time dashboard** | High | High | - | Build ({{Persona 1 & 2 priority}}) |
| **Mobile approval** | Medium | Low | High | Build ({{Persona 3 needs}}, {{Persona 1 benefits}}) |
| **Advanced reporting** | Medium | High | - | Build ({{CFO pain}}) |
| **Workflow customization** | Low | Low | High | Defer Phase 2 ({{niche, high effort}}) |

### Sales Strategy (By Persona)

**For Persona 1 (Finance Manager)**:
- **Channel**: LinkedIn, industry events, peer referrals
- **Messaging**: "Free 10 hours/week. Redeploy team to forecasting."
- **Proof**: Reference from {{similar company}}, ROI calculator
- **Sales Approach**: Education + trial (let them feel the value)

**For Persona 2 (CFO)**:
- **Channel**: LinkedIn, board/investor networks
- **Messaging**: "6-month ROI. Scale finance team without headcount."
- **Proof**: Customer case study with metrics
- **Sales Approach**: {{Persona 1}} champion sells internally; we support with {{board-level proof}}

### Marketing Messaging (By Persona)

| Element | Persona 1 | Persona 2 | Persona 3 |
|---|---|---|---|
| **Headline** | "Cut invoice time {{%}}" | "Control costs, scale finance" | "Make approvals 10x faster" |
| **Subheading** | "From 33 hours to 5. Guaranteed." | "Real-time visibility. Audit-ready." | "Approve from anywhere." |
| **CTA** | "Start free trial" | "Request demo with CFO" | "Watch 2-min video" |

---

## PERSONA VALIDATION & REFRESH

### How Personas Were Validated
- {{Customer interviews: {{#}} from each segment}}
- {{Survey validation: {{#}} respondents, {{%}} agree with persona}}
- {{Product usage data: {{%}} of users match primary persona profile}}
- {{Sales data: {{%}} of deals come from persona 1, {{%}} from persona 2}}

### Signals That Personas Need Refresh
- {{New customer segment entering ({{%}} of revenue)}}
- {{Buying process changed (sales cycle shortened from {{weeks}} to {{weeks}})}}
- {{Key pain point solved (no longer a differentiator)}}
- {{Competitors targeting same personas with different positioning}}

### Next Persona Review
- **Date**: {{Next annual review or {{trigger}}}}
- **Action**: {{Conduct 10 interviews, refresh survey}}
- **Owner**: {{Product / Marketing}}

---

## APPENDIX

### A. Research Methodology & Data
- {{Interview guide & questions}}
- {{Survey results summary}}
- {{Raw interview notes or transcripts (confidential)}}

### B. Persona Profiles (Visual/One-Pagers)
{{Link to downloadable one-pagers for distribution to team}}

### C. Buying Process Map (Visual)
{{Timeline showing decision stages, timeline, stakeholders}}

### D. Win/Loss Data by Persona
{{Analysis of which personas buy from us vs. competitors, and why}}

```

## Quality Gates
- [ ] 2-3 primary personas identified with distinct buying processes and pain points
- [ ] Each persona grounded in research (interviews, surveys, product data, sales data)
- [ ] Demographics include title, company size, industry, tenure
- [ ] Psychographics capture values, motivations, fears
- [ ] JTBD identified (outcome, not features) for each persona
- [ ] Pain points quantified (frequency, cost, impact) with customer quotes
- [ ] Buying triggers documented with timing and likelihood
- [ ] Buying process mapped with timeline, stages, decision authority, approval flow
- [ ] Objections identified with root causes and rebuttals
- [ ] Success metrics defined and measurable post-implementation
- [ ] Go-to-market recommendations flow from persona insights (product, sales, marketing)

## Examples

### Good Output (excerpt)
```
PRIMARY PERSONA 1: Sarah, Finance Manager

Demographics:
- Title: Finance Manager (manages 2 AP clerks)
- Company: 80 employees, $8M revenue, professional services firm
- Industry: Law firm
- Tenure: 4 years in role (established, knows the pain)
- Reports to: CFO

JTBD (Primary Job):
"Get real-time cash position visibility so I can forecast accurately and recommend payment timing to CFO."
(Not just "process invoices" — the outcome is visibility and decision-support)

Pain Points:
- Manual Invoice Entry: 400 invoices/month × 5 min = 33 hours/month = $3,300 cost
- Cash Visibility Delay: 21-day lag from invoice receipt to cash impact recorded. Forecast is always wrong.
- Compliance Risk: 2-3 errors/month during month-end close. One bad entry breaks reconciliation.

Buying Process:
1. Recognition (Week 1): Invoice volume grew 25% YoY. Manual process breaking. Sarah realizes need.
2. Research (Weeks 2-4): Searches "invoice automation law firm". Shortlists {{3 tools}} based on reviews.
3. Trial (Weeks 5-8): Tests {{tool}} with 50 real invoices. Loves ease-of-use. Questions integration with QuickBooks.
4. Approval (Weeks 9-10): Sarah presents ROI to CFO: "Frees 33 hours/month ($3,300 value). ROI 6 months."
5. Implementation (Weeks 11-16): 2 weeks onboarding, training, data migration.

Objections & Rebuttals:
- "We've tried before and it failed" → "Previous tool had poor onboarding. Ours integrates QuickBooks in 2 hours (theirs took 4 weeks). Here's {{reference}} from {{law firm}} who had same issue."
- "How's support?" → "Dedicated US support, 4-hour response time. {{80%}} of issues resolved via chat."

Success Metrics:
- Time: 33 hours → 5 hours/month (by month 2)
- Accuracy: <0.5% errors (by month 3)
- Visibility: Real-time cash dashboard used in weekly forecast (by month 2)
- Cost savings: $3,300/month freed for strategic projects (immediate)

---

PERSONA 2: David, CFO

Pain Point: "I don't trust our cash position forecast. Finance Manager tells me X, but actuals are different due to timing lags. Costs us money."

JTBD: "Have accurate, real-time cash forecast so I can make smart payment/investment decisions."

Buying Influence: HIGH (approves ${{}} budget). Cares about: ROI, risk, financial impact.

Objection: "How is ROI 6 months?"
Rebuttal: "Reference from {{similar}} firm: saved $40K in late-payment fees in year 1 by getting accurate cash position 2 weeks earlier. That alone pays for tool."
```

### Bad Output (what to avoid)
```
Persona: Finance Professional

This person needs better invoice processing. They want a tool that's easy to use and has good integrations. They're busy and don't have time for complex setup.

(Why this fails: No name, no research grounding, no psychographics, no quantified pain, no buying process, no objections, generic "easy to use" doesn't inform product decisions)
```

## Common Mistakes

1. **Personas Based on Assumptions, Not Research**: You create a persona in a meeting without talking to customers. Result: product built for wrong person. Better: interview 10 customers, find patterns, then codify personas.

2. **Too Many Personas (Diluted Focus)**: 6 personas listed. Every person interprets "our customer" differently. Better: 2-3 primary personas with distinct buying processes. Secondary personas can be lighter.

3. **Persona Without JTBD**: Persona lists pain points ("invoice processing is manual") but not job ("get cash visibility to forecast accurately"). Result: product built around wrong metric. Better: Jobs-to-be-done informs all product decisions.

4. **Personas Outdated**: Created 2 years ago. Market shifted, buying process changed, new personas emerged. Still using old personas for strategy. Better: annual refresh. If {{%}} of new customers come from new persona, time to update.

5. **No Buying Process Mapped**: Persona exists, but nobody knows how long they take to decide, who approves, what they need to see. Sales team makes up own assumptions. Better: Document typical buying journey for each persona (stages, timeline, stakeholders, decision criteria).

## Anti-Patterns

1. **Persona Describing a Single Customer, Not a Segment**: "This is Janet from company X." Janet is too specific (1 data point). Better: "Finance managers at law firms, 50-100 employees, $5-15M revenue" (pattern across {{#}} customers).

2. **Feature-First Personas**: "This persona wants advanced reporting." Why? What outcome do they get? Better: "Finance Manager needs real-time cash forecast. Advanced reporting enables that."

3. **Personas Without Objections**: List of ideal traits but no mention of concerns they'll raise. Sales team surprised when prospect says "I'm worried about integration." Better: Document top {{3-5 objections}} each persona raises.

4. **Messaging Not Tailored by Persona**: Same message sent to Finance Manager and CFO. Manager cares about ease-of-use; CFO cares about ROI. Better: Different positioning for each (ease-of-use vs. cost savings).

5. **Product Roadmap Ignores Persona Priorities**: Personas say {{Feature A}} is important to persona 1, but product team prioritizes {{Feature B}} because it's technically interesting. Better: Every feature on roadmap ties to persona need.

