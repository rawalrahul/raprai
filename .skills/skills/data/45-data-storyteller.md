---
name: data-storyteller
description: "Transform raw data, charts, and analyses into compelling executive narratives. Extract insights, frame with 'so what', provide recommendations, and ensure decision readiness."
category: data
difficulty: intermediate
model_boost: "Weak model presents data without insight or actionable recommendations"
---

# Data Storyteller

## Purpose
Raw numbers don't drive decisions—stories do. This skill transforms analyses into narratives that executives understand, remember, and act on. The output is a structured story with clear insight, business implications, and recommended actions, ready for presentation and decision-making.

## When to Use
- Presenting analysis results to executives or stakeholders
- Converting dashboards into decision memos
- Creating reports for board-level communication
- Synthesizing multiple data sources into coherent narrative
- **Do NOT use when**: Exploratory analysis, or audience prefers raw tables/numbers

## Instructions

### Step 1: Extract the Core Insight
Find the one surprising, important thing the data reveals:

**Poor insight (data without meaning):**
```
"Monthly revenue is $2.4M. In Q3 it was $2.1M. There was a 14% increase."
→ Recitation of numbers, no insight about why or what it means
```

**Good insight (situation + change + implication):**
```
"Revenue grew 14% YoY to $2.4M, driven entirely by high-value customers
(>$1000/month). Low-value customer revenue actually declined 8%.
This signals our product increasingly serves enterprise needs."
→ Identifies source of growth, reveals strategic shift, invites action
```

**Insight extraction process:**
```
1. What changed?
   Metric: Monthly revenue
   Baseline: $2.1M (Q3 2024)
   Current: $2.4M (Q3 2025)
   Change: +$300K (+14%)

2. Why did it change?
   Decomposition analysis:
   - Enterprise segment (>$1000/mo): +$220K (+28%)
   - Mid-market ($100-1000/mo): +$45K (+9%)
   - SMB (<$100/mo): -$35K (-8%)

   Root cause: Enterprise expansion in financial services sector

3. What does it mean?
   Interpretation: Market is shifting toward high-value customers
   Implication: Our GTM should emphasize enterprise capabilities
   Risk: Neglecting SMB segment could hollow out base

4. So what?
   The "so what" is the insight:
   "Revenue growth masks diverging customer quality.
   We're succeeding with enterprise but losing SMB customers.
   Action needed: Define long-term SMB strategy (focus or exit)."
```

### Step 2: Choose the "So What" Frame
Structure insight around business impact, not methodology:

**Poor frame (technical, process-focused):**
```
"We analyzed 500K transactions using logistic regression.
The model showed customer tenure (coefficient=0.23) and engagement
(coefficient=0.41) are significant predictors of churn."
→ Focuses on method, not impact; requires audience to translate to action
```

**Good frame (business impact-focused):**
```
"We can now predict customers at high churn risk before they leave.
Early indicators: engagement drops below 2 sessions/week and
tenure <12 months. By targeting these customers with success outreach,
we estimate 15% reduction in churn, worth $1.2M annually."
→ Focuses on business outcome; clear action (target these customers)
```

**"So what" reframes for different audiences:**

**For CFO/Board (financial frame):**
```
Data: 20% of customers churn each quarter
So what (financial): Acquiring new customer costs $5K, LTV=$18K.
High churn (20%/quarter) means most customers never reach profitability.
Action: Improve retention from 80% to 85% quarterly (+5pp) = $2.1M NPV annually
```

**For Product/Engineering (strategic frame):**
```
Data: Feature adoption increases retention 25% (93% vs. 74%)
So what (strategic): Most customers don't know about our core feature.
We're selling the wrong benefits in onboarding.
Action: Redesign first-week experience to introduce feature in context
```

**For Sales (revenue frame):**
```
Data: Sales process takes average 85 days, complex enterprise takes 120 days
So what (revenue): Slow sales cycle limits pipeline throughput.
For $10M ARR goal, we need 2x closing rate or 50% shorter cycle.
Action: Implement sales accelerators (compressed demos, simpler contracts)
Target: Reduce to 60-day average cycle
```

### Step 3: Structure the Narrative Arc
Organize story for cognitive impact and memory:

**The Situation-Complication-Resolution arc (executive-friendly):**

```
SITUATION (Context):
- Our customer base consists of 3 segments: Enterprise, Mid-market, SMB
- Growth is a key strategic priority
- Last year we grew 12% YoY

COMPLICATION (What's surprising):
- This year we grew 14% YoY, but...
- Enterprise segment grew 28% (exceptional)
- SMB segment SHRUNK 8% (unexpected)
- Overall growth masks deteriorating SMB health

RESOLUTION (What we should do):
Option 1: Double down on enterprise (higher margin, lower support)
- Pros: Faster growth, better unit economics
- Cons: Risks losing SMB base, dependence on few large customers

Option 2: Stabilize SMB with targeted retention
- Pros: Diversified revenue, stable base for growth
- Cons: Requires investment, slower net revenue growth

Option 3: Segment strategy (nurture enterprise, wind down SMB)
- Pros: Focused go-to-market, clearer messaging
- Cons: Customer loyalty risk, engineering complexity

RECOMMENDATION:
Pursue Option 2 with timeline: Stabilize SMB (3 months),
then pivot to enterprise growth (ongoing).
Success metrics: SMB churn <5%, enterprise growth >20%
```

**Key structural principle: Inverted pyramid**
```
HEADLINE (1 sentence):
"SMB customer segment is eroding despite overall 14% growth;
immediate retention action required."

SUMMARY (3-5 sentences):
Enterprise segment strong (28% growth). SMB declining (-8%).
Root cause: Underinvestment in SMB success, no dedicated support.
Estimated risk: Loss of SMB base within 12 months if unaddressed.
Recommended action: Hire dedicated SMB success manager, implement automation.

DETAILS (Data, analysis, supporting evidence):
[Charts, metrics, cohort analysis]

APPENDIX (Methodology, assumptions, caveats):
[Statistical tests, data sources, limitations]

Why inverted pyramid?
Executive reads headline + summary and understands story
Manager reads through details for confidence
Analyst references appendix for rigor
Everyone finds what they need quickly
```

### Step 4: Create Supporting Data Visualizations
Design charts to prove insight, not just decorate:

**Visualization selection for storytelling:**

```
INSIGHT: Enterprise revenue grew 28%, SMB shrunk 8%

POOR VISUALIZATION:
- Bar chart showing all revenue segments with similar visual weight
- Requires viewer to calculate growth rates mentally
- Doesn't highlight the story (divergence)

GOOD VISUALIZATION:
- Slope chart (100 points at t=0) showing diverging trajectories
  Enterprise: 100 → 128
  Mid-market: 100 → 109
  SMB: 100 → 92
- Visual immediately shows divergence
- Story unmistakable: Enterprise growing, SMB declining

SUPPORTING CHARTS:
1. Cohort analysis: Retention by segment and cohort vintage
   (Shows SMB cohorts don't last; enterprise cohorts sticky)
2. Customer acquisition: New customers by segment
   (Shows we stopped acquiring SMB customers)
3. Churn drivers: What's causing SMB churn?
   (Identifies problems to solve)
```

**Visualization quality checklist:**
- One insight per chart (not cluttered)
- Chart type matches story (not ornamental)
- Axes labeled clearly, units obvious
- Color coding consistent across presentation
- Annotation highlighting key point (not assuming audience sees it)

### Step 5: Build Recommendations with Clear Trade-offs
Guide decision-making, not decision-making:

**Good recommendation structure:**

```
INSIGHT: Customer acquisition cost has increased 35% YoY
Cause analysis:
- Ad spend increased 40% (intentional marketing expansion)
- Conversion rate declined 8% (ad quality or saturation)
- Sales team size stable (not better at closing)

OPTION A: Maintain current CAC (reduce spend)
Pros: Lower marketing expense, improved unit economics
Cons: Growth slows from 15% to 8%, delays $5M ARR target by 8 months
Who benefits: Finance (lower spend), Ops (simpler execution)
Who loses: Sales (lower pipeline), Growth (miss goals)

OPTION B: Accept higher CAC (maintain spend)
Pros: Hit growth targets, build brand awareness at scale
Cons: Unit economics worse (LTV/CAC ratio 2.2x vs. target 3.0x)
      Requires price increase or cost reduction to sustain profitably
Who benefits: Growth (hit targets), Sales (strong pipeline)
Who loses: Finance (margins), Board (path to profitability unclear)

OPTION C: Improve conversion (maintain spend, better efficiency)
Pros: Hit growth targets with same spend (improves CAC)
Cons: Requires product changes (longer timeline), not guaranteed
      If successful, best outcome; if fails, have no fallback

RECOMMENDATION:
Pursue Option C with 90-day sprint + Option A fallback.
- Launch conversion optimization program (target: recover 4pp drop)
- Set checkpoint at 45 days: if on track, continue; else revert to B
- Success metric: CAC back to $2,000 (from $2,700) by Q2 2026

IMPLICATIONS:
- Product prioritizes funnel optimization (delay feature X by 1 quarter)
- Sales team trains on new close process (investment: $50K)
- Risk: If not successful, growth delayed to Q3
```

### Step 6: Create Decision-Ready Presentation
Prepare presentation that moves from insight to decision:

```
EXECUTIVE PRESENTATION STRUCTURE (15 minutes)

0-2 min: HEADLINE + CONTEXT
"We're winning in enterprise, losing in SMB. Our three-segment strategy
needs to become a focused two-segment strategy."

2-5 min: DATA STORY (The situation-complication-resolution)
[Show diverging revenue trajectory]
"Enterprise revenue up 28%, SMB down 8%. This divergence is accelerating."
[Show cohort retention by segment]
"Newer SMB cohorts don't stick; older enterprise cohorts have 95% retention."

5-8 min: ROOT CAUSE ANALYSIS
"Why? We optimized for enterprise sales and product. SMB got no dedicated
support. They churn after 6 months when enthusiasm wears off."

8-12 min: OPTIONS + RECOMMENDATION
[Compare 3 strategic options with trade-offs]
"Option C (improve SMB retention) has highest upside but highest risk.
Recommend: 90-day pilot with clear success metrics. If not working by day 45, revert to
B (accept enterprise-only strategy)."

12-15 min: DECISION + NEXT STEPS
"Approve Option C pilot? If yes:
- Product: Reassign 1 PM to SMB experience (Friday onboarding)
- Sales: Hire 1 SMB success manager (start now, lead pilot)
- Board: Budget $200K pilot, report results in April"

ONE-PAGER SUMMARY:
Headline: SMB Segment Deterioration
Insight: Enterprise growth masks SMB erosion; strategic drift
Action: 90-day retention pilot, abort/scale decision at day 45
Success metrics: SMB churn <5%, retention cohort analysis shows improvement
Budget: $200K, 1 PM, 1 CSM
Timeline: Start now, results by April 30
Decision needed: Approve pilot? CEO sign-off needed
```

## Output Template

**Data Story Document:**

```markdown
# Memo: Why Our Growth Strategy Is Diverging

TO: Executive Team
FROM: Analytics
DATE: 2026-03-05
DECISION NEEDED: Approve SMB retention pilot or pivot to enterprise-only?

## Headline
Enterprise segment thriving (+28% growth) while SMB eroding (-8% decline).
Current strategy doesn't work for both; must choose focus.

## The Situation
[1 paragraph: Context, strategy, prior status]

## The Complication
[Data showing what's surprising: diverging trajectories, cohort analysis]

## Root Cause
[Why it happened: Market signals, product focus, support gaps]

## Trade-off Analysis
[3 options with pros/cons, not recommendation]

## Recommendation
[Clear action, timeline, success metrics, who owns what]

## Supporting Data
[Charts: Revenue by segment, retention cohorts, CAC by channel]

## FAQ
Q: Why did SMB decline?
A: [Root cause analysis]

Q: What if we do nothing?
A: [Risk quantified]

Q: How long will the pilot take?
A: [Timeline and checkpoints]
```

## Quality Gates

1. **One clear insight**: Can audience state it in one sentence after reading?
2. **"So what" explicit**: Business implications clear, not methodology focus
3. **Options presented**: Trade-offs visible, decision-makers understand stakes
4. **Recommendation specific**: Not vague; includes action, owner, timeline
5. **Supporting data present**: Charts prove story, not decorate it
6. **Decision path clear**: What decision is needed? Who decides? When?

## Examples

**Good: Clear story arc with recommendation**
```
Situation: Customer spend concentrates in high-value segment
Complication: But we're spending marketing budget equally across all segments
Resolution: Reallocate 60% of budget to high-value segment acquisition
Recommendation: A/B test allocation over 2 quarters, measure CAC and LTV
Result: Move marketing budget to high-value (approved), expected $2M impact
```

**Bad: Data dump without story**
```
"We analyzed 2M transactions. Using cohort analysis, we found that
customers acquired in Q4 have 15% higher retention than Q1 customers.
Churn rate is 5% monthly. LTV varies by segment."

Issues: No insight extracted, no "so what", no recommendation,
no decision specified. Audience doesn't know why this matters.
```

## Common Mistakes

1. **Inverted structure**: Burying insight in appendix; executive tunes out before learning story
2. **Methodology obsession**: "We built a logistic regression model" instead of "We can predict who'll churn"
3. **Too many options**: Presenting 7 strategic choices; decision-maker paralyzed
4. **Undefined success metrics**: "Improve retention" without specifying what success looks like
5. **Recommendation without owner**: "We should optimize conversion" (by whom? by when?)
6. **Ignoring trade-offs**: Presenting only upside, hiding costs/risks

## Anti-Patterns

1. **"More analysis needed"**: Every data story ending in "need more data to decide"; delays action indefinitely
2. **Politically safe recommendations**: Recommending no change to avoid conflict; data suggests action
3. **Metric cherry-picking**: Showing metric that supports hypothesis, hiding contradictory metrics
4. **Absent baseline**: Claiming improvement without context (10% growth vs. what?)
5. **False precision**: Recommending $2.1M savings when based on estimates ±$500K