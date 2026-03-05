---
name: status-report
description: "Create clear, action-oriented status reports with RAG (Red/Amber/Green) status, accomplishments, risks, and asks. Tailored for weekly team, monthly exec, and board formats."
category: communication
difficulty: beginner
model_boost: "Weak models produce rambling status updates without priority hierarchy, missing critical information for decision-making"
---

# Status Report

## Purpose
Status reports answer one core question: "What do I need to know about this work right now?" Effective reports are scannable, honest about risk, and clear about what you need from stakeholders. This skill creates reports calibrated to audience (team, manager, executive, board) that accelerate decision-making and prevent surprises.

## When to Use
- Weekly team syncs or standup updates
- Monthly manager check-ins or all-hands updates
- Executive reviews or board meetings
- Project milestones or phase gates
- Escalation or change communication
- **Do NOT use when**: Creating reports with dishonest status to avoid accountability; reporting without actual data; when a different format (conversation, presentation) is more appropriate

## Instructions

### Step 1: Determine Your Audience & Cadence
Different audiences need different information. Calibrate your report:

**Team-level (weekly, 5-10 min read)**:
- What you shipped
- What you're working on
- Blockers (so team can unblock you)
- Asks (if you need team input)

**Manager-level (weekly or bi-weekly, 10-15 min read)**:
- RAG status on key initiatives
- Major accomplishments
- Key risks and mitigation
- Resource/support needs
- Context on what's not working

**Executive-level (monthly, 5-10 min read)**:
- Top 3 accomplishments
- RAG status on strategic initiatives only
- Major risks and mitigation
- Key metrics
- Asks (if you need executive support)

**Board-level (quarterly, 10-15 min review + presentation)**:
- Strategic progress against company priorities
- RAG status on critical initiatives
- Top 3 accomplishments with business impact
- Top 2-3 risks with mitigation
- Key metrics (revenue, growth, unit economics, customer health)
- Asks (capital, strategy support, hiring approval)

### Step 2: Assign RAG Status Honestly
RAG (Red/Amber/Green) status forces clarity on health. Be honest, not optimistic.

**Green** (On track):
- You'll hit your target
- No major risks that would change outcome
- Example: "Shipping feature by March 15 (on track)" when you have buffer

**Amber** (At risk):
- You might miss the target, but have mitigation plan
- One or more risks that could impact if unaddressed
- Example: "Shipping feature by March 15 (at risk due to API delays; mitigating by pulling in eng support from Platform team)"

**Red** (Off track):
- You will not hit the target, or already missed it
- Major risks with no clear mitigation yet, or needs immediate decision
- Example: "Shipping feature by March 15 is not possible; recommending April 15 instead. Need approval to descope 2-3 features."

**Honest RAG is the most valuable thing you can communicate.** It lets managers allocate resources, take action, or reset expectations. Fake Green status creates surprises later.

### Step 3: List Accomplishments (Specific, With Context)
Don't just list what you did. Explain why it matters.

**Weak accomplishments**:
- "Shipped feature X"
- "Completed project Y"
- "Hired 5 people"

**Strong accomplishments** (specific + impact):
- "Shipped premium pricing feature. Early data: 20% of users are upgrading. Projected $2M incremental ARR."
- "Completed API redesign 2 weeks ahead of schedule. System latency dropped 40%. Improved developer experience for 10+ internal teams."
- "Hired 5 engineers (3 senior, 2 mid-level). Filled all open positions. Team velocity increased 25% in March."

Quantify when possible (metrics, dates, customers impacted, revenue). Provide context that explains why it's important.

### Step 4: Identify & Prioritize Risks (With Mitigation)
List 2-4 risks for manager/exec/board-level reports. For team-level, focus on blockers.

**Structure for each risk**:
1. **Risk statement** (what could go wrong): "API vendor might change pricing model"
2. **Probability & impact** (low/medium/high): "Medium probability, high impact ($200K cost increase)"
3. **Mitigation** (what you're doing): "Evaluating build-vs-buy on alternative APIs; will have recommendation by April 15"
4. **Escalation point** (if mitigation fails): "If no alternative is viable by May 1, we need executive decision on absorbing cost vs. raising prices"

**Examples**:
- **Risk**: "Our main customer (40% of revenue) is evaluating competitors. They're unhappy with onboarding time."
  - **Mitigation**: "Assigned dedicated CSM. Built onboarding shortcut. Reviewing with them on April 10. Expect positive signals by month-end."
  - **Escalation**: "If they're not satisfied after review, we may need to offer discount to retain."

- **Risk**: "Engineering hiring is slow. Market is competitive for senior engineers."
  - **Mitigation**: "Increased recruiter focus; referral bonus to 5K. Built 'engineering at [Company]' content. Pipeline improved to 8 qualified candidates."
  - **Escalation**: "If hiring doesn't accelerate by Q2, we may need to delay roadmap by one quarter."

Mitigation shows you're thinking ahead. Escalation point prepares leadership for decisions they might need to make.

### Step 5: Be Honest About What's Not Working
The hardest part of status reports is admitting when something's not working. But this information is crucial.

**Examples**:
- "Outbound sales isn't hitting targets. Close rate is 8% vs. 15% target. Root cause: sales team is underselling premium features. I'm working with product to improve positioning. Expect improvement in May, but April will miss quota."

- "Onboarding is taking too long (25 days vs. 7-day target). Customers are frustrated. Root cause: process has too many manual steps and customer success team is under-resourced. We're automating 3 steps and hiring 2 CSMs. Improvement timeline: June."

- "Retention is down 5 percentage points YoY. We're churn-focused now. Analyzing why. Early hypothesis: newer product features are confusing existing users. Building 3 educational pieces this month."

Honesty builds trust. Leaders respect managers who admit problems and solve them faster than those who hide problems and let them grow.

### Step 6: Ask for What You Need (Be Specific)
Don't bury asks. State them clearly.

**Weak asks**:
- "We might need help with hiring"
- "Resources would be great"
- "Need to discuss roadmap"

**Strong asks** (specific, with context):
- "I need to hire 2 senior engineers by June 1. Recruiting team has capacity for 1 req. Can we fund the 2nd recruiter, or should I adjust timeline?"
- "API redesign is blocked on Platform team prioritization. They have 3 competing projects. Can you help reprioritize so we can unblock this?"
- "Q3 roadmap requires 20% more engineering capacity than we have. Options: (1) extend timeline to Q4, (2) hire 2 engineers, (3) reduce scope. I recommend option 2 because of market window. Need approval."

Specific asks create action. Vague asks create more meetings.

### Step 7: Create the Report (Format by Audience)

#### Team-Level Weekly Update (Synchronous or Async Slack/Email)

**Format**:
- **This week**: [3-5 things completed, with brief context]
- **Next week**: [3-5 things starting, with any dependencies]
- **Blockers**: [Anything preventing progress, who can help]
- **Asks**: [Anything you need from team]

**Example**:
"**This week**: Shipped search filters feature. Early usage is high (25% of users using in first 2 days). Also completed performance analysis—identified N+1 queries in user profile page. Starting optimization next week.

**Next week**: Optimization work + designing new reporting dashboard. Depends on finalizing spec with Product.

**Blockers**: Need GraphQL schema decision from API team. We're holding on dashboard design until we know if we're querying REST or GraphQL.

**Asks**: Can someone unblock the schema decision? I can jump on a 30-min sync to align.

Thanks,
[Name]"

#### Manager-Level Bi-Weekly Update (Email or Document)

**Format**:
- **Overall RAG**: [Status on your key goals/projects, 1-3 items]
- **Accomplishments**: [2-4 accomplishments with impact]
- **What's not working**: [Honest assessment of underperformance, with actions]
- **Risks**: [2-4 risks, with mitigation]
- **Asks**: [Specific support you need]
- **Metrics**: [Key metrics for your area—growth, quality, efficiency]

**Example**:
"**Overall RAG**:
- Q2 roadmap delivery: Green (on track for all 5 initiatives)
- Customer success retention: Amber (93% retention vs. 95% target; see below)
- Team expansion: Amber (1 of 2 senior hires complete; slow pipeline on 2nd)

**Accomplishments**:
- Shipped premium pricing feature. 20% of new customers choose premium. Projected $2M incremental ARR in full year.
- Reduced onboarding time from 25 to 20 days through automation of 2-step process. Next phase targets 15 days by Q3.
- Mentored 3 junior engineers; two got promoted to mid-level. Team morale up (April survey: 8.2/10 vs. 7.5/10 in Jan).

**What's not working**:
- Customer retention dropped 2% YoY. Root cause: existing customers frustrated with premium feature complexity. Action: creating 3 educational pieces this month; recording a live onboarding training for premium features on April 20.

**Risks**:
- Hiring is slow. Market is competitive. Pipeline of qualified senior engineers is only 2 candidates. Mitigation: Referral bonus increased to 5K; content campaign launching April 15. Escalation: If June pipeline still low, we may need to adjust timeline on team expansion.
- One major customer (15% of revenue) is evaluating competitors due to onboarding friction. Mitigation: Dedicated CSM assigned; customer success director doing weekly check-ins. Escalation: May need to offer discount to retain if they're not satisfied after improvement plan.

**Asks**:
- Want to discuss compensation strategy to be more competitive for senior hires. Quick call next week?
- Need approval on hiring 2nd CSM (budget impact: $120K/year). Justification: customer success is key to retention; current team is under-resourced.

**Metrics** (attached):
- Team velocity: 85 pts/sprint (target: 80)
- Churn: 7% (target: <5%)
- NPS: 52 (target: 60)
- Time to value: 20 days (target: 15 days)"

#### Executive-Level Monthly Update (Document for Review + Presentation)

**Format**:
- **Strategic highlights** (top 3 wins)
- **RAG status** (only strategic initiatives, 2-3 items)
- **Key risks** (top 2, with mitigation)
- **Key metrics**
- **Asks/decisions needed**

**Example**:
"**Strategic Highlights**:
1. Premium pricing launched. 20% attach rate. Projected $2M incremental ARR.
2. Customer satisfaction improved. NPS up 8 points (52→60) due to onboarding improvements.
3. Team expanded with 3 new senior engineers. Velocity up 25%.

**RAG Status**:
- Q2 roadmap: Green. All 5 initiatives on track for shipping by deadline.
- Revenue growth: Green. ARR growth 45% YoY. Tracking to $25M exit velocity by year-end.
- Customer retention: Amber. 93% vs. 95% target. See risks below.

**Key Risks**:
1. Retention risk (15% of revenue at churn risk). Mitigation: onboarding improvements underway; should see improvement by month-end. Escalation: if no improvement, may need to offer retention discount.
2. Competitive risk in premium segment. Mitigation: building unique analytics dashboard in Q3 to differentiate. Escalation: if market shifts quickly, may need expedited roadmap.

**Metrics** (this month):
- ARR: $22M (45% YoY growth)
- Churn: 7% monthly (target <5%)
- NPS: 52 (up from 44 in January)
- Retention: 93% (target 95%)
- New customers: 320 (up 30% YoY)

**Asks**:
- Approval to hire 2nd CSM ($120K/year). Justification: customer success is leverage point for retention; current team under-resourced.
- Decision on premium product positioning. Two options for marketing emphasis. Recommend option 1 (advanced analytics). Quick decision needed by Friday for Q2 campaign planning."

#### Board-Level Quarterly Update (Document + 15-20 min presentation)

**Format**:
- **Executive summary** (1 paragraph on progress)
- **Strategic progress** (vs. plan, with RAG on 2-3 initiatives)
- **Key accomplishments** (top 3, with business impact)
- **Key risks** (2-3, with mitigation)
- **Metrics** (revenue, growth, key unit economics)
- **Asks/decisions** (what you need from board)

**Example**:
"**Executive Summary**:
Q1 was strong execution. We shipped premium pricing, expanded the team, and improved customer satisfaction. ARR up 45% YoY to $22M. Churn ticking up slightly; addressing through onboarding and engagement improvements.

**Strategic Progress**:
- Expand to premium segment: Green. Launched pricing, 20% of new customers adopting. Projected $2M incremental ARR.
- Improve unit economics: Amber. CAC down 15%; LTV up 20%. Payback period improved to 10 months from 12 months. Target: 8 months. Action: reducing onboarding cost through automation (in progress).
- Team expansion: Amber. Hired 3 of 5 senior engineers planned for H1. Recruiting remains competitive. Expect to complete hiring by July.

**Key Accomplishments**:
1. Shipped premium pricing. Early adoption strong (20% of new customers). Projected incremental revenue impact: $2M ARR.
2. Improved customer satisfaction. NPS up 8 points (52). Onboarding improvements (5-day reduction) contributed significantly.
3. Expanded team from 32 to 38 (16% growth). Hired senior engineers in infrastructure and product.

**Key Risks**:
1. Churn is rising (7% vs. 5% target). Root cause: complexity of premium features. Mitigation: (a) educational content + live training launching April 20; (b) dedicated CSM for at-risk accounts. Expect improvement by June.
2. Competitive threat in premium segment. Competitor launched copycat feature. Mitigation: accelerating unique analytics dashboard to Q3 (was Q4). Need to review impact on roadmap.

**Metrics**:
- ARR: $22M (45% YoY growth)
- Net revenue retention: 120% (strong)
- Churn: 7% (target <5%; up from 5% in Dec)
- CAC payback: 10 months (improving; target: 8 months)
- NPS: 52 (up from 44 in Jan; target 60)
- Customer count: 420 (up 35% YoY)

**Asks/Decisions**:
1. Approval to accelerate competitive feature to Q3 (marketing impact decision).
2. Feedback on go-to-market positioning for premium segment (two strategic options; recommend option 1).
3. Capital planning: seed conversations for Series B (projected timeline: Q4 based on runway and growth)."

### Step 8: Proofread & Make it Scannable
- Use bold for headers and key numbers
- Use bullet points, not paragraphs
- Keep sentences short
- Lead with RAG status, accomplishments, risks (most important)
- Put details in attachments or links, not the body
- Proofread for tone (confident but not arrogant, honest but not self-flagellating)

## Output Template

**Report Type**: [Team/Manager/Executive/Board]
**Period**: [Week of X / Month of X / Quarter X]
**Owner**: [Your name]

**RAG Status** (if applicable): [Green/Amber/Red + brief context]

**Key Accomplishments**:
- [Accomplishment 1 + impact/metrics]
- [Accomplishment 2 + impact/metrics]
- [Accomplishment 3 + impact/metrics]

**What's Working Well**:
- [Positive trend 1]
- [Positive trend 2]

**What's Not Working**:
- [Challenge 1 + root cause + action]
- [Challenge 2 + root cause + action]

**Key Risks** (if applicable):
- Risk: [Risk statement]
  - Probability/impact: [Assessment]
  - Mitigation: [What you're doing]
  - Escalation: [Decision point if mitigation fails]

**Metrics**:
- [KPI 1]: [Current value] (target: [X], vs. [period]: [trend])
- [KPI 2]: [Current value] (target: [X], vs. [period]: [trend])

**Blockers** (team-level) or **Asks** (manager/exec-level):
- [Ask 1 + context]
- [Ask 2 + context]

## Quality Gates

1. **RAG is honest**: Would you stake your reputation on this status?
2. **Accomplishments have impact**: Can you quantify why it matters?
3. **Risks are real, not hypothetical**: Are these actual risks, not things that "might" happen?
4. **Mitigation is credible**: Is what you're doing actually addressing the risk?
5. **Asks are specific**: Could someone take action on your ask?
6. **Metrics tell a story**: Do the numbers show progress, stall, or decline?
7. **Scannable**: Could someone understand the key points in 90 seconds?
8. **Honest about what's not working**: Are you acknowledging failures or minimizing them?

## Examples

### Good: Team-Level (Weekly Slack)
"**This week**: Shipped search filters. 25% of users trying in first 2 days (great early adoption). Also completed performance analysis—found N+1 queries in user profile page.

**Next week**: Query optimization + dashboard design. Dashboard depends on API schema decision from Platform team.

**Blocker**: Need GraphQL vs. REST decision ASAP. Can we do a 30-min sync with Platform lead?

**Metrics**: Search feature live with 0 critical bugs. Performance improvements expected 20% latency reduction."

### Good: Manager-Level (Bi-Weekly Email)
"**Overall RAG**: Green on roadmap, Amber on retention.

**Wins**: Shipped premium feature (20% adoption, $2M ARR impact). Improved onboarding from 25 to 20 days. One junior engineer promoted.

**Challenge**: Retention down 2%. Existing customers struggle with premium complexity. Action: three educational pieces this month + live training April 20.

**Risk**: Major customer (15% revenue) evaluating competitors. Mitigation: dedicated CSM + weekly director check-ins. Escalation: may need discount if not satisfied.

**Asks**: (1) Approve 2nd CSM hire ($120K/year)—customer success is under-resourced. (2) 30-min discussion on compensation strategy to compete for senior hires."

### Good: Executive-Level (Monthly)
"**Summary**: Strong Q1 execution. Premium launch successful (20% adoption). Churn ticking up—addressing. ARR 45% YoY growth to $22M.

**RAG**: Premium segment (Green). Churn (Amber—7% vs. 5% target; mitigating). Hiring (Amber—3 of 5 placed; competitive market).

**Wins**: (1) Premium pricing 20% attach. (2) NPS up 8 points. (3) Team expanded 16%.

**Risk**: Churn. Mitigation: educational content + CSM focus. Escalation: if no improvement by June, needs different strategy.

**Metrics**: ARR $22M (45% growth). Churn 7% (target <5%). NPS 52 (target 60). Payback 10mo (target 8mo).

**Asks**: (1) Approve 2nd CSM. (2) Feedback on premium positioning (two options). (3) Capital planning for Series B discussion (Q4 seed)."

### Bad: Vague, Dishonest, Buried Asks
"Things are going well. Team is working hard. We'll probably hit targets. Some customer issues but we're on top of it. Might need some help with hiring at some point. Everything is Green."

No specifics. Status is fake. Asks are buried. No metrics. Doesn't help anyone make decisions.

## Common Mistakes

1. **Green status when it's really Amber**: You're optimistic, not realistic. Leaders make decisions based on status. False Green creates surprises.

2. **Metrics without context**: "ARR is $22M." Good. But is that up from $20M or down from $25M? "ARR $22M (45% YoY growth, up 10% from last month)" is better.

3. **Risks without mitigation**: "Customer X might churn." Okay, what are you doing about it? Mitigations show you're thinking ahead and managing, not just reporting problems.

4. **Accomplishments that are activities, not outcomes**: "Shipped feature X" is activity. "Shipped feature X; 20% of users adopted; NPS improved 8 points" is outcome.

5. **Burying the main news**: Lead with RAG status and key accomplishments. Details come after.

6. **Making asks that aren't asks**: "We might need help with hiring" is vague. "Can you approve 2nd recruiter to fill 5 open req? I recommend funding from [budget], or we extend timeline to July" is actionable.

7. **Overcomplicated format**: You've made a document that's hard to scan. Use headers, bullets, bold. Assume your audience has 10 minutes max.

## Anti-Patterns

1. **Cheerleading instead of honesty**: "Everything is amazing! Team is crushing it! We're on track for everything!" Sets unrealistic expectations. Leaders prefer honest assessment.

2. **Blame-shifting in risks**: "Customer isn't happy because they don't understand how to use the product." vs. "Customer satisfaction lower than expected due to onboarding complexity. Action: simplifying onboarding + educational content."

3. **Asking without doing**: "We need 2 more people. Can we hire?" vs. "We need 2 more people. Here's why [metric impact]. Recruiting has pipeline of 5 candidates. Can you approve budget of $200K/year and expedite hiring approval?"

4. **Making status reports about you instead of what matters**: "I've been working so hard..." vs. "Premium feature shipped. 20% adoption. $2M impact."

5. **Expecting everyone to read everything**: Board doesn't care about team-level blockers. Execs don't need weekly metrics. Calibrate to audience.
