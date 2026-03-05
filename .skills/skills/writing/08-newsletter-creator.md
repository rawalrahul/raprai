---
name: newsletter-creator
description: "Generate email newsletters optimized for open rates, click-through, and mobile display. Includes subject line formulas, preview text strategy, modular sections, and CTA hierarchy that segment audiences and respect inbox psychology."
category: writing
difficulty: intermediate
model_boost: "Eliminates generic newsletter templates; fixes missing preview text, poor CTA hierarchy, and mobile-breaking layouts"
---

# Newsletter Creator

## Purpose
Build email newsletters that maximize open rates through scientific subject line engineering, preview text strategy, and mobile-first formatting. This skill produces segmentation-ready content with clear CTA hierarchy, scannable architecture, and psychological triggers that increase click-through without resorting to clickbait or manipulation.

## When to Use
- Writing weekly/monthly subscriber newsletters with mixed content types
- Creating onboarding email sequences for new subscribers
- Designing promotional newsletters with product announcements
- Building educational digest emails (curation of external content)
- Crafting re-engagement campaigns for inactive subscribers
- **Do NOT use when**: designing transactional emails (order confirmations, password resets—different template needs), creating SMS bulk messages, or writing emails for cold outreach campaigns

## Instructions

### Step 1: Engineer the Subject Line
Subject lines determine 47% of open decisions; weak subjects lose 70% of potential readers.

**Use these proven formulas:**
- **Curiosity gap** ("The one LinkedIn habit I stole from Navy SEALs"—promises insight, creates pattern completion urge)
- **Number specificity** ("7 things" over "some things"; "23% more" over "significantly more"—brain trusts numbers)
- **Question format** ("Are you making this hiring mistake?"—creates cognitive tension requiring resolution)
- **Segmented specificity** ("For product managers: " or "[Company name] members:"—relevance increases open 12-18%)
- **Negative pattern interrupt** ("Don't [popular action]"—stops scroll, creates controversy check)
- **Time element** ("Last week's 3 biggest news items"—creates scarcity and urgency)

**Avoid:**
- ALL CAPS (spam-trigger, kills credibility)
- Excessive punctuation (!!!??? reads as low-quality)
- Generic openers ("Monthly update" or "Latest news"—zero differentiation)
- Misleading claims (damages open rates for NEXT email by 40% when opened disappointed)
- Subject longer than 50 characters (truncates on mobile, loses impact)

**Testing rules:**
- Test two subject lines: one curiosity-based, one number-based
- Change only ONE element (curiosity gap vs. question, not both simultaneously)
- Wait until Wednesday-Friday send for accurate opens (weekend sends inflate perceived performance)

### Step 2: Craft Preview Text Strategy
Preview text (47-100 characters visible in inbox preview) is FREE real estate most newsletters waste:

**Formula**: {{SUBJECT CONTINUATION}} + {{MICRO-VALUE}} + {{ACTION HINT}}

Example subject: "The one LinkedIn habit I stole from Navy SEALs"
Example preview: "Plus: why 90% of professionals don't use this. Read inside."

**Rules:**
- Never repeat subject line (wastes space, provides no new information)
- Include micro-value (number, insight, or benefit teaser) not visible in subject
- Always end with action hint ("Read inside," "Discover why," "See the full breakdown")
- Keep to 95 characters maximum (Gmail cuts at 123 on desktop, 50 on mobile)
- Use preview text unique to each segment (if segmenting, previews must validate subject's promise for each group)

### Step 3: Structure Content Architecture
Newsletter architecture determines whether readers scroll past first section (70% do) or stay engaged through CTAs.

**Mobile-first structure:**
```
HEADER: Logo + date (single line) + segmented subject line call-out
|
HERO SECTION: 1-2 sentence hook + primary CTA (button or link)
|
BODY SECTIONS:
  - Section 1 (lead story): 100-150 words + CTA
  - Section 2 (curated insight): 80-120 words + CTA
  - Section 3 (optional): 50-100 words
|
FOOTER: Social links + unsubscribe + company address (compliance)
```

**Formatting rules:**
- Maximum line length 65 characters (mobile constraint)
- White space between sections (crucial for mobile readability)
- Button CTAs (not just links) increase click-through 28%
- Color contrast ratio 4.5:1 minimum (accessibility + visibility)
- Font size minimum 14px for body text
- Alt text for ALL images (email clients block images by default; alt text shows purpose)

### Step 4: Design CTA Hierarchy
CTAs are the business outcome; poor hierarchy creates decision paralysis.

**Primary CTA (one per newsletter):**
- Placed after hook and first section (where attention is highest)
- Uses action verb ("Read the full report," "Register now," "Join the webinar")
- Button format (not plain link) with 15-20px padding
- Color contrasts with background (navy button on white, not gray on light blue)
- Account for "preview pane" constraint: primary CTA must be visible above fold without scrolling

**Secondary CTAs (2-3 maximum):**
- Placed end of relevant sections only (don't scatter throughout)
- Use different color or text-link format (visual distinction from primary)
- Each secondary CTA should branch to different audience segment intent

**Footer CTA:**
- Always include social shares (increases reach through network)
- Archive/past issues link (builds habit for regular readers)
- Preference center link, NOT just "unsubscribe" (reduces unsubscribe rate 15-40%)

### Step 5: Apply Segmentation Hooks
Segmentation increases click-through 14-30%; embed signals into copy:

**Segment signals in subject + preview:**
- Role-based: "For [Role]:" in subject line (product managers vs. executives read different angles)
- Behavior-based: "Since you read about [past topic]:" validates previous engagement
- Company-stage-based: "For early-stage founders:" or "For enterprise teams:"
- Interest-based: Previous click patterns determine content ordering (click science articles? Lead with that)

**Body section ordering by segment:**
- Product managers: Lead with strategy/vision → then tactics → implementation
- Executives: Lead with business impact → then strategy → optional deep-dive
- Founders: Lead with founder POV/story → then applicable tactics → resource links

### Step 6: Optimize for Email Client Rendering
Email clients render HTML differently; account for major constraints:

**Gmail/Apple Mail (66% of users):**
- Supports modern CSS; test with @media queries for mobile
- Images load by default (can use image-based text, but provide alt)
- Dark mode: test both light and dark versions; provide explicit dark mode styles

**Outlook (15% of users):**
- Limited CSS support; avoid margin, padding on containers
- Use nested tables for layout (not modern, but necessary)
- Test footer spacing (Outlook adds extra line breaks)

**Mobile rendering (55% of opens):**
- Single-column layout enforced
- Button width 100% on mobile (minimum 44px touch target)
- Font scaling: test 14px minimum, 18px headlines on actual mobile device
- Link spacing: minimum 20px vertical between clickable elements

### Step 7: Build Engagement Feedback Loops
Every newsletter should enable measurement for iteration:

**Metrics to track per section:**
- Subject line open rate (benchmark: 20-25% for regular newsletters)
- Click-through rate per section/CTA (benchmark: 2-5% depending on audience)
- Unsubscribe rate (benchmark: 0.1-0.5%; above 1% indicates content mismatch)
- Forward rate (indicates audience sees value worth sharing)

**Iteration cycle:**
- Test subject lines weekly; scale winners
- Track which sections get clicks (eliminate consistently low-CTR sections)
- Segment by engagement level; adjust frequency for inactive (Tuesday send for engaged, Thursday for lukewarm)

## Output Template

### Email Newsletter Structure
```
---HEADER---
[LOGO] | {{DATE}}

---HERO SECTION---
Subject line echo: "{{SEGMENTED_HOOK}}"

[Compelling hook sentence]
[CTA Button: {{ACTION_VERB}} →]

---SECTION 1: LEAD STORY---
Subheading: {{STORY_TITLE}}

[100-150 words on primary topic]
[CTA Link or Button: {{SECONDARY_ACTION}}]

---SECTION 2: CURATED INSIGHT---
Subheading: {{INSIGHT_TITLE}}

[80-120 words on supporting story or trend]
[CTA: {{DISCOVER_MORE_ACTION}}]

---SECTION 3: [OPTIONAL]---
[50-100 words on bonus content or resource]

---FOOTER---
[Social icons: {{PLATFORMS}}]
[Preference center link]
[Unsubscribe link]
[Company address + compliance text]

---METADATA---
Subject Line: {{SUBJECT_WITH_LENGTH}}
Preview Text: {{PREVIEW_WITH_LENGTH}}
Send Day/Time: {{OPTIMAL_SEND}}
Segment: {{AUDIENCE_SEGMENT}}
```

## Quality Gates
- [ ] Subject line contains number, question, curiosity gap, or segmentation keyword AND is under 50 characters
- [ ] Preview text differs from subject, includes micro-value, ends with action hint, and is under 95 characters
- [ ] Primary CTA appears above fold (visible without mobile scroll) and uses action verb
- [ ] Mobile rendering tested: single column, 14px+ body font, 44px+ touch targets, button widths at 100%
- [ ] All images include alt text that explains purpose if images don't load
- [ ] CTA hierarchy clear: 1 primary, 2-3 secondary max, each in logical section placement
- [ ] No section exceeds 150 words (scannable constraint—newsletters aren't articles)
- [ ] Segmentation signal visible in subject/preview line; body ordering matches segment intent
- [ ] Footer includes preference center link (reduces unsubscribe rate 15-40% vs. unsubscribe-only)
- [ ] All color contrast ratios meet 4.5:1 minimum for accessibility

## Examples

### Good Output (B2B Newsletter)

```
---HEADER---
[INSIGHTS LOGO] | March 5, 2026

---HERO---
For product managers: The hiring mistake costing you your best engineers

[Most companies hire engineers for what they can do. The best companies hire them for what they'll learn. Here's why that distinction matters.]

[CTA Button: Read the case study →]

---SECTION 1---
When hiring stalls growth: Why "years of experience" predicts nothing

Last week, Databricks' hiring manager published a contrarian take: her team's best engineers had the LEAST years of experience. Why? Because they optimized for learning velocity, not credential checking. She ran a study across 180 hires: engineers hired for "growth mindset" shipped 34% more features in year one, despite weaker GPAs.

The pattern: companies optimizing for pedigree grow slower than companies optimizing for velocity. One Sequoia partner calls it "the 10x signal everyone ignores."

[Read the full Databricks analysis]

---SECTION 2---
Quick hit: The LinkedIn habit I stole from Navy SEALs

SEAL teams use a "pre-game" ritual: 2 minutes of deliberate focus before any operation. Applied to hiring, that means: one hiring manager, 2-minute preparation per candidate (re-read CV, note 2-3 specific questions), zero distractions. Companies using this saw 23% fewer bad hires.

[See the manager checklist]

---SECTION 3---
Bonus resource: Compensation trend report (2026)
New data on how unicorns structure equity vs. salary, plus regional variance. [Access the report]

---FOOTER---
[Social icons] [Preference center] [Unsubscribe]
```

### Bad Output (what to avoid)

```
Subject: Monthly Newsletter
Preview: Check out this month's content!

Hello! This month we have lots of great updates for you. Our team has been working hard on new products and services. We hope you enjoy reading our newsletter.

Here are some topics we're covering:
- Topic 1
- Topic 2
- Topic 3

Click here to learn more about our services.

[Multiple links scattered everywhere]

Thanks for subscribing!

[Generic footer with no preference option]
```

## Common Mistakes

1. **Mistake**: Subject line and preview text nearly identical ("March Newsletter" subject / "March Newsletter with 3 great stories" preview) → **Fix**: Preview text should answer "why should I care?" after the subject creates curiosity. Subject hooks, preview validates the hook.

2. **Mistake**: Primary CTA buried in footer or after 300 words of text → **Fix**: Primary CTA appears after hook and first section (where 70% of readers still pay attention). Secondary CTAs in footer.

3. **Mistake**: Same newsletter sent to all segments (executives, managers, ICs) → **Fix**: Reorder sections by segment intent. Executives see business impact first; managers see implementation second; ICs see technical depth first.

4. **Mistake**: No preview text set (email client shows first 47 characters of body, usually "View in browser" or random text) → **Fix**: Always intentionally craft preview text; it's 10% more real estate to convince opens.

5. **Mistake**: Images without alt text; newsletter appears blank to image-blocking clients → **Fix**: Include alt text for all images explaining what they show. Test sending to Gmail account with images disabled.

## Anti-Patterns

- Never use ALL CAPS in subject lines (triggers spam filters, reads as low-quality)
- Never exceed 3 CTAs per newsletter (decision paralysis; readers will click first or none)
- Never send "test" or incomplete versions (damages email reputation, reduces deliverability)
- Never ignore mobile rendering (55% of opens are mobile; layouts breaking here are invisible failures)
- Never make unsubscribe difficult (legal requirement, and hard unsubscribe forces SPAM marking which damages reputation)
- Never test multiple variables simultaneously (can't isolate what drove performance change)
- Never assume same content works for all segments (role-based segmentation increases CTR 14-30%)
- Never send without confirming preview text is intentional (default preview text wastes 100 characters of persuasion)
