---
name: risk-register-generator
description: "Generate risk registers with identification, probability/impact scoring, mitigation strategies, ownership, and heat map visualization. Enables proactive risk management and informs strategic decisions."
category: business
difficulty: intermediate
model_boost: "Prevents unknown risks from becoming crises; produces instead identified, scored, and mitigated risks with clear ownership."
---

# Risk Register Generator

## Purpose
A risk register systematically identifies and tracks business risks. This skill generates registers that: identify risks (what could go wrong), score them (probability × impact), document mitigation strategies (what we'll do), assign ownership (who watches it), and create heat maps (visual priority). Output enables: early warning systems, proactive mitigation, board-ready risk disclosures, and disciplined decision-making under uncertainty.

## When to Use
- Starting a high-stakes project (product launch, fundraising, M&A, market entry)
- Annual strategic planning (what could derail our plan?)
- Identifying blind spots (what aren't we thinking about?)
- Board reporting (what risks keep management up at night?)
- **Do NOT use when**: Risk landscape is stable (low-risk business); risks are actively happening (in crisis mode); organization is immature (first focus on vision, then risks).

## Instructions

### Step 1: Brainstorm Risks (Structured & Unstructured)
Generate potential risks. Use categories to ensure coverage:

**Brainstorming Categories**:
- **Market Risks**: Demand doesn't materialize, competitors emerge, market shifts
- **Customer Risks**: Customer concentration (top 3 customers = {{%}} of revenue), churn rises, customer loses funding
- **Product Risks**: Technical debt, features don't sell, security/privacy breaches
- **Team Risks**: Key person departure, skill gaps, team conflicts
- **Financial Risks**: Burn rate too high, funding dries up, unit economics break
- **Operational Risks**: Process failures, system downtime, compliance violations
- **Competitive Risks**: Incumbent enters, price war, technology disruption
- **External Risks**: Recession, regulatory change, supply chain disruption

Generate 20-30 risks. Don't filter yet.

### Step 2: Score Each Risk (Probability & Impact)
Not all risks are equal. Score:

**Probability** (likelihood it will occur):
- 1 (Low): <10% chance
- 2 (Medium): 10-50% chance
- 3 (High): >50% chance

**Impact** (severity if it occurs):
- 1 (Low): Manageable, minor business impact
- 2 (Medium): Notable impact, requires response
- 3 (High): Severe impact, could threaten business viability

**Risk Score**: Probability × Impact (range 1-9)
- Score 9 (3×3): Kill-or-be-killed risk (highest priority)
- Score 6 (2×3 or 3×2): Major risk, needs active mitigation
- Score 4 (2×2): Moderate risk, monitor & plan mitigation
- Score 1-2: Low risk, acknowledge but don't obsess

### Step 3: Identify Mitigation Strategies
For each significant risk, define what you'll do to reduce probability or impact.

**Mitigation Types**:
- **Reduce Probability**: Action to make risk less likely (hire expert, build backup plan, validate assumption)
- **Reduce Impact**: Action to limit damage if risk occurs (contract with backup vendor, diversify customer base, build reserve)
- **Transfer Risk**: Pass risk to someone else (insurance, vendor contracts with SLAs)
- **Accept Risk**: Acknowledge risk, don't mitigate (conscious trade-off)

**Example**:
**Risk**: "Key technical person leaves, taking institutional knowledge"
- **Reduce Probability**: Hire 2nd person with similar skills (by Q2); improve documentation (Q1)
- **Reduce Impact**: Cross-train {{person 2}} on critical systems (ongoing); document key processes (Q1)
- **Transfer**: Buy key-person insurance (if company is {{$}} revenue)
- **Accept**: Acknowledge risk if mitigation cost is too high

### Step 4: Assign Ownership & Monitoring
Each risk needs an owner who tracks it.

**Risk Owner**: Role responsible for monitoring and escalating
- Typically senior person (VP or C-level) for high-impact risks
- Team lead for operational risks
- Has authority to escalate if risk materializes

**Monitoring Metric**: How do you know if the risk is happening?
- Example: "Customer concentration risk" → Monitor if any customer is {{%}} of revenue (monthly); escalate if {{threshold}} hit

**Escalation Path**: If risk triggers, who do you tell?
- Example: If {{key person}} gives notice, immediately escalate to CEO & Board

### Step 5: Create Heat Map Visualization
Plot risks on a Probability vs. Impact matrix. Visualizes priority.

**Heat Map** (3×3 Grid):
```
Impact
  High   | 3,1 (Red) | 3,2 (Red) | 3,3 (Red)
         | Monitor   | Mitigate  | Kill-or-be-Killed
  Medium | 2,1 (Yel) | 2,2 (Yel) | 2,3 (Red)
         | Monitor   | Monitor   | Mitigate
  Low    | 1,1 (Grn) | 1,2 (Grn) | 1,3 (Yel)
         | Monitor   | Monitor   | Monitor
         └─────────────────────────────────
           Low      Medium      High
                  Probability
```

**Risk Color Coding**:
- **Red (9, 8, 6)**: Active mitigation required; board visibility
- **Yellow (4, 3)**: Monitor closely; plan mitigation
- **Green (2, 1)**: Acknowledge; review annually

### Step 6: Plan Mitigation Timeline
When will you implement mitigation? Map to company milestones or quarters.

**Example**:
- **Q1**: Hire 2nd technical person (reduce key-person risk)
- **Q2**: Secure Series B (reduce funding risk)
- **Q3**: Launch customer success program (reduce churn risk)

Sequence matters. Some risks must be mitigated before others can be addressed.

### Step 7: Establish Monitoring & Review Cadence
How often do you check on risks?

**Cadence** (suggested):
- **Weekly**: High-probability risks (3×3, 3×2, 2×3) — flag immediately if triggered
- **Monthly**: Medium risks (2×2, 2×1, 1×3) — review in operations meeting
- **Quarterly**: Low risks (1×1, 1×2, 3×1) — review in strategy meeting

**Trigger** (escalate immediately if):
- High-risk mitigation deadline missed
- Risk probability increases (from Low to Medium, Medium to High)
- Risk impact assessment changes (new data shows impact is higher)
- Similar risk materializes at competitor (early warning)

### Step 8: Document Contingency Plans
If risk materializes, what's the backup plan?

**Contingency Example**:
**Risk**: "Customer churn spikes >10% monthly"
- **Detection**: Monthly churn report shows {{metric}} exceeded
- **Immediate Response** (Days 1-3):
  - {{Customer Success}} contacts {{# at-risk}} customers with [[issue]] (we know why churn rising)
  - Offer [[compensation or feature]] to high-value customers to reduce churn
- **Mid-term Response** (Weeks 2-4):
  - {{Product team}} fast-tracks {{feature}} causing churn
  - {{Sales}} pauses new customer acquisition (focus on retention)
- **Long-term Response** (Months 2+):
  - Fix underlying issue (product or pricing)
  - Rebuild customer confidence

## Output Template

```markdown
# RISK REGISTER: {{Company/Project Name}}
**As of**: {{Date}}
**Last Updated**: {{Date}}
**Review Cycle**: {{Monthly / Quarterly}}
**Owner/Champion**: {{Title (e.g., CFO, Project Manager)}}
**Board Update**: {{Link to board materials or date of last presentation}}

---

## EXECUTIVE SUMMARY

**Total Risks Identified**: {{#}}
- **Red Risks** (3×3, need active mitigation): {{#}}
- **Yellow Risks** (2×2 to 3×2, monitor closely): {{#}}
- **Green Risks** (1×1 to 2×1, acknowledge): {{#}}

**Key Risks This Period**:
1. {{Highest-impact risk}}: Probability {{P}}, Impact {{I}}, Score {{P×I}}. Mitigation: {{}}
2. {{Next highest}}: {{}}
3. {{}}

**Change from Last Period**:
- {{Risk 1}} probability {{increased/decreased}} from {{}} to {{}} → {{reason}}
- {{New risk emerged}}: {{}}
- {{Risk mitigated}} → moved from {{status}} to {{new status}}

---

## RISK SCORING LEGEND

| Score | Color | Interpretation | Action |
|---|---|---|---|
| **9** (3×3) | Red | Kill-or-be-killed risk | Active mitigation required; weekly review |
| **8** (3×2, 2×3) | Red | Severe risk | Active mitigation; bi-weekly review |
| **6** (3×1, 2×2, 1×3) | Yellow | Major risk | Plan mitigation; monthly review |
| **4** (2×2, 1×2) | Yellow | Moderate risk | Monitor; escalate if probability rises |
| **2-3** (1×1, 1×2, 2×1) | Green | Low risk | Acknowledge; annual review |

---

## RISK REGISTER (Sorted by Score: Highest First)

### RISK 1: {{Risk Name}} [SCORE: 9]
**Category**: {{Market / Product / Team / Financial / Competitive}}

**Description**: {{What could go wrong? Context.}}
- Current State: {{What's the situation now?}}
- Trigger: {{What would cause this risk to materialize?}}

**Probability**: 3 (High, >50% chance) {{Reasoning: {{}}}}
**Impact**: 3 (High, threat to business viability) {{Reasoning: {{}}}}
**Score**: 9 (3×3) — {{Kill-or-be-killed}}

**Risk Owner**: {{Role/Name}} (owns monitoring and escalation)
**Stakeholders Affected**: {{Who is impacted if this materializes?}}

#### Mitigation Strategy
**Goal**: {{Reduce {{probability / impact}} to {{target score}}}}

**Actions** (to reduce probability):
1. {{Action to reduce likelihood}}: {{Owner}}, due {{date}}, measures {{metric}}
2. {{Action}}: {{}}

**Actions** (to reduce impact):
1. {{Action to limit damage}}: {{Owner}}, due {{date}}, measures {{metric}}
2. {{Action}}: {{}}

**Timeline**: {{When will mitigation be complete?}}

**Success Metric**: {{How will we know risk probability/impact is lower?}}
- {{Metric 1}}: {{Target}}
- {{Metric 2}}: {{Target}}

#### Monitoring
**Monitor Frequency**: {{Weekly / Bi-weekly}} (high-risk cadence)

**Monitoring Metric**: {{Early warning signal}}
- {{If {{metric]] {{exceeds}} {{threshold}}, escalate immediately}}
- Example: "If {{metric]] hits {{value}}, we have {{# days}} to respond"

**Escalation Path**: {{If risk triggers}}
1. {{Risk Owner]] alerts {{manager / CEO / Board]]
2. Convene {{crisis team]] ({{roles]])
3. Execute contingency plan (see below)

#### Contingency Plan (If Risk Materializes)
**Detection**: {{How we know risk has occurred}}

**Immediate Response** (Days 1-3):
1. {{Action}}
2. {{Action}}

**Short-term Response** (Weeks 2-4):
1. {{Action}}
2. {{Action}}

**Long-term Response** (Months 2+):
1. {{Action}}
2. {{Action}}

**Communication**:
- {{Stakeholder 1}} will be informed: {{method}}, {{timeline}}
- {{Stakeholder 2}}: {{}}

---

### RISK 2: {{Risk Name}} [SCORE: 8]
[Same structure as above]

---

### RISK 3: {{Risk Name}} [SCORE: 6]
[Abbreviated: focus on top {{N}} risks; others summarized]

---

## RISK HEAT MAP (Visual)

```
Impact (Severity)
     3 (High)  | Risk 1 (9)     | Risk 2 (8)     | Risk 3 (8)
               | [Red - Severe] | [Red - Severe] | [Red - Severe]
               |
     2 (Medium)| Risk 5 (6)     | Risk 4 (4)     | Risk 6 (6)
               | [Yellow-Major] | [Yellow-Mod]   | [Yellow-Major]
               |
     1 (Low)   | Risk 8 (1)     | Risk 9 (2)     | Risk 7 (3)
               | [Green-Monitor]| [Green-Monitor]| [Yellow-Minor]
               |
                 1 (Low)        2 (Medium)      3 (High)
                 Probability (Likelihood)
```

**Interpretation**:
- {{Upper right (high prob, high impact)}}: Kill-or-be-killed → red
- {{Top left or bottom right}}: Major but manageable → yellow
- {{Bottom left}}: Low risk → green

---

## RISK TREND ANALYSIS

**Period**: {{Last 12 months}}

| Risk | {{Q1 Score}} | {{Q2 Score}} | {{Q3 Score}} | {{Q4 Score}} | Trend | Driver |
|---|---|---|---|---|---|---|
| {{Risk 1}} | {{}} | {{}} | {{}} | {{}} | {{↑ Increasing}} | {{Competitor entered market}} |
| {{Risk 2}} | {{}} | {{}} | {{}} | {{}} | {{↓ Decreasing}} | {{Series B funding secured}} |
| {{Risk 3}} | {{}} | {{}} | {{}} | {{}} | {{→ Stable}} | {{}} |

**Key Observations**:
- {{Risk 1 increasing}}: Competitive threat emerging; mitigation accelerating
- {{Risk 2 decreasing}}: Funding secured; financial risk reduced
- {{New risk this quarter}}: {{Risk X}} ({{reason}})
- {{Risk resolved}}: {{Risk Y}} ({{mitigation successful}})

---

## DEPENDENCY MAP (How Risks Interact)

**Risk Chains** (if one happens, it triggers others):
- If {{Risk 1}} ({{key person leaves}}) happens → {{Risk 3}} (product delays) likely → {{Risk 4}} (customer churn) likely
- If {{Risk 2}} (funding dries up) happens → {{Risk 5}} (team downsizing) likely

**Interdependencies**:
- {{Risk A}} and {{Risk B}} both require {{mitigation action X}} → sequence matters
- {{Risk C}} mitigation would reduce {{Risk D}} probability → synergies

---

## MITIGATION ROADMAP (By Quarter)

| Quarter | Risk Addressed | Mitigation Action | Owner | Success Metric | Status |
|---|---|---|---|---|---|
| **Q1** | {{Risk 1}} | {{Hire 2nd technical person}} | {{VP Eng}} | {{Person hired and ramped}} | In Progress |
| **Q1** | {{Risk 2}} | {{Secure Series B commitment}} | {{CEO}} | {{${{}} raised}} | In Progress |
| **Q2** | {{Risk 3}} | {{Build feature X}} | {{Product}} | {{NPS improves}} | Planned |
| **Q3** | {{Risk 4}} | {{Launch customer success program}} | {{VP CS}} | {{Churn improves}} | Planned |
| **Q4** | {{Risk 5}} | {{Diversify customer base}} | {{Sales}} | {{{{%}} from top customer}} | Planned |

---

## RISK MONITORING DASHBOARD

**Metrics Tracked (Real-time or Weekly)**:

| Risk | Monitor Metric | Current Value | Target / Threshold | Status | Alert |
|---|---|---|---|---|---|
| {{Key person risk}} | {{# technical people}} | {{1}} | {{≥2}} | ⚠️ At Risk | If {{value}}, hire immediately |
| {{Customer concentration}} | {{Top customer {{%}} of revenue}} | {{{{%}}}} | {{<{{%}}}}}} | ✓ On Track | If {{{{%}}}} → diversify |
| {{Product risk}} | {{NPS}} | {{{{}}}} | {{>45}} | ⚠️ At Risk | If <40, prioritize features |
| {{Funding risk}} | {{Cash runway}} | {{{{}} months}} | {{>12 months}} | ✓ On Track | If <6 months, raise capital |
| {{Churn risk}} | {{Monthly churn {{%}}}} | {{{{%}}}} | {{<5%}} | ⚠️ Elevated | If {{{{%}}}}, exec review |

**Dashboard Link**: {{Link to live dashboard or spreadsheet}}

---

## BOARD/STAKEHOLDER COMMUNICATION

### Board Risk Summary (For Board Meetings)
**Top 3 Risks This Period**:
1. {{Risk 1}} (Score 9): {{1-sentence summary}}. Mitigation: {{}}. Status: {{}}
2. {{Risk 2}} (Score 8): {{}}. Mitigation: {{}}. Status: {{}}
3. {{Risk 3}} (Score 6): {{}}. Mitigation: {{}}. Status: {{}}

**Risks Resolved This Period**: {{Risk X}} (resolved via {{mitigation}}). Previous score {{}} → {{}}

**New Risks Emerged**: {{Risk Y}} (new), score {{}}. Mitigation: {{}}

### Key Decisions Informed by Risk Register
- **Decision 1**: {{We decided to {{action]] because {{risk]] posed {{threat]]. This {{reduces / transfers]] risk.}}
- **Decision 2**: {{}}

---

## PROCESS & GOVERNANCE

### How Risks Are Identified & Added
- {{Monthly risk brainstorm}} with {{team / exec team}})
- {{New risks from {{customer feedback / competitive intel / incident]]}}: {{process to flag}}
- {{Risks re-scored }} if {{conditions change]]

### Risk Review Schedule
- **Weekly**: High-risk (${{9, 8, 6}}) monitoring
- **Monthly**: All risks reviewed in {{meeting name / team}}
- **Quarterly**: Risk register updated and presented to {{Board / Leadership}}
- **Annually**: Full risk refresh (new brainstorm, re-scoring)

### Risk Ownership & Escalation
- **Risk Owner**: {{Role}} monitors and escalates if {{threshold}} hit
- **Escalation**: {{Risk Owner}} → {{Manager}} → {{VP}} → {{CEO}} → {{Board}} (as needed)
- **Urgency**: {{#}} days to escalate if threshold hit

---

## APPENDIX

### A. Risk Assessment Methodology
- {{Probability scoring rationale}} (why we estimate {{}} for {{Risk]]))
- {{Impact scoring rationale}}
- {{Historical data or benchmarks}} used

### B. Incident Log (Historical)
{{Risks that materialized in past, mitigation taken, outcome}}
- {{Risk X]}: Occurred {{date}}, cost ${{}} to remediate
- {{Risk Y]}: Near-miss {{date}}, triggered mitigation {{action}}

### C. Risk Scenarios (Stress Testing)
{{What-if analysis: if {{worst-case risk]] occurs, what happens?}}
- Scenario: Competitor enters with 50% lower pricing
- Financial impact: {{%}} customer loss, {{$}} revenue impact
- Mitigation: {{}}

---

**Document Owner**: {{Role/Name}}
**Last Review**: {{Date}}
**Next Review**: {{Date}}
**Contact for Questions**: {{Email / Phone}}
```

## Quality Gates
- [ ] 15-30 risks identified across categories (market, product, team, financial, competitive, operational)
- [ ] Each risk scored on Probability (1-3) and Impact (1-3) with reasoning
- [ ] High-impact risks (score 6+) have detailed mitigation strategies with owners and timelines
- [ ] Risk owners assigned (not diffused), with monitoring metrics and escalation paths
- [ ] Heat map visualizes priority and risk concentration
- [ ] Contingency plans documented for top 3-5 risks
- [ ] Monitoring cadence defined (weekly for red, monthly for yellow, quarterly for green)
- [ ] Risk trend analysis shows how risks are evolving over time
- [ ] Mitigation roadmap sequenced by quarter and ties to business milestones
- [ ] Board summary communicates top 3 risks and mitigation status

## Examples

### Good Output (excerpt)
```
RISK 1: Key Technical Person Leaves [SCORE: 9]
Category: Team

Description: Our CTO holds critical architectural knowledge. If he leaves, we lose 6+ months of onboarding new lead engineer. Product roadmap stalls. Customers churn due to bugs/slow feature velocity.

Probability: 3 (High, >50%)
- Reasoning: He's expressed frustration with fundraising distractions. Tech talent market is hot; poachers approach regularly. No non-compete/retention agreement.

Impact: 3 (High, threat to business viability)
- Reasoning: Product is complex. No 2nd person understands all systems. 6-month ramp-up for new lead would halt roadmap. Likely 20-30% customer churn.

Risk Owner: VP Engineering (daily oversight) → CEO (escalation)

Mitigation Actions:
1. Hire 2nd technical co-founder by Q1 (by Jan 31) — VP Eng owns
   - Success metric: 2nd engineer hired, ramped on critical systems by March
2. Improve documentation of critical systems by Q1 (bi-weekly sessions, 2hrs each)
   - Success metric: Top 5 systems fully documented
3. Offer retention bonus (${{amount}}) + equity refresh ({{#}} options)
   - Success metric: Letter of commitment signed

Monitoring:
- Weekly 1:1 with CTO (check satisfaction, listen for flight risk)
- Monthly: Interview CTO's direct reports (any issues?)
- If he signals departure: Execute {{emergency plan}} ({{ external founder search}}, {{ interim contract CTO}})

---

RISK 2: Customer Concentration [SCORE: 8]
Category: Market

Description: Top 3 customers represent {{%}} of revenue. If any churn, revenue drops {{%}}. Creates single points of failure.

Probability: 2 (Medium, 10-50% chance)
- Reasoning: {{Customer A}} is 6 months post-contract. {{Customer B}} is long-term. {{Customer C}} is at-risk (product gaps).

Impact: 3 (High, threatens business viability if {{Customer A}} or {{Customer B]] churn)

Mitigation:
1. Reduce customer concentration: {{Customer A}} is {{%}} of revenue; target is <{{%}}. Sales team focuses on new customer acquisition (Q1-Q4).
   - Success metric: New customers = {{50%}} of revenue by EOY
2. Increase {{Customer C}} retention: {{Feature X}} (their key request) by Q2.
   - Success metric: {{Customer C}} renews at end of contract

Monitoring:
- Monthly: {{Customer A}} health check (NPS, usage, support cases)
- If churn risk rises: CEO calls {{Customer A}} CFO directly
```

### Bad Output (what to avoid)
```
Risks:
- Market risk
- Product risk
- Team risk
- Competition

(Why this fails: No specific risks identified, no probability/impact scoring, no mitigation, no ownership, no actionability)
```

## Common Mistakes

1. **Risk Register Created Once, Never Updated**: Risk register created in Q1, not touched until next year. Market changed, new risks emerged, mitigation status unknown. Better: Monthly review. Update scores if probability/impact changes. Add new risks immediately.

2. **All Risks Treated Equally**: 30 risks listed, all at "Red" priority. Leadership doesn't know what to focus on. Better: Strict scoring. Focus mitigation on score 9 risks. Monitor score 6 risks. Acknowledge but defer score 2 risks.

3. **Mitigation Actions Vague**: "Reduce customer concentration risk" with no specific action or timeline. Still concentrated. Better: "Hire 2 sales reps by Q2. Target {{# new customers}} by Q3. {{%}} from top customer should drop from {{%}} to {{%}} by EOY."

4. **No Monitoring Metric**: Risk is identified but no signal to know if it's happening. CEO finds out when it's already a crisis. Better: "If {{metric]] hits {{threshold]], escalate immediately." Example: "If any customer is >{{%}} of revenue, red alert."

5. **Risks Not Linked to Decisions**: Risk register sits on shelf. Strategic decisions made without reference to risks. "We'll enter market X" without assessing risks. Better: "Market entry risk is {{score}}. Mitigation: {{}}. We're proceeding because {{}} outweighs risk."

## Anti-Patterns

1. **Risk Register as "CYA" Document**: Created for board, never used internally. Team doesn't know risks exist. Better: Live document. Used weekly for monitoring and decisions.

2. **Probability/Impact Inflation**: Every risk scored 9 to "get funding." Investors see risk register full of "kill-or-be-killed" risks; credibility lost. Better: Honest scoring. High scores are credible.

3. **No Contingency Plans**: Risk identified, mitigation planned, but "if it happens" is blank. Crisis occurs; team scrambles (preventable). Better: Think through contingency: "If {{key person]] leaves, we immediately contract {{interim CTO}} while searching for permanent hire."

4. **Dependency Risks Ignored**: Risk A and Risk B are connected, but register treats them separately. When A happens, B cascades. Better: Map dependencies. "If {{Risk A]] happens, {{Risk B]] becomes 10x more likely."

5. **Risk Ownership Too Diffuse**: Risk owned by "everyone" or "leadership." Nobody specifically watches it. Better: Single owner. "VP Eng owns customer concentration risk. Monthly report to CEO."

