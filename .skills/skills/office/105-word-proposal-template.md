---
name: word-proposal-template
description: "Build persuasive business proposals with cover page, scope, timeline, pricing, and signature block. Use when asked to 'write a proposal' or 'create a bid document'."
category: office
difficulty: beginner
model_boost: "Fixes weak proposals: unclear scope, vague pricing, missing timeline, no signature authority."
---

# Word Proposal Template

## Purpose
Structure persuasive proposals that win business. This skill organizes proposals into sections that address client concerns in order: your understanding of the need, your solution, scope boundaries, timeline/milestones, team qualifications, transparent pricing, and terms. A strong proposal is a sales document—every section builds confidence that you'll deliver.

## When to Use
- "I need to write a proposal" for a client project
- "Create a bid document" for RFP response
- "Build a statement of work (SOW)"
- **Do NOT use when**: Writing a report (use 104-word-report-builder); writing a contract (use 109-word-contract-drafter)

## Instructions

### Step 1: Cover Page Design
First impression matters. Make it crisp and professional.

**Cover Page Structure**
```
[3-4 blank lines]
[CLIENT LOGO or placeholder {Client Logo Here}]
[3 blank lines]
[PROJECT TITLE in large bold font (18pt+)]
[Subtitle describing scope in italics, 12pt]
[5-6 blank lines]
[Prepared by: Your Company Name]
[Your company logo]
[3 blank lines]
[Date: Month DD, YYYY]
[Version: {{PROPOSAL REV X}}]
[Document ID or Proposal #: {{PROP-2024-0012}}]
```

**Optional (for formal proposals)**
- Confidentiality statement: "This proposal contains confidential information"
- Client reference: "In response to RFP #[ID] dated [date]"
- Project code: Used for tracking in your system

**Formatting**
- Center alignment for cover page elements
- Background color optional (light gray or brand color, not distracting)
- Page break after cover page: Ctrl+Enter

### Step 2: Executive Summary (1 page max)
Busy executives read only this—make it tight and persuasive.

**Three-Part Structure**
1. **Opportunity Recognition** (2-3 sentences)
   - Show you understand their problem/goal
   - Example: "You've indicated your need to reduce cloud infrastructure costs by 20% while improving system uptime. Your current multi-cloud setup lacks centralized monitoring and governance."

2. **Our Approach** (2-3 sentences)
   - High-level solution; save details for later
   - Example: "We propose a phased engagement: (1) audit your current cloud setup (2 weeks), (2) design a consolidated infrastructure with FinOps governance (4 weeks), (3) migrate workloads with zero downtime (8 weeks). Total engagement: 14 weeks."

3. **Expected Outcomes** (2-3 sentences)
   - Quantify benefits: savings, timeline, risk reduction
   - Example: "Estimated outcomes: 22% cost reduction ($450K annually), 99.95% uptime SLA, and a reusable FinOps framework for future cloud decisions. Engagement cost: $180K."

**Format**
- 3-4 short paragraphs or bullet points
- < 1 page
- Include key numbers (cost, timeline, expected savings)
- No jargon your client won't understand

### Step 3: Understanding of Your Needs
Demonstrate you've listened and understand their problem.

**Structure** (H2 subsections)
- **Current State**: What are they doing now? What's working/not working?
- **Challenge/Opportunity**: What triggered the need for help?
- **Success Criteria**: What does success look like to them?

**Writing Tips**
- Use their language: If they said "reducing tech debt," use that phrase, not "legacy system modernization"
- Show research: "Your 2024 annual report highlighted supply chain transparency as a strategic priority"
- Be specific: "Managing 47 AWS accounts across 3 regions without a cost allocation framework creates blind spots"
- Never patronize: "You likely haven't considered X" → Instead, acknowledge market context

**Example**
```
## Understanding of Your Needs

### Current State
Acme Corp currently maintains a hybrid infrastructure:
- 35 on-premises servers handling legacy applications
- AWS services for new cloud-native workloads (EC2, RDS, Lambda)
- Azure storage for data analytics workloads
- Manual cost tracking across all platforms

### Challenge
Without centralized monitoring and governance, you lack visibility into:
- Which teams/projects are driving costs
- Where redundancy exists (e.g., dual databases)
- Opportunities to optimize compute, storage, and data transfer

### Success Criteria
Your team defined success as:
1. Cost transparency by project/team/cost center
2. 20% cost reduction YoY without sacrificing performance
3. Governance framework that survives staffing changes
4. Ability to forecast and budget cloud costs quarterly
```

### Step 4: Proposed Solution (2-3 pages)
This is your selling section. Organize by phase/component.

**Solution Overview** (1 paragraph)
- High-level approach
- Example: "We'll implement a three-phase FinOps program: (1) Audit and discovery, (2) Governance and optimization, (3) Ongoing cost management and forecasting."

**Phase-by-Phase Breakdown** (H3 subsections)
For each phase, describe:
- **Objective**: What we're accomplishing
- **Approach**: How we'll do it
- **Deliverables**: What you receive
- **Timeline**: Duration
- **Team**: Who's involved (your side + their side)

**Example: Phase 1**
```
### Phase 1: Cloud Infrastructure Audit (2 weeks)

**Objective**
Document current state, identify cost drivers and optimization opportunities.

**Approach**
- Review your AWS, Azure, and on-prem architectures
- Analyze 90 days of cloud billing data
- Interview engineering leads to understand workload requirements
- Benchmark against industry standards (compute utilization, storage growth rates)

**Deliverables**
- Comprehensive infrastructure report with current costs, architecture diagrams
- Cost drivers analysis (top 10 most expensive resources)
- Quick wins document (savings achievable in 0-30 days)
- Detailed findings presentation to your steering committee

**Timeline**: 2 weeks (10 business days)
- Week 1: Architecture review + data analysis
- Week 2: Interviews + report writing + presentation prep

**Your Team Responsibilities**
- Designate single point of contact for access requests
- Provide read-only cloud platform access (AWS/Azure/on-prem)
- Participate in 3-4 interviews with technical leads (~1 hour each)
```

**Architecture Diagram (optional)**
Insert visual of "current state → future state" if helpful.

### Step 5: Scope of Work (In-Scope vs Out-of-Scope)
Clarity prevents scope creep and disappoints early.

**Table Format** (clear, scannable)
```
| In-Scope | Out-of-Scope |
|---|---|
| AWS cost optimization (EC2, RDS, S3) | Google Cloud (not part of current environment) |
| Data transfer cost analysis | Application code refactoring |
| Reserved Instance purchase recommendations | Hardware procurement (on-premises) |
| Cost allocation tagging strategy | Vendor negotiations (your responsibility) |
| Monthly FinOps reporting template | Data migration (separate engagement) |
```

**Assumptions** (list any constraints)
- Client will provide cloud platform access by [date]
- Client will dedicate 5 hours/week for interviews and reviews
- No more than 47 AWS accounts in scope (if new accounts added, timeline extends)
- Engagement assumes no major platform migrations during the project

**Out-of-Scope Mitigation**
If something's likely to come up, address it:
- "Google Cloud optimization: Available as Phase 4 scope expansion (estimated 1 week, $25K)"

### Step 6: Timeline and Milestones
Gantt-style table shows progress and accountability.

**Format** (visible, easy to understand)
```
| Phase | Start | End | Duration | Key Milestones |
|---|---|---|---|---|
| Phase 1: Audit | Week 1 | Week 2 | 2 weeks | Infra report delivered (EOD Friday, Week 2) |
| Phase 2: Design | Week 3 | Week 6 | 4 weeks | Governance framework reviewed (EOD Week 5); final approval (EOD Week 6) |
| Phase 3: Migration | Week 7 | Week 14 | 8 weeks | Test migration complete (Week 10); production cutover (Week 14) |
| Phase 4: Handoff | Week 15 | Week 15 | 1 week | Team training, documentation delivered, go-live support |

**Total Duration**: 15 weeks (starting [Date])
**Expected Completion**: [Target completion date]
```

**Dependencies**
- If Phase 2 depends on Phase 1 completion, state it: "Phase 2 start date assumes Phase 1 on-time completion"
- Escalation process: "If Phase 1 reveals unexpected complexity, we'll notify within 3 days and propose timeline adjustment"

**Key Dates**
- Proposal acceptance deadline: [Date]
- Ideal engagement start date: [Date]
- Hard deadline (if any): [Date]

### Step 7: Team Qualifications
Explain why YOUR team can deliver.

**Team Structure**
```
| Role | Name | Experience | Responsibility |
|---|---|---|---|
| Engagement Lead | Jane Smith | 12 years cloud architecture | Overall delivery, client liaison |
| Principal Cloud Architect | Bob Johnson | AWS certified solutions architect | Infrastructure design, optimization strategy |
| Senior Cost Engineer | Sarah Lee | 5 years FinOps | Cost analysis, tagging strategy, reporting |
| Implementation Lead | Mike Chen | 8 years AWS/Azure | Hands-on implementation, testing |
| Support Engineer | Alex Rodriguez | 3 years cloud ops | Migration support, runbook development |
```

**Relevant Experience** (brief bullets)
- 8+ years implementing FinOps at enterprise scale
- Reduced cloud costs for 15+ Fortune 500 clients (average 24% savings)
- AWS Advanced Partner for cost optimization
- Published research on cloud cost forecasting (included in appendix)

**Certifications** (if relevant)
- AWS Solutions Architect Professional
- Certified FinOps Practitioner
- ISO 27001 (for security-sensitive clients)

### Step 8: Pricing and Payment Terms
Be transparent. Hidden costs kill deals.

**Pricing Breakdown** (itemized)
```
| Service | Unit | Qty | Unit Price | Total |
|---|---|---|---|---|
| Cloud Infrastructure Audit | weeks | 2 | $12,000 | $24,000 |
| FinOps Governance Design | weeks | 4 | $11,000 | $44,000 |
| Implementation & Migration | weeks | 8 | $10,000 | $80,000 |
| Project Management | % of fees | 1 | 10% | $14,800 |
| **Subtotal** | | | | **$162,800** |
| **Contingency** (10% risk buffer) | | | | **$16,280** |
| **Total Engagement Fee** | | | | **$179,080** |

**Optional Add-Ons** (if client wants more)
- Extended support (3 months post-handoff): $8,000/month
- Cloud cost optimization retainer (monthly advisory): $6,000/month
- Advanced FinOps training for client team: $15,000 (1 week, max 8 attendees)
```

**Payment Schedule** (typical for consulting)
```
| Milestone | % of Fee | Amount | Due Date |
|---|---|---|---|
| Upon signature | 25% | $44,770 | Day 0 |
| Phase 1 completion | 25% | $44,770 | End of Week 2 |
| Phase 2 completion | 25% | $44,770 | End of Week 6 |
| Final delivery | 25% | $44,770 | End of Week 15 |
```

**Alternative**: 50% upfront, 50% upon completion (for shorter engagements < 8 weeks)

**Expense Reimbursement** (if applicable)
- Travel (airfare economy, hotel, ground transportation): Actual + 5% admin fee
- Software/tools licenses: Actual cost
- Out-of-pocket client expenses: Itemized, submitted monthly

**Price Guarantee**
"Pricing is valid for 30 days from proposal date. Extensions requested after [date] may require pricing adjustment based on market conditions."

### Step 9: Terms and Conditions
Protect both parties with clear expectations.

**Key Clauses** (in plain language, not legalese)

**Confidentiality**
- Both parties agree to keep sensitive information confidential
- Exceptions: required by law, with prior notice

**Limitation of Liability**
- Our liability is limited to fees paid in this engagement
- We're not liable for indirect damages (lost profit, data loss)

**Intellectual Property**
- Work products (reports, frameworks, code) are yours to use
- We retain rights to methodology and tools we developed before this engagement

**Client Responsibilities**
- Provide necessary system access within [X days]
- Dedicate resources as outlined in project schedule
- Approve deliverables within 5 business days of review
- Notify us of scope changes in writing

**Changes to Scope**
- Additional work requests require written change order
- Timeline and budget may be adjusted based on approved changes

**Termination**
- Either party can terminate with 10 days' written notice
- If terminated early, client pays for work completed through termination date
- Completed deliverables remain property of client

**Dispute Resolution**
- First: Good-faith discussion between engagement leads
- If unresolved after 14 days: Escalate to account executives
- Legal remedies: [Mediation | Arbitration | Your jurisdiction]

### Step 10: Acceptance and Signature Block
Make it easy for them to say yes.

**Acceptance Section**
```
## Acceptance

By signing below, the Client agrees to the terms and conditions outlined
in this proposal and authorizes the engagement to proceed.

**CLIENT**
Client Company Name: _________________________________
Authorized Signature: __________________________________
Print Name & Title: ____________________________________
Date: ____________________________________________________________

**OUR FIRM**
Our Company Name: __________________________________
Authorized Signature: __________________________________
Print Name & Title: ____________________________________
Date: ____________________________________________________________

---

## Appendix A: Relevant Case Study

[1-page case study showing similar work you've done for another client in their industry]

## Appendix B: Team Bios

[1-2 page detailed bios of key team members]

## Appendix C: References

Available upon request:
- 3 clients from similar engagements (contact info provided separately)
```

## Output Template
```
# {{COMPANY}} Proposal: {{PROJECT NAME}}

**Prepared by**: {{Your company}}
**Date**: {{Month DD, YYYY}}
**Valid Through**: {{Expiration date, typically 30 days}}
**Proposal ID**: {{PROP-YYYY-####}}

---

## Executive Summary
{{Opportunity recognition (2-3 sentences)}}
{{Our approach (2-3 sentences)}}
{{Expected outcomes with quantified benefits (2-3 sentences)}}

## Understanding of Your Needs
### Current State
{{Description of how they work now}}

### Challenge/Opportunity
{{What problem or goal prompted this}}

### Success Criteria
- {{Specific goal 1}}
- {{Specific goal 2}}
- {{Specific goal 3}}

## Proposed Solution
{{High-level approach}}

### Phase 1: {{Name}}
**Objective**: {{What we achieve}}
**Deliverables**: {{What you receive}}
**Timeline**: {{Duration}}

### Phase 2: {{Name}}
[Same structure]

## Scope of Work
| In-Scope | Out-of-Scope |
|---|---|
| {{Item}} | {{Item}} |

## Timeline & Milestones
Engagement Start: {{Date}}
Completion Target: {{Date}}
Total Duration: {{X weeks}}

[Gantt table]

## Team
| Role | Name | Background |
|---|---|---|
| {{Role}} | {{Name}} | {{X years experience}} |

## Investment
Total Engagement Fee: ${{Total}}

[Pricing breakdown table]

## Terms
- Confidentiality: [Standard]
- Liability: Limited to fees paid
- IP: Client retains work products
- Changes: Require written change order

## Acceptance
[Signature blocks for both parties]
```

## Quality Gates
- [ ] Executive summary is ≤ 1 page and includes quantified outcomes
- [ ] Scope section clearly separates In-Scope from Out-of-Scope (no ambiguity)
- [ ] Timeline shows start/end dates and key milestones (not vague "TBD")
- [ ] Pricing is itemized with clear payment schedule (not a single lump sum)
- [ ] Team bios explain why they're qualified (specific experience, not generic)
- [ ] Terms and conditions address key client concerns (IP, confidentiality, changes)
- [ ] Signature block is present with clear acceptance language
- [ ] No jargon your client won't understand; or jargon is explained

## Examples

### Good Output (excerpt)
```
## Executive Summary

CloudTech Corp needs to reduce multi-cloud costs by 20% while implementing
governance that survives staffing changes. Your current AWS, Azure, and
on-prem infrastructure lacks centralized cost visibility, creating blind spots.

We propose a 15-week engagement to audit your infrastructure, design a
FinOps governance framework, and implement cost optimization. Our team
has reduced costs for 18 Fortune 500 clients by an average of 24%.

Expected outcomes: $450K annual cost reduction, 99.95% uptime SLA, and
a reusable FinOps framework. Investment: $179,080.

## Scope of Work
| In-Scope | Out-of-Scope |
|---|---|
| AWS cost optimization (EC2, RDS, S3, Lambda) | Google Cloud services |
| Azure cost analysis | Hardware procurement |
| Reserved Instance strategy | Application refactoring |
| Monthly cost reporting template | Data migration |

## Timeline
| Phase | Dates | Duration |
|---|---|---|
| Audit | Jan 1-14 | 2 weeks |
| Design | Jan 15-Feb 11 | 4 weeks |
| Implementation | Feb 12-Apr 8 | 8 weeks |
| Handoff | Apr 9-13 | 1 week |

## Investment
Cloud Audit: $24,000
Governance Design: $44,000
Implementation: $80,000
Project Management: $14,800
Contingency (10%): $16,280
**Total: $179,080**

## Payment Schedule
25% ($44,770) upon signature
25% ($44,770) at Phase 1 completion
25% ($44,770) at Phase 2 completion
25% ($44,770) at final handoff
```

### Bad Output (what to avoid)
```
Executive summary: 3 pages with deep methodology explanation
Scope section: Vague ("We'll optimize your cloud" with no specifics about what)
Timeline: "Weeks 1-15" with no specific dates or milestones
Pricing: "Cloud optimization engagement: $150,000" with no breakdown
Team section: Lists names only, no relevant experience
Payment terms: "Invoice upon completion" (no progress milestones)
Signature block: Missing or unclear who has authority to sign
Assumptions/dependencies: Not stated; client surprised mid-project
```

## Common Mistakes

1. **Mistake**: Proposal scope is vague ("We'll improve cloud costs").
   → **Fix**: Be specific: "We will conduct an audit of AWS/Azure infrastructure, identify 10+ cost optimization opportunities, and implement Reserved Instance purchasing strategy."

2. **Mistake**: Timeline shows durations ("4 weeks") without specific dates.
   → **Fix**: Show calendar dates: "Audit: January 1-14, 2024" so client can block time.

3. **Mistake**: Pricing is a single line ("Consulting: $100K") with no breakdown.
   → **Fix**: Itemize (audit $20K, design $40K, implementation $40K) so client sees value per phase.

4. **Mistake**: Team section lists names with no credentials or relevant experience.
   → **Fix**: "Jane Smith (AWS certified architect, 12 years cloud infrastructure, led 15 FinOps projects)" explains why she's qualified.

5. **Mistake**: Signature block is missing or lacks specificity on payment terms.
   → **Fix**: Include clear signature lines, payment schedule, and termination clause.

## Anti-Patterns
- Never leave scope ambiguous. (Scope creep kills profitability; out-of-scope must be explicit.)
- Never propose without understanding their success criteria. (You'll deliver the wrong thing.)
- Never omit timeline specifics (dates, milestones, dependencies). (Vagueness invites disputes.)
- Never hide pricing or bundle everything into one number. (Clients want to see what they're paying for.)
- Never list team members without their relevant experience. (They don't know if your team is qualified.)
- Never forget the signature block. (How do they formally accept the proposal?)
