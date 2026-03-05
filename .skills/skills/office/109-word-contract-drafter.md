---
name: word-contract-drafter
description: "Draft contracts and agreements in Word: recitals, definitions, obligations, liability, dispute resolution. NOT legal advice—this is structure and standard clauses."
category: office
difficulty: intermediate
model_boost: "Fixes weak contracts: missing key clauses, vague obligations, unclear liability limitations."
---

# Word Contract Drafter

## Purpose
Create contract documents with standard legal structure: recitals (context), definitions (precision), obligations (clear responsibilities), liability limits (risk management), and dispute resolution. This skill provides template language and arrangement, not legal advice. A well-structured contract prevents disputes by making expectations explicit.

## When to Use
- "Draft a contract for [service/product/partnership]"
- "Create an agreement with [vendor/client]"
- "Document the terms of [arrangement]"
- **Do NOT use when**: Seeking legal advice; interpreting law; or unusual/high-stakes contracts (always use a lawyer)

## Important Disclaimer
This skill provides contract structure and template language. This is NOT legal advice. Every contract should be reviewed by a lawyer in your jurisdiction before signing. Contract law varies by location (state, country). Industry-specific language may be needed. Use this for drafting; have an attorney review before execution.

## Instructions

### Step 1: Contract Header and Identifying Information
Professional formatting and clear identification.

**Contract Document Header**
```
                            STATEMENT OF WORK

This Statement of Work (this "SOW") is entered into as of {{Date}},
by and between:

{{YOUR COMPANY NAME}}, a {{State}} {{entity type}} ("Company")

AND

{{CLIENT/VENDOR NAME}}, a {{State}} {{entity type}} ("Client")

(Together, the "Parties")
```

**Alternative**: "Service Agreement", "Vendor Agreement", "Consulting Agreement", "Partnership Agreement" (title depends on nature)

**Metadata Section** (helps organize contracts)
```
SOW Number:              {{SOW-2024-0045}}
Effective Date:          {{March 1, 2024}}
Expiration Date:         {{March 1, 2025}}
Primary Contact (Company): {{Jane Doe, jane@company.com}}
Primary Contact (Client):  {{Bob Smith, bob@client.com}}
```

### Step 2: Recitals (WHEREAS Clauses)
Recitals provide context and intent; they're part of the contract but usually not enforceable on their own.

**Structure**
```
RECITALS:

WHEREAS, Company has expertise in {{expertise description}}; and

WHEREAS, Client seeks {{description of need or goal}}; and

WHEREAS, the Parties wish to engage with each other on the terms and
conditions set forth herein.

NOW, THEREFORE, in consideration of the mutual covenants and agreements
herein contained, and for other good and valuable consideration, the
receipt and sufficiency of which are hereby acknowledged, the Parties agree
as follows:
```

**Example (Real)**
```
WHEREAS, Company is a cloud infrastructure consulting firm specializing
in cost optimization and FinOps; and

WHEREAS, Client operates multi-cloud environments (AWS, Azure) and seeks
to reduce annual cloud spending by 20% while maintaining system reliability; and

WHEREAS, the Parties wish to enter into a consulting engagement on the
terms set forth in this SOW.
```

**Purpose**
- Recitals set the deal context
- If interpretation dispute arises, recitals clarify intent
- Keep recitals factual; avoid legal conclusions

### Step 3: Definitions Section
Precision prevents disputes.

**Format**
```
1. DEFINITIONS

As used in this {{Agreement/SOW}}, the following terms have the meanings
set forth below:

1.1 "{{TERM}}" means {{definition}}.

1.2 "{{TERM}}" means {{definition}}.

... [additional definitions]
```

**Common Definitions to Include**

```
1.1 "Confidential Information" means all non-public information disclosed
    by one Party to the other, including business plans, customer lists,
    technical data, and pricing, marked as confidential or reasonably
    understood to be confidential.

1.2 "Deliverables" means the specific outputs Company will provide, as
    detailed in Schedule A (attached).

1.3 "Services" means the consulting and technical services described in
    Section 2 of this Agreement.

1.4 "Work Product" means any documents, software, reports, or other
    materials created by Company in performance of the Services.

1.5 "Effective Date" means {{March 1, 2024}}, or if later, the date the
    last Party signs this Agreement.

1.6 "Term" means the period from the Effective Date through {{March 1, 2025}},
    unless earlier terminated per Section 8.

1.7 "Parties" means Company and Client, collectively.
```

**Drafting Tip**
- Define terms consistently throughout document (once defined, use same term everywhere)
- Use defined terms in all caps ({{TERM}}) for clarity
- Avoid circular definitions ("A is B, and B is A")

### Step 4: Scope of Work / Services
Clear scope prevents scope creep.

**Section Format**
```
2. SCOPE OF WORK

2.1 Services. During the Term, Company shall provide the following
    Services to Client:

    (a) {{Service 1 description}}
    (b) {{Service 2 description}}
    (c) {{Service 3 description}}

2.2 Deliverables. The Services shall result in the following Deliverables:

    (a) {{Deliverable 1}} - due {{date}}
    (b) {{Deliverable 2}} - due {{date}}
    (c) {{Deliverable 3}} - due {{date}}

    Deliverables are attached as Schedule A.

2.3 Exclusions. The following are expressly excluded and NOT part of this SOW:

    (a) {{Excluded item 1}}
    (b) {{Excluded item 2}}
    (c) {{Excluded item 3}}

    Any work outside the Scope requires a written change order.
```

**Real Example**
```
2.1 Services. Company shall provide cloud infrastructure audit and
    FinOps governance design, specifically:

    (a) Assessment of Client's current AWS and Azure infrastructure
    (b) Cost analysis and identification of optimization opportunities
    (c) Design of a FinOps governance framework
    (d) Recommendation report with prioritized cost-reduction initiatives

2.3 Exclusions. The following are NOT included:

    (a) Implementation of optimization recommendations (separate engagement)
    (b) Google Cloud services (not part of current environment)
    (c) Data migration or application refactoring
    (d) Ongoing support or maintenance (post-engagement)

    Any additional work must be documented in a written change order.
```

**Drafting Tip**
- In-scope must be specific enough to measure
- Out-of-scope should preempt scope creep (list what won't be done)
- Change order clause means any scope expansion requires written agreement

### Step 5: Obligations (Who Does What)
Clear responsibilities prevent finger-pointing.

**Company's Obligations**
```
3. COMPANY'S OBLIGATIONS

3.1 Delivery of Services. Company shall:

    (a) Provide Services in a professional and workmanlike manner,
        consistent with industry standards.

    (b) Deliver Deliverables by the dates set forth in Schedule A.

    (c) Assign qualified personnel to perform the Services.

    (d) Keep Client informed of progress via {{weekly | monthly}} status updates.

    (e) Maintain confidentiality of Client's sensitive information.

3.2 Compliance. Company shall comply with all applicable laws and
    regulations in performing the Services.
```

**Client's Obligations**
```
4. CLIENT'S OBLIGATIONS

4.1 Cooperation. Client shall:

    (a) Provide Company with necessary system access (AWS/Azure accounts,
        VPN, etc.) by {{date}}.

    (b) Designate a single point of contact for access requests and decisions.

    (c) Respond to information requests within {{X business days}}.

    (d) Dedicate {{X hours per week}} for interviews and reviews.

    (e) Review draft Deliverables and provide feedback within {{5 business days}}.

4.2 Information. Client shall provide accurate information needed for
    Company to complete the Services.

4.3 Third-Party Approvals. Client is responsible for obtaining any
    third-party approvals or licenses necessary for Company to access
    Client's systems.
```

**Drafting Tip**
- Obligations should be measurable/verifiable
- Timelines must be realistic (don't set deadlines you can't meet)
- Include what BOTH parties commit to (not one-sided)

### Step 6: Representations and Warranties
What each party is asserting as true.

**Company Represents**
```
5. REPRESENTATIONS AND WARRANTIES

5.1 Company represents and warrants that:

    (a) Company has the authority to enter into this Agreement.

    (b) Company's personnel performing Services are qualified and will comply
        with applicable laws.

    (c) Company will not infringe any third-party intellectual property rights
        in performing the Services.

    (d) Company is not under any obligation that would prevent performance
        of this Agreement.
```

**Client Represents**
```
5.2 Client represents and warrants that:

    (a) Client has the authority to enter into this Agreement.

    (b) Client owns or has licenses to all information provided to Company.

    (c) Client's use of the Deliverables will not infringe any third-party
        intellectual property rights.
```

**Disclaimer of Other Warranties**
```
5.3 EXCEPT AS EXPRESSLY SET FORTH IN THIS SECTION 5, COMPANY MAKES NO
    OTHER WARRANTIES, EXPRESS OR IMPLIED, INCLUDING ANY WARRANTY OF
    MERCHANTABILITY OR FITNESS FOR A PARTICULAR PURPOSE.
```

**Drafting Tip**
- Reps and warranties reflect what you're confident asserting
- Don't over-promise ("perfect quality", "guaranteed results")
- Limit to what you actually control

### Step 7: Limitation of Liability
Defines the ceiling on financial damages.

**Standard Limitation Clause**
```
6. LIMITATION OF LIABILITY

6.1 LIMITATION. EXCEPT FOR BREACHES OF CONFIDENTIALITY (SECTION 7) OR
    INFRINGEMENT OF INTELLECTUAL PROPERTY (SECTION 5.1(c)), AND EXCEPT
    FOR GROSS NEGLIGENCE OR WILLFUL MISCONDUCT, IN NO EVENT SHALL EITHER
    PARTY BE LIABLE FOR INDIRECT, INCIDENTAL, CONSEQUENTIAL, SPECIAL,
    PUNITIVE, OR LOST PROFITS DAMAGES, EVEN IF ADVISED OF THE POSSIBILITY
    OF SUCH DAMAGES.

6.2 CAP ON LIABILITY. EACH PARTY'S TOTAL LIABILITY UNDER THIS AGREEMENT
    SHALL NOT EXCEED THE FEES PAID (OR PAYABLE) IN THE TWELVE MONTHS
    PRECEDING THE CLAIM.

Example: If Company is paid $100K and causes damage of $500K due to
negligence, Company's maximum liability is $100K (not $500K).
```

**Interpretation**
- Cap on liability limits financial exposure
- Carve-outs (exceptions) ensure critical areas like data protection aren't limited
- Gross negligence is usually still liable (intentional bad acts aren't excused)

**Drafting Tip**
- Set cap at a defensible amount (usually 1x annual contract value)
- Carve out what matters: IP, confidentiality, data protection
- Make clear what damages are excluded (indirect losses, lost profit)

### Step 8: Indemnification (Hold Harmless)
One party agrees to cover losses caused by the other.

**Company Indemnifies Client**
```
7. INDEMNIFICATION

7.1 Company's Indemnity. Company shall defend, indemnify, and hold harmless
    Client from any claims, damages, losses, or expenses (including
    attorneys' fees) arising from:

    (a) Company's breach of this Agreement;

    (b) Company's infringement of third-party intellectual property rights;

    (c) Personal injury or property damage caused by Company's negligence;

    (d) Company's violation of applicable law.

    provided Client: (i) promptly notifies Company of the claim, (ii) gives
    Company sole control of defense (if not Company's breach), and
    (iii) cooperates in the defense.
```

**Client Indemnifies Company**
```
7.2 Client's Indemnity. Client shall defend, indemnify, and hold harmless
    Company from any claims arising from:

    (a) Client's use of the Deliverables beyond the scope authorized;

    (b) Client's breach of this Agreement;

    (c) Client-provided information that infringes third-party rights.
```

**Drafting Tip**
- Indemnification is about liability assignment
- Usually the party causing the problem indemnifies the other
- Conditions (prompt notice, sole defense control) protect the indemnifying party

### Step 9: Term and Termination
When the agreement starts, ends, and how to exit early.

**Term and Renewal**
```
8. TERM AND TERMINATION

8.1 Term. This Agreement shall commence on the Effective Date and continue
    through {{March 1, 2025}} (the "Initial Term"), unless earlier terminated
    per this Section 8.

8.2 Renewal. This Agreement may be renewed for {{additional one-year terms}}
    upon written agreement of both Parties at least {{60 days}} before
    expiration of the then-current Term.
```

**Termination for Convenience** (either party can exit)
```
8.3 Termination for Convenience. Either Party may terminate this Agreement
    without cause by providing {{30 days}} written notice to the other Party.

    If Client terminates for convenience:
    (a) Client shall pay Company for all Services rendered through the
        termination date plus {{any non-cancellable obligations}}.
    (b) Company shall deliver Work Product completed as of termination date.
```

**Termination for Cause** (breach-based)
```
8.4 Termination for Cause. Either Party may terminate immediately upon
    written notice if:

    (a) The other Party materially breaches this Agreement and fails to cure
        within {{15 days}} of written notice; OR

    (b) The other Party becomes insolvent or bankrupt.
```

**Effect of Termination**
```
8.5 Obligations Upon Termination.

    (a) Company shall immediately cease Services and return/destroy Client's
        Confidential Information.

    (b) Client shall pay all accrued fees through termination date.

    (c) Sections {{7 (Indemnification), 9 (Confidentiality), 10 (IP)}} shall
        survive termination indefinitely.

    (d) Confidentiality obligations survive {{2 years}} after termination.
```

**Drafting Tip**
- Termination for convenience allows either party to exit (fair but risky)
- Termination for cause protects you if other party breaches
- Clarify what survives termination (confidentiality, indemnification usually do)

### Step 10: Intellectual Property Ownership
Who owns what's created.

**Company-Created IP**
```
9. INTELLECTUAL PROPERTY

9.1 Ownership of Deliverables. Client shall own all right, title, and
    interest in the Work Product delivered under this Agreement, including
    all intellectual property rights.

    Client shall have a perpetual, royalty-free license to use the Work
    Product for its own business purposes.

9.2 Company Pre-Existing IP. Company retains all right, title, and interest
    in:

    (a) Tools, methodologies, and software developed by Company prior to
        this Agreement ("Pre-Existing IP");

    (b) Improvements or enhancements to Pre-Existing IP made during this
        engagement.

    Company grants Client a non-exclusive, royalty-free license to use
    Pre-Existing IP solely as incorporated in the Deliverables.

9.3 Third-Party IP. Client is responsible for ensuring it has rights to
    use any third-party materials provided to Company for incorporation
    in the Deliverables.
```

**Real Example (Consulting)**
```
- Reports you write = Client owns
- Your methodology, frameworks, analysis techniques = You own
- Client can use your framework in their reports, but not sell it
```

**Drafting Tip**
- Clarify what Client owns vs. what Company retains
- Distinguish between deliverables (usually Client owns) and methodology (usually Company owns)
- Third-party licenses should be addressed (who pays, who gets rights)

### Step 11: Confidentiality
How sensitive information is protected.

**Definition and Obligations**
```
10. CONFIDENTIALITY

10.1 Definition. "Confidential Information" means all non-public information
     disclosed by one Party to the other, including business plans, customer
     data, pricing, technical information, and any information marked
     confidential.

10.2 Obligations. The receiving Party shall:

     (a) Maintain Confidential Information in strict confidence;

     (b) Limit disclosure to employees/contractors with a need to know;

     (c) Protect Confidential Information using reasonable security measures
         (at minimum, as it protects its own confidential information);

     (d) NOT disclose to third parties without prior written consent,
         except as required by law (with advance notice).

10.3 Exceptions. Confidential Information does NOT include information that:

     (a) Is publicly available (not due to breach);

     (b) Was independently developed without reference to disclosed info;

     (c) Is received from a third party without confidentiality obligations;

     (d) Is required to be disclosed by law/regulation (with notice).

10.4 Return or Destruction. Upon termination, each Party shall, upon
     request, return or destroy Confidential Information (except one copy
     may be retained for legal compliance).
```

**Duration**
```
10.5 Survival. Confidentiality obligations shall survive termination of
     this Agreement for {{X years}} (commonly 2–5 years).
```

**Drafting Tip**
- Define what's confidential (more clarity = fewer disputes)
- Exceptions prevent over-broad restriction (standard exceptions: public info, independently developed)
- Duration should match sensitivity (trade secrets: longer; pricing: shorter)

### Step 12: Dispute Resolution
How to handle disagreements.

**Escalation Path**
```
11. DISPUTE RESOLUTION

11.1 Good Faith Negotiation. If a dispute arises, each Party shall attempt
     to resolve it through good-faith negotiation by senior executives within
     {{10 business days}} of written notice.

11.2 Mediation. If negotiation fails, the Parties shall submit to mediation
     in {{City, State}} before pursuing litigation. Costs split equally.

11.3 Litigation/Arbitration. If mediation fails:

     [Option A - Litigation]
     Each Party consents to exclusive jurisdiction and venue in the
     {{State}} courts; governed by {{State}} law (without regard to
     conflict of laws).

     [Option B - Arbitration]
     Disputes shall be resolved via binding arbitration administered by
     {{AAA/JAMS}} in {{City}}, per its Commercial Arbitration Rules.
     One arbitrator shall decide unless claim exceeds ${{X}}, then three
     arbitrators. Loser pays all arbitration costs and attorneys' fees.

11.4 Attorneys' Fees. The prevailing party may recover attorneys' fees and
     costs incurred in resolving disputes.
```

**Drafting Tip**
- Escalation path avoids jumping straight to lawyers (saves money)
- Mediation is faster/cheaper than litigation
- Arbitration is binding and final; litigation allows appeals
- Choose venue/law near where you are (home court advantage)

### Step 13: General Provisions
Standard housekeeping clauses.

**Amendment and Assignment**
```
12. GENERAL PROVISIONS

12.1 Amendment. This Agreement may be amended only by written agreement
     signed by both Parties. No oral amendments are valid.

12.2 Assignment. Neither Party may assign this Agreement without the other's
     prior written consent (except Company may assign to a successor entity
     in a merger/acquisition, with notice to Client).
```

**Entire Agreement**
```
12.3 Entire Agreement. This Agreement (including all Schedules and exhibits)
     constitutes the entire agreement between the Parties and supersedes
     all prior negotiations, representations, and agreements.

     Any prior agreements, purchase orders, or emails are void.
```

**Severability**
```
12.4 Severability. If any provision is found invalid, the remaining
     provisions shall remain in effect.
```

**Notices**
```
12.5 Notices. All notices shall be in writing and delivered by:

     (a) Hand delivery;
     (b) Email (if confirmed receipt);
     (c) Certified mail, return receipt requested.

     Addresses for notice:

     If to Company: {{Address, Email, Phone}}
     If to Client:  {{Address, Email, Phone}}
```

**Counterparts**
```
12.6 Counterparts. This Agreement may be executed in counterparts (PDF
     emails count), each as an original, all constituting one agreement.
```

**Governing Law**
```
12.7 Governing Law. This Agreement shall be governed by the laws of
     {{State/Country}}, without regard to conflict of laws principles.
```

## Output Template
```
                          {{CONTRACT TITLE}}

THIS {{CONTRACT TYPE}} (this "Agreement") is entered into as of
{{Date}}, by and between:

{{Your Company Name}}, a {{State}} {{entity}} ("Company")

AND

{{Other Party Name}}, a {{State}} {{entity}} ("{{Party Name}}")

---

1. RECITALS
   WHEREAS, {{Context 1}}; and
   WHEREAS, {{Context 2}}; and
   NOW, THEREFORE, {{Parties agree as follows}}.

2. DEFINITIONS
   {{Key defined terms (Confidential Information, Services, etc.)}}

3. SCOPE OF WORK
   3.1 Services: {{Description}}
   3.2 Deliverables: {{List with dates}}
   3.3 Exclusions: {{What's NOT included}}

4. OBLIGATIONS
   4.1 Company shall: {{List}}
   4.2 Client shall: {{List}}

5. REPRESENTATIONS AND WARRANTIES
   {{What each Party asserts as true}}

6. LIMITATION OF LIABILITY
   {{Cap on damages (typically 1x annual fees)}}

7. INDEMNIFICATION
   {{Who covers whose losses}}

8. TERM AND TERMINATION
   8.1 Term: {{Start–End dates}}
   8.2 Termination for Convenience: {{Notice period}}
   8.3 Termination for Cause: {{Breach conditions}}

9. INTELLECTUAL PROPERTY
   {{Who owns Deliverables vs. Pre-Existing IP}}

10. CONFIDENTIALITY
    {{Definition, obligations, duration}}

11. DISPUTE RESOLUTION
    {{Escalation → Mediation → Litigation/Arbitration}}

12. GENERAL PROVISIONS
    {{Amendment, Assignment, Entire Agreement, Governing Law}}

---

SIGNATURE BLOCK:

IN WITNESS WHEREOF, the Parties have executed this Agreement as of the
Effective Date.

COMPANY:                        CLIENT:

_______________________        _______________________
Signature                      Signature

_______________________        _______________________
Print Name & Title             Print Name & Title

_______________________        _______________________
Date                           Date

---

SCHEDULES:
Schedule A: Deliverables and Timeline
Schedule B: Pricing and Payment Terms
```

## Quality Gates
- [ ] Key definitions are clear and consistent throughout
- [ ] Scope section has in-scope AND out-of-scope items (prevents creep)
- [ ] Both parties' obligations are listed (not one-sided)
- [ ] Liability is capped at a defensible amount
- [ ] IP ownership is clear (Client owns deliverables, Company owns methodology)
- [ ] Termination clause exists (for cause and for convenience)
- [ ] Dispute resolution path is escalation-based (negotiation → mediation → litigation)
- [ ] Contract is signed by authorized representatives with titles
- [ ] Governing law and jurisdiction are specified

## Examples

### Good Output (excerpt)
```
2. SCOPE OF WORK

2.1 Services. Company shall provide:
    (a) AWS and Azure infrastructure audit (review 90 days of billing, assess
        architecture, identify savings opportunities)
    (b) Cost analysis report with top 20 optimization recommendations
    (c) FinOps governance framework design (cost allocation, chargeback model)

2.2 Deliverables:
    (a) Infrastructure Audit Report — Due Week 2, January 30, 2024
    (b) Cost Optimization Roadmap — Due Week 6, March 5, 2024
    (c) FinOps Framework Design Document — Due Week 8, March 20, 2024

2.3 Exclusions. NOT included in this SOW:
    (a) Implementation of optimization recommendations
    (b) Ongoing cost management or support post-delivery
    (c) Google Cloud services
    (d) Data migration or application refactoring

    Any work beyond this scope requires written change order.

6. LIMITATION OF LIABILITY
   6.1 EXCEPT FOR BREACHES OF CONFIDENTIALITY OR IP INFRINGEMENT,
       NEITHER PARTY'S LIABILITY SHALL EXCEED THE FEES PAID IN THE
       TWELVE MONTHS BEFORE THE CLAIM.

       Example: If Client pays Company $150K and claims $1M in damages,
       maximum liability is $150K.

9. INTELLECTUAL PROPERTY
   9.1 Client owns all Work Product (audit reports, recommendations).
   9.2 Company retains its pre-existing methodology and tools.
       Client may use methodology within reports, not separately.

12.7 GOVERNING LAW
     This Agreement is governed by California law, without regard to
     conflict of laws principles. Disputes shall be resolved in California
     state courts (or arbitration per Section 11).
```

### Bad Output (what to avoid)
```
Scope: "Company will help Client" (vague; not measurable)
No exclusions; Client thinks everything is included
Only Company has obligations; Client has none
No liability cap; Company exposed to unlimited damages
Unclear who owns the deliverables; copyright fights likely
No termination clause; how do you get out?
Signed by "Manager" without authority to bind the company
Governing law missing; which state's law applies?
```

## Common Mistakes

1. **Mistake**: Scope is vague ("provide consulting services").
   → **Fix**: List specific deliverables with dates (audit report due Week 2, recommendations due Week 4).

2. **Mistake**: Liability cap is missing; Company exposed to unlimited damages.
   → **Fix**: Cap liability at 1x annual contract value (reasonable and defensible).

3. **Mistake**: Only Company has obligations; Client obligations missing.
   → **Fix**: List what Client must do (provide access, respond to requests, etc.).

4. **Mistake**: IP ownership is unclear; both parties claim the work.
   → **Fix**: "Client owns all Deliverables; Company retains pre-existing methodology."

5. **Mistake**: No termination clause; stuck in agreement forever.
   → **Fix**: Include termination for cause (breach with cure period) and for convenience (30 days notice).

## Anti-Patterns
- Never sign a one-sided contract. (Get your obligations in writing too.)
- Never omit a liability cap. (Without cap, you're exposed to unlimited damages.)
- Never skip definitions. (Vague terms lead to disputes.)
- Never agree to "indemnify for any reason." (Narrow it to what you actually caused.)
- Never forget governing law/jurisdiction. (Disputes are costlier without a clear venue.)
- Never leave scope open. (List exclusions explicitly; scope creep kills profitability.)
- Never sign a contract unsigned by someone with authority. (Get title and signature authority confirmed.)
