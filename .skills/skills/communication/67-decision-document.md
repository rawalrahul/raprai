---
name: decision-document
description: "Build transparent decision documents with options matrix, weighted pros/cons, clear recommendations, reversibility assessment, and stakeholder sign-off to accelerate complex decisions."
category: communication
difficulty: intermediate
model_boost: "Weak models present options equally without clear recommendation; miss reversibility analysis; lack stakeholder alignment"
---

# Decision Document

## Purpose
Most decisions fail not because of bad thinking, but because they're made opaquely and stakeholders aren't aligned. A decision document makes your reasoning transparent, invites scrutiny, surfaces disagreements early, and creates accountability. The best leaders use decision documents to decide faster (because analysis is rigorous), not slower. This skill creates a template that scales from tactical ("which vendor?") to strategic ("which market?") decisions.

## When to Use
- Major decisions affecting multiple teams or budgets
- Strategic decisions (market, product, organization)
- Irreversible or expensive decisions (hiring, tools, architecture)
- Decisions that will face pushback or disagreement
- Any decision where stakeholder buy-in matters
- **Do NOT use when**: The decision is tactical and only affects your team; you have full authority and urgency is critical; the decision is reversible and low-stakes

## Instructions

### Step 1: Define the Decision
Be specific. "Should we hire?" is vague. "Should we hire 2 senior engineers in Q2 at $300K fully-loaded cost?" is clear.

**Good decision statement**:
- Specific problem you're solving
- Scope (what does this affect? who?)
- Constraints (budget, timeline, non-negotiables)
- Decision deadline (when does this need to be made?)

**Example**:
"Decision: Should we build customer analytics dashboard in-house or buy a third-party solution? Scope: affects Product team's ability to understand usage patterns and Customer Success team's ability to identify at-risk customers. Budget: $50K one-time build or $15K/month license + implementation. Timeline: need solution by Q2 launch (4 months). Decision deadline: Friday so we can start procurement or dev planning."

### Step 2: Identify All Stakeholders
Who cares about this decision? Who has to live with the outcome?

**Types of stakeholders**:
- **Decision-maker**: Who has final authority?
- **Impacted**: Who has to implement or live with the outcome?
- **Advisors**: Who has relevant expertise?
- **Approvers**: Who needs to sign off (Finance, Legal, etc.)?

**Map them**:
- **Decision-maker**: [Name, why them]
- **Impacted by build decision**: Product team (time), Customer Success (feature adoption), Engineering (maintenance)
- **Impacted by buy decision**: Finance (recurring cost), Customer Success (onboarding new tool), Product (less control)
- **Advisors**: [Analytics lead who understands landscape, Finance team on cost models]
- **Approvers**: [Finance director, CTO]

You'll want input from each group before deciding. Document this so people know they were considered.

### Step 3: Generate Real Options
Brainstorm 3–5 genuine options. Not strawmen. Not "obviously bad" options. Real alternatives.

**Criteria for real options**:
- It's something a reasonable decision-maker would consider
- It has distinct trade-offs vs. other options
- You've researched it enough to describe it credibly
- Someone in your organization might actually prefer it

**For "build vs. buy" decision**:
1. **Build in-house**: Custom, full control, takes 4 months, $50K, maintains forever
2. **Buy third-party SaaS**: Mixpanel, Amplitude, or similar. $15K/month, 2-week onboarding, limited customization
3. **Buy + build hybrid**: Buy base analytics, build custom reports on top. $10K/month + $20K one-time build. Best of both, but more complex.
4. **Do nothing (status quo)**: Keep current basic reporting. Better than current: not much. Downside: continue missing usage insights.
5. **Contract third-party analyst**: Hire consultant to do analysis 10 hours/week. $8K/month. No tool. Doesn't scale.

Options 1, 2, 3 are real. Option 4 (status quo) is important for comparison. Option 5 shows you thought beyond typical choices.

### Step 4: Create an Options Matrix
Build a table comparing options across key dimensions. This makes trade-offs visible.

**Dimensions to include** (customize to your decision):
- **Cost**: One-time + recurring
- **Time to value**: When can you use it?
- **Control/customization**: How much can you tailor it?
- **Effort to maintain**: How much ongoing work?
- **Scalability**: Does it work if you 10x your data/users?
- **Vendor lock-in**: How hard to switch later?
- **Team capability**: Can your team execute?
- **Risk**: What could go wrong?

**Example matrix** (Build vs. Buy vs. Hybrid):

| Dimension | Build | Buy (Mixpanel) | Hybrid | Do Nothing |
|-----------|-------|----------------|--------|------------|
| **Initial cost** | $50K | $0 | $20K | $0 |
| **Annual cost** | $10K (infra) | $180K | $130K | $0 |
| **Time to 1st dashboard** | 4 months | 2 weeks | 4 weeks | — |
| **Customization** | 100% | 30% | 70% | — |
| **Maintenance burden** | High (own it forever) | Low (vendor handles) | Medium (both) | None |
| **Scalability to 10M events/mo** | Yes (with effort) | Yes (built-in) | Yes | Not applicable |
| **Vendor lock-in** | None | High (data export limited) | Medium | None |
| **Team capability** | Have it (Analytics eng hired) | Need training (2 weeks) | Have it | Have it |
| **Risk** | Timeline slip, bugs, turnover | Limited customization, cost | Complexity, both systems | Competitors ahead |

Matrix makes trade-offs visible without verdict. Each option wins on different dimensions.

### Step 5: Build Pros & Cons With Weighting
For each option, list major pros and cons. Weight them by importance.

**Weighting approach**:
- Identify 3-4 criteria that matter most (e.g., Cost, Time to Value, Customization)
- Assign weight to each (1–5 stars, or % of total)
- Score each option on each criterion (1–5)
- Calculate weighted score (optional, but helps)

**Example** (Build option):
**Pros**:
- 🟢 Custom (5/5 importance): Can build exactly what we need. Addresses future requirements. Score: 5/5
- 🟢 No vendor lock-in (3/5 importance): Own the data and code. Can switch tools later. Score: 5/5
- 🟢 Team growth (2/5 importance): Analytics engineer learns our domain deeply. Becomes asset. Score: 4/5

**Cons**:
- 🔴 Time to value (5/5 importance): 4 months before useful. We need insights now. Score: 2/5
- 🔴 Maintenance burden (4/5 importance): Own it forever. Bugs, scaling, updates. Cost of ownership. Score: 2/5
- 🔴 Opportunity cost (3/5 importance): Engineer could be working on product features. Score: 2/5
- 🔴 Risk (3/5 importance): Scope creep, timeline slip, engineer leaves. Score: 2/5

**Weighted score** (rough):
Pros: (5×5 + 5×3 + 4×2) / 20 = 4.2/5
Cons: (2×5 + 2×4 + 2×3 + 2×3) / 15 = 2.1/5
Net: Positive on dimensions we care about, but significant downsides on speed.

Weight towards things that matter (Cost, Time, Customization if you care; Scalability, Maintenance if you care). Be honest about which dimensions matter most.

### Step 6: Address Reversibility
Some decisions are reversible; some are not. This changes the risk calculus.

**Reversible decisions** (easier to change later):
- Tool choice: You can switch vendors next year if this one doesn't work
- Process change: You can revert if it doesn't improve things
- Hiring in new domain: You can not rehire in that area if it doesn't work out

**Irreversible decisions** (hard to undo):
- Architecture choice: Changing core architecture is months of work
- Market entry: Pulling out of a market means relationship cost
- Acquisitions or major partnerships: Untangling is messy

**Why it matters**: If the decision is reversible, you can be bolder. Pick the best bet, not the safest bet. If irreversible, you need higher conviction and more analysis.

**Address reversibility in your doc**:
"If we choose Buy (Mixpanel), we can switch to a different vendor next year with 2 weeks data migration. This is reversible. If we choose Build, we're committed to maintaining this code for years. This is less reversible. Given reversibility, choosing Buy is lower-risk; we can always build later if it's not good enough."

### Step 7: Recommend (Clearly)
Don't present options neutrally and let everyone argue. Make a recommendation.

**Format**:
"**Recommendation: [Option X]**

**Why**: [2-3 sentences on why this is best given our priorities and constraints]

**Next steps**: [What happens if you agree with this recommendation]

**Risks mitigated by this choice**: [How does this choice reduce risks]"

**Example**:
"**Recommendation: Buy (Mixpanel)**

**Why**: We need to understand customer usage patterns within 8 weeks. Building in-house takes 4 months and carries execution risk. Mixpanel is proven, costs $180K/year, and gets us insights in 2 weeks. The 70% customization limitation is acceptable because we can build custom reports on top if needed. This is reversible; we can build in-house later if Mixpanel doesn't meet needs.

**Next steps**: If approved, Finance will execute contract (due by Friday). Product and CS onboard to Mixpanel next week. First analytics dashboard ready by April 15.

**Risks mitigated**: Timeline risk (solved by buying), team overload (solved by outsourcing), expertise gap (vendor handles training)."

The recommendation should be defensible but clear. It's not neutral. It's "given what matters, here's what I think we should do."

### Step 8: Flag Assumptions & Unknowns
Decisions rest on assumptions. Make yours explicit.

**Assumptions**:
- We need dashboards by Q2 (vs. Q3)
- Mixpanel's customization is sufficient for CS use cases
- Analytics engineer would be full-time on this (vs. 50%)
- No significant changes to our data model in next year

**Unknowns** (things you don't know but are assuming):
- Will Mixpanel pricing increase after year 1?
- How many custom reports will CS need?
- What if our data volume grows beyond Mixpanel's tier?

**Why**: If someone doesn't agree with an assumption, they can flag it. "Actually, we need dashboards by next month" changes the analysis. "Mixpanel might not be enough" changes the recommendation. Surface assumptions so they can be challenged.

### Step 9: Gather Feedback (Async + Sync)
Decision documents only work if people actually review and comment.

**Process**:
1. **Async review** (3-5 days): Share document with stakeholders. Ask for comments on options, weighting, recommendation. People can disagree async; saves time.
2. **Sync discussion** (30 min): Walk through decision with stakeholders. Surface disagreements. Clarify assumptions.
3. **Revision** (optional): If feedback surfaces major concerns, revise and resend before final decision.
4. **Decision & communication**: Decision-maker decides (taking stakeholder input into account). Communicate decision to everyone.

**Async feedback template**:
"Please review this decision document by [date]. Comment on:
- Do you agree with the options considered?
- Do you agree with the weighting of pros/cons?
- Do you agree with the recommendation?
- What concerns do you have?
- What am I missing?"

**In the sync discussion**:
- Walk through the matrix and recommendation (10 min)
- Open discussion: what's your take? (15 min)
- Resolve disagreements or concerns (5 min)
- Decision-maker: what's your call? (5 min)

### Step 10: Document the Decision & Next Steps
Once decided, document it clearly so people know what's going to happen.

**Decision record**:
- **Decision**: [What was decided]
- **Recommendation**: [Which option was chosen and why]
- **Stakeholder input**: [What concerns/support came up]
- **Next steps**: [What happens now, who owns what, by when]
- **Metrics for success**: [How we'll measure if this was the right call]
- **Review date**: [When we'll revisit this decision]

**Example**:
"**Decision: Buy Mixpanel for customer analytics**

**Recommendation**: Approved. Finance will contract ($180K/year). Product and CS onboard next week.

**Stakeholder input**:
- Finance approved cost and budget source.
- CS raised concern about customization limits; mitigated by noting we can build custom reports on top.
- Analytics engineer (new hire) is excited to learn the tool vs. building from scratch.

**Next steps**:
- Finance: Execute contract by Friday. Cost coded to Product budget.
- Product: Onboard team to Mixpanel first week of April. Owner: [Product Manager]
- CS: Set up standard dashboards. Owner: [CS Lead]
- Analytics: Build custom reports for high-value use cases. Owner: [Analytics Eng]

**Metrics for success**:
- Dashboard up and running by April 15
- CS using dashboard weekly in customer calls (goal: 80% of calls)
- Ability to answer "Which customers are at churn risk?" within 1 week (vs. 3 weeks now)
- Customer feedback on analytics dashboard quality (target: 7/10)

**Review date**: June 30. At that point, we'll assess: did this deliver what we needed? Should we keep or change?"

### Step 11: Communicate the Decision
Don't just update the stakeholders. Communicate to the broader team.

**Communication**:
- **Who**: Everyone who needs to know (impacted teams, cross-functional stakeholders)
- **What**: Decision made, why it was chosen, what happens next
- **When**: Within 1 day of decision
- **How**: Quick email or team update (don't require reading a 5-page doc)

**Sample communication**:
"**Decision: Analytics platform update**

We decided to use Mixpanel for our customer analytics. Why: we need usage insights by Q2, and buying gets us running in 2 weeks vs. 4 months to build. Mixpanel costs $180K/year and handles 90% of our use cases.

Next steps:
- Finance finalizing contract (due Friday)
- Product and CS onboarding next week
- First dashboard ready April 15

Questions? Reach out. [Link to full decision doc]"

Short, clear, action-oriented. People know what's happening and why.

## Output Template

**Decision Title**: [What's being decided]
**Decision-maker**: [Who has final authority]
**Deadline**: [When this needs to be decided]
**Scope**: [What does this affect, who's impacted]

**Stakeholders**:
- Decision-maker: [Name, role]
- Impacted: [Teams, people]
- Advisors: [Experts]
- Approvers: [Sign-off required]

**Options Considered**:
1. [Option A]: [Description, key trade-offs]
2. [Option B]: [Description, key trade-offs]
3. [Option C]: [Description, key trade-offs]

**Options Matrix**: [Dimensions vs. Options table showing trade-offs]

**Pros & Cons** (with weighting):
- **Option A**: [Pros (weighted)] vs. [Cons (weighted)]
- **Option B**: [Pros (weighted)] vs. [Cons (weighted)]
- **Option C**: [Pros (weighted)] vs. [Cons (weighted)]

**Reversibility**: [Is this decision reversible? How hard to undo?]

**Recommendation**: [Option X, because...]

**Next Steps** (if approved): [What happens, who, when]

**Assumptions**: [What are you assuming? What could be wrong?]

**Unknowns**: [What don't you know, but are assuming?]

**Feedback Requested**: [What do you want stakeholder input on?]

**Decision & Rationale**: [Once decided: what was chosen, why, stakeholder feedback incorporated]

**Metrics for Success**: [How we'll measure if this was right]

**Review Date**: [When we'll revisit]

## Quality Gates

1. **Is the decision clear?**: Could someone unfamiliar with this read it and understand what's being decided?
2. **Are options real?**: Would a reasonable decision-maker consider each option?
3. **Is the matrix fair?**: Does each option have a chance to shine (or fail) on some dimension?
4. **Is weighting transparent?**: Does it make sense which dimensions matter most?
5. **Is the recommendation clear?**: Is it obvious which option you're recommending and why?
6. **Are assumptions explicit?**: If someone disagrees with a key assumption, would the recommendation change?
7. **Is reversibility addressed?**: Do people understand how hard it is to undo this decision?
8. **Stakeholders are looped in**: Has everyone who cares about this decision been asked for input?

## Examples

### Good: Clear Decision with Recommendation
"**Decision: Should we hire an in-house DevOps engineer or use a managed infrastructure vendor?**

**Recommendation: Hire in-house DevOps engineer**

**Why**: We have specific infrastructure complexity (distributed systems, custom monitoring) that a managed vendor can't handle. We need deep knowledge of our systems for optimization. One in-house engineer (salary $150K) vs. managed vendor ($200K/year). Given complexity, in-house is better fit. This is partially reversible (we can hire a vendor later, but we'll have lost institutional knowledge).

**Options**:
1. Hire in-house: Full control, deep knowledge, $150K salary + benefits, takes 4 weeks to hire
2. Managed vendor: Outsourced, predictable cost ($200K/year), less control, takes 2 weeks to onboard
3. Hybrid: 1 in-house + supplemental vendor support ($150K + $50K/year), best of both, complexity

**Pros/cons** (weighting):
- **Cost** (weight: 3/5): In-house wins ($150K vs. $200K). Saves $50K/year. Score: In-house 4/5, Vendor 2/5
- **Knowledge** (weight: 5/5): In-house wins. Deep knowledge of our systems. Vendor is generic. Score: In-house 5/5, Vendor 2/5
- **Speed** (weight: 2/5): Vendor wins. Onboards in 2 weeks vs. 4 weeks to hire. Score: In-house 3/5, Vendor 5/5
- **Scalability** (weight: 2/5): In-house limited to one person. Vendor scales. Score: In-house 2/5, Vendor 5/5

**Reversibility**: In-house is reversible. We can hire a vendor later. Losing knowledge is the cost.

**Assumptions**:
- We have time to hire in 4 weeks
- One engineer is sufficient (we're not 50-person company; 10 people)
- Managed vendors don't understand our custom stack

**Next steps**: Hire DevOps engineer immediately. 4-week search timeline.

**Success metrics**: System uptime 99.95%+, incident response <1 hour, on-call burden manageable (<2 pages/week)."

### Good: Strategic Decision with Options Matrix
"**Decision: Should we enter the European market in 2024 or 2025?**

[Options Matrix]:
| Dimension | 2024 | 2025 |
|-----------|------|------|
| **Investment** | $500K (hiring, ops) | $300K (more efficient) |
| **Revenue impact Year 1** | $200K | $100K |
| **Competitive risk** | Low (early mover advantage) | High (competitors moving in) |
| **Team readiness** | 60% ready (hiring needed) | 90% ready |
| **Effort level** | Very high (founder CEO time) | High (hired GM handles) |
| **Reversibility** | Hard to pull back mid-year | Easier to delay |

**Recommendation: Enter 2024 despite higher lift**

**Why**: Competitive window is closing. Competitors are building out EMEA strategies. If we wait until 2025, we're a follower, not leader. The $500K investment is worth the early mover advantage. Reversibility is a factor, but the risk of missing the market is bigger than the risk of executing under strain.

**Risks mitigated**: Competitive risk (first-mover advantage), talent acquisition (entering market early attracts local talent), pricing power (establish early before price wars).

**Review date**: Q2 2024. If European hiring isn't on track or market conditions change, we can re-evaluate."

### Bad: Neutral, No Recommendation
"**Options**:
1. Build: 4 months, $50K, full control
2. Buy: 2 weeks, $180K/year, less control
3. Hybrid: Mix of both

All options have trade-offs. The team should decide which matters most to them."

No recommendation. No weighting. Abdication of decision-making. Forces everyone to re-analyze from scratch.

### Bad: Hidden Weighting
"**Cons of Option A**: Cost, maintenance burden, risk
**Cons of Option B**: Can't customize, vendor dependency
**Cons of Option C**: Complexity

Option B has fewer cons. Therefore Option B is best."

Weighting is hidden. Option B looks better because fewer cons were listed, not because it actually is better. Unclear reasoning.

## Common Mistakes

1. **Fake options**: Including options you don't actually want to consider. This wastes everyone's time. Only include options that are genuinely possible.

2. **No recommendation**: Presenting all options equally and letting the team decide. This isn't collaborative; it's abdicating. Give your best recommendation, then invite pushback.

3. **Hidden weighting**: "Cost is important" but then dismissing the cheapest option because "it doesn't match culture." Transparency requires you to weight criteria explicitly.

4. **One-sided pros/cons**: Listing 5 pros for option A and 5 cons for option B. Fair analysis has pros AND cons for each, weighted honestly.

5. **Ignoring reversibility**: Treating a $1M architecture decision the same as a $1K tool choice. Reversibility changes the risk calculus.

6. **Stakeholder surprise**: Deciding without asking stakeholders. You walk out of a meeting with a decision, they find out via email, they're surprised. Loop people in early.

7. **Decision fatigue**: Making the document too long, too complex. If it's >5 pages, people won't read it. Simplify and put details in appendix.

## Anti-Patterns

1. **Analysis paralysis**: Perfecting the decision document while the market window closes. "We'll decide once we have perfect data." Decision documents should inform decisions that happen in weeks, not months.

2. **Democratic indecision**: Looping in 10 stakeholders and then treating their feedback as requiring unanimous agreement. That's not decision-making; that's politics. Decision-maker decides, stakeholder input shapes but doesn't control.

3. **Post-hoc rationalization**: Building the decision document after you've already decided (to justify what you want). That's not transparent; that's fake consensus. Build the doc first, decide second.

4. **Moving goalposts**: Stakeholder says "I disagree because X" and instead of addressing X, you revise the doc to hide it. Transparency means surfacing disagreements, not smoothing them over.

5. **No follow-up**: Decision made, communicated, forgotten. Six months later, no one knows if it was right. Good decisions include metrics to measure success and a review date to revisit.
