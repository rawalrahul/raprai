---
name: sop-writer
description: "Generate detailed standard operating procedures (SOPs) with numbered steps, decision trees, process flows, version control, and approval workflows. Ensures consistency, trains new hires, and prevents knowledge silos."
category: business
difficulty: beginner
model_boost: "Prevents undocumented processes, knowledge silos, and inconsistent execution; produces instead clear, actionable procedures."
---

# SOP Writer

## Purpose
A Standard Operating Procedure (SOP) documents how a process should be executed, step-by-step. This skill generates SOPs with: numbered steps, decision trees (if X then do Y), role assignments (who is responsible), approval workflows (who approves and when), error handling (what to do if it fails), and version control (tracking changes). Output enables: consistent execution, faster onboarding, reduced errors, and prevents key-person dependencies.

## When to Use
- Documenting core business processes (customer onboarding, invoice approval, hiring, etc.)
- Preparing for scaling (process must work when {{# of people}} increases)
- Reducing reliance on 1-2 people who know "how we do it"
- Training new hires or departments
- Ensuring compliance or audit requirements (documented processes)
- **Do NOT use when**: Process is <3 steps and intuitive; process changes weekly (document after stabilization); nobody actually follows documented processes (fix the underlying issue first).

## Instructions

### Step 1: Define SOP Scope & Objective
What process are you documenting? Start and end points?

**Example**: "Customer Onboarding SOP"
- **Start**: Customer signs contract and gets login credentials
- **End**: Customer uses product for first revenue transaction (invoice processed)
- **Goal**: New customer is productive within 3 business days

Clear scope prevents: documenting too much (entire product journey) or too little (3 vague steps).

### Step 2: Map the Current Process (As-Is)
Walk through the process with someone who does it. Document:
- **Steps**: What actually happens (not what should happen)
- **Decision points**: Where does the process branch? (If customer has X integration requirement, route to technical onboarding)
- **Handoffs**: Where does work move from one person/department to another?
- **Time blocks**: How long does each step take?
- **Pain points**: Where do things break or get delayed?

### Step 3: Identify Decision Points & Branches
Real-world processes branch. Document decision trees.

**Example**:
- If customer signs annual contract → offer white-glove onboarding (1-week implementation)
- If customer signs monthly contract → self-serve onboarding (customer uses guide)
- If customer requires custom integrations → escalate to technical lead

### Step 4: Define Roles & Responsibilities
Who does what? Use RACI if complex:
- **R**esponsible: Who executes the step
- **A**ccountable: Who owns outcome (usually same as responsible)
- **C**onsulted: Who is asked for input
- **I**nformed: Who is kept in loop

### Step 5: Write Steps in Numbered Format
Each step is a single, clear action. No compound steps.

**Good**:
1. Receive customer sign-up confirmation email
2. Create account in {{system}}
3. Send welcome email with onboarding guide and scheduled call time

**Bad**:
1. Receive customer sign-up, create their account, send welcome email, and schedule onboarding call

Numbered steps are scannable and trackable ("We're on step 7 of 12").

### Step 6: Add Detail: What, Who, Tools, Timeline
For each step, specify:
- **What**: Action to take
- **Who**: Role responsible
- **Tools/Systems**: System or tool used (CRM, form, etc.)
- **Timeline**: How long this should take
- **Success Criteria**: How do you know this step was done right?

### Step 7: Document Decision Trees & Branch Logic
Where does the process branch?

**Decision Point**: "Does customer need custom integration?"
- **If YES**: Route to {{Technical Onboarding Path}} (Step 8a-8d)
- **If NO**: Route to {{Self-Serve Path}} (Step 9-12)

Clear branching prevents: people making different decisions and creating inconsistency.

### Step 8: Add Error Handling & Troubleshooting
What if something goes wrong? Document recovery.

**Example**:
- **If customer doesn't show up for onboarding call**:
  - Wait 10 minutes
  - Send chat message: "Are you still available?"
  - If no response in 5 minutes, send email: "We missed you. Rescheduling for {{}}."
  - Log in CRM as "customer no-show"

### Step 9: Define Approval & Sign-Off
Who approves completion of this SOP? When?

**Example**: "Sales Manager approves onboarding completion once customer has processed first invoice (success criterion). Sign-off in CRM."

### Step 10: Add Version Control & Update History
SOPs change. Track versions.

**Header**:
- Version: {{1.2}}
- Last Updated: {{Date}} (by {{person}})
- Next Review: {{Date}}
- Owner: {{Role}}

**Change Log**:
- v1.2 (Jan 2025): Added decision tree for custom integrations (customers increasingly asking)
- v1.1 (July 2024): Reduced onboarding timeline from 5 days to 3 days
- v1.0 (Jan 2024): Initial SOP

This prevents outdated processes and shows evolution.

## Output Template

```markdown
# STANDARD OPERATING PROCEDURE: {{Process Name}}

**Version**: {{1.0}}
**Last Updated**: {{Date}} by {{Author}}
**Next Review Date**: {{Date}}
**Owner/Champion**: {{Role/Name}}
**Scope**: {{Start point}} → {{End point}}
**Purpose**: {{Why this process exists, desired outcome}}

---

## QUICK REFERENCE

| Attribute | Value |
|---|---|
| **Process Owner** | {{Role}} |
| **Average Duration** | {{# business days}} |
| **Key Decision Points** | {{#}} |
| **Handoffs Between Teams** | {{# (e.g., Sales → Onboarding → Support)}} |
| **Success Criterion** | {{Measurable outcome (e.g., customer's first transaction in system)}} |
| **SLA** | {{Timeline from start to finish (e.g., "3 business days")}} |

---

## OVERVIEW & CONTEXT

### What is This Process?
{{1-2 sentences describing what this process accomplishes}}

### Why It Matters
{{Why we have this process. Business impact if not done well. Compliance/risk if relevant.}}

### When to Use This SOP
{{When should a team member follow this? (e.g., "When a customer signs a contract", "When a support ticket comes in")}}

### Scope: INCLUDED vs. EXCLUDED

**IN Scope**:
- {{Activity 1}}: {{What we document}}
- {{Activity 2}}: {{}}

**OUT of Scope** (documented elsewhere):
- {{Activity A}}: {{Why not here (e.g., covered in {{other SOP}})}}
- {{Activity B}}: {{}}

---

## PROCESS FLOWCHART (Visual)

```
[Start] → [Step 1] → [Decision: X?]
    ├→ [If Yes] → [Step 2a] → [Step 3a] → [End]
    └→ [If No] → [Step 2b] → [Step 3b] → [End]
```

(Or: Swimlane diagram showing roles and handoffs)

---

## STEP-BY-STEP PROCEDURES

### Step 1: {{Action Title}}
**Role**: {{Who does this}} (e.g., "Sales Rep" or "Customer Success Manager")
**Tools Required**: {{System/tool used}}
**Timeline**: {{How long (e.g., "5 minutes")}}
**Input**: {{What information or data is needed}}

**Procedure**:
1. {{Detailed sub-step 1}}
2. {{Sub-step 2}}
3. {{Sub-step 3}}

**Success Criteria**: {{How do you know this was done correctly?}}
- ☐ {{Checklist item 1}}
- ☐ {{Checklist item 2}}

**Example**: {{Real example from recent execution}}

**Common Mistakes**:
- {{Mistake 1}}: {{What goes wrong and why}}
- {{Mistake 2}}: {{}}

---

### Step 2: {{Action Title}}
**Role**: {{}}
**Tools Required**: {{}}
**Timeline**: {{}}
**Input**: {{}}

**Procedure**:
...

---

### DECISION POINT: {{Decision Title}}
**At this point, the process branches based on {{criteria}}**

**Question**: {{Is {{condition]] true?}}

**If YES** → Continue to {{Step X (Path A)}}
- {{Reason this path is taken}}: {{Example condition}}

**If NO** → Continue to {{Step Y (Path B)}}
- {{Reason this path is taken}}: {{Example condition}}

---

### Step 3a: {{Path A Title}} (If [Condition] = YES)
**Role**: {{}}
**Tools**: {{}}
**Timeline**: {{}}

**Procedure**:
...

---

### Step 3b: {{Path B Title}} (If [Condition] = NO)
**Role**: {{}}
**Tools**: {{}}
**Timeline**: {{}}

**Procedure**:
...

---

## ROLES & RESPONSIBILITIES

| Role | Steps Responsible For | Authority | Notes |
|---|---|---|---|
| {{Role 1 (e.g., Sales Rep)}} | {{Steps 1-2}} | {{Can approve? Can escalate?}} | {{Context}} |
| {{Role 2 (e.g., Onboarding Manager)}} | {{Steps 3-5}} | {{}} | {{}} |
| {{Role 3 (e.g., Tech Lead)}} | {{Step 6 (if escalated)}} | {{Can approve; must notify manager}} | {{}} |

---

## APPROVAL & SIGN-OFF

### Who Approves Completion?
{{Role responsible for sign-off}} (e.g., "Sales Manager")

### Approval Criteria
- ☐ {{Criterion 1}}: {{Measurable outcome (e.g., "Customer has processed first invoice")}}
- ☐ {{Criterion 2}}: {{}}
- ☐ {{Criterion 3}}: {{}}

### Where Approval is Recorded
{{System or location}} (e.g., "CRM {{field}} marked 'Onboarding Complete'", "Spreadsheet {{}}")

### Timeline
{{By when should approval happen relative to process start?}} (e.g., "Within 3 business days of contract signature")

---

## SYSTEMS & TOOLS USED

| System | Purpose | Link/Access |
|---|---|---|
| {{CRM Name}} | {{Used for step(s) X}} | {{Link or access instructions}} |
| {{Email/Communication Tool}} | {{Used for notifications}} | {{}} |
| {{Form/Document}} | {{Used for data collection}} | {{Link or template}} |
| {{{{Reporting Dashboard}}}} | {{For verification/audit}} | {{}} |

---

## ERROR HANDLING & TROUBLESHOOTING

### Issue 1: {{Common Problem}}
**Symptom**: {{How you notice this went wrong}}
**Root Cause**: {{Why it happens}}
**Solution**:
1. {{Recovery step 1}}
2. {{Recovery step 2}}
3. {{Log issue for improvement}} (where?)

**Prevention**: {{How to avoid next time}}

---

### Issue 2: {{Common Problem}}
**Symptom**: {{}}
**Root Cause**: {{}}
**Solution**:
1. {{}}
2. {{}}
3. {{}}

**Prevention**: {{}}

---

## METRICS & MONITORING

### Process Health Metrics (Track Monthly)
| Metric | Target | How Measured | Owner |
|---|---|---|---|
| **{{Metric 1: e.g., % of customers onboarded in SLA}}** | {{Target %}} | {{CRM report or manual count}} | {{Manager}} |
| **{{Metric 2: e.g., average time per step}}** | {{# hours}} | {{Time stamps in system}} | {{}} |
| **{{Metric 3: e.g., error rate}}** | {{<{{%}}}} | {{Manual review or system log}} | {{}} |

### Dashboard / Reporting
{{Where to find metrics}}: {{{{System or link}}}}

---

## CHANGE MANAGEMENT

### How to Update This SOP
1. {{Identify issue or improvement}} (e.g., "Step 3 takes 2 hours; should take 30 min")
2. {{Document proposed change}}: What's changing and why?
3. {{Approval}}: {{Process Owner}} reviews and approves
4. {{Test}}: Try new process with {{# of transactions}}
5. {{Rollout}}: Update SOP, train team
6. {{Monitor}}: Track metrics; revert if needed

### Escalation Path
If process breaks or can't be followed:
1. {{Frontline person}} attempts {{error handling}}, then escalates to {{Manager}}
2. {{Manager}} assesses: Can we fix quickly, or defer to {{Process Owner}}?
3. {{Process Owner}} makes decision: Adjust process or escalate further

---

## TRAINING & ONBOARDING

### How New Hires Learn This SOP
1. {{New hire reads SOP}} ({{# minutes}} read time)
2. {{Shadow experienced person}} for {{# transactions}} (see it done)
3. {{Perform process under supervision}} ({{#}} transactions observed)
4. {{Perform independently}}, manager spot-checks
5. {{Sign-off}}: Trainer confirms competency

### Testing / Competency Check
{{# of correct executions}} in a row = competency certified

### Refresher Training
{{When to retrain}} (e.g., "Annually or after major SOP change")

---

## VERSION HISTORY & CHANGE LOG

| Version | Date | Changed By | Changes Made | Reason |
|---|---|---|---|---|
| **1.0** | {{Date}} | {{Name}} | Initial SOP | {{New process}} |
| **1.1** | {{Date}} | {{}} | {{Step 3 timing reduced from 4 hours to 2 hours; added decision tree for custom integrations}} | {{Customers increasingly requesting custom integrations; process scaled}} |
| **1.2** | {{Date}} | {{}} | {{}} | {{}} |

---

## APPENDICES

### A. Templates & Checklists
- {{Onboarding Checklist}}: {{Link}}
- {{Customer Data Form}}: {{Link}}
- {{Sign-off Document}}: {{Link}}

### B. Examples
- {{Example 1: Customer with standard onboarding}}: {{Link to case or email sample}}
- {{Example 2: Customer with custom integration (Path A)}}: {{}}
- {{Example 3: Escalation/error scenario}}: {{}}

### C. Related SOPs
- {{Other Process 1}}: {{Why related (handoff, input/output)}}
- {{Other Process 2}}: {{}}

### D. External References / Compliance
- {{Regulation or policy}}: {{Citation or link}} (if applicable)

---

## APPROVAL & SIGN-OFF (SOP Document Itself)

| Role | Name | Signature | Date |
|---|---|---|---|
| **Process Owner** | {{}} | | |
| **Manager** | {{}} | | |
| **Compliance/Quality** | {{}} | | {{Only if regulatory requirement}} |

---

## QUICK REFERENCE CARD (Print & Laminate)

```
CUSTOMER ONBOARDING SOP — QUICK REFERENCE

STEPS IN ORDER:
1. Create account in CRM
2. Send welcome email with guide
3. Schedule onboarding call
[Decision: Custom integration needed?]
   → YES: Route to Tech Lead (Step 4a)
   → NO: Self-serve onboarding (Step 4b)
4a/4b. Complete onboarding
5. Send sign-off email
6. Manager approves in CRM

SUCCESS CRITERIA:
☐ Account created within 4 hours
☐ Customer scheduled within 24 hours
☐ Customer productive within 3 days

COMMON ISSUES:
- Customer doesn't show for call → Wait 10 min, send message, reschedule
- Integration fails → Contact Tech Lead, escalate

CONTACT:
Process Owner: {{Name}} {{Email}} {{Phone}}
Manager: {{}} {{}} {{}}
```

```

## Quality Gates
- [ ] Process has clear start and end points (scope defined)
- [ ] Steps are numbered and single-action (not compound)
- [ ] Each step specifies: What, Who, Tools, Timeline, Success Criteria
- [ ] Decision points documented with branches (If X, then go to Step Y)
- [ ] Roles clearly assigned (RACI or simple role → steps mapping)
- [ ] Approval & sign-off process defined (who approves, when, where)
- [ ] Error handling & troubleshooting documented (common issues + recovery)
- [ ] Systems & tools listed with access info
- [ ] Metrics defined for monitoring process health
- [ ] Version control & change log established
- [ ] Training/onboarding plan included

## Examples

### Good Output (excerpt)
```
SOP: Customer Onboarding

STEP 3: Send Welcome Email with Onboarding Guide
Role: Customer Success Manager (CSM)
Tools: Gmail, {{product}} Onboarding Portal
Timeline: Within 4 hours of account creation

Procedure:
1. Open {{product}} CRM, find customer record
2. Copy {{link to onboarding guide}} from template
3. Draft email using {{template: "Welcome {{customer_name}}"}}
4. Customize: replace {{customer_name}}, {{integration_type}}, {{call_time}}
5. Send email from {{CS email}}
6. Mark in CRM: "Welcome Email Sent" + timestamp

Success Criteria:
☐ Email sent within 4 hours of account creation
☐ Email includes onboarding guide link
☐ Email includes scheduled call time
☐ Email marked in CRM

Common Mistakes:
- Forgot to customize {{customer_name}} → reread email before sending
- Sent wrong integration guide → check {{integration_type}} field matches guide
- Sent from wrong email → use {{CS email}} template, not personal

---

DECISION POINT: Does Customer Need Custom Integration?
At this point, assess the customer's technical requirements.

Question: Did customer indicate in {{contract}} they need custom integration beyond our pre-built connectors?

If YES (e.g., customer uses rare ERP):
→ Route to STEP 4a: Technical Onboarding (Tech Lead takes over)
   Tech Lead completes custom integration assessment, quotes timeline

If NO (customer using supported ERP like {{list}}):
→ Route to STEP 4b: Self-Serve Onboarding (Customer follows guide)
   Customer logs in, configures integration themselves (typically 30 min)
```

### Bad Output (what to avoid)
```
SOP: Customer Onboarding

Steps:
1. Create customer account
2. Send welcome info and schedule call
3. Complete onboarding
4. Finish

(Why this fails: Vague steps (what info? how schedule?), no decision points, no success criteria, no error handling, no tools listed, no timeline)
```

## Common Mistakes

1. **Steps Too Vague**: "Send onboarding materials." To whom? From what email? Which materials? Which system tracks it? Better: "CSM sends welcome email (from {{template}}) with link to {{guide URL}} within 4 hours via Gmail, marks CRM as 'Welcome Sent'."

2. **Compound Steps (Multiple Actions in One)**: "Create account, send email, and schedule call." Better: Separate steps. Step 1: Create account. Step 2: Send email. Step 3: Schedule call. Scannable and trackable.

3. **No Decision Points Documented**: Real process branches ("If customer has custom integration needs, escalate"). SOP doesn't mention this. New person doesn't know when to escalate. Better: Document decision clearly. "If customer requires {{integration not in list}}, escalate to {{Tech Lead}}. Otherwise, customer self-serves."

4. **No Error Handling**: "Send email." What if customer email bounces? SOP silent. Better: "If email bounces, resend to {{backup email}} or phone call. If all contact attempts fail, escalate to {{Manager}}."

5. **SOP Never Updated**: Created 2 years ago. Process has changed 3 times. SOP is outdated. New people follow old process. Better: Version control. Each change documented. Annual review. Review date in header.

## Anti-Patterns

1. **SOP as Aspirational Document**: SOP says "Onboarding in 3 days" but actual is 7 days because {{resources aren't there}}. SOP is fantasy, not reality. Better: Document actual process (7 days). Then improve process. Then update SOP.

2. **SOP So Detailed It's Unusable**: 15-page SOP with {{300}} steps and {{50}} screenshots. Intimidating. New people don't read it. Better: Keep to 5-8 core steps. Detailed procedures in appendix. Quick reference card for daily use.

3. **Roles Not Clear**: SOP doesn't specify who does each step. Assumption: "Everyone knows." Result: Wrong person does it, or nobody does it (each assumes other will). Better: Every step lists role: "Sales Rep", "Onboarding Manager", "Tech Lead".

4. **No Success Metrics**: SOP gets executed, but nobody knows if it's working. Is {{metric]] good or bad? Better: Define metrics ({{% onboarded in SLA}}), track monthly, alert if trending bad.

5. **Approval Blurry**: SOP never specifies who approves completion. Result: Work gets done but never signed off. Confusion on state. Better: "Manager approves completion once customer has processed first invoice (sign in CRM: 'Onboarding Complete')."

