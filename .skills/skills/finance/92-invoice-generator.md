---
name: invoice-generator
description: "Create professional invoices with accurate line items, tax calculations, payment terms, late fee policies, multi-currency support, and tracking for reliable cash flow management."
category: finance
difficulty: beginner
model_boost: "Fixes cash collection delays from unprofessional invoicing and payment confusion"
---

# Invoice Generator

## Purpose

Sloppy invoices cost you cash. Missing payment terms, unclear line items, or no late fee policy delay payment and create disputes. This skill guides you through creating professional, legally sound invoices with clear payment expectations, accurate tax calculations, and multi-currency support (if needed). Whether you're freelancing, running a service business, or managing corporate billing, a standardized invoice template and process accelerates cash collection.

## When to Use

- You're a freelancer or service provider billing clients
- You own a business with recurring or one-off invoicing
- You want to reduce payment delays and billing disputes
- You're setting up invoicing for the first time or moving to a new system
- You need to invoice in multiple currencies or tax jurisdictions
- **Do NOT use when**: You have a dedicated accounting team (they'll have systems), you're owed just one payment (a simple email works), or you're completely automated (invoice generation is already built into your SaaS)

## Instructions

### Step 1: Choose Your Invoicing Method

**Option A: Template (Google Sheets, Excel, Word)**
- Cost: Free or $0-5
- Setup: 30 minutes
- Best for: Freelancers, small service providers
- Trade-off: Manual, prone to errors

**Option B: Invoicing SaaS (Wave, Square Invoices, FreshBooks)**
- Cost: $0-40/month (Wave free tier, most platforms $15-40)
- Setup: 1 hour
- Best for: Service businesses, recurring invoicing
- Trade-off: Learning curve, possible monthly fee

**Option C: Accounting Software (QuickBooks, Xero)**
- Cost: $15-100+/month
- Setup: 2-4 hours
- Best for: Growing businesses, tax/bookkeeping integration
- Trade-off: Overkill for freelancers, high cost

**Recommendation**: Start with a template (Option A) if you invoice <10 clients/month. Upgrade to SaaS (Option B) if you hit >20 invoices/month.

### Step 2: Design Your Invoice Header

Your invoice must identify you and the client clearly.

**Your Information** (top left):
- Legal business name (not nickname)
- Business address
- Phone and email
- Tax ID (EIN in US, VAT in EU, etc.)
- Logo (optional but professional)

**Client Information** (top right):
- Client name
- Client contact person
- Client mailing address
- Client tax ID (if applicable)

**Invoice Details** (center):
- Invoice number (e.g., INV-2026-001, formatted consistently)
- Invoice date (date issued)
- Due date (payment deadline; e.g., 30 days from invoice date)
- PO number (if client requires; they reference this)

**Example**:
```
ACME CONSULTING INC.          | Client: TechCorp Inc.
123 Main St, San Francisco    | Attn: Jane Smith
Tax ID: 12-3456789           | 456 Oak Ave, Seattle, WA 98101
(415) 555-1234              | Tax ID: 98-7654321
billing@acmeconsulting.com  |

INVOICE
Invoice #: INV-2026-00042
Invoice Date: 2026-03-05
Due Date: 2026-04-04
PO #: TC-2026-1001 (if provided)
```

### Step 3: Build Your Line Items (Detailed and Clear)

Each line item describes what you're billing for. Be specific.

**Bad line items:**
- "Consulting": Too vague; client will question it.
- "Work": What work?

**Good line items:**
```
Description                        | Quantity | Rate        | Amount
----                              | -------- | ----        | ------
Web design (homepage redesign)    | 40 hours | $150/hour   | $6,000
Content writing (3 blog posts)    | 3 posts  | $500/post   | $1,500
Revision rounds (2 additional)    | 2 rounds | $300/round  | $600
Project management                | 1        | $1,000      | $1,000
                                  |          | Subtotal:   | $9,100
```

**Clarity rules**:
- What was delivered? (homepage redesign, 10 pages of content, 20-hour consulting engagement)
- How many? (hours, posts, days, units)
- What's the rate? (hourly, per-unit, fixed fee)
- What's the total? (Qty × Rate)

Include units (hours, days, per-project) so the client can verify. If you billed 40 hours at $150/hour but the client thinks you worked 30 hours, show the math: 40 × $150 = $6,000. Transparency prevents disputes.

### Step 4: Add Taxes (Jurisdiction-Specific)

Tax is client-dependent and jurisdiction-dependent. Know the rules in your jurisdiction and your clients'.

**In the USA (Sales Tax)**:
- Most states: Add sales tax (varies 5-10%) based on client location
- Exceptions: Some states don't tax services; most tax goods
- Rule: Charge tax if your client is in-state, unless they're tax-exempt (nonprofits, resellers)

**In the EU (VAT - Value Added Tax)**:
- Standard: Add 17-25% VAT (varies by country)
- B2B exception: If client is a business in the EU with a VAT ID, you may not charge VAT (they claim it back), but you still need their VAT ID on the invoice
- Rule: Charge VAT unless customer has VAT ID from EU

**In Canada (GST/HST)**:
- Small businesses (<$30k/year): No GST required
- Larger: 5% GST or 13-15% HST depending on province

**International (Multiple Taxes)**:
- Keep it simple: Research each client's jurisdiction once, file it, and reuse
- OR use an invoicing tool that handles this automatically

**On the invoice**:
```
Subtotal:           $9,100
Sales Tax (8%):       $728  (if US, California client)
or
Subtotal:           $9,100
VAT (20%):          $1,820  (if EU, B2B with VAT ID exempt)
                   -------
Total Due:         $10,628 (or $9,100 if VAT exempt)
```

**Notes**:
- If VAT exempt: "VAT not charged - client VAT ID: [VAT#]"
- If tax-exempt: "Tax-exempt - exemption #: [#]"

### Step 5: Define Payment Terms and Due Date

Clear payment terms prevent disputes and cash flow delays.

**Common terms**:
- **Net 30**: Due 30 days from invoice date (standard B2B)
- **Net 15**: Due 15 days (faster payment, common for smaller invoices)
- **Net 60**: Due 60 days (usually for large accounts or government clients)
- **Due on receipt**: Payment due immediately (rare, use for upfront services)
- **2/10 Net 30**: 2% discount if paid within 10 days, otherwise due in 30 days (incentivizes early payment)

**Pick one and be consistent**. Document it on every invoice.

**On the invoice**:
```
Terms: Net 30
Due Date: 2026-04-04 (30 days from invoice date)
```

Or, if you offer an early-pay discount:
```
Terms: 2/10 Net 30
If paid by 2026-03-15: $10,415 (2% discount)
If paid by 2026-04-04: $10,628
```

### Step 6: Add Late Fee Policy (Teeth for Delinquent Accounts)

Late payment is common. A stated late fee encourages on-time payment and compensates you for collection costs.

**Late fee options**:
- **Fixed fee**: "$50 per month late" (simple, enforceable)
- **Percentage**: "1.5% per month on unpaid balance" (compounds, incentivizes faster payment)
- **Interest**: "Prime + 5%" (less common for small businesses)

**Legal note**: Some jurisdictions have limits on late fees. In the US, FDCPA sets reasonable limits; check your state. In EU, Late Payment Directive allows statutory interest + reasonable collection costs.

**On the invoice**:
```
Terms: Net 30
Late Payment Fee: $50 per month or 1.5% monthly interest, whichever is greater
```

State it clearly so it's enforceable if you need to collect.

### Step 7: Payment Instructions (Make It Easy to Pay)

The easier you make payment, the faster you get paid.

**Payment methods** (offer multiple):
- Bank transfer (ACH in US, SEPA in EU): Lowest cost to you, secure
- Credit card (Stripe, Square): Faster but you pay 2-3% processing fee
- PayPal/Venmo: Informal, okay for small amounts
- Check: Slow but sometimes required
- Wire transfer: Expensive for small amounts

**On the invoice**:
```
PAYMENT INSTRUCTIONS

Bank Transfer (ACH) [Preferred]:
  Bank Name: First National Bank
  Account Name: ACME Consulting Inc.
  Account Number: 1234567890
  Routing Number: 123456789
  Reference: Invoice #INV-2026-00042

Credit Card:
  Pay online: [link to Stripe or payment portal]

PayPal:
  billing@acmeconsulting.com
```

Provide bank details clearly. Don't ask clients to Google you; it delays payment.

### Step 8: Add Terms & Conditions (Legal Protection)

Small terms clarify expectations and protect you legally.

**Standard clauses**:

**Scope of Work**:
"Services rendered per the engagement letter dated [date]. Additional work outside the scope will be billed at $[rate]/hour."

**Payment Terms**:
"Payment is due by [DATE]. Late payments accrue interest of 1.5% per month."

**Confidentiality**:
"Any confidential information shared by the client remains confidential and will not be disclosed to third parties."

**Limitation of Liability**:
"In no event shall [Your Company] be liable for any indirect or consequential damages."

**Dispute Resolution**:
"Any disputes will be resolved via arbitration under the laws of [JURISDICTION]."

**Termination**:
"The client may terminate this engagement with 7 days' notice. All work completed to date is non-refundable."

**Example footer**:
```
TERMS & CONDITIONS

Payment is due by 2026-04-04. Invoices not paid within 30 days of the due date
accrue late fees of 1.5% per month.

Services rendered per the engagement letter dated 2026-02-01. Any additional
work outside the agreed scope will be billed separately.

Disputes will be resolved via arbitration under the laws of California.
```

Keep it short; don't overwhelm the client. But state the key protections.

### Step 9: Multi-Currency (If You Invoice Internationally)

If you bill clients in multiple currencies, decide on currency upfront.

**Options**:
- **Always invoice in your home currency**: Simplest, client bears exchange rate risk
- **Invoice in client's currency**: Better for international clients, you bear exchange rate risk
- **Invoice in a neutral currency (USD)**: Standard for B2B, accepted globally

**On the invoice**:
```
All amounts in USD.
Exchange rate (if applicable): 1 USD = 0.92 EUR (as of 2026-03-05)
Payment in USD to: [bank account]
```

If the client asks you to invoice in their currency, use the exchange rate on the invoice date (or use a service like Stripe that handles conversion).

**Avoid ambiguity**: Specify currency (USD, EUR, GBP) on every monetary amount.

### Step 10: Create Your Invoice Template and Process

**Build your template** (Google Docs, Excel, or invoicing tool):
- Use consistent formatting (fonts, colors, spacing)
- Build formulas so totals auto-calculate
- Pre-fill your company info; only change client details
- Save as a template, not a one-off

**Your invoicing process**:

1. **On Project Start**: Get client's full legal name, address, tax ID, PO# (if required), preferred payment method
2. **As Work Progresses**: Track hours, deliverables, or milestones (daily/weekly; don't wait until project end)
3. **Before Invoice**: Confirm with client: "I'll send you an invoice for $X on [date]. Sound good?" (prevents surprises)
4. **Generate Invoice**: Use template, fill in details, calculate total, sign (if required)
5. **Send Invoice**: Email with subject "Invoice #INV-2026-00042 due 2026-04-04" (clear in subject line)
6. **Track and Follow Up**:
   - Log invoice in a spreadsheet (invoice #, date, amount, client, due date, status)
   - 5 days before due: Check if paid. If not, send reminder.
   - On due date + 5 days: Send first late notice.
   - On due date + 15 days: Send second notice, escalate to manager or attorney if needed.

### Step 11: Invoicing Tools Comparison

**Wave (Free)**:
- No cost for invoicing
- Auto-reminders for unpaid invoices
- Basic reports
- Good for <50 invoices/month

**Stripe Billing**:
- $0.50 per invoice + payment fees
- Recurring billing, subscriptions
- Good for SaaS or subscription models

**Freshbooks**:
- $15-55/month
- All invoicing features, time tracking, expense management
- Good for service businesses

**Xero**:
- $13-70/month
- Accounting-grade invoicing, integration with accounting
- Good for businesses with bookkeeping needs

Pick one; don't overthink it. All do the job.

## Output Template

```
# Invoice Generator Setup

## Invoicing Method
[ ] Template (Excel/Sheets/Docs) | [ ] Wave | [ ] FreshBooks | [ ] Other

## Your Business Information
- Legal Business Name: [NAME]
- Address: [ADDRESS]
- Phone: [NUMBER]
- Email: [EMAIL]
- Tax ID: [ID#]
- Logo: [LOGO or NONE]

## Invoice Numbering Scheme
Format: [PREFIX]-[YEAR]-[NUMBER]
Example: INV-2026-00042
Starting #: [#]

## Billing Details
- Line Item Template: [Attach or describe]
- Tax Jurisdiction(s): [Your state/country]
- Tax Rate: [%]
- Multi-Currency: [Yes/No] | Currencies: [List]

## Payment Terms
- Standard Terms: Net 30 (or your default)
- Early Pay Discount: [None or percentage]
- Late Fee: 1.5% per month

## Payment Methods (Accepted)
- [ ] Bank Transfer | Details: [bank info or "to be provided"]
- [ ] Credit Card | Stripe/Square link: [LINK]
- [ ] PayPal | Email: [EMAIL]
- [ ] Check | Mailing address: [ADDRESS]

## Invoice Template
- [Attach template or describe location]
- Formula for total (tax auto-calculated): [Yes/No]

## Invoicing Process
1. Collect client info on project start
2. Track work weekly (hours, deliverables)
3. Confirm invoice amount with client 3 days before invoicing
4. Generate and send invoice
5. Follow-up timeline:
   - Day -5 (5 days before due): Check payment
   - Day 0 (Due date): If not paid, send reminder
   - Day +5: First late notice
   - Day +15: Second notice, escalate

## Invoice Tracking System
- Tool: [Spreadsheet / Invoicing app]
- Tracked fields: Invoice #, date, amount, client, due date, status, paid date
- Review cadence: [Weekly/Biweekly]

## Legal Terms & Conditions
[List key clauses: payment due date, late fee, scope, confidentiality, dispute resolution]

## Testing
- [ ] Sent test invoice to self, verified all calculations
- [ ] Confirmed bank transfer details with client
- [ ] Reviewed for spelling, correct amounts, clear due date
```

## Quality Gates (5+)

1. **Line Items Specific**: Could a client dispute any line item? If yes, be more specific.
2. **Taxes Calculated Correctly**: Have you verified tax rate for your jurisdiction and client location?
3. **Payment Instructions Clear**: Can someone with no prior context complete payment in <2 minutes?
4. **Due Date Explicit**: Is the actual due date (not just "Net 30") on the invoice?
5. **Late Fee Stated**: Is late fee clear and reasonable for your jurisdiction?
6. **Template Reusable**: Can you reuse the template for next invoice with minimal changes?

## Examples

### Good Invoice (Clear, Professional, Low Disputes)

```
ACME CONSULTING                         Client: TechCorp Inc.
San Francisco, CA                       Attn: Jane Smith
Tax ID: 12-3456789                     456 Oak Ave, Seattle, WA 98101
billing@acmeconsulting.com             Tax ID: 98-7654321

INVOICE
Invoice #: INV-2026-00042
Invoice Date: 2026-03-05
Due Date: 2026-04-04 (Net 30)
PO #: TC-2026-1001

DESCRIPTION                              QTY  |  RATE      | AMOUNT
Website redesign (homepage + 2 subpages)  40   | $150/hr    | $6,000
Blog post writing (3 posts, SEO-optimized) 3  | $500/post  | $1,500
Revision round (2 additional)              2   | $300/round |   $600
Project management                         1   | $1,000/mo  | $1,000
                                                            --------
Subtotal:                                                   $9,100
Sales Tax (8% - WA):                                          $728
                                                            --------
TOTAL DUE:                                                 $10,628

PAYMENT INSTRUCTIONS

Bank Transfer (ACH) [Preferred]:
  Bank: First National Bank, SF
  Account: ACME Consulting Inc.
  Account #: 1234567890
  Routing #: 123456789
  Reference: INV-2026-00042

Credit Card:
  https://stripe.acmeconsulting.com/pay

TERMS: Payment due 2026-04-04. Late payments accrue 1.5% monthly interest.
Services per engagement letter of 2026-02-01. Additional work outside scope billed separately.
```

---

### Bad Invoice (Vague, Confusing, Delays Payment)

```
ACME CONSULTING
Invoice #1
For: TechCorp
Due: In 30 days
Amount: $10,628

Work done:
- Website stuff: $6,000
- Writing: $1,500
- Revisions: $600
- Other: $1,000
- Tax: $728

Questions?
Send us a check or something.
```

Problems:
- Invoice # not formatted; hard to track
- "Website stuff" is vague; client may question
- No specific due date; client may pay when they feel like it
- No tax explanation
- No payment instructions
- Handwavy closing ("or something")

## Common Mistakes (3+)

1. **Vague Line Items**: "Consulting" instead of "20 hours web strategy consulting" invites negotiation and disputes. Be specific: what was delivered?

2. **Wrong Tax Rate**: You charged 10% tax when your client's location requires 8%. Client notices, disputes invoice, delays payment. Verify tax rates by jurisdiction beforehand.

3. **No Due Date**: "Net 30" is relative; client may interpret differently. Put the actual date (2026-04-04). Remove ambiguity.

4. **Missing Payment Instructions**: Client asks "where do I send the check?" You respond, they follow up, payment delays another week. Include all payment methods and details upfront.

5. **No Late Fee**: Without late fee, there's no consequence for late payment. State a late fee clearly (1.5% per month is common).

6. **Inconsistent Invoicing**: Invoice 1 due "Net 30," Invoice 2 due "in 30 days," Invoice 3 due "by [date]." Consistency matters. Use same terms for all clients.

## Anti-Patterns (3+)

1. **Invoicing Too Late**: You finish project in month 1, invoice in month 3 (forgotten). Invoice as soon as work is done or on a regular schedule (e.g., monthly on the 1st). Fresh invoice = faster payment.

2. **No Follow-Up**: You send invoice, never check if it's been paid until you need the cash. Calendar reminder: 5 days before due date, follow up with client. Proactive follow-up accelerates payment.

3. **No Dispute Prevention**: You invoice for 50 hours but client thinks it's 40. No surprise: they dispute and withhold payment. Confirm hours weekly or in real time; don't wait until invoice to surface discrepancies.

4. **Too Lenient Terms**: You offer "Net 60" to all clients to be friendly, but it kills your cash flow. Standard is Net 30. Be consistent and firm on payment terms.

---

**Next Steps**: Create your first invoice using the template. Include line items, your payment methods, and late fee. Send to a trusted advisor for feedback. Once approved, save as your standard template.
