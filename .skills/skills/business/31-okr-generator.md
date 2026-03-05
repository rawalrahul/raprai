---
name: okr-generator
description: "Generate company, team, and individual OKRs with outcome-driven objectives, measurable key results, cascading alignment, and scoring criteria. Ensures strategic focus and enables transparent progress tracking."
category: business
difficulty: intermediate
model_boost: "Prevents vague goal-setting and misaligned OKRs common in weak organizations; produces instead focused, measurable, cascading OKRs with clear ownership."
---

# OKR Generator

## Purpose
OKRs (Objectives and Key Results) are a goal-setting framework that drives strategic focus and transparent execution. This skill generates company-level OKRs (strategic direction), team OKRs (how each team contributes), and individual OKRs (how individuals execute), with proper cascading alignment, measurable key results, and scoring criteria. Output enables quarterly cadence, regular progress tracking, and course correction.

## When to Use
- Planning quarterly or annual strategy (especially early-stage startups and scaling companies)
- Aligning teams around shared priorities (5+ people need goal clarity)
- Measuring and tracking progress transparently (quarterly reviews, board reporting)
- Improving execution velocity through focus (when org has too many priorities)
- **Do NOT use when**: Your company is pre-product-market fit (focus on customer validation, not metrics); you haven't defined success criteria (do that first); OKRs would distract from immediate firefighting (address crises first).

## Instructions

### Step 1: Define Company-Level Objectives (Qualitative)
Objectives are **qualitative, inspiring outcomes** that focus the organization. They answer: "What do we want to achieve this quarter?" Not "what metrics do we hit" (that's Key Results). Objectives should be:
- Ambitious but achievable (not 50x growth, but 2-3x)
- Outcome-focused (not task-focused: "Launch product" is weak; "Dominate SMB segment" is strong)
- Memorable (1-2 sentences, repeatable)
- Tied to competitive positioning or business model change

Examples of strong objectives:
- "Establish product-market fit with SMB segment" (validation-focused)
- "Transition from sales-led to product-led growth" (model change)
- "Become the #1 trusted partner for Fortune 500 digital transformation" (positioning)
- "Build unstoppable retention moat via network effects" (strategy shift)

Weak objectives:
- "Increase revenue" (vague, no focus)
- "Launch mobile app" (task, not outcome)
- "Ship features faster" (improvement without direction)

Typical company has **3-5 objectives per quarter**. More dilutes focus.

### Step 2: Define Key Results (Quantitative & Measurable)
Key Results are **measurable outcomes** that define success for each objective. Each objective has 2-4 Key Results. KRs should be:
- Quantified (metrics with units and targets)
- Measurable (not subjective: "improve customer satisfaction" is weak; "NPS 55-60" is strong)
- Outcome-focused (not activity: "conduct 50 customer interviews" is activity; "validate 3 use cases with paying pilots" is outcome)
- Ambitious (target 70-80% confidence you'll hit 100%; if you're 95% confident, you're too conservative)

Mapping Objective → Key Results:

**Objective**: "Establish product-market fit with SMB segment"
- **KR 1**: Reach NPS ≥ 50 (from 42 currently)
- **KR 2**: Achieve <5% monthly churn in target segment (from 8%)
- **KR 3**: Acquire 30 paying SMB customers (from 8 currently), each profitable on contribution margin
- **KR 4**: Validate willingness-to-pay at $250-500/month via pricing survey with 20 SMBs

**Objective**: "Transition to product-led growth"
- **KR 1**: 40% of new customers come from self-serve (from 5%)
- **KR 2**: Time-to-first-value reduced to < 5 minutes (from 30 minutes)
- **KR 3**: Free trial signup-to-paid conversion reaches 8% (from 3%)
- **KR 4**: Product-led cohort CAC < $50 (from $1,200 with sales team)

### Step 3: Cascade to Team OKRs
Each company OKR rolls down into team OKRs. Team OKRs answer: "How does this team contribute to company goals?" Alignment is key: if Engineering owns "Transition to product-led growth," their OKRs might be:

**Team**: Product & Engineering
**Company OKR Contributing**: "Transition to product-led growth"
- **Team OKR 1**: "Reduce onboarding friction to enable self-serve motion" (contributes to KR: time-to-first-value < 5 min)
  - KR 1: Onboarding completion rate 70% by month 1 (from 40%)
  - KR 2: Average time to first data upload: 3 minutes (from 15 min)
  - KR 3: Ship 3 one-click integrations (addresses top friction point)

- **Team OKR 2**: "Improve in-app guidance and analytics" (contributes to KR: free trial conversion 8%)
  - KR 1: Build contextual help for top 5 features (70% of users use them)
  - KR 2: Surface personalized product recommendations based on usage (increase feature discovery 25%)
  - KR 3: Implement analytics to measure engagement by feature (enable data-driven decisions)

**Team**: Sales & Customer Success
**Company OKR Contributing**: "Establish product-market fit with SMB"
- **Team OKR 1**: "Acquire 30 profitable SMB customers with repeatable sales motion"
  - KR 1: Close 20 customers at $250-500/month ARPU (contribution margin > 70%)
  - KR 2: Develop repeatable SMB sales playbook (customer acquisition cost < $600)
  - KR 3: Identify top 3 SMB verticals and close 2 customers each (establish beachhead)

Not every company OKR has a team OKR. Some are company-wide (like fundraising). Some teams support multiple OKRs.

### Step 4: Cascade to Individual OKRs (Optional for Smaller Teams)
Individual OKRs are owned by specific people and support team OKRs. They're more detailed and tactical. Example:

**Individual**: Jane (Product Manager)
**Contributing to Team OKR**: "Reduce onboarding friction"
- **OKR 1**: Onboarding experience redesign
  - KR 1: Conduct 10 user testing sessions, document friction points
  - KR 2: Redesign flow (MVP), launch to 20% of users
  - KR 3: Achieve 60% completion rate in beta (from 40%)

**Individual**: Mike (Enterprise Account Executive)
**Contributing to Team OKR**: "Acquire 30 profitable SMB customers"
- **OKR 1**: Close 4 SMB customers (20% of company target)
  - KR 1: Build SMB prospect list (200+ companies in target verticals)
  - KR 2: Achieve 15% outreach-to-meeting conversion (quality targeting)
  - KR 3: Close 4 customers at average $400 ARPU (profitable contribution margin)

### Step 5: Set Confidence Level & Scoring Criteria
For each OKR, assign:
- **Confidence Level**: Low (25-50%), Medium (50-75%), High (75-95%). If you're 95%+ confident, you're too conservative.
- **Scoring Criteria**: How you'll measure completion:
  - 100% = all KRs fully achieved
  - 70-90% = most KRs achieved, 1-2 missed
  - 40-70% = mixed results, some KRs achieved
  - 0-40% = insufficient progress, most KRs missed

Example scoring:
**OKR: Achieve <5% monthly churn**
- **Scoring**:
  - 100% = 4.5% or lower churn achieved
  - 70% = 5-6% churn achieved (close, but miss target)
  - 50% = 6-7% churn achieved (partial progress)
  - 0% = 7%+ churn (no progress)

### Step 6: Identify Dependency & Risks
Identify cross-team dependencies and risks to each OKR:

**OKR**: "Launch mobile app to enable field service adoption"
- **Dependency**: Design team must deliver mockups by week 2 (blocks engineering)
- **Risk**: If Design dept is overloaded, this slips to next quarter
- **Mitigation**: Allocate designer to this project exclusively Q1; defer lower-priority projects

### Step 7: Plan Check-in Cadence
- **Company OKRs**: Review every 4 weeks (30-min check-in) for progress and course correction
- **Team OKRs**: Review every 2 weeks (15-min sync) with your manager
- **Individual OKRs**: Review weekly (self-tracked) with team

At end of quarter, score all OKRs (0-100%) and hold **retrospective**: What did we learn? What should we do differently next quarter?

## Output Template

```markdown
# OKR Roadmap: {{Company Name}}
**Quarter**: {{Q1 2025}}
**Planning Date**: {{Date}}
**Review Frequency**: {{Weekly/Bi-weekly/Monthly}}
**Scoring Window**: {{End of Q1: March 31}}

---

## COMPANY-LEVEL OKRs

### Objective 1: {{Qualitative Outcome Statement}}
**Rationale**: {{Why this matters now. Market context, competitive position, business model shift}}
**Time Frame**: {{Quarter}}
**Confidence Level**: {{Low/Medium/High}} ({{}% confidence we'll achieve 100%)

#### Key Result 1: {{Measurable Target}}
- **Current State**: {{Baseline metric}}
- **Target**: {{Ambitious but achievable number}} ({{% improvement}})
- **Measurement**: {{How we'll measure (tool, frequency)}}
- **Owner**: {{Lead executive/team}}
- **Scoring Criteria**:
  - 100%: {{Full achievement}}
  - 70%: {{Partial achievement (e.g., {{number}}}} reached)
  - 50%: {{Half progress}}
  - 0%: {{No progress}}

#### Key Result 2: {{}}
- **Current State**: {{}}
- **Target**: {{}}
- **Measurement**: {{}}
- **Owner**: {{}}
- **Scoring Criteria**: {{}}

#### Key Result 3: {{}}

### Objective 2: {{}}
...

### Objective 3: {{}}
...

---

## TEAM-LEVEL OKRs

### Team: {{Team Name}} (Owner: {{Manager}})
**Contribution to Company OKRs**: {{Links to which company OKRs}}

#### Team OKR 1: {{Outcome}}
**Rationale**: {{How this team OKR supports company objective}}
**Confidence Level**: {{Low/Medium/High}}

- **Key Result 1**: {{Target}}
  - Current State: {{}}
  - Target: {{}}
  - Owner: {{Individual name}}
  - Measurement: {{How tracked}}

- **Key Result 2**: {{}}
  - Current State: {{}}
  - Target: {{}}
  - Owner: {{}}
  - Measurement: {{}}

#### Team OKR 2: {{}}

### Team: {{Next Team}}
**Contribution to Company OKRs**: {{}}
#### Team OKR 1: {{}}
...

---

## INDIVIDUAL OKRs (Optional)

### Individual: {{Name}} (Title: {{Title}}, Manager: {{Manager}})
**Role**: {{Describe role and primary responsibility}}

#### Individual OKR 1: {{Outcome Supporting Team OKR}}
- **Key Result 1**: {{Specific, measurable target}}
  - Current: {{}}
  - Target: {{}}
  - Measurement: {{}}

#### Individual OKR 2: {{}}

---

## CROSS-TEAM DEPENDENCIES & RISKS

| Company OKR | Team A Dependency | Team B Dependency | Risk | Mitigation |
|---|---|---|---|---|
| {{OKR 1}} | {{Team A task, due date}} | {{Team B task, due date}} | {{Risk if dependencies slip}} | {{Mitigation: hire, replan, etc.}} |
| {{OKR 2}} | {{}} | {{}} | {{}} | {{}} |

---

## SUCCESS METRICS & TRACKING

### Monthly Check-in Template (Every 4 weeks)
**Company Objective**: {{}}
- **KR 1 Progress**: {{Baseline}} → {{Current}} ({{% to target}})
- **KR 2 Progress**: {{}} → {{}} ({{%}})
- **Status**: {{On Track / At Risk / Off Track}}
- **Notes**: {{What's working, what's not, course corrections}}
- **Confidence**: {{Low/Medium/High}} (revised from start of quarter)

### Quarterly Scoring (End of Q)
**Objective 1**: {{Score}} / 100%
- KR 1: {{Achieved / Missed}} ({{Final metric}})
- KR 2: {{Achieved / Missed}}
- KR 3: {{Achieved / Missed}}
- **Overall Assessment**: {{What we learned, why we scored this}}

---

## QUARTERLY RETROSPECTIVE TEMPLATE

**Quarter Completed**: {{Q1}}
**Overall Company OKR Score**: {{Average % across all OKRs}}

### What Went Well
- {{OKR 1}}: Achieved {{%}}. Reasons: {{Execution excellence, team alignment, market tailwinds}}

### What Didn't Go Well
- {{OKR 2}}: Achieved {{%}}. Reasons: {{Underestimated effort, dependency slipped, market shifted}}

### Lessons for Next Quarter
- {{Lesson 1}}: {{What we should do differently}}
- {{Lesson 2}}: {{Process improvement}}

### Adjusted Priorities for Q{{Next}}
- {{Old priority}} deprioritized because {{}}
- {{New priority}} elevated because {{}}

---

## NEXT QUARTER PLANNING

**Q{{Next}} Themes**: {{Strategic focus areas based on retrospective}}

**Proposed Company OKRs for Q{{Next}}**:
1. {{}}
2. {{}}
3. {{}}

(Details will be fleshed out in Q{{Next}} planning session)
```

## Quality Gates
- [ ] Company OKRs are outcome-focused (not task-focused), memorable, and 3-5 in number
- [ ] Each objective has 2-4 Key Results, all quantified with measurable targets
- [ ] Key Results are ambitious (70-80% confidence of 100% achievement, not 95%+ conservative)
- [ ] Team OKRs cascade to company OKRs (clear connection to how team contributes)
- [ ] Each OKR has an owner and measurement methodology (tool, frequency, data source)
- [ ] Dependencies identified and risks documented with mitigation plans
- [ ] Scoring criteria defined for each KR (what 100%, 70%, 50%, 0% looks like)
- [ ] Check-in cadence established (company 4-weekly, team 2-weekly, individual weekly)

## Examples

### Good Output (excerpt)
```
Company Objective: "Establish product-market fit with SMB segment"
Rationale: We've validated demand (50+ pilot customers), but haven't proven repeatability or profitability. FY 2025 depends on landing 30+ profitable SMB customers and reducing churn from 8% to <5%.

Key Result 1: Achieve NPS ≥ 50 (from 42)
- Current State: NPS 42 (50 respondents, Q4 2024)
- Target: NPS 50+ by Q1 end
- Measurement: Monthly NPS survey (via Delighted), 50+ responses
- Scoring: 100% = NPS 50+, 70% = NPS 47-49, 50% = NPS 44-46, 0% = NPS <44

---

Team: Sales & Customer Success
Team OKR: "Acquire 30 profitable SMB customers"
Rationale: To hit company objective of product-market fit, we need 30 paying SMB customers at $250-500/month with contribution margin >70%.

Key Result 1: Close 20 customers at $250-500 ARPU
- Current: 8 customers, avg $180 ARPU (unprofitable at contribution margin)
- Target: 20 new customers, avg $350 ARPU (70%+ contribution margin)
- Measurement: CRM pipeline tracking, weekly reviews
- Owner: VP Sales

---

Individual: Mike (Enterprise AE, targeting SMB)
Individual OKR: "Close 4 SMB customers (20% of company target)"
- KR 1: Build SMB prospect list of 200+ companies in target verticals (logistics, field service, manufacturing)
- KR 2: Achieve 15% meeting conversion (outreach → meeting booked)
- KR 3: Close 4 customers at avg $350 ARPU

Scoring:
- 100%: 4 customers closed, avg $350+ ARPU
- 70%: 3 customers closed, avg $300+ ARPU
- 50%: 2 customers closed, avg $250+ ARPU
- 0%: <2 customers
```

### Bad Output (what to avoid)
```
Objective: "Grow revenue"
(Too vague, not outcome-focused, not memorable)

Key Result: "Increase sales team size"
(Task-focused, not outcome-focused; hiring is activity, revenue is outcome)

Key Result: "Improve customer satisfaction"
(Unmeasurable, subjective; NPS 55 is measurable)

Team OKR: "Ship new features"
(Activity, not outcome; what problem do they solve? What customer behavior changes?)
```

## Common Mistakes

1. **Confusing Tasks with Key Results**: "Ship mobile app by Q2" is a task (project milestone). KR is the outcome: "Enable 20% of new customers to onboard via mobile, reducing time-to-first-value 40%." Better: "40% of daily active users access product via mobile, with engagement parity to web." This is outcome-focused and measurable.

2. **OKRs That Are 95%+ Likely to Achieve (Too Conservative)**: If you're 95% confident you'll hit a KR, you've set the bar too low. OKRs should be ambitious: 70-80% confidence of 100% achievement. This means 20-30% of quarters you'll miss some OKRs—that's healthy. If you're hitting 100% every quarter, your OKRs are too easy.

3. **Cascading That Breaks Alignment**: Engineering sets "Ship 30 features" (task-focused), Sales sets "Close 50 deals" (activity-focused), neither directly supports company "Product-market fit with SMB." Better cascade: Company OKR (PMF with SMB) → Sales Team OKR (acquire 30 SMB customers) → Individual OKR (close 5 customers). Each level explicitly supports the next.

4. **Too Many OKRs (Loss of Focus)**: Company with 8 OKRs per quarter. Every team is pulled in different directions, priorities conflict, nothing gets finished. Healthy: 3-5 company OKRs, each team has 2-3 OKRs. Forced prioritization creates focus.

5. **No Check-in Cadence (Orphaned OKRs)**: OKRs set in January, never revisited until year-end. Reality: Market shifts, dependencies slip, priorities change. Establish check-in: Company 4-weekly (30 min), Teams 2-weekly (15 min). If an OKR goes off-track mid-quarter, course correct (reprioritize, add resources, adjust target).

## Anti-Patterns

1. **OKRs as Performance Reviews**: Managers use OKR achievement as sole input to raises/promotions. Problem: Discourages ambitious OKRs (people set safe ones). Solution: OKR achievement is 1 input to performance (not sole input). Separate: OKR execution (did we achieve business outcomes?) from performance evaluation (technical skills, teamwork, growth).

2. **Cascading Too Rigidly**: Company sets 5 OKRs, demands every team align to one. Problem: Some teams (finance, HR, ops) don't directly map to revenue OKRs. Solution: Not every team needs a cascade. Some teams have supporting OKRs (Finance: "Improve cash runway forecasting accuracy by 25%"). These aren't aligned to company revenue OKR, but they enable execution.

3. **Individual OKRs for Individual Contributors in Small Teams**: Small team (5 people), everyone has individual OKRs. Creates friction and confusion (am I responsible for my individual goals or team goals?). Solution: For teams <8, use team OKRs only. Individuals within team contribute to team OKR but own specific workstreams (not separate OKRs).

4. **No Contingency or Pivot Plan**: Q1 OKR: "Achieve NPS 50." At week 10, NPS is still 35 (no progress). Team keeps grinding. At Q-end, they miss OKR. Better: At week 4 check-in, diagnose: "NPS isn't moving because {{root cause}}. Do we (a) invest more in {{solution}} and revise target to 40, or (b) pivot strategy?" Make course correction early, don't wait until end of quarter.

5. **Scoring Inflation**: At end of Q, team reports "We achieved 85% on KR (target was 100, actual was 85)" and claims 85% success. But scoring should be binary or tiered (100% vs 70% vs 50% vs 0%). Better: "We achieved 85 vs target 100. At 85%, we didn't hit the threshold for 100% success, so we score this KR at 70%. Overall, we achieved 2.5 / 3 objectives (83%)." This prevents grade inflation.

