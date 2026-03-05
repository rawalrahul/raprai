---
name: contract-reviewer
description: "Analyze contracts for key terms, flag risks, track obligations, and summarize in plain language to identify red flags before signing (not legal advice)."
category: finance
difficulty: intermediate
model_boost: "Fixes signing contracts blindly and missing unfavorable terms until too late"
---

# Contract Reviewer

## Purpose

Most people skim contracts, sign, and regret it later. A systematic review process surfaces hidden risks, clarifies obligations, and flags unfavorable terms *before* you sign. This skill provides a checklist for key terms, a risk-flagging framework, and a plain-language summary template. You'll exit with a checklist you can apply to any contract and a summary that prevents surprises.

**Legal disclaimer**: This skill is for your own review and understanding, not legal advice. For major contracts (real estate, employment, partnerships), consult a lawyer.

## When to Use

- You're about to sign a contract (employment, service agreement, purchase, lease, partnership)
- You're reviewing a term sheet or major agreement
- You want to understand what you're committing to before signing
- You want to identify red flags or unusual terms
- **Do NOT use when**: You lack domain expertise (e.g., securities law), the contract is very complex (use a lawyer), or you're signing in crisis mode (take time to review)

## Instructions

### Step 1: Identify Contract Type and Parties

**Contract types** (each has different key terms):
- **Employment Agreement**: Salary, benefits, restrictive covenants, IP assignment
- **Service Agreement (B2B)**: Scope of work, payment terms, liability, termination
- **Purchase Agreement**: Product, price, delivery, warranties, return policy
- **Lease**: Rent, term, maintenance, termination, early exit
- **NDA (Non-Disclosure)**: What's confidential, duration, exceptions
- **Partnership/Operating Agreement**: Roles, ownership, profit split, dispute resolution
- **Vendor/SaaS Agreement**: Service levels, pricing, data rights, termination

**Parties involved**:
- Your name / company name (sign as which entity?)
- Other party / company (who are you agreeing with?)
- Guarantors (who else is responsible if you default?)

Write these down. Seems obvious but errors here are expensive.

### Step 2: Identify the Core Commercial Terms

Every contract has commercial core—what you're trading.

**Employment**:
- Salary: $X/year, paid [frequency]
- Sign-on bonus: $Y (paid when?)
- Stock options: Vesting schedule, strike price, how many
- Benefits: Health, 401k match, paid time off
- Severance: What if you're fired? Laid off?

**Service Agreement**:
- Scope of work: What exactly are you delivering?
- Timeline: When do you deliver?
- Payment: $X total, paid when? (upfront, in milestones, on completion?)
- Change requests: What if customer wants changes? How do you bill?

**Purchase**:
- Product: Exactly what are you buying? (SKU, quantity)
- Price: Total cost, payment terms, any volume discounts?
- Delivery: Who pays shipping? When do they deliver?
- Warranty: Does it come with a guarantee? For how long?

**Lease**:
- Rent: $X/month, paid to whom, due when?
- Term: Start date, end date, renewal options
- Maintenance: Who fixes what? (Landlord fixes structure, tenant fixes cosmetic)
- Early exit: Can you break the lease? Penalty?

Write down the "deal." If you can't summarize it in 2-3 sentences, something's unclear.

### Step 3: Build Your Contract Review Checklist

Use this checklist for any contract type.

```
GENERAL CHECKLIST (All Contracts)

[ ] Contract Title and Parties
    - [ ] My name/entity is spelled correctly
    - [ ] Other party's legal name is correct
    - [ ] Effective date is specified
    - [ ] Term/duration is clear

[ ] Consideration (What am I getting?)
    - [ ] The core exchange is clear (I do X, they pay $Y)
    - [ ] Payment amounts are explicit (not vague)
    - [ ] Payment schedule is defined (when do I get paid?)

[ ] Obligations (What am I agreeing to do?)
    - [ ] My responsibilities are clearly stated
    - [ ] Success criteria are measurable (not subjective)
    - [ ] Timelines are realistic
    - [ ] Are there "unlimited" or "best efforts" clauses? (RISK)

[ ] Liability & Insurance
    - [ ] Am I liable for damage, losses, or third-party claims?
    - [ ] Is there a liability cap? (e.g., "not more than the contract amount")
    - [ ] Are there exclusions? (e.g., "not liable for indirect damages")
    - [ ] Do I need insurance? Who's the named beneficiary?

[ ] Intellectual Property (IP)
    - [ ] Who owns the work I create? (Me or the client?)
    - [ ] Can I use it for my portfolio or past work?
    - [ ] Are there preexisting IP rights? (Libraries, frameworks I use)

[ ] Confidentiality & Restrictions
    - [ ] What information is confidential? (Too broad?)
    - [ ] Duration: How long does confidentiality last?
    - [ ] Non-compete: Am I restricted from working with competitors? (How broadly?)
    - [ ] Non-solicitation: Can I recruit from them / can they recruit me?

[ ] Termination
    - [ ] How do I get out? (Notice period? Penalty?)
    - [ ] What happens to unpaid work? (Do I get paid for work done?)
    - [ ] What happens to my obligations after termination? (Do non-competes survive?)

[ ] Dispute Resolution
    - [ ] How do we resolve disagreements? (Mediation? Arbitration? Court?)
    - [ ] In which state/country's laws?
    - [ ] Who pays legal fees if there's a dispute?

[ ] Amendment & Severability
    - [ ] Can this contract be modified? (By whom? How?)
    - [ ] If one part is deemed unenforceable, do other parts survive?

[ ] Entire Agreement
    - [ ] Is this the full agreement? (Or are there side letters, emails?)
    - [ ] What versions/exhibits are included?

TYPE-SPECIFIC CHECKLIST (Employment)

[ ] Compensation & Benefits
    - [ ] Salary is explicit (not "competitive" or TBD)
    - [ ] Benefits: Health, dental, vision, retirement match
    - [ ] PTO: Vacation, sick days, parental leave
    - [ ] Bonus structure: How much? When? (Guaranteed or discretionary?)

[ ] Stock Options (if applicable)
    - [ ] Vesting schedule: [4-year vesting, 1-year cliff is standard]
    - [ ] Strike price: Set fairly or deeply underwater?
    - [ ] What happens to options if you're fired or leave?
    - [ ] Can they change the strike price? (Red flag if yes)

[ ] Severance
    - [ ] Notice required: How much notice to fire you? (e.g., 30 days)
    - [ ] Severance if fired without cause: [X weeks/months]
    - [ ] Severance if you resign: Typically $0 (but may vary)
    - [ ] Severance if company is acquired: (Sometimes included)

[ ] Restrictive Covenants
    - [ ] Non-compete: Can't work for competitors for [X time, X geography]
    - [ ] Non-solicitation: Can't recruit employees or clients for [X time]
    - [ ] Are these enforceable in your state? (California: basically void. Others: varies)

[ ] IP Assignment
    - [ ] Does the company own everything you create? (Usually yes)
    - [ ] Exceptions: Work on your own time, using own equipment, unrelated to company?

TYPE-SPECIFIC CHECKLIST (Service Agreement)

[ ] Scope of Work
    - [ ] What exactly am I delivering? (Be specific; avoid "etc.")
    - [ ] Out of scope: What am I NOT responsible for?
    - [ ] Deliverables: Code, documents, presentations? Formats?

[ ] Timeline
    - [ ] When does work start?
    - [ ] Milestones: What do I deliver when?
    - [ ] Final deadline: Clear date?
    - [ ] Are there contingencies if customer is slow? (e.g., "timeline assumes timely feedback")

[ ] Payment Terms
    - [ ] Total contract value: Clear number?
    - [ ] Payment schedule: Upfront, milestone-based, on completion?
    - [ ] What if they don't pay? (Late fees? Can I stop work?)

[ ] Change Requests
    - [ ] How do we handle scope changes? (New contract? Change order? Verbal?)
    - [ ] Additional cost: Who decides if changes are paid? (Red flag: "at company discretion")
    - [ ] Scope creep risk: What prevents this? (Answer: clear scope + formal change process)

[ ] Liability & Warranties
    - [ ] Do I warrant the work is original and error-free? (RISK: hard to guarantee)
    - [ ] Am I liable if the work causes damage / loss? (How much? Capped?)
    - [ ] What if they use the work for something different than intended? (RISK: broad use)

[ ] Confidentiality
    - [ ] What information is confidential?
    - [ ] Does the NDA survive the contract end? (How long?)
    - [ ] Can I reference this project in my portfolio? (Red flag: no)

[ ] Termination
    - [ ] Can they terminate early? (With notice? Penalty?)
    - [ ] What happens to incomplete work? (Payment for work done?)
    - [ ] Transition: Do I have to hand over everything?
```

### Step 4: Flag Risks and Red Flags

Common problematic terms:

**Indemnification** (MAJOR RISK):
- "You agree to indemnify us against all claims arising from your work"
- Translation: If they get sued, you pay for their legal defense + any judgment
- Risk: Massive, undefined liability
- Solution: Negotiate cap ("indemnity capped at total contract value")

**Unlimited Liability**:
- "Your liability is unlimited"
- Translation: If something goes wrong, you could owe millions
- Solution: Push for cap ("liability capped at 12 months of fees" or "1x contract value")

**Unlimited Scope** ("etc.," "and other services as requested"):
- Translation: Work keeps expanding; they control scope
- Solution: Define scope precisely; add change order process

**Broad IP Assignment** ("all work you create belongs to us"):
- Translation: Even code you wrote on your own time, using your own laptop, belongs to the client
- Risk: If you've done similar work elsewhere, you could be sued
- Solution: Carve out exceptions ("code created outside of work, unrelated to company purpose")

**Non-Compete** (Varies by state):
- "You can't work for competitors for 2 years within 50 miles"
- Risk: Very restrictive; limits your future job prospects
- Solution: Narrow the geographic area and duration; check if enforceable in your state (many aren't)

**Unilateral Modification** ("Company can change terms at any time"):
- Translation: They can change contract mid-project; you're stuck
- Solution: Require mutual agreement to modify; or specify what they can't change (pricing, termination)

**Mandatory Arbitration** (vs. court litigation):
- Translation: You waive right to sue in court; must arbitrate
- Risk: Arbitration is faster but less transparent; binding decisions
- Solution: Accept if arbitration is in your city; reject if you'd have to travel

**Entire Agreement** ("This supersedes all prior agreements"):
- Translation: Ignore emails, verbal commitments, LOIs; only the signed contract matters
- Solution: Insist that side letters or prior understandings are documented as addendums before signing

### Step 5: Create a Plain-Language Summary

Translate the contract into simple terms. This clarifies your obligations and catches missed details.

```
PLAIN LANGUAGE SUMMARY: Employment Agreement with TechCorp

The Deal:
I will work full-time as Senior Engineer at TechCorp for 3 years, starting April 1, 2026.
In exchange, they'll pay me $150,000/year + $30,000 sign-on bonus + health insurance + 401k.

My Obligations:
1. Work full-time, report to VP Engineering
2. Own the backend API architecture (scope defined in Exhibit A)
3. Maintain confidentiality of company info (proprietary code, business plans, customer data)
4. Don't work for competitors or recruit employees for 18 months after I leave
5. Assign all IP created at work to TechCorp

Their Obligations:
1. Pay salary monthly
2. Provide health, dental, vision insurance
3. Match 401k up to 4%
4. 20 days PTO per year
5. Stock options: 40,000 shares, 4-year vesting, 1-year cliff, strike price $5

Exit Scenarios:
- If they fire me without cause: I get 3 months severance + 3 months COBRA
- If I resign: I get nothing, but equity vests on last day worked
- If company is acquired: Same terms apply (no acceleration)

Red Flags I Notice:
1. Non-compete is 18 months and state-wide (broad; limits future jobs)
2. Severance is only if fired without cause (not if laid off due to restructuring—clarify)
3. Stock options have 1-year cliff (I lose everything if I leave before month 13)
4. Indemnification clause is broad—they can make me pay their legal fees if sued

Before signing, I need to:
- Clarify severance for layoffs (push for same as "without cause")
- Reduce non-compete to 6 months and limit to direct competitors
- Ensure options vest even if acquired
- Negotiate indemnification cap
```

### Step 6: Negotiate (Before Signing)

Armed with your summary and red flags, negotiate.

**Negotiation approach**:

1. **Identify high-priority changes** (2-3 that matter most to you)
2. **Propose alternatives** (don't just complain; offer solutions)
3. **Explain reasoning** (they're more likely to agree if they understand why)
4. **Get it in writing** (emails or addendum, not verbal)
5. **Walk away if needed** (better to decline than sign a bad deal)

**Example**:

*Red flag*: "Non-compete is 18 months, state-wide"

*Your proposal*: "I'm comfortable with 6-month non-compete limited to [Direct competitors: Stripe, Square, others in payments]"

*Reasoning*: "18 months limits my career opportunities. 6 months and a limited list are fair protections for TechCorp without preventing me from working in adjacent spaces."

*Outcome*: Often they'll accept this or meet you at 12 months and geographic limit (e.g., "San Francisco Bay Area"). Get agreement in writing before signing.

### Step 7: Document Your Review and Get Legal Review (If Needed)

**For major contracts** (employment, partnerships, real estate):
- Cost of lawyer: $500-2,000
- Cost of signing bad contract: Potentially unlimited
- Worth it? Usually yes.

**For minor contracts** (small service agreements, standard SaaS terms):
- Run through your checklist
- Flag red flags
- Negotiate key terms
- Sign if satisfied

**Document your review**:
```
CONTRACT REVIEW LOG

Contract: [Name]
Date Reviewed: [Date]
Reviewed by: [You]
Legal review? [Yes/No, and by whom]

Key Terms Summary:
[1-2 sentences on the deal]

Red Flags Identified:
1. [Flag 1]
2. [Flag 2]

Negotiated Changes:
1. [Change 1] - Status: [Accepted / Pending / Rejected]

Final Assessment:
[ ] Safe to sign
[ ] Proceed with caution (specific concerns noted)
[ ] Do not sign without further review

Notes: [Any additional context]
```

## Output Template

```
# Contract Review Summary

## Contract Details
- Type: [Employment / Service / Purchase / Lease / Other]
- Parties: [Your name] and [Other party]
- Date reviewed: [Date]
- Signed? [Yes/No]

## Plain Language Summary
[1 paragraph: what's the deal?]

## Core Commercial Terms
- [Term 1]: [Description]
- [Term 2]: [Description]

## Red Flags Identified
1. [Flag 1]: [Why it matters]
2. [Flag 2]: [Why it matters]

## Recommended Changes
1. [Change 1]: From "[old]" to "[new]" - Rationale: [why]
2. [Change 2]: From "[old]" to "[new]" - Rationale: [why]

## Obligations (Mine)
- [Obligation 1]
- [Obligation 2]

## Obligations (Theirs)
- [Obligation 1]
- [Obligation 2]

## Risk Assessment
[ ] Low risk, safe to sign
[ ] Medium risk, negotiate changes first
[ ] High risk, get legal review

## Negotiation Status
- [ ] Ready to sign as-is
- [ ] Negotiating items: [List]
- [ ] Rejected / walked away

## Final Decision
[ ] Signed
[ ] Not signed (reason: [brief explanation])
```

## Quality Gates (5+)

1. **Summary Accurate**: Does your 1-paragraph summary match the contract? (If not, re-read.)
2. **Red Flags Specific**: Can you articulate *why* each flag matters, not just that it's a flag?
3. **Obligations Clear**: Could someone else read your summary and know what you're responsible for?
4. **Negotiation Proposed**: For each red flag, do you have a concrete counter-proposal?
5. **Major Contracts Reviewed by Lawyer**: For employment, partnerships, or >$50k deals, get legal eyes

## Examples

### Good Contract Review (Detailed, Negotiated)

**Contract**: Service Agreement for Web Design ($15,000)

**Red Flag 1**: "Scope is open-ended: homepage + 'other pages as mutually agreed'"

**Negotiation**: Push for "Homepage + 2 subpages (Services, About) specifically. Additional pages billed at $2,000/page."

**Red Flag 2**: "Indemnification: I'm liable for all claims arising from the work"

**Negotiation**: "Indemnity capped at contract value ($15,000). Does not include claims arising from client's use of the work beyond original specifications."

**Result**: Scope is now fixed (prevents creep); indemnity is capped (manageable risk). Safe to sign.

---

### Bad Contract Review (Skipped Review)

"It's a standard SaaS agreement; everyone signs these. I'll just sign."

Problems:
- Didn't read the contract
- Missed that you're liable for data breaches
- Missed that they can change pricing annually
- Missed 30-day termination notice for you, 60 days for them (asymmetric)
- Will regret this when circumstances change

## Common Mistakes (3+)

1. **Skipping Red Flags**: You see "indemnification" and don't understand it, so you ignore it. Don't. Red flags exist for a reason. Ask what it means.

2. **Verbal Commitments**: They verbally promise something (higher salary, stock acceleration) but it's not in the contract. Verbal doesn't matter. Get it in writing or assume it doesn't exist.

3. **Negotiation Paralysis**: You identify red flags but don't propose changes. Just ask. Worst they say is no. Often they'll accept or compromise.

4. **Signature Binding Without Clarity**: You sign without fully understanding. Contract is now binding. Don't sign if you're unclear. Ask questions first.

5. **Ignoring Entire Agreement Clause**: There's an email from the recruiter promising something. Contract says "this supersedes all prior agreements." Email promise doesn't count. Get every promise in the contract.

## Anti-Patterns (3+)

1. **Lawyer Theater**: You consult a lawyer, they find problems, you're scared, you walk away. Sometimes that's right. Sometimes lawyers are overly cautious. Get a second opinion or negotiation-focused lawyer, not just a risk-mitigation one.

2. **Perfectionism**: You spend 8 hours negotiating minor terms and miss the major ones. Focus on 2-3 high-impact changes. Don't nitpick everything.

3. **Late Review**: You're about to start work Monday, contract arrives Thursday. No time to review. Push back: "I need 48 hours to review; can we move start date to Wednesday?"

---

**Next Steps**: Pick a contract you're considering or recently signed. Run through the checklist. Write a plain-language summary. Identify top 3 red flags. Propose concrete changes if you haven't signed yet.
