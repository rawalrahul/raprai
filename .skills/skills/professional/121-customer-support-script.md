---
name: customer-support-script
description: "Create customer support frameworks with greeting templates, triage decision trees, empathy statement libraries, escalation criteria, resolution confirmation, CSAT prompts, knowledge base templates, and SLA response guidelines by severity."
category: professional
difficulty: intermediate
model_boost: "Weak models lack empathy layering, proper triage logic, or SLA-aware response severity calibration"
---

# Customer Support Script

## Purpose
Quality support scripts ensure consistency, speed, and customer satisfaction. They provide guardrails so representatives don't improvise under pressure, reducing response time variance and improving first-contact resolution. Scripts are not robotic; they're frameworks that blend empathy, technical knowledge, and process discipline. They also create training curriculum for new support hires. This skill combines service recovery psychology, triage logic, and knowledge management into reusable workflows.

## When to Use
- **Building support team playbooks** (new team or quality initiative)
- **Improving CSAT and reducing ticket escalations** (process standardization)
- **Training new support hires** (scripts are the onboarding curriculum)
- **Creating SLAs and severity classifications** (when you need consistent response standards)
- **Do NOT use when**: Handling highly anomalous or sensitive situations (e.g., abuse, data breach response), or providing technical deep-dives that require subject-matter expertise (those need specialized technical docs, not scripts)

## Instructions

### Step 1: Design the Support Greeting & Tone Foundation
Set the customer's first impression. Greeting should be warm, professional, and invite dialogue.

**Standard Greeting** (Email or Chat):
"Hi [Customer Name],

Thanks for reaching out! I'm [Your Name], and I'm here to help. I've reviewed your message and want to make sure I understand the situation fully.

[Restate their issue in your own words]

Let me walk you through some solutions. If you have any questions along the way, just ask—I'm here to help."

**Urgent Greeting** (If severity is High/Critical):
"Hi [Customer Name],

Thanks for flagging this. I can see this is impacting your [production/business critical workflow], and I want to resolve this quickly.

I'm [Your Name]. Here's what I'm going to do: [Immediate action]. In parallel, I'm looping in [team/specialist] to [specific action].

I'll update you within [timeframe]. In the meantime, here's a workaround to keep you moving: [Workaround if available]."

**Empathy Tone** (If customer is frustrated):
"Hi [Customer Name],

I can see you've been working on this issue for [time period], and I understand how frustrating that must be. I appreciate your patience.

Here's what we're going to do differently this time: [Specific action plan]. You've given me great details; let me make sure we get this resolved."

### Step 2: Build a Triage Decision Tree
Not all issues are equal. Map severity based on impact (business impact + number of customers affected + data risk).

**Severity Tiers**:

**Critical (P1)**:
- Production/revenue-impacting (customers can't use core feature)
- Data loss or security risk
- Affects multiple customers
- Response SLA: 1 hour | Resolution target: 4 hours

**High (P2)**:
- Significant functionality broken (workaround exists but tedious)
- Affects one key customer or revenue-impacting
- Response SLA: 2 hours | Resolution target: 24 hours

**Medium (P3)**:
- Feature not working as expected; customer can work around it
- Non-critical workflow impacted
- Response SLA: 8 hours | Resolution target: 3 business days

**Low (P4)**:
- Feature request or documentation improvement
- Minor UI bug or cosmetic issue
- Response SLA: 24 hours | Resolution target: 7 business days

**Triage Decision Tree**:

```
INTAKE DECISION TREE

Is the issue blocking production or core workflow?
├─ YES: Does it affect multiple customers OR customer's primary use case?
│  ├─ YES → CRITICAL (P1)
│  └─ NO, but data is at risk → CRITICAL (P1)
│  └─ NO, single customer, workaround exists → HIGH (P2)
├─ NO: Is the customer unable to perform any meaningful work?
│  ├─ YES → HIGH (P2)
│  └─ NO: Can they work around it or use alternative feature?
│     ├─ YES → MEDIUM (P3)
│     └─ NO → HIGH (P2)
└─ NO: Is it a feature request or cosmetic issue?
   └─ YES → LOW (P4)

ESCALATION TRIGGER:
├─ If customer is upset AND issue persists 24h+ → Escalate to manager
├─ If technical investigation exceeds 4 hours AND issue is P1/P2 → Escalate to engineering
├─ If customer requests manager or escalation → Escalate (honor request)
```

### Step 3: Develop an Empathy Statement Library
Customers want to feel heard. Use these frameworks; don't just state facts.

**Acknowledgment of Frustration**:
- "I can see you've been trying to resolve this for [X days]. That must be frustrating."
- "I understand this is blocking your [use case]. Let me prioritize this."
- "Your feedback is valuable; we clearly missed the mark here."

**Validation of Impact**:
- "You're right—this shouldn't happen. Here's why it did [brief reason], and here's how we'll prevent it."
- "I can see this is affecting your ability to [outcome]. That's unacceptable on our end."
- "You've invested time in this; I'm going to make sure we fix it properly."

**Commitment to Ownership**:
- "I'm going to own this end-to-end and keep you in the loop every step."
- "This is my top priority today. You'll hear from me by [specific time] with an update."
- "I'm not handing this off. I'll be the single point of contact until it's resolved."

**Recovery / Service Recovery**:
- "We dropped the ball here. In addition to fixing the issue, I'd like to [offer credit / extend trial / recognize impact]."
- "This shouldn't have happened. Here's what we're doing to prevent it, and here's how we're making it right."

### Step 4: Create Ticket Response Templates by Issue Type
Standard responses speed up support and ensure consistency. Customize each with the customer's specific details.

**Template 1: Password Reset / Access Issue**

"Hi [Name],

I see you're having trouble logging in. Here's how we'll fix this:

**Immediate fix (try this first):**
1. Go to [login page]
2. Click "Forgot Password"
3. Enter your email: [email]
4. Click the reset link in your email (check spam folder)
5. Set a new password

**If that doesn't work:**
[Alternative steps or escalation to technical team]

**Still stuck?**
Reply with:
- What error message you see (screenshot if possible)
- What browser and device you're using
- Whether you've tried multiple times

I'll get back to you within [SLA time]. If you need access urgently, let me know and I can escalate to our engineering team to reset your account manually.

Thanks,
[Your Name]"

**Template 2: Feature Not Working as Expected**

"Hi [Name],

Thanks for the detailed report on [issue]. I've tested this on my end and can reproduce it. Here's what's happening:

**The issue:** [Technical explanation in plain English]

**Why it matters:** [How it affects them]

**What we're doing:**
- Our engineering team has confirmed this is a bug (ticket: [#ID])
- We're working on a fix, targeting [date/release]
- Interim workaround: [Steps to work around it]

**What you can do now:**
[Workaround steps]

I'll send you an update [weekly / when fixed]. If this is blocking your work, reply and let me know; we may be able to prioritize this.

Thanks for your patience,
[Your Name]"

**Template 3: Integration Not Working**

"Hi [Name],

I see your [integration name] sync failed. Let me walk you through the troubleshooting:

**Common causes and fixes:**

1. **API key expired or revoked?**
   - Go to [your external service settings] and regenerate your API key
   - Paste the new key into [our integration settings]
   - Test the connection

2. **Rate limit hit?**
   - We sync every [frequency]; your account may be hitting rate limits
   - Solution: [Increase limits on the external service OR adjust sync frequency]

3. **Data mapping changed?**
   - Your [external service] schema may have changed
   - Solution: [Re-map fields] or [refresh connection]

**If you've tried these:**
Reply with:
- Last successful sync date
- Error message from the integration dashboard (screenshot helps)
- Your API key details (last 4 digits only for security)

I'll dig into our logs and get back to you within [SLA].

Thanks,
[Your Name]"

**Template 4: Billing / Subscription Question**

"Hi [Name],

Thanks for asking about [billing question]. Here's what I found:

**Your current plan:** [Plan name, cost, renewal date, features]

**About the charge for [amount]:**
- This is for [what it covers] from [date] to [date]
- Your invoice is available here: [link]

**If you have concerns:**
- You can modify your plan here: [link]
- Prorated credits will apply if you downgrade
- Annual plans are non-refundable but can be paused

**Other options:**
- Upgrade to [plan] if you need [feature]
- Contact our billing team: [email] for custom arrangements

Let me know if you have questions, or if you'd like me to help you adjust your plan.

Thanks,
[Your Name]"

### Step 5: Build Escalation Criteria & Handoff Scripts
Know when and how to escalate. Clear handoffs prevent customer frustration.

**Escalation Criteria**:

**Escalate to Technical Team** when:
- Initial troubleshooting (3+ steps) doesn't resolve the issue
- Issue requires code review or database access
- Multiple customers report the same bug (possible widespread issue)
- Root cause is unclear after 1 hour of investigation

**Escalate to Manager** when:
- Customer is dissatisfied after multiple support interactions
- Customer requests a manager or escalation explicitly
- Issue touches billing, contracts, or contractual SLA terms
- Potential reputational or legal risk

**Escalate to Product** when:
- Customer requests a feature that impacts core product direction
- Multiple customers report the same missing feature
- Issue involves usability or UI improvement feedback

**Handoff Script** (to customer):

"Hi [Name],

I've investigated your issue and need to get our specialized team involved to solve this properly. Here's what I'm doing:

**Who I'm looping in:** [Team/person name and title]
**Why them:** [They handle [type of issue] and have access to [system/data]]
**What happens next:** They'll review everything I've documented and reach out within [time] with next steps
**Your point of contact:** [Name], but I'll stay looped in to make sure this gets resolved

You might see a new email from [team]; that's expected. I've given them full context, so you won't need to repeat yourself.

Thanks for your patience. We're going to get this sorted.

[Your Name]"

### Step 6: Create Resolution Confirmation & Closure Protocol
Confirm the issue is actually resolved. This prevents "solved but reopened" tickets.

**Resolution Confirmation** (before closing):

"Hi [Name],

I want to make sure we've fully resolved your issue before I close this ticket.

**What we did:**
- [Action taken]
- [Result achieved]

**Can you confirm:**
1. You've tried the solution on your end?
2. The issue is now resolved (or workaround is working)?
3. You don't need anything else from us?

Once you confirm, I'll close this ticket. If you run into anything else, just reply and it'll reopen.

Thanks,
[Your Name]"

**Closure Message** (if customer confirms):

"Perfect! I'm closing this ticket. If the issue comes back or you need anything else, just reply here and it'll reopen automatically.

Thanks for reaching out, and sorry for the trouble. We appreciate your patience.

[Your Name]"

### Step 7: Design CSAT Survey & Follow-Up
Measure satisfaction and identify improvement opportunities.

**CSAT Survey** (sent after ticket closure):

"We'd love your feedback on your support experience!

**How satisfied are you with the support you received?**
- Very satisfied
- Satisfied
- Neutral
- Dissatisfied
- Very dissatisfied

**Any additional comments?** [Open text field]

[Optional: "Would you like a manager to follow up?" checkbox]"

**Follow-up if Dissatisfied**:
"Hi [Name],

I saw your feedback that you were dissatisfied with your support experience. I want to understand what went wrong so we can do better.

**Can you tell me:**
- What could we have done differently?
- Was the response time an issue?
- Did we miss something in our solution?

I'd like to personally ensure your issue is truly resolved. Can we hop on a quick call?

[Calendar link]

Thanks,
[Your Name]"

### Step 8: Build Knowledge Base Article Templates
Support documents become reference material. Structure them for self-service.

**Knowledge Base Template**:

```
# [Clear Problem Title]

## Quick Answer
[One-sentence summary for busy users]

## The Detailed Guide

### What is this issue?
[Explain the problem in plain English; not jargon]

### Why does it happen?
[Briefly explain root cause; help users understand]

### How to fix it

**Step 1: [Action]**
[Screenshot if helpful]
[Why this step matters]

**Step 2: [Action]**
[Screenshot if helpful]

### Troubleshooting

**If you see Error X:**
→ Try [solution]

**If that doesn't work:**
→ Check [thing] and then try [solution]

### Still stuck?
[Contact support link]
[Expected response time]

## Related Articles
[Link to similar issues or related features]

## Last updated
[Date] by [Author]
```

### Step 9: Create SLA Response Templates by Severity
Tailor response time and initial message to severity.

**P1 (Critical) - 1-Hour Response**:

"Hi [Name],

I'm on it. I've just:
- [Immediate action #1]
- [Immediate action #2]
- Looped in [specialist] to [investigate/fix]

**Status:** [Current state]
**Next update:** [Time] today

I'll keep you in the loop every [30 min / hour] until this is resolved.

[Your Name]"

**P2 (High) - 2-Hour Response**:

"Hi [Name],

Thanks for reporting this. I understand this is affecting [your work], and I'm prioritizing it.

Here's what I found:
- [Initial investigation result]

Here's what we're doing:
- [Next steps, with rough timeline]

I'll update you by [time] with more details.

[Your Name]"

**P3 (Medium) - 8-Hour Response**:

"Hi [Name],

Thanks for the report. I've reviewed your issue and here's the initial assessment:

[Assessment + what we're doing]

Timeline: We're targeting resolution by [date].

I'll update you [daily / when resolved].

[Your Name]"

**P4 (Low) - 24-Hour Response**:

"Hi [Name],

Thanks for reaching out. I've added this to our backlog.

[Assessment + why it's prioritized at this level]

Typical timeline: [Estimate]

We'll update you when we have progress to share.

[Your Name]"

### Step 10: Build Quality & Consistency Checkpoints
Before sending any support response:

- [ ] **Empathy check**: Did I acknowledge the customer's situation? Would they feel heard?
- [ ] **Clarity check**: Would a non-technical person understand my response? No jargon; plain English.
- [ ] **Completeness check**: Did I provide enough information to either resolve or escalate? Or will they have to reply with more questions?
- [ ] **Tone check**: Does my response match the severity? P1 critical issue shouldn't have a casual tone.
- [ ] **Action clarity check**: Does the customer know what to do next? Is the next step clear (troubleshoot, wait for escalation, etc.)?

## Output Template

```
---
SUPPORT SCRIPT LIBRARY
Version: 1.0
Last Updated: [MM/DD/YYYY]
Maintained by: [Support Manager]
---

# Support Framework

## 1. Severity Classifications & SLAs

| Severity | Definition | Response SLA | Resolution Target |
|----------|------------|--------------|-------------------|
| P1 - Critical | Production-blocking, data risk, multi-customer | 1 hour | 4 hours |
| P2 - High | Key feature broken, single customer revenue impact | 2 hours | 24 hours |
| P3 - Medium | Feature not working, workaround exists | 8 hours | 3 business days |
| P4 - Low | Feature request, cosmetic, documentation | 24 hours | 7 business days |

## 2. Triage Decision Tree
[Insert decision tree]

## 3. Empathy Statement Library

**Frustration acknowledgment:**
- [Option 1]
- [Option 2]
- [Option 3]

**Impact validation:**
- [Option 1]
- [Option 2]

**Ownership commitment:**
- [Option 1]
- [Option 2]

## 4. Response Templates

### Template: Password/Access Issue
[Full template]

### Template: Feature Not Working
[Full template]

### Template: Integration Issue
[Full template]

### Template: Billing Question
[Full template]

## 5. Escalation Criteria & Scripts

**When to escalate to Technical:**
[Criteria list]

**When to escalate to Manager:**
[Criteria list]

**Handoff script:**
[Script]

## 6. Resolution & Closure

**Confirmation message:**
[Template]

**Closure message:**
[Template]

## 7. CSAT & Follow-Up

**Survey template:**
[Survey]

**Dissatisfaction follow-up:**
[Template]

## 8. Knowledge Base Article Template
[Template structure]

## 9. SLA-Specific Response Templates

**P1 Critical response:**
[Template]

**P2 High response:**
[Template]

**P3 Medium response:**
[Template]

**P4 Low response:**
[Template]

## 10. Quality Checklist

- [ ] Empathy: Customer feels heard
- [ ] Clarity: Non-technical user understands
- [ ] Completeness: No additional questions needed
- [ ] Tone: Matches severity level
- [ ] Action clarity: Next step is obvious
```

## Quality Gates

1. **SLA Adherence Test**: Set up a support ticket. Does your team respond within the SLA for that severity? If not, adjust SLAs or add staffing.

2. **Template Authenticity**: Have a rep read a template aloud. Does it sound natural, or robotic? If robotic, rewrite for conversational tone.

3. **Empathy Layering**: Review a closed ticket. Did the rep use at least one empathy statement? If not, coach and retrain.

4. **Escalation Discipline**: Audit 20 tickets. Did escalations follow the decision tree? If not, clarify criteria.

5. **Knowledge Base Coverage**: List your top 20 ticket issues. Are 80%+ covered in the knowledge base? If not, create articles for the gaps.

6. **CSAT Response Rate**: Is your CSAT survey response rate above 40%? If not, move it to immediately after ticket closure or send it via SMS.

## Examples

### Good Support Interaction

**Customer ticket**: "Your app keeps crashing when I try to export reports. I've been working on this for 2 days. Help!"

**Support response** (P2 - High):

"Hi Sarah,

I can see you've been troubleshooting this for 2 days, and I understand how frustrating that must be. I'm going to solve this.

Here's what I found: The crash happens when reports exceed 100K rows. We've identified this as a bug (ticket #5847) and are working on a fix for next week's release.

**Immediate workaround (use this today):**
1. Filter your data to last 6 months (reduces row count)
2. Export that subset
3. Repeat for earlier data if needed

This keeps you moving while we fix it.

**What's next:**
- I'm looping in our engineering team to see if we can rush the fix
- I'll update you by EOD tomorrow with an ETA
- You'll get early access to the fixed version before public release

Thanks for catching this and for your patience.

[Support agent]"

**Why it works**: Acknowledges frustration, provides immediate workaround, explains the issue, commits to next steps with timeline, offers recovery (early access).

### Bad Support Interaction

**Customer ticket**: "Your app keeps crashing when I try to export reports. I've been working on this for 2 days. Help!"

**Support response**:

"Hi Sarah,

Thanks for reaching out. Can you provide more details about the crash?

- What version are you using?
- What browser?
- Can you screenshot the error?

Once I have this info, I can look into it.

[Support agent]"

**Why it fails**: No empathy for the 2-day struggle. Puts burden on customer to gather debug info. Doesn't offer workaround or timeline. Doesn't make customer feel prioritized.

## Common Mistakes

1. **SLA mismatches between what's promised and what's delivered**: Marketing promises 2-hour response, but typical response is 6 hours. Set realistic SLAs and meet them consistently.

2. **Escalation avoidance**: Agent spends 4 hours investigating when the right path is escalation at hour 1. Clear escalation criteria and empower agents to escalate.

3. **Knowledge base not linked in responses**: Agent writes a detailed email response that could have been a link to existing KB article. Train agents to link KB articles and reduce duplicate support work.

4. **Tone misalignment**: P1 critical issue gets a casual response ("Hey, I looked into this..."). Match tone to severity.

5. **Not following up with escalations**: Customer's issue is escalated to engineering, but support doesn't follow up. Set a calendar reminder to check on escalations weekly.

6. **Skipping the resolution confirmation**: Agent assumes issue is fixed and closes the ticket; customer reopens it the next day. Always confirm before closing.

## Anti-Patterns

1. **The template-first approach**: Agent uses template verbatim without customizing to the customer. Templates are guides; personalize them with customer's specific situation and names.

2. **Closing without resolution**: Closing a ticket after sending a solution suggestion, without confirming the customer tried it. Keep ticket open until customer confirms resolution.

3. **Ignoring repeat issues**: Same bug reported 5 times in a month, but not prioritized until it's reported by a VIP customer. Track recurring issues and escalate to product/engineering after 3 reports.

4. **No ownership for escalations**: Issue is escalated but no single person owns follow-up. Assign one support agent as owner, even if engineering is investigating. They're the customer's single point of contact.

5. **Billing/contracts handled casually**: Support agent offers discount without consulting manager/billing. Escalate billing and contract questions; don't improvise.
