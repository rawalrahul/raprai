---
name: pitch-deck-script-generator
description: "Generate compelling investor pitch narratives with story arc, objection preemption, funding justification, and demo talking points. Scripts follow proven frameworks (problem-solution-market-team) and anticipate investor skepticism."
category: business
difficulty: intermediate
model_boost: "Prevents weak pitches that bury the ask, lack credibility signals, or fail to address investor objections before they arise."
---

# Pitch Deck Script Generator

## Purpose
A pitch deck script is the narrative that brings slides to life. This skill generates 10-15 minute investor pitch narratives structured for maximum persuasion: opening hook, problem setup, solution narrative, market validation, business model, competitive positioning, team credibility, funding ask with allocation, and preemptive objection handling. Output is speaker notes + talking points per slide, enabling confident delivery and handling interruptions.

## When to Use
- Pitching to VCs, angels, or corporate investors
- Board presentations requiring investor alignment
- Product launches where you need to persuade a large audience
- Partnership or acquisition pitches
- **Do NOT use when**: You lack validated customer problem (conduct discovery first); you have no clear business model; your narrative contradicts slide content (revise slides first).

## Instructions

### Step 1: Build Your Opening Hook (30 seconds)
Start with a provocative observation, not your mission statement. Hook examples:
- "95% of small businesses lose 8 hours/week to payroll admin. We cut that to 15 minutes."
- "The average developer spends 2 hours debugging for every 1 hour writing code. We've cut that in half."
- "Shopify powers 4 million stores, but none of them can predict demand 6 months out. We just helped a $50M brand cut inventory costs 18%."

Avoid: "We're excited to introduce our innovative platform..." Avoid naming your company first. Lead with customer benefit. This forces you to think outcome-first, not product-first.

### Step 2: Define the Problem with Narrative Evidence
Don't list pain points. Tell a story: "I met Jane, a 20-person SaaS founder. Every month, she spends $2,000 on contractors doing manual invoice tracking. She's tried 4 tools. Each adds 45 minutes of busywork per week. She told me, 'I'd pay anything to get this back in my engineers' hands where it belongs.'"

Include: (1) specific person, (2) quantified problem (frequency × cost), (3) attempted solutions and why they fail, (4) emotional cost (stress, time lost with family, missed growth).

### Step 3: Introduce Solution Without Feature Lists
Show a demo clip (15-30 seconds max) or explain in 2-3 sentences: "We built a tool where you drop your invoice CSV and get a cleaned database in seconds, with flagged duplicates and categorization already done. 90% reduction in manual work."

Mapping to problem: "Instead of Jane spending 2 hours on this, she spends 10 minutes. That 1.75 hours × $80/hour × 4 weeks = $560/month ROI."

Emphasis: Outcome first (time saved, revenue gained), feature second. Avoid: "We use machine learning..." unless it directly explains why your solution is better than alternatives.

### Step 4: Validate Market Opportunity with Customer Proof
"We've talked to 50+ companies in this space. 45 said this is a top-3 problem. 30 agreed to pilot our beta. 18 have paid for our MVP at $200/month. Our NPS is 52." (NPS > 40 = product-market fit signal)

Or: "Forrester reports the invoice automation market is $2.8B, growing 18% CAGR. We're targeting mid-market (100-1000 employees), representing $400M SAM with 5% CAGR faster than broader market."

Avoid: "The market is huge, everyone needs this." Investors want specific data: actual pilot results, research citations, retention metrics.

### Step 5: Present Business Model with Unit Economics
"We charge $250/month per company. Average customer generates $500 MRR by month 3. Our fully-loaded CAC is $1,200 (including sales, marketing, onboarding). That's a 5-month payback period. With our current churn of 2% monthly, LTV is $30K. That's a 25x CAC multiple, which is healthy for B2B SaaS."

Include pricing rationale: "We tested pricing with 20 customers using Van Westendorp method. $250 hit the price-quality sweet spot—not too cheap (signals low quality), not too expensive (competitors charge $500, but we're 80% of their feature set with 50% better UX)."

### Step 6: Quantify Competitive Advantage (Not Parity)
Don't say "We're like Zapier but for invoices." Investors yawn. Instead: "The 3 competitors in this space focus on enterprises with armies of support staff. We're designed for lean teams—the average setup takes 30 minutes vs. their 4 weeks. We own the SMB segment where our unit economics are 3x better than their models can support."

Or: "We have exclusive data partnerships with 5 invoice vendors, giving us 2-year lead time on feature parity. Competitors have to build integrations from scratch; we have them pre-built."

### Step 7: Establish Team Credibility
"I've built 2 prior companies, one acquired by Slack for $30M. My CTO led infrastructure at Stripe for 5 years and shipped 3 major systems serving 2M+ merchants. My VP Sales closed $50M in ACV at Zendesk. We're not betting on unproven people—we're all-in because we know how to execute this playbook."

Avoid: "I have an MBA and 10 years experience." Instead: "I've personally sold $8M to Fortune 500 companies, which is exactly our beachhead market."

### Step 8: Justify Funding Ask with Allocation
"We're raising $2M to reach $2M ARR in 18 months. Here's how: $1M goes to hiring 3 engineers to ship mobile app and 2 integrations our customers request. $600K goes to sales: 2 AEs + 1 SDR to expand SMB segment. $300K to marketing ops to measure CAC and optimize. $100K buffer for legal, accounting, ops."

Show how this allocation changes trajectory. "With this team, we model $3M churn and $7M new ACV by month 18. Without it, we plateau at $600K ARR and likely require Series B in 2 years at a down round."

### Step 9: Preempt Objections Before They're Asked
"I know what you're thinking: 'Aren't the incumbents, like Intacct, going to copy you?' Two reasons they won't: (1) Their economic model is built on 18-month sales cycles and $50K minimums. SMB segment is 30% margins for them—not strategic. (2) Their product debt is 15 years of enterprise cruft. Redesigning for ease-of-use would cannibalize their existing base. We've seen this pattern before—Slack vs. Hipchat, Notion vs. Confluence."

Or: "You might worry we haven't solved churn. Honest: enterprise SaaS churn is 2-5%, we're at 8% because we're early. But our monthly ACV is growing 15%, so even with churn, we're profitable on contribution margin today."

### Step 10: Close with Clear Call-to-Action
"We're looking for a lead investor who brings capital plus SMB channel insights. We're closing by April 1st and currently hold commitments from $1.2M. Would you like to do a deeper dive on unit economics or see a product demo?"

## Output Template

```markdown
# Pitch Deck Script: {{Company Name}} — {{Subtitle: "Your Tagline"}}
**Audience**: {{VC/Angel/Board}}
**Duration**: {{10-15 minutes}}
**Goal**: {{Secure ${{}} commitment / Board approval for {{}} / Partnership with {{}}}}

---

## SLIDE 1: Opening Hook (0:00-0:30)
**Slide Content**: {{Hook statement + impactful visual}}

**Script**:
"{{Opening hook: specific observation + quantified benefit}}"

**Talking Points**:
- {{Why this problem matters now (market trend)}}
- {{Your unique angle on the problem}}

---

## SLIDE 2: The Problem (0:30-1:30)
**Slide Content**: {{Customer story OR pain point infographic}}

**Script**:
"I met {{Customer name}}, {{title}} at {{company size}}. {{Specific situation}}. They told me, '{{Customer quote about the problem}}'."

**Quantified Pain**:
- {{Frequency}}: "This happens {{daily/weekly/per project}}"
- {{Cost}}: "It costs {{$amount}} per {{time period}}"
- {{Opportunity Cost}}: "{{Team spends X hours}} that could go to {{growth activity}}"

**Talking Points**:
- {{Why existing solutions fail}}
- {{Why this is a top-3 problem for the segment}}

---

## SLIDE 3: The Market Opportunity (1:30-2:30)
**Slide Content**: {{TAM/SAM/SOM table OR market size chart}}

**Script**:
"TAM is {{$amount}} ({{sourced from Gartner/IDC/etc.}}). We're going after SAM of {{$amount}}, which is {{market segment}}, where we have unique advantages. Year 1 SOM is {{$amount}}, achievable with {{specific go-to-market approach}}."

**Key Metrics**:
- **TAM**: ${{}} — {{calculation}}
- **SAM**: ${{}} — {{your serviceable segment}}
- **SOM Year 1**: ${{}} — {{% market share achievable}}

**Talking Points**:
- {{Why this segment is growing faster than broader market}}
- {{Why you own this segment better than competitors}}

---

## SLIDE 4-5: The Solution (2:30-4:00)
**Slide Content**: {{Product demo video (30sec) OR key feature screenshots}}

**Script**:
"Here's what we've built. {{Scenario}}: You have {{Problem scenario}}. With our product, {{Solution flow}}. {{Outcome in seconds/minutes}}."

**Mapping Solution to Problem**:
- {{Problem A}} → {{Our Solution}} → {{Quantified Outcome (time saved / revenue gained)}}
- {{Problem B}} → {{Our Solution}} → {{Outcome}}

**Talking Points**:
- {{Why this approach is different from incumbents}}
- {{Key design principle (ease-of-use, speed, integration, etc.)}}
- **Demo Tips**: If showing live demo, have backup screenshots. Narrate the user journey, not features. Show the before/after (manual process vs. automated).

---

## SLIDE 6: Traction & Validation (4:00-5:30)
**Slide Content**: {{Customer logos OR metrics dashboard OR customer quote testimonials}}

**Script**:
"We've {{validated with 50 pilot customers}}. {{Specific customer quote}}. Our metrics: {{NPS = X}}, {{Retention = Y}}, {{Time-to-value = Z}}."

**Key Traction Signals**:
- **Customers**: {{# paying}} ({{$}} MRR), {{# pilots}} (in progress)
- **NPS**: {{Score}} ({{comparison to industry benchmark}})
- **Churn**: {{Monthly %}} ({{trend: improving/stable}})
- **Time-to-Value**: {{# of days}} to first ROI
- **Growth Rate**: {{MoM %}} growth ({{traction]})

**Talking Points**:
- {{Biggest win to date (revenue, usage, customer size)}}
- {{Why traction validates the problem (not just product interest)}}

---

## SLIDE 7: Business Model & Unit Economics (5:30-7:00)
**Slide Content**: {{Pricing table OR unit economics chart}}

**Script**:
"We charge {{pricing model}}. Our unit economics are healthy: CAC of ${{}} recovers in {{#}} months, yielding an LTV of ${{}} for a {{#}}x multiple. We're already {{gross margin %}} on contribution margin."

**Unit Economics Breakdown**:
- **Pricing**: {{Model}} @ {{price range}}
- **CAC**: ${{}} ({{breakdown: Sales {{%}}, Marketing {{%}}, Onboarding {{%}}}}
- **CAC Payback**: {{# of months}}
- **LTV**: ${{}} (assuming {{churn %}})
- **LTV:CAC**: {{#}}x ({{healthy = 3-4x+}})
- **Gross Margin**: {{%}}
- **Contribution Margin**: {{%}} ({{showing path to unit economics profitability}})

**Talking Points**:
- {{Why our CAC is lower than incumbents (self-serve vs. enterprise sales)}}
- {{How you'll improve LTV (feature adoption, upsell, reducing churn)}}

---

## SLIDE 8: Competition & Differentiation (7:00-8:30)
**Slide Content**: {{2x2 competitive matrix (Price vs. Feature, or Speed vs. Depth)}}

**Script**:
"We have 3 main competitors: {{Competitor A}}, {{Competitor B}}, {{Competitor C}}. Here's how we differ: {{Competitor A}} focuses on {{segment}}, which means {{product trade-off}}. We own {{our segment}} by being {{unique advantage}}. They can't copy us because {{defensibility reason}}."

**Competitive Positioning**:
| Competitor | Market Focus | Pricing | Key Weakness |
|---|---|---|---|
| {{Incumbent}} | {{}} | {{}} | {{}} |
| {{Incumbent}} | {{}} | {{}} | {{}} |
| **Us** | **{{Our focus}}** | **{{Our price}}** | **{{Our strength}}** |

**Talking Points**:
- {{Why you aren't trying to out-feature competitors}}
- {{Your moat (data, network effects, switching costs, regulatory, distribution)}}

---

## SLIDE 9: Team (8:30-9:30)
**Slide Content**: {{Founder bios OR team expertise matrix}}

**Script**:
"My background: {{Founder 1 — relevant prior success}}. My CTO {{Founder 2 — technical credibility}}. VP Sales {{Founder 3 — sales track record}}. Together, we've {{combined achievement}}."

**Team Credibility**:
- **{{Founder 1}} (CEO)**: {{Prior exit}}, {{relevant expertise}}, {{customer relationships}}
- **{{Founder 2}} ({{Title}})**: {{Technical depth or domain experience}}, {{system shipped at scale}}, {{team size led}}
- **{{Founder 3}} ({{Title}})**: {{Revenue generation track record}}, {{customer segment familiarity}}

**Talking Points**:
- {{Why THIS team can execute (not generic startup enthusiasm)}}
- {{What's the gap that a new hire would fill (be honest)}}

---

## SLIDE 10: Funding Ask & Allocation (9:30-11:00)
**Slide Content**: {{Funding breakdown chart (pie/waterfall)}}

**Script**:
"We're raising ${{}} to hit ${{}} ARR in {{# of months}}. Here's the allocation: {{Investment breakdown}}. With this capital, we'll {{achieve milestone}}, which positions us for Series B at {{target valuation}}."

**Funding Allocation**:
- **Team ({{%}})**: {{#}} engineers, {{#}} AEs, {{#}} marketing = ${{}}
- **Product ({{%}})**: Mobile app, integrations, infrastructure = ${{}}
- **Go-to-Market ({{%}})**: Sales, marketing, partnerships = ${{}}
- **Operations ({{%}})**: Legal, accounting, facilities = ${{}}

**Milestones This Funding Unlocks**:
- {{Month 3}}: {{Product milestone}} (enabling {{customer segment}} expansion)
- {{Month 6}}: {{Revenue target}} ARR (validating {{market assumption}})
- {{Month 12}}: {{Team size}} (enabling {{scale achievement}})
- {{Month 18}}: {{Series B readiness metric}}

**Talking Points**:
- {{How much of the round is allocated (committed)}}
- {{Why this amount is sufficient (not more, not less)}}

---

## SLIDE 11: Preemptive Objections & Handling (11:00-13:00)
**Objection 1**: "Aren't the incumbents going to copy you?"

**Your Response**: "{{Specific reason they can't copy you without harming their existing business}} — we've seen this with {{analogy: Slack vs Hipchat, Notion vs Confluence}}. Their incentives are misaligned."

---

**Objection 2**: "Your churn is 8%, but SaaS averages 2-5%?"

**Your Response**: "You're right on benchmark. Our churn is elevated because we're pre-product-market fit—{{specific reason: low NPS, feature gaps, target segment immaturity}}. We've modeled the path to {{target churn %}} by {{tactic}}. {{Industry example}} followed the same trajectory."

---

**Objection 3**: "How will you compete on price against {{Incumbent}} who has 1M customers?"

**Your Response**: "We're not trying to out-price them. We're out-focusing them. They chase everyone; we own {{specific segment}} exclusively. Their LTV isn't compatible with SMB pricing—they need $50K ACV minimum. We win with $200/month × volume. Different markets, not a race."

---

**Objection 4**: "What if {{Market shift}} happens and your assumption is wrong?"

**Your Response**: "We've already stress-tested this. If {{market shift}}, we pivot to {{adjacent market}}. {{Example in our industry}} pivoted when {{market changed]]; they landed on {{larger TAM}]. We have {{ ## }} months of runway to test and iterate."

---

## SLIDE 12: The Ask & Next Steps (13:00-15:00)
**Slide Content**: {{Your lead investor position OR partnership offer}}

**Script**:
"We're looking for a {{lead investor who brings {{expertise: SMB channels / enterprise contacts / etc.}}}}. We're closing {{date}} and currently hold {{$X}} in commitments. We'd love to find the right partner to accelerate this. What questions do you have?"

**Talking Points**:
- {{Why their specific expertise or network adds value (not just money)}}
- {{Timeline for decision (without pressure)}}
- {{Next step if they're interested (deeper dive, product demo, reference calls)}}

---

## Q&A Backup Slides

### Backup Slide A: Customer Testimonials
"{{Customer quote: specific result (metric + emotional resonance)}}
— {{Customer name, Title, Company}}"

### Backup Slide B: Detailed Unit Economics Model
[Show your 3-year financial model]

### Backup Slide C: Market Research & Validation
[Citations from Forrester, Gartner, or your own research]

### Backup Slide D: Product Roadmap
[6-month priorities aligned to revenue/retention targets]

### Backup Slide E: Risk Mitigation Plan
[Top 3 risks + mitigation strategy + detection triggers]

---

## Delivery Tips
- **Rehearse**: Practice this script 10+ times. You should know it without reading.
- **Pace**: Spend more time on slides that investors care most about (traction, unit economics, team).
- **Flexibility**: Have answer ready if interrupted. Don't plow through; engage if investor jumps ahead.
- **Objection Handling**: Listen fully before responding. Start with "Great question." Buy 3 seconds to think.
- **Demo Contingency**: If live demo fails, have pre-recorded video and screenshots. Keep moving.
- **Time Discipline**: Use a silent timer. Leave 5 minutes for questions.
```

## Quality Gates
- [ ] Opening hook is story-based, not mission-based; positions customer benefit first
- [ ] Problem statement includes quantified cost (dollars or hours), customer quote, and failed alternatives
- [ ] Traction section shows paying customers, NPS, and retention—not just pilot count
- [ ] Unit economics show CAC, LTV, payback period, and gross margin with realistic assumptions
- [ ] Competitive section positions your segment advantage, not feature parity
- [ ] Team section establishes domain credibility (prior exits, scale, customer relationships) not just job titles
- [ ] Funding ask includes specific allocation (% to team, product, marketing) and achieves clear milestones
- [ ] 4-5 preemptive objections addressed with specific rebuttals, not defensive language
- [ ] Script is 10-15 minutes when read at normal pace (test with timer)

## Examples

### Good Output (excerpt)
```
SLIDE 2: The Problem (Problem Story)

Script:
"I met Sarah, a controller at Acme Manufacturing, $40M revenue, 120 employees. Every month-end, she manually reconciles 2,000 invoices across 4 accounting systems. It takes her team 60 hours. In her words: 'We're drowning. I have a finance degree, and I'm doing data entry. We lose sight of cash position until week 2 of the next month, which costs us time on collections.' They've tried 3 accounting platforms in the last 5 years. Each promised automation but added complexity."

Quantified Pain:
- Frequency: 1x monthly, 60 hours effort
- Cost: $4,800/month in team labor (60 hrs × $80/hr burden)
- Opportunity Cost: Delayed cash position visibility = $50K in float costs annually

Objection to Address Early:
You might ask: "Why doesn't accounting software solve this?" Good question. Most platforms require custom mapping for every new vendor, which resets the clock every time a new supplier joins. Sarah's team spends more time maintaining integrations than doing actual reconciliation."
```

### Bad Output (what to avoid)
```
SLIDE 2: The Problem

Script:
"Invoices are complex. Businesses struggle with manual processes. Our software makes it easier. We've identified a large market opportunity."

Talking Points:
- Problems with manual invoicing
- Customers want automation
- Growing demand for solutions

(Why this fails: No customer story, no quantified pain, no emotional stakes, no proof of attempts to solve the problem. Investors don't care about "businesses struggle"—they care about specific customers with specific dollar losses.)
```

## Common Mistakes

1. **Spending Too Much Time on Product, Too Little on Traction**: You show a 3-minute demo of feature A, B, C, but only mention you have 5 customers. Investors care more about whether the problem is real (evidenced by paying customers, NPS, retention) than your feature list. Reverse allocation: 5-10% on demo, 25% on traction.

2. **Weak Team Credibility Statements**: "I have 8 years in tech and a Stanford degree." Investors don't care about tenure or school; they care about: "I closed $50M in enterprise deals" or "I shipped PayPal's fraud detection system to 1M merchants." Use specific wins that prove you can execute this playbook.

3. **Confusing Objection Deflection with Objection Addressing**: Objection: "Won't incumbents copy you?" Bad answer: "We'll move fast. We're agile." Good answer: "Intacct's unit economics require $50K ACV minimums. If they drop to SMB pricing, they cut revenue 80%. We've seen this with Slack/HipChat; the incumbent can't pivot without cannibalizing their core." This shows you've thought about competitive incentives, not just hoped to be faster.

4. **Funding Ask Without Connection to Metrics**: "We're raising $2M" but no explanation of how this capital moves the needle. After funding: What's your new MRR growth rate? New team size? New customer segment? "This $2M funds 5 engineers and 2 AEs, moving us from $300K to $2M ARR in 18 months" is compelling because it's testable.

5. **Script Too Scripted**: Reading word-for-word sounds robotic and breaks rapport. Memorize structure and key numbers, but deliver conversationally. Investor interrupts with question? You shouldn't have to flip through slides to recover—you own the narrative.

## Anti-Patterns

1. **The Feature Dump**: "We have integration with 50+ tools, advanced reporting, custom workflows, role-based access, API v2, webhooks..." Investors' eyes glaze over. Features are table stakes. Lead with outcomes: "Our customers reduce manual work 80%. The reason: purpose-built UX for their workflow, not generic software. Most tools are 80% features they don't use; we're 80% things they actually need."

2. **Competitive Denial**: "We have no competitors. The market has never seen a solution like ours." Red flag. There's ALWAYS a competitor (even if it's a manual process or Zapier + Excel). Honest positioning: "Our 3 competitors are {{Incumbent A}}, {{B}}, and {{C}}. They own the enterprise segment. We're going after SMB, which is {{# of companies}} and {{growing % CAGR}} faster." This shows you've done homework and own a differentiated segment.

3. **The Infinitely Large TAM**: "We're targeting global businesses of any size." Vague and unconvincing. "We're targeting North American SMBs (100-500 employees) in {{specific industry}} on {{product type}}. That's {{specific # of companies}}, growing {{% CAGR}}." This forces you to be specific about your actual beachhead and it's more credible.

4. **Assuming Investor Context**: "As you know, invoice automation is a $2.8B market." They don't know, and if they do, citing it gives no differentiation. Skip and jump to your angle: "Gartner values the invoice automation market at $2.8B. We've identified that {{% goes to SMBs}}, a segment growing {{% faster}} than enterprises. That's our TAM: {{$amount}}."

5. **No Credible Metric for Product-Market Fit**: "We're gaining traction" with no specifics. Investors want proof: NPS (>40), retention (>80% annual), or willingness-to-pay (customer acquisition cost). If you lack these, be honest: "We're pre-product-market fit. We're measuring {{these metrics}} to validate fit by {{date}}. Current status: {{}}."

