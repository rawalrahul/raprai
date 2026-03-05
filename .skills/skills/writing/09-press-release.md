---
name: press-release-writer
description: "Generate AP-style press releases with inverted pyramid structure, attributed quotes, boilerplate section, and media contact details. Follows industry standards for newsworthiness, quote attribution, and distribution formatting."
category: writing
difficulty: beginner
model_boost: "Fixes journalistic structure violations (burying lead, unattributed claims, missing boilerplate); enforces AP style standards"
---

# Press Release Writer

## Purpose
Produce AP-compliant press releases that journalists and news aggregators actually use. This skill applies the inverted pyramid structure (most newsworthy information first), proper quotation formatting, and journalism standards that increase pickup probability in media outlets, newswires, and industry publications.

## When to Use
- Announcing company funding, acquisitions, or major partnerships
- Launching new products or significant feature releases
- Reporting research findings, survey results, or industry milestones
- Appointing executives or announcing leadership changes
- Announcing awards, certifications, or industry recognitions
- **Do NOT use when**: creating internal announcements (use memo format), marketing promotional materials (use press release with different tone), or sharing unverified claims (must have third-party validation or data)

## Instructions

### Step 1: Validate Newsworthiness
Not every announcement is a press release. Filter through these criteria:

**High newsworthiness** (tier 1):
- First-to-market announcement (product, service, or approach never publicly available before)
- Significant funding event ($1M+) from recognized VCs or strategic investors
- Executive appointments with clear industry impact
- Research findings with data, published study, or third-party validation
- Acquisitions, mergers, or strategic partnerships changing market position
- Awards from recognized third-party organizations
- Market entry into new geography or vertical with significant business impact

**Medium newsworthiness** (tier 2):
- Feature releases solving documented industry problem
- Expansion announcements (new office, significant hiring)
- Certifications or compliance milestones (SOC 2, ISO, etc.)
- Customer wins if customer is well-known or achievement is quantified
- Research or data insights with credible methodology

**Low newsworthiness** (tier 3 - reconsider):
- Routine product updates or bug fixes (not newsworthy without context)
- Customer logos without specific achievement attached
- Rebrands or logo changes (internal interest only)
- Participation in events without speaker/award component
- "Thought leadership" positioning without research backing

### Step 2: Craft the Lede (Opening Paragraph)
The lede contains the complete story; journalists decide whether to read further in 3 seconds.

**Formula**: {{WHO}}, {{WHAT}}, {{WHEN}}, {{WHERE}}, {{WHY}} all in 2-3 sentences

**What goes in the lede:**
- Company name and the NEWS (not context, not background)
- Single most newsworthy fact (funding amount, product launch, appointment, acquisition)
- Immediate business impact or significance
- Date of announcement (today's date if day-of release)
- Location if relevant to story (e.g., "headquartered in Boston")

**What does NOT go in lede:**
- Company history ("Founded in 2015...")—save for boilerplate
- Multiple products or updates (lead with ONE, mention others later)
- Vague claims ("innovative," "disrupting," "leading")—use specific metrics
- Opinion or positioning language (journalist's job to interpret significance)

**Lede formula by category:**

*Funding:*
"{{COMPANY}} announced a {{ROUND}} funding round of {{AMOUNT}} led by {{LEAD_INVESTOR}} {{DATE}} to {{PRIMARY_USE}}, {{SECONDARY_USE}}."

*Product launch:*
"{{COMPANY}} launched {{PRODUCT_NAME}}, a {{CATEGORY}} designed to {{CORE_BENEFIT}}, {{DATE}}. The tool {{SPECIFIC_CAPABILITY}} {{SUPPORTING_CAPABILITY}}."

*Executive appointment:*
"{{COMPANY}} appointed {{PERSON_NAME}} as {{TITLE}}, effective {{DATE}}. {{PERSON}} joins from {{PREVIOUS_ROLE}} where [brief credential]."

*Acquisition:*
"{{COMPANY}} acquired {{TARGET_COMPANY}}, a {{TARGET_CATEGORY}}, for {{AMOUNT/UNDISCLOSED}} {{DATE}} to {{STRATEGIC_BENEFIT}}."

### Step 3: Structure the Body (Inverted Pyramid)
Pyramid order: most newsworthy facts first, supporting details after, context and background last.

**Paragraph 2: Supporting newsworthy detail**
- Expand on the lede's key claim with one additional piece of information
- Could be: second use case, additional funding co-lead, second executive appointment, customer win
- One paragraph maximum (3-4 sentences)

**Paragraph 3-4: Quantifiable impact or product details**
- If funding: total addressable market, current revenue, customer count, growth rate
- If product: user problem solved (with metric), unique approach or technical innovation
- If appointment: specific achievements in previous role (not generic praise)
- Data should be specific ("34% faster" not "significantly faster")

**Paragraph 5: Market context or problem statement**
- Industry problem being addressed (with source if available)
- Market size or trend supporting the announcement
- Competitor landscape or standard approach (without naming)
- Keep to 2-3 sentences; this contextualizes for journalists unfamiliar with vertical

**Paragraph 6-7: Quote #1 from CEO/Founder**
- Builds credibility; provides human voice journalists need
- Quote should expand on announcement's significance, not repeat lede
- Provide context: {{TITLE}}: "{{QUOTE}}"
- Quote should be 1-2 sentences (journalists trim longer quotes)
- Avoid generic praise ("We're excited to announce..."); use specific business language

**Paragraph 8-9: Supporting details (customer validation, features, use cases)**
- If funding: expected milestones, hiring plans
- If product: specific features with use case examples
- If appointment: team reporting structure, strategic focus areas
- Cite research or third-party validation (analyst firms, surveys)

**Paragraph 10: Quote #2 from investor/customer/partner**
- Third-party validation of newsworthiness
- For funding: investor perspective on market opportunity
- For product: customer problem statement and solution fit
- For appointment: reference to what person will accomplish

**Paragraph 11: Company background (boilerplate)**
- Standard 2-3 sentence description of what the company does
- Include founding year, headquarters, total funding if material
- Customer count or market position if available
- Website URL and social media handles
- Separate boilerplate with "###" line break (industry standard)

### Step 4: Write Quotation Blocks Strategically
Quotes are the most-read component (after headline); they carry the personality and credibility.

**Quote rules:**
- Speaker title: always include full title at time of quote
- Quote content: specific, opinion-based, or strategic—never fact-based statements (those go in body)
- Quote length: 1-2 sentences maximum (journalists cut long quotes)
- Frequency: 2-3 quotes per release maximum (more feels promotional)
- Attribution format: {{TITLE}}: "{{QUOTE}}"

**Quote examples:**

Bad: "We're excited to announce this funding round and are thankful to our investors for their support."
Good: "This funding validates our thesis: companies waste 40% of their training budgets. We're using this capital to automate that waste."

Bad: "Our new product is innovative and will disrupt the market."
Good: "Most compliance tools force managers to become admins. Our tool runs compliance checks in the background, freeing managers to focus on growth."

### Step 5: Add Media Contact and Boilerplate
Press releases end with formalized contact and company description.

**Format:**

```
###

About {{COMPANY_NAME}}

[2-3 sentence description of company, what it does, mission]

[Founding year, headquarters, key metrics: funding raised, customer count, or market position]

[Website, social handles if notable]

For media inquiries:
{{CONTACT_NAME}}
{{TITLE}}
{{COMPANY_NAME}}
{{EMAIL}}
{{PHONE}}
```

**Boilerplate guidelines:**
- Written in third person (not "we are," but "{{COMPANY}} is")
- Factual, not promotional (no "leading," "innovative," or "best-in-class")
- 2-3 sentences maximum
- Include founding year if company is under 10 years old (signals startup)
- Include customer count if 100+ or market position if unique
- Only include social handles if journalist audience uses them (usually not)

### Step 6: Format for Distribution
AP style and wire service standards ensure maximum distribution.

**Technical formatting:**
- Headline: CAPS, 10 words maximum, leads with news (e.g., "DATABRICKS RAISES $150M IN SERIES E FUNDING")
- Dateline: {{CITY, STATE}} – Month Date, Year (e.g., "SAN FRANCISCO, Calif. – March 5, 2026 –")
- Spacing: Double-spaced body (tradition, makes editing visible)
- Line length: 65-70 characters (readable in most email clients)
- Total length: 400-600 words (journalists skim; use newswire word limits)

**Structure checklist:**
```
[HEADLINE]

[DATELINE]

[LEDE PARAGRAPH]

[Body paragraphs 2-10]

###

[BOILERPLATE]

[MEDIA CONTACT]
```

### Step 7: Prepare for Multiple Distribution Channels
Different outlets have different requirements; prep for variations.

**Print/traditional newswires:**
- Headline emphasizes news value
- Lede contains all critical facts (some journalists only read first paragraph)
- Quotes from recognized executives (journalists trust authority figures)
- Boilerplate is standard

**Online/digital outlets:**
- Headline includes keyword (SEO matters for online distribution)
- Dateline includes city for geographic relevance
- Quotes from founder/CEO + customer/partner (validation matters)
- Links to website in boilerplate (digital audiences expect clickable assets)

**Industry publications:**
- Vertical-specific language (terminology familiar to insiders)
- Industry problem framing (appeals to trade publication editors)
- Customer win story angle (industry pubs focus on application, not announcement)

## Output Template

```
{{HEADLINE_ALL_CAPS_10_WORDS_MAX}}

{{CITY_STATE}} – {{MONTH_DATE_YEAR}} –

{{LEDE_2-3_SENTENCES_WHO_WHAT_WHEN_WHERE_WHY}}

{{SUPPORTING_DETAIL_1_PARAGRAPH_EXPANSION}}

{{QUANTIFIABLE_IMPACT_OR_PRODUCT_DETAILS_2_PARAGRAPHS}}

{{MARKET_CONTEXT_PARAGRAPH}}

{{EXECUTIVE_QUOTE_PARAGRAPH}}

{{SUPPORTING_DETAILS_FEATURES_CUSTOMERS_2_PARAGRAPHS}}

{{INVESTOR_OR_CUSTOMER_VALIDATION_QUOTE_PARAGRAPH}}

###

About {{COMPANY_NAME}}

{{2-3_SENTENCE_COMPANY_DESCRIPTION}}

For media inquiries:
{{CONTACT_NAME}}
{{TITLE}}
{{EMAIL}}
{{PHONE}}
```

## Quality Gates
- [ ] Lede answers WHO, WHAT, WHEN, WHERE, WHY in 2-3 sentences with most newsworthy fact first
- [ ] No marketing language ("innovative," "disruptive," "leading," "excited") in body paragraphs
- [ ] All claims backed by data or attribution (no "significantly" without metric, "customers love" without quote)
- [ ] Quotes are opinion-based or strategic, not factual restatement of lede
- [ ] Quote attribution includes full title at time of quote
- [ ] Release is 400-600 words with inverted pyramid structure (most newsworthy facts first, background last)
- [ ] Boilerplate is 2-3 sentences in third person with founding year and key metrics
- [ ] Media contact section includes name, title, email, phone
- [ ] Dateline uses AP format: {{CITY_STATE}} – {{MONTH_DATE_YEAR}}
- [ ] Headline is all caps and under 10 words, emphasizing news value not positioning

## Examples

### Good Output (Funding Announcement)

```
DATABRICKS RAISES $150M IN SERIES E TO SCALE AI INFRASTRUCTURE

SAN FRANCISCO, Calif. – March 5, 2026 –

Databricks announced a Series E funding round of $150 million led by Sequoia Capital, valuing the company at $43 billion. The funding supports expansion into enterprise AI infrastructure, following 127% year-over-year revenue growth.

The company now has 1,200+ enterprise customers, including 50% of Fortune 500 companies. Databricks powers machine learning pipelines handling 13 trillion daily transactions across customer networks.

The market opportunity is substantial. Gartner estimates the enterprise AI infrastructure market will reach $89 billion by 2028, with enterprises currently spending 40% of AI budgets on inefficient data pipeline infrastructure.

"Most enterprises are data-rich but insight-poor," said Ali Ghodsi, CEO and co-founder of Databricks. "Our customers save 6 months and $8 million per AI project by using unified infrastructure instead of cobbled point solutions. This funding accelerates our roadmap to make that timeline standard across industries."

Databricks' platform consolidates three functions—data engineering, analytics, and AI—eliminating data silos that currently plague enterprise AI adoption. The Series E will fund expansion in Europe and Asia-Pacific, where demand for unified infrastructure exceeds domestic supply by 3:1.

"Databricks is solving the data infrastructure problem that has frustrated every major enterprise we work with," said Jess Lee, partner at Sequoia Capital. "This round reflects our conviction that unified infrastructure will become table stakes for enterprise AI adoption, similar to how Hadoop standardized data warehousing."

The company plans to hire 300 engineers in the next 18 months, focusing on product velocity and customer success. All-hands meeting is scheduled for March 10.

###

About Databricks

Databricks provides the Lakehouse Platform, which consolidates data engineering, analytics, and machine learning in a single, unified system. Founded in 2013 and headquartered in San Francisco, Databricks is used by 50% of Fortune 500 companies and has processed over 13 trillion daily transactions. The company has raised $1.4 billion in total funding.

For media inquiries:
Sarah Chen
VP of Communications
Databricks
sarah.chen@databricks.com
(415) 555-0147
```

### Bad Output (what to avoid)

```
DATABRICKS ANNOUNCES EXCITING NEW FUNDING

We're thrilled to announce Databricks has raised a significant Series E funding round led by prestigious investors. This exciting milestone validates our innovative approach to data infrastructure.

Databricks is a leading provider of AI and machine learning infrastructure. Customers love our products and we have grown rapidly. We serve many large enterprises.

We will use the funding to expand our team and invest in R&D. We're excited about the future and what we can accomplish with this capital.

"Databricks is an innovative company that will disrupt the data infrastructure space," said an investor representative.

Our team is committed to delivering the best-in-class solutions to our customers.

For more information, visit databricks.com
```

## Common Mistakes

1. **Mistake**: Burying the news (lede opens with company history "Founded in 2013, Databricks has always focused on...") → **Fix**: Lead with the newsworthy fact in first sentence. History goes in boilerplate.

2. **Mistake**: Unattributed claims ("Customers save $8M per project") used as fact in body → **Fix**: Either include metric in company press release data with source, or attribute to executive quote.

3. **Mistake**: Marketing language in press body ("innovative solution," "disruptive technology," "delighted to announce") → **Fix**: Replace with specific facts and data. Marketing language is why journalists ignore company press releases.

4. **Mistake**: Quote length exceeds 2 sentences or restates the lede → **Fix**: Quotes should provide new perspective or strategic reasoning, not repeat announcement details.

5. **Mistake**: Missing boilerplate or contact information → **Fix**: Include "About {{Company}}" section with founding year, headquarters, customer count or market position, AND contact name/title/email/phone for journalists.

## Anti-Patterns

- Never lead with company positioning ("{{Company}} is a leading provider of...") instead of news value
- Never use ALL CAPS except for headlines and after "###" sections
- Never include hyperlinks in body (journalists copy/paste; links break); include website in boilerplate
- Never make financial claims without attribution (specify "company reported" vs. third-party analyst)
- Never exceed 600 words (journalists have seconds to decide; long releases get deleted)
- Never quote generic praise ("great partner," "excited announcement"); quotes must add new information
- Never omit media contact section (journalists need a clear way to request comment or clarification)
- Never send without spell-check and fact verification (credibility is the press release's only asset)
