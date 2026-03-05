---
name: project-charter-generator
description: "Generate PMI-aligned project charters with scope, objectives, stakeholder map, milestones, success criteria, RACI matrix, and risk profile. Prevents scope creep and ensures stakeholder alignment."
category: business
difficulty: intermediate
model_boost: "Prevents project sprawl and vague stakeholder expectations; produces instead focused, bounded projects with clear authority and escalation paths."
---

# Project Charter Generator

## Purpose
A project charter is the project's foundational document, establishing authority, scope, success criteria, stakeholders, and governance. This skill generates charters aligned to PMI standards (Project Management Institute), including: problem statement, objectives, scope boundaries, stakeholder identification, RACI matrix (Responsible, Accountable, Consulted, Informed), milestones, success criteria, constraints, and risk profile. Output prevents scope creep, clarifies who decides what, and ensures stakeholder alignment before project launch.

## When to Use
- Starting a significant project (cross-functional, multi-quarter, or high-stakes)
- Projects with multiple stakeholders and unclear authority (prevents conflict)
- Preventing scope creep (charter defines boundaries upfront)
- Resource-intensive initiatives requiring explicit approval
- **Do NOT use when**: Project is small (<2 weeks, single-person); project scope is unstable (do discovery first); stakeholders are aligned and scope is clear (light checklist may suffice).

## Instructions

### Step 1: Define Business Case & Problem Statement
Articulate the business problem driving the project. This is the "why"—the gap between current state and desired state.

**Strong Business Case**:
- Current State: "We process customer invoices manually in 4 different systems. It takes Finance 60 hours/month."
- Desired State: "Automate invoice processing end-to-end. Reduce manual effort to 8 hours/month."
- Cost of Inaction: "$4,800/month in excess labor costs. 3-week cash position visibility delay = $50K float annually."
- Business Driver: "Scaling to 500 SMB customers requires 3-4x invoice volume. Manual process won't scale; need automation."

Without clear business case, project loses focus and executive support.

### Step 2: Identify Project Stakeholders & RACI Matrix
Stakeholder Map: Who is impacted? Who influences success? Who has authority?

Create RACI Matrix:
- **R**esponsible: Who does the work (often multiple)
- **A**ccountable: Who owns the outcome (1 person)
- **C**onsulted: Who is asked for input before decision (bidirectional communication)
- **I**nformed: Who is kept in loop after decision (one-way update)

Example (Invoice Automation Project):
| Role | Responsible | Accountable | Consulted | Informed |
|---|---|---|---|---|
| Finance Lead | | A | C | |
| Engineering Lead | R | | C | |
| VP Operations | | A | C | |
| CTO | | | C | |
| Customer (pilot) | | | C | I |
| Board | | | C | I |

Only 1 Accountable per decision area (prevents diffusion of responsibility).

### Step 3: Define Project Objectives & Scope
**Objectives** are what the project achieves (measurable outcomes). **Scope** is the work included and explicitly excluded.

**Good Objectives**:
- Reduce invoice processing time from 60 hours to 8 hours/month
- Automate data extraction from 95% of invoice formats
- Enable real-time cash position visibility

**Scope In**:
- Vendor invoice processing (AP flow)
- Integration with existing ERP (SAP)
- Multi-format support (PDF, email, portal)

**Scope Out**:
- Customer invoice generation (separate AR project)
- Mobile approval workflow (Phase 2)
- Custom workflow logic (will be configurable but not bespoke)

Clear out-of-scope prevents "scope creep" (stakeholders adding requirements mid-project).

### Step 4: Set Success Criteria & Measurable Benefits
Success criteria quantify whether the project achieved objectives.

**Quantitative Criteria**:
- Processing time: 60 hours → 8 hours/month (87% reduction)
- Data extraction accuracy: 95%+
- System uptime: 99.9%
- User adoption: 90% of Finance team using system by week 4

**Qualitative Criteria**:
- Finance team satisfaction: NPS ≥ 40
- Executive stakeholder alignment: Unanimous approval of outcomes

**Business Benefits**:
- Cost savings: $4,800/month labor freed up
- Time-to-insight: Cash position visibility improves from +21 days to +3 days
- Scalability: System supports 5x customer growth without manual scaling

### Step 5: Create Timeline & Milestones
Milestones are major checkpoints (not daily tasks). Typically 4-8 per project.

**Example (12-week project)**:
- **Week 0**: Charter approval, team kickoff
- **Week 2**: Requirements finalized, vendor selected, team onboarded
- **Week 4**: Technical design approved, data migration plan locked
- **Week 8**: MVP deployed, pilot Finance team testing
- **Week 10**: Bugs fixed, documentation complete
- **Week 12**: Full rollout, post-launch support

Each milestone should have:
- Acceptance criteria (what "done" means)
- Owner (who is accountable for hitting it)
- Risk (what could slip this milestone?)

### Step 6: Identify Constraints & Assumptions
**Constraints** are external limits. **Assumptions** are beliefs we're betting on.

**Constraints**:
- Budget: $300K maximum
- Timeline: Must launch by {{Date}} (business requirement)
- Team: Only 2 engineers available (others on other projects)
- Vendor lock-in: Committed to {{Vendor}} for 3 years

**Assumptions**:
- Finance team will dedicate 20 hours/week for requirements & testing
- Current invoice volume is {{X}}, won't exceed {{Y}} during project
- Vendor will provide integration by {{Date}}
- Existing ERP APIs are documented and stable

Flag assumptions as risks if they're uncertain. "Assumption: Vendor delivers on schedule. If not, project slips 4 weeks."

### Step 7: Identify Risks & Mitigation
List top 5-10 project risks. Assess probability (low/med/high) and impact if realized.

**Risk Example**: "Finance team unavailable for testing during Q4 budget close"
- Probability: Medium (historically challenging)
- Impact: High (requires feedback loop; without it, system misses requirements)
- Mitigation: Schedule testing for post-budget-close; hire QA contractor for interim testing

### Step 8: Define Governance & Escalation
Who decides what? What's escalated when?

**Governance**:
- **Project Steering Committee** (monthly, 30 min): VP Operations, CTO, Finance Lead. Approves major changes, budget, timeline.
- **Technical Working Group** (weekly, 1 hr): Engineering, Finance tech lead, IT. Resolves technical decisions, integration issues.
- **Change Control Board**: Any scope change >5 days of effort requires steering committee approval.

**Escalation Path**:
- Engineering can approve technical decisions <2 days effort
- VP Operations approves process changes >10 hours/week impact on Finance
- CTO approves any architecture changes or vendor commitments

Clear governance prevents: "Whose decision is it?" and unilateral scope changes.

### Step 9: Resource Plan & Budget
Specify team, skills, and budget required.

**Team**:
- Project Manager (1 FTE, 12 weeks): ${{}}
- Technical Lead / Engineering (1 FTE, 12 weeks): ${{}}
- Finance SME (0.5 FTE, 12 weeks): ${{}}
- QA / Testing (0.3 FTE, 12 weeks): ${{}}
- Vendor / External (consulting): ${{}}

**Budget**: ${{Total}}, allocated: {{%}} labor, {{%}} vendor, {{%}} tools, {{%}} contingency

### Step 10: Define Communication & Approval
Who communicates what to whom, and how often?

**Cadence**:
- **Steering Committee**: Monthly, written report pre-meeting
- **Project team**: Weekly syncs (standups) + bi-weekly retrospectives
- **Stakeholder updates**: Monthly all-hands update (5 min)
- **Executive summary**: Monthly {{}} format (1 page)

**Approval Gate**: Charter approved by {{Authority}} before project kickoff.

## Output Template

```markdown
# PROJECT CHARTER: {{Project Name}}
**Project Code**: {{PC-###}}
**Status**: {{Draft / Approved}}
**Approved By**: {{Executive Sponsor}}
**Approval Date**: {{Date}}
**Expected Completion**: {{Date}}

---

## BUSINESS CASE

### Problem Statement
{{Current state description}}: {{What's broken, painful, or inefficient}}
- {{Specific impact metric 1}}: {{$amount or % impact}}
- {{Specific impact metric 2}}: {{}}

{{Cost of inaction}}: {{If we don't fix this, {{risk/cost}} will occur}}

### Desired State
{{Envisioned future state after project}}: {{What success looks like}}
- {{Metric 1}}: {{Target}}, from {{current}} ({{% improvement}})
- {{Metric 2}}: {{}}

### Business Driver
{{Why now? What changed?}}
- {{Market shift, customer request, competitive threat, scaling need}}

---

## PROJECT OBJECTIVES & SCOPE

### Objectives (What We're Achieving)
1. {{Measurable outcome 1}}
2. {{Measurable outcome 2}}
3. {{Measurable outcome 3}}

### Scope: IN
- {{Deliverable 1}}: {{Description}} ({{Owner}})
- {{Deliverable 2}}: {{}}

### Scope: OUT (Explicitly Excluded)
- {{Out of scope 1}}: {{Why (e.g., Phase 2, not aligned to primary objective)}}
- {{Out of scope 2}}: {{}}

**Scope Creep Prevention**: Any {{deliverable}} request must be approved by {{Steering Committee}} and assessed for impact on timeline/budget.

---

## SUCCESS CRITERIA & BENEFITS

### Quantitative Success Criteria
| Metric | Current | Target | Measurement Method |
|---|---|---|---|
| {{Metric 1}} | {{Baseline}} | {{Target}} | {{How measured}} |
| {{Metric 2}} | {{}} | {{}} | {{}} |

### Qualitative Success Criteria
- {{Stakeholder satisfaction}}: {{Target}} (measured via {{survey/feedback}})
- {{Process adoption}}: {{Target}} (measured via {{usage metrics}})

### Business Benefits
- **Cost Reduction**: ${{amount}} annually ({{how achieved}})
- **Time Savings**: {{hours}} hours/month freed up ({{what can be done with time}})
- **Quality/Accuracy**: {{% improvement}} ({{measurement}})
- **Scalability**: System supports {{# of X}} (enables {{growth}})

---

## STAKEHOLDER MAP & RACI MATRIX

### Stakeholder List
| Role | Name | Influence (High/Med/Low) | Interest (High/Med/Low) | Primary Concern |
|---|---|---|---|---|
| {{Role 1}} | {{Name}} | High | High | {{What matters to them}} |
| {{Role 2}} | {{Name}} | High | Med | {{}} |

### RACI Matrix (Decision/Work Area)

| Role / Activity | Requirement Gathering | Technical Design | Testing & QA | Rollout | Post-Launch Support |
|---|---|---|---|---|---|
| **Project Manager** | A,C | C | C | A,R | A,I |
| **Engineering Lead** | C | A,R | C | R | I |
| **Finance SME** | R,A | C | R | C | R |
| **VP Operations** | C | C | C | A | C |
| **CTO** | C | C | C | I | I |

**Legend**: A = Accountable (1 only, owns outcome), R = Responsible (does work), C = Consulted (ask for input), I = Informed (kept in loop)

---

## TIMELINE & MILESTONES

### Gantt Summary (High Level)
```
Phase 1: Design (Wk 0-2)
Phase 2: Build (Wk 3-8)
Phase 3: Test (Wk 6-10)
Phase 4: Rollout (Wk 11-12)
```

### Key Milestones

| Milestone | Target Date | Owner | Acceptance Criteria | Risk/Dependencies |
|---|---|---|---|---|
| **Charter Approval** | {{Date}} | {{Name}} | {{Authority}} signs off | {{}} |
| **Requirements Locked** | {{Date}} | {{PM, Finance SME}} | {{# of req}}, all stakeholders sign-off | Finance availability |
| **Technical Design Review** | {{Date}} | {{Tech Lead}} | {{CTO approval}}, {{design doc}} | {{}} |
| **MVP Build Complete** | {{Date}} | {{Eng Lead}} | {{Feature set}}, code review passed | {{}} |
| **Pilot Testing Start** | {{Date}} | {{QA Lead}} | {{Test plan}}, 3 Finance users trained | {{}} |
| **Go/No-Go Decision** | {{Date}} | {{VP Ops}} | {{Metrics hit 90%+}} | {{}} |
| **Full Rollout** | {{Date}} | {{PM}} | {{100% of Finance using}}, {{target metric}} hit | {{}} |

---

## CONSTRAINTS & ASSUMPTIONS

### Hard Constraints
- **Budget**: ${{amount}} (cannot exceed without {{Authority}} approval)
- **Timeline**: Must launch by {{Date}} (business critical: {{reason}})
- **Team Availability**: {{# engineers}} available (others on {{project}})
- **Vendor Commitment**: Locked into {{Vendor}} contract through {{Date}}
- **Technology**: Must integrate with {{existing system}} (no rip-and-replace)

### Assumptions
| Assumption | Risk if Wrong | Mitigation |
|---|---|---|
| Finance will dedicate 20 hrs/week | Project delays 4 weeks | Have QA contractor ready for interim testing |
| Invoice volume < {{#}}/month during project | Performance issues, rework | Monitor volume weekly; alert if trending >{{threshold}} |
| Vendor delivers {{integration}} on schedule | Project delays 3 weeks | Build contract penalty clause; identify alternative vendor |
| Current ERP APIs are documented | Integration takes 2x longer | Allocate 2 weeks for API reverse-engineering in timeline |

---

## RISK REGISTER

| # | Risk | Probability | Impact | Owner | Mitigation | Trigger |
|---|---|---|---|---|---|---|
| 1 | Finance unavailable for testing during Q4 budget close | Medium | High | PM | Schedule testing post-close; hire QA contractor | Testing phase needs to slip 2 weeks |
| 2 | Vendor integration delays | Medium | High | Tech Lead | Build contract penalty clause; identify alt vendor | Integration code not received by week 5 |
| 3 | Requirements scope creep (stakeholders add features mid-project) | High | Medium | PM | Implement Change Control Board; all requests must be approved | Any request for change takes >2 days |
| 4 | Data migration quality issues (duplicate/bad data in legacy system) | Medium | High | Eng Lead | Run data audit pre-migration; build data cleansing scripts | Migration test shows >5% error rate |
| 5 | User adoption lower than 80% | Medium | Med | Finance SME | Build training plan; assign champion in Finance | Week 2 post-rollout: <70% of team using system |

---

## GOVERNANCE & CHANGE CONTROL

### Steering Committee
**Meeting**: Monthly, {{Date}}, {{Duration}}
**Attendees**: VP Operations (Chair), CTO, Finance Lead, PM (secretary)
**Purpose**: Approve budget, timeline changes; review progress; escalate issues
**Authority**: Approve any change >5 days effort or >${{amount}} budget impact

**Decision Criteria**:
- Approved if: {{Impact on timeline < 1 week, impact on budget < 5%}}
- Escalated if: {{Impact on timeline 1-2 weeks, impact on budget 5-10%}}
- Rejected if: {{Misaligned to project objective}}

### Change Control Board
**When Triggered**: Any request for scope change
**Process**:
1. {{PM}} documents change request (why, impact on timeline/budget, value)
2. {{Tech Lead}} assesses effort & risk
3. {{Steering Committee}} votes (approve, defer, reject)
4. If approved: {{PM}} updates schedule & baseline

### Escalation Path
- **Technical Decision** (builds, integrations, architecture): {{Tech Lead}} approves <2 days; escalates >2 days to CTO
- **Process/Data Change** (impacts Finance workflows): {{Finance SME}} approves; {{VP Operations}} approves if >10 hrs/week impact
- **Budget Variance** >5%: {{CFO}} approval
- **Timeline Slip** >2 weeks: {{CEO/Board}} notification

---

## RESOURCE PLAN & BUDGET

### Team Composition
| Role | Person | FTE | Duration | Skill | Notes |
|---|---|---|---|---|---|
| {{Project Manager}} | {{Name}} | 1.0 | 12 weeks | PMP, vendor mgmt | Lead person for governance |
| {{Technical Lead}} | {{Name}} | 1.0 | 12 weeks | {{Language}}, APIs | Owns technical decisions |
| {{Finance SME}} | {{Name}} | 0.5 | 12 weeks | {{Domain}} | Process & data expert |
| {{QA/Tester}} | {{Name}} | 0.3 | 12 weeks | QA automation | Testing & validation |
| {{Vendor / Consultant}} | {{Vendor}} | {{}} | {{}} | {{Specialty}} | {{Focus area}} |

### Budget Breakdown
| Item | Amount | Notes |
|---|---|---|
| **Labor** | ${{}} | Team salaries (fully loaded with overhead) |
| **Vendor/Integration** | ${{}} | {{Vendor}} consulting, integration |
| **Tools & Infrastructure** | ${{}} | {{Tool}} license, cloud resources |
| **Training & Documentation** | ${{}} | Staff training, user guides, runbooks |
| **Contingency (10%)** | ${{}} | Buffer for unknowns |
| **TOTAL PROJECT COST** | ${{}} | {{}} |

### ROI Calculation
- **Project Cost**: ${{}}
- **Annual Benefit**: ${{}} (cost savings, productivity gains)
- **Payback Period**: {{months}} (cost / monthly benefit)
- **3-Year ROI**: {{%}} (cumulative benefit / cost)

---

## COMMUNICATION & APPROVALS

### Communication Plan
| Audience | Frequency | Format | Owner | Content |
|---|---|---|---|---|
| {{Steering Committee}} | Monthly | In-person meeting + pre-read | PM | Progress, risks, decisions |
| {{Project Team}} | Weekly | Standup (30 min) + async updates | PM | Blockers, progress, next week plan |
| {{Executive Sponsors}} | Monthly | 1-page summary | PM | Milestone progress, budget, risks |
| {{Broader Stakeholders}} | Monthly | All-hands update | PM | High-level progress, timeline |

### Approval Gates

**Gate 1: Charter Approval** (Week 0)
- **Approver**: {{CEO / Board}}
- **Criteria**: Stakeholder alignment, budget approved, timeline feasible
- **Condition**: Sign-off before team kickoff

**Gate 2: Requirements Sign-Off** (Week 2)
- **Approver**: {{VP Operations, Finance Lead}}
- **Criteria**: All requirements documented, prioritized, estimated
- **Condition**: Proceed to design phase

**Gate 3: Technical Design Review** (Week 3)
- **Approver**: {{CTO}}
- **Criteria**: Architecture vetted, risks mitigated, vendor ready
- **Condition**: Proceed to build phase

**Gate 4: Go/No-Go for Rollout** (Week 10)
- **Approver**: {{VP Operations, CTO}}
- **Criteria**: {{Test coverage 95%+}}, {{critical bugs fixed}}, {{training complete}}, {{success criteria met 90%+}}
- **Condition**: Proceed to production rollout or defer to next week

---

## APPENDIX

### A. Detailed Requirements (Link or Attachment)
{{URL or document name}}

### B. Technical Architecture Diagram
{{Link or embedded diagram}}

### C. Data Migration Plan
{{Link or summary}}

### D. Training & Rollout Plan
{{Link or summary}}

---

**Charter Approval Signature**

| Role | Name | Signature | Date |
|---|---|---|---|---|
| Executive Sponsor | {{}} | | |
| Project Manager | {{}} | | |
| {{Department Head}} | {{}} | | |

```

## Quality Gates
- [ ] Business case clearly articulates current state, desired state, and cost of inaction
- [ ] Project objectives are measurable and aligned to business case
- [ ] Scope clearly defines what's IN and OUT to prevent creep
- [ ] RACI matrix shows 1 Accountable per decision area; prevents diffusion of responsibility
- [ ] Milestones are spaced 2-4 weeks apart with acceptance criteria and owners
- [ ] Top 5-10 risks identified with probability, impact, and mitigation
- [ ] Governance structure defines who approves what, change control process
- [ ] Resource plan and budget align (team capacity supports timeline)
- [ ] Charter is approved by executive sponsor before kickoff

## Examples

### Good Output (excerpt)
```
PROJECT CHARTER: Invoice Automation
Status: Approved | Approved By: VP Operations | Date: Jan 5, 2025

BUSINESS CASE:
Current State: Finance processes 400 invoices/month manually across 4 systems. 60 hours/month effort, 21-day cash visibility lag.
Desired State: Automated invoice processing with 95% accuracy, 8 hours/month manual effort, real-time cash visibility.
Cost of Inaction: $4,800/month labor + $50K annual float cost. At 5x customer growth (1,600 invoices/month), process breaks.

MILESTONES:
- Week 2: Requirements locked (15 requirements, all approved by Finance)
- Week 8: MVP tested by 3 pilot Finance users
- Week 12: Full rollout; 90% of invoices processed automatically

RACI MATRIX:
| Role | Requirement Gathering | Build | Testing | Rollout |
|---|---|---|---|---|
| Finance Lead | A, R | C | R | C |
| Eng Lead | C | A, R | C | R |
| VP Ops | C | C | C | A |

RISKS:
1. Finance unavailable during Q4 budget close (mid-project) | Medium prob, High impact | Mitigation: Hire QA contractor for interim testing
2. Vendor integration delays | Medium prob, High impact | Mitigation: Contract penalty clause; identify alt vendor

GO/NO-GO GATE (Week 10):
Criteria: 95%+ test coverage, <5 critical bugs, 90%+ users trained, NPS > 30
If met: Proceed to rollout. If not: Defer 1 week.
```

### Bad Output (what to avoid)
```
PROJECT CHARTER: Improve Invoice Processing

OBJECTIVES:
- Make invoices easier to process
- Reduce manual work
- Improve accuracy

(Why this fails: Vague objectives (what is "easier"?), no metrics (how much reduction?), no scope boundaries, no stakeholder clarity, no risk assessment, no governance)
```

## Common Mistakes

1. **Vague Objectives Without Metrics**: "Improve customer experience" is unmeasurable. Better: "Reduce invoice processing time from 60 hours to 8 hours/month (87% reduction)." This is specific and testable.

2. **RACI Confusion (Multiple Accountables)**: "Both Finance and Engineering are accountable for testing." Result: Finger-pointing when testing fails. Better: "Finance Lead is Accountable for test plan and validation. Engineering is Responsible for fixing bugs identified."

3. **No Escalation Path**: Project hits a conflict (Finance wants Feature A, Engineering says it delays timeline 3 weeks). Who decides? Better: "Any scope change >5 days is decided by Steering Committee. If decision impacts budget >5%, CFO approval required."

4. **Assumptions Not Flagged as Risks**: Charter assumes "Finance will dedicate 20 hours/week" but doesn't flag this as a risk. Mid-project, Finance says they only have 10 hours/week. Timeline slips. Better: Mark assumption as risk with mitigation ("Hire QA contractor if Finance unavailable").

5. **Budget With No Contingency**: "Project costs exactly $300K" (no buffer). Real world: Vendor delay, unexpected data quality issues, additional testing. Result: Project runs over budget or cuts corners. Better: 10-15% contingency. "$300K base + $30K contingency (10%), total $330K."

## Anti-Patterns

1. **Charter as "Cover Your Ass" Document**: Created, distributed, never reviewed. Project launches, nobody remembers what's in charter. Better: Charter is living document. Reviewed at each steering committee meeting. Updated if assumptions or risks change.

2. **Scope So Vague It Explodes**: "In scope: Improve invoice processing" could mean 10 different things. Mid-project: stakeholder requests 5 features assuming they were "obviously in scope." Result: Scope creep, timeline slip. Better: Detailed scope statement with 10-15 explicit deliverables listed.

3. **RACI So Complex It's Useless**: 10x10 matrix with every role R/A/C/I. Nobody knows who owns what. Better: Simplified RACI (5-6 key decision areas, 5-6 key roles). "Finance is A for requirements, Eng is A for design, PM is A for timeline."

4. **Risk Register That Never Changes**: Created week 1, 10 risks listed. Week 6, 5 risks have materialized, 3 have changed probability, 2 new risks emerged. Register unchanged. Better: Review risk register at every team sync. Update probability, impact, status. Remove mitigated risks.

5. **Governance Gate Too Rigid**: Gate criteria: "100% of tests pass, zero bugs, 100% of users trained." Reality: Week 10, 98% tests pass, 2 minor bugs (post-launch fix planned), 95% trained. Gate fails; rollout denied. Frustration. Better: Gate criteria: "95%+ tests pass, <5 critical bugs, >90% trained." Allows reasonable trade-offs.

